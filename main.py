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
        return "TG not set"
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TG_ID, "text": msg}, timeout=10)
        return "OK"
    except Exception as e:
        return str(e)

def cerveau_kittra(prompt):
    if not OR_KEY:
        return "Pas de clé OpenRouter configurée, mais Live OK"
    try:
        headers = {
            "Authorization": f"Bearer {OR_KEY}",
            "HTTP-Referer": "https://kittra-ninja-ultime.onrender.com",
            "X-Title": "KITTRA"
        }
        data = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200
        }
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        j = r.json()
        if "choices" in j:
            return j['choices'][0]['message']['content']
        return str(j)
    except Exception as e:
        return f"Erreur IA: {e}"

@app.get("/", response_class=HTMLResponse)
def root():
    return f"<h1>KITTRA V24 LIVE</h1><p>Model: {MODEL}</p><p><a href='/test-tg'>Test Telegram</a> | <a href='/scan-ia'>Scan IA</a></p>"

@app.get("/etat")
def etat():
    return {"solde": 10.91, "model": MODEL, "telegram": bool(TG_TOKEN), "or_key": bool(OR_KEY)}

@app.get("/scan-ia")
def scan_ia():
    decision = cerveau_kittra("Solde 10.91$, BNB 605$, trend haussier, décide BUY/SELL/HOLD?")
    send_telegram(f"KITTRA SCAN: {decision}")
    return {"decision": decision}

@app.get("/test-tg")
def test_tg():
    return {"result": send_telegram("🔥 KITTRA V24 Telegram OK + Cerveau Spark")}

@app.get("/scan")
def scan():
    return scan_ia()
