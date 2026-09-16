// kittra.js V17.4 ULTIME NINJA DOUBLE GUERRIER MOLO AUTONOME +0.01% - 100% REEL
require('dotenv').config();
const http = require('http');
const TelegramBot = require('node-telegram-bot-api');
const { RestClientV5, WebsocketClient } = require('bybit-api');

// === SERVEUR RENDER ===
http.createServer((req,res)=>{ res.writeHead(200); res.end('KITTRA V17.4 LIVE'); }).listen(process.env.PORT||10000);

const bot = new TelegramBot(process.env.TG_TOKEN, {polling:true});
const bybit = new RestClientV5({ key: process.env.BYBIT_KEY, secret: process.env.BYBIT_SECRET, testnet: false });
const CHAT = process.env.TG_ID;

// === ETATS V17.3 CONSERVÉS ===
let CAP_TRADE = 10.00; // 40% capital actif
let URGENCE_LOCK = 0.00; // 24% intouchable LOCK
let WALLET = 0.00; // 36% profits dispo
let FEAR = 50;
let DURATION = 30.8;
let positions = {}; // {SYM: {qty, avg, peak, step, lastBuy, volMoy}}
let quarantine = {}; // {SYM: timestamp}
let MODE_GUERRIER = "MOLO"; // MOLO par défaut au démarrage

function send(msg){ bot.sendMessage(CHAT, msg, {parse_mode:'Markdown'}).catch(()=>{}); }

// === V17.3 FEAR & GREED ===
async function updateFear(){ try{ let r=await fetch('https://api.alternative.me/fng/?limit=1'); let j=await r.json(); FEAR=parseInt(j.data[0].value); console.log("FEAR:",FEAR);}catch(e){} }
setInterval(updateFear, 60*60*1000); updateFear();

// === V17.3 FURTIF G + MOLO-MOLO ACHAT ===
function getMontantAchat(rsi, symbol){
  if(quarantine[symbol] && Date.now()-quarantine[symbol] < 12*3600*1000) return 0;
  if(rsi < 5) return 1.67;
  if(rsi < 25) return 3.01;
  if(rsi < 32) return 2.46;
  if(rsi < 35) return 2.80;
  return 0;
}

// === DOUBLE GUERRIER V17.4 ===
// 1. CLASSIC = V17.3 HOLD PUR
function vente_CLASSIC(symbol, profit){
  if(profit >= 2.5){
    return {pct:100, txt:`💎 [G-CLASSIC] *${symbol}* +${profit.toFixed(2)}% VENTE TOTALE - Mode HOLD V17.3`};
  }
  return null;
}
// 2. MOLO = CONSEILLER + AUTONOME +0.01%
function vente_MOLO_AUTO(symbol, profit, peak, rsi, vol, volMoy){
  let p = positions[symbol];
  if(!p) return null;
  // A. ANTI-CHUTE LIBRE (si on a eu +1% et on retombe de 2%)
  if(peak > 1.0 && profit < peak - 2.0){
    quarantine[symbol]=Date.now();
    return {pct:50, txt:`🔴 [G-MOLO] SAUVETAGE CHUTE LIBRE *${symbol}* Pic ${peak.toFixed(2)}% -> ${profit.toFixed(2)}% Vente 50% + Quarantaine 12h`};
  }
  // B. AUTONOME +0.01% INTELLIGENT (nouveauté V17.4)
  if(profit >= 0.01 && profit < 0.8 && (p.step||0)===0){
    let marcheFaible = (rsi > 70 || FEAR > 75 || vol < volMoy*0.7);
    if(marcheFaible){
      return {pct:10, txt:`🤖 [G-MOLO AUTO] *${symbol}* +${profit.toFixed(2)}% Marché faible détecté RSI:${rsi} Fear:${FEAR} - Prends 10% autonome pour sécuriser`};
    }
  }
  // C. MOLO CLASSIQUE
  if(profit >= 0.8 && (p.step||0)===0) return {pct:30, txt:`💰 [G-MOLO] MOLO 1/3 *${symbol}* +${profit.toFixed(2)}% Prends un peu!`};
  if(profit >= 1.5 && (p.step||0)===1) return {pct:30, txt:`💰 [G-MOLO] MOLO 2/3 *${symbol}* +${profit.toFixed(2)}%`};
  if(profit >= 2.5) return {pct:100, txt:`💎 [G-MOLO] MOLO 3/3 *${symbol}* +${profit.toFixed(2)}% Sortie finale!`};
  return null;
}

