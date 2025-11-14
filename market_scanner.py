import os
import requests
import time
import hmac
import hashlib
import base64
from telegram import Bot
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
import json

# Config
KUCOIN_API_KEY = os.environ.get('KUCOIN_API_KEY')
KUCOIN_API_SECRET = os.environ.get('KUCOIN_API_SECRET')
KUCOIN_API_PASSPHRASE = os.environ.get('KUCOIN_API_PASSPHRASE')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

KUCOIN_BASE_URL = "https://api-futures.kucoin.com"
SCAN_INTERVAL = 300  # 5 minutes
MIN_VOLUME_USDT = 1000000  # 1M USDT
MIN_SCORE = 4

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
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
    """Calculate MACD indicator"""
    prices_series = pd.Series(prices)
    exp1 = prices_series.ewm(span=12, adjust=False).mean()
    exp2 = prices_series.ewm(span=26, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return histogram.iloc[-1]

def calculate_ema(prices, period):
    """Calculate EMA indicator"""
    return pd.Series(prices).ewm(span=period, adjust=False).mean().iloc[-1]

def create_signature(method, endpoint, timestamp, body=''):
    """Create KuCoin API signature"""
    str_to_sign = str(timestamp) + method + endpoint + body
    signature = base64.b64encode(
        hmac.new(
            KUCOIN_API_SECRET.encode('utf-8'),
            str_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
    ).decode()
    
    passphrase = base64.b64encode(
        hmac.new(
            KUCOIN_API_SECRET.encode('utf-8'),
            KUCOIN_API_PASSPHRASE.encode('utf-8'),
            hashlib.sha256
        ).digest()
    ).decode()
    
    return signature, passphrase

def get_headers(method, endpoint, body=''):
    """Generate KuCoin API headers"""
    timestamp = str(int(time.time() * 1000))
    signature, passphrase = create_signature(method, endpoint, timestamp, body)
    
    return {
        'KC-API-KEY': KUCOIN_API_KEY,
        'KC-API-SIGN': signature,
        'KC-API-TIMESTAMP': timestamp,
        'KC-API-PASSPHRASE': passphrase,
        'KC-API-KEY-VERSION': '2',
        'Content-Type': 'application/json'
    }

def get_active_contracts():
    """Get all active KuCoin Futures contracts"""
    try:
        endpoint = '/api/v1/contracts/active'
        headers = get_headers('GET', endpoint)
        response = requests.get(f"{KUCOIN_BASE_URL}{endpoint}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '200000':
                return data.get('data', [])
        print(f"Error getting contracts: {response.text}")
        return []
    except Exception as e:
        print(f"Exception in get_active_contracts: {e}")
        return []

def get_ticker(symbol):
    """Get ticker data for a specific symbol"""
    try:
        endpoint = f'/api/v1/ticker?symbol={symbol}'
        headers = get_headers('GET', endpoint)
        response = requests.get(f"{KUCOIN_BASE_URL}{endpoint}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '200000':
                return data.get('data')
        return None
    except Exception as e:
        print(f"Error getting ticker for {symbol}: {e}")
        return None

def get_klines(symbol, granularity=60):
    """Get klines/candlestick data
    granularity: 1, 5, 15, 30, 60, 120, 240, 480, 720, 1440, 10080 (minutes)
    """
    try:
        # Get last 100 candles
        to_time = int(time.time())
        from_time = to_time - (granularity * 60 * 100)
        
        endpoint = f'/api/v1/kline/query?symbol={symbol}&granularity={granularity}&from={from_time}&to={to_time}'
        headers = get_headers('GET', endpoint)
        response = requests.get(f"{KUCOIN_BASE_URL}{endpoint}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '200000':
                klines = data.get('data', [])
                # KuCoin returns: [timestamp, open, high, low, close, volume]
                closes = [float(k[4]) for k in klines]
                return closes if len(closes) >= 50 else None
        return None
    except Exception as e:
        print(f"Error getting klines for {symbol}: {e}")
        return None

def analyze_coin(symbol, price, volume_24h):
    """Analyze coin using technical indicators"""
    closes = get_klines(symbol)
    if not closes or len(closes) < 50:
        return None
    
    try:
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
        
        result = {
            'symbol': symbol,
            'price': price,
            'volume_24h': volume_24h,
            'rsi': rsi,
            'ema20': ema20
        }
        
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
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

async def send_telegram(message):
    """Send message to Telegram"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
    except Exception as e:
        print(f"Telegram error: {e}")

async def scan_market():
    """Main market scanning loop"""
    print("🚀 KuCoin Futures Market Scanner Started!")
    print(f"📊 Scanning interval: {SCAN_INTERVAL}s")
    print(f"💰 Min volume: ${MIN_VOLUME_USDT:,.0f}")
    print(f"⭐ Min score: {MIN_SCORE}/10\n")
    
    scan_count = 0
    
    while True:
        scan_count += 1
        print(f"\n{'='*60}")
        print(f"🔍 SCAN #{scan_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # Get all active contracts
        contracts = get_active_contracts()
        if not contracts:
            print("❌ Failed to get contracts")
            await asyncio.sleep(SCAN_INTERVAL)
            continue
        
        print(f"📋 Found {len(contracts)} active contracts")
        
        # Filter USDT perpetual contracts with good volume
        usdt_contracts = []
        for contract in contracts:
            symbol = contract.get('symbol', '')
            if 'USDT' in symbol and contract.get('type') == 'FFWCSX':  # Perpetual
                ticker = get_ticker(symbol)
                if ticker:
                    volume_24h = float(ticker.get('turnover', 0))
                    if volume_24h >= MIN_VOLUME_USDT:
                        usdt_contracts.append({
                            'symbol': symbol,
                            'price': float(ticker.get('price', 0)),
                            'volume_24h': volume_24h
                        })
                await asyncio.sleep(0.2)  # Rate limiting
        
        print(f"💎 Analyzing {len(usdt_contracts)} high-volume pairs...")
        
        setups = []
        for contract in usdt_contracts[:30]:  # Limit to top 30
            symbol = contract['symbol']
            price = contract['price']
            volume_24h = contract['volume_24h']
            
            analysis = analyze_coin(symbol, price, volume_24h)
            if analysis:
                setups.append(analysis)
                print(f"  ✅ {analysis['type']}: {symbol} (Score: {analysis['score']}/10)")
            
            await asyncio.sleep(0.5)  # Rate limiting
        
        # Send top 3 setups to Telegram
        if setups:
            setups.sort(key=lambda x: x['score'], reverse=True)
            print(f"\n📤 Sending {min(3, len(setups))} alerts to Telegram...")
            
            for setup in setups[:3]:
                emoji = "🟢" if setup['type'] == "LONG" else "🔴"
                msg = f"""
{emoji} <b>{setup['type']} SETUP</b>

<b>Contract:</b> {setup['symbol']}
<b>Price:</b> ${setup['price']:.4f}
<b>24h Volume:</b> ${setup['volume_24h']/1000000:.2f}M
<b>Score:</b> {setup['score']}/10

<b>📊 Indicators:</b>
• RSI: {setup['rsi']:.1f}
• EMA20: ${setup['ema20']:.4f}

<b>✅ Signals:</b>
{chr(10).join(f"  • {s}" for s in setup['signals'])}

⏰ {datetime.now().strftime('%H:%M:%S')}
🔗 KuCoin Futures
"""
                await send_telegram(msg.strip())
                await asyncio.sleep(2)
            
            print(f"✅ Sent {len(setups[:3])} alerts")
        else:
            print("❌ No quality setups found")
        
        print(f"\n⏳ Next scan in {SCAN_INTERVAL}s...")
        print(f"{'='*60}")
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    if not all([KUCOIN_API_KEY, KUCOIN_API_SECRET, KUCOIN_API_PASSPHRASE]):
        print("❌ Missing KuCoin API credentials!")
        print("Set: KUCOIN_API_KEY, KUCOIN_API_SECRET, KUCOIN_API_PASSPHRASE")
        exit(1)
    
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        print("❌ Missing Telegram credentials!")
        print("Set: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
        exit(1)
    
    try:
        asyncio.run(scan_market())
    except KeyboardInterrupt:
        print("\n\n👋 Scanner stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
