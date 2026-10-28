from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os, json, datetime, time, hmac, hashlib, requests

app = FastAPI()

COFFRE_FILE = "coffre_tresor.json"
TRADES_FILE = "trades_kittra.json"

def get_tg():
    t = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    c = os.getenv("TG_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
    return t, c

def send_tg(msg):
    try:
        t,c = get_tg()
        if not t or not c:
            return "NO TG"
        r = requests.post(f"https://api.telegram.org/bot{t}/sendMessage", json={"chat_id": c, "text": msg}, timeout=10)
        return f"OK {r.status_code}"
    except Exception as e:
        return str(e)[:100]

def load_coffre():
    try:
        if os.path.exists(COFFRE_FILE):
            return json.loads(open(COFFRE_FILE).read())
    except:
        pass
    return {"principal": 10.91, "coffre": 0.0, "urgence": 0.0, "safepal": 0.0, "total_gains": 0.0}

def save_coffre(d):
    open(COFFRE_FILE, "w").write(json.dumps(d))

def load_trades():
    try:
        if os.path.exists(TRADES_FILE):
            return json.loads(open(TRADES_FILE).read())
    except:
        pass
    return []

def save_trades(d):
    open(TRADES_FILE, "w").write(json.dumps(d))

def get_bybit():
    k = os.getenv("BYBIT_API_KEY")
    s = os.getenv("BYBIT_API_SECRET")
    coffre = load_coffre()
    if not k or not s:
        return coffre["principal"], "JSON"
    try:
        ts = str(int(time.time()*1000))
        p = "accountType=UNIFIED"
        sig = hmac.new(s.encode(), (ts+k+"5000"+p).encode(), hashlib.sha256).hexdigest()
        h = {"X-BAPI-API-KEY": k, "X-BAPI-SIGN": sig, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": "5000"}
        r = requests.get("https://api.bybit.com/v5/account/wallet-balance?"+p, headers=h, timeout=10).json()
        v = float(r["result"]["list"][0]["totalEquity"])
        return v, "BYBIT"
    except:
        return coffre["principal"], "FALLBACK"

def analyse_jour():
    d = datetime.datetime.now().day
    if d in [1,2,3,28,29,30]:
        return {"type": "FAVORABLE_ACHAT", "mise": 100, "action": "BUY GIGA", "raison": f"Jour {d}: fin/debut mois chute - MEILLEUR BUY"}
    if d in [5,6,7,8,18,19,20,21,22,25,26,27]:
        return {"type": "FAVORABLE_VENTE", "mise": 100, "action": "SELL GIGA", "raison": f"Jour {d}: pic historique - MEILLEUR SELL"}
    return {"type": "ORDINAIRE", "mise": 30, "action": "SCALP PRUDENT", "raison": f"Jour {d}: calme - 30% seulement"}

@app.get("/", response_class=HTMLResponse)
def home():
    cap, src = get_bybit()
    j = analyse_jour()
    c = load_coffre()
    mise = cap * j["mise"] / 100
    html = f"<html><body style=background:#000;color:#0f0;text-align:center;font-family:monospace;padding:15px><h2>KITTRA V27 ESSENTIEL</h2><p>Principal: {c['principal']}$ | Coffre: {c['coffre']}$ | Urgence: {c['urgence']}$ | SafePal: {c['safepal']}$</p><p>CAP REEL: {cap}$ ({src}) | MISE: {mise:.2f}$ ({j['mise']}%)</p><p><b>{j['type']}</b> - {j['action']}<br>{j['raison']}</p><hr><a href=/etat><button style=padding:12px;width:90%;margin:5px>ETAT</button></a><br><a href=/scan><button style=padding:12px;width:90%;margin:5px>SCAN TRADER</button></a><br><a href=/profit?m=1><button style=padding:12px;width:90%;margin:5px>TEST PROFIT +1$</button></a><br><a href=/bilan-hebdo><button style=padding:12px;width:90%;margin:5px>BILAN HEBDO + REPARTITION</button></a><br><a href=/test-telegram><button style=padding:12px;width:90%;margin:5px>TEST TELEGRAM</button></a></body></html>"
    return HTMLResponse(html)

@app.get("/etat")
def etat():
    cap, src = get_bybit()
    j = analyse_jour()
    c = load_coffre()
    t, chat = get_tg()
    return {"v": "V27 ESSENTIEL", "cap_reel": cap, "src": src, "jour": j, "mise": round(cap*j["mise"]/100,2), "coffre": c, "tg": {"token": bool(t), "chat": bool(chat)}, "time": str(datetime.datetime.now())}

@app.get("/scan")
def scan():
    cap, src = get_bybit()
    j = analyse_jour()
    c = load_coffre()
    mise = cap * j["mise"] / 100
    if "ACHAT" in j["type"]:
        dec = f"BUY BNB/SOL avec {mise:.2f}$"
    elif "VENTE" in j["type"]:
        dec = f"SELL tout target {mise:.2f}$"
    else:
        dec = f"HOLD ou SCALP 30% {mise:.2f}$ prudent"
    return {"jour": j, "cap": cap, "mise": mise, "decision": dec, "coffre": c}

@app.get("/profit")
def profit(m: float, s: str = "TRADE"):
    c = load_coffre()
    trades = load_trades()
    c["coffre"] += m
    c["total_gains"] += m
    save_coffre(c)
    trades.append({"date": str(datetime.datetime.now()), "gain": m, "type": s})
    save_trades(trades)
    send_tg(f"PROFIT {s} +{m}$ - Coffre {c['coffre']}$")
    return {"ok": True, "gain": m, "coffre": c}

@app.get("/bilan-hebdo")
def bilan_hebdo():
    c = load_coffre()
    gain = c["total_gains"]
    if gain <= 0:
        return {"msg": "Pas de gains", "coffre": c}
    total = gain
    reinvest = total * 0.5
    reste = total * 0.5
    urgence = reste * 0.4
    safepal = reste * 0.3
    coffre_part = reste * 0.3
    c["urgence"] += urgence
    c["safepal"] += safepal
    c["coffre"] += coffre_part
    c["principal"] += reinvest
    c["total_gains"] = 0
    save_coffre(c)
    msg = f"BILAN HEBDO +{total:.2f}$ - 50% REINVEST {reinvest:.2f}$ -> Principal {c['principal']:.2f}$ - 50% COFFRE: Urgence {urgence:.2f}$ SafePal {safepal:.2f}$ Coffre {coffre_part:.2f}$"
    send_tg(msg)
    return {"bilan": f"+{total}$", "repartition": {"reinvest_50": reinvest, "urgence_20": urgence, "safepal_15": safepal, "coffre_15": coffre_part}, "nouveau": c}

@app.get("/test-telegram")
def test_tg():
    cap, src = get_bybit()
    res = send_tg(f"KITTRA V27 ESSENTIEL TEST - CAP {cap}$ {src} - OK Gardien {datetime.datetime.now()}")
    return {"result": res}

@app.get("/ping")
def ping():
    return {"ok": True, "v": "V27"}
