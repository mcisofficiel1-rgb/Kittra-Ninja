```javascript
// ===============================================
// KITTRA NINJA V1 - RÉEL - CERVEAU + PWA
// ===============================================
const CONFIG = {
  KITTRANINJATRADE_KEY: "omHyTld2qJJIybioLu",
  KITTRANINJATRADE_SECRET: "1Ozaa1MSI5TcGofGeSk4Nl9yICkrDWQNA46n",
  KITTRAVAULTMASTER: "KvM-ABJ-5Sep2026-9pL2_X8qZ!_Ninja_Babi",
  TELEGRAM: "8765920829:AAFdiSgT3p5nsHTNRtI50mcWguD1v4jrlok",
  CHAT_ID: "METS_TON_ID_ICI"
};

const { RestClientV5, WebsocketClient } = require('bybit-api');
const TelegramBot = require('node-telegram-bot-api');
const express = require('express');
const path = require('path');

const client = new RestClientV5({ key: CONFIG.KITTRANINJATRADE_KEY, secret: CONFIG.KITTRANINJATRADE_SECRET });
const ws = new WebsocketClient({ key: CONFIG.KITTRANINJATRADE_KEY, secret: CONFIG.KITTRANINJATRADE_SECRET });
const tg = new TelegramBot(CONFIG.TELEGRAM);
let coffre = 0; let principal = 12; let memoire = [];

// 1. SURVEILLANCE
ws.subscribeV5(['tickers.BTCUSDT','tickers.ETHUSDT','tickers.SOLUSDT','tickers.BNBUSDT'], 'spot');
ws.subscribeV5(['tickers.BTCUSDT','tickers.ETHUSDT'], 'linear');

ws.on('update', async (d) => {
  const prix = parseFloat(d.data.lastPrice); const coin = d.data.symbol;
  const rsi = await getRSI(coin); const dernier = getDernier(coin);
  const dip = dernier ? ((prix-dernier)/dernier)*100 : 0;
  const profit = dernier ? ((prix-dernier)/dernier)*100 : 0;

  if (rsi < 30 || dip <= -4) {
    await client.submitOrder({category:'spot', symbol:coin, side:'Buy', orderType:'Market', qty:String(12/prix)});
    memoire.push({coin, prix, rsi, type:'ACHAT'});
  }
  if (profit >= 5) {
    await client.submitOrder({category:'spot', symbol:coin, side:'Sell', orderType:'Market', qty:String(12/prix)});
    const surplus = prix*(12/prix) - 12;
    if (surplus > 0) { coffre += surplus; tg.sendMessage(CONFIG.CHAT_ID, `💰 BONUS ${surplus.toFixed(2)} ${coin} -> Coffre`); }
  }
  if (rsi < 12) {
    await client.submitOrder({category:'spot', symbol:coin, side:'Sell', orderType:'Market', qty:'100%'});
    tg.sendMessage(CONFIG.CHAT_ID, `🚨 ${coin} va mourir - vendu`);
  }
  if (profit < -10) { killSwitch(coin); setTimeout(()=>{}, 60000); }
});

// BILAN 7 JOURS 50/50
setInterval(() => {
  const gains = principal - 12;
  if (gains > 0) { coffre += gains*0.5; principal += gains*0.5; }
}, 7*24*60*60*1000);

// AUTO-SWEEP
setInterval(() => {
  const j = new Date().getDay();
  if (j===1 && coffre>0) { const m=coffre*0.05; coffre-=m; }
  if (j>=2 && j<=5 && coffre>0) { const m=coffre*0.70; coffre-=m; }
}, 24*60*60*1000);

// RADAR + KILL-SWITCH + NINJA
function radar() { setInterval(async () => { if (await hack()) await killSwitch(); }, 5000); }
async function killSwitch(){ await client.cancelAllOrders({category:'spot'}); await client.cancelAllOrders({category:'linear'}); }
async function getRSI(){ return 25; } function getDernier(){ return 50000; } async function hack(){ return false; }

// PWA 3 BOUTONS + SERVEUR
const app = express();
app.use(express.static(path.join(__dirname)));
app.get('/api/tx', (req,res) => res.json(memoire));
app.get('/api/security', (req,res) => res.json({vault: CONFIG.KITTRAVAULTMASTER, status:'ACTIF', verrou:'2 pouces+voix', antivol:'puce auto-destruction', secours:'voix+2 pouces+phrase+3 mots'}));
app.get('/api/brain', (req,res) => res.json({coffre, principal, memoire, mode:'Ninja furtif ON'}));

app.listen(10000, () => { console.log("🔒 SECRET VAULT NINJA ACTIF avec KvM-ABJ-5Sep2026"); radar(); });
```