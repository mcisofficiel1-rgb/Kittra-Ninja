from fastapi import FastAPI;from fastapi.responses import HTMLResponse;import os,requests,json,datetime,random
app=FastAPI();M=os.getenv("OPENROUTER_MODEL","meta-llama/muse-spark-1.3");K=os.getenv("OPENROUTER_API_KEY");T=os.getenv("TG_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN");I=os.getenv("TG_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")
C="coffre_tresor.json";L=lambda f,d: json.loads(open(f).read()) if os.path.exists(f) else d;W=lambda f,d: open(f,"w").write(json.dumps(d))
G=lambda m: requests.post(f"https://api.telegram.org/bot{T}/sendMessage",json={"chat_id":I,"text":m},timeout=10).text if T and I else f"MISS T:{bool(T)} I:{bool(I)}"
B=lambda p: requests.post("https://openrouter.ai/api/v1/chat/completions",headers={"Authorization":f"Bearer {K}"},json={"model":M,"messages":[{"role":"user","content":p}]},timeout=20).json().get('choices',[{}])[0].get('message',{}).get('content','NO KEY') if K else "NO KEY"
J=lambda: (lambda d: {"type":"FAVORABLE_ACHAT","mise":100} if d in [1,2,3,28,29,30] else {"type":"FAVORABLE_VENTE","mise":100} if d in [5,6,7,8,18,19,20,21,22,25,26,27] else {"type":"ORDINAIRE","mise":30})(datetime.datetime.now().day)
@app.get("/",response_class=HTMLResponse)
def r():j=J();return f"<h1>KITTRA V26 17L</h1><p>TG:{bool(T)} {bool(I)} | {j['type']} {j['mise']}%</p><a href='/etat'>/etat</a> | <a href='/test-telegram'>/test-telegram</a> | <a href='/scan-ninja'>/scan-ninja</a>"
@app.get("/etat")
def e():return {"coffre":L(C,{"principal":10.91}),"jour":J(),"tg":{"token":bool(T),"chat_id":bool(I),"env":{"TG_TOKEN":bool(os.getenv("TG_TOKEN")),"TELEGRAM_BOT_TOKEN":bool(os.getenv("TELEGRAM_BOT_TOKEN")),"CHAT_ID":bool(os.getenv("CHAT_ID"))}},"cles":bool(K and T)}
@app.get("/test-telegram")
def t():return {"result":G(f"🧪 KITTRA V26 17L TEST {datetime.datetime.now()} - TG OK Gardien!"),"token":bool(T),"id":bool(I)}
@app.get("/scan-ninja")
def s():j=J();c=L(C,{"principal":10.91});m=c["principal"]*j["mise"]/100;i=B(f"{j} mise {m}$ BUY/SELL/HOLD?") if K else j["type"];G(f"✅ {j['type']} {m}$ -> {i}");return {"type":j["type"],"mise":m,"ia":i,"tg_sent":bool(T and I)}
@app.get("/ping")
def p():return {"ok":True,"tg":bool(T and I)}￼Enter
