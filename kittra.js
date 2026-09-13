// KITTRA V16 FINALE INTEGRALE 100% - TOUT SYSTEME + A+B+C + MANGER PETIT A PETIT
const express = require('express');
const fs = require('fs');
const path = require('path');
const { RestClientV5, WebsocketClient } = require('bybit-api');
const TelegramBot = require('node-telegram-bot-api');

// ===== 1. TES CLES - A CHANGER ICI =====
const BYBIT_API_KEY = "omHyTld2qJJIybioLu";
const BYBIT_API_SECRET = "1Ozaa1MSI5TcGofGeSk4Nl9yICkrDWQNA46n";
const MASTER_KEY = "KvM-ABJ-5Sep2026-9pL2_X8qZ!_Ninja_Babi";
const TELEGRAM_TOKEN = "8765920829:AAFdiSgT3p5nsHTNRtI50mcWguD1v4jrlok";
const TELEGRAM_CHAT_ID = "7895041967";
const MON_WALLET = "TG8UcJUH152YyWsSArL4cwwV78GZijYJoqG";
const CHAINE = "TRC20";

// ===== 2. CONFIG COMPLETE =====
let CONFIG = {
  principal: 10, // capital pour trader
  coffre_total: 0, // seulement les profits
  urgences_usdt: 0,
  liste_coins: ['BTCUSDT','ETHUSDT','SOLUSDT'], // IA va agrandir seule
  TOP_N: 10,
  // PRINCIPE CONSERVATEUR 0.1% > PERTE
  TAKE_PROFIT: 0.8, // on vend à +0.8% (petit mais sûr)
  STOP_LOSS: -1.2, // on coupe à -1.2% (vite pour pas perdre gros)
  MIN_PROFIT_SECURISE: 0.1,
  MIN_RSI_DATA: 15,
  COOLDOWN_SEC: 180, // 3 min entre 2 trades même coin
  jour_sweep: 0, // Dimanche
  heure_sweep: 18,
  repartition: { trading: 40, urgences: 24, business: 12, maison: 8, enfants: 4 }
};

const client = new RestClientV5({ key: BYBIT_API_KEY, secret: BYBIT_API_SECRET, testnet: false });
const app = express(); app.use(express.json());
const bot = new TelegramBot(TELEGRAM_TOKEN);

// ===== 3. MEMOIRE =====
let MEMOIRE = { trades:[], stats:{}, deadCoins:[], vuCoins:[], coffres:{business:0, maison:0, enfants:0}, gains:0, pertes:0, niveau:1, kill_switch:false, derniereActivite: Date.now() };
try{ if(fs.existsSync('./memoire.json')) MEMOIRE = JSON.parse(fs.readFileSync('./memoire.json')); }catch(e){}
function saveMemoire(){ try{ fs.writeFileSync('./memoire.json', JSON.stringify(MEMOIRE, null, 2)); }catch(e){} }

let PRIX={}, HISTO={}, POS={}, SCORE={}, VOLUME={}, FEAR_GREED=50, TENDANCE_1H={}, LAST_TRADE={};
let BYBIT_HEALTH={fails:0, lastOk:Date.now()}, LAST_PRICE_TIME=Date.now();

async function alerte(msg){ console.log(msg); try{ await bot.sendMessage(TELEGRAM_CHAT_ID, `🤖 V16 [${MASTER_KEY}]: ${msg}`);}catch(e){} }
function activerKillSwitch(raison){ MEMOIRE.kill_switch=true; saveMemoire(); alerte(`🚨 KILL-SWITCH: ${raison} | Capital ${CONFIG.principal.toFixed(2)}$`); }

// ===== 4. CERVEAU C : FEAR & GREED =====
async function getFearGreed(){
  try{
    let r=await fetch('https://api.alternative.me/fng/?limit=1'); let j=await r.json();
    FEAR_GREED=parseInt(j.data[0].value);
    console.log(`[C] Fear&Greed ${FEAR_GREED} ${j.data[0].value_classification}`);
    if(FEAR_GREED<=20) await alerte(`😱 PEUR EXTREME ${FEAR_GREED}/100 - J'ARRETE D'ACHETER`);
    if(FEAR_GREED>=85) await alerte(`🤑 GREED EXTREME ${FEAR_GREED}/100 - JE SECURISE MEME +0.1%`);
    return FEAR_GREED;
  }catch(e){ return 50; }
}

