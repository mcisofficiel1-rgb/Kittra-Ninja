// KITTRA v16.1 NINJA BABI - Version Web Service Gratuit 100%
require('http').createServer((req,res) => res.end('Kittra v16.1 LIVE Ninja Babi')).listen(process.env.PORT || 10000);

const { RestClientV5 } = require('bybit-api');

const client = new RestClientV5({
  key: process.env.BYBIT_KEY,
  secret: process.env.BYBIT_SECRET,
  testnet: false
});

console.log("🔐 Kittra v16.1 démarré");
console.log("BYBIT_KEY:", process.env.BYBIT_KEY ? "OK" : "MANQUE");
console.log("BYBIT_SECRET:", process.env.BYBIT_SECRET ? "OK" : "MANQUE");
console.log("TELEGRAM:", process.env.TELEGRAM_BOT_TOKEN ? "OK" : "MANQUE");

async function scanNewListings() {
  try {
    console.log("👀 Scan listings...");
    // Ta logique ici
    // const res = await client.getInstrumentsInfo({ category: 'spot' });
  } catch (e) {
    console.log("Erreur scan:", e.message);
  }
}

scanNewListings();
setInterval(scanNewListings, 60000);

console.log("✅ Kittra LIVE - Web Service OK");
