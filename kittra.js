// KITTRA V17.3 ULTIME - 100% - FURTIF + NINJA + 12H PATIENT + DOUBLE CERVEAU + SWEEP HEBDO
// OPTIMISE RENDER GRATUIT - NE DORT JAMAIS
require('http').createServer((req,res)=>res.end('V17.3 ULTIME LIVE')).listen(process.env.PORT||10000);
const { RestClientV5, WebsocketClient } = require('bybit-api');
const fs=require('fs');

// --- CONFIG ---
let CONFIG={ principal_total:10, principal_guerrier:5, principal_gardien:5, TP_G:0.8, SL_G:-1.2, TP_GA:1.5, SL_GA:-0.8, COOLDOWN:180, TRADING_PCT:40 };
const client=new RestClientV5({key:process.env.BYBIT_KEY, secret:process.env.BYBIT_SECRET, testnet:false});

let MEMOIRE={ stats:{}, deadCoins:[], vuCoins:[], gains:0, pertes:0, pnl_g:0, pnl_ga:0, last_split:'', last_weekly:'', last_week_profit:0, trading_pct:40, urgence_locked:0, coffres:{trading:0, wallet:0} };
try{ if(fs.existsSync('./memoire.json')) MEMOIRE=Object.assign(MEMOIRE, JSON.parse(fs.readFileSync('./memoire.json'))); CONFIG.TRADING_PCT=MEMOIRE.trading_pct; }catch(e){}
function save(){ fs.writeFileSync('./memoire.json', JSON.stringify(MEMOIRE,null,2)); }

let PRIX={}, HISTO={}, POS_G={}, POS_GA={}, SCORE={}, FEAR=50, LAST_TRADE={};

// --- ANTI-CLONE + TELEGRAM ---
async function killClones(){ try{ await fetch(`https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true`);}catch(e){} }
killClones();
async function tg(m){ try{ await fetch(`https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/sendMessage`,{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({chat_id:process.env.TELEGRAM_CHAT_ID, text:m})}); }catch(e){} }

let OFFSET=0;
async function ecoute(){
  try{
    let r=await fetch(`https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/getUpdates?offset=${OFFSET}&timeout=15`);
    let j=await r.json();
    for(let u of j.result||[]){ OFFSET=u.update_id+1; let txt=u.message?.text||''; if(String(u.message?.chat?.id)!==String(process.env.TELEGRAM_CHAT_ID)) continue;
      if(txt.startsWith('/ping')) await tg(`🛸 V17.3 ULTIME OK\nCap Trade:${CONFIG.principal_total.toFixed(2)}$ (sur ${CONFIG.TRADING_PCT}%)\n🔒 Urgence Bybit:${MEMOIRE.urgence_locked.toFixed(2)}$ (intouchable)\n💸 Wallet:${MEMOIRE.coffres.wallet.toFixed(2)}$\nFear:${FEAR} Quar:${MEMOIRE.deadCoins.length}`);
      if(txt.startsWith('/dead')) await tg(`💀 Quar 12h: ${MEMOIRE.deadCoins.map(d=>d.symbol).join(',')}`);
    }
  }catch(e){} setTimeout(ecoute,2500);
}
ecoute();