// ===== 5. CERVEAU A : BOUGIES 1H =====
async function analyserBougies1H(coin){
  try{
    let k=await client.getKline({ category:'spot', symbol:coin, interval:'60', limit:24 });
    let closes=k.result.list.map(x=>parseFloat(x[4])).reverse();
    let sma7=closes.slice(-7).reduce((a,b)=>a+b)/7; let sma24=closes.reduce((a,b)=>a+b)/24;
    let chute=((closes[closes.length-1]-closes[0])/closes[0])*100;
    let tendance="NEUTRE";
    if(closes[closes.length-1]<sma7 && sma7<sma24 && chute<-5) tendance="CHUTE LIBRE - NE PAS ACHETER";
    else if(chute<-10) tendance="KRACH - ATTENDRE";
    else if(closes[closes.length-1]>sma7 && chute>1) tendance="HAUSSE SAINE";
    TENDANCE_1H[coin]={tendance, chute:chute.toFixed(2)}; return TENDANCE_1H[coin];
  }catch(e){ return {tendance:"NEUTRE", chute:0}; }
}

// ===== 6. CERVEAU B : NOUVEAUX LISTINGS =====
async function detecterNouveauxListings(){
  try{
    let tickers=await client.getTickers({category:'spot'});
    for(let t of tickers.result.list){
      if(!t.symbol.endsWith('USDT')) continue;
      if(MEMOIRE.vuCoins.includes(t.symbol)||MEMOIRE.deadCoins.includes(t.symbol)) continue;
      let vol=parseFloat(t.volume24h); let change=parseFloat(t.price24hPcnt)*100;
      if(vol>10000000 && Math.abs(change)>20){
        MEMOIRE.vuCoins.push(t.symbol); if(MEMOIRE.vuCoins.length>500) MEMOIRE.vuCoins.shift(); saveMemoire();
        if(FEAR_GREED<75){
          await alerte(`🆕 NOUVEAU LISTING ${t.symbol} Vol ${(vol/1e6).toFixed(1)}M$ ${change.toFixed(1)}% - Analyse 1H...`);
          let a=await analyserBougies1H(t.symbol);
          if(a.tendance.includes("HAUSSE") &&!CONFIG.liste_coins.includes(t.symbol)){
            CONFIG.liste_coins.unshift(t.symbol); CONFIG.liste_coins=CONFIG.liste_coins.slice(0,CONFIG.TOP_N);
            await alerte(`✅ LISTING VALIDE ${t.symbol} ajouté pour petit profit`);
          }
        }
      }
    }
  }catch(e){}
}

// ===== 7. IA APPRENTISSAGE + ANALYSE MARCHE =====
function calculerRSI(coin){
  let p=HISTO[coin]; if(!p||p.length<CONFIG.MIN_RSI_DATA) return null;
  let g=0,l=0; for(let i=1;i<p.length;i++){ let d=p[i]-p[i-1]; if(d>0) g+=d; else l-=d; }
  if(l===0) return 75; return 100-(100/(1+g/l));
}
function apprendre(coin, profitPct){
  if(!MEMOIRE.stats[coin]) MEMOIRE.stats[coin]={trades:0,wins:0,profitTotal:0,score:50};
  let s=MEMOIRE.stats[coin]; s.trades++; s.profitTotal+=profitPct; if(profitPct>0) s.wins++;
  s.avg=s.profitTotal/s.trades; s.score=Math.max(5,Math.min(95,(s.wins/s.trades*50)+(s.avg*5)+50));
  SCORE[coin]=s.score; saveMemoire();
}
async function analyserMarcheGlobal(){
  try{
    let tickers=await client.getTickers({category:'spot'});
    let top=tickers.result.list.filter(t=>t.symbol.endsWith('USDT')&&parseFloat(t.volume24h)>500000).sort((a,b)=>parseFloat(b.volume24h)-parseFloat(a.volume24h)).slice(0,30);
    let nb=CONFIG.principal<20?3:CONFIG.principal<100?5:CONFIG.principal<500?8:CONFIG.TOP_N;
    let meilleurs=top.filter(t=>!MEMOIRE.deadCoins.includes(t.symbol)&&(SCORE[t.symbol]||50)>20).slice(0,nb).map(t=>t.symbol);
    CONFIG.liste_coins=[...new Set([...CONFIG.liste_coins,...meilleurs])].slice(0,nb);
    for(let t of tickers.result.list){
      let ch=parseFloat(t.price24hPcnt)*100;
      if(ch<-30&&parseFloat(t.volume24h)<1000000&&!MEMOIRE.deadCoins.includes(t.symbol)){
        MEMOIRE.deadCoins.push(t.symbol); saveMemoire();
        if(POS[t.symbol]) await vendre(t.symbol,true);
        await alerte(`💀 COIN MOURANT ${t.symbol} ${ch.toFixed(1)}% - VENTE FORCEE + BLACKLIST`);
      }
    }
  }catch(e){}
}

