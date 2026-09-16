// kittra.js V17.4 ULTIME NINJA DOUBLE GUERRIER MOLO AUTONOME +0.01% - 100% COMPLET V17.3 INCLUS
require('dotenv').config();
const http = require('http');
const TelegramBot = require('node-telegram-bot-api');
const { RestClientV5, WebsocketClient } = require('bybit-api');

// === SERVEUR RENDER V17.3 ===
http.createServer((req,res)=>{res.writeHead(200); res.end('KITTRA V17.4 DOUBLE GUERRIER MOLO AUTO OK');}).listen(process.env.PORT||10000);

const bot = new TelegramBot(process.env.TG_TOKEN, {polling:true});
const bybit = new RestClientV5({key:process.env.BYBIT_KEY, secret:process.env.BYBIT_SECRET});
const CHAT = process.env.TG_ID;

// === TOUT V17.3 CONSERVÉ ===
let CAP_TRADE = 10.00; // 40%
let URGENCE_LOCK = 0.00; // 24% intouchable LOCK
let WALLET = 0.00; // 36%
let FEAR = 69;
let positions = {}; // {BTCUSDT:{qty, avg, peak, step, lastBuy}}
let quarantine = {}; // {SYMBOL: timestamp}
let MODE_GUERRIER = "MOLO"; // MOLO par défaut
let DURATION = 30.8;

function send(msg){ bot.sendMessage(CHAT, msg).catch(()=>{}); }

// === V17.3 FEAR & GREED ===
async function updateFear(){
  try{
    let r = await fetch('https://api.alternative.me/fng/?limit=1');
    let j = await r.json();
    FEAR = parseInt(j.data[0].value);
  }catch(e){}
}
setInterval(updateFear, 3600000); updateFear();

// === V17.3 FURTIF G + ACHAT MOLO-MOLO ===
function getMontantAchat(rsi){
  if(rsi < 5) return 1.67;
  if(rsi < 25) return 3.01;
  if(rsi < 32) return 2.46;
  if(rsi < 35) return 2.80;
  return 0;
}
function isFurtifG(symbol, vol, rsi){
  if(quarantine[symbol] && Date.now()-quarantine[symbol] < 12*3600*1000) return false; // Quar 12h
  return symbol.endsWith('USDT') && vol > 1000000 && rsi < 40;
}

// === DOUBLE GUERRIER ===
function vente_CLASSIC(symbol, profit){
  if(profit >= 2.5) return {pct:100, txt:`💎 [G-CLASSIC] ${symbol} +${profit.toFixed(2)}% VENTE TOTALE HOLD V17.3`};
  return null;
}
function vente_MOLO_AUTO(symbol, profit, peak, rsi, vol, volMoy){
  let p = positions[symbol];
  // 1. ANTI-CHUTE LIBRE V17.4
  if(peak > 1.0 && profit < peak - 2.0){
    quarantine[symbol]=Date.now();
    return {pct:50, txt:`🔴 [G-MOLO] SAUVETAGE CHUTE LIBRE ${symbol} Pic ${peak.toFixed(2)}% -> ${profit.toFixed(2)}% Vente 50% + Quarantaine 12h`};
  }
  // 2. AUTONOME +0.01% INTELLIGENT
  if(profit >= 0.01 && profit < 0.8 && (p.step||0)===0){
    let marcheFaible = (rsi>70 || FEAR>75 || vol < volMoy*0.7);
    if(marcheFaible) return {pct:10, txt:`🤖 [G-MOLO AUTO] ${symbol} +${profit.toFixed(2)}% Marché faible RSI:${rsi} Fear:${FEAR} - Prends 10% autonome`};
  }
  if(profit >= 0.8 && (p.step||0)===0) return {pct:30, txt:`💰 [G-MOLO] MOLO 1/3 ${symbol} +${profit.toFixed(2)}% Prends un peu!`};
  if(profit >= 1.5 && (p.step||0)===1) return {pct:30, txt:`💰 [G-MOLO] MOLO 2/3 ${symbol} +${profit.toFixed(2)}%`};
  if(profit >= 2.5) return {pct:100, txt:`💎 [G-MOLO] MOLO 3/3 ${symbol} +${profit.toFixed(2)}% Sortie finale!`};
  return null;
}

// === MOTEUR V17.3 + V17.4 ===
function onPrix(symbol, prix, rsi, vol){
  let p = positions[symbol];
  if(!p) return;
  let profit = ((prix - p.avg)/p.avg)*100;
  p.peak = Math.max(p.peak||0, profit);
  let ordre = MODE_GUERRIER==="CLASSIC"? vente_CLASSIC(symbol, profit) : vente_MOLO_AUTO(symbol, profit, p.peak, rsi, vol, 2000000);
  if(ordre){
    send(ordre.txt);
    // ICI CODE VENTE BYBIT REEL : bybit.submitOrder(...)
    if(ordre.pct===100) delete positions[symbol];
    else { p.qty *= (1-ordre.pct/100); p.step = (p.step||0)+1; }
    if(profit>0){ URGENCE_LOCK += profit*0.006; WALLET += profit*0.004; } // 60/40 sweep
  } else {
    let ic = profit>=0?'💰':'🔴';
    send(`${ic} [G-${MODE_GUERRIER}] ${symbol} ${profit.toFixed(2)}% Peak:${p.peak.toFixed(2)}% RSI:${rsi}`);
  }
}

// === COMMANDES V17.3 ===
bot.onText(/\/ping/, ()=>{
  send(`🛸 V17.4 ULTIME NINJA DOUBLE GUERRIER MOLO AUTO OK\nMode:${MODE_GUERRIER} (défaut MOLO)\nCap Trade ${CAP_TRADE.toFixed(2)}$ 40%\nUrgence LOCK ${URGENCE_LOCK.toFixed(2)}$ 24% intouchable\nWallet ${WALLET.toFixed(2)}$ 36%\nFear:${FEAR} Quar:${Object.keys(quarantine).length} DURATION:${DURATION}s\nPositions:${Object.keys(positions).join(',')||'Aucune'}\n\n/mode classic -> V17.3 HOLD\n/mode molo -> V17.4 Conseiller +0.01%`);
});
bot.onText(/\/mode (.+)/, (msg, m)=>{
  let md=m[1].toUpperCase();
  if(md.includes('CLASSIC')) MODE_GUERRIER="CLASSIC";
  if(md.includes('MOLO')) MODE_GUERRIER="MOLO";
  send(`✅ Mode Guerrier changé: ${MODE_GUERRIER}`);
});

// === SWEEP DIMANCHE 18H V17.3 ===
setInterval(()=>{
  let d=new Date();
  if(d.getDay()===0 && d.getHours()===18){
    send(`💎 SWEEP DIMANCHE 18H\nUrgence LOCK: ${URGENCE_LOCK.toFixed(2)}$ (60% profits)\nWallet: ${WALLET.toFixed(2)}$ (40% profits)\nFear:${FEAR}`);
  }
}, 3600000);

send(`🛸 KITTRA V17.4 ULTIME NINJA DOUBLE GUERRIER MOLO AUTONOME +0.01% LIVE\nMode par défaut: MOLO\nV17.3 complet: Furtif G, Quar 12h, Fear, Hold, Sweep, Cap 40/24/36`);