// --- OUTILS INTELLIGENTS ---
async function getFear(){ try{ let r=await fetch('https://api.alternative.me/fng/?limit=1'); let j=await r.json(); FEAR=parseInt(j.data[0].value); }catch(e){} }
async function analyse1H(c){ try{ let k=await client.getKline({category:'spot', symbol:c, interval:'60', limit:24}); let cl=k.result.list.map(x=>parseFloat(x[4])).reverse(); let chute=((cl[cl.length-1]-cl[0])/cl[0])*100; return {tendance:chute<-10?"KRACH":chute<-5?"CHUTE":"HAUSSE"}; }catch(e){ return {tendance:"NEUTRE"}; } }
function rsi(c){ let p=HISTO[c]; if(!p||p.length<15) return null; let g=0,l=0; for(let i=1;i<p.length;i++){ let d=p[i]-p[i-1]; if(d>0) g+=d; else l-=d; } if(l===0) return 75; return 100-(100/(1+g/l)); }
function apprendre(c,pct){ if(!MEMOIRE.stats[c]) MEMOIRE.stats[c]={trades:0,wins:0,profitTotal:0,score:50}; let s=MEMOIRE.stats[c]; s.trades++; s.profitTotal+=pct; if(pct>0) s.wins++; s.score=Math.max(5,Math.min(95,(s.wins/s.trades*50)+(s.profitTotal/s.trades*5)+50)); SCORE[c]=s.score; save(); }
function taille(c,mode){ let sc=SCORE[c]||50; if(mode==='G'&&sc<30) return 0; if(mode==='GA'&&sc<45) return 0; let base=mode==='G'?CONFIG.principal_guerrier*0.4:CONFIG.principal_gardien*0.15; return Math.min(base*sc/60, mode==='G'?CONFIG.principal_guerrier*0.6:CONFIG.principal_gardien*0.25); }

// --- SYSTEME FURTIF + NINJA (V16 que tu voulais) ---
function furtifNinjaDelay(){ return new Promise(r=>setTimeout(r, 800 + Math.random()*2200)); } // 0.8s à 3s aléatoire pour ne pas se faire repérer
function ninjaQty(qty){ return (parseFloat(qty) * (0.97 + Math.random()*0.06)).toFixed(6); } // varie quantité -3% à +3% = ninja

async function acheter(sym,mode,prix){
  let POS=mode==='G'?POS_G:POS_GA; if(POS[sym]) return; if(Date.now()-(LAST_TRADE[sym]||0)<180000) return;
  let r=rsi(sym); if(r===null||r>(mode==='G'?35:25)) return; if(FEAR<=20) return;
  let bougie=await analyse1H(sym); if(bougie.tendance==="KRACH") return;
  let mont=taille(sym,mode); if(mont<1) return;
  if(mode==='G'&&CONFIG.principal_guerrier<mont) return; if(mode==='GA'&&CONFIG.principal_gardien<mont) return;

  // FURTIF : achat en 2 fois si montant > 2$ pour cacher l'ordre
  try{
    await furtifNinjaDelay(); // NINJA : attend aléatoire
    let qty1 = ninjaQty(mont/prix/2);
    let qty2 = ninjaQty(mont/prix/2);
    if(mont>2){
      await client.submitOrder({category:'spot', symbol:sym, side:'Buy', orderType:'Market', qty:qty1});
      await new Promise(r=>setTimeout(r,1200));
      await client.submitOrder({category:'spot', symbol:sym, side:'Buy', orderType:'Market', qty:qty2});
    }else{
      await client.submitOrder({category:'spot', symbol:sym, side:'Buy', orderType:'Market', qty:ninjaQty(mont/prix)});
    }
    if(mode==='G') CONFIG.principal_guerrier-=mont; else CONFIG.principal_gardien-=mont;
    POS[sym]={prix, qty:(mont/prix).toFixed(6), montant:mont}; LAST_TRADE[sym]=Date.now(); save();
    await tg(`${mode==='G'?'🟢 FURTIF G':'🔵 NINJA GA'} ${sym} ${mont.toFixed(2)}$ RSI ${r.toFixed(0)}`);
  }catch(e){}
}

