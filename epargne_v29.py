# epargne_v29.py - KITTRA V29 - S'adapte à tes 6 fichiers existants
# Il utilise main.py, ajoute.py, memoire_qg.json automatiquement
import json, os, requests
from datetime import datetime

JSON_EPARGNE = "json_epargne.json"
JSON_MEMOIRE = "memoire_qg.json"  # ton fichier existant #3

def load_json(path):
    try:
        with open(path, 'r') as f: return json.load(f)
    except: return {}

def save_json(path, data):
    with open(path, 'w') as f: json.dump(data, f, indent=2)

# --- 1. SCAN LIVE Bybit KITTRAEPARGNE (utilise ton BYBIT existant de main.py) ---
def scan_live_balance():
    epargne = load_json(JSON_EPARGNE)
    # Si ton main.py a déjà bybit_price, on réutilise
    # Sinon on lit le fichier
    return epargne.get("EPARGNE_CAPITAL_LIVE", 0.0)

# --- 2. MUSE SPARK + BALEINES (utilise GROQ_API_KEY de ton main.py) ---
def muse_spark_decide(prices_24h, whale_news, capital):
    """
    prices_24h: dict venant de ton main.py kittra_scout() étendu
    whale_news: dict venant de detecteur_baleines()
    """
    candidates = []
    for coin, ch in prices_24h.items():
        if ch <= -5:
            score = abs(ch) + (10 if coin in whale_news else 0)
            candidates.append((coin, ch, score))
    if not candidates:
        return {"action": "WAIT"}
    
    candidates.sort(key=lambda x: x[2], reverse=True)
    coin, ch, _ = candidates[0]
    
    amount = 1.5 if ch <= -12 else 1.0 if ch <= -8 else 0.5
    if capital < amount:
        return {"action": "WAIT", "reason": "capital low"}
    
    palier = -12 if ch <= -12 else -8 if ch <= -8 else -5
    return {"action": "BUY", "coin": coin, "change": ch, "palier": palier, "amount": amount, "whale": whale_news.get(coin, "")}

# --- 3. GET /epargne-status (route à ajouter dans main.py) ---
def get_epargne_status():
    epargne = load_json(JSON_EPARGNE)
    memoire = load_json(JSON_MEMOIRE)
    
    live = scan_live_balance()
    
    # Fige INITIAL au premier transfert réel Bybit
    if epargne.get("EPARGNE_INITIAL", 0.0) == 0.0 and live > 0:
        epargne["EPARGNE_INITIAL"] = live
        epargne["EPARGNE_LAST_SCAN"] = datetime.utcnow().isoformat()
        save_json(JSON_EPARGNE, epargne)
    
    epargne["EPARGNE_CAPITAL_LIVE"] = live
    
    # Auto-expand selon capital (6e fichier = ta logique existante)
    if live >= 20:
        allowed = epargne["EPARGNE_CRYPTOS_START"] + epargne["AUTO_EXPAND"]["tiers"]["5-20"] + epargne["AUTO_EXPAND"]["tiers"]["20-100"][:2]
    elif live >= 5:
        allowed = epargne["EPARGNE_CRYPTOS_START"] + epargne["AUTO_EXPAND"]["tiers"]["5-20"]
    else:
        allowed = epargne["EPARGNE_CRYPTOS_START"]
    
    perf = 0
    if epargne["EPARGNE_INITIAL"] > 0:
        perf = ((live - epargne["EPARGNE_INITIAL"]) / epargne["EPARGNE_INITIAL"]) * 100
    
    return {
        "V": "V29 EPARGNE AUTO",
        "initial": epargne["EPARGNE_INITIAL"],
        "live": live,
        "perf": f"{perf:.2f}%",
        "bonus": epargne.get("EPARGNE_BONUS_USDT", 0.0),
        "cryptos_start": allowed,
        "cryptos_live": epargne.get("EPARGNE_CRYPTOS_LIVE", {}),
        "rules": epargne["EPARGNE_RULES"],
        "whale_tracking": epargne["WHALE_TRACKING"],
        "memoire_trades_count": len(memoire.get("trades", [])),
        "last_scan": epargne.get("EPARGNE_LAST_SCAN")
    }

# --- 4. Pour ton main.py (fichier 1 sur 6), ajoute SEULEMENT ces 4 lignes ---
# from epargne_v29 import get_epargne_status, muse_spark_decide
# @app.get("/epargne-status")
# def epargne_status():
#     return get_epargne_status()
# Dans ta boucle while True de main.py, après kittra_scout(), appelle muse_spark_decide()
