// =========================================================
// KITTRA DRONE v16.1 FURTIF FUTURISTE - INTEGRALE A+B+C
// Ninja Babi - Stealth, Intelligent, Discret
// =========================================================
require('http').createServer((req,res) => res.end('Drone Stealth LIVE')).listen(process.env.PORT || 10000);

const { RestClientV5, WebsocketClient } = require('bybit-api');
const fs = require('fs');

// --- CONFIG DRONE FURTIF ---
let CONFIG = {
  principal: 10,
  coffre_total: 0,
  urgences: 0,
  TOP_N: 10,
  TAKE_PROFIT: 0.8, // +0.8% on mange petit
  STOP_LOSS: -1.2, // -1.2% on coupe vite
  MIN_PROFIT_FURTIF: 0.1,// même +0.1% on sécurise si danger
  COOLDOWN: 180, // 3 min entre 2 trades même coin
  jour_sweep: 0, // Dimanche
  heure_sweep: 18,
  repartition: { trading: 40, urgences: 24, business: 12, maison: 8, enfants: 4 }
};

const client = new RestClientV5({
  key: process.env.BYBIT_KEY,
  secret: process.env.BYBIT_SECRET,
  testnet: false
});

const WALLET = process.env.WALLET || "TG8UcJUH152YyWsSArL4cwwV78GZijYJoqG";
const CHAINE = "TRC20";

// --- MEMOIRE DRONE ---
let MEMOIRE = { trades:[], stats:{}, deadCoins:[], vuCoins:[], coffres:{business:0, maison:0, enfants:0}, gains:0, pertes:0, kill:false };
try{ if(fs.existsSync('./memoire.json')) MEMOIRE = JSON.parse(fs.readFileSync('./memoire.json')); }catch(e){}
function save(){ try{ fs.writeFileSync('./memoire.json', JSON.stringify(MEMOIRE, null, 2)); }catch(e){} }

let PRIX={}, HISTO={}, POS={}, SCORE={}, FEAR=50, TENDANCE={}, LAST_TRADE={}, LAST_PRICE=Date.now();

// --- TELEGRAM FURTIF (message court) ---
async function tg(msg){
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chat = process.env.TELEGRAM_CHAT_ID;
  if(!token ||!chat) return;
  try{
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ chat_id: chat, text: `🛸 DRONE: ${msg}`, parse_mode:'Markdown' })
    });
  }catch(e){}
}

// --- CERVEAU C : FEAR & GREED ---
async function getFear(){
  try{
    let r = await fetch('https://api.alternative.me/fng/?limit=1');
    let j = await r.json();
    FEAR = parseInt(j.data[0].value);
    if(FEAR <= 20) await tg(`😱 PEUR ${FEAR} - Drone en pause`);
    if(FEAR >= 85) await tg(`🤑 GREED ${FEAR} - Mode sécurisation +0.1%`);
  }catch(e){ FEAR = 50; }
}

// --- CERVEAU A : BOUGIES 1H ---
async function analyse1H(coin){
  try{
    let k = await client.getKline({ category:'spot', symbol:coin, interval:'60', limit:24 });
    let closes = k.result.list.map(x=>parseFloat(x[4])).reverse();
    let sma7 = closes.slice(-7).reduce((a,b)=>a+b)/7;
    let sma24 = closes.reduce((a,b)=>a+b)/24;
    let chute = ((closes[closes.length-1]-closes[0])/closes[0])*100;
    let t = "NEUTRE";
    if(closes[closes.length-1] < sma7 && chute < -5) t = "CHUTE";
    else if(chute < -10) t = "KRACH";
    else if(closes[closes.length-1] > sma7 && chute > 1) t = "HAUSSE";
    TENDANCE[coin] = {tendance:t, chute:chute.toFixed(1)};
    return TENDANCE[coin];
  }catch(e){ return {tendance:"NEUTRE", chute:0}; }
}

