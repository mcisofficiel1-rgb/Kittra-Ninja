import os
import json
import time
import threading
from flask import Flask, jsonify, send_from_directory
from pybit.unified_trading import HTTP
import requests

app = Flask(__name__)
print("=== KITTRA NINJA ULTIME V17.4 STARTING ===")

try:
    with open('Kittra.json', 'r') as f:
        config = json.load(f)
    VAULT_ADDRESS = config['vault']['VAULT_ADDRESS']
    VAULT_NAME = config['vault']['VAULT_NAME']
except:
    VAULT_ADDRESS = "TG8UcJUH152YyWsSArL4cwwV78GZiYJoqG"
    VAULT_NAME = "KITTRA-VAULT"
    config = {"MODE": "MAINNET"}

@app.route('/')
def home():
    if os.path.exists('index.html'):
        return send_from_directory('.', 'index.html')
    return f"KITTRA {VAULT_NAME} LIVE - {VAULT_ADDRESS}"

@app.route('/ping')
def ping():
    return jsonify({"status": "✅ KITTRA LIVE", "vault": VAULT_ADDRESS, "anti_sleep": "ACTIVE", "mode": "MAINNET"})

@app.route('/api/status')
def api_status():
    return jsonify({"principal": "127.45", "coffre_total": "89.30", "mode": "MAINNET", "vault": VAULT_ADDRESS})

@app.route('/api/transactions')
def api_trans():
    return jsonify({"principal": "127.45", "coffre_total": "89.30", "vault": VAULT_ADDRESS})

@app.route('/<path:path>')
def files(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return jsonify({"error": "Not Found"}), 404

def anti_sleep_system():
    time.sleep(30)
    while True:
        try:
            url = os.getenv("RENDER_EXTERNAL_URL", "https://kittra-ninja-ultime.onrender.com")
            requests.get(f"{url}/ping", timeout=10)
            print(f"[ANTI-SLEEP] Ping OK - KITTRA RESTE EVEILLE")
            time.sleep(600)
        except:
            time.sleep(60)

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

try:
    session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)
except:
    session = None

def send_telegram(msg):
    try:
        if BOT_TOKEN and CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except: pass

def trading_loop():
    time.sleep(5)
    send_telegram(f"🥷 KITTRA {VAULT_NAME} LIVE! {VAULT_ADDRESS} - ANTI-SLEEP ACTIF")
    while True:
        try:
            if session:
                bal = session.get_wallet_balance(accountType="UNIFIED")
                print("Balance OK")
            time.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=trading_loop, daemon=True).start()
    threading.Thread(target=anti_sleep_system, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
