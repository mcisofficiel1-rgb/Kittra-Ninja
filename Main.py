import os, threading, time, requests
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

# --- V17.8 AUTO-DETECT QUI MARCHAIT ---
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

print("=== KITTRA V18.2.2 GARDE-FOU + CHECK PRIX ===")
print(f"KEY:{bool(API_KEY)} SEC:{bool(API_SECRET)} TG:{bool(BOT_TOKEN)}")
print(f"INTERNE:{WALLET_TRADING_INTERNE} EXTERNE:{WALLET_EPARGNE_EXTERNE}")

session = None
if API_KEY and API_SECRET:
    try:
        session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)
        print(">>> Session Bybit OK ✅")
    except Exception as e:
        print(f">>> Erreur {e}")
else:
    print(">>> PAS DE SESSION")

CONFIG = {
 "principal":10.3443,
 "principal_securite":0.95, # 95% = 9.82$ minimum à garder
 "coffre_total":0,
 "urgences_lock":0,
 "wallet_perso":{"last_withdraw":datetime.utcnow()-timedelta(days=31)},
 "memoire":{"business":0,"maison":0,"enfants":0},
 "repartition":{"trading":40,"urgences":24,"business":12,"maison":8,"enfants":4}
}
SYMBOLS = ["BTCUSDT","SOLUSDT","ETHUSDT","TRXUSDT"]
state = {"paused_until":0}