// ===== 8. TRADING CONSERVATEUR =====
function taillePosition(coin){
  let sc=SCORE[coin]||50; if(sc<40) return 0;
  let base=CONFIG.principal*0.08; let multi=sc/60;
  return Math.min(base*multi, CONFIG.principal*0.20);
}
async function acheter(sym){
  try{
    if(POS[sym]) throw new Error("Deja en position");
    if(MEMOIRE.kill_switch) throw new Error("Kill switch actif");
    if(Date.now()-(LAST_TRADE[sym]||0) < CONFIG.COOLDOWN_SEC*1000) throw new Error("Cooldown");
    let rsi=calculerRSI(sym); if(rsi===null) throw new Error(`RSI chargement ${HISTO[sym]?.length||0}/${CONFIG.MIN_RSI_DATA}`);
    if(rsi>25) throw new Error(`RSI ${rsi.toFixed(0)} trop haut (>25)`);
    if(FEAR_GREED<=20) throw new Error(`Fear ${FEAR_GREED} peur extreme`);
    if(FEAR_GREED>=85 && rsi>20) throw new Error(`Greed ${FEAR_GREED} trop haut`);
    let bougie=await analyserBougies1H(sym);
    if(bougie.tendance.includes("CHUTE")||bougie.tendance.includes("KRACH")) throw new Error(`1H ${bougie.tendance}`);
    if((SCORE[sym]||50)<40) throw new Error(`Score ${SCORE[sym]||50} trop bas`);
    let montant=taillePosition(sym); if(montant<1) throw new Error(`Montant ${montant.toFixed(2)}$ trop petit ou score bas`);
    if(CONFIG.principal<montant) throw new Error(`Capital ${CONFIG.principal.toFixed(2)}$ < ${montant.toFixed(2)}$`);
    let qty=montant/PRIX[sym]; if(qty*PRIX[sym]<1) throw new Error("Min 1$ Bybit");
    console.log(`[ACHAT] ${sym} ${montant.toFixed(2)}$ qty ${qty.toFixed(6)}`);
    let res=await client.submitOrder({ category:'spot', symbol:sym, side:'Buy', orderType:'Market', qty:qty.toFixed(6) });
    console.log("ACHAT OK", res.result||res);
    CONFIG.principal-=montant; POS[sym]={prix:PRIX[sym], qty:qty.toFixed(6), montant, date:Date.now()}; LAST_TRADE[sym]=Date.now();
    MEMOIRE.trades.push({type:"ACHAT", coin:sym, prix:PRIX[sym], montant, date:new Date().toISOString()}); saveMemoire();
    await alerte(`🟢 ACHAT ${sym} ${montant.toFixed(2)}$ RSI ${rsi.toFixed(0)} 1H:${bougie.tendance} F&G:${FEAR_GREED} Score:${(SCORE[sym]||50).toFixed(0)} | Capital restant ${CONFIG.principal.toFixed(2)}$`);
  }catch(e){ if(!e.message.includes("RSI chargement")&&!e.message.includes("Cooldown")&&!e.message.includes("Deja en")){ console.log(`ECHEC ACHAT ${sym}: ${e.message}`); } }
}
async function vendre(sym, force=false){
  try{
    let p=POS[sym]; if(!p) return;
    let profitPct=((PRIX[sym]-p.prix)/p.prix)*100;
    let doit=false;
    if(force) doit=true;
    else if(profitPct>=CONFIG.TAKE_PROFIT) doit=true;
    else if(profitPct<=CONFIG.STOP_LOSS) doit=true;
    else if(profitPct>=CONFIG.MIN_PROFIT_SECURISE && FEAR_GREED>=80) doit=true;
    else if(profitPct>=CONFIG.MIN_PROFIT_SECURISE && TENDANCE_1H[sym]?.tendance.includes("CHUTE")) doit=true;
    if(!doit) return;
    console.log(`[VENTE] ${sym} ${profitPct.toFixed(2)}%`);
    await client.submitOrder({ category:'spot', symbol:sym, side:'Sell', orderType:'Market', qty:p.qty });
    let profitUsdt=parseFloat(p.qty)*(PRIX[sym]-p.prix);
    CONFIG.principal+=p.montant+profitUsdt;
    if(profitUsdt>0){ CONFIG.coffre_total+=profitUsdt; MEMOIRE.gains++; } else { MEMOIRE.pertes++; if(CONFIG.principal<2) activerKillSwitch(`Capital critique ${CONFIG.principal}$`); }
    apprendre(sym, profitPct); delete POS[sym]; LAST_TRADE[sym]=Date.now();
    MEMOIRE.trades.push({type:"VENTE", coin:sym, prix:PRIX[sym], profit:profitUsdt, pct:profitPct, date:new Date().toISOString()}); saveMemoire();
    await alerte(`${profitUsdt>=0?'🔴 VENTE PROFIT':'🔴 VENTE STOP'} ${sym} ${profitPct.toFixed(2)}% (${profitUsdt.toFixed(4)}$) | Capital ${CONFIG.principal.toFixed(2)}$ Coffre ${CONFIG.coffre_total.toFixed(2)}$`);
  }catch(e){ console.error(`ECHEC VENTE ${sym}:`, e.message); await alerte(`❌ ECHEC VENTE ${sym}: ${e.message}`); }
}

