import os, threading, time, requests, json
from datetime import datetime
from flask import Flask, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

def get_env(*n):
    for x in n:
        v=os.getenv(x)
        if v: return v
    return None

API_KEY=get_env("API_KEY","BYBIT_API_KEY")
API_SECRET=get_env("API_SECRET","BYBIT_API_SECRET")
BOT_TOKEN=get_env("TELEGRAM_BOT_TOKEN","TG_TOKEN")
CHAT_ID=get_env("TELEGRAM_CHAT_ID","TG_ID")
RENDER_URL=os.getenv("RENDER_EXTERNAL_URL","https://kittra-ninja-ultime.onrender.com")
WALLET_EXTERNE="TG8UcJUH152YyWsSArL4cwwV78GZiYJoqG"

session=HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET) if API_KEY else None

CONFIG={"principal":10.3443,"principal_securite":0.30,"coffre_total":0.0,"wallet_perso":{"bonus":0.0},"stats":{"trades":0,"win":0,"profit_total":0.0},"capital_base":10.0,"seuil_securite":11.0}
positions={}; price_history={}; KITTRA_FILE="Kittra.json"

def load():
    global positions, CONFIG
    try:
        with open(KITTRA_FILE,"r") as f:
            d=json.load(f); positions=d.get("positions",{}); CONFIG["stats"]=d.get("stats",CONFIG["stats"]); CONFIG["coffre_total"]=d.get("coffre",0); CONFIG["wallet_perso"]=d.get("wallet_perso",{"bonus":0})
    except: pass

def save():
    with open(KITTRA_FILE,"w") as f:
        json.dump({"positions":positions,"stats":CONFIG["stats"],"coffre":CONFIG["coffre_total"],"wallet_perso":CONFIG["wallet_perso"]}, f)

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHAT_ID,"text":m}, timeout=10)
    except: pass

def get_real_balance():
    try:
        coins=session.get_wallet_balance(accountType="UNIFIED")['result']['list'][0]['coin']
        for c in coins:
            if c['coin']=='USDT': return float(c['walletBalance'])
    except: return None
    return None

def transfer_to_fund(amount):
    try:
        session.create_internal_transfer(coin="USDT", amount=str(round(amount,4)), fromAccountType="UNIFIED", toAccountType="FUND")
        return True
    except Exception as e:
        print(f"TRANSFER FAIL {e}")
        try:
            session.asset_transfer(coin="USDT", amount=str(round(amount,4)), fromAccountType="UNIFIED", toAccountType="FUND")
            return True
        except Exception as e2:
            print(f"TRANSFER FAIL2 {e2}"); return False

def check_and_secure_base():
    bal=get_real_balance()
    if not bal: return False
    base=CONFIG.get("capital_base",10.0); seuil=CONFIG.get("seuil_securite",11.0)
    if bal >= seuil:
        a_securiser=bal-base
        if a_securiser >= 0.5:
            if transfer_to_fund(a_securiser):
                CONFIG["coffre_total"]+=a_securiser; save()
                send_tg(f"🔒 COFFRE AUTO SÉCURISÉ! +{a_securiser:.2f}$ -> FUND\n💰 Retour base {base}$\n🏦 Coffre total: {CONFIG['coffre_total']:.2f}$")
                return True
    return False

def get_price(s):
    try: return float(session.get_tickers(category="spot", symbol=s)['result']['list'][0]['lastPrice'])
    except: return None

def get_qty_coin(s):
    try:
        coins=session.get_wallet_balance(accountType="UNIFIED")['result']['list'][0]['coin']
        cn=s.replace("USDT","")
        for c in coins:
            if c['coin']==cn: return float(c['walletBalance'])
        return 0.0
    except: return 0.0

def get_variation_5min(symbol):
    try:
        p=get_price(symbol)
        if not p: return 0
        now=time.time()
        if symbol not in price_history: price_history[symbol]=[]
        price_history[symbol].append((now,p))
        price_history[symbol]=[(t,pr) for t,pr in price_history[symbol] if now-t<=600]
        if len(price_history[symbol])<2: return 0
        return (p-price_history[symbol][0][1])/price_history[symbol][0][1]*100
    except: return 0

