const express = require('express');
const path = require('path');
const fs = require('fs');
const { RestClientV5 } = require('bybit-api');

// 1. TES CLÉS
const VAULT = "KvM-ABJ-5Sep2026-9pL2_X8qZ!_Ninja_Babi";
const BYBIT_API_KEY = "omHyTld2qJJIybioLu";
const BYBIT_API_SECRET = "1Ozaa1MSI5TcGofGeSk4Nl9yICkrDWQNA46n";
const TELEGRAM_TOKEN = "8765920829:AAFdiSgT3p5nsHTNRtI50mcWguD1v4jrlok";
const TELEGRAM_CHAT_ID = "7895041967";
const MON_WALLET_COFFRE_FORT = "TG8UcJUH152YyWsSArL4cwwV78GZijYJoqG";
const CHAINE_COFFRE = 'TRC20';
const client = new RestClientV5({ key: BYBIT_API_KEY, secret: BYBIT_API_SECRET, testnet: false });

// 2. CONFIG - CAPITAL SACRÉ
const CONFIG = {
  principal: 10, // CAPITAL SACRÉ. NE DOIT JAMAIS DESCENDRE
  urgences_usdt: 0,
  usdt_par_achat: 1,
  coffre_total: 0, // TOUS LES SURPLUS VONT ICI
  liste_coins: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
  jour_sweep: 0, // Dimanche 18h
  repartition: { trading: 40, urgences: 24, business: 12, maison: 8, enfants: 4 }
};

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname)));
let bot = null; try { const TelegramBot = require('node-telegram-bot-api'); bot = new TelegramBot(TELEGRAM_TOKEN, { polling: false }); } catch(e){}
let MEMOIRE = { trades: [], gains: 0, pertes: 0, niveau: 1, coffres: {business:0, maison:0, enfants:0}, kill_switch: false };
let POSITIONS = {}; let PRIX_LAST = { BTCUSDT: 65000, ETHUSDT: 3500, SOLUSDT: 150 };
try{ if(fs.existsSync('./memoire.json')) MEMOIRE = JSON.parse(fs.readFileSync('./memoire.json')); }catch(e){}
function saveMemoire(){ try{ fs.writeFileSync('./memoire.json', JSON.stringify(MEMOIRE)); }catch(e){} }
function activerKillSwitch(raison){ MEMOIRE.kill_switch = true; if(bot){ bot.sendMessage(TELEGRAM_CHAT_ID, `🚨 KITTRA ALERTE: ${raison}`); } }

// 3. FONCTIONS BYBIT
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
    console.log(`✅ ${montant.toFixed(2)} USDT ENVOYÉ AU COFFRE: ${nomCoffre}`);
    if(bot) bot.sendMessage(TELEGRAM_CHAT_ID, `💰 KITTRA: ${montant.toFixed(2)} USDT vers Coffre ${nomCoffre.toUpperCase()}`);
  }catch(e){ console.error("❌ ERREUR RETRAIT:", e); }
}

// 4. LOGIQUE TRADING + COFFRE FORT SURPLUS
function phase_SURVEILLANCE(){
  for(let coin of CONFIG.liste_coins){
    let prix = PRIX_LAST[coin]; let rsi = Math.random()*100;
    if(!POSITIONS[coin]){ if(rsi < 30) return {action:"ACHAT", coin}; }
    else{ let profit = ((prix - POSITIONS[coin].prixEntree)/POSITIONS[coin].prixEntree)*100;
      if(profit >= 5 || profit <= -7) return {action:"VENTE", coin, profit};
    }
  }
  return {action:"SURVEILLANCE"};
}

