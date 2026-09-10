const { RestClientV5, WebsocketClient } = require('bybit-api');
const TelegramBot = require('node-telegram-bot-api');
const express = require('express');
const path = require('path');

const CONFIG = {
  KITTRANINJATRADE_KEY: "omHyTld2qJJIybioLu",
  KITTRANINJATRADE_SECRET: "1Ozaa1MSI5TcGofGeSk4Nl9yICkrDWQNA46n",
  KITTRAVAULTMASTER: "KvM-ABJ-5Sep2026-9pL2_X8qZ!_Ninja_Babi ",
  TELEGRAM: "8765920829:AAFdiSgT3p5nsHTNRtI50mcWguD1v4jrlok",
  CHAT_ID: "7895041967"
};

const client = new RestClientV5({ 
  key: CONFIG.KITTRANINJATRADE_KEY, 
  secret: CONFIG.KITTRANINJATRADE_SECRET 
});

const ws = new WebsocketClient({ 
  market: 'v5',
  key: CONFIG.KITTRANINJATRADE_KEY, 
  secret: CONFIG.KITTRANINJATRADE_SECRET
});

const tg = new TelegramBot(CONFIG.TELEGRAM);

let coffre = 0;
let principal = 12;
let memoire = [];

ws.subscribeV5(['tickers.BTCUSDT','tickers.ETHUSDT'], 'spot');

ws.on('update', async (d) => {
  console.log("Prix reçu:", d.data.symbol, d.data.lastPrice);
});

const app = express();
app.use(express.static(path.join(__dirname)));
app.get('/', (req,res) => res.sendFile(path.join(__dirname, 'index.html')));
app.get('/api/brain', (req,res) => res.json({coffre, principal, memoire}));

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => {
  console.log(`SECRET VAULT NINJA ACTIF sur port ${PORT}`);
});
