import os, json, time, hmac, hashlib, datetime, requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()
COFFRE_FILE = "coffre_tresor.json"

def load_coffre():
    if os.path.exists(COFFRE_FILE):
        return json.loads(open(COFFRE_FILE).read())
    return {"principal": 10.91, "coffre": 0.0}

def get_bybit_balance():
    key = os.getenv("BYBIT_API_KEY")
    secret = os.getenv("BYBIT_API_SECRET")
    if not key or not secret:
        return {"real": load_coffre()["principal"], "source": "JSON_FALLBACK", "error": "NO BYBIT KEYS"}
    try:
        ts = str(int(time.time()*1000))
        param = "accountType=UNIFIED"
        payload = ts + key + "5000" + param
        sign = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        headers = {"X-BAPI-API-KEY": key, "X-BAPI-SIGN": sign, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": "5000"}
        r = requests.get(f"https://api.bybit.com/v5/account/wallet-balance?{param}", headers=headers, timeout=10).json()
        bal = float(r['result']['list'][0]['totalEquity'])
        return {"real": bal, "source": "BYBIT", "totalEquity": bal}
    except Exception as e:
        return {"real": load_coffre()["principal"], "source": "FALLBACK", "error": str(e)[:100]}

def jour_type():
    d = datetime.datetime.now().day
    if d in [1,2,3,28,29,30]: return {"type": "FAVORABLE_ACHAT", "mise": 100, "raison": f"Jour {d} - BUY GIGA"}
    if d in [5,6,7,8,18,19,20,21,22,25,26,27]: return {"type": "FAVORABLE_VENTE", "mise": 100, "raison": f"Jour {d} - SELL GIGA"}
    return {"type": "ORDINAIRE", "mise": 30, "raison": f"Jour {d} - SCALP PRUDENT"}

@app.get("/", response_class=HTMLResponse)
def home():
    j = jour_type()
    b = get_bybit_balance()
    c = load_coffre()
    tg_ok = bool(os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN"))
    return f"""
<html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width'>
<style>body{{background:#000;color:#f00;text-align:center;font-family:monospace}}#eye{{width:140px;height:140px;margin:20px auto;background:radial-gradient(circle,#f00 20%,#000033 80%);border-radius:50%;box-shadow:0 0 40px red;}}button{{width:92%;padding:14px;margin:4px;background:#111;color:#f00;border:2px solid #f00;border-radius:10px}}#out{{background:#050000;border:2px solid red;padding:10px;margin:10px;color:#0f8;text-align:left;white-space:pre-wrap;min-height:200px;border-radius:10px}}</style>
</head><body><div id=eye></div><h1>KITTRA V26 BYBIT</h1>
<div>REEL: {b['real']}$ | JSON: {c['principal']}$ | {j['type']} | TG:{'OK' if tg_ok else 'NO'} | BYBIT:{b['source']}</div>
<button onclick="fetch('/etat').then(r=>r.json()).then(j=>out.innerText=JSON.stringify(j,null,2))">ETAT + BYBIT</button>
<button onclick="fetch('/scan-ninja').then(r=>r.json()).then(j=>out.innerText=JSON.stringify(j,null,2))">SCAN</button>
<button onclick="fetch('/test-telegram').then(r=>r.json()).then(j=>out.innerText=JSON.stringify(j,null,2))">TEST TG</button>
<div id=out>{j['raison']}<br>Capital: {b}</div></body></html>
"""

@app.get("/etat")
def etat():
    return {{"bybit": get_bybit_balance(), "coffre": load_coffre(), "jour": jour_type(), "tg": bool(os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN"))}}

@app.get("/scan-ninja")
def scan():
    j = jour_type()
    b = get_bybit_balance()
    mise = b['real'] * j['mise'] / 100
    return {{"capital_reel": b['real'], "source": b['source'], "type": j['type'], "mise": mise, "raison": j['raison']}}

@app.get("/test-telegram")
def test_tg():
    token = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TG_CHAT_ID") or os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat: return {{"error": "NO TG KEYS", "token": bool(token), "chat": bool(chat)}}
    b = get_bybit_balance()
    r = requests.post(f"https://api.telegram.org/bot{{token}}/sendMessage", json={{"chat_id": chat, "text": f"🧪 KITTRA V26 TEST Capital reel {{b['real']}}$ Source {{b['source']}}"}}, timeout=10).json()
    return {{"telegram": r, "bybit": b}}

@app.get("/ping")
def ping(): return {{"ok": True, "bybit_keys": bool(os.getenv("BYBIT_API_KEY")), "time": str(datetime.datetime.now())}}￼Enter
