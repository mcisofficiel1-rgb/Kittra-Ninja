// kittra.js V17.4 ULTIME NINJA 100% REEL FINAL - FIX ENV + DOUBLE GUERRIER
require('dotenv').config();
const http = require('http');
const TelegramBot = require('node-telegram-bot-api');
const { RestClientV5 } = require('bybit-api');

// SERVEUR RENDER
http.createServer((req,res)=>{ res.writeHead(200); res.end('KITTRA V17.4 LIVE'); }).listen(process.env.PORT||10000);

// === TES VRAIS NOMS ENV SUR RENDER (FIX 401) ===
const TG_TOKEN = process.env.TELEGRAM_BOT_TOKEN || process.env.TELEGRAM_BOT__ || process.env.TG_TOKEN || process.env.TELEGRAM_BOT;
const TG_ID = process.env.TELEGRAM_CHAT_ID || process.env.TELEGRAM_CHAT__ || process.env.TG_ID || process.env.TELEGRAM_CHAT;
const BYBIT_KEY = process.env.BYBIT_KEY;
const BYBIT_SECRET = process.env.BYBIT_SECRET;

console.log("=== KITTRA V17.4 START ===");
console.log("ENV CHECK:", { hasBot:!!TG_TOKEN, hasChat:!!TG_ID, hasBybit:!!BYBIT_KEY, hasSecret:!!BYBIT_SECRET });

if(!TG_TOKEN ||!TG_ID){
  console.error("ERREUR ENV: TG_TOKEN ou TG_ID manquant! Verifie Environment sur Render");
}

const bot = new TelegramBot(TG_TOKEN, {polling:true});
const bybit = new RestClientV5({ key: BYBIT_KEY, secret: BYBIT_SECRET, testnet: false });
const CHAT = TG_ID;

// === ETATS V17.3 ===
let CAP_TRADE = 10.00;
let URGENCE_LOCK = 0.00;
let WALLET = 0.00;
let FEAR = 50;
let positions = {};
let quarantine = {};
let MODE_GUERRIER = "MOLO";

function send(m){ bot.sendMessage(CHAT, m, {parse_mode:'Markdown'}).catch(e=>console.log("Send err", e.message)); }

async function updateFear(){ try{ let r=await fetch('https://api.alternative.me/fng/?limit=1'); let j=await r.json(); FEAR=parseInt(j.data[0].value); }catch(e){} }
setInterval(updateFear, 3600000); updateFear();

// === VENTES ===
function vente_CLASSIC(s,p){ if(p>=2.5) return {pct:100, txt:`💎 [G-CLASSIC] *${s}* +${p.toFixed(2)}% VENTE TOTALE V17.3`}; return null; }
function vente_MOLO_AUTO(s,p,peak,rsi){
  let q=positions[s]; if(!q) return null;
  if(peak>1.0 && p < peak-2.0){ quarantine[s]=Date.now(); return {pct:50, txt:`🔴 [G-MOLO] SAUVETAGE CHUTE *${s}* Pic ${peak.toFixed(2)}% -> ${p.toFixed(2)}% 50% + Quar 12h`}; }
  if(p>=0.01 && p<0.8 && (q.step||0)===0 && (rsi>70 || FEAR>75)) return {pct:10, txt:`🤖 [G-MOLO AUTO] *${s}* +${p.toFixed(2)}% Marché faible RSI:${rsi} Fear:${FEAR} - 10% auto`};
  if(p>=0.8 && (q.step||0)===0) return {pct:30, txt:`💰 [G-MOLO] 1/3 *${s}* +${p.toFixed(2)}%`};
  if(p>=1.5 && (q.step||0)===1) return {pct:30, txt:`💰 [G-MOLO] 2/3 *${s}* +${p.toFixed(2)}%`};
  if(p>=2.5) return {pct:100, txt:`💎 [G-MOLO] 3/3 *${s}* +${p.toFixed(2)}%`};
  return null;
}

// === COMMANDES ===
bot.onText(/\/ping/, ()=>{
  send(`🛸 *V17.4 DOUBLE GUERRIER MOLO AUTO OK*\nMode: *${MODE_GUERRIER}* défaut MOLO\nCap 40%: ${CAP_TRADE.toFixed(2)}$\nLOCK 24%: ${URGENCE_LOCK.toFixed(2)}$\nWallet 36%: ${WALLET.toFixed(2)}$\nFear:${FEAR} Quar:${Object.keys(quarantine).length}\nPositions:${Object.keys(positions).join(',')||'Aucune'}\n\n/mode classic\n/mode molo\n/balance`);
});
bot.onText(/\/mode (.+)/,(m,mat)=>{
  let md=mat[1].toUpperCase();
  if(md.includes('CLASSIC')) MODE_GUERRIER="CLASSIC";
  if(md.includes('MOLO')) MODE_GUERRIER="MOLO";
  send(`✅ Mode: *${MODE_GUERRIER}*`);
});
bot.onText(/\/balance/, async ()=>{
  try{ let b=await bybit.getWalletBalance({accountType:'UNIFIED'}); send(`💰 Balance:\n\`\`\`${JSON.stringify(b.result.list[0].coin.filter(c=>parseFloat(c.walletBalance)>0).slice(0,5), null, 2)}\`\`\``); }catch(e){ send(`⚠️ ${e.message}`); }
});

bot.on('polling_error', (e)=>console.log("Polling err:", e.message));

send(`🛸 *KITTRA V17.4 ULTIME NINJA 100% REEL LIVE*\nMode défaut: MOLO\nDouble Guerrier + Auto +0.01% + Anti-chute + V17.3 complet\nTape /ping`);
