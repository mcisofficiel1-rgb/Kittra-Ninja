import os, time
from pybit.unified_trading import HTTP

# === CONFIG V19.3 - KITTRA GARDIEN ===
API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = ["DOGEUSDT", "TRXUSDT", "BNBUSDT", "BTCUSDT"] # 4 coins décidé
USDT_PAR_TRADE = 1.10
USDT_VOULU = {"BNBUSDT": 5.20, "DOGEUSDT": 1.10, "TRXUSDT": 1.10, "BTCUSDT": 1.10}

session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)

def get_real_balance():
    try:
        bal = session.get_wallet_balance(accountType="UNIFIED")
        coins = bal['result']['list'][0]['coin']
        for c in coins:
            if c['coin'] == 'USDT':
                return float(c['walletBalance']), float(c['availableToWithdraw'] if 'availableToWithdraw' in c else c['walletBalance'])
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

# === FONCTION ACHAT CORRIGÉE V19.3 - ANTI 170131 ===
def buy_coin(symbol, usdt_amount):
    try:
        price = get_price(symbol)
        if price == 0:
            print(f"{symbol} prix 0")
            return False

        # V19.3 CORRECTION ICI: On envoie USDT, pas quantité de coin
        print(f"Achat {symbol} pour {usdt_amount}$")
        order = session.place_order(
            category="spot",
            symbol=symbol,
            side="Buy",
            orderType="Market",
            qty=str(usdt_amount),  # Montant en USDT
            marketUnit="quoteCoin"  # <<< CLE QUI CORRIGE 170131
        )
        print(f"✅ ACHAT OK {symbol}: {order}")
        return True
    except Exception as e:
        print(f"❌ Achat {symbol} {e}")
        return False

def sell_coin(symbol, qty_base):
    try:
        order = session.place_order(
            category="spot",
            symbol=symbol,
            side="Sell",
            orderType="Market",
            qty=str(qty_base) # Pour vente on vend en quantité de coin
        )
        print(f"✅ VENTE OK {symbol}")
        return True
    except Exception as e:
        print(f"❌ Vente {symbol} {e}")
        return False

# === BOUCLE PRINCIPALE KITTRA ===
def main_loop():
    while True:
        wallet, dispo = get_real_balance()
        print(f"V19.3 4-COINS 1.10$ LIVE! Solde:{wallet}$ Dispo:{dispo}$")
        
        for sym in SYMBOLS:
            usdt_final = USDT_VOULU.get(sym, USDT_PAR_TRADE)
            if dispo >= usdt_final:
                buy_coin(sym, usdt_final)
                time.sleep(3)
        
        time.sleep(60) # Attente 60s

if __name__ == "__main__":
    main_loop()
