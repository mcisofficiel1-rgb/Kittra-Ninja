# KITTRA V26 FINAL - SIMPLE + TOUTES LES FONCTIONS
import os, json, time, hmac, hashlib, datetime, requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()
COFFRE_FILE = "coffre_tresor.json"

# ========== 1. COFFRE ==========
def load_coffre():
    """Charge le coffre local"""
    try:
        if os.path.exists(COFFRE_FILE):
            return json.loads(open(COFFRE_FILE, "r").read())
    except:
        pass
    return {"principal": 10.91, "coffre": 0.0, "trades": 0}

def save_coffre(data):
    """Sauvegarde le coffre"""
    with open(COFFRE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ========== 2. BYBIT - CAPITAL REEL ==========
def get_bybit_balance():
    """
    Recupere le vrai capital Bybit UNIFIED
    Auto-detect: BYBIT_API_KEY + BYBIT_API_SECRET
    """
    key = os.getenv("BYBIT_API_KEY")
    secret = os.getenv("BYBIT_API_SECRET")
    coffre = load_coffre()

    if not key or not secret:
        return {
            "real": coffre["principal"],
            "source": "JSON_FALLBACK",
            "detail": "Pas de cles BYBIT"
        }

    try:
        timestamp = str(int(time.time() * 1000))
        param = "accountType=UNIFIED"
        recv = "5000"
        payload = timestamp + key + recv + param
        sign = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

        headers = {
            "X-BAPI-API-KEY": key,
            "X-BAPI-SIGN": sign,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv
        }
        url = "https://api.bybit.com/v5/account/wallet-balance?" + param
        r = requests.get(url, headers=headers, timeout=10).json()

        # Total equity UNIFIED
        equity = float(r["result"]["list"][0]["totalEquity"])

        return {
            "real": equity,
            "source": "BYBIT",
            "totalEquity": equity,
            "raw": r["result"]["list"][0]
        }
    except Exception as e:
        return {
            "real": coffre["principal"],
            "source": "FALLBACK_ERROR",
            "error": str(e)[:150]
        }

# ========== 3. JOURS FAVORABLES ==========
def jour_type():
    """
    Determine le type de jour
    ACHAT: 1,2,3,28,29,30 -> mise 100%
    VENTE: 5,6,7,8,18,19,20,21,22,25,26,27 -> mise 100%
    ORDINAIRE: autre -> mise 30% scalp prudent
    """
    d = datetime.datetime.now().day

    if d in [1, 2, 3, 28, 29, 30]:
        return {
            "jour": d,
            "type": "FAVORABLE_ACHAT",
            "mise": 100,
            "raison": f"Jour {d} FAVORABLE ACHAT - Mise GIGA 100%",
            "action": "ACHETER FORT"
        }

    if d in [5, 6, 7, 8, 18, 19, 20, 21, 22, 25, 26, 27]:
        return {
            "jour": d,
            "type": "FAVORABLE_VENTE",
            "mise": 100,
            "raison": f"Jour {d} FAVORABLE VENTE - Sortie GIGA 100%",
            "action": "VENDRE FORT"
        }

    return {
        "jour": d,
        "type": "ORDINAIRE",
        "mise": 30,
        "raison": f"Jour {d} ORDINAIRE - Scalp prudent 30%",
        "action": "SCALP PRUDENT"
    }

# ========== 4. TELEGRAM ==========
def get_telegram_creds():
    """Auto-detect toutes les variantes de noms TG"""
    token = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    chat = os.getenv("TG_CHAT_ID") or os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    return token, chat

def envoyer_telegram(message):
    """Envoie un message Telegram"""
    token, chat = get_telegram_creds()
    if not token or not chat:
        return {"ok": False, "error": "NO TG KEYS"}

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat, "text": message, "parse_mode": "HTML"}, timeout=10).json()
        return {"ok": True, "result": r}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ========== 5. SCAN NINJA ==========
def scan_ninja_logic():
    """Logique centrale V26"""
    bybit = get_bybit_balance()
    jour = jour_type()
    coffre = load_coffre()

    capital_reel = bybit["real"]
    mise_pourcent = jour["mise"]
    mise_dollars = capital_reel * mise_pourcent / 100

    return {
        "capital_reel": capital_reel,
        "source": bybit["source"],
        "jour_type": jour["type"],
        "jour_num": jour["jour"],
        "mise_pourcent": mise_pourcent,
        "mise_dollars": round(mise_dollars, 2),
        "raison": jour["raison"],
        "action": jour["action"],
        "coffre": coffre,
        "bybit_detail": bybit
    }

