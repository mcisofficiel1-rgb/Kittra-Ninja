const express = require('express');
const path = require('path');
const fs = require('fs');
const { RestClientV5, WebsocketClient } = require('bybit-api');
const TelegramBot = require('node-telegram-bot-api');

// ===== 1. TES CLÉS GARDIEN =====
const BYBIT_API_KEY = "omHyTld2qJJIybioLu";
const BYBIT_API_SECRET = "1Ozaa1MSI5TcGofGeSk4Nl9yICkrDWQNA46n";
const TELEGRAM_TOKEN = "8765920829:AAFdiSgT3p5nsHTNRtI50mcWguD1v4jrlok";
const TELEGRAM_CHAT_ID = "7895041967";
const MON_WALLET_COFFRE_FORT = "TG8UcJUH152YyWsSArL4cwwV78GZijYJoqG";
const CHAINE_COFFRE = 'TRC20';

// ===== 2. CONFIG - CAPITAL SACRÉ V12 =====
const CONFIG = {
  principal: 10, // CAPITAL SACRÉ. NE DOIT JAMAIS DESCENDRE
  urgences_usdt: 0,
  usdt_par_achat: 1,
  coffre_total: 0,
  liste_coins: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
  jour_sweep: 0, // Dimanche 18h
  repartition: { trading: 40, urgences: 24, business: 12, maison: 8, enfants: 4 },
  TAKE_PROFIT: 5,
  STOP_LOSS: -7
};

const client = new RestClientV5({ key: BYBIT_API_KEY, secret: BYBIT_API_SECRET, testnet: false });
const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname)));

const bot = new TelegramBot(TELEGRAM_TOKEN);

// ===== 3. MÉMOIRE + ANTI-DORMEUR =====
let MEMOIRE = { trades: [], gains: 0, pertes: 0, niveau: 1, coffres: {business:0, maison:0, enfants:0}, kill_switch: false, derniereActivite: Date.now() };
let POSITIONS = {};
let PRIX_LAST = { BTCUSDT: 65000, ETHUSDT: 3500, SOLUSDT: 150 };
let HISTORIQUE_PRIX = { BTCUSDT: [], ETHUSDT: [], SOLUSDT: [] }; // AMELIORATION 1: VRAI RSI

try{ if(fs.existsSync('./memoire.json')) MEMOIRE = JSON.parse(fs.readFileSync('./memoire.json')); }catch(e){}
function saveMemoire(){ try{ fs.writeFileSync('./memoire.json', JSON.stringify(MEMOIRE)); }catch(e){} }

async function alerte(msg){
    console.log(msg);
    await bot.sendMessage(TELEGRAM_CHAT_ID, `🤖 KITTRA V12: ${msg}`).catch(()=>{});
}

function activerKillSwitch(raison){
  MEMOIRE.kill_switch = true;
  alerte(`🚨 KILL-SWITCH ACTIVÉ: ${raison}. Capital=${CONFIG.principal.toFixed(2)}$`);
}

// ===== 4. AMELIORATION 1: VRAI CALCUL RSI =====
function calculerRSI(coin){
    const prix = HISTORIQUE_PRIX[coin];
    if(prix.length < 15) return 50;
    let gains=0, pertes=0;
    for(let i=1; i<prix.length; i++){
        let diff = prix[i] - prix[i-1];
        if(diff > 0) gains += diff; else pertes -= diff;
    }
    let rs = gains / pertes;
    return 100 - (100 / (1 + rs));
}

// ===== 5. FONCTIONS BYBIT =====
async function acheter(symbol, montantUSDT){
  const qty = montantUSDT / PRIX_LAST[symbol];
  await client.submitOrder({ category: 'spot', symbol, side: 'Buy', orderType: 'Market', qty: qty.toFixed(6) });
  return {ok: true, qty: qty.toFixed(6), prix: PRIX_LAST[symbol]};
}

async function vendre(symbol){
  const position = POSITIONS[symbol];
  await client.submitOrder({ category: 'spot', symbol, side: 'Sell', orderType: 'Market', qty: position.qty });
  return {ok: true, prix: PRIX_LAST[symbol]};
}

async function envoyerVersCoffreFort(nomCoffre, montant){
  if(montant < 1) return;
  try{
    await client.submitWithdrawal({ coin: 'USDT', chain: CHAINE_COFFRE, address: MON_WALLET_COFFRE_FORT, amount: montant.toFixed(2) });
    alerte(`💰 ${montant.toFixed(2)} USDT ENVOYÉ AU COFFRE: ${nomCoffre.toUpperCase()}`);
  }catch(e){ alerte(`❌ ERREUR RETRAIT: ${e.message}`); }
}

// ===== 6. LOGIQUE TRADING V12 AMELIORÉ =====
function phase_SURVEILLANCE(){
  for(let coin of CONFIG.liste_coins){
    let prix = PRIX_LAST[coin];
    let rsi = calculerRSI(coin); // AMELIORATION 1: RSI REEL

    if(!POSITIONS[coin]){
        if(rsi < 30) return {action:"ACHAT", coin, rsi};
    } else {
        let profit = ((prix - POSITIONS[coin].prixEntree)/POSITIONS[coin].prixEntree)*100;
        if(profit >= CONFIG.TAKE_PROFIT || profit <= CONFIG.STOP_LOSS)
            return {action:"VENTE", coin, profit, rsi};
    }
  }
  return {action:"SURVEILLANCE"};
}

