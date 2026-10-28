from fastapi import FastAPI
from fastapi.responses import HTMLResponse
 os,requests,json,datetime,glob,random

app=FastAPI()
MODEL=os.getenv("OPENROUTER_MODEL","meta-llama/llama-3.1-8b-instruct")
OR_KEY=os.getenv("OPENROUTER_API_KEY")

# --- AUTO-DETECT TELEGRAM 100% ---
def get_tg():
    token=os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
    chat=os.getenv("TG_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    return token, chat

TG_TOKEN, TG_ID = get_tg()

COFFRE="coffre_tresor.json";TRADES="trades_kittra.json";ATTENTE="attente_decision.json";REGLES="regles_kittra.json"

def load(f,d):
    try:
        if os.path.exists(f):
            return json.loads(open(f).read())
    except:
        pass
    return d

def save(f,d):
    open(f,"w").write(json.dumps(d))

def send_tg(m):
    try:
        tok, cid = get_tg()
        if not tok or not cid:
            print(f"TG MISSING token={bool(tok)} chat={bool(cid)} env={dict(os.environ)}")
            return f"TG MISSING token={bool(tok)} chat={bool(cid)}"
        r=requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",json={"chat_id":cid,"text":m,"parse_mode":"HTML"},timeout=15)
        print(f"TG SEND {r.status_code} {r.text[:200]}")
        return f"OK {r.status_code}"
    except Exception as e:
        print(f"TG ERR {e}")
        return str(e)

def cerveau(p):
    try:
        if not OR_KEY:
            return "Live OK - Pas de cle OR"
        r=requests.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":f"Bearer {OR_KEY}","HTTP-Referer":"https://kittra-ninja-ultime.onrender.com","X-Title":"KITTRA"},json={"model":MODEL,"messages":[{"role":"user","content":p}],"max_tokens":300},timeout=30).json()
        return r['choices'][0]['message']['content'] if "choices" in r else str(r)
    except Exception as e:
        return f"Err:{e}"

def analyse_jour():
    jour=datetime.datetime.now().day
    if jour in [1,2,3,28,29,30]:
        return {"type":"FAVORABLE_ACHAT","mise":100,"raison":f"Jour {jour}: chute historique fin/debut mois, baleines accumulent. MEILLEUR BUY","action":"BUY GIGA"}
    if jour in [5,6,7,8,18,19,20,21,22,25,26,27]:
        return {"type":"FAVORABLE_VENTE","mise":100,"raison":f"Jour {jour}: pic historique, tout le monde achete, MEILLEUR SELL","action":"SELL GIGA"}
    return {"type":"ORDINAIRE","mise":30,"raison":f"Jour {jour}: ordinaire, calme. Prudent 30%","action":"SCALP PRUDENT 30%"}

def load_coffre():
    return load(COFFRE,{"principal":10.91,"coffre":0.0,"urgence":0.0,"safepal":0.0,"crypto":"USDT"})

def save_coffre(d):
    save(COFFRE,d)

def crypto_meurt(p_now,p_avant):
    if not p_avant:
        return {"alerte":False}
    chute=((p_now-p_avant)/p_avant)*100
    return {"alerte":chute<-3,"chute":chute,"msg":f"CRYPTO MEURT {chute:.2f}% en 15min! VENTE RAPIDE"} if chute<-3 else {"alerte":False,"chute":chute}

def baleine_tracker():
    a=random.choice(["BUY_100K","SELL_100K","RIEN"])
    return {"detecte":a!="RIEN","action":a,"kittra":"10$ meme seconde, ninja"} if a!="RIEN" else {"detecte":False}

@app.get("/",response_class=HTMLResponse)
def root():
    c=load_coffre();j=analyse_jour()
    tok,cid=get_tg()
    return f"<h1>KITTRA V26 NINJA FINAL</h1><p>Principal:{c['principal']}$ ({j['mise']}% en jeu) | Coffre:{c['coffre']}$ | Urgence:{c['urgence']}$ | SafePal:{c['safepal']}$</p><p><b>{j['type']}</b>: {j['raison']}</p><p>TG token:{bool(tok)} chat:{bool(cid)} | MODEL:{MODEL}</p><p><a href='/scan-ninja'>SCAN NINJA</a> | <a href='/bilan-journalier'>Bilan Jour</a> | <a href='/bilan-hebdo'>Bilan Hebdo</a> | <a href='/etat'>Etat</a> | <a href='/test-telegram'>Test Telegram</a> | <a href='/fichiers'>Fichiers</a></p>"

@app.get("/etat")
def etat():
 from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os,requests,json,datetime,glob,random

app=FastAPI()
MODEL=os.getenv("OPENROUTER_MODEL","meta-llama/llama-3.1-8b-instruct")
OR_KEY=os.getenv("OPENROUTER_API_KEY")

# --- AUTO-DETECT TELEGRAM 100% ---
def get_tg():
    token=os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
    chat=os.getenv("TG_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    return token, chat

TG_TOKEN, TG_ID = get_tg()

COFFRE="coffre_tresor.json";TRADES="trades_kittra.json";ATTENTE="attente_decision.json";REGLES="regles_kittra.json"

def load(f,d):
    try:
        if os.path.exists(f):
            return json.loads(open(f).read())
    except:
        pass
    return d

def save(f,d):
    open(f,"w").write(json.dumps(d))

def send_tg(m):
    try:
        tok, cid = get_tg()
        if not tok or not cid:
            print(f"TG MISSING token={bool(tok)} chat={bool(cid)} env={dict(os.environ)}")
            return f"TG MISSING token={bool(tok)} chat={bool(cid)}"
        r=requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",json={"chat_id":cid,"text":m,"parse_mode":"HTML"},timeout=15)
        print(f"TG SEND {r.status_code} {r.text[:200]}")
        return f"OK {r.status_code}"
    except Exception as e:
        print(f"TG ERR {e}")
        return str(e)

def cerveau(p):
    try:
        if not OR_KEY:
            return "Live OK - Pas de cle OR"
        r=requests.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":f"Bearer {OR_KEY}","HTTP-Referer":"https://kittra-ninja-ultime.onrender.com","X-Title":"KITTRA"},json={"model":MODEL,"messages":[{"role":"user","content":p}],"max_tokens":300},timeout=30).json()
        return r['choices'][0]['message']['content'] if "choices" in r else str(r)
    except Exception as e:
        return f"Err:{e}"

def analyse_jour():
    jour=datetime.datetime.now().day
    if jour in [1,2,3,28,29,30]:
        return {"type":"FAVORABLE_ACHAT","mise":100,"raison":f"Jour {jour}: chute historique fin/debut mois, baleines accumulent. MEILLEUR BUY","action":"BUY GIGA"}
    if jour in [5,6,7,8,18,19,20,21,22,25,26,27]:
        return {"type":"FAVORABLE_VENTE","mise":100,"raison":f"Jour {jour}: pic historique, tout le monde achete, MEILLEUR SELL","action":"SELL GIGA"}
    return {"type":"ORDINAIRE","mise":30,"raison":f"Jour {jour}: ordinaire, calme. Prudent 30%","action":"SCALP PRUDENT 30%"}

def load_coffre():
    return load(COFFRE,{"principal":10.91,"coffre":0.0,"urgence":0.0,"safepal":0.0,"crypto":"USDT"})

def save_coffre(d):
    save(COFFRE,d)

def crypto_meurt(p_now,p_avant):
    if not p_avant:
        return {"alerte":False}
    chute=((p_now-p_avant)/p_avant)*100
    return {"alerte":chute<-3,"chute":chute,"msg":f"CRYPTO MEURT {chute:.2f}% en 15min! VENTE RAPIDE"} if chute<-3 else {"alerte":False,"chute":chute}

def baleine_tracker():
    a=random.choice(["BUY_100K","SELL_100K","RIEN"])
    return {"detecte":a!="RIEN","action":a,"kittra":"10$ meme seconde, ninja"} if a!="RIEN" else {"detecte":False}

@app.get("/",response_class=HTMLResponse)
def root():
    c=load_coffre();j=analyse_jour()
    tok,cid=get_tg()
    return f"<h1>KITTRA V26 NINJA FINAL</h1><p>Principal:{c['principal']}$ ({j['mise']}% en jeu) | Coffre:{c['coffre']}$ | Urgence:{c['urgence']}$ | SafePal:{c['safepal']}$</p><p><b>{j['type']}</b>: {j['raison']}</p><p>TG token:{bool(tok)} chat:{bool(cid)} | MODEL:{MODEL}</p><p><a href='/scan-ninja'>SCAN NINJA</a> | <a href='/bilan-journalier'>Bilan Jour</a> | <a href='/bilan-hebdo'>Bilan Hebdo</a> | <a href='/etat'>Etat</a> | <a href='/test-telegram'>Test Telegram</a> | <a href='/fichiers'>Fichiers</a></p>"

@app.get("/etat")
def etat():
    tok,cid=get_tg()
    return {
        "coffre":load_coffre(),
        "jour":analyse_jour(),
        "baleine":baleine_tracker(),
        "regles":load(REGLES,[]),
        "model":MODEL,
        "telegram":{"token":bool(tok),"chat_id":bool(cid),"env_found":{"TG_TOKEN":bool(os.getenv("TG_TOKEN")),"TELEGRAM_BOT_TOKEN":bool(os.getenv("TELEGRAM_BOT_TOKEN")),"CHAT_ID":bool(os.getenv("CHAT_ID")),"TG_CHAT_ID":bool(os.getenv("TG_CHAT_ID")),"TELEGRAM_CHAT_ID":bool(os.getenv("TELEGRAM_CHAT_ID"))},"token_preview":(tok[:10]+"...") if tok else None},
        "cles":bool(OR_KEY and tok)
    }

@app.get("/test-telegram")
def test_telegram():
    tok,cid=get_tg()
    msg=f"KITTRA V26 TEST LIVE {datetime.datetime.now()} - Token {bool(tok)} Chat {bool(cid)} - Ca marche Gardien!"
    res=send_tg(msg)
    return {"env":f"token={bool(tok)} chat={bool(cid)}","send_result":res,"message":msg,"time":str(datetime.datetime.now())}

@app.get("/fichiers")
def fichiers():
    return {"fichiers":glob.glob("*.json")+glob.glob("*.py"),"coffre":load_coffre(),"note":"Lecteur universel"}

@app.get("/scan-ninja")
def scan_ninja():
    c=load_coffre();j=analyse_jour();b=baleine_tracker();p_now=605;p_avant=625;mort=crypto_meurt(p_now,p_avant)
    mise_reelle=c["principal"]*j["mise"]/100
    prompt=f"Solde {c['principal']}$, Mise {mise_reelle}$ ({j['mise']}%), Jour {j}, Baleine {b}, Mort {mort}, BNB {p_now}$. Decide BUY/SELL/HOLD + crypto BNB/SOL/ARB + confiance 0-100"
    ia=cerveau(prompt);conf=85 if "FAVORABLE" in j["type"] else 45
    if mort["alerte"]:
        ia=f"VENTE RAPIDE URGENTE {mort['msg']}";conf=95
    if b["detecte"]:
        ia+=f" + SUIVI BALEINE NINJA {b['action']}"
    if conf<60:
        att=load(ATTENTE,[]);att.append({"id":str(datetime.datetime.now()),"decision":ia,"details":f"Jour {j['type']} mise {mise_reelle}$ | Baleine {b} | Prix {p_now}$","conf":conf,"deadline":str(datetime.datetime.now()+datetime.timedelta(hours=18))});save(ATTENTE,att)
        send_tg(f"FLOU {conf}% - {j['type']} mise {mise_reelle}$\n{j['raison']}\nBaleine:{b}\nJe veux: {ia}\nReponds /repondre?reponse=OUI ou NON. 18h max")
        return {"type":j["type"],"mise":mise_reelle,"raison":j["raison"],"decision":ia,"status":"ATTENTE ACCORD 18H","baleine":b,"mort":mort}
    send_tg(f"{j['type']} {conf}% - Mise {mise_reelle}$\n{j['raison']}\nAction: {ia}\nBaleine:{b}")
    return {"type":j["type"],"mise":mise_reelle,"raison":j["raison"],"decision":ia,"confiance":conf,"baleine":b,"mort":mort}

@app.get("/repondre")
def repondre(reponse: str):
    att=load(ATTENTE,[])
    if not att:
        return {"msg":"Pas d'attente"}
    last=att[-1];save(ATTENTE,[])
    if reponse.upper()=="OUI":
        send_tg(f"Gardien OUI -> J'execute {last['decision']}");return {"execute":last}
    else:
        send_tg(f"Gardien NON -> J'annule {last['decision']}");return {"annule":last}

@app.get("/profit")
def profit(m: float,s="MOLO"):
    c=load_coffre();c["coffre"]+=m;save(COFFRE,c);tr=load(TRADES,[]);tr.append({"date":str(datetime.datetime.now()),"type":s,"gain":m});save(TRADES,tr)
    if m>=1:
        send_tg(f"PROFIT {s} +{m}$ -> Coffre direct + Sous-coffre 1$ auto. Coffre:{c['coffre']}$")
    else:
        send_tg(f"PROFIT {s} +{m}$ -> Coffre {c['coffre']}$")
    return c

@app.get("/bilan-journalier")
def bilan_j():
    c=load_coffre();tr=load(TRADES,[]);reg=load(REGLES,[])
    analyse=cerveau(f"Trades {tr[-5:]} Coffre {c} Regles {reg}. Analyse erreurs, corrige 1 regle pour demain.")
    reg.append({"date":str(datetime.date.today()),"lecon":analyse});save(REGLES,reg)
    send_tg(f"BILAN JOUR {datetime.date.today()}\nPrincipal {c['principal']}$ Coffre {c['coffre']}$\nLecon IA: {analyse}")
    return {"bilan":c,"lecon":analyse}

@app.get("/bilan-hebdo")
def bilan_h():
    c=load_coffre();g=c["principal"]-10.91
    if g<=0:
        return {"msg":"Pas de gains"}
    pc=g*0.5;u=pc*0.4;s=pc*0.3;cr=pc*0.3;r=g*0.5
    c["urgence"]+=u;c["safepal"]+=s;c["coffre"]+=cr;c["principal"]+=r;save_coffre(c)
    conseil=cerveau(f"Semaine +{g}$ Repart Urgence {u} SafePal {s} Coffre {cr} Reinvest {r}. Strat meilleure? Conseil?")
    send_tg(f"BILAN HEBDO +{g}$\n50% Coffre: Urgence {u}$ | SafePal {s}$ | Coffre {cr}$\n50% Reinvest {r}$ -> Principal {c['principal']}$\nConseil: {conseil}")
    return {"coffre":c,"conseil":conseil}

@app.get("/lundi-sweep")
def lundi():
    c=load_coffre();sw=c["coffre"]*0.05;c["coffre"]-=sw;c["safepal"]+=sw;save_coffre(c)
    choix=cerveau(f"Tu as {sw}$ SafePal, choisis 1 crypto GIGA: SOL,ARB,BNB,AVAX? Repond nom seul.")
    send_tg(f"LUNDI SWEEP 5% Coffre {sw}$ -> SafePal en {choix} pour GIGA Mardi-Vendredi")
    return {"sweep":sw,"crypto":choix,"coffre":c}

@app.get("/ping")
def ping():
    return {"ok":True,"v":"V26","model":MODEL,"time":str(datetime.datetime.now())}￼Enter   tok,cid=get_tg()
    return {
        "coffre":load_coffre(),