# ========== 6. ROUTES API ==========

@app.get("/", response_class=HTMLResponse)
def home():
    scan = scan_ninja_logic()
    token, chat = get_telegram_creds()

    html = f"""
    <html>
    <head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
    <style>
        body{{background:#000;color:#ff0000;text-align:center;font-family:monospace;padding:10px}}
        #eye{{width:120px;height:120px;margin:20px auto;background:radial-gradient(circle,#ff0000 20%,#000033 80%);border-radius:50%;box-shadow:0 0 40px red;animation:pulse 2s infinite}}
        @keyframes pulse{{0%{{box-shadow:0 0 20px red}}50%{{box-shadow:0 0 50px red}}100%{{box-shadow:0 0 20px red}}}}
        button{{width:90%;padding:14px;margin:5px;background:#111;color:#ff0000;border:2px solid #ff0000;border-radius:12px;font-weight:bold}}
        #out{{background:#050000;border:2px solid red;padding:12px;margin:12px auto;max-width:600px;color:#0f8;text-align:left;white-space:pre-wrap;border-radius:12px;min-height:200px;font-size:12px}}
        .badge{{display:inline-block;padding:4px 8px;border:1px solid red;border-radius:6px;margin:2px;font-size:11px}}
    </style>
    </head>
    <body>
        <div id="eye"></div>
        <h1>KITTRA V26 FINAL</h1>
        <div>
            <span class="badge">CAPITAL: {scan['capital_reel']}$</span>
            <span class="badge">{scan['jour_type']}</span>
            <span class="badge">SRC: {scan['source']}</span>
            <span class="badge">TG: {'OK' if token and chat else 'NO'}</span>
        </div>
        <div style="margin:10px;color:#ffaa00">{scan['raison']} - Mise: {scan['mise_dollars']}$</div>

        <button onclick="call('/etat')">ETAT + BYBIT REEL</button>
        <button onclick="call('/scan-ninja')">SCAN NINJA</button>
        <button onclick="call('/test-telegram')">TEST TELEGRAM</button>
        <button onclick="call('/ping')">PING</button>

        <div id="out">Bienvenue Gardien - {scan['raison']}
Capital reel: {scan['capital_reel']}$
Mise: {scan['mise_pourcent']}% = {scan['mise_dollars']}$
Source: {scan['source']}</div>

        <script>
        function call(url){{
            document.getElementById('out').innerText='Chargement '+url+'...';
            fetch(url).then(r=>r.json()).then(j=>document.getElementById('out').innerText=JSON.stringify(j,null,2)).catch(e=>document.getElementById('out').innerText='Erreur '+e)
        }}
        setInterval(()=>{{fetch('/ping').catch(()=>{{}})}}, 150000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/etat")
def etat():
    scan = scan_ninja_logic()
    token, chat = get_telegram_creds()
    return {
        "version": "V26 FINAL SIMPLE",
        "bybit": scan["bybit_detail"],
        "capital_reel": scan["capital_reel"],
        "source": scan["source"],
        "jour": scan,
        "coffre": scan["coffre"],
        "telegram": {"has_token": bool(token), "has_chat": bool(chat)},
        "time": str(datetime.datetime.now())
    }

@app.get("/scan-ninja")
def scan_ninja():
    return scan_ninja_logic()

@app.get("/test-telegram")
def test_telegram():
    bybit = get_bybit_balance()
    msg = f"KITTRA V26 TEST\nCapital reel: {bybit['real']}$\nSource: {bybit['source']}\nJour: {jour_type()['type']}\nTime: {datetime.datetime.now()}"
    res = envoyer_telegram(msg)
    return {"telegram": res, "bybit": bybit, "message_envoye": msg}

@app.get("/ping")
def ping():
    return {
        "ok": True,
        "v": "V26",
        "bybit_keys": bool(os.getenv("BYBIT_API_KEY")),
        "tg_keys": bool(get_telegram_creds()[0]),
        "time": str(datetime.datetime.now()),
        "keep_alive": "anti-dormeur actif"
    }

@app.get("/bilan-journalier")
def bilan_j():
    scan = scan_ninja_logic()
    return {"bilan": "journalier V26", "scan": scan}

@app.get("/api/status")
def api_status():
    return scan_ninja_logic()