def get_seuil_intelligence_adaptatif(capital):
    if capital < 20: return 50
    elif capital < 100: return 60
    else: return 70

def get_signal_intelligent_60(symbol, seuil):
    try:
        var5=get_variation_5min(symbol); score=0
        if var5 < -2.0: score+=40
        elif var5 < -1.5: score+=30
        elif var5 < -0.8: score+=15
        if symbol in price_history and len(price_history[symbol])>=3:
            prices=[pr for _,pr in price_history[symbol]]; avg=sum(prices)/len(prices)
            if prices[-1] < avg*0.995: score+=30
        if symbol in price_history and len(price_history[symbol])>=4:
            prices=[pr for _,pr in price_history[symbol]]
            if prices[-1] > prices[-2] and prices[-2] < prices[-3]: score+=30
        if score >= seuil: return f"BUY_DIP_{seuil}"
        if var5 > 3.0: return "SELL_PUMP"
        return "NEUTRAL"
    except: return "NEUTRAL"

def peut_trader(symbol, usdt):
    bal=get_real_balance()
    if not bal or bal < 1.1: return False
    if usdt < 1.1: return False
    if symbol in positions: return False
    return True

# === SYSTEME DE SECURITE QUE TU AS DEMANDE ===
def is_insufficient_error(res):
    txt = str(res).lower()
    return any(x in txt for x in ["insufficient", "not enough", "110007", "170007", "ab not enough", "balance"])

def try_buy_safe(s, usdt):
    """TON NOUVEAU SYSTEME: si achat rate -> retourne False et continue avec ce qu'il a"""
    try:
        if not peut_trader(s, usdt):
            return False, "skip"

        res = session.place_order(category="spot", symbol=s, side="Buy", orderType="Market", qty=str(round(usdt,2)), marketUnit="quoteCoin")

        # Bybit repond avec retCode
        if isinstance(res, dict):
            if res.get('retCode')!= 0:
                msg = res.get('retMsg','')
                if is_insufficient_error(res) or is_insufficient_error(msg):
                    print(f"⚠️ SOLDE INSUFFISANT pour {s} ({msg}) -> je continue avec mes positions actuelles {list(positions.keys())}")
                    return False, f"SOLDE_INSUFFISANT_{s}"
                else:
                    print(f"❌ Achat {s} échoué: {msg} -> je passe")
                    return False, msg

        # Succès
        print(f"✅ ACHAT OK {s} pour {usdt}$")
        return True, res

    except Exception as e:
        err = str(e)
        if is_insufficient_error(err):
            print(f"⚠️ EXCEPTION SOLDE INSUFFISANT {s}: {e} -> je continue à trader ce que je possède")
            return False, "SOLDE_INSUFFISANT_EXCEPTION"
        print(f"BUY EXCEPTION {s}: {e}")
        return False, err

def sell_v19_3(s, qty):
    try: return session.place_order(category="spot", symbol=s, side="Sell", orderType="Market", qty=str(qty))
    except Exception as e: print(f"SELL {e}"); return None

def continue_trading_existing():
    """Si achat rate, il trade ce qu'il a déjà"""
    if not positions:
        # Sync wallet si positions vides mais coins présents
        for sym in ["BNBUSDT","SOLUSDT","BTCUSDT","ETHUSDT","XRPUSDT"]:
            q = get_qty_coin(sym)
            if q > 0.0001:
                p = get_price(sym)
                if p:
                    positions[sym]={"entry_price":p,"qty":q,"molo_05":False,"molo_10":False,"molo_20":False,"ninja_30":False,"mega_40":False,"mega_50":False,"mega_60":False}
                    print(f"🔄 SYNC AUTO TROUVE {sym} qty {q}")
        save()

    # Lance vente autonome sur ce qu'il possède
    for sym in list(positions.keys()):
        price=get_price(sym)
        if price:
            check_and_sell_MOLO_NINJA(sym, price)

