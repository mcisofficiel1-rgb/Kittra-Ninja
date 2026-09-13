// KITTRA v16.1 - Ninja Babi Edition
// 7 Coffres Render - Modèle sde123@

require('dotenv').config();
const config = {
  BYBIT_KEY: process.env.BYBIT_KEY, // ex: sde123@_BybitKey_Babi
  BYBIT_SECRET: process.env.BYBIT_SECRET, // ex: sde123@_BybitSecret_Babi_Long
  TELEGRAM_TOKEN: process.env.TELEGRAM_BOT_TOKEN,
  TELEGRAM_CHAT_ID: process.env.TELEGRAM_CHAT_ID,
  BYBIT_DEMO: process.env.BYBIT_DEMO === 'true' || process.env.BYBIT_DEMO === 'false' ? process.env.BYBIT_DEMO : 'false',
  MASTER_KEY: process.env.MASTER_KEY, // ex: sde123@_Master_KvM-ABJ-5Sep_Ninja_Babi
  WALLET_ADDRESS: process.env.WALLET_ADDRESS // ex: sde123@_Wallet_0x1234Babi
};

// Vérif que les 7 cases sont bien là
console.log("🔐 Vérif coffres Render:");
console.log("BYBIT_KEY:", config.BYBIT_KEY ? "OK" : "MANQUE");
console.log("BYBIT_SECRET:", config.BYBIT_SECRET ? "OK" : "MANQUE");
console.log("MASTER:", config.MASTER_KEY);

const { RestClientV5 } = require('bybit-api');

const client = new RestClientV5({
  key: config.BYBIT_KEY,
  secret: config.BYBIT_SECRET,
  testnet: config.BYBIT_DEMO === 'true'
});

async function scanNewListings() {
  console.log("👀 Kittra v16.1 scan en cours...");
  // Ta logique de listing ici
  // const listings = await client.getTickers...
  // if (listing valide) -> envoie Telegram
}

function sendTelegram(msg) {
  const url = `https://api.telegram.org/bot${config.TELEGRAM_TOKEN}/sendMessage?chat_id=${config.TELEGRAM_CHAT_ID}&text=${msg}`;
  fetch(url);
}

// Lancement
scanNewListings();
setInterval(scanNewListings, 60000); // scan toutes les 60s
