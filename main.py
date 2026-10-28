from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os
import requests
import json
import datetime
import glob
import random
import time
import hmac
import hashlib

app = FastAPI()

def get_tg():
    token = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    chat = os.getenv("TG_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
    return token, chat

def load_file(f, d):
    try:
        if os.path.exists(f):
            return json.loads(open(f).read())
    except:
        pass
    return d

def save_file(f, d):
    open(f, "w").write(json.dumps(d))

def send_tg(m):
    try:
        tok, cid = get_tg()
        if not tok or not cid:
            return f"NO TG token={bool(tok)} chat={bool(cid)}"
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": m}, timeout=10)
        return f"OK {r.status_code}"
    except Exception as e:
        return str(e)

def get_bybit():
    key = os.getenv("BYBIT_API_KEY")
    sec = os.getenv("BYBIT_API_SECRET")
    if not key or not sec:
        return 10.91, "JSON"
    try:
        ts = str(int(time.time() * 1000))
        p = "accountType=UNIFIED"
        sign = hmac.new(sec.encode(), (ts + key + "5000" + p).encode(), hashlib.sha256).hexdigest()
        h = {"X-BAPI-API-KEY": key, "X-BAPI-SIGN": sign, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": "5000"}
        r = requests.get("https://api.bybit.com/v5/account/wallet-balance?" + p, headers=h, timeout=10).json()
        v = float(r["result"]["list"][0]["totalEquity"])
        return v, "BYBIT"
    except Exception as e:
        return 10.91, f"ERR {e}"[:60]

def analyse_jour():
    d = datetime.datetime.now().day
    if d in [1, 2, 3, 28, 29, 30]:
        return {"type": "FAVORABLE_ACHAT", "mise": 100, "raison": f"Jour {d} chute baleines BUY"}
    if d in [5, 6, 7, 8, 18, 19, 20, 21, 22, 25, 26, 27]:
        return {"type": "FAVORABLE_VENTE", "mise": 100, "raison": f"Jour {d} pic SELL"}
    return {"type": "ORDINAIRE", "mise": 30, "raison": f"Jour {d} calme 30%"}

@app.get("/", response_class=HTMLResponse)
def root():
    cap, src = get_bybit()
    j = analyse_jour()
    tok, cid = get_tg()
    html = f"""
    <html><body style='background:black;color:red;text-align:center;font-family:monospace;padding:20px'>
    <h1>KITTRA V26 LIVE</h1>
    <p>CAP {cap}$ SRC {src} | {j['type']} {j['mise']}%</p>
    <p>TG token={bool(tok)} chat={bool(cid)}</p>
    <p>{j['raison']}</p>
    <button onclick="fetch('/etat').then(r=>r.json()).then(j=>document.body.innerHTML='<pre>'+JSON.stringify(j,null,2)+'</pre>')" style='padding:15px;width:90%;background:#111;color:red;border:2px solid red;margin:5px'>ETAT</button><br>
    <button onclick="fetch('/test-telegram').then(r=>r.json()).then(j=>alert(JSON.stringify(j)))" style='padding:15px;width:90%;background:#111;color:red;border:2px solid red;margin:5px'>TEST TELEGRAM</button><br>
    <button onclick="fetch('/scan-ninja').then(r=>r.json()).then(j=>document.body.innerHTML='<pre>'+JSON.stringify(j,null,2)+'</pre>')" style='padding:15px;width:90%;background:#111;color:red;border:2px solid red;margin:5px'>SCAN NINJA</button>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/etat")
def etat():
    cap, src = get_bybit()
    j = analyse_jour()
    tok, cid = get_tg()
    return {
        "cap": cap,
        "src": src,
        "jour": j,
        "telegram": {"token": bool(tok), "chat": bool(cid), "env": {"TG_TOKEN": bool(os.getenv("TG_TOKEN")), "TELEGRAM_BOT_TOKEN": bool(os.getenv("TELEGRAM_BOT_TOKEN")), "CHAT_ID": bool(os.getenv("CHAT_ID")), "TG_CHAT_ID": bool(os.getenv("TG_CHAT_ID"))}},
        "time": str(datetime.datetime.now())
    }

@app.get("/test-telegram")
def test_tg():
    cap, src = get_bybit()
    msg = f"KITTRA V26 TEST LIVE {datetime.datetime.now()} CAP {cap}$ {src} - Ca marche Gardien!"
    res = send_tg(msg)
    return {"sent": msg, "result": res}

@app.get("/scan-ninja")
def scan():
    cap, src = get_bybit()
    j = analyse_jour()
    mise = cap * j["mise"] / 100
    return {"cap": cap, "src": src, "jour": j, "mise_dollars": mise, "action": j["type"]}

@app.get("/ping")
def ping():
    return {"ok": True, "time": str(datetime.datetime.now())}￼Enter
