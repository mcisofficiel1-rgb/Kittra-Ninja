import os, threading, time, requests, json
from datetime import datetime, timedelta
from flask import Flask, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

# --- V17.8 AUTO-DETECT QUI MARCHAIT (gardé de l'ancien) ---
def get_env(*names):
    for n in names:
        v = os.getenv(n)
        if v:
            print(f"ENV trouvé: {n} = OK")
            return v
    return None

API_KEY = get_env("API_KEY","BYBIT_API_KEY","BYBIT_KEY","BYBIT_API","APIKEY")
API_SECRET = get_env("API_SECRET","BYBIT_API_SECRET","BYBIT_SECRET","BYBIT_API_SEC","APISECRET")
BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN","TG_TOKEN","BOT_TOKEN","TELEGRAM_TOKEN")
CHAT_ID = get_env("TELEGRAM_CHAT_ID","TG_ID","CHAT_ID","TELEGRAM_ID")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL","https://kittra-ninja-ultime.onrender.com")
WALLET_TRADING_INTERNE = get_env("WALLET_TRADING_INTERNE","BYBIT_UNIFIED") or "BYBIT_UNIFIED"
WALLET_EPARGNE_EXTERNE = get_env("WALLET_EPARGNE_EXTERNE","WALLET_EXTERNE") or "TG8UcJUH152YyWsSArL4cwwV78GZiYJoqG"

print("=== KITTRA V18.5 FUSION ULTIME ≤1≥ + GARDE-FOU ===")
print(f"KEY:{bool(API_KEY)} SEC:{bool(API_SECRET)} TG:{bool(BOT_TOKEN)}")
print(f"INTERNE:{WALLET_TRADING_INTERNE} EXTERNE:{WALLET_EPARGNE_EXTERNE}")

session = None
if API_KEY and API_SECRET:
    try:
        session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)
        print(">>> Session Bybit OK ✅")
    except Exception as e:
        print(f">>> Erreur {e}")
else:
    print(">>> PAS DE SESSION")

# === CONFIG V18.2.2 GARDÉE (ancien essentiel) + FIX nouveau ===
CONFIG = {
    "principal": 10.3443,
    "principal_securite": 0.95, # 9.82$ minimum à garder - GARDE-FOU
    "coffre_total": 0,
    "urgences_lock": 0,
    "wallet_perso": {"last_withdraw": datetime.utcnow()-timedelta(days=31)},
    "memoire": {"business":0,"maison":0,"enfants":0},
    "repartition": {"trading":40,"urgences":24,"business":12,"maison":8,"enfants":4}
}

# FUSION: AUTO-COINS (ancien + nouveau) - IL CHOISIT SEUL
AUTO_COINS = ["BTCUSDT","SOLUSDT","ETHUSDT","TRXUSDT","BNBUSDT","XRPUSDT","AVAXUSDT","DOGEUSDT"]
price_history = {}
positions = {}
KITTRA_FILE = "Kittra.json"

def load():
    global positions
    try:
        with open(KITTRA_FILE,"r") as f:
            data=json.load(f)
            positions=data.get("positions",{})
    except: pass

def save():
    with open(KITTRA_FILE,"w") as f:
        json.dump({"positions":positions, "cap":CONFIG["principal"]}, f)

def send_tg(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_real_balance():
    if not session: return None
    try:
        coins = session.get_wallet_balance(accountType="UNIFIED")['result']['list'][0]['coin']
        for c in coins:
            if c['coin']=='USDT': return float(c['walletBalance'])
        return float(coins[0]['walletBalance']) if coins else 0.0
    except Exception as e:
        print(f"BAL ERROR {e}"); return None

def get_signal(symbol):
    if not session: return None,None,None,None,None
    try:
        kl = session.get_kline(category="spot",symbol=symbol,interval="15",limit=30)['result']['list']
        closes = [float(k[4]) for k in reversed(kl)]
        if len(closes)<21: return None,None,None,None,None
        ema9=sum(closes[-9:])/9; ema21=sum(closes[-21:])/21
        gains=[max(0,closes[i]-closes[i-1]) for i in range(1,15)]
        losses=[max(0,closes[i-1]-closes[i]) for i in range(1,15)]
        rsi=100-(100/(1+(sum(gains)/14)/(sum(losses)/14+0.00001)))
        return rsi,ema9,ema21,closes[-1],(closes[-1]-closes[-2])/closes[-2]*100
    except: return None,None,None,None,None

def get_variation_5min(symbol, price_now):
    old = price_history.get(symbol)
    if not old:
        price_history[symbol] = {"price": price_now, "time": time.time()}
        return 999
    if time.time() - old["time"] >= 300:
        var = (price_now - old["price"])/old["price"]*100
        price_history[symbol] = {"price": price_now, "time": time.time()}
        return var
