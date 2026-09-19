import os, threading, time, requests, json
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

def get_env(*names):
    for n in names:
        v = os.getenv(n)
        if v:
            print(f"ENV trouvé: {n} = OK")
            return v
    return None

API_KEY = get_env("API_KEY","BYBIT_API_KEY","BYBIT_KEY","BYBIT_API","APIKEY")
API_SECRET = get_env("API_SECRET","BYBIT_API_SECRET","BYBIT_SECRET","BYBIT_API_SEC","APISECRET")
BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN","TG_TOKEN","BOT_TOKEN","TELEGRAM_TOKEN")
CHAT_ID = get_env("TELEGRAM_CHAT_ID","TG_ID","CHAT_ID","TELEGRAM_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL","https://kittra-ninja-ultime.onrender.com")
WALLET_TRADING_INTERNE = get_env("WALLET_TRADING_INTERNE","BYBIT_UNIFIED") or "BYBIT_UNIFIED"
WALLET_EPARGNE_EXTERNE = get_env("WALLET_EPARGNE_EXTERNE","WALLET_EXTERNE") or "TG8UcJUH152YyWsSArL4cwwV78GZiYJoqG"

print("=== KITTRA V18.6 GARDE-FOU 30% LIBEREE ===")
print(f"KEY:{bool(API_KEY)} SEC:{bool(API_SECRET)} TG:{bool(BOT_TOKEN)}")

session = None
if API_KEY and API_SECRET:
    try:
        session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)
        print(">>> Session Bybit OK ✅")
    except Exception as e:
        print(f">>> Erreur {e}")
else:
    print(">>> PAS DE SESSION")

# CONFIG CORRIGEE 30% GARDE-FOU
CONFIG = {
    "principal": 10.3443,
    "principal_securite": 0.30, # 30% GARDE = 3.10$ bloque, 70% = 7.24$ pour trader
    "coffre_total": 0,
    "urgences_lock": 0,
    "wallet_perso": {"last_withdraw": datetime.utcnow()-timedelta(days=31)},
    "memoire": {"business":0,"maison":0,"enfants":0},
    "repartition": {"trading":40,"urgences":24,"business":12,"maison":8,"enfants":4}
}

AUTO_COINS = ["BTCUSDT","SOLUSDT","ETHUSDT","TRXUSDT","BNBUSDT","XRPUSDT","AVAXUSDT","DOGEUSDT"]
price_history = {}
positions = {}
KITTRA_FILE = "Kittra.json"

def load():
    global positions
    try:
        with open(KITTRA_FILE,"r") as f:
            data=json.load(f)
            positions=data.get("positions",{})
    except: pass

def save():
    with open(KITTRA_FILE,"w") as f:
        json.dump({"positions":positions, "cap":CONFIG["principal"]}, f)