async function vendre(sym,mode,force=false){
  let POS=mode==='G'?POS_G:POS_GA; let p=POS[sym]; if(!p) return; let prix=PRIX[sym]; if(!prix) return;
  let pct=((prix-p.prix)/p.prix)*100; let TP=mode==='G'?CONFIG.TP_G:CONFIG.TP_GA; let SL=mode==='G'?CONFIG.SL_G:CONFIG.SL_GA;
  // HOLD PATIENT : ne ferme jamais à vue, seulement TP/SL/Force
  if(!(force||pct>=TP||pct<=SL)) return;
  try{ await furtifNinjaDelay(); await client.submitOrder({category:'spot', symbol:sym, side:'Sell', orderType:'Market', qty:ninjaQty(p.qty)}); let profit=parseFloat(p.qty)*(prix-p.prix); if(mode==='G'){ CONFIG.principal_guerrier+=p.montant+profit; MEMOIRE.pnl_g+=profit; }else{ CONFIG.principal_gardien+=p.montant+profit; MEMOIRE.pnl_ga+=profit; } CONFIG.principal_total=CONFIG.principal_guerrier+CONFIG.principal_gardien; if(profit>0) MEMOIRE.gains++; else MEMOIRE.pertes++; apprendre(sym,pct); delete POS[sym]; save(); await tg(`${profit>=0?'💰':'🔴'} [${mode}] ${sym} ${pct.toFixed(2)}%`); }catch(e){}
}

// --- SCAN + QUARANTAINE 12H + REBOND ---
async function scan(){
  try{
    let tks=await client.getTickers({category:'spot'});
    for(let t of tks.result.list){ if(!t.symbol.endsWith('USDT')) continue; let isDead=MEMOIRE.deadCoins.some(d=>d.symbol===t.symbol); if(isDead||MEMOIRE.vuCoins.includes(t.symbol)) continue;
      let vol=parseFloat(t.volume24h), ch=parseFloat(t.price24hPcnt)*100;
      if(vol>1000000 && Math.abs(ch)>15){ MEMOIRE.vuCoins.push(t.symbol); if(MEMOIRE.vuCoins.length>500) MEMOIRE.vuCoins.shift(); save(); }
      if(ch<-30 && vol<1000000){ MEMOIRE.deadCoins.push({symbol:t.symbol, heure:Date.now(), chute:ch, prix_chute:parseFloat(t.lastPrice)}); save(); await vendre(t.symbol,'G',true); await vendre(t.symbol,'GA',true); await tg(`💀 ${t.symbol} ${ch.toFixed(1)}% -> QUARANTAINE 12h`); }
    }
  }catch(e){}
}
async function checkRebond(){
  if(!MEMOIRE.deadCoins.length) return; let now=Date.now(), reste=[];
  for(let d of MEMOIRE.deadCoins){ let age=(now-d.heure)/3600000; if(age>12) continue;
    try{ let tk=await client.getTickers({category:'spot', symbol:d.symbol}); let info=tk.result.list[0]; if(!info){ reste.push(d); continue; }
      let prix=parseFloat(info.lastPrice), vol=parseFloat(info.volume24h), rebond=d.prix_chute?((prix-d.prix_chute)/d.prix_chute*100):0;
      if(rebond>20 && vol>3000000){ await tg(`♻️ REBOND ${d.symbol} +${rebond.toFixed(1)}% Vol ${(vol/1e6).toFixed(1)}M`); MEMOIRE.vuCoins=MEMOIRE.vuCoins.filter(c=>c!==d.symbol); SCORE[d.symbol]=60; }else reste.push(d);
    }catch(e){ reste.push(d); }
  } MEMOIRE.deadCoins=reste; save();
}

