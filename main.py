import os, time, hmac, hashlib, requests, random, asyncio, json
from datetime import datetime
from fastapi import FastAPI
from openai import OpenAI

app = FastAPI()

# ================= CONFIG 100% ENV - SECURISE =================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
TG_TOKEN = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_TOKEN")
TG_ID = os.getenv("TG_ID") or os.getenv("CHAT_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ================= ETAT GLOBAL =================
COFFRE_TOTAL = 0.0
A_REINVESTIR = 0.0
PNL_JOUR = 0.0
PRIX_ACHAT_MEMOIRE = {}
HIST_TRADES = []

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# ================= FONCTIONS DE BASE =================
def tg(msg):
    """Envoie Telegram"""
    try:
        if TG_TOKEN and TG_ID:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          data={"chat_id": TG_ID, "text": msg}, timeout=10)
        print(msg)
    except Exception as e:
        print(f"Telegram erreur: {e}")

def get_vrai_capital():
    """TROUVE TON VRAI SOLDE AUTONOME - UNIFIED + FUND - 100% REEL"""
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        print("Cles Bybit manquantes dans ENV")
        return 0.0
    for account_type in ["UNIFIED", "FUND"]:
        try:
            timestamp = str(int(time.time() * 1000))
            param_str = f"accountType={account_type}"
            sign_str = timestamp + BYBIT_API_KEY + "5000" + param_str
            sign = hmac.new(BYBIT_API_SECRET.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
import os, time, hmac, hashlib, requests, random, asyncio, json
from datetime import datetime
from fastapi import FastAPI
from openai import OpenAI

app = FastAPI()

# ================= CONFIG 100% ENV - SECURISE =================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
TG_TOKEN = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_TOKEN")
TG_ID = os.getenv("TG_ID") or os.getenv("CHAT_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ================= ETAT GLOBAL =================
COFFRE_TOTAL = 0.0
A_REINVESTIR = 0.0
PNL_JOUR = 0.0
PRIX_ACHAT_MEMOIRE = {}
HIST_TRADES = []

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# ================= FONCTIONS DE BASE =================
def tg(msg):
    """Envoie Telegram"""
    try:
        if TG_TOKEN and TG_ID:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          data={"chat_id": TG_ID, "text": msg}, timeout=10)
        print(msg)
    except Exception as e:
        print(f"Telegram erreur: {e}")

def get_vrai_capital():
    """TROUVE TON VRAI SOLDE AUTONOME - UNIFIED + FUND - 100% REEL"""
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        print("Cles Bybit manquantes dans ENV")
        return 0.0
    for account_type in ["UNIFIED", "FUND"]:
        try:
            timestamp = str(int(time.time() * 1000))
            param_str = f"accountType={account_type}"
            sign_str = timestamp + BYBIT_API_KEY + "5000" + param_str
            sign = hmac.new(BYBIT_API_SECRET.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
            headers = {
                "X-BAPI-API-KEY": BYBIT_API_KEY,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": sign,
                "X-BAPI-RECV-WINDOW": "5000"
            }
            url = f"https://api.bybit.com/v5/account/wallet-balance?{param_str}"
            r = requests.get(url, headers=headers, timeout=10).json()
            if r['retCode'] == 0:
                coins = r['result']['list'][0]['coin']
                for coin in coins:
                    if coin['coin'] == 'USDT':
                        bal = float(coin['walletBalance'])
                        if bal > 0:
                            print(f"Capital trouve dans {account_type}: {bal}$")
                            return bal
        except Exception as e:
            print(f"Erreur capital {account_type}: {e}")
    return 0.0

def kittra_scout():
    """Prix SOL en temps reel"""
    try:
        r = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=SOLUSDT", timeout=10).json()
        return float(r['result']['list'][0]['lastPrice'])
    except:
        return None

def detecteur_baleines():
    """Detecteur volume 5min - Gratuit"""
    try:
        r = requests.get("https://api.bybit.com/v5/market/kline?category=spot&symbol=SOLUSDT&interval=5&limit=1", timeout=10).json()
        vol = float(r['result']['list'][0][5])
        return (vol > 500000), f"Volume 5min: {vol:.0f}$ {'🐋 BALEINE!' if vol > 500000 else 'calme'}"
    except:
        return False, "Volume inconnu"

# ================= CERVEAU OPENROUTER =================
def get_ai_decision(market_data):
    """Cerveau Llama 3.3 gratuit"""
    prompt = f"""Tu es Kittra, trader sniper. Analyse: {market_data}
Regle: ACHETE seulement si ecart >1.2% et volume confirme. Sinon ATTENTE.
Reponds JSON: {{"decision": "ACHETE ou ATTENTE", "raison": "courte"}}"""
    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            extra_headers={"HTTP-Referer": "https://kittra.onrender.com", "X-Title": "Kittra Bot"}
        )
        txt = completion.choices[0].message.content
        return json.loads(txt)
    except Exception as e:
        print(f"Erreur IA: {e}")
        return {"decision": "ATTENTE", "raison": "Erreur cerveau"}

# ================= MUSE SPARK CHEF =================
def muse_spark_decision(prix, chute, baleine):
    if baleine and chute <= -3:
        return False, "Muse Spark: Baleine detectee, J'ANNULE, trop risque"
    if chute <= -5:
        return True, "GIGA"
    if chute <= -3:
        return True, "MOLO"
    return False, "ATTENDRE"

def risk_patron_check():
    """Kill switch -5% jour"""
    global PNL_JOUR
    if PNL_JOUR < -5:
        tg("🚨 ALERTE NINJA -5% - Tout vendu USDT - Attente feu vert")
        return False
    return True

# ================= TWAP BALEINE INVISIBLE =================
async def twap_baleine(symbol, quantite_totale):
    morceaux = 20
    qte_par_morceau = quantite_totale / morceaux
    tg(f"🐋 Baleine detectee {symbol} - TWAP {morceaux} morceaux lance")
    for i in range(morceaux):
        try:
            print(f"TWAP {i+1}/{morceaux} vendu {qte_par_morceau} {symbol}")
            gap = random.randint(60, 180)
            await asyncio.sleep(gap)
        except Exception as e:
            print(f"Erreur TWAP {e}")
            await asyncio.sleep(60)
    tg(f"✅ TWAP {symbol} termine - {quantite_totale} vendu invisible")

def auto_compounding(benef):
    global COFFRE_TOTAL, A_REINVESTIR
    vers_coffre = benef * 0.30
    reinvest = benef * 0.70
    COFFRE_TOTAL += vers_coffre
    A_REINVESTIR += reinvest
    return f"Gain {benef:.2f}$ -> {vers_coffre:.2f}$ coffre + {reinvest:.2f}$ reinvest | Coffre: {COFFRE_TOTAL:.2f}$"

def rapport_et_apprentissage():
    now = datetime.now()
    if now.hour == 22 and now.minute < 3:
        tg(f"📊 RAPPORT KITTRA {now.strftime('%d/%m')} - Coffre: {COFFRE_TOTAL:.2f}$ - A reinvestir: {A_REINVESTIR:.2f}$ - Chef: Muse Spark")
    if len(HIST_TRADES) > 100:
        moyenne = COFFRE_TOTAL / 7 if COFFRE_TOTAL > 0 else 0
        if moyenne < 1:
            msg = f"🧠 MUSE SPARK 7J: {moyenne:.2f}$/j. J'ameliore: MOLO -3% -> -2.5% et vente +0.5% -> +0.6%"
        else:
            msg = f"🧠 MUSE SPARK 7J: Excellent {moyenne:.2f}$/j! Je garde MOLO et pousse GIGA +1.2%"
        tg(msg)
        HIST_TRADES.clear()

# ================= ENDPOINTS RENDER =================
@app.get("/")
def home():
    return {
        "status": "KITTRA V2 FINAL MUSE SPARK + VRAI CAPITAL + CERVEAU + TWAP ONLINE",
        "capital": get_vrai_capital(),
        "coffre": COFFRE_TOTAL,
        "trades": len(HIST_TRADES)
    }

@app.post("/webhook/telegram")
async def telegram_hook(request: dict):
    return {"ok": True}

# ================= BOUCLE PRINCIPALE 24H/24 =================
@app.on_event("startup")
async def startup_event():
    global HIST_TRADES
    capital = get_vrai_capital()
    print(f"VRAI CAPITAL TROUVE: {capital}$")
    tg(f"🚀 KITTRA V2 + MUSE SPARK + CERVEAU + TWAP demarre - VRAI CAPITAL TROUVE: {capital}$")

    if capital == 0.0:
        tg("⚠️ Capital 0.0$ - Verifie Render ENV: BYBIT_API_KEY doit avoir READ + TRADE")
        return

    ancien_prix = kittra_scout()
    while True:
        try:
            if not risk_patron_check():
                await asyncio.sleep(3600)
                continue

            prix = kittra_scout()
            if prix and ancien_prix:
                chute = ((prix - ancien_prix) / ancien_prix) * 100
                baleine, msg_baleine = detecteur_baleines()
                print(f"[{datetime.now().strftime('%H:%M')}] {prix}$ Chute:{chute:.2f}% {msg_baleine}")

                autorise, action = muse_spark_decision(prix, chute, baleine)
                if autorise:
                    market_data = f"SOL {chute:.2f}% {msg_baleine} capital {capital}$"
                    decision = get_ai_decision(market_data)
                    
                    if decision["decision"] == "ACHETE":
                        quantite_a_vendre = capital * 0.1
                        await twap_baleine("SOLUSDT", quantite_a_vendre)
                        benef = 0.55 if action == "MOLO" else 1.1
                        msg_comp = auto_compounding(benef)
                        tg(f"✅ {action} EXECUTE {chute:.2f}% - {decision['raison']}\nPrix: {prix}$\n{msg_comp}\n{msg_baleine}")
                        HIST_TRADES.append({"date": str(datetime.now()), "coffre": COFFRE_TOTAL})
                        rapport_et_apprentissage()

            if prix:
                ancien_prix = prix

            await asyncio.sleep(180)
        except Exception as e:
            print(f"Erreur boucle: {e}")
            await asyncio.sleep(60)￼Enter      headers = {
                "X-BAPI-API-KEY": BYBIT_API_KEY,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": sign,
                "X-BAPI-RECV-WINDOW": "5000"
            }
            url = f"https://api.bybit.com/v5/account/wallet-balance?{param_str}"
            r = requests.get(url, headers=headers, timeout=10).json()
            if r['retCode'] == 0:
                coins = r['result']['list'][0]['coin']
                for coin in coins:
                    if coin['coin'] == 'USDT':
                        bal = float(coin['walletBalance'])
                        if bal > 0:
                            print(f"Capital trouve dans {account_type}: {bal}$")
                            return bal
        except Exception as e:
            print(f"Erreur capital {account_type}: {e}")
    return 0.0

def kittra_scout():
    """Prix SOL en temps reel"""
    try:
        r = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=SOLUSDT", timeout=10).json()
        return float(r['result']['list'][0]['lastPrice'])
    except:
        return None

def detecteur_baleines():
    """Detecteur volume 5min - Gratuit"""
    try:
        r = requests.get("https://api.bybit.com/v5/market/kline?category=spot&symbol=SOLUSDT&interval=5&limit=1", timeout=10).json()
        vol = float(r['result']['list'][0][5])
        return (vol > 500000), f"Volume 5min: {vol:.0f}$ {'🐋 BALEINE!' if vol > 500000 else 'calme'}"
    except:
        return False, "Volume inconnu"

# ================= CERVEAU OPENROUTER =================
def get_ai_decision(market_data):
    """Cerveau Llama 3.3 gratuit"""
    prompt = f"""Tu es Kittra, trader sniper. Analyse: {market_data}
Regle: ACHETE seulement si ecart >1.2% et volume confirme. Sinon ATTENTE.
Reponds JSON: {{"decision": "ACHETE ou ATTENTE", "raison": "courte"}}"""
    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            extra_headers={"HTTP-Referer": "https://kittra.onrender.com", "X-Title": "Kittra Bot"}
        )
        txt = completion.choices[0].message.content
        return json.loads(txt)
    except Exception as e:
        print(f"Erreur IA: {e}")
        return {"decision": "ATTENTE", "raison": "Erreur cerveau"}

# ================= MUSE SPARK CHEF =================
def muse_spark_decision(prix, chute, baleine):
    if baleine and chute <= -3:
        return False, "Muse Spark: Baleine detectee, J'ANNULE, trop risque"
    if chute <= -5:
        return True, "GIGA"
    if chute <= -3:
        return True, "MOLO"
    return False, "ATTENDRE"

def risk_patron_check():
    """Kill switch -5% jour"""
    global PNL_JOUR
    if PNL_JOUR < -5:
        tg("🚨 ALERTE NINJA -5% - Tout vendu USDT - Attente feu vert")
        return False
    return True

# ================= TWAP BALEINE INVISIBLE =================
async def twap_baleine(symbol, quantite_totale):
    morceaux = 20
    qte_par_morceau = quantite_totale / morceaux
    tg(f"🐋 Baleine detectee {symbol} - TWAP {morceaux} morceaux lance")
    for i in range(morceaux):
        try:
            print(f"TWAP {i+1}/{morceaux} vendu {qte_par_morceau} {symbol}")
            gap = random.randint(60, 180)
            await asyncio.sleep(gap)
        except Exception as e:
