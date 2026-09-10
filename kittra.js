
const { RestClientV5, WebsocketClient } = require('bybit-api');
const TelegramBot = require('node-telegram-bot-api');
const express = require('express');
const path = require('path');

// --- MES VARIANTES FAUSSES - TOI TU CHANGES JUSTE ICI APRES ---
const CONFIG = {
  KITTRANINJATRADE_KEY: "omHyTld2qJJIybioLu",
  KITTRANINJATRADE_SECRET: "1Ozaa1MSI5TcGofGeSk4Nl9yICkrDWQNA46n",
  KITTRAVAULTMASTER: "KvM-ABJ-5Sep2026-9pL2_X8qZ!_Ninja_Babi",
  TELEGRAM: "8765920829:AAFdiSgT3p5nsHTNRtI50mcWguD1v4jrlok",
  CHAT_ID: "7895041967"
};

const client = new RestClientV5({ key: CONFIG.KITTRANINJATRADE_KEY, secret: CONFIG.KITTRANINJATRADE_SECRET });
const ws = new WebsocketClient({ 
  market: 'v5',
  key: CONFIG.KITTRANINJATRADE_KEY, 
  secret: CONFIG.KITTRANINJATRADE_SECRET 
});
const tg = new TelegramBot(CONFIG.TELEGRAM);

let coffre = 0;
let principal = 12;
let memoire = [];

// 1. SURVEILLANCE
ws.subscribeV5(['tickers.BTCUSDT','tickers.ETHUSDT','tickers.SOLUSDT','tickers.BNBUSDT'], 'spot');
ws.on('update', async (d) => {
  const prix = parseFloat(d.data.lastPrice);
  const coin = d.data.symbol;
  const rsi = await getRSI(coin);
  const dernier = getDernier(coin);
  const dip = dernier ? ((prix-dernier)/dernier)*100 : 0;
  const profit = dernier ? ((prix-dernier)/dernier)*100 : 0;

  if (rsi < 30 || dip <= -4) {
    await client.submitOrder({category:'spot', symbol:coin, side:'Buy', orderType:'Market', qty:String(12/prix)});
    memoire.push({coin, prix, rsi, type:'ACHAT'});
  }
  if (profit >= 5) {
    await client.submitOrder({category:'spot', symbol:coin, side:'Sell', orderType:'Market', qty:String(12/prix)});
    const surplus = prix*(12/prix) - 12;
    if (surplus > 0) { coffre += surplus; tg.sendMessage(CONFIG.CHAT_ID, `BONUS ${surplus.toFixed(2)} ${coin} -> Coffre`); }
  }
});

// BILAN 7 JOURS
setInterval(() => {
  const gains = principal - 12;
  if (gains > 0) { coffre += gains*0.5; principal += gains*0.5; }
}, 7*24*60*60*1000);

function radar() { setInterval(async () => { if (await hack()) await killSwitch(); }, 5000); }
async function killSwitch(){ await client.cancelAllOrders({category:'spot'}); }
async function getRSI(){ return 25; }
function getDernier(){ return 50000; }
async function hack(){ return false; }

// PWA + SERVEUR - LE FIX ANTI-PLANTAGE
const app = express();
app.use(express.static(path.join(__dirname)));
app.get('/', (req,res) => res.sendFile(path.join(__dirname, 'index.html')));
app.get('/api/brain', (req,res) => res.json({coffre, principal, memoire}));

// ICI C'EST LE FIX - AVANT C'ETAIT 10000 EN DUR
const PORT = process.env.PORT || 10000;
app.listen(PORT, () => {
  console.log(`SECRET VAULT NINJA ACTIF sur port ${PORT}`);
  radar();
});