// --- SPLIT + SWEEP HEBDO +1%/-1% ---
async function dailySplit(){
  let today=new Date().toISOString().slice(0,10); if(MEMOIRE.last_split===today) return;
  try{
    let b=await client.getWalletBalance({accountType:'UNIFIED'}); let usdt=parseFloat(b.result.list[0].coin.find(c=>c.coin==='USDT')?.walletBalance||CONFIG.principal_total+MEMOIRE.urgence_locked);
    let totalReel = usdt<3? CONFIG.principal_total+MEMOIRE.urgence_locked : usdt - MEMOIRE.coffres.wallet;
    let tradingCapital = totalReel - MEMOIRE.urgence_locked;
    CONFIG.principal_total=tradingCapital; CONFIG.principal_guerrier=tradingCapital*0.5; CONFIG.principal_gardien=tradingCapital*0.5;
    MEMOIRE.last_split=today; MEMOIRE.pnl_g=0; MEMOIRE.pnl_ga=0; save();
  }catch(e){}
}
async function weeklySweep(){
  let now=new Date(); if(now.getUTCDay()!==0 || now.getUTCHours()!==18) return;
  let today=now.toISOString().slice(0,10); if(MEMOIRE.last_weekly===today) return;
  let profit = (CONFIG.principal_guerrier+CONFIG.principal_gardien+MEMOIRE.urgence_locked) - 10;
  if(profit<=0.5){ CONFIG.TRADING_PCT=Math.max(20, CONFIG.TRADING_PCT-1); await tg(`📉 HEBDO ${today} Pas de profit -> Trading ${CONFIG.TRADING_PCT}% (-1%)`); }
  else{
    if(profit>MEMOIRE.last_week_profit) CONFIG.TRADING_PCT=Math.min(60, CONFIG.TRADING_PCT+1); else CONFIG.TRADING_PCT=Math.max(20, CONFIG.TRADING_PCT-1);
    let trading = profit*CONFIG.TRADING_PCT/100; let urgences=profit*0.24; let wallet=profit-trading-urgences;
    MEMOIRE.urgence_locked+=urgences; MEMOIRE.coffres.wallet+=wallet; MEMOIRE.coffres.trading=trading;
    CONFIG.principal_total=trading; CONFIG.principal_guerrier=trading*0.5; CONFIG.principal_gardien=trading*0.5;
    await tg(`💰 SWEEP HEBDO ${today} Profit:${profit.toFixed(2)}$\n📈 Trading ${CONFIG.TRADING_PCT}% = ${trading.toFixed(2)}$ -> Kittra garde\n🔒 Urgence 24% = ${urgences.toFixed(2)}$ LOCK sur Bybit (Kittra touche plus)\n💸 Wallet 36% = ${wallet.toFixed(2)}$ à transférer\n${profit>MEMOIRE.last_week_profit?'⬆️ +1%':'⬇️ -1%'}`);
  }
  MEMOIRE.trading_pct=CONFIG.TRADING_PCT; MEMOIRE.last_week_profit=profit; MEMOIRE.last_weekly=today; save();
}

function startWS(){ const ws=new WebsocketClient({market:'v5'}); ws.subscribeV5(['BTCUSDT'].map(c=>`tickers.${c}`),'spot'); ws.on('update', d=>{ if(!d.data?.symbol) return; PRIX[d.data.symbol]=parseFloat(d.data.lastPrice); if(!HISTO[d.data.symbol]) HISTO[d.data.symbol]=[]; HISTO[d.data.symbol].push(PRIX[d.data.symbol]); if(HISTO[d.data.symbol].length>100) HISTO[d.data.symbol].shift(); }); ws.on('close',()=>setTimeout(startWS,5000)); }
startWS();

setInterval(async()=>{ for(let c of Object.keys(PRIX)){ await acheter(c,'G',PRIX[c]); await vendre(c,'G'); try{ let tk=await client.getTickers({category:'spot', symbol:c}); if(parseFloat(tk.result.list[0]?.volume24h||0)>5000000){ await acheter(c,'GA',PRIX[c]); await vendre(c,'GA'); } }catch(e){} } },15000);
setInterval(scan,90000); setInterval(checkRebond,2*3600000); setInterval(getFear,300000); setInterval(dailySplit,60000); setInterval(weeklySweep,3600000);
dailySplit(); getFear(); scan();
console.log("V17.3 ULTIME ACTIF - RENDER GRATUIT"); tg(`🛸 V17.3 ULTIME demarrée\nFurtif+Ninja+Double Cerveau+12H Patient\nCap Trade:${CONFIG.principal_total}$ Urgence LOCK:${MEMOIRE.urgence_locked.toFixed(2)}$`);
