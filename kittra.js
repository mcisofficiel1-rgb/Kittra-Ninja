// ==========================================
// KITTRA-NINJA-V16.1 FINAL - FULL PROPRE
// By Babi - Render Web Service Gratuit
// ==========================================
require('http').createServer((req,res) => res.end('Kittra V16.1 LIVE')).listen(process.env.PORT || 10000);

const { RestClientV5 } = require('bybit-api');

// --- CONFIG ---
const client = new RestClientV5({
  key: process.env.BYBIT_KEY,
  secret: process.env.BYBIT_SECRET,
  testnet: false
});

const TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT = process.env.TELEGRAM_CHAT_ID;
let knownSymbols = new Set();
let firstRun = true;

// --- TELEGRAM ---
async function sendTelegram(text) {
  if(!TELEGRAM_TOKEN || !TELEGRAM_CHAT) {
    console.log("⚠️ Telegram non configuré");
    return;
  }
  try {
    const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;
    await fetch(url, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ chat_id: TELEGRAM_CHAT, text: text, parse_mode: 'Markdown' })
    });
    console.log("📨 Telegram OK");
  } catch(e) { console.log("Telegram ERR:", e.message) }
}

// --- SCAN V16.1 ---
async function scan() {
  try {
    const response = await client.getInstrumentsInfo({ category: 'spot' });
    const list = response.result.list;

    if(firstRun) {
      list.forEach(c => knownSymbols.add(c.symbol));
      console.log(`👀 Initialisation: ${knownSymbols.size} coins chargés`);
      await sendTelegram(`✅ *Kittra V16.1 démarrée*\n\n👀 ${knownSymbols.size} coins en mémoire\n🚀 Surveillance des nouveaux listings active`);
      firstRun = false;
      return;
    }

    for(const coin of list) {
      if(!knownSymbols.has(coin.symbol)) {
        console.log(`🚀 NOUVEAU LISTING: ${coin.symbol}`);
        knownSymbols.add(coin.symbol);
        
        // Seulement les paires USDT nouvelles
        if(coin.symbol.endsWith('USDT')) {
          await sendTelegram(
            `🚀 *NOUVEAU LISTING BYBIT DETECTÉ*\n\n` +
            `💎 *${coin.symbol}*\n` +
            `📅 ${new Date().toLocaleString()}\n` +
            `⚡ Kittra-Ninja-V16.1`
          );
        }
      }
    }
    console.log(`✅ Scan OK - ${knownSymbols.size} coins`);

  } catch(err) {
    console.log("❌ Erreur scan:", err.message);
  }
}

// --- LANCEMENT ---
console.log("🔐 Kittra-Ninja-V16.1 FULL démarrée");
console.log("BYBIT_KEY:", process.env.BYBIT_KEY ? "OK" : "MANQUE");
console.log("BYBIT_SECRET:", process.env.BYBIT_SECRET ? "OK" : "MANQUE");

scan();
setInterval(scan, 30000); // scan toutes les 30 secondes