// ===== 9. COFFRE-FORT + REPARTITION =====
async function envoyerVersCoffreFort(nom, montant){
  if(montant<1.1){ console.log(`Coffre ${nom} ${montant.toFixed(2)}$ <1.1$ garde memoire`); MEMOIRE.coffres[nom]=(MEMOIRE.coffres[nom]||0)+montant; saveMemoire(); return; }
  try{
    let r=await client.submitWithdrawal({ coin:'USDT', chain:CHAINE, address:MON_WALLET, amount:montant.toFixed(2), forceChain:1 });
    console.log(`Retrait ${nom} OK`, r.result||r); MEMOIRE.coffres[nom]=(MEMOIRE.coffres[nom]||0)+montant; saveMemoire();
    await alerte(`💰 ${montant.toFixed(2)} USDT -> COFFRE ${nom.toUpperCase()} vers ${MON_WALLET}`);
  }catch(e){
    console.log(`Retrait ${nom} echec ${e.message}`); MEMOIRE.coffres[nom]=(MEMOIRE.coffres[nom]||0)+montant; saveMemoire();
    await alerte(`⚠️ Retrait ${nom} ${montant.toFixed(2)}$ gardé en memoire (erreur: ${e.message})`);
  }
}
async function repartirEtSweeper(){
  if(CONFIG.coffre_total<0.5) return;
  let total=CONFIG.coffre_total; let rep=CONFIG.repartition;
  let aTrading=total*rep.trading/100; let aUrg=total*rep.urgences/100; let aSweep=total-aTrading-aUrg;
  CONFIG.principal+=aTrading; CONFIG.urgences_usdt+=aUrg;
  let div=100-rep.trading-rep.urgences;
  let parts={ business:aSweep*rep.business/div, maison:aSweep*rep.maison/div, enfants:aSweep*rep.enfants/div };
  let msg=`📊 REPARTITION HEBDO ${total.toFixed(2)}$ (petit à petit)\nTRADING:+${aTrading.toFixed(2)}$\nURGENCES:+${aUrg.toFixed(2)}$\n`;
  for(let k in parts){ await envoyerVersCoffreFort(k, parts[k]); msg+=`${k.toUpperCase()}:+${parts[k].toFixed(2)}$\n`; }
  CONFIG.coffre_total=0; saveMemoire(); await alerte(msg);
}