def send_tg(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_real_balance():
    if not session: return None
    try:
        coins = session.get_wallet_balance(accountType="UNIFIED")['result']['list'][0]['coin']
        for c in coins:
            if c['coin']=='USDT':
                return float(c['walletBalance'])
        return float(coins[0]['walletBalance']) if coins else 0.0
    except Exception as e:
        print(f"BAL ERROR {e}"); return None

def get_signal(symbol):
    if not session: return None,None,None,None,None
    try:
        kl = session.get_kline(category="spot",symbol=symbol,interval="15",limit=30)['result']['list']
        closes = [float(k[4]) for k in reversed(kl)]
        if len(closes)<21: return None,None,None,None,None
        ema9=sum(closes[-9:])/9; ema21=sum(closes[-21:])/21
        gains=[max(0,closes[i]-closes[i-1]) for i in range(1,15)]
        losses=[max(0,closes[i-1]-closes[i]) for i in range(1,15)]
        rsi=100-(100/(1+(sum(gains)/14)/(sum(losses)/14+0.00001)))
        return rsi,ema9,ema21,closes[-1],(closes[-1]-closes[-2])/closes[-2]*100
    except: return None,None,None,None,None

def get_variation_5min(symbol, price_now):
    old = price_history.get(symbol)
    if not old:
        price_history[symbol] = {"price": price_now, "time": time.time()}
        return 999
    if time.time() - old["time"] >= 300:
        var = (price_now - old["price"])/old["price"]*100
        price_history[symbol] = {"price": price_now, "time": time.time()}
        return var
    return 999

def peut_trader(bal, usdt_demande, price, symbol):
    if bal is None: return False, "Solde non lu", 0
    min_garde = CONFIG["principal"] * CONFIG["principal_securite"] # 3.10$
    if bal < min_garde: return False, f"⛔ SOLDE {bal:.2f}$ < GARDE 30% {min_garde:.2f}$ BLOQUÉ", 0
    if usdt_demande > bal: return False, f"⛔ ACHAT {usdt_demande:.2f}$ > SOLDE {bal:.2f}$", 0
    reste = bal - usdt_demande
    if reste < min_garde:
        max_possible = bal - min_garde
        if max_possible < 1.0:
            return False, f"⛔ Reste {reste:.2f}$ < garde 30% {min_garde:.2f}$ BLOQUÉ", 0
        else:
            return True, f"⚠️ Achat réduit pour protéger 30%", max_possible
    if not price or price<=0: return False, f"⛔ Prix {symbol} invalide", 0
    if usdt_demande < 1.0: return False, f"⛔ Montant {usdt_demande:.2f}$ < 1$ MIN BYBIT", 0
    if usdt_demande/price < 0.000001: return False, "Qty trop petite", 0
    return True, "OK", usdt_demande

def choisir_meilleur_crypto():
    candidats = []
    for sym in AUTO_COINS:
        rsi,ema9,ema21,price,chg = get_signal(sym)
        if not rsi or not price: continue
        var5 = get_variation_5min(sym, price)
        if var5==999: continue
        if -1.0 <= var5 <= 1.0 and rsi < 40 and sym not in positions:
            score = 100 - abs(var5) - rsi*0.1
            candidats.append((rsi, sym, price, var5, score))
    if not candidats: return None
    candidats.sort(key=lambda x: x[4], reverse=True)
    return candidats[0]

def withdraw_to_externe(nom, montant):
    if montant<1.1: CONFIG["memoire"][nom]+=montant; return
    try:
        session.withdraw(coin="USDT",chain="TRC20",address=WALLET_EPARGNE_EXTERNE,amount=str(round(montant,2)),forceChain=1)
        send_tg(f"💸 {montant:.2f}$ -> {nom.upper()} -> {WALLET_EPARGNE_EXTERNE[:6]}...")
    except Exception as e:
        CONFIG["memoire"][nom]+=montant
        send_tg(f"⚠️ {nom} memoire {e}")

def repartition_dimanche():
    total=CONFIG["coffre_total"]
    if total<0.5: return
    rep=CONFIG["repartition"]; aTrading=total*rep["trading"]/100; aUrg=total*rep["urgences"]/100
    aSweep=total-aTrading-aUrg
    CONFIG["principal"]+=aTrading; CONFIG["urgences_lock"]+=aUrg
    div=100-rep["trading"]-rep["urgences"]
    msg=f"📊 REPART {total:.2f}$ TRADING +{aTrading:.2f}$ URGENCE LOCK +{aUrg:.2f}$\n"
    for k in ["business","maison","enfants"]:
        v=aSweep*rep[k]/div
        withdraw_to_externe(k,v); msg+=f"{k.upper()} +{v:.2f}$\n"
    CONFIG["coffre_total"]=0; send_tg(msg)

def trading_loop():
    time.sleep(5); load()
    bal=get_real_balance()
    if bal is not None:
        send_tg(f"🥷 V18.6 GARDE-FOU 30% LIVE!\nSolde:{bal:.4f}$ Principal:{CONFIG['principal']:.2f}$ Garde 30%:{CONFIG['principal']*0.30:.2f}$\nDispo trading: {bal - CONFIG['principal']*0.30:.2f}$\nRange ≤1≥ -1%/+1% ✅")
    while True:
        try:
            now=datetime.utcnow()
            if now.weekday()==6 and now.hour==18 and now.minute<5:
                repartition_dimanche()
            if not session: time.sleep(60); continue
            for sym in list(positions.keys()):
                rsi,ema9,ema21,price,chg = get_signal(sym)
                if not price: continue
                p=positions[sym]; profit=(price-p["avg"])/p["avg"]*100
                if profit<=0: continue
                ordre=None
                if profit>0 and profit<0.8: ordre={"pct":30, "txt":f"💰 MOLO 1/3 {sym} +{profit:.2f}%"}
                elif profit>=1.5 and p.get("step",0)==1: ordre={"pct":30, "txt":f"💰 MOLO 2/3 {sym} +{profit:.2f}%"}
                elif profit>=2.5: ordre={"pct":100, "txt":f"💎 SORTIE {sym} +{profit:.2f}%"}
                if ordre:
                    try:
                        qty_sell=round(p["qty"]*ordre["pct"]/100,6)
                        session.place_order(category="spot",symbol=sym,side="Sell",orderType="Market",qty=str(qty_sell))
                        send_tg(f"{ordre['txt']}\nVente RÉELLE {sym} @ {price}")
                        if ordre["pct"]==100: del positions[sym]
                        else: p["qty"]*=(1-ordre["pct"]/100); p["step"]=p.get("step",0)+1
                        save()
                    except Exception as e: send_tg(f"❌ Vente {sym} {e}")
            if len(positions)<2:
                choix = choisir_meilleur_crypto()
                if choix:
                    rsi, sym, price, var5, score = choix
                    bal = get_real_balance()
                    usdt_voulu = 1.10
                    ok, raison, usdt_final = peut_trader(bal, usdt_voulu, price, sym)
                    print(f"CHECK ≤1≥ {sym} RSI {rsi:.1f} var5 {var5:.2f}% Bal {bal:.2f}$ -> {raison}")
                    if ok:
                        qty = round(usdt_final/price,6)
                        if qty*price < 1.0: qty = round(1.05/price,6)
                        try:
                            session.place_order(category="spot",symbol=sym,side="Buy",orderType="Market",qty=str(qty))
                            positions[sym]={"qty":qty,"avg":price,"peak":0,"step":0}
                            save()
                            reste = bal - usdt_final
                            send_tg(f"🤫 [KITTRA ACHAT ≤1≥ 30% GARDE] {sym}\nRSI {rsi:.1f} var5 {var5:.2f}% Score {score:.1f}\nPrix {price} Montant {usdt_final:.2f}$\nSolde {bal:.2f}$ -> {reste:.2f}$ garde 30% {CONFIG['principal']*0.30:.2f}$ OK")
                        except Exception as e:
                            send_tg(f"❌ Achat {sym} {e}\nQty {qty} Valeur {qty*price:.2f}$")
            time.sleep(60)
        except Exception as e:
            print(f"LOOP {e}"); time.sleep(60)

def anti_sleep():
    while True:
        time.sleep(600)
        try: requests.get(f"{RENDER_URL}/ping", timeout=10)
        except: pass

@app.route("/")
def home():
    bal=get_real_balance()
    txt=f"{bal:.4f} USDT" if bal is not None else "Clés non lues"
    min_garde=CONFIG["principal"]*CONFIG["principal_securite"]
    return f"<h1>V18.6 GARDE-FOU 30% REAL</h1><h2>{txt} | Principal {CONFIG['principal']:.2f}$ | Garde 30% {min_garde:.2f}$ | Dispo {bal-min_garde:.2f}$ si bal</h2><p>Positions: {list(positions.keys())}<br>Scan: {', '.join(AUTO_COINS)}</p>"

@app.route("/ping")
def ping():
    bal=get_real_balance()
    ok,raison,final = peut_trader(bal, 1.10, 100, "TEST") if bal else (False,"no bal",0)
    return jsonify({"v":"18.6-garde-30","balance":bal,"principal":CONFIG["principal"],"garde_30":CONFIG["principal"]*0.30,"dispo":bal-CONFIG["principal"]*0.30 if bal else 0,"peut_trader":ok,"raison":raison,"final_amount":final,"positions":list(positions.keys())})

threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=anti_sleep, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
