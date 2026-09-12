const express = require('express');
const path = require('path');
const fs = require('fs');
const { RestClientV5, WebsocketClient } = require('bybit-api');
const TelegramBot = require('node-telegram-bot-api');

// ===== 1. TES VARIANTES - TU METS TES VRAIES CLES ICI FACILEMENT =====
const BYBIT_API_KEY = "omHyTld2qJJIybioLu"; // <-- MET TA CLE API ICI
const BYBIT_API_SECRET = "1Ozaa1MSI5TcGofGeSk4Nl9yICkrDWQNA46n"; // <-- MET TON SECRET ICI
const MASTER_KEY = "KvM-ABJ-5Sep2026-9pL2_X8qZ!_Ninja_Babi"; // <-- MASTER
const TELEGRAM_TOKEN = "8765920829:AAFdiSgT3p5nsHTNRtI50mcWguD1v4jrlok"; // <-- TOKEN TELEGRAM
const TELEGRAM_CHAT_ID = "7895041967";
const MON_WALLET_COFFRE_FORT = "TG8UcJUH152YyWsSArL4cwwV78GZijYJoqG";

// ===== 2. CONFIG =====
const CONFIG = { principal: 10, usdt_par_achat: 1, liste_coins: ['BTCUSDT','ETHUSDT','SOLUSDT'], TAKE_PROFIT: 5, STOP_LOSS: -7 };
const client = new RestClientV5({ key: BYBIT_API_KEY, secret: BYBIT_API_SECRET, testnet: false });
const app = express();
app.use(express.json());
const bot = new TelegramBot(TELEGRAM_TOKEN);

let POSITIONS = {};
let PRIX_LAST = { BTCUSDT: 65000, ETHUSDT: 3500, SOLUSDT: 150 };
let HISTORIQUE_PRIX = { BTCUSDT: [], ETHUSDT: [], SOLUSDT: [] };

function calculerRSI(coin){
    const prix = HISTORIQUE_PRIX[coin]; if(prix.length < 15) return 50;
    let gains=0, pertes=0; for(let i=1; i<prix.length; i++){ let diff = prix[i]-prix[i-1]; if(diff>0) gains+=diff; else pertes-=diff; }
    if(pertes===0) return 70; return 100 - (100/(1+gains/(pertes||1)));
}
async function acheter(symbol, montant){ const qty = montant / PRIX_LAST[symbol]; await client.submitOrder({ category:'spot', symbol, side:'Buy', orderType:'Market', qty:qty.toFixed(6) }); return {ok:true, qty:qty.toFixed(6), prix:PRIX_LAST[symbol]}; }
async function vendre(symbol){ const position = POSITIONS[symbol]; await client.submitOrder({ category:'spot', symbol, side:'Sell', orderType:'Market', qty:position.qty }); return {ok:true, prix:PRIX_LAST[symbol]}; }

function phase_SURVEILLANCE(){
  for(let coin of CONFIG.liste_coins){
    let prix = PRIX_LAST[coin]; let rsi = calculerRSI(coin);
    if(!POSITIONS[coin] && rsi < 30) return {action:"ACHAT", coin, rsi};
    if(POSITIONS[coin]){ let profit = ((prix - POSITIONS[coin].prixEntree)/POSITIONS[coin].prixEntree)*100; if(profit >= CONFIG.TAKE_PROFIT || profit <= CONFIG.STOP_LOSS) return {action:"VENTE", coin, profit, rsi}; }
  } return {action:"SURVEILLANCE"};
}
async function phase_ACTION(signal){
  if(signal.action=="ACHAT" && CONFIG.principal >= CONFIG.usdt_par_achat){
      let res = await acheter(signal.coin, CONFIG.usdt_par_achat);
      if(res.ok){ CONFIG.principal -= CONFIG.usdt_par_achat; POSITIONS[signal.coin] = {prixEntree: res.prix, qty: res.qty}; console.log(`ACHAT ${signal.coin}`); bot.sendMessage(TELEGRAM_CHAT_ID, `🟢 ACHAT ${signal.coin} RSI ${signal.rsi.toFixed(0)}`).catch(()=>{}); }
  }
  if(signal.action=="VENTE"){
    let res = await vendre(signal.coin); if(res.ok){ let vVente = POSITIONS[signal.coin].qty * res.prix; let vAchat = POSITIONS[signal.coin].qty * POSITIONS[signal.coin].prixEntree; CONFIG.principal += vAchat + (vVente-vAchat>0?0:vVente-vAchat); delete POSITIONS[signal.coin]; bot.sendMessage(TELEGRAM_CHAT_ID, `🔴 VENTE ${signal.coin} ${signal.profit.toFixed(2)}%`).catch(()=>{}); }
  }
}

// WEBSOCKET AVEC RECONNEXION
function startWS(){
  const ws = new WebsocketClient({ market: 'v5', key: BYBIT_API_KEY, secret: BYBIT_API_SECRET });
  ws.subscribeV5(CONFIG.liste_coins.map(c=>`tickers.${c}`), 'spot');
  ws.on('update', (d)=>{ if(!d.data?.symbol) return; let coin=d.data.symbol; let prix=parseFloat(d.data.lastPrice); PRIX_LAST[coin]=prix; HISTORIQUE_PRIX[coin].push(prix); if(HISTORIQUE_PRIX[coin].length>100) HISTORIQUE_PRIX[coin].shift(); });
  ws.on('close', ()=> setTimeout(startWS, 5000));
}
startWS();
setInterval(async ()=>{ let sig=phase_SURVEILLANCE(); if(sig.action!="SURVEILLANCE") await phase_ACTION(sig); }, 15000);

// CORRECTION PORT RENDER - C'EST CA QUI ENLEVE TON ERREUR
app.get('/', (req,res)=> res.send('KITTRA V13 VIVANT avec MASTER '+MASTER_KEY));
app.get('/ping', (req,res)=> res.json({status:"V13 EVEILLE", master: MASTER_KEY, prix:PRIX_LAST}));

const PORT = process.env.PORT || 10000;
app.listen(PORT, '0.0.0.0', ()=> console.log(`V13 ACTIF sur port ${PORT} - MASTER ${MASTER_KEY}`));
