import os, threading, time, requests
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

# --- V17.8 AUTO-DETECT AMELIORE - LIT TOUT (ton ancien qui marchait) ---
def get_env(*names):
    for n in names:
        v = os.getenv(n)
        if v:
            print(f"ENV trouvé: {n} = OK")
            return v
    return None

# Bybit - essaie TOUS les noms
API_KEY = get_env("API_KEY","BYBIT_API_KEY","BYBIT_KEY","BYBIT_API","APIKEY","ApiKey")
API_SECRET = get_env("API_SECRET","BYBIT_API_SECRET","BYBIT_SECRET","BYBIT_API_SEC","APISECRET","ApiSecret")
# Telegram - essaie TOUS les noms
BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN","TG_TOKEN","BOT_TOKEN","TELEGRAM_TOKEN","TG_BOT_TOKEN")
CHAT_ID = get_env("TELEGRAM_CHAT_ID","TG_ID","CHAT_ID","TELEGRAM_ID","TG_CHAT_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL","https://kittra-ninja-ultime.onrender.com")

# --- V18.2.1 - 2 WALLETS NOTES + RENDER ---
WALLET_TRADING_INTERNE = get_env("WALLET_TRADING_INTERNE","BYBIT_UNIFIED","TRADING_WALLET") or "BYBIT_UNIFIED"
WALLET_EPARGNE_EXTERNE = get_env("WALLET_EPARGNE_EXTERNE","WALLET_EXTERNE","EXTERNE_WALLET") or "TG8UcJUH152YyWsSArL4cwwV78GZiYJoqG"

print("=== KITTRA V18.2.1 FUSION V17.8+V18.2 ===")
print(f"FINAL API_KEY: {'TROUVÉ ✅' if API_KEY else 'MANQUANT ❌'}")
print(f"FINAL API_SECRET: {'TROUVÉ ✅' if API_SECRET else 'MANQUANT ❌'}")
print(f"FINAL BOT_TOKEN: {'TROUVÉ ✅' if BOT_TOKEN else 'MANQUANT ❌'}")
print(f"FINAL CHAT_ID: {'TROUVÉ ✅' if CHAT_ID else 'MANQUANT ❌'}")
print(f"INTERNE: {WALLET_TRADING_INTERNE} | EXTERNE: {WALLET_EPARGNE_EXTERNE}")

# Session Bybit sécurisée
session = None
if API_KEY and API_SECRET:
    try:
        session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)
        print(">>> Bybit Session CRÉÉE avec succès ✅")
    except Exception as e:
        print(f">>> Erreur session: {e}")
else:
    print(">>> PAS DE SESSION - Mets les 2 clés Bybit dans Environment Render")

CONFIG = {
 "principal":10.3443,
 "coffre_total":0,
 "urgences_lock":0,
 "wallet_perso":{"USDT":0,"TRX":0,"last_withdraw":datetime.utcnow()-timedelta(days=31)},
 "memoire":{"business":0,"maison":0,"enfants":0},
 "repartition":{"trading":40,"urgences":24,"business":12,"maison":8,"enfants":4}
}
SYMBOLS = ["BTCUSDT","SOLUSDT","ETHUSDT","TRXUSDT"]
state = {"loss_streak":0,"win_streak":0,"paused_until":0}

