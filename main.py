from fastapi import FastAPI
import os, json, time, hmac, hashlib, requests, datetime

app = FastAPI()
COFFRE_FILE = "coffre_tresor.json"
EPARGNE_FILE = "json_epargne.json"
MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/muse-spark-1.3")
OR_KEY = os.getenv("OPENROUTER_API_KEY")
MAX_TRADE = 2.0
MAX_TRADE_BYBIT = 5.0
SAFEPAL_ADDRESS = os.getenv("SAFEPAL_ADDRESS", "")

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
    return {"principal": 10.91, "coffre": 0.0, "urgence": 0.0, "safepal": 0.0, "total_gains": 0.0, "last_bilan": "", "epargne_capital": 7.9872}

def save_coffre(d):
    open(COFFRE_FILE, "w").write(json.dumps(d))

def bybit_sign(params):
    k = os.getenv("BYBIT_API_KEY"); s = os.getenv("BYBIT_API_SECRET")
    ts = str(int(time.time()*1000))
    sig = hmac.new(s.encode(), (ts+k+"5000"+params).encode(), hashlib.sha256).hexdigest()
    return {"X-BAPI-API-KEY": k, "X-BAPI-SIGN": sig, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": "5000"}

def get_balance_principal():
    try:
        p = "accountType=UNIFIED"
        r = requests.get("https://api.bybit.com/v5/account/wallet-balance?"+p, headers=bybit_sign(p), timeout=10).json()
        return float(r["result"]["list"][0]["totalEquity"])
    except: return 10.91

def get_sub_uid():
    try:
        r = requests.get("https://api.bybit.com/v5/asset/transfer/query-sub-member-list", headers=bybit_sign(""), timeout=10).json()
        lst = r.get("result", {}).get("subMemberList", [])
        for sub in lst:
            if sub.get("subMemberName") == "KITTRAEPARGNE": return sub.get("uid")
        if lst: return lst[0].get("uid")
    except Exception as e: print(f"UID ERR {e}")
    return None

def get_balance_epargne():
    uid = get_sub_uid()
    if not uid:
        try:
            if os.path.exists(EPARGNE_FILE):
                d = json.loads(open(EPARGNE_FILE).read())
                return float(d.get("EPARGNE_CAPITAL_LIVE", 7.9872))
        except: pass
        return 7.9872
    try:
        p = f"accountType=UNIFIED&memberId={uid}"
        r = requests.get("https://api.bybit.com/v5/account/wallet-balance?"+p, headers=bybit_sign(p), timeout=10).json()
        return float(r["result"]["list"][0]["totalEquity"])
    except: return 7.9872

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

def check_C_avant_B(symbol, balance, voulu):
    info = get_pair_info(symbol); price = get_price(symbol)
    if price <= 0: return {"ok": False, "raison": f"{symbol} prix introuvable, je passe au suivant"}
    min_notional = info["min_notional"]
    if voulu < min_notional:
        if min_notional <= balance and min_notional <= MAX_TRADE_BYBIT:
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
        body = {"coin": "USDT", "chain": "BSC", "address": SAFEPAL_ADDRESS, "amount": str(montant), "timestamp": ts}
        payload = json.dumps(body)
        k = os.getenv("BYBIT_API_KEY"); s = os.getenv("BYBIT_API_SECRET")
        sig = hmac.new(s.encode(), (ts+k+"5000"+payload).encode(), hashlib.sha256).hexdigest()
        h = {"X-BAPI-API-KEY": k, "X-BAPI-SIGN": sig, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": "5000", "Content-Type": "application/json"}
        r = requests.post("https://api.bybit.com/v5/asset/withdraw/create", headers=h, data=payload, timeout=15).json()
        return r
    except Exception as e: return {"ok": False, "raison": str(e)}

# --- MEMOIRE VENTE PRINCIPAL ---
VENTE_PRINCIPAL_MEMO = {}
PRINCIPAL_LADDER = [{"profit": 0.5, "pct": 30}, {"profit": 1.5, "pct": 20}, {"profit": 2.5, "pct": 15}, {"profit": 3.0, "pct": 10}]
EPARGNE_BUY_LADDER = [{"chute": -5, "montant": 0.5}, {"chute": -8, "montant": 1.0}, {"chute": -12, "montant": 1.5}]
EPARGNE_SELL_LADDER = [{"profit": 4, "pct": 25}, {"profit": 10, "pct": 25}, {"profit": 26, "pct": 50}]

@app.on_event("startup")
def on_start():
    cap = get_balance_principal(); ep = get_balance_epargne()
    send_tg(f"🔥 KITTRA V34 FINAL DEMARRE !\nPrincipal ULTIME: {cap}$ Liste: {liste_auto_principal(cap)}\nEpargne: {ep}$ Liste: {liste_auto_epargne(ep)}\nSysteme: C avant B + Passage autonome + MOLO Principal + Dip Epargne + Bilan Hebdo + SafePal")

@app.get("/")
def home():
    return {"v": "V34 FINAL", "principal": get_balance_principal(), "epargne": get_balance_epargne(), "liste_principal": liste_auto_principal(get_balance_principal()), "liste_epargne": liste_auto_epargne(get_balance_epargne()), "coffre": load_coffre()}

# --- ACHAT PRINCIPAL ---
@app.get("/scan-vrai")
def scan_vrai():
    bal_p = get_balance_principal()
    candidats = liste_auto_principal(bal_p)
    out = []
    for sym in candidats:
        check = check_C_avant_B(sym, bal_p, MAX_TRADE)
        if not check["ok"]:
            out.append({"pair": sym, "skip": check["raison"]})
            continue
        order = place_order_reel(sym, check["qty"], "Buy", False)
        if order.get("retCode") == 0:
            send_tg(f"✅ VRAI ACHAT Principal ULTIME {sym} {check['qty']} = {check['voulu']}$ a {check['price']}$")
            out.append({"pair": sym, "achete": check["voulu"], "prix_achat": check["price"]})
            break
        else:
            out.append({"pair": sym, "refuse": order.get("retMsg")})
            continue
    return {"balance_principal": bal_p, "liste": candidats, "resultats": out}

# --- ACHAT EPARGNE : ACHETE LA BAISSE -5 / -8 / -12 ---
@app.get("/scan-epargne-vrai")
def scan_epargne_vrai():
    bal = get_balance_epargne()
    candidats = liste_auto_epargne(bal)
    out = []
    for sym in candidats:
        chute = get_change_24h(sym)
        palier = None
        for p in EPARGNE_BUY_LADDER:
            if chute <= p["chute"]:
                palier = p
                break
        if not palier:
            out.append({"pair": sym, "chute": chute, "skip": f"{sym} chute {chute:.2f}% pas assez, j'attends -5% / -8% / -12%"})
            continue
        check = check_C_avant_B(sym, bal, MAX_TRADE)
        if not check["ok"]:
            out.append({"pair": sym, "skip": check["raison"]})
            continue
        order = place_order_reel(sym, check["qty"], "Buy", True)
        if order.get("retCode") == 0:
            send_tg(f"✅ VRAI ACHAT Epargne {sym} chute {chute:.2f}% palier {palier['chute']}% - {check['qty']} = {check['voulu']}$")
            out.append({"pair": sym, "achete": check["voulu"], "chute": chute})
            break
        else:
            out.append({"pair": sym, "refuse": order.get("retMsg")})
            continue
    return {"balance_epargne": bal, "liste": candidats, "resultats": out}

# --- VENTE PRINCIPAL MOLO : BASE SUR PRIX D'ACHAT ---
@app.get("/vente-principal")
def vente_principal_route(symbol: str = "GIGAUSDT", qty: float = 10, prix_achat: float = 0.01):
    prix_actuel = get_price(symbol)
    if prix_actuel <= 0: return {"ok": False, "raison": f"{symbol} prix introuvable"}
    if prix_actuel <= prix_achat:
        return {"ok": False, "raison": f"{symbol} Prix actuel {prix_actuel}$ <= Prix achat {prix_achat}$, je ne vends PAS a perte"}
    profit_pct = (prix_actuel - prix_achat) / prix_achat * 100
    palier = None
    for p in PRINCIPAL_LADDER:
        key = f"{symbol}_{p['profit']}"
        if profit_pct >= p["profit"] and key not in VENTE_PRINCIPAL_MEMO:
            palier = p
            break
    if not palier:
        return {"ok": False, "raison": f"{symbol} Profit {profit_pct:.2f}% - Aucun nouveau palier, j'attends +0.5% / +1.5% / +2.5% / +3%"}
    qty_sell = round(qty * palier["pct"] / 100, 8)
    info = get_pair_info(symbol)
    if qty_sell < info["min_qty"]:
        return {"ok": False, "raison": f"{symbol} Qty {qty_sell} < min Bybit {info['min_qty']}"}
    order = place_order_reel(symbol, qty_sell, "Sell", False)
    if order.get("retCode") == 0:
        VENTE_PRINCIPAL_MEMO[f"{symbol}_{palier['profit']}"] = True
        send_tg(f"💰 MOLO VENTE Principal {symbol} Profit +{profit_pct:.2f}% Palier +{palier['profit']}% - Vendu {palier['pct']}% = {qty_sell} - Achat {prix_achat}$ -> Vente {prix_actuel}$")
        return {"vente": palier, "qty": qty_sell, "profit": profit_pct}
    return {"refuse": order}

# --- VENTE EPARGNE : VEND LA MONTEE +4 / +10 / +26 ---
@app.get("/vente-epargne")
def vente_epargne_route(symbol: str = "BNBUSDT", qty: float = 0.01, profit_pct: float = 5.0):
    if profit_pct >= 26: pct = 50
    elif profit_pct >= 10: pct = 25
    elif profit_pct >= 4: pct = 25
    else: return {"msg": f"Epargne profit {profit_pct}% < 4%, je ne vends pas, j'attends la remontee"}
    qty_sell = round(qty * pct / 100, 8)
    order = place_order_reel(symbol, qty_sell, "Sell", True)
    if order.get("retCode") == 0:
        send_tg(f"💰 VENTE Epargne {symbol} {qty_sell} = {pct}% - Profit marche +{profit_pct}%")
        return {"vente": pct, "qty": qty_sell}
    return {"refuse": order}

@app.get("/bilan-hebdo-vrai")
def bilan_hebdo_vrai():
    c = load_coffre()
    gain = c["total_gains"]
    if gain <= 0: return {"msg": "Pas de gains cette semaine", "coffre": c}
    total = gain
    reinvest = total * 0.5
    reste = total * 0.5
    urgence = reste * 0.4
    safepal_part = reste * 0.3
    coffre_part = reste * 0.3
    principal_part = reinvest * 0.7
    epargne_part = reinvest * 0.3
    c["urgence"] += urgence
    c["safepal"] += safepal_part
    c["coffre"] += coffre_part
    c["principal"] += principal_part
    c["total_gains"] = 0
    c["last_bilan"] = str(datetime.datetime.now())
    save_coffre(c)
    res_safepal = transfert_safepal(safepal_part)
    msg = f"📊 BILAN HEBDO VRAI +{total:.2f}$\n1er REINVEST 50% = {reinvest:.2f}$ -> Principal +{principal_part:.2f}$ / Epargne +{epargne_part:.2f}$\n2e URGENCE 20% = {urgence:.2f}$\n3e SAFEPAL 15% = {safepal_part:.2f}$ -> {res_safepal}\n4e COFFRE 15% = {coffre_part:.2f}$\nBONUS 50% applique"
    send_tg(msg)
    return {"bilan": total, "reinvest_principal": principal_part, "reinvest_epargne": epargne_part, "urgence": urgence, "safepal": safepal_part, "coffre": coffre_part, "safepal_result": res_safepal, "nouveau_coffre": c}

@app.get("/profit")
def profit(m: float, s: str = "TRADE"):
    c = load_coffre(); c["coffre"] += m; c["total_gains"] += m; save_coffre(c)
    send_tg(f"💰 PROFIT {s} +{m}$ - Coffre {c['coffre']}$ - Total gains semaine {c['total_gains']}$")
    return {"ok": True, "coffre": c}

@app.get("/ping")
def ping():
    return {"ok": True, "v": "V34", "uid": bool(get_sub_uid()), "safepal_config": bool(SAFEPAL_ADDRESS)}
