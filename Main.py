import os
import time
from pybit.unified_trading import HTTP

# === CONFIG V19.3 - KITTRA GARDIEN ===
API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")

SYMBOLS = ["DOGEUSDT", "TRXUSDT", "BNBUSDT", "BTCUSDT"]
USDT_VOULU = {"BNBUSDT": 5.20, "DOGEUSDT": 1.10, "TRXUSDT": 1.10, "BTCUSDT": 1.10}

session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)

def get_real_balance():
    try:
        bal = session.get_wallet_balance(accountType="UNIFIED")
        coins = bal['result']['list'][0]['coin']
        for c in coins:
            if c['coin'] == 'USDT':
                avail = c.get('availableToWithdraw') or c.get('availableBalance') or c['walletBalance']
                return float(c['walletBalance']), float(avail)
        return 0, 0
    except Exception as e:
        print(f"Erreur balance: {e}")
        return 0, 0

def get_price(symbol):
    try:
        ticker = session.get_tickers(category="spot", symbol=symbol)
        return float(ticker['result']['list'][0]['lastPrice'])
    except:
        return 0

def buy_coin(symbol, usdt_amount):
    try:
        print(f"Achat {symbol} pour {usdt_amount}$")
        order = session.place_order(
            category="spot",
            symbol=symbol,
            side="Buy",
            orderType="Market",
            qty=str(usdt_amount),
            marketUnit="quoteCoin" # ANTI 170131
        )
        print(f"✅ ACHAT OK {symbol}")
        return True
    except Exception as e:
        print(f"❌ Achat {symbol} {e}")
        return False

def main_loop():
    while True:
        wallet, dispo = get_real_balance()
        print(f"V19.3 4-COINS 1.10$ LIVE! Solde:{wallet}$ Dispo:{dispo}$")

        # Achat 1 seul coin par minute pour ne pas vider 10$
        for sym in SYMBOLS:
            usdt_final = USDT_VOULU.get(sym, 1.10)
            if dispo >= usdt_final:
                if buy_coin(sym, usdt_final):
                    break # On achète 1 seul puis on attend
                time.sleep(2)

        time.sleep(60)

if __name__ == "__main__":
    main_loop()
