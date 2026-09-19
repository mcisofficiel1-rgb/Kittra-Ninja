import os, threading, time, requests, json
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pybit.unified_trading import HTTP
app = Flask(__name__)

def get_env(*names):
    for n in names:
        v=os.getenv(n)
        if v: return v
    return None

API_KEY=get_env("API_KEY","BYBIT_API_KEY"); API_SECRET=get_env("API_SECRET","BYBIT_API_SECRET")
BOT_TOKEN=get_env("TELEGRAM_BOT_TOKEN","TG_TOKEN"); CHAT_ID=get_env("TELEGRAM_CHAT_ID","TG_ID")
RENDER_URL=os.getenv("RENDER_EXTERNAL_URL","https://kittra-ninja-ultime.onrender.com")
WALLET_EXTERNE="TG8UcJUH152YyWsSArL4cwwV78GZiYJoqG"

session=HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET) if API_KEY else None

CONFIG={"principal":10.3443,"principal_securite":0.30,"coffre_total":0,"urgences_lock":0,"wallet_perso":{"bonus":0},"memoire":{"business":0,"maison":0},"repartition":{"trading":40,"urgences":24,"business":12,"maison":8,"enfants":4},"stats":{}}
AUTO_COINS=["BTCUSDT","SOLUSDT","ETHUSDT","TRXUSDT","BNBUSDT","XRPUSDT","AVAXUSDT","DOGEUSDT"]
MIN_NOTIONAL={"BTCUSDT":5.0,"SOLUSDT":5.0,"ETHUSDT":5.0,"AVAXUSDT":5.0,"BNBUSDT":5.0,"XRPUSDT":1.0,"TRXUSDT":1.0,"DOGEUSDT":1.0}
price_history={}; positions={}; KITTRA_FILE="Kittra.json"

def load():
    global positions, CONFIG
    try:
        with open(KITTRA_FILE,"r") as f:
            d=json.load(f); positions=d.get("positions",{}); CONFIG["stats"]=d.get("stats",{})
    except: pass
def save():
    with open(KITTRA_FILE,"w") as f: json.dump({"positions":positions,"stats":CONFIG["stats"],"coffre":CONFIG["coffre_total"]}, f)
def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHAT_ID,"text":m}, timeout=10)
    except: pass
def get_real_balance():
    try:
        coins=session.get_wallet_balance(accountType="UNIFIED")['result']['list'][0]['coin']
        for c in coins:
            if c['coin']=='USDT': return float(c['walletBalance'])
    except: return None

def get_signal_intelligent(symbol):
    try:
        kl=session.get_kline(category="spot",symbol=symbol,interval="15",limit=50)['result']['list']
        closes=[float(k[4]) for k in reversed(kl)]
        gains=[max(0,closes[i]-closes[i-1]) for i in range(1,15)]; losses=[max(0,closes[i-1]-closes[i]) for i in range(1,15)]
        rs=(sum(gains)/14)/(sum(losses)/14+0.00001); rsi=100-(100/(1+rs))
        price=closes[-1]; chg15=(closes[-1]-closes[-2])/closes[-2]*100
        chg1h=(closes[-1]-closes[-4])/closes[-4]*100 if len(closes)>=4 else 0
        score=0
        if rsi<25: score+=40
        elif rsi<35: score+=30
        elif rsi<45: score+=15
        if -1.2 <= chg15 <= 0.2: score+=30
        if chg1h < -1: score+=15
        score+=min(CONFIG["stats"].get(symbol,0)*2,10)
        return {"rsi":rsi,"price":price,"chg15":chg15,"chg1h":chg1h,"score":score}
    except: return None

def get_variation_5min(sym, price_now):
    old=price_history.get(sym)
    if not old: price_history[sym]={"price":price_now,"time":time.time()}; return 999
    if time.time()-old["time"]>=300:
        var=(price_now-old["price"])/old["price"]*100; price_history[sym]={"price":price_now,"time":time.time()}; return var
    return 999