async function phase_ACTION(signal){
  if(signal.action=="ACHAT"){
    // On prend dans le capital pour acheter
    if(CONFIG.principal >= CONFIG.usdt_par_achat){
      let res = await acheter(signal.coin, CONFIG.usdt_par_achat);
      if(res.ok){
        CONFIG.principal -= CONFIG.usdt_par_achat; // Retire du capital
        POSITIONS[signal.coin] = {prixEntree: res.prix, qty: res.qty};
        MEMOIRE.trades.push({type:"ACHAT", coin:signal.coin, montant:CONFIG.usdt_par_achat});
      }
    }
  }
  if(signal.action.includes("VENTE")){
    let res = await vendre(signal.coin);
    if(res.ok){
      let valeurVente = POSITIONS[signal.coin].qty * res.prix;
      let valeurAchat = POSITIONS[signal.coin].qty * POSITIONS[signal.coin].prixEntree;
      let profitUSDT = valeurVente - valeurAchat;

      if(profitUSDT > 0){
        // SURPLUS: Va direct dans le coffre_total. Capital reste intact
        CONFIG.coffre_total += profitUSDT;
        CONFIG.principal += valeurAchat; // On remet le capital de base
        console.log(`💰 SURPLUS DE ${profitUSDT.toFixed(2)}$ MIS AU COFFRE`);
      }else{
        // PERTE: On prend sur le capital
        CONFIG.principal += valeurVente;
        if(CONFIG.principal < 5) activerKillSwitch("Capital < 5$");
      }

      delete POSITIONS[signal.coin];
      MEMOIRE.trades.push({type:"VENTE", coin:signal.coin, profit:profitUSDT});
      if(profitUSDT>0) MEMOIRE.gains++; else MEMOIRE.pertes++;
    }
  }
  saveMemoire();
}

// 5. RÉPARTITION DIMANCHE
async function repartirEtSweeper(){
  if(CONFIG.coffre_total < 2) return;
  let rep = CONFIG.repartition;
  let totalProfit = CONFIG.coffre_total;

  let resteTrading = totalProfit * (rep.trading/100);
  let resteUrgences = totalProfit * (rep.urgences/100);
  CONFIG.principal += resteTrading; // 40% retourne au capital
  CONFIG.urgences_usdt += resteUrgences; // 24% pour urgences sur Bybit

  let aSweeper = totalProfit * ((100 - rep.trading - rep.urgences)/100);
  let montants = {
    business: aSweeper * (rep.business/(100-rep.trading-rep.urgences)),
    maison: aSweeper * (rep.maison/(100-rep.trading-rep.urgences)),
    enfants: aSweeper * (rep.enfants/(100-rep.trading-rep.urgences)),
  };
  for(let coffre in montants){ await envoyerVersCoffreFort(coffre, montants[coffre]); MEMOIRE.coffres[coffre] += montants[coffre]; }

  CONFIG.coffre_total = 0; // Vide le coffre
  saveMemoire();

  if(bot) bot.sendMessage(TELEGRAM_CHAT_ID, `📊 RÉPARTITION DIMANCHE: Capital=${CONFIG.principal.toFixed(2)}$ | Urgences=${CONFIG.urgences_usdt.toFixed(2)}$`);
}

// 6. BOUCLES
try{ const { WebsocketClient } = require('bybit-api'); const ws = new WebsocketClient({ market: 'v5', key: BYBIT_API_KEY, secret: BYBIT_API_SECRET, testnet: false }); ws.subscribeV5(['tickers.BTCUSDT', 'tickers.ETHUSDT', 'tickers.SOLUSDT'], 'spot'); ws.on('update', (d)=>{ PRIX_LAST[d.data.symbol] = parseFloat(d.data.lastPrice); }); }catch(e){}
setInterval(async ()=>{ if(!MEMOIRE.kill_switch){ let sig = phase_SURVEILLANCE(); if(sig.action!="SURVEILLANCE") await phase_ACTION(sig); } }, 15000);
setInterval(async ()=>{ let date = new Date(); if(date.getDay() == CONFIG.jour_sweep && date.getHours() == 18){ await repartirEtSweeper(); } }, 1000*60*60);

app.get('/api/transactions', (req,res)=> res.json({ principal: CONFIG.principal, urgences_usdt: CONFIG.urgences_usdt, coffre_total: CONFIG.coffre_total, coffres: MEMOIRE.coffres }));
app.listen(process.env.PORT||10000, ()=> console.log(`KITTRA V11 COFFRE-FORT ACTIF`));