def send_tg(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_real_balance():
    if not session: return None
    try:
        resp = session.get_wallet_balance(accountType="UNIFIED")
        coins = resp['result']['list'][0]['coin']
        for c in coins:
            if c['coin']=='USDT': return float(c['walletBalance'])
        return float(coins[0]['walletBalance']) if coins else 0.0
    except Exception as e:
        print(f"BYBIT ERROR: {e}")
        return None

def get_signal(symbol):
    if not session: return None,None,None,None,None
    try:
        klines = session.get_kline(category="spot",symbol=symbol,interval="15",limit=30)['result']['list']
        closes = [float(k[4]) for k in reversed(klines)]
        if len(closes)<21: return None,None,None,None,None
        ema9 = sum(closes[-9:])/9
        ema21 = sum(closes[-21:])/21
        gains = [max(0, closes[i]-closes[i-1]) for i in range(1,15)]
        losses = [max(0, closes[i-1]-closes[i]) for i in range(1,15)]
        avg_g = sum(gains)/14
        avg_l = sum(losses)/14+0.00001
        rs = avg_g/avg_l
        rsi = 100-(100/(1+rs))
        price = closes[-1]
        change = (closes[-1]-closes[-2])/closes[-2]*100
        return rsi,ema9,ema21,price,change
    except: return None,None,None,None,None

def withdraw_to_externe(nom, montant):
    if montant < 1.1:
        CONFIG["memoire"][nom]+=montant
        print(f"{nom} {montant}$ <1.1 memoire")
        return
    try:
        session.withdraw(coin="USDT",chain="TRC20",address=WALLET_EPARGNE_EXTERNE,amount=str(round(montant,2)),forceChain=1)
        send_tg(f"💸 *{montant:.2f} USDT* -> {nom.upper()} vers `{WALLET_EPARGNE_EXTERNE[:6]}...{WALLET_EPARGNE_EXTERNE[-4:]}`")
    except Exception as e:
        CONFIG["memoire"][nom]+=montant
        send_tg(f"⚠️ Echec {nom} {montant:.2f}$ memoire: {e}")

def repartition_dimanche():
    total = CONFIG["coffre_total"]
    if total < 0.5: return
    rep = CONFIG["repartition"]
    aTrading = total*rep["trading"]/100
    aUrg = total*rep["urgences"]/100
    aSweep = total-aTrading-aUrg
    CONFIG["principal"]+=aTrading
    CONFIG["urgences_lock"]+=aUrg
    div = 100-rep["trading"]-rep["urgences"]
    parts = {"business":aSweep*rep["business"]/div,"maison":aSweep*rep["maison"]/div,"enfants":aSweep*rep["enfants"]/div}
    msg = f"📊 *REPARTITION DIMANCHE 18H*\nTotal: {total:.2f}$\n✅ TRADING +{aTrading:.2f}$\n🔒 URGENCE LOCK +{aUrg:.2f}$ TOTAL {CONFIG['urgences_lock']:.2f}$\n"
    for k,v in parts.items():
        withdraw_to_externe(k,v)
        msg+=f"{k.upper()} +{v:.2f}$ -> externe\n"
    CONFIG["coffre_total"]=0
    send_tg(msg)

def trading_loop():
    time.sleep(5)
    bal = get_real_balance()
    if session and bal is not None:
        send_tg(f"🥷 *V18.2.1 FUSION LIVE!*\nSolde Réel: {bal:.4f} USDT\nInterne: {WALLET_TRADING_INTERNE}\nExterne: `{WALLET_EPARGNE_EXTERNE}`\nMode +3%/+4.5%/+6% auto")
    else:
        print("Trading loop en attente clés...")
    while True:
        try:
            now = datetime.utcnow()
            if now.weekday()==6 and now.hour==18 and now.minute<5:
                repartition_dimanche()
            if now.day==1 and now.hour==18 and now.minute<6:
                send_tg(f"🔓 *RETRAIT MENSUEL DEBLOQUE!* Tape /retrait_mensuel")
            if not session:
                time.sleep(60); continue
            best=None; best_rsi=100
            for sym in SYMBOLS:
                rsi,ema9,ema21,price,chg = get_signal(sym)
                if rsi and ema9 and ema21 and rsi<35 and ema9>ema21 and rsi<best_rsi:
                    best_rsi=rsi; best=(sym,rsi,ema21,price,chg)
            if best and time.time()>state["paused_until"]:
                sym,rsi,ema21,price,chg = best
                bal = get_real_balance()
                if bal and bal>1:
                    usdt_trade = bal*0.25
                    qty = round(usdt_trade/price,6)
                    try:
                        session.place_order(category="spot",symbol=sym,side="Buy",orderType="Market",qty=str(qty))
                        send_tg(f"🤖 *ACHAT* {sym} RSI {rsi:.1f} {usdt_trade:.2f}$ @ {price} TP +3/+4.5/+6%")
                    except Exception as e:
                        send_tg(f"❌ Echec achat {sym} {e}")
            time.sleep(60)
        except Exception as e:
            print(f"LOOP ERROR {e}"); time.sleep(60)

def anti_sleep_loop():
    while True:
        time.sleep(600)
        try: requests.get(f"{RENDER_URL}/ping", timeout=10)
        except: pass

@app.route("/")
def home():
    bal = get_real_balance()
    txt = f"{bal:.4f} USDT (RÉEL)" if bal is not None else "Clés Bybit non lues - vérifie Render ENV"
    return f"<h1>🥷 KITTRA V18.2.1 FUSION LIVE</h1><h2>{txt}</h2><p>Interne:{WALLET_TRADING_INTERNE}</p><p>Externe:{WALLET_EPARGNE_EXTERNE}</p><p>Bybit OK: {bool(session)} | TG OK: {bool(BOT_TOKEN)}</p>"

@app.route("/ping")
def ping():
    return jsonify({
        "status":"✅ LIVE V18.2.1 FUSION",
        "real_balance":get_real_balance(),
        "interne":WALLET_TRADING_INTERNE,
        "externe":WALLET_EPARGNE_EXTERNE,
        "keys_detected":{"bybit_key":bool(API_KEY),"bybit_secret":bool(API_SECRET),"tg_token":bool(BOT_TOKEN),"tg_id":bool(CHAT_ID)},
        "coffre":CONFIG["coffre_total"],
        "urgence_lock":CONFIG["urgences_lock"],
        "is_real":True
    })

threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=anti_sleep_loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