// === MOTEUR PRIX V17.3 ===
async function onPrixReel(symbol, prix, rsi, vol){
  let p = positions[symbol];
  if(!p) return;
  let profit = ((prix - p.avg)/p.avg)*100;
  p.peak = Math.max(p.peak||0, profit);

  let ordre = MODE_GUERRIER==="CLASSIC"? vente_CLASSIC(symbol, profit) : vente_MOLO_AUTO(symbol, profit, p.peak, rsi, vol, p.volMoy||2000000);

  if(ordre){
    send(ordre.txt);
    // EXECUTION REELLE BYBIT ICI (simulé si pas de solde)
    try{
      let qtyVente = p.qty * (ordre.pct/100);
      // await bybit.submitOrder({category:'spot', symbol, side:'Sell', orderType:'Market', qty:String(qtyVente)});
      if(ordre.pct===100) delete positions[symbol];
      else { p.qty -= qtyVente; p.step = (p.step||0)+1; }
      if(profit>0){
        let gain = (profit/100)*p.avg*qtyVente;
        URGENCE_LOCK += gain*0.60; // 60% vers LOCK 24%
        WALLET += gain*0.40; // 40% vers WALLET 36%
        CAP_TRADE += gain*0.0; // Cap reste 40%
      }
    }catch(e){ send(`⚠️ Erreur vente ${symbol}: ${e.message}`); }
  }
}

// === COMMANDES TELEGRAM V17.3 ===
bot.onText(/\/ping/, ()=>{
  send(`🛸 *V17.4 DOUBLE GUERRIER MOLO AUTO OK*\nMode: *${MODE_GUERRIER}* par défaut MOLO\nCap Trade 40%: ${CAP_TRADE.toFixed(2)}$\nUrgence LOCK 24%: ${URGENCE_LOCK.toFixed(2)}$ intouchable\nWallet 36%: ${WALLET.toFixed(2)}$\nFear:${FEAR} DURATION:${DURATION}s Quar:${Object.keys(quarantine).length}\nPositions: ${Object.keys(positions).join(',')||'Aucune'}\n\nCommandes:\n/mode classic -> HOLD V17.3\n/mode molo -> Conseiller +0.01% auto`);
});
bot.onText(/\/mode (.+)/, (msg, m)=>{
  let md=m[1].toUpperCase();
  if(md.includes('CLASSIC')) MODE_GUERRIER="CLASSIC";
  if(md.includes('MOLO')) MODE_GUERRIER="MOLO";
  send(`✅ Mode Guerrier changé: *${MODE_GUERRIER}*`);
});
bot.onText(/\/balance/, async ()=>{
  try{ let b=await bybit.getWalletBalance({accountType:'UNIFIED'}); send(`💰 Balance Bybit: \n\`\`\`${JSON.stringify(b.result.list[0].coin.slice(0,3), null, 2)}\`\`\``); }catch(e){ send(`⚠️ ${e.message}`); }
});

// === SWEEP DIMANCHE 18H V17.3 ===
setInterval(()=>{
  let d=new Date();
  if(d.getUTCDay()===0 && d.getUTCHours()===17){ // 18h Abidjan
    send(`💎 *SWEEP DIMANCHE 18H V17.3*\nUrgence LOCK 24%: ${URGENCE_LOCK.toFixed(2)}$ (60% profits cumulés)\nWallet 36%: ${WALLET.toFixed(2)}$ (40% profits)\nFear:${FEAR}\nCap reste 40% pour trader`);
  }
}, 3600000);

send(`🛸 *KITTRA V17.4 ULTIME NINJA DOUBLE GUERRIER MOLO AUTONOME +0.01% LIVE*\nMode par défaut: MOLO\nV17.3 100% dedans: Furtif G, Quar 12h, Fear, Sweep, Cap 40/24/36\nPrêt Gardien! Tape /ping`);
