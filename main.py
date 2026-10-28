import os, json, time, hmac, hashlib, datetime, requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

def load_coffre():
    if os.path.exists("coffre_tresor.json"):
        return json.loads(open("coffre_tresor.json").read())
    return {"principal": 10.91, "coffre": 0.0}

def get_bybit_balance():
    key = os.getenv("BYBIT_API_KEY")
    secret = os.getenv("BYBIT_API_SECRET")
    if not key or not secret:
        return {"real": load_coffre()["principal"], "source": "JSON"}
    try:
        ts = str(int(time.time()*1000))
        param = "accountType=UNIFIED"
        payload = ts + key + "5000" + param
        sign = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        headers = {"X-BAPI-API-KEY": key, "X-BAPI-SIGN": sign, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": "5000"}
        url = "https://api.bybit.com/v5/account/wallet-balance?" + param
        r = requests.get(url, headers=headers, timeout=10).json()
        bal = float(r["result"]["list"][0]["totalEquity"])
        return {"real": bal, "source": "BYBIT"}
    except Exception as e:
        return {"real": load_coffre()["principal"], "source": "FALLBACK", "error": str(e)[:80]}

def jour_type():
    d = datetime.datetime.now().day
    if d in [1,2,3,28,29,30]:
        return {"type": "FAVORABLE_ACHAT", "mise": 100, "raison": "Jour BUY GIGA"}
    if d in [5,6,7,8,18,19,20,21,22,25,26,27]:
        return {"type": "FAVORABLE_VENTE", "mise": 100, "raison": "Jour SELL GIGA"}
    return {"type": "ORDINAIRE", "mise": 30, "raison": "Jour SCALP"}

@app.get("/", response_class=HTMLResponse)
def home():
    j = jour_type()
    b = get_bybit_balance()
    c = load_coffre()
    html = "<html><head><meta charset='UTF-8'><style>body{background:#000;color:red;text-align:center;font-family:monospace}#eye{width:120px;height:120px;margin:20px auto;background:radial-gradient(circle,red 20%,#000033 80%);border-radius:50%}button{width:90%;padding:12px;margin:4px;background:#111;color:red;border:2px solid red;border-radius:10px}#out{background:#050000;border:2px solid red;padding:10px;margin:10px;color:#0f8;text-align:left;min-height:150px}</style></head><body><div id=eye></div><h1>KITTRA V26</h1><div>REEL: " + str(b['real']) + "$ | " + j['type'] + " | SRC:" + b['source'] + "</div><button onclick=\"fetch('/etat').then(r=>r.json()).then(j=>out.innerText=JSON.stringify(j,null,2))\">ETAT</button><button onclick=\"fetch('/scan-ninja').then(r=>r.json()).then(j=>out.innerText=JSON.stringify(j,null,2))\">SCAN</button><button onclick=\"fetch('/test-telegram').then(r=>r.json()).then(j=>out.innerText=JSON.stringify(j,null,2))\">TEST TG</button><div id=out>" + j['raison'] + "</div></body></html>"
    return HTMLResponse(content=html)

@app.get("/etat")
def etat():
    return {"bybit": get_bybit_balance(), "coffre": load_coffre(), "jour": jour_type()}

@app.get("/scan-ninja")
def scan():
    j = jour_type()
    b = get_bybit_balance()
    mise = b["real"] * j["mise"] / 100
    return {"capital_reel": b["real"], "source": b["source"], "type": j["type"], "mise": mise}

@app.get("/test-telegram")
def test_tg():
    token = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TG_CHAT_ID") or os.getenv("CHAT_ID")
    if not token or not chat:
        return {"error": "NO TG", "has_token": bool(token), "has_chat": bool(chat)}
    b = get_bybit_balance()
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    r = requests.post(url, json={"chat_id": chat, "text": "KITTRA V26 TEST Capital " + str(b["real"]) + "$"}, timeout=10).json()
    return {"tg": r, "bybit": b}

@app.get("/ping")
def ping():
    return {"ok": True, "bybit_keys": bool(os.getenv("BYBIT_API_KEY")), "time": str(datetime.datetime.now())}￼Enter
