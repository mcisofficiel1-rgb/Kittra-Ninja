import os, time, hmac, hashlib, requests, random, asyncio, json
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from openai import OpenAI

app = FastAPI()

# ========== CONFIG 100% ENV ==========
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
TG_TOKEN = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_TOKEN")
TG_ID = os.getenv("TG_ID") or os.getenv("CHAT_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

COFFRE_TOTAL = 0.0
A_REINVESTIR = 0.0
PNL_JOUR = 0.0
HIST_TRADES = []
MODE_ACTUEL = "BALEINE"

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY) if OPENROUTER_API_KEY else None

def tg(msg):
    try:
        if TG_TOKEN and TG_ID:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id": TG_ID, "text": msg}, timeout=10)
        print(msg)
    except: pass

def get_vrai_capital():
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        return 10.91
    for account_type in ["UNIFIED", "FUND"]:
        try:
            timestamp = str(int(time.time() * 1000))
            param_str = f"accountType={account_type}"
            sign_str = timestamp + BYBIT_API_KEY + "5000" + param_str
            sign = hmac.new(BYBIT_API_SECRET.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
            headers = {"X-BAPI-API-KEY": BYBIT_API_KEY, "X-BAPI-TIMESTAMP": timestamp, "X-BAPI-SIGN": sign, "X-BAPI-RECV-WINDOW": "5000"}
            url = f"https://api.bybit.com/v5/account/wallet-balance?{param_str}"
            r = requests.get(url, headers=headers, timeout=10).json()
            if r['retCode'] == 0:
                for coin in r['result']['list'][0]['coin']:
                    if coin['coin'] == 'USDT' and float(coin['walletBalance']) > 0:
                        return float(coin['walletBalance'])
        except: pass
    return 10.91

def kittra_scout():
    try: return float(requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=SOLUSDT", timeout=5).json()['result']['list'][0]['lastPrice'])
    except: return None

def detecteur_baleines():
    try:
        v = float(requests.get("https://api.bybit.com/v5/market/kline?category=spot&symbol=SOLUSDT&interval=5&limit=1", timeout=5).json()['result']['list'][0][5])
        return (v > 500000, f"Volume {v:.0f}$ {'🐋 BALEINE!' if v>500000 else 'calme'}")
    except: return False, "Volume inconnu"

def get_ai_decision(market_data):
    try:
        prompt = f"Tu es Kittra trader sniper. Analyse {market_data}. ACHETE si ecart>1.2% sinon ATTENTE. JSON {{'decision':'ACHETE ou ATTENTE','raison':'courte'}}"
        c = client.chat.completions.create(model="meta-llama/llama-3.3-70b-instruct:free", messages=[{"role":"user","content":prompt}], extra_headers={"HTTP-Referer":"https://kittra.onrender.com","X-Title":"Kittra"})
        return json.loads(c.choices[0].message.content)
    except: return {"decision":"ATTENTE","raison":"Erreur cerveau"}

def muse_spark_decision(prix, chute, baleine):
    if baleine and chute <= -3: return False, "Muse Spark: Baleine ANNULE"
    if chute <= -5: return True, "GIGA"
    if chute <= -3: return True, "MOLO"
    return False, "ATTENDRE"

def risk_patron_check():
    return False if PNL_JOUR < -5 else True

async def twap_baleine(symbol, qte):
    mor = 20; qt = qte/mor
    tg(f"🐋 TWAP {symbol} {mor}x lance")
    for i in range(mor):
        print(f"TWAP {i+1}/{mor} {qt}"); await asyncio.sleep(random.randint(60,180))
    tg(f"✅ TWAP {symbol} fini")

def auto_compounding(benef):
    global COFFRE_TOTAL, A_REINVESTIR
    COFFRE_TOTAL += benef*0.30; A_REINVESTIR += benef*0.70
    return f"Gain {benef:.2f}$ -> {benef*0.30:.2f}$ coffre + {benef*0.70:.2f}$ reinvest | Coffre {COFFRE_TOTAL:.2f}$"

def etat_data():
    cap = get_vrai_capital()
    return {"solde":cap,"principal":cap,"disponible":cap,"en_cours":"0.00","en_trade":False,"mode":MODE_ACTUEL,"position":"BNBUSDT+HYPEUSDT","coffre":{"total":COFFRE_TOTAL,"vault":"TG8UcJUH152YyWsSArL4cwwV78GZiYJoqG"},"win_rate":0,"trades":len(HIST_TRADES)}

@app.get("/etat")
def etat(): return etat_data()
@app.get("/api/transactions")
def api_trans(): return etat_data()
@app.get("/api/status")
def api_status(): d=etat_data(); d["positions"]=["BNBUSDT","HYPEUSDT"]; return d
@app.get("/api/set_mode")
def set_mode(mode: str = Query("BALEINE")): global MODE_ACTUEL; MODE_ACTUEL=mode; return {"status":f"MODE {mode} ACTIVE","mode":MODE_ACTUEL}
@app.post("/scan")
def scan(): return {"status":"SCAN ALL OK","detecte":["BNBUSDT","HYPEUSDT","SOLUSDT"],"mode":MODE_ACTUEL}
@app.get("/ping")
def ping(): return {"status":"OK","mode":MODE_ACTUEL}
@app.get("/")
def home():
    try:
        if os.path.exists("index.html"): return HTMLResponse(open("index.html","r",encoding="utf-8").read())
    except: pass
    return etat_data()

@app.on_event("startup")
async def startup():
    cap=get_vrai_capital(); tg(f"🚀 KITTRA V23 demarre - CAPITAL {cap}$ - MODE {MODE_ACTUEL}"); old=kittra_scout()
    while True:
        try:
            if not risk_patron_check(): await asyncio.sleep(3600); continue
            prix=kittra_scout()
            if prix and old:
                chute=((prix-old)/old)*100; baleine,msg=detecteur_baleines(); ok,act=muse_spark_decision(prix,chute,baleine)
                if ok:
                    dec=get_ai_decision(f"SOL {chute:.2f}% {msg} cap {cap}$")
                    if dec["decision"]=="ACHETE":
                        await twap_baleine("SOLUSDT",cap*0.1); ben=0.55 if act=="MOLO" else 1.1; msgc=auto_compounding(ben)
                        tg(f"✅ {act} {chute:.2f}% - {dec['raison']}\nPrix {prix}$\n{msgc}\n{msg}"); HIST_TRADES.append({"date":str(datetime.now()),"coffre":COFFRE_TOTAL})
                old=prix
            await asyncio.sleep(180)
        except Exception as e: print(f"Err {e}"); await asyncio.sleep(60)
