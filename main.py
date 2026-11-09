from fastapi import FastAPI
import os, json, time, hmac, hashlib, requests, datetime

app = FastAPI()
COFFRE_FILE = "coffre_tresor.json"
EPARGNE_FILE = "json_epargne.json"
EPARGNE_BONUS_FILE = "bonus_epargne_semaine.json"
MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/muse-spark-1.3")
OR_KEY = os.getenv("OPENROUTER_API_KEY")
MAX_TRADE = 2.0
MAX_TRADE_BYBIT = 5.0
SAFEPAL_ADDRESS = os.getenv("SAFEPAL_ADDRESS", "")
VRAI_PRINCIPAL = 9.30
VRAI_EPARGNE = 7.991064

# --- MODE = LE ROLE DE CE SERVICE ---
# Sur kittra-ninja-ultime : MODE = PRINCIPAL
# Sur kittraepagne : MODE = EPARGNE
MODE = os.getenv("MODE", "PRINCIPAL").upper()

def je_suis_principal():
    return MODE == "PRINCIPAL"

def je_suis_epargne():
    return MODE == "EPARGNE"

def get_tg():
    t = os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    c = os.getenv("TG_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
    return t, c

def send_tg(msg):
    try:
        t, c = get_tg()
        if not t or not c: return "NO TG"
        r = requests.post(f"https://api.telegram.org/bot{t}/sendMessage", json={"chat_id": c, "text": msg}, timeout=10)
        print(f"TG -> {r.status_code}")
        return f"OK {r.status_code}"
    except Exception as e:
        return str(e)

def load_coffre():
    try:
        if os.path.exists(COFFRE_FILE):
            return json.loads(open(COFFRE_FILE).read())
    except: pass
    return {"principal": VRAI_PRINCIPAL, "coffre": 0.0, "urgence": 0.0, "safepal": 0.0, "total_gains": 0.0, "last_bilan": "", "epargne_capital": VRAI_EPARGNE}

def save_coffre(d):
    open(COFFRE_FILE, "w").write(json.dumps(d))

def load_bonus_epargne():
    try:
        if os.path.exists(EPARGNE_BONUS_FILE):
            return json.loads(open(EPARGNE_BONUS_FILE).read())
    except: pass
    return {"bonus_semaine": 0.0, "nb_ventes": 0, "derniere_vente": "", "semaine_debut": datetime.date.today().isoformat()}

def save_bonus_epargne(d):
    open(EPARGNE_BONUS_FILE, "w").write(json.dumps(d))

def ajouter_bonus_epargne(profit_dollars, symbol, profit_pct):
    d = load_bonus_epargne()
    d["bonus_semaine"] = round(d["bonus_semaine"] + profit_dollars, 4)
    d["nb_ventes"] += 1
    d["derniere_vente"] = f"{symbol} +{profit_pct:.2f}% = +{profit_dollars:.4f}$ le {datetime.date.today().isoformat()}"
    save_bonus_epargne(d)
    return d

def bybit_sign(params):
    k = os.getenv("BYBIT_API_KEY"); s = os.getenv("BYBIT_API_SECRET")
    ts = str(int(time.time()*1000))
    sig = hmac.new(s.encode(), (ts+k+"5000"+params).encode(), hashlib.sha256).hexdigest()
    return {"X-BAPI-API-KEY": k, "X-BAPI-SIGN": sig, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": "5000"}

def get_balance_principal():
    total = 0.0
    vu = set()
    for account in ["UNIFIED", "SPOT", "FUND"]:
        try:
            p = f"accountType={account}"
            r = requests.get("https://api.bybit.com/v5/account/wallet-balance?"+p, headers=bybit_sign(p), timeout=10).json()
            lst = r.get("result", {}).get("list", [])
            if not lst: continue
            for coin in lst[0].get("coin", []):
                name = coin.get("coin", "")
                usd = float(coin.get("usdValue", 0) or 0)
                key = f"{name}_{usd}"
                if key in vu: continue
                vu.add(key)
                total += usd
        except Exception as e:
            print(f"BAL PRINCIPAL {account} ERR {e}")
    if total > 0:
        return round(total, 4)
    return VRAI_PRINCIPAL

def get_sub_uid():
    try:
        r = requests.get("https://api.bybit.com/v5/asset/transfer/query-sub-member-list", headers=bybit_sign(""), timeout=10).json()
        lst = r.get("result", {}).get("subMemberList", [])
        if not lst:
            return None
        for sub in lst:
            name = str(sub.get("subMemberName", "")).upper()
            nick = str(sub.get("nickname", "")).upper()
            user = str(sub.get("username", "")).upper()
            if "KITTRA" in name or "KITTRA" in nick or "KITTRA" in user or "EPAGNE" in name or "EPAGNE" in nick or "EPARGNE" in name or "EPARGNE" in nick:
                return sub.get("uid")
        if len(lst) == 1:
            return lst[0].get("uid")
        return lst[0].get("uid")
    except Exception as e:
        print(f"UID ERR {e}")
        return None

def get_balance_epargne():
    uid = get_sub_uid()
    if not uid:
        try:
            if os.path.exists(EPARGNE_FILE):
                d = json.loads(open(EPARGNE_FILE).read())
                return float(d.get("EPARGNE_CAPITAL_LIVE", VRAI_EPARGNE))
        except: pass
        return VRAI_EPARGNE
    total = 0.0
    vu = set()
    for account in ["UNIFIED", "SPOT", "FUND"]:
        try:
            p = f"accountType={account}&memberId={uid}"
            r = requests.get("https://api.bybit.com/v5/account/wallet-balance?"+p, headers=bybit_sign(p), timeout=10).json()
            lst = r.get("result", {}).get("list", [])
            if not lst: continue
            for coin in lst[0].get("coin", []):
                name = coin.get("coin", "")
                usd = float(coin.get("usdValue", 0) or 0)
                key = f"{name}_{usd}"
                if key in vu: continue
                vu.add(key)
                total += usd
        except Exception as e:
            print(f"BAL EPARGNE {account} ERR {e}")
    if total > 0:
        return round(total, 4)
    return VRAI_EPARGNE

def get_pair_info(symbol):
    try:
        r = requests.get(f"https://api.bybit.com/v5/market/instruments-info?category=spot&symbol={symbol}", timeout=10).json()
        info = r["result"]["list"][0]
        lot = info.get("lotSizeFilter", {})
        return {"min_qty": float(lot.get("minOrderQty", 0)), "qty_step": float(lot.get("qtyStep", 0.001)), "min_notional": float(info.get("minOrderAmt", 5.0)), "ok": True}
    except: return {"min_qty": 0, "qty_step": 0.001, "min_notional": 5.0, "ok": False}

def get_price(symbol):
    try:
        r = requests.get(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}", timeout=10).json()
        return float(r["result"]["list"][0]["lastPrice"])
    except: return 0.0

def get_change_24h(symbol):
    try:
        r = requests.get(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}", timeout=10).json()
        return float(r["result"]["list"][0].get("price24hPcnt", 0)) * 100
    except: return 0.0

def liste_auto_principal(capital):
    base = ["GIGAUSDT", "BNBUSDT", "SOLUSDT"]
    if capital >= 15: base += ["DOGEUSDT", "PEPEUSDT"]
    if capital >= 30: base += ["SHIBUSDT", "ZECUSDT", "ONDOUSDT", "QNTUSDT", "ETHUSDT"]
    return base

def liste_auto_epargne(capital):
    base = ["BNBUSDT", "SOLUSDT", "DOGEUSDT"]
    if capital >= 10: base += ["PEPEUSDT", "CRXUSDT"]
    if capital >= 20: base += ["SHIBUSDT", "ZECUSDT", "ONDOUSDT", "QNTUSDT", "ETHUSDT"]
    return base

# --- C AVANT B : Check avant Buy ---
def check_C_avant_B(symbol, balance, voulu):
    info = get_pair_info(symbol); price = get_price(symbol)
    if price <= 0: return {"ok": False, "raison": f"{symbol} prix introuvable, je passe au suivant"}
    min_notional = info["min_notional"]
    if voulu < min_notional:
        if min_notional <= balance and min_notional <= 10:
            voulu = min_notional
        else:
            return {"ok": False, "raison": f"{symbol} demande {min_notional}$, j'ai {balance:.2f}$, je passe au suivant", "info": info, "price": price}
    frais = voulu * 0.001 + 0.01
    if balance < voulu + frais:
        return {"ok": False, "raison": f"{symbol} besoin {voulu+frais:.2f}$ avec frais, j'ai {balance:.2f}$, je passe au suivant", "info": info, "price": price}
    qty_raw = voulu / price
    step = info["qty_step"] if info["qty_step"] > 0 else 0.001
    qty = int(qty_raw / step) * step
    qty = round(qty, 8)
    if qty <= 0: return {"ok": False, "raison": f"{symbol} qty trop petite, je passe au suivant"}
    return {"ok": True, "voulu": voulu, "qty": qty, "price": price, "info": info, "frais": frais}

def place_order_reel(symbol, qty, side, is_epargne=False):
    try:
        ts = str(int(time.time()*1000))
        body = {"category": "spot", "symbol": symbol, "side": side, "orderType": "Market", "qty": str(qty)}
        if is_epargne:
            uid = get_sub_uid()
            if uid: body["subMemberId"] = str(uid)
        payload = json.dumps(body)
        k = os.getenv("BYBIT_API_KEY"); s = os.getenv("BYBIT_API_SECRET")
        sig = hmac.new(s.encode(), (ts+k+"5000"+payload).encode(), hashlib.sha256).hexdigest()
        h = {"X-BAPI-API-KEY": k, "X-BAPI-SIGN": sig, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": "5000", "Content-Type": "application/json"}
        r = requests.post("https://api.bybit.com/v5/order/create", headers=h, data=payload, timeout=15).json()
        print(f"ORDER {side} {symbol} -> {r}")
        return r
    except Exception as e: return {"retMsg": f"EXC {e}"}

# --- CERVEAU = Muse Spark 1.3 - Les 2 l'utilisent ---
def cerveau(prompt):
    if not OR_KEY: return "DECISION: HOLD"
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {OR_KEY}"}, json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200}, timeout=20).json()
        return r["choices"][0]["message"]["content"]
    except Exception as e: return f"ERR {e}"

def transfert_safepal(montant):
    if not SAFEPAL_ADDRESS:
        return {"ok": False, "raison": "SAFEPAL_ADDRESS pas configure, je garde en coffre"}
    if montant < 5:
        return {"ok": False, "raison": f"SafePal {montant}$ trop petit, min Bybit 5$, j'accumule"}
    try:
        ts = str(int(time.time()*1000))
        body = {"coin": "USDT", "chain": "BSC", "address": SAFEPAL_ADDRESS, "amount": str(montant)}
        payload = json.dumps(body)
        k = os.getenv("BYBIT_API_KEY"); s = os.getenv("BYBIT_API_SECRET")
        sig = hmac.new(s.encode(), (ts+k+"5000"+payload).encode(), hashlib.sha256).hexdigest()
        h = {"X-BAPI-API-KEY": k, "X-BAPI-SIGN": sig, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": "5000", "Content-Type": "application/json"}
        r = requests.post("https://api.bybit.com/v5/asset/withdraw/create", headers=h, data=payload, timeout=15).json()
        return r
    except Exception as e: return {"retMsg": f"EXC {e}"}

# --- MEMO VENTE : Ne pas revendre 2 fois le meme palier ---
VENTE_PRINCIPAL_MEMO = {}
EPARGNE_VENTE_MEMO = {}
PRINCIPAL_SELL_LADDER = [{"profit": 0.5, "pct": 30}, {"profit": 1.5, "pct": 20}, {"profit": 2.5, "pct": 15}, {"profit": 3, "pct": 10}]
EPARGNE_SELL_LADDER = [{"profit": 4, "pct": 25}, {"profit": 10, "pct": 25}, {"profit": 26, "pct": 50}]

@app.get("/")
def home():
    bal_p = get_balance_principal()
    bal_e = get_balance_epargne()
    bonus = load_bonus_epargne()
    return {"mode": MODE, "principal": bal_p, "epargne": bal_e, "total_2_comptes": round(bal_p + bal_e, 4), "wallet_bonus_epargne_semaine": bonus["bonus_semaine"], "nb_ventes_epargne_semaine": bonus["nb_ventes"], "msg": "KITTRA V38 - MODE, Les 2 utilisent le cerveau, C avant B, Vente qui monte meme si je dors, Bonus Epargne dans son wallet perso, Repartition Dimanche"}

@app.get("/ping")
def ping():
    bal_p = get_balance_principal()
    bal_e = get_balance_epargne()
    uid = get_sub_uid()
    return {"ok": True, "mode": MODE, "uid_trouve": bool(uid), "uid": uid, "principal": bal_p, "epargne": bal_e, "total": round(bal_p + bal_e, 4), "bonus_epargne_semaine": load_bonus_epargne()}

# --- TRADE MOLO PRINCIPAL : Cerveau + C avant B ---
@app.get("/scan-vrai")
def scan_vrai():
    if not je_suis_principal():
        return {"ok": False, "raison": "Je suis KITTRA EPARGNE, je ne trade PAS le Principal. Va sur kittra-ninja-ultime."}
    bal_p = get_balance_principal()
    candidats = liste_auto_principal(bal_p)
    out = []
    for sym in candidats:
        chute = get_change_24h(sym)
        price = get_price(sym)
        decision = cerveau(f"Principal {sym} prix {price} chute 24h {chute:.2f}% solde {bal_p}$. Tu es le cerveau Principal. Dis-moi si j'achete maintenant ? Reponds BUY si oui, HOLD ou SELL si non, avec 1 phrase de raison. Dis-moi aussi si cette crypto monte tres souvent dans la semaine ou si elle est en train de mourir.")
        if "BUY" not in decision.upper():
            out.append({"pair": sym, "skip": f"Cerveau Principal dit {decision[:150]}"})
            continue
        info = get_pair_info(sym)
        voulu = info["min_notional"]
        check = check_C_avant_B(sym, bal_p, voulu)
        if not check["ok"]:
            out.append({"pair": sym, "skip": check["raison"]})
            continue
        order = place_order_reel(sym, check["qty"], "Buy", False)
        if order.get("retCode") == 0:
            send_tg(f"✅ VRAI ACHAT Principal {sym} {check['voulu']}$ - Cerveau : {decision[:150]} - C avant B OK : solde {bal_p}$ >= {check['voulu'] + check['frais']:.2f}$ avec frais, minimum Bybit {info['min_notional']}$")
            out.append({"pair": sym, "achete": check["voulu"], "price": price, "cerveau": decision[:150]})
            break
        else:
            out.append({"pair": sym, "refuse": order.get("retMsg")})
            continue
    return {"balance_principal": bal_p, "liste": candidats, "resultats": out}

# --- TRADE EPARGNE : Cerveau + Chute = Signal + C avant B ---
@app.get("/scan-epargne-vrai")
def scan_epargne_vrai():
    if not je_suis_epargne():
        return {"ok": False, "raison": "Je suis KITTRA Principal, je ne trade PAS l'Epargne. Va sur kittraepagne."}
    bal = get_balance_epargne()
    candidats = liste_auto_epargne(bal)
    out = []
    for sym in candidats:
        chute = get_change_24h(sym)
        price = get_price(sym)
        if chute > -5:
            out.append({"pair": sym, "chute": chute, "skip": f"{sym} chute {chute:.2f}% pas assez, j'attends -5% pour demander au cerveau"})
            continue
        decision = cerveau(f"Epargne {sym} prix {price} chute 24h {chute:.2f}% solde {bal}$. Tu es le cerveau Epargne. Dis-moi : Est-ce que cette crypto chute puis remonte vite en boucle dans la semaine ? Ou est-ce qu'elle ne fait que chuter et ne remonte jamais ? Ou est-ce qu'elle est en train de mourir ? Reponds par : ACHETER_CHUTE_REMONTEE_VITE si elle chute puis remonte vite, ou NE_PAS_ACHETER_MOURIR si elle ne remonte jamais ou si elle meurt. Donne aussi 1 phrase de raison.")
        print(f"CERVEAU EPARGNE {sym} -> {decision}")
        texte = decision.upper()
        if "NE_PAS_ACHETER" in texte or "MOURIR" in texte or "MORT" in texte or "NE_REMONTE_JAMAIS" in texte or "CHUTE_SANS_REMONTEE" in texte or "DANGER" in texte:
            out.append({"pair": sym, "chute": chute, "skip": f"Cerveau Epargne refuse {sym} : {decision[:150]} - Il ne fait que chuter ou il est en train de mourir, je protege mon Epargne, je passe au suivant"})
            continue
        if "ACHETER" not in texte and "REMONT" not in texte and "BUY" not in texte:
            out.append({"pair": sym, "chute": chute, "skip": f"Cerveau Epargne pas sur pour {sym} : {decision[:150]} - Je ne buy pas, je passe au suivant"})
            continue
        info = get_pair_info(sym)
        min_bybit = info["min_notional"]
        voulu = min_bybit
        if min_bybit <= 1.0:
            voulu = 1.5
        check = check_C_avant_B(sym, bal, voulu)
        if not check["ok"]:
            out.append({"pair": sym, "chute": chute, "skip": check["raison"]})
            continue
        order = place_order_reel(sym, check["qty"], "Buy", True)
        if order.get("retCode") == 0:
            send_tg(f"✅ VRAI ACHAT Epargne {sym} chute {chute:.2f}% - J'ai achete {check['voulu']}$ - Cerveau : {decision[:150]} - C avant B OK : solde {bal}$ >= {check['voulu'] + check['frais']:.2f}$ avec frais, minimum Bybit {min_bybit}$")
            out.append({"pair": sym, "achete": check["voulu"], "chute": chute, "min_bybit": min_bybit, "frais": check["frais"], "cerveau": decision[:150]})
            break
        else:
            out.append({"pair": sym, "refuse": order.get("retMsg")})
            continue
    return {"balance_epargne": bal, "liste": candidats, "resultats": out}

# --- VENTE MOLO PRINCIPAL : A partir de +0.5% qui monte, meme si je dors ---
@app.get("/vente-principal")
def vente_principal_route(symbol: str = "GIGAUSDT", qty: float = 10, prix_achat: float = 0.01):
    if not je_suis_principal():
        return {"ok": False, "raison": "Je suis KITTRA EPARGNE, je ne vends PAS le Principal."}
    prix_actuel = get_price(symbol)
    if prix_actuel <= prix_achat:
        return {"ok": False, "raison": f"MOLO : Prix actuel {prix_actuel}$ <= Prix achat {prix_achat}$, je ne vends PAS a perte"}
    profit_pct = (prix_actuel - prix_achat) / prix_achat * 100
    if profit_pct < 0.5:
        return {"msg": f"MOLO {symbol} profit {profit_pct:.2f}% < 0.5%, je ne vends pas, j'attends"}
    pct_a_vendre = 0
    paliers = []
    for p in PRINCIPAL_SELL_LADDER:
        key = f"{symbol}_{p['profit']}"
        if profit_pct >= p["profit"] and key not in VENTE_PRINCIPAL_MEMO:
            pct_a_vendre += p["pct"]
            paliers.append(p)
            VENTE_PRINCIPAL_MEMO[key] = True
    if pct_a_vendre == 0:
        return {"msg": f"MOLO {symbol} profit {profit_pct:.2f}% - Tous les paliers deja vendus, j'attends un nouveau trade"}
    qty_sell = round(qty * pct_a_vendre / 100, 8)
    order = place_order_reel(symbol, qty_sell, "Sell", False)
    if order.get("retCode") == 0:
        send_tg(f"💰 VENTE MOLO Principal {symbol} {qty_sell} = {pct_a_vendre}% - Profit +{profit_pct:.2f}% - Paliers : {paliers} - Meme si je me suis reveille tard, je vends a partir de +0.5%")
        return {"vente": pct_a_vendre, "qty": qty_sell, "profit": profit_pct, "paliers": paliers}
    for p in paliers:
        VENTE_PRINCIPAL_MEMO.pop(f"{symbol}_{p['profit']}", None)
    return {"refuse": order}

# --- VENTE EPARGNE : A partir de +4% qui monte + Bonus dans son wallet perso ---
@app.get("/vente-epargne")
def vente_epargne_route(symbol: str = "BNBUSDT", qty: float = 0.01, profit_pct: float = 5.0, prix_achat: float = 0.0):
    if not je_suis_epargne():
        return {"ok": False, "raison": "Je suis KITTRA Principal, je ne vends PAS l'Epargne."}
    if profit_pct < 4:
        return {"msg": f"Epargne {symbol} profit {profit_pct:.2f}% < 4%, je ne vends pas, j'attends la remontee"}
    pct_a_vendre = 0
    paliers = []
    for p in EPARGNE_SELL_LADDER:
        key = f"{symbol}_{p['profit']}"
        if profit_pct >= p["profit"] and key not in EPARGNE_VENTE_MEMO:
            pct_a_vendre += p["pct"]
            paliers.append(p)
            EPARGNE_VENTE_MEMO[key] = True
    if pct_a_vendre == 0:
        return {"msg": f"Epargne {symbol} profit {profit_pct:.2f}% - Tous les paliers deja vendus, j'attends un nouveau trade"}
    qty_sell = round(qty * pct_a_vendre / 100, 8)
    order = place_order_reel(symbol, qty_sell, "Sell", True)
    if order.get("retCode") == 0:
        prix_actuel = get_price(symbol)
        if prix_achat > 0:
            profit_dollars = round(qty_sell * prix_actuel - qty_sell * prix_achat, 4)
        else:
            profit_dollars = round(qty_sell * prix_actuel * profit_pct / 100, 4)
        if profit_dollars > 0:
            bonus = ajouter_bonus_epargne(profit_dollars, symbol, profit_pct)
            send_tg(f"💰 VENTE Epargne {symbol} {qty_sell} = {pct_a_vendre}% - Profit +{profit_pct:.2f}% - Paliers : {paliers} - Bonus +{profit_dollars}$ -> Wallet Bonus Epargne perso = {bonus['bonus_semaine']}$ total semaine ({bonus['nb_ventes']} ventes). Dimanche je fais la repartition.")
        else:
            send_tg(f"💰 VENTE Epargne {symbol} {qty_sell} = {pct_a_vendre}% - Profit +{profit_pct:.2f}% - Paliers : {paliers}")
        return {"vente": pct_a_vendre, "qty": qty_sell, "profit": profit_pct, "paliers": paliers, "bonus_dollars": profit_dollars}
    for p in paliers:
        EPARGNE_VENTE_MEMO.pop(f"{symbol}_{p['profit']}", None)
    return {"refuse": order}

# --- BILAN HEBDO DIMANCHE : Prendre les bonus de la semaine, Repartition, Recommencer le cycle ---
@app.get("/bilan-hebdo-vrai")
def bilan_hebdo_vrai():
    bonus_data = load_bonus_epargne()
    bonus_semaine = bonus_data["bonus_semaine"]
    if bonus_semaine <= 0:
        return {"msg": "Pas de bonus Epargne cette semaine, Wallet Bonus = 0, je recommence le cycle."}
    reinvest = round(bonus_semaine * 0.50, 4)
    urgence = round(bonus_semaine * 0.20, 4)
    safepal = round(bonus_semaine * 0.15, 4)
    coffre_part = round(bonus_semaine * 0.15, 4)
    reinvest_principal = round(reinvest * 0.70, 4)
    reinvest_epargne = round(reinvest * 0.30, 4)
    coffre = load_coffre()
    coffre["urgence"] = round(coffre.get("urgence", 0) + urgence, 4)
    coffre["coffre"] = round(coffre.get("coffre", 0) + coffre_part, 4)
    coffre["total_gains"] = round(coffre.get("total_gains", 0) + bonus_semaine, 4)
    coffre["last_bilan"] = datetime.date.today().isoformat()
    save_coffre(coffre)
    if safepal >= 5:
        res = transfert_safepal(safepal)
        safepal_msg = f"Transfert SafePal {safepal}$ : {res}"
    else:
        coffre["safepal"] = round(coffre.get("safepal", 0) + safepal, 4)
        save_coffre(coffre)
        safepal_msg = f"SafePal {safepal}$ < 5$ Bybit, j'accumule dans le coffre jusqu'a 5$. Coffre SafePal = {coffre['safepal']}$"
    save_bonus_epargne({"bonus_semaine": 0.0, "nb_ventes": 0, "derniere_vente": "", "semaine_debut": datetime.date.today().isoformat()})
    msg = f"📊 BILAN HEBDO DIMANCHE EPARGNE\nBonus semaine : {bonus_semaine}$ ({bonus_data['nb_ventes']} ventes)\nREINVEST 50% = {reinvest}$ (Principal {reinvest_principal}$ + Epargne {reinvest_epargne}$)\nURGENCE 20% = {urgence}$\nSAFEPAL 15% = {safepal}$ - {safepal_msg}\nCOFFRE 15% = {coffre_part}$\nWallet Bonus remis a 0, nouveau cycle Lundi."
    send_tg(msg)
    return {"bonus_semaine": bonus_semaine, "reinvest": reinvest, "urgence": urgence, "safepal": safepal, "coffre": coffre_part, "msg": msg}

@app.get("/profit")
def profit(m: float = 1.0):
    p = round(m * 0.5, 4); u = round(m * 0.2, 4); s = round(m * 0.15, 4); c = round(m * 0.15, 4)
    return {"profit": m, "REINVEST_50": p, "URGENCE_20": u, "SAFEPAL_15": s, "COFFRE_15": c}