def send_tg(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_real_balance():
    if not session: return None
    try:
        coins = session.get_wallet_balance(accountType="UNIFIED")['result']['list'][0]['coin']
        for c in coins:
            if c['coin']=='USDT': return float(c['walletBalance'])
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
        gains=[max(0,closes[i]-closes[i-1]) for i in range(1,15)]; losses=[max(0,closes[i-1]-closes[i]) for i in range(1,15)]
        rsi=100-(100/(1+(sum(gains)/14)/(sum(losses)/14+0.00001)))
        return rsi,ema9,ema21,closes[-1],(closes[-1]-closes[-2])/closes[-2]*100
    except: return None,None,None,None,None

def peut_trader(bal, usdt_demande, price, symbol):
    """CHECK INTELLIGENT: solde principal + prix crypto + montant achat"""
    if bal is None: return False, "Solde non lu", 0
    min_garde = CONFIG["principal"] * CONFIG["principal_securite"] # 9.82$

    # 1. Check solde principal
    if bal < min_garde:
        return False, f"⛔ SOLDE {bal:.2f}$ < PRINCIPAL PROTÉGÉ {min_garde:.2f}$ - BLOQUÉ", 0

    # 2. Check montant achat vs solde réel Bybit
    if usdt_demande > bal:
        return False, f"⛔ ACHAT {usdt_demande:.2f}$ > SOLDE {bal:.2f}$ - Impossible", 0

    # 3. Check si après achat il reste principal
    reste = bal - usdt_demande
    if reste < min_garde:
        # Réduit achat pour protéger principal
        max_possible = bal - min_garde
        if max_possible < 1:
            return False, f"⛔ Reste {reste:.2f}$ < {min_garde:.2f}$ garde principal - BLOQUÉ", 0
        else:
            return True, f"⚠️ Achat réduit pour protéger principal", max_possible

    # 4. Check prix crypto réel
    if not price or price <=0:
        return False, f"⛔ Prix {symbol} invalide", 0

    # 5. Check quantité minimum Bybit (1$ min)
    if usdt_demande < 1:
        return False, f"⛔ Montant {usdt_demande:.2f}$ < 1$ min Bybit", 0

    # 6. Ne trade que surplus si solde proche principal
    surplus = bal - CONFIG["principal"]
    if surplus > 0 and surplus < usdt_demande:
        usdt_safe = max(surplus * 0.5, 1.0)
        return True, f"⚠️ Surplus {surplus:.2f}$ seulement - trade réduit", usdt_safe

    return True, "OK", usdt_demande

def withdraw_to_externe(nom, montant):
    if montant<1.1: CONFIG["memoire"][nom]+=montant; return
    try:
        session.withdraw(coin="USDT",chain="TRC20",address=WALLET_EPARGNE_EXTERNE,amount=str(round(montant,2)),forceChain=1)
        send_tg(f"💸 {montant:.2f}$ -> {nom.upper()} -> {WALLET_EPARGNE_EXTERNE[:6]}...")
    except Exception as e:
        CONFIG["memoire"][nom]+=montant; send_tg(f"⚠️ {nom} memoire {e}")

def repartition_dimanche():
    total=CONFIG["coffre_total"]
    if total<0.5: return
    rep=CONFIG["repartition"]; aTrading=total*rep["trading"]/100; aUrg=total*rep["urgences"]/100; aSweep=total-aTrading-aUrg
    CONFIG["principal"]+=aTrading; CONFIG["urgences_lock"]+=aUrg
    div=100-rep["trading"]-rep["urgences"]
    parts={"business":aSweep*rep["business"]/div,"maison":aSweep*rep["maison"]/div,"enfants":aSweep*rep["enfants"]/div}
    msg=f"📊 REPART {total:.2f}$ TRADING +{aTrading:.2f}$ URGENCE LOCK +{aUrg:.2f}$\n"
    for k,v in parts.items(): withdraw_to_externe(k,v); msg+=f"{k.upper()} +{v:.2f}$\n"
    CONFIG["coffre_total"]=0; send_tg(msg)

def trading_loop():
    time.sleep(5); bal=get_real_balance()
    if bal is not None:
        send_tg(f"🥷 V18.2.2 INTELLIGENT LIVE!\nSolde:{bal:.4f}$ Principal:{CONFIG['principal']:.2f}$ Garde:{CONFIG['principal']*0.95:.2f}$\nCheck solde+prix avant chaque achat - plus de hasard")
    while True:
        try:
            now=datetime.utcnow()
            if now.weekday()==6 and now.hour==18 and now.minute<5: repartition_dimanche()
            if now.day==1 and now.hour==18 and now.minute<6: send_tg(f"🔓 RETRAIT MENSUEL DEBLOQUE!")
            if not session: time.sleep(60); continue

            # CHOIX MEILLEUR CRYPTO (pas hasard - RSI le plus bas)
            candidates=[]
            for sym in SYMBOLS:
                rsi,ema9,ema21,price,chg=get_signal(sym)
                if rsi and ema9 and ema21 and rsi<35 and ema9>ema21:
                    candidates.append((rsi,sym,price,ema9,ema21,chg))
            if not candidates:
                time.sleep(60); continue

            candidates.sort(key=lambda x: x[0]) # trie RSI le plus bas = meilleur
            rsi,sym,price,ema9,ema21,chg = candidates[0]

            # CHECK COMPLET AVANT ACHAT
            bal = get_real_balance()
            usdt_voulu = bal*0.25 if bal else 0

            ok, raison, usdt_final = peut_trader(bal, usdt_voulu, price, sym)

            print(f"CHECK {sym} Bal:{bal:.2f}$ Voulu:{usdt_voulu:.2f}$ Final:{usdt_final:.2f}$ Prix:{price} -> {raison}")

            if not ok:
                if now.minute==0: send_tg(raison)
                time.sleep(60); continue

            if "réduit" in raison:
                send_tg(f"{raison}\n{sym} RSI {rsi:.1f} Prix {price} - Achat ajusté {usdt_final:.2f}$")

            # DOUBLE CHECK juste avant ordre (prix peut changer)
            price_check = get_signal(sym)[3]
            if not price_check or abs(price_check-price)/price>0.02: # si prix bouge >2% annule
                send_tg(f"⛔ {sym} prix a bougé {price}->{price_check} - annulé anti-hazard")
                time.sleep(60); continue

            qty = round(usdt_final/price,6)
            if qty<=0: time.sleep(60); continue

            try:
                session.place_order(category="spot",symbol=sym,side="Buy",orderType="Market",qty=str(qty))
                reste = bal - usdt_final
                send_tg(f"🤖 ACHAT SÉCURISÉ ✅\n{sym} RSI {rsi:.1f} @ {price}\nMontant {usdt_final:.2f}$ Qty {qty}\nSolde avant {bal:.2f}$ -> après {reste:.2f}$ (garde {CONFIG['principal']*0.95:.2f}$)")
            except Exception as e:
                send_tg(f"❌ Echec {sym} {e}")

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
    bal=get_real_balance(); txt=f"{bal:.4f} USDT" if bal is not None else "Clés non lues"
    min_garde=CONFIG["principal"]*CONFIG["principal_securite"]
    return f"<h1>V18.2.2 CHECK SOLDE+PRIX LIVE</h1><h2>{txt} | Principal {CONFIG['principal']:.2f}$ | Garde {min_garde:.2f}$</h2><p>Interne:{WALLET_TRADING_INTERNE}<br>Externe:{WALLET_EPARGNE_EXTERNE}</p>"

@app.route("/ping")
def ping():
    bal=get_real_balance()
    ok,raison,final = peut_trader(bal, bal*0.25 if bal else 0, 100, "TEST") if bal else (False,"no bal",0)
    return jsonify({"v":"18.2.2-check","balance":bal,"principal":CONFIG["principal"],"min_garde":CONFIG["principal"]*0.95,"peut_trader":ok,"raison":raison,"final_amount":final,"interne":WALLET_TRADING_INTERNE,"externe":WALLET_EPARGNE_EXTERNE})

threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=anti_sleep, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