// --- CERVEAU B : LISTINGS + IA MARCHE ---
async function scanMarche(){
  try{
    let tickers = await client.getTickers({category:'spot'});
    let top = tickers.result.list.filter(t=>t.symbol.endsWith('USDT') && parseFloat(t.volume24h) > 500000)
     .sort((a,b)=>parseFloat(b.volume24h)-parseFloat(a.volume24h)).slice(0,30);

    // IA: choisit les meilleurs selon score
    let nb = CONFIG.principal < 20? 3 : CONFIG.principal < 100? 5 : 8;
    let meilleurs = top.filter(t=>!MEMOIRE.deadCoins.includes(t.symbol) && (SCORE[t.symbol]||50) > 20).slice(0,nb).map(t=>t.symbol);

    // Detection nouveaux listings
    for(let t of tickers.result.list){
      if(!t.symbol.endsWith('USDT')) continue;
      if(MEMOIRE.vuCoins.includes(t.symbol) || MEMOIRE.deadCoins.includes(t.symbol)) continue;
      let vol = parseFloat(t.volume24h); let change = parseFloat(t.price24hPcnt)*100;
      if(vol > 10000000 && Math.abs(change) > 20){
        MEMOIRE.vuCoins.push(t.symbol); if(MEMOIRE.vuCoins.length>500) MEMOIRE.vuCoins.shift(); save();
        if(FEAR < 75){
          let a = await analyse1H(t.symbol);
          if(a.tendance.includes("HAUSSE") &&!meilleurs.includes(t.symbol)){
            meilleurs.unshift(t.symbol);
            await tg(`🆕 Listing validé ${t.symbol} Vol ${(vol/1e6).toFixed(1)}M`);
          }
        }
      }
      // Coin mourant
      if(change < -30 && parseFloat(t.volume24h) < 1000000 &&!MEMOIRE.deadCoins.includes(t.symbol)){
        MEMOIRE.deadCoins.push(t.symbol); save();
        if(POS[t.symbol]) await vendre(t.symbol, true);
        await tg(`💀 ${t.symbol} mourant ${change.toFixed(1)}% blacklist`);
      }
    }
  }catch(e){}
}

// --- IA LEARNING ---
function rsi(coin){
  let p = HISTO[coin]; if(!p || p.length < 15) return null;
  let g=0,l=0; for(let i=1;i<p.length;i++){ let d=p[i]-p[i-1]; if(d>0) g+=d; else l-=d; }
  if(l===0) return 75; return 100-(100/(1+g/l));
}
function apprendre(coin, pct){
  if(!MEMOIRE.stats[coin]) MEMOIRE.stats[coin]={trades:0,wins:0,profitTotal:0,score:50};
  let s=MEMOIRE.stats[coin]; s.trades++; s.profitTotal+=pct; if(pct>0) s.wins++;
  s.score = Math.max(5, Math.min(95, (s.wins/s.trades*50)+(s.profitTotal/s.trades*5)+50));
  SCORE[coin]=s.score; save();
}
function taillePos(coin){
  let sc=SCORE[coin]||50; if(sc<40) return 0;
  let base=CONFIG.principal*0.08; return Math.min(base*sc/60, CONFIG.principal*0.20);
}

// --- TRADING FURTIF ---
async function acheter(sym){
  try{
    if(POS[sym] || MEMOIRE.kill) return;
    if(Date.now()-(LAST_TRADE[sym]||0) < CONFIG.COOLDOWN*1000) return;
    let r = rsi(sym); if(r===null) return;
    if(r > 25) return;
    if(FEAR <= 20) return;
    if(FEAR >= 85 && r > 20) return;
    let bougie = await analyse1H(sym);
    if(bougie.tendance.includes("CHUTE") || bougie.tendance.includes("KRACH")) return;
    if((SCORE[sym]||50) < 40) return;
    let montant = taillePos(sym); if(montant < 1 || CONFIG.principal < montant) return;
    let qty = montant / PRIX[sym];
    await client.submitOrder({ category:'spot', symbol:sym, side:'Buy', orderType:'Market', qty:qty.toFixed(6) });
    CONFIG.principal -= montant;
    POS[sym]={prix:PRIX[sym], qty:qty.toFixed(6), montant, date:Date.now()}; LAST_TRADE[sym]=Date.now();
    MEMOIRE.trades.push({type:"ACHAT", coin:sym, prix:PRIX[sym], montant, date:new Date().toISOString()}); save();
    await tg(`🟢 ACHAT ${sym} ${montant.toFixed(2)}$ RSI ${r.toFixed(0)} 1H:${bougie.tendance}`);
  }catch(e){}
}
async function vendre(sym, force=false){
  try{
    let p=POS[sym]; if(!p) return;
    let pct = ((PRIX[sym]-p.prix)/p.prix)*100;
    let doit = false;
    if(force) doit=true;
    else if(pct >= CONFIG.TAKE_PROFIT) doit=true;
    else if(pct <= CONFIG.STOP_LOSS) doit=true;
    else if(pct >= CONFIG.MIN_PROFIT_FURTIF && FEAR >= 80) doit=true;
    else if(pct >= CONFIG.MIN_PROFIT_FURTIF && TENDANCE[sym]?.tendance.includes("CHUTE")) doit=true;
    if(!doit) return;
    await client.submitOrder({ category:'spot', symbol:sym, side:'Sell', orderType:'Market', qty:p.qty });
    let profit = parseFloat(p.qty)*(PRIX[sym]-p.prix);
    CONFIG.principal += p.montant + profit;
    if(profit > 0){ CONFIG.coffre_total += profit; MEMOIRE.gains++; } else { MEMOIRE.pertes++; }
    apprendre(sym, pct); delete POS[sym]; LAST_TRADE[sym]=Date.now();
    MEMOIRE.trades.push({type:"VENTE", coin:sym, prix:PRIX[sym], profit, pct, date:new Date().toISOString()}); save();
    await tg(`${profit>=0?'🔴 PROFIT':'🔴 STOP'} ${sym} ${pct.toFixed(2)}% (${profit.toFixed(4)}$) Cap ${CONFIG.principal.toFixed(2)}$`);
  }catch(e){}
}