def peut_trader(bal, usdt, price, sym):
    min_garde=CONFIG["principal"]*CONFIG["principal_securite"]
    if bal is None: return False,"Solde non lu",0
    if bal < min_garde: return False,f"⛔ SOLDE {bal:.2f} < GARDE 30%",0
    if usdt > bal: return False,f"⛔ {usdt:.2f} > {bal:.2f}",0
    reste=bal-usdt
    if reste < min_garde:
        max_pos=bal-min_garde
        if max_pos < 1: return False,f"Reste {reste:.2f} < garde",0
        return True,"Réduit garde 30%",max_pos
    return True,"OK",usdt

def trading_loop():
    time.sleep(5); load()
    bal=get_real_balance()
    if bal: send_tg(f"🧠 V19.2 MOLO ACHAT<Vente LIVE!\nSolde:{bal:.4f}$ Garde:{CONFIG['principal']*0.30:.2f}$ Dispo:{bal-CONFIG['principal']*0.30:.2f}$\nVente +0.5 +1 +2 +3 + coffre +4 +5 +7 +10")
    while True:
        try:
            # ===== VENTES MOLO ACHAT < VENTE =====
            for sym in list(positions.keys()):
                data=get_signal_intelligent(sym)
                if not data: continue
                p=positions[sym]; profit=(data["price"]-p["avg"])/p["avg"]*100
                if profit > p.get("peak",0): p["peak"]=profit; save()
                ordre=None
                # MOLO - ACHAT<Vente +0.5 +1 +2 +3
                if profit>=0.5 and p.get("s05",0)==0: ordre={"pct":25,"txt":f"💰 MOLO +0.5% {sym}","key":"s05","coffre":False}
                elif profit>=1.0 and p.get("s1",0)==0: ordre={"pct":25,"txt":f"💰 MOLO +1% {sym}","key":"s1","coffre":False}
                elif profit>=2.0 and p.get("s2",0)==0: ordre={"pct":25,"txt":f"💰 MOLO +2% {sym}","key":"s2","coffre":False}
                elif profit>=3.0 and p.get("s3",0)==0: ordre={"pct":25,"txt":f"💰 MOLO +3% {sym}","key":"s3","coffre":False}
                # COFFRE AUTONOME +4 +5 +7 +10
                elif profit>=4.5 and p.get("c4",0)==0: ordre={"pct":20,"txt":f"🏦 COFFRE +4.5% BONUS {sym}","key":"c4","coffre":True}
                elif profit>=5.5 and p.get("c5",0)==0: ordre={"pct":30,"txt":f"🏦 COFFRE +5.5% BONUS {sym}","key":"c5","coffre":True}
                elif profit>=7.5 and p.get("c7",0)==0: ordre={"pct":30,"txt":f"💎 WALLET PERSO +7.5% {sym}","key":"c7","coffre":True}
                elif profit>=10: ordre={"pct":100,"txt":f"🚀 JACKPOT +{profit:.1f}% {sym}","key":"c10","coffre":True}
                # TRAILING
                elif profit>0 and profit < p.get("peak",0)-0.6 and p.get("peak",0)>=2: ordre={"pct":100,"txt":f"💎 TRAILING {sym} +{profit:.2f}% peak {p['peak']:.2f}%","key":"trail","coffre":False}

                if ordre:
                    try:
                        qty_sell=round(p["qty"]*ordre["pct"]/100,6)
                        session.place_order(category="spot",symbol=sym,side="Sell",orderType="Market",qty=str(qty_sell))
                        gain=qty_sell*(data["price"]-p["avg"])
                        if ordre["coffre"]:
                            CONFIG["coffre_total"]+=gain; CONFIG["wallet_perso"]["bonus"]+=gain*0.5
                            send_tg(f"{ordre['txt']}\nGain BONUS {gain:.4f}$ -> COFFRE {CONFIG['coffre_total']:.4f}$\nPrincipal gardé!")
                        else:
                            send_tg(f"{ordre['txt']} @ {data['price']:.4f} Profit {profit:.2f}%")
                        CONFIG["stats"][sym]=CONFIG["stats"].get(sym,0)+1
                        if ordre["pct"]==100: del positions[sym]
                        else: p["qty"]-=qty_sell; p[ordre["key"]]=1
                        save()
                    except Exception as e: send_tg(f"❌ Vente {sym} {e}")

            # ===== ACHAT INTELLIGENT =====
            if len(positions)<3:
                meilleurs=[]
                for sym in AUTO_COINS:
                    if sym in positions: continue
                    d=get_signal_intelligent(sym)
                    if not d: continue
                    var5=get_variation_5min(sym, d["price"])
                    if var5==999: continue
                    if -1.5 <= var5 <= 1.0 and d["rsi"] < 45 and d["score"]>=40:
                        d["var5"]=var5; d["symbol"]=sym; meilleurs.append(d)
                if meilleurs:
                    meilleurs.sort(key=lambda x: x["score"], reverse=True)
                    choix=meilleurs[0]; sym=choix["symbol"]; price=choix["price"]; score=choix["score"]
                    bal=get_real_balance()
                    min_req=MIN_NOTIONAL.get(sym,1.0)
                    if score>=75: usdt_voulu=5.50
                    elif min_req>=5: usdt_voulu=5.20
                    else: usdt_voulu=1.10
                    ok, raison, usdt_final=peut_trader(bal, usdt_voulu, price, sym)
                    if ok:
                        qty=round(usdt_final/price,6)
                        try:
                            session.place_order(category="spot",symbol=sym,side="Buy",orderType="Market",qty=str(qty))
                            positions[sym]={"qty":qty,"avg":price,"peak":0,"s05":0,"s1":0,"s2":0,"s3":0,"c4":0,"c5":0,"c7":0}
                            save()
                            send_tg(f"🧠 [ACHAT ≤{usdt_final:.2f}≥] {sym} Score {score}/100\nRSI {choix['rsi']:.1f} var5 {choix['var5']:.2f}% @ {price}")
                        except Exception as e:
                            if "170140" in str(e) and usdt_final<5:
                                try:
                                    ok2,r2,f2=peut_trader(bal,5.50,price,sym)
                                    if ok2:
                                        qty2=round(f2/price,6)
                                        session.place_order(category="spot",symbol=sym,side="Buy",orderType="Market",qty=str(qty2))
                                        positions[sym]={"qty":qty2,"avg":price,"peak":0,"s05":0,"s1":0,"s2":0,"s3":0,"c4":0,"c5":0,"c7":0}
                                        save()
                                        send_tg(f"🧠 [FALLBACK 5.50$] {sym} Score {score}")
                                except Exception as e2: send_tg(f"❌ {sym} fallback {e2}")
                            else: send_tg(f"❌ Achat {sym} {e}")

            # ===== HEBDO DIMANCHE 18H =====
            now=datetime.utcnow()
            if now.weekday()==6 and now.hour==18 and now.minute<2:
                bal=get_real_balance()
                if bal and bal>CONFIG["principal"]:
                    profit=bal-CONFIG["principal"]
                    send_tg(f"📅 HEBDO DIMANCHE 18H\nProfit {profit:.2f}$ -> Repart 40% trading 24% urg 12% business 8% maison 4% enfants + TRC20 {WALLET_EXTERNE}")
                    time.sleep(300)
            time.sleep(45)
        except Exception as e:
            print(f"LOOP {e}"); time.sleep(60)

def anti_sleep():
    while True:
        time.sleep(600)
        try: requests.get(f"{RENDER_URL}/ping", timeout=10)
        except: pass

@app.route("/")
def home():
    bal=get_real_balance(); txt=f"{bal:.4f} USDT" if bal else "No bal"
    return f"<h1>V19.2 MOLO 0.5 1 2 3 + COFFRE 4 5 7 10</h1><h2>{txt} Positions {list(positions.keys())} Coffre {CONFIG['coffre_total']:.2f}$</h2>"
@app.route("/ping")
def ping():
    return jsonify({"v":"19.2","bal":get_real_balance(),"pos":list(positions.keys()),"coffre":CONFIG["coffre_total"]})

threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=anti_sleep, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
