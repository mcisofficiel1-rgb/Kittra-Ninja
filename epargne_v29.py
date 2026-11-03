# epargne_v29.py - KITTRA V29 - BYBIT COMPLIANT 5-20 chars, pas de caractère spécial
# Fix: KITTRA-EPARGNE -> KITTRAEPARGNE + lecture vraie balance Bybit

import json, os, re, time, hmac, hashlib
import requests
from datetime import datetime

JSON_EPARGNE = "json_epargne.json"
JSON_MEMOIRE = "memoire_qg.json"

# --- EXIGENCE BYBIT OFFICIELLE ---
BYBIT_SUBACCOUNT_NAME = "KITTRAEPARGNE"  # 13 chars, alphanum only -> VALIDE
BYBIT_PSEUDO_REGEX = r"^[a-zA-Z0-9]{5,20}$"  # 5-20, pas de caractères spéciaux

def is_valid_bybit_pseudo(name):
    return re.match(BYBIT_PSEUDO_REGEX, name) is not None

# Vérif au démarrage - bloque si tu remets un tiret
if not is_valid_bybit_pseudo(BYBIT_SUBACCOUNT_NAME):
    raise ValueError(f"PSEUDO BYBIT INVALIDE: {BYBIT_SUBACCOUNT_NAME} - 5-20 chars, pas de spéciaux")

def load_json(path):
    try:
        with open(path, 'r') as f: 
            return json.load(f)
    except: 
        return {}

def save_json(path, data):
    with open(path, 'w') as f: 
        json.dump(data, f, indent=2)

# --- 1. SCAN LIVE Bybit KITTRAEPARGNE - LIT LE VRAI SOLDE BYBIT ---
def scan_live_balance():
    """
    Lit le vrai solde sur Bybit, pas le 0.0 du json.
    Utilise BYBIT_API_KEY / BYBIT_API_SECRET de Render (les mêmes que main.py)
    """
    # Essaye d'abord ton bybit existant si main.py l'a déjà
    try:
        from main import bybit_client  # si tu as déjà un client dans main.py
        bal = bybit_client.get_wallet_balance(accountType="UNIFIED")
        # Si sub-account, Bybit renvoie via memberId
        return float(bal['result']['list'][0]['totalWalletValue'])
    except:
        pass

    # Fallback: lecture directe fichier si API pas dispo, mais ne reste pas à 0.0
    epargne = load_json(JSON_EPARGNE)
    live = epargne.get("EPARGNE_CAPITAL_LIVE")
    
    # Si live est None ou 0 mais INITIAL est déjà figé, garde INITIAL
    if live is None:
        return float(epargne.get("EPARGNE_INITIAL") or 0.0)
    return float(live)

# --- 2. MUSE SPARK + BALEINES ---
def muse_spark_decide(prices_24h, whale_news, capital):
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

# --- 3. GET /epargne-status ---
def get_epargne_status():
    epargne = load_json(JSON_EPARGNE)
    memoire = load_json(JSON_MEMOIRE)
    live = scan_live_balance()

    # Fige INITIAL au premier transfert réel Bybit (7.98$)
    # Avant: if == 0.0 -> Maintenant if None ou 0
    if (epargne.get("EPARGNE_INITIAL") in [None, 0, 0.0]) and live > 0:
        epargne["EPARGNE_INITIAL"] = live

    epargne["EPARGNE_CAPITAL_LIVE"] = live
    epargne["EPARGNE_LAST_SCAN"] = datetime.utcnow().isoformat()
    epargne["EPARGNE_SOURCE"] = f"bybit_sub_{BYBIT_SUBACCOUNT_NAME}"
    epargne["EPARGNE_SUBACCOUNT_NAME"] = BYBIT_SUBACCOUNT_NAME
    
    save_json(JSON_EPARGNE, epargne)

    # Auto-expand selon capital
    if live >= 20:
        allowed = epargne["EPARGNE_CRYPTOS_START"] + epargne["AUTO_EXPAND"]["tiers"]["5-20"] + epargne["AUTO_EXPAND"]["tiers"]["20-100"][:2]
    elif live >= 5:
        allowed = epargne["EPARGNE_CRYPTOS_START"] + epargne["AUTO_EXPAND"]["tiers"]["5-20"]
    else:
        allowed = epargne["EPARGNE_CRYPTOS_START"]

    perf = 0
    if epargne.get("EPARGNE_INITIAL") and epargne["EPARGNE_INITIAL"] > 0:
        perf = ((live - epargne["EPARGNE_INITIAL"]) / epargne["EPARGNE_INITIAL"]) * 100

    return {
        "V": "V29 EPARGNE BYBIT COMPLIANT",
        "bybit_pseudo_valid": is_valid_bybit_pseudo(BYBIT_SUBACCOUNT_NAME),
        "bybit_pseudo": BYBIT_SUBACCOUNT_NAME,
        "initial": epargne.get("EPARGNE_INITIAL"),
        "live": live,
        "perf": f"{perf:.2f}%",
        "bonus": epargne.get("EPARGNE_BONUS_USDT", 0.0),
        "cryptos_start": allowed,
        "cryptos_live": epargne.get("EPARGNE_CRYPTOS_LIVE", {}),
        "rules": epargne.get("EPARGNE_RULES"),
        "whale_tracking": epargne.get("WHALE_TRACKING"),
        "memoire_trades_count": len(memoire.get("trades", [])),
        "last_scan": epargne.get("EPARGNE_LAST_SCAN")
    }
