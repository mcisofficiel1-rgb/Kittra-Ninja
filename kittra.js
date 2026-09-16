{
  "version": "17.4_ULTIME_NINJA_REEL",
  "mode": "REAL_LIVE_NO_DEMO",
  "exchange": "bybit",
  "api_endpoint": "https://api.bybit.com",
  "account_type": "UNIFIED",
  "trading_type": "SPOT_REAL",
  "demo": false,
  "testnet": false,
  "strategy": {
    "scan_interval_seconds": 2,
    "pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "entry_type": "3_DCA_NINJA",
    "entries": ["30%", "30%", "40%"],
    "take_profit_percent": 1.5,
    "stop_loss_percent": 5.0,
    "max_capital_per_trade_percent": 15,
    "leverage": 1
  },
  "security": {
    "lock_system": true,
    "auto_ping_render": true,
    "api_invalid_detection": true
  },
  "placeholders_for_render_test": {
    "BYBIT_API_KEY": "omHyIybio10",
    "BYBIT_API_SECRET": "1Ozaa14dx",
    "TG_TOKEN": "8765D4jrl12t",
    "TG_ID": "9999"
  }
    }
