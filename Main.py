import os
import json
import time
import threading
from flask import Flask
from pybit.unified_trading import HTTP
import requests

# --- SERVEUR WEB POUR RENDER GRATUIT (NE PAS TOUCHER) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "KITTRA-VAULT LIVE - REAL MONEY ACTIVE - BOT IS TRADING"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()
# ---------------------------------------------------------

print("=== KITTRA NINJA ULTIME STARTING ===")

# Charger la config
with open('Kittra.json', 'r') as f:
    config = json.load(f)

print(f"MODE: {config['MODE']}")
print(f"VAULT: {config['vault']['VAULT_NAME']} -> {config['vault']['VAULT_ADDRESS']}")

# Connexion Bybit REAL
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET
)

# Telegram
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print(f"Telegram error: {e}")

send_telegram(f"🥷 KITTRA {config['vault']['VAULT_NAME']} LIVE EN ARGENT REEL! Mode: {config['MODE']}")

# Boucle de trading principale
def trading_loop():
    while True:
        try:
            # Exemple: Check balance
            balance = session.get_wallet_balance(accountType="UNIFIED")
            print(f"Balance check: OK - KITTRA VAULT ACTIF")
            
            # ICI TON LOGIC DE TRADING EXISTANT
            # ... ton code de scalp ...
            
            time.sleep(60)  # scan chaque minute
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

# Lancer le trading
if __name__ == "__main__":
    trading_loop()
