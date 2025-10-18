import os
import requests
import time
import hmac
import hashlib
from telegram import Bot
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime

# Config
PIONEX_API_KEY = os.environ.get('PIONEX_API_KEY')
PIONEX_API_SECRET = os.environ.get('PIONEX_API_SECRET')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

PIONEX_BASE_URL = "https://api.pionex.com"
SCAN_INTERVAL = 300
MIN_VOLUME_USDT = 500000
MIN_SCORE = 4

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum()/period
    down = -seed[seed < 0].sum()/period
    rs = up/down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100./(1. + rs)
    for i in range(period, len(prices)):
        delta = deltas[i-1]
        upval = delta if delta > 0 else 0
        downval = -delta if delta < 0 else 0
        up = (up*(period-1) + upval)/period
        down = (down*(period-1) + downval)/period
        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1. + rs)
    return rsi[-1]

def calculate_macd(prices):
    prices_series = pd.Series(prices)
    exp1 = prices_series.ewm(span=12, adjust=False).mean()
    exp2 = prices_series.ewm(span=26, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return histogram.iloc[-1]

def calculate_ema(prices, period):
    return pd.Series(prices).ewm(span=period, adjust=False).mean().iloc[-1]

def create_signature(query_string):
    return hmac.new(PIONEX_API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_all_tickers():
    timestamp = str(int(time.time() * 1000))
    path = "/api/v1/market/tickers"
    query_string = f"timestamp={timestamp}"
    signature = create_signature(f"GET{path}?{query_string}")
    headers = {"PIONEX-KEY": PIONEX_API_KEY, "PIONEX-SIGNATURE": signature}
    try:
        response = requests.get(f"{PIONEX_BASE_URL}{path}?{query_string}", headers=headers)
        return response.json().get('data', {}).get('tickers', [])
    except Exception as e:
        print(f"Error: {e}")
        return []

def get_klines(symbol):
    timestamp = str(int(time.time() * 1000))
    path = "/api/v1/market/klines"
    query_string = f"symbol={symbol}&interval=1h&limit=100&timestamp={timestamp}"
    signature = create_signature(f"GET{path}?{query_string}")
    headers = {"PIONEX-KEY": PIONEX_API_KEY, "PIONEX-SIGNATURE": signature}
    try:
        response = requests.get(f"{PIONEX_BASE_URL}{path}?{query_string}", headers=headers)
        klines = response.json().get('data', {}).get('klines', [])
        return [float(k['close']) for k in klines]
    except:
        return None

def analyze_coin(symbol, price):
    closes = get_klines(symbol)
    if not closes or len(closes) < 50:
        return None
    
    rsi = calculate_rsi(np.array(closes))
    macd = calculate_macd(closes)
    ema20 = calculate_ema(closes, 20)
    
    # LONG signals
    long_score = 0
    signals = []
    if 25 < rsi < 40:
        long_score += 2
        signals.append(f"RSI oversold: {rsi:.1f}")
    if macd > 0:
        long_score += 2
        signals.append("MACD bullish")
    if price > ema20:
        long_score += 2
        signals.append(f"Above EMA20")
    
    # SHORT signals
    short_score = 0
    short_signals = []
    if rsi > 65:
        short_score += 2
        short_signals.append(f"RSI overbought: {rsi:.1f}")
    if macd < 0:
        short_score += 2
        short_signals.append("MACD bearish")
    if price < ema20:
        short_score += 2
        short_signals.append(f"Below EMA20")
    
    result = {'symbol': symbol, 'price': price, 'rsi': rsi, 'ema20': ema20}
    if long_score >= MIN_SCORE:
        result['type'] = 'LONG'
        result['score'] = long_score
        result['signals'] = signals
        return result
    if short_score >= MIN_SCORE:
        result['type'] = 'SHORT'
        result['score'] = short_score
        result['signals'] = short_signals
        return result
    return None

async def send_telegram(message):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
    except Exception as e:
        print(f"Telegram error: {e}")

async def scan_market():
    print("🚀 Pionex Market Scanner Started!")
    scan_count = 0
    
    while True:
        scan_count += 1
        print(f"\n🔍 SCAN #{scan_count} - {datetime.now().strftime('%H:%M:%S')}")
        
        tickers = get_all_tickers()
        if not tickers:
            print("❌ Failed to get tickers")
            await asyncio.sleep(SCAN_INTERVAL)
            continue
        
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('_USDT') and float(t.get('volume', 0)) > MIN_VOLUME_USDT]
        print(f"📊 Analyzing {len(usdt_pairs)} pairs...")
        
        setups = []
        for ticker in usdt_pairs[:20]:  # Limit 20 pairs
            symbol = ticker['symbol']
            price = float(ticker['close'])
            analysis = analyze_coin(symbol, price)
            if analysis:
                setups.append(analysis)
                print(f"  ✅ {analysis['type']}: {symbol} (Score: {analysis['score']})")
            await asyncio.sleep(0.5)
        
        # Send top 3 setups
        if setups:
            setups.sort(key=lambda x: x['score'], reverse=True)
            for setup in setups[:3]:
                emoji = "🟢" if setup['type'] == "LONG" else "🔴"
                msg = f"""
{emoji} <b>{setup['type']} SETUP</b>

<b>Coin:</b> {setup['symbol']}
<b>Price:</b> ${setup['price']:.8f}
<b>Score:</b> {setup['score']}/10

<b>📊 Indicators:</b>
• RSI: {setup['rsi']:.1f}
• EMA20: ${setup['ema20']:.8f}

<b>✅ Signals:</b>
{chr(10).join(f"  • {s}" for s in setup['signals'])}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
                await send_telegram(msg.strip())
                await asyncio.sleep(2)
            print(f"✅ Sent {len(setups[:3])} alerts")
        else:
            print("❌ No quality setups found")
        
        print(f"⏳ Next scan in {SCAN_INTERVAL}s")
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(scan_market())
