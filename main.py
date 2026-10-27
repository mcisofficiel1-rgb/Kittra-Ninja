from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os, requests

app = FastAPI()

MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/muse-spark-1.3")
OR_KEY = os.getenv("OPENROUTER_API_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_ID = os.getenv("TG_CHAT_ID")

def send_telegram(msg):
    if not TG_TOKEN or not TG_ID:
        return "No TG"
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        return "OK"
    except Exception as e:
        return str(e)

def cerveau_kittra(prompt):
    if not OR_KEY:
        return "Pas de clé OpenRouter"
    headers = {
        "Authorization": f"Bearer {OR_KEY}",
        "HTTP-Referer": "https://kittra-ninja-ultime.onrender.com",
        "X-Title": "KITTRA V23"
    }
    system = "Tu es KITTRA V23 NINJA ULTIME, trader autonome comme Muse Spark. Solde 10.91$. Décide BUY/SELL/HOLD avec 1 phrase. Mode BALEINE, gestion risque stricte."
    data = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "max_tokens": 250
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
    return r.json()['choices'][0]['message']['content']

HTML = """
<html><head><meta charset="utf-8"><title>KITTRA V24</title>
<style>body{background:#000;color:#0f8;padding:20px;font-family:monospace}
.card{border:1px solid #0f8;padding:10px;margin:10px 0;border-radius:8px}
.btn{background:#0f8;color:#000;padding:10px;border:0;border-radius:5px;margin:5px}</style>
</head><body>
<h1>🥷 KITTRA V24 AUTONOME + TELEGRAM</h1>
<div class="card">Cerveau: MODEL_PLACEHOLDER</div>
<div class="card">Telegram: TG_STATUS</div>
<button class="btn" onclick="fetch('/scan-ia').then(r=>r.json()).then(d=>alert(d.decision))">SCAN IA + TELEGRAM</button>
<button class="btn" onclick="fetch('/etat').then(r=>r.json()).then(d=>alert(JSON.stringify(d)))">ETAT</button>
</body></html>
"""

@app.get("/", response_class=HTMLResponse)
def root():
    h = HTML.replace("MODEL_PLACEHOLDER", MODEL).replace("TG_STATUS", "OK ✅" if TG_TOKEN else "Non configuré")
    return h

@app.get("/etat")
def etat():
    return {"solde": 10.91, "mode": "BALEINE", "model": MODEL, "telegram": bool(TG_TOKEN)}

@app.get("/scan-ia")
def scan_ia():
    prompt = "Solde 10.91$, BNB=605$, trend haussier, volume +12%, RSI 58. Décide BUY/SELL/HOLD et taille position?"
    decision = cerveau_kittra(prompt)
    
    msg_tg = f"🤖 *KITTRA V24 SCAN*\n\n*Model:* {MODEL}\n*Solde:* 10.91$\n*Décision:* {decision}\n\n[Dashboard](https://kittra-ninja-ultime.onrender.com)"
    tg = send_telegram(msg_tg)
    
    return {"cerveau": MODEL, "decision": decision, "telegram": tg}

@app.get("/scan")
def scan():
    return scan_ia()

@app.get("/test-tg")
def test_tg():
    return {"sent": send_telegram("🔥 KITTRA V24 Telegram OK ! Cerveau Muse Spark branché")}
