# KuCoin Futures Market Scanner 🚀

Automatický scanner pro KuCoin Futures, který sleduje trh a posílá trading signály přes Telegram.

## 🎯 Features

- 📊 **Real-time scanning** - Sleduje aktivní futures kontrakty na KuCoin
- 🤖 **Technical Analysis** - RSI, MACD, EMA indikátory
- 📱 **Telegram Alerts** - Automatické notifikace na Telegram
- 🎯 **LONG/SHORT signály** - Identifikuje trading příležitosti
- 💎 **Volume filtering** - Zaměřuje se na likvidní páry
- ⚡ **Fast & Efficient** - Optimalizované API volání

## 📋 Indikátory

Bot analyzuje:
- **RSI (14)** - Identifikuje oversold/overbought zóny
- **MACD** - Detekuje bullish/bearish momentum
- **EMA (20)** - Trend direction

## 🔧 Instalace

### 1. Klonování repozitáře

```bash
git clone https://github.com/yourusername/kucoin-futures-scanner.git
cd kucoin-futures-scanner
```

### 2. Instalace závislostí

```bash
pip install -r requirements.txt
```

### 3. Nastavení environment variables

Vytvořte `.env` soubor nebo nastavte proměnné:

```bash
export KUCOIN_API_KEY="your_api_key"
export KUCOIN_API_SECRET="your_api_secret"
export KUCOIN_API_PASSPHRASE="your_passphrase"
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

## 🔑 Získání API klíčů

### KuCoin Futures API

1. Přihlaste se na [KuCoin](https://www.kucoin.com)
2. Jděte do **API Management**
3. Vytvořte nový API klíč s oprávněním **General** (pouze čtení)
4. **DŮLEŽITÉ**: Nastavte IP whitelist pro bezpečnost
5. Uložte si:
   - API Key
   - API Secret
   - Passphrase

### Telegram Bot

1. Otevřete Telegram a najděte [@BotFather](https://t.me/botfather)
2. Napište `/newbot` a postupujte podle instrukcí
3. Uložte si **Bot Token**
4. Zjistěte své Chat ID:
   - Napište zprávu vašemu botovi
   - Otevřete: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Najděte `"chat":{"id":123456789}` - to je vaše Chat ID

## 🚀 Spuštění

### Lokálně

```bash
python market_scanner.py
```

### Na Heroku

```bash
heroku create your-app-name
heroku config:set KUCOIN_API_KEY="your_key"
heroku config:set KUCOIN_API_SECRET="your_secret"
heroku config:set KUCOIN_API_PASSPHRASE="your_passphrase"
heroku config:set TELEGRAM_BOT_TOKEN="your_token"
heroku config:set TELEGRAM_CHAT_ID="your_chat_id"
git push heroku main
```

### Na VPS (systemd service)

Vytvořte `/etc/systemd/system/kucoin-scanner.service`:

```ini
[Unit]
Description=KuCoin Futures Scanner
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/kucoin-futures-scanner
Environment="KUCOIN_API_KEY=your_key"
Environment="KUCOIN_API_SECRET=your_secret"
Environment="KUCOIN_API_PASSPHRASE=your_passphrase"
Environment="TELEGRAM_BOT_TOKEN=your_token"
Environment="TELEGRAM_CHAT_ID=your_chat_id"
ExecStart=/usr/bin/python3 /path/to/market_scanner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Aktivujte service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kucoin-scanner
sudo systemctl start kucoin-scanner
sudo systemctl status kucoin-scanner
```

## ⚙️ Konfigurace

V `market_scanner.py` můžete upravit:

```python
SCAN_INTERVAL = 300        # Interval scanování (sekundy)
MIN_VOLUME_USDT = 1000000  # Minimální 24h volume ($)
MIN_SCORE = 4              # Minimální score pro signál (0-10)
```

## 📊 Výstup

Bot posílá na Telegram zprávy ve formátu:

```
🟢 LONG SETUP

Contract: BTCUSDT
Price: $45,234.50
24h Volume: $1.2B
Score: 6/10

📊 Indicators:
• RSI: 35.2
• EMA20: $44,890.00

✅ Signals:
  • RSI oversold: 35.2
  • MACD bullish
  • Above EMA20

⏰ 14:30:15
🔗 KuCoin Futures
```

## 🔒 Bezpečnost

- ✅ Nikdy nesdílejte vaše API klíče
- ✅ Použijte API klíč pouze s read-only oprávněním
- ✅ Nastavte IP whitelist na KuCoin
- ✅ Ukládejte credentials v environment variables, ne v kódu
- ✅ Pravidelně rotujte API klíče

## 📝 Poznámky

- Bot **POUZE** sleduje trh a posílá signály
- **NEOBCHODUJE** automaticky
- Je to nástroj pro analýzu, ne trading robot
- Vždy proveďte vlastní analýzu před tradingem

## 🐛 Troubleshooting

### "Failed to get contracts"
- Zkontrolujte API credentials
- Ověřte, že API klíč má správná oprávnění
- Zkontrolujte IP whitelist na KuCoin

### "Telegram error"
- Ověřte Bot Token
- Zkontrolujte Chat ID
- Ujistěte se, že jste napsali botovi alespoň jednu zprávu

### Rate limiting
- KuCoin má rate limity na API
- Bot má vestavěné delays mezi požadavky
- Při problémech zvyšte `SCAN_INTERVAL`

## 📄 License

MIT License - můžete svobodně používat a upravovat

## 🤝 Příspěvky

Pull requesty jsou vítány! Pro větší změny prosím nejdřív otevřete issue.

## ⚠️ Disclaimer

Tento bot je pouze pro vzdělávací a informační účely. Autor nenese žádnou odpovědnost za finanční ztráty vzniklé používáním tohoto software. Trading s kryptoměnami je vysoce rizikový. Investujte pouze to, co si můžete dovolit ztratit.

---

Made with ❤️ for crypto traders