def get_auto_coins_by_capital(cap):
    if cap < 20: return ["BNBUSDT"]
    elif cap < 50: return ["BNBUSDT","SOLUSDT"]
    elif cap < 100: return ["BNBUSDT","SOLUSDT","BTCUSDT"]
    elif cap < 250: return ["BNBUSDT","SOLUSDT","BTCUSDT","XRPUSDT","DOGEUSDT"]
    else: return ["BNBUSDT","SOLUSDT","BTCUSDT","XRPUSDT","DOGEUSDT","TRXUSDT","ETHUSDT"]

def check_and_sell_MOLO_NINJA(symbol, price):
    pos=positions.get(symbol)
    if not pos: return
    entry=float(pos.get('entry_price',0))
    if entry==0: return
    gain=(price-entry)/entry*100
    qty_real=get_qty_coin(symbol)
    if qty_real < 0.0001:
        if symbol in positions: del positions[symbol]; save()
        return
    if gain >= 10.0 and not pos.get('mega_60'):
        vendu=qty_real
        if sell_v19_3(symbol, vendu):
            CONFIG["stats"]["win"]+=1; CONFIG["stats"]["profit_total"]+= (price-entry)*vendu; CONFIG["coffre_total"]+= price*vendu*0.5
            send_tg(f"💥 JACKPOT +10% {symbol}! Coffre {CONFIG['coffre_total']:.2f}$"); del positions[symbol]; save(); return
    if gain >= 6.0 and not pos.get('mega_60'):
        vendu=qty_real*0.99
        if sell_v19_3(symbol, vendu):
            CONFIG["wallet_perso"]["bonus"]+= price*vendu*0.5; pos['mega_60']=True; pos['mega_50']=True; pos['mega_40']=True; pos['ninja_30']=True; pos['molo_20']=True; pos['molo_10']=True; pos['molo_05']=True; save(); send_tg(f"🔥 +6% {symbol}"); return
    if gain >= 5.0 and not pos.get('mega_50'):
        vendu=qty_real*0.5
        if sell_v19_3(symbol, vendu):
            CONFIG["coffre_total"]+= price*vendu*0.5; pos['mega_50']=True; pos['mega_40']=True; pos['ninja_30']=True; pos['molo_20']=True; pos['molo_10']=True; pos['molo_05']=True; save(); send_tg(f"💎 +5% {symbol} Coffre {CONFIG['coffre_total']:.2f}$"); return
    if gain >= 4.0 and not pos.get('mega_40'):
        vendu=qty_real*0.4
        if sell_v19_3(symbol, vendu):
            CONFIG["coffre_total"]+= price*vendu*0.5; pos['mega_40']=True; pos['ninja_30']=True; pos['molo_20']=True; pos['molo_10']=True; pos['molo_05']=True; save(); send_tg(f"🚀 +4% {symbol} Coffre {CONFIG['coffre_total']:.2f}$"); return
    if gain >= 3.0 and not pos.get('ninja_30'):
        vendu=qty_real*0.3
        if sell_v19_3(symbol, vendu):
            CONFIG["coffre_total"]+= price*vendu*0.5; pos['ninja_30']=True; pos['molo_20']=True; pos['molo_10']=True; pos['molo_05']=True; save(); send_tg(f"🥷 +3% {symbol}"); return
    if gain >= 2.0 and not pos.get('molo_20'):
        vendu=qty_real*0.3
        if sell_v19_3(symbol, vendu):
            CONFIG["wallet_perso"]["bonus"]+= price*vendu*0.5; pos['molo_20']=True; pos['molo_10']=True; pos['molo_05']=True; save(); send_tg(f"🔥 +2% {symbol}"); return
    if gain >= 1.0 and not pos.get('molo_10'):
        vendu=qty_real*0.3
        if sell_v19_3(symbol, vendu):
            CONFIG["coffre_total"]+= price*vendu*0.5; pos['molo_10']=True; pos['molo_05']=True; save(); send_tg(f"💰 +1% {symbol} COFFRE {CONFIG['coffre_total']:.2f}$"); return
    if gain >= 0.5 and not pos.get('molo_05'):
        vendu=qty_real*0.3
        if sell_v19_3(symbol, vendu):
            pos['molo_05']=True; save(); send_tg(f"🐢 +0.5% {symbol} Gain {gain:.2f}%"); return

