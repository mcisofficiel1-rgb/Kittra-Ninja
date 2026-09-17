import os, re, threading, time, asyncio
from flask import Flask, jsonify
from pybit.unified_trading import HTTP
import requests

app = Flask(__name__)

# --- CLÉS - Lues depuis Render Environment ---
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://kittra-ninja-ultime.onrender.com")

print("=== KITTRA V17.6 REAL MODE ===")
print(f"API_KEY present: {bool(API_KEY)}")
print(f"API_SECRET present: {bool(API_SECRET)}")

# Connexion Bybit RÉELLE
try:
    session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)
    print("Bybit Session créée")
except Exception as e:
    print(f"Erreur création session: {e}")
    session = None

def get_real_balance():
    if not session or not API_KEY:
        return None
    try:
        resp = session.get_wallet_balance(accountType="UNIFIED")
        # Bybit renvoie liste de coins
        coins = resp['result']['list'][0]['coin']
        for c in coins:
            if c['coin'] == 'USDT':
                return float(c['walletBalance'])
        # fallback premier coin
        return float(coins[0]['walletBalance'])
    except Exception as e:
        print(f"BYBIT ERROR: {e}")
        return None

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

@app.route("/")
def home():
    bal = get_real_balance()
    bal_txt = f"{bal:.4f} USDT" if bal is not None else "Clés manquantes ou Erreur API"
    html = f"""
    <h1>🥷 KITTRA NINJA V17.6 LIVE</h1>
    <h2>SOLDE RÉEL: {bal_txt}</h2>
    <p>Mode: BYBIT MAINNET REAL</p>
    <p>Anti-sleep: ACTIVE</p>
    <p><a href="/ping">/ping</a> | <a href="/api/status">/api/status</a></p>
    """
    return html

@app.route("/ping")
def ping():
    bal = get_real_balance()
    return jsonify({
        "status": "✅ KITTRA LIVE",
        "real_balance": bal,
        "balance_text": f"{bal} USDT" if bal is not None else "API Error",
        "is_real": True,
        "exchange": "BYBIT MAINNET",
        "anti_sleep": "ACTIVE",
        "keys_loaded": bool(API_KEY and API_SECRET)
    })

@app.route("/api/status")
def api_status():
    bal = get_real_balance()
    return jsonify({
        "principal": bal,
        "is_real": True,
        "source": "BYBIT API DIRECT",
        "keys_ok": bool(API_KEY and API_SECRET)
    })

def trading_loop():
    send_telegram("🥷 KITTRA V17.6 démarré - Mode RÉEL Bybit actif!")
    while True:
        try:
            bal = get_real_balance()
            if bal is not None:
                print(f"=== VRAI SOLDE BYBIT: {bal:.4f} USDT ===")
            else:
                print("=== VRAI SOLDE BYBIT: None - Vérifie tes clés dans Environment ===")
            # --- ICI TU METS TA LOGIQUE DE TRADING RÉEL ---
            time.sleep(60)
        except Exception as e:
            print(f"LOOP ERROR: {e}")
            time.sleep(10)

def anti_sleep_loop():
    while True:
        time.sleep(600) # 10 min
        try:
            requests.get(f"{RENDER_URL}/ping", timeout=10)
            print("[ANTI-SLEEP] Ping auto OK")
        except Exception as e:
            print(f"[ANTI-SLEEP] fail: {e}")

# Lancer threads - CORRIGÉ SANS REGEX BUG
threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=anti_sleep_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