// --- COFFRE + REPARTITION DIMANCHE 18H ---
async function envoyerCoffre(nom, montant){
  if(montant < 1.1){ MEMOIRE.coffres[nom]=(MEMOIRE.coffres[nom]||0)+montant; save(); return; }
  try{
    await client.submitWithdrawal({ coin:'USDT', chain:CHAINE, address:WALLET, amount:montant.toFixed(2), forceChain:1 });
    MEMOIRE.coffres[nom]=(MEMOIRE.coffres[nom]||0)+montant; save();
    await tg(`💰 ${montant.toFixed(2)}$ -> COFFRE ${nom.toUpperCase()}`);
  }catch(e){ MEMOIRE.coffres[nom]=(MEMOIRE.coffres[nom]||0)+montant; save(); }
}
async function repartir(){
  if(CONFIG.coffre_total < 0.5) return;
  let total=CONFIG.coffre_total; let rep=CONFIG.repartition;
  let aTrading=total*rep.trading/100; let aUrg=total*rep.urgences/100; let aSweep=total-aTrading-aUrg;
  CONFIG.principal+=aTrading; CONFIG.urgences+=aUrg;
  let div=100-rep.trading-rep.urgences;
  let parts={ business:aSweep*rep.business/div, maison:aSweep*rep.maison/div, enfants:aSweep*rep.enfants/div };
  let msg=`📊 REPARTITION ${total.toFixed(2)}$\n`;
  for(let k in parts){ await envoyerCoffre(k, parts[k]); msg+=`${k}:${parts[k].toFixed(2)}$\n`; }
  CONFIG.coffre_total=0; save(); await tg(msg);
}

// --- WEBSOCKET FURTIF (jitter aléatoire) ---
function startWS(){
  const ws=new WebsocketClient({ market:'v5', key:process.env.BYBIT_KEY, secret:process.env.BYBIT_SECRET });
  ws.subscribeV5(['BTCUSDT','ETHUSDT','SOLUSDT'].map(c=>`tickers.${c}`), 'spot');
  ws.on('update', d=>{
    if(!d.data?.symbol) return;
    PRIX[d.data.symbol]=parseFloat(d.data.lastPrice);
    if(!HISTO[d.data.symbol]) HISTO[d.data.symbol]=[];
    HISTO[d.data.symbol].push(Prix[d.data.symbol] || PRIX[d.data.symbol]);
    if(HISTO[d.data.symbol].length>100) HISTO[d.data.symbol].shift();
    LAST_PRICE=Date.now();
  });
  ws.on('close', ()=> setTimeout(startWS, 5000 + Math.random()*3000));
}
startWS();

// --- BOUCLES FURTIVES avec jitter ---
setInterval(async()=>{ if(MEMOIRE.kill) return; for(let c of Object.keys(PRIX)){ await acheter(c); await vendre(c); } }, 15000 + Math.random()*5000);
setInterval(scanMarche, 120000 + Math.random()*30000);
setInterval(getFear, 600000);
setInterval(async()=>{ let d=new Date(); if(d.getDay()===CONFIG.jour_sweep && d.getHours()===CONFIG.heure_sweep && d.getMinutes()<5) await repartir(); }, 60000);

scanMarche(); getFear();
console.log("🛸 DRONE FURTIF V16.1 ACTIF - Mode discret intelligent");
tg(`🛸 Drone furtif démarré Cap ${CONFIG.principal}$ - Objectif +0.8% / -1.2%`);