def trading_loop():
    time.sleep(5); load()
    bal=get_real_balance()
    if bal: send_tg(f"🧠 KITTRA V21 SAFE-RETURN LIVE! Solde:{bal:.2f}$ | Si achat rate -> continue avec {list(positions.keys())}")
    while True:
        try:
            bal=get_real_balance()
            if not bal: time.sleep(45); continue
            check_and_secure_base()
            capital_total=bal+CONFIG["coffre_total"]
            seuil=get_seuil_intelligence_adaptatif(capital_total)
            AUTO_COINS=get_auto_coins_by_capital(capital_total)

            bnb_qty=get_qty_coin("BNBUSDT")
            if bnb_qty>0.001 and "BNBUSDT" not in positions:
                positions["BNBUSDT"]={"entry_price":10.34,"qty":bnb_qty,"molo_05":False,"molo_10":False,"molo_20":False,"ninja_30":False,"mega_40":False,"mega_50":False,"mega_60":False}; save(); send_tg(f"🔄 SYNC BNB {bnb_qty}")

            # 1. TOUJOURS VENDRE D'ABORD ce qu'on a
            for sym in list(positions.keys()):
                price=get_price(sym)
                if price: check_and_sell_MOLO_NINJA(sym, price)

            # 2. ESSAYER D'ACHETER - avec filet de sécurité
            achat_rate_count = 0
            for sym in AUTO_COINS:
                if sym in positions: continue
                sig=get_signal_intelligent_60(sym, seuil)
                if "BUY_DIP" in sig:
                    success, reason = try_buy_safe(sym, 5)
                    if success:
                        p=get_price(sym)
                        positions[sym]={"entry_price":p,"qty":5/p,"molo_05":False,"molo_10":False,"molo_20":False,"ninja_30":False,"mega_40":False,"mega_50":False,"mega_60":False}
                        save(); send_tg(f"🛒 ACHAT Intel {seuil}% {sym} à {p}$")
                        break # un achat à la fois
                    else:
                        achat_rate_count += 1
                        # Si solde insuffisant, on ne bloque pas, on va trader l'existant
                        if "SOLDE_INSUFFISANT" in reason:
                            print("🔄 Solde insuffisant detecté -> je trade mes positions actuelles")
                            continue_trading_existing()
                            break

            # Si tous les achats ratent pour solde, on force le trading existant
            if achat_rate_count >= len(AUTO_COINS):
                continue_trading_existing()

            time.sleep(45)
        except Exception as e:
            print(f"LOOP {e}"); time.sleep(60)

def weekly_tasks():
    while True:
        now=datetime.now()
        if now.weekday()==0 and now.hour==8: send_tg(f"📅 LUNDI AUDIT | Pos:{list(positions.keys())} | Coffre:{CONFIG['coffre_total']:.2f}$")
        if now.weekday()==4 and now.hour==20 and CONFIG["coffre_total"]>=5: send_tg(f"🏦 COFFRE {CONFIG['coffre_total']:.2f}$ prêt -> {WALLET_EXTERNE}")
        if now.weekday()==6 and now.hour==20: send_tg(f"📊 RAPPORT HEBDO | Win:{CONFIG['stats']['win']} Profit:{CONFIG['stats']['profit_total']:.2f}$ Coffre:{CONFIG['coffre_total']:.2f}$")
        time.sleep(3600)

def anti_sleep():
    while True:
        time.sleep(600)
        try: requests.get(f"{RENDER_URL}/ping", timeout=10)
        except: pass

@app.route("/")
def home():
    bal=get_real_balance(); return f"<h1>V21 SAFE-RETURN OK</h1><h2>Solde:{bal} | Pos:{list(positions.keys())} | Coffre:{CONFIG['coffre_total']}$ | Base 10$</h2>"

@app.route("/ping")
def ping():
    return jsonify({"v":"21","bal":get_real_balance(),"pos":list(positions.keys()),"coffre":CONFIG["coffre_total"]})

threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=weekly_tasks, daemon=True).start()
threading.Thread(target=anti_sleep, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