// ===== 10. SURVEILLANCE FERMETURE BYBIT =====
async function surveillerBybit(){
  try{ await client.getWalletBalance({accountType:'UNIFIED'}); BYBIT_HEALTH.lastOk=Date.now(); BYBIT_HEALTH.fails=0; }
  catch(e){
    BYBIT_HEALTH.fails++; console.log(`Bybit fail ${BYBIT_HEALTH.fails} ${e.message}`);
    if(BYBIT_HEALTH.fails>=10 || Date.now()-BYBIT_HEALTH.lastOk>10*60*1000){
      await alerte(`🚨 BYBIT FERMETURE DETECTEE - LIQUIDATION + TRANSFERT AUTO VERS ${MON_WALLET}`);
      for(let c in POS){ try{ await client.submitOrder({category:'spot',symbol:c,side:'Sell',orderType:'Market',qty:POS[c].qty}); await alerte(`💸 LIQUIDATION ${c}`);}catch(e){} }
      try{ let b=await client.getWalletBalance({accountType:'UNIFIED'}); let usdt=parseFloat(b.result.list[0].coin.find(x=>x.coin=='USDT')?.walletBalance||0); if(usdt>1.1) await client.submitWithdrawal({coin:'USDT',chain:CHAINE,address:MON_WALLET,amount:usdt.toFixed(2)}); }catch(e){}
      MEMOIRE.kill_switch=true; saveMemoire();
    }
  }
}

// ===== 11. WEBSOCKET + BOUCLES =====
function startWS(){
  const ws=new WebsocketClient({ market:'v5', key:BYBIT_API_KEY, secret:BYBIT_API_SECRET });
  ws.subscribeV5(CONFIG.liste_coins.map(c=>`tickers.${c}`), 'spot');
  ws.on('update', d=>{ if(!d.data?.symbol) return; let c=d.data.symbol; let p=parseFloat(d.data.lastPrice); PRIX[c]=p; if(!HISTO[c]) HISTO[c]=[]; HISTO[c].push(p); if(HISTO[c].length>100) HISTO[c].shift(); LAST_PRICE_TIME=Date.now(); });
  ws.on('open', ()=> alerte(`WS Connecté MASTER ${MASTER_KEY}`));
  ws.on('close', ()=>{ console.log("WS fermé reconnexion 5s"); setTimeout(()=>{ startWS(); analyserMarcheGlobal(); },5000); });
}
startWS();

setInterval(async ()=>{ if(MEMOIRE.kill_switch) return; for(let c of CONFIG.liste_coins){ await acheter(c); await vendre(c); } }, 15000);
setInterval(analyserMarcheGlobal, 5*60*1000);
setInterval(detecterNouveauxListings, 2*60*1000);
setInterval(getFearGreed, 10*60*1000);
setInterval(surveillerBybit, 60*1000);
setInterval(async ()=>{ let d=new Date(); if(d.getDay()===CONFIG.jour_sweep&&d.getHours()===CONFIG.heure_sweep&&d.getMinutes()<5) await repartirEtSweeper(); }, 60*1000);

analyserMarcheGlobal(); getFearGreed(); detecterNouveauxListings();

// ===== 12. SERVEUR =====
app.get('/', (req,res)=> res.send(`KITTRA V16 INTEGRALE VIVANTE MASTER ${MASTER_KEY} - Capital ${CONFIG.principal.toFixed(2)}$ Coffre ${CONFIG.coffre_total.toFixed(2)}$ Coins ${CONFIG.liste_coins.join(',')} F&G ${FEAR_GREED}`));
app.get('/ping', (req,res)=> res.json({version:"V16 INTEGRALE A+B+C", master:MASTER_KEY, capital:CONFIG.principal, coffre:CONFIG.coffre_total, urgences:CONFIG.urgences_usdt, coins:CONFIG.liste_coins, scores:SCORE, tendance1H:TENDANCE_1H, fearGreed:FEAR_GREED, positions:POS, deadCoins:MEMOIRE.deadCoins, coffres:MEMOIRE.coffres, health:BYBIT_HEALTH, kill:MEMOIRE.kill_switch}));
app.get('/api/status', (req,res)=> res.json({principal:CONFIG.principal, coffre:CONFIG.coffre_total, rsi:{BTC:calculerRSI('BTCUSDT'), ETH:calculerRSI('ETHUSDT'), SOL:calculerRSI('SOLUSDT')}}));

const PORT=process.env.PORT||10000;
app.listen(PORT,'0.0.0.0',()=>{ console.log(`V16 INTEGRALE ACTIF sur ${PORT} MASTER ${MASTER_KEY}`); alerte(`V16 INTEGRALE DEMARRE - Capital ${CONFIG.principal}$ - Objectif +0.8% Stop -1.2% - Manger petit à petit - A+B+C actifs`); });