async function phase_ACTION(signal){
  MEMOIRE.derniereActivite = Date.now(); // AMELIORATION 2: TRACKER ACTIVITE

  if(signal.action=="ACHAT"){
    if(CONFIG.principal >= CONFIG.usdt_par_achat){
      let res = await acheter(signal.coin, CONFIG.usdt_par_achat);
      if(res.ok){
        CONFIG.principal -= CONFIG.usdt_par_achat;
        POSITIONS[signal.coin] = {prixEntree: res.prix, qty: res.qty};
        MEMOIRE.trades.push({type:"ACHAT", coin:signal.coin, montant:CONFIG.usdt_par_achat});
        alerte(`🟢 ACHAT ${signal.coin} à ${res.prix}$ | RSI: ${signal.rsi.toFixed(0)}`);
      }
    }
  }

  if(signal.action=="VENTE"){
    let res = await vendre(signal.coin);
    if(res.ok){
      let valeurVente = POSITIONS[signal.coin].qty * res.prix;
      let valeurAchat = POSITIONS[signal.coin].qty * POSITIONS[signal.coin].prixEntree;
      let profitUSDT = valeurVente - valeurAchat;

      if(profitUSDT > 0){
        CONFIG.coffre_total += profitUSDT; // SURPLUS AU COFFRE
        CONFIG.principal += valeurAchat; // CAPITAL RESTE INTACT
        MEMOIRE.gains++;
      } else {
        CONFIG.principal += valeurVente; // PERTE SUR CAPITAL
        MEMOIRE.pertes++;
        if(CONFIG.principal < 5) activerKillSwitch("Capital < 5$");
      }
      delete POSITIONS[signal.coin];
      alerte(`🔴 VENTE ${signal.coin} | P&L: ${signal.profit.toFixed(2)}% | Coffre: +${profitUSDT.toFixed(3)}$`);
    }
  }
  saveMemoire();
}

// ===== 7. RÉPARTITION DIMANCHE V12 =====
async function repartirEtSweeper(){
  if(CONFIG.coffre_total < 2) return;
  let rep = CONFIG.repartition;
  let totalProfit = CONFIG.coffre_total;

  let resteTrading = totalProfit * (rep.trading/100);
  let resteUrgences = totalProfit * (rep.urgences/100);
  CONFIG.principal += resteTrading;
  CONFIG.urgences_usdt += resteUrgences;

  let aSweeper = totalProfit * ((100 - rep.trading - rep.urgences)/100);
  let montants = {
    business: aSweeper * (rep.business/(100-rep.trading-rep.urgences)),
    maison: aSweeper * (rep.maison/(100-rep.trading-rep.urgences)),
    enfants: aSweeper * (rep.enfants/(100-rep.trading-rep.urgences)),
  };

  let message = `📊 RÉPARTITION HEBDO\n`;
  for(let coffre in montants){
      await envoyerVersCoffreFort(coffre, montants[coffre]);
      MEMOIRE.coffres[coffre] += montants[coffre];
      message += `${coffre.toUpperCase()}: +${montants[coffre].toFixed(2)}$\n`;
  }
  message += `TRADING: +${resteTrading.toFixed(2)}$\nURGENCES: +${resteUrgences.toFixed(2)}$`;

  CONFIG.coffre_total = 0;
  saveMemoire();
  alerte(message);
}

// ===== 8. WEBSOCKET + BOUCLES =====
const ws = new WebsocketClient({ market: 'v5', key: BYBIT_API_KEY, secret: BYBIT_API_SECRET, testnet: false });
ws.subscribeV5(CONFIG.liste_coins.map(c=>`tickers.${c}`), 'spot');
ws.on('update', (d)=>{
    let coin = d.data.symbol;
    let prix = parseFloat(d.data.lastPrice);
    PRIX_LAST[coin] = prix;
    HISTORIQUE_PRIX[coin].push(prix); // Pour RSI
    if(HISTORIQUE_PRIX[coin].length > 100) HISTORIQUE_PRIX[coin].shift(); // Garde 100 bougies
});

// Boucle Trading toutes 15s
setInterval(async ()=>{
    if(!MEMOIRE.kill_switch){
        let sig = phase_SURVEILLANCE();
        if(sig.action!="SURVEILLANCE") await phase_ACTION(sig);
    }
}, 15000);

// Boucle Répartition 1x/heure
setInterval(async ()=>{
    let date = new Date();
    if(date.getDay() == CONFIG.jour_sweep && date.getHours() == 18){
        await repartirEtSweeper();
    }
}, 1000*60*60);

// ===== 9. AMELIORATION 3: ROUTE ANTI-DORMEUR POUR UPTIMEROBOT =====
app.get('/ping', (req,res)=>{
    res.json({status: "KITTRA V12 EST ÉVEILLÉ 👑", capital: CONFIG.principal, coffre: CONFIG.coffre_total});
});

// ===== 10. AMELIORATION 4: DASHBOARD API =====
app.get('/api/status', (req,res)=> res.json({
    principal: CONFIG.principal.toFixed(2),
    urgences_usdt: CONFIG.urgences_usdt.toFixed(2),
    coffre_total: CONFIG.coffre_total.toFixed(2),
    coffres: MEMOIRE.coffres,
    positions: POSITIONS,
    derniereActivite: new Date(MEMOIRE.derniereActivite).toLocaleString()
}));

app.listen(process.env.PORT||10000, ()=> alerte(`V12 COFFRE-FORT ACTIF. Mode PAS DEPO. Surveillance H24`));
