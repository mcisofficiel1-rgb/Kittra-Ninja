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
positions={}
price_history={}
KITTRA_FILE="Kittra.json"

def load():
    global positions, CONFIG
    try:
        with open(KITTRA_FILE,"r") as f:
            d=json.load(f)
            positions=d.get("positions",{})
            CONFIG["stats"]=d.get("stats",CONFIG["stats"])
            CONFIG["coffre_total"]=d.get("coffre",0)
            CONFIG["wallet_perso"]=d.get("wallet_perso",{"bonus":0})
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
            prices=[pr for _,pr in price_history[symbol]]
            avg=sum(prices)/len(prices)
            if prices[-1] < avg*0.995: score+=30
        if score >= seuil: return f"BUY_DIP_{seuil}"
        if var5 > 3.0: return "SELL_PUMP"
        return "NEUTRAL"
    except: return "NEUTRAL"

def is_insufficient_error(res):
    txt=str(res).lower()
    return any(x in txt for x in ["insufficient","not enough","110007","170007","ab not enough","balance"])

def try_buy_safe(s, usdt):
    try:
        if s in positions: return False, "skip"
        bal=get_real_balance()
        if not bal or bal < 1.1: return False, "skip"
        if usdt < 1.1: return False, "skip"
        res=session.place_order(category="spot", symbol=s, side="Buy", orderType="Market", qty=str(round(usdt,2)), marketUnit="quoteCoin")
        if isinstance(res, dict) and res.get('retCode')!=0:
            msg=res.get('retMsg','')
            if is_insufficient_error(res) or is_insufficient_error(msg):
                print(f"SOLDE INSUFFISANT {s}")
                return False, f"SOLDE_INSUFFISANT_{s}"
            return False, msg
        return True, res
    except Exception as e:
        if is_insufficient_error(e): return False, "SOLDE_INSUFFISANT_EXCEPTION"
        return False, str(e)

def sell_v19_3(s, qty):
    try: return session.place_order(category="spot", symbol=s, side="Sell", orderType="Market", qty=str(qty))
    except Exception as e: print(f"SELL {e}"); return None

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
        if sell_v19_3(symbol, qty_real):
            CONFIG["stats"]["win"]+=1; CONFIG["stats"]["profit_total"]+= (price-entry)*qty_real
            send_tg(f"JACKPOT +10% {symbol}"); del positions[symbol]; save(); return
    if gain >= 6.0 and not pos.get('mega_60'):
        if sell_v19_3(symbol, qty_real*0.99):
            pos['mega_60']=True; pos['mega_50']=True; pos['mega_40']=True; pos['ninja_30']=True; pos['molo_20']=True; pos['molo_10']=True; pos['molo_05']=True; save(); send_tg(f"+6% {symbol}"); return
    if gain >= 1.0 and not pos.get('molo_10'):
        if sell_v19_3(symbol, qty_real*0.3):
            pos['molo_10']=True; pos['molo_05']=True; save(); send_tg(f"+1% {symbol} Gain {gain:.2f}%"); return
    if gain >= 0.5 and not pos.get('molo_05'):
        if sell_v19_3(symbol, qty_real*0.3):
            pos['molo_05']=True; save(); send_tg(f"+0.5% {symbol} Gain {gain:.2f}%"); return

def trading_loop():
    time.sleep(5); load()
    bal=get_real_balance()
    if bal: send_tg(f"KITTRA V21 SAFE-RETURN LIVE! Solde:{bal:.2f}$")
    while True:
        try:
            bal=get_real_balance()
            if not bal: time.sleep(45); continue
            capital_total=bal+CONFIG["coffre_total"]
            seuil=get_seuil_intelligence_adaptatif(capital_total)
            # FIX PRIX BNB REEL
            bnb_qty=get_qty_coin("BNBUSDT")
            if bnb_qty>0.001:
                prix_reel=get_price("BNBUSDT") or 774.0
                if "BNBUSDT" not in positions or positions["BNBUSDT"].get("entry_price",0) < 100:
                    positions["BNBUSDT"]={"entry_price":prix_reel,"qty":bnb_qty,"molo_05":False,"molo_10":False,"molo_20":False,"ninja_30":False,"mega_40":False,"mega_50":False,"mega_60":False}
                    save(); send_tg(f"SYNC BNB CORRIGE {bnb_qty} a {prix_reel}$")
            for sym in list(positions.keys()):
                pr=get_price(sym)
                if pr: check_and_sell_MOLO_NINJA(sym, pr)
            # ACHAT SAFE
            coins=["BNBUSDT"] if capital_total < 20 else ["BNBUSDT","SOLUSDT"]
            for sym in coins:
                if sym in positions: continue
                sig=get_signal_intelligent_60(sym, seuil)
                if "BUY_DIP" in sig:
                    ok, reason=try_buy_safe(sym, 5)
                    if ok:
                        p=get_price(sym)
                        positions[sym]={"entry_price":p,"qty":5/p,"molo_05":False,"molo_10":False,"molo_20":False,"ninja_30":False,"mega_40":False,"mega_50":False,"mega_60":False}
                        save(); send_tg(f"ACHAT {sym} a {p}$"); break
                    if "SOLDE_INSUFFISANT" in reason:
                        print("Solde insuffisant -> continue trading existant"); break
            time.sleep(45)
        except Exception as e: print(f"LOOP {e}"); time.sleep(60)

def anti_sleep():
    while True:
        time.sleep(600)
        try: requests.get(f"{RENDER_URL}/ping", timeout=10)
        except: pass

@app.route("/")
def home():
    bal=get_real_balance()
    return f"<h1>V21 OK</h1><h2>Solde:{bal} Pos:{list(positions.keys())} Coffre:{CONFIG['coffre_total']}</h2>"

@app.route("/ping")
def ping():
    return jsonify({"v":"21","bal":get_real_balance(),"pos":list(positions.keys())})

threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=anti_sleep, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
