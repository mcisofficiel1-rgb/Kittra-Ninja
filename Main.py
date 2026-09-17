import os, asyncio, threading, time, hashlib, hmac, random
from flask import Flask, jsonify, request, render_template_string
from pybit.unified_trading import HTTP
import requests

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://kittra-ninja-ultime.onrender.com")

# VRAIE CONNEXION BYBIT - MAINNET
session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)

def get_real_balance():
    try:
        bal = session.get_wallet_balance(accountType="UNIFIED")
        usdt = bal['result']['list'][0]['coin'][0]['walletBalance']
        return float(usdt)
    except Exception as e:
        print(f"BYBIT ERROR: {e}")
        return None

@app.route("/")
def home():
    real_bal = get_real_balance()
    display = f"{real_bal:.2f} USDT" if real_bal is not None else "API Error - Vérifie clé Bybit"
    return f"<h1>🥷 KITTRA NINJA LIVE</h1><h2>SOLDE RÉEL BYBIT: {display}</h2><p>Anti-sleep: ACTIVE</p>"

@app.route("/ping")
def ping():
    real_bal = get_real_balance()
    return jsonify({"status": "✅ KITTRA LIVE", "real_balance": real_bal, "anti_sleep": "ACTIVE", "exchange": "BYBIT MAINNET"})

@app.route("/api/status")
def api_status():
    real_bal = get_real_balance()
    return jsonify({"principal": real_bal, "is_real": True, "source": "BYBIT API DIRECT"})

def trading_loop():
    while True:
        try:
            bal = get_real_balance()
            print(f"=== VRAI SOLDE BYBIT: {bal} USDT ===")
            if bal:
                # Ici ton vrai trading
                pass
        except Exception as e:
            print(f"LOOP ERROR: {e}")
        time.sleep(60)

# Anti-sleep
def anti_sleep():
    while True:
        time.sleep(600)
        try:
            requests.get(f"{RENDER_URL}/ping")
            print("[ANTI-SLEEP] Ping OK")
        except: pass

threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=anti_sleep, daemon=True).start()

if __name__ == "__main__":
    print("=== KITTRA V17.5 REAL BYBIT MODE ===")
    app.run(host="0.0.0.0", port=10000)
