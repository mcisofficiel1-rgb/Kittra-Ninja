import os, threading, time
from flask import Flask, jsonify
from pybit.unified_trading import HTTP
import requests

app = Flask(__name__)

# --- V17.8 AUTO-DETECT BYBIT + TG - LIT TOUT ---
def get_env(*names):
    for n in names:
        v = os.getenv(n)
        if v:
            print(f"ENV trouvé: {n} = OK")
            return v
    return None

# Il essaie TOUS les noms possibles pour Bybit
API_KEY = get_env("API_KEY", "BYBIT_API_KEY", "BYBIT_KEY", "BYBIT_API", "APIKEY", "ApiKey")
API_SECRET = get_env("API_SECRET", "BYBIT_API_SECRET", "BYBIT_SECRET", "BYBIT_API_SEC", "APISECRET", "ApiSecret")

# Il essaie TOUS les noms pour Telegram
BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN", "TG_TOKEN", "BOT_TOKEN", "TELEGRAM_TOKEN", "TG_BOT_TOKEN")
CHAT_ID = get_env("TELEGRAM_CHAT_ID", "TG_ID", "CHAT_ID", "TELEGRAM_ID", "TG_CHAT_ID")

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://kittra-ninja-ultime.onrender.com")

print("=== KITTRA V17.8 AUTO-DETECT ===")
print(f"FINAL API_KEY: {'TROUVÉ ✅' if API_KEY else 'MANQUANT ❌'}")
print(f"FINAL API_SECRET: {'TROUVÉ ✅' if API_SECRET else 'MANQUANT ❌'}")
print(f"FINAL BOT_TOKEN: {'TROUVÉ ✅' if BOT_TOKEN else 'MANQUANT ❌'}")
print(f"FINAL CHAT_ID: {'TROUVÉ ✅' if CHAT_ID else 'MANQUANT ❌'}")

session = None
if API_KEY and API_SECRET:
    try:
        session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)
        print(">>> Bybit Session CRÉÉE avec succès ✅")
    except Exception as e:
        print(f">>> Erreur session: {e}")
else:
    print(">>> PAS DE SESSION - Mets les 2 clés Bybit dans Environment")

def get_real_balance():
    if not session:
        return None
    try:
        resp = session.get_wallet_balance(accountType="UNIFIED")
        coins = resp['result']['list'][0]['coin']
        for c in coins:
            if c['coin'] == 'USDT':
                return float(c['walletBalance'])
        return float(coins[0]['walletBalance']) if coins else 0.0
    except Exception as e:
        print(f"BYBIT ERROR: {e}")
        return None

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

@app.route("/")
def home():
    bal = get_real_balance()
    txt = f"{bal:.4f} USDT (RÉEL)" if bal is not None else "Clés Bybit non lues"
    return f"<h1>🥷 KITTRA V17.8 AUTO-DETECT LIVE</h1><h2>{txt}</h2><p>Bybit OK: {bool(session)} | TG OK: {bool(BOT_TOKEN)}</p>"

@app.route("/ping")
def ping():
    return jsonify({
        "status": "✅ LIVE V17.8",
        "real_balance": get_real_balance(),
        "keys_detected": {
            "bybit_key": bool(API_KEY),
            "bybit_secret": bool(API_SECRET),
            "tg_token": bool(BOT_TOKEN),
            "tg_id": bool(CHAT_ID)
        },
        "is_real": True
    })

@app.route("/api/status")
def api_status():
    return jsonify({"principal": get_real_balance(), "is_real": True})

def trading_loop():
    send_telegram("🥷 KITTRA V17.8 AUTO-DETECT démarré!")
    while True:
        bal = get_real_balance()
        print(f"=== VRAI SOLDE BYBIT: {bal if bal is not None else 'None - Vérifie Environment'} ===")
        time.sleep(60)

def anti_sleep_loop():
    while True:
        time.sleep(600)
        try: requests.get(f"{RENDER_URL}/ping", timeout=10)
        except: pass

threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=anti_sleep_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
