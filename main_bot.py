import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import os

# --- CONFIGURATION ---
SYMBOL = "GC=F"  # Gold Futures
INTERVAL = "1m"
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
        requests.get(url, timeout=5)
    except:
        pass

def sniper_logic():
    # 1. Fetch Data
    df = yf.download(tickers=SYMBOL, period='1d', interval=INTERVAL, progress=False)
    if df.empty or len(df) < 20: return
    
    # Handle MultiIndex columns if yfinance returns them
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # 2. Indicators (Manual EMA)
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()

    # 3. Human Eye Calculation
    curr = df.iloc[-1]
    body = abs(curr['open'] - curr['close'])
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    total_range = curr['high'] - curr['low']

    # 4. Angle/Slope (30 Degree Rule)
    # Compares EMA15 now vs 5 mins ago
    price_change = df['ema15'].iloc[-1] - df['ema15'].iloc[-6]
    angle = np.degrees(np.arctan(price_change / (df['close'].mean() * 0.0001)))

    # --- SNIPER CONDITIONS ---
    # Trend: 9 > 15 and Angle is healthy (not sideways)
    is_uptrend = curr['ema9'] > curr['ema15'] and angle > 15
    # Retest: Low touched the 9 EMA
    did_retest = curr['low'] <= curr['ema9']
    # Rejection: Long lower wick (Hammer)
    has_wick = lower_wick > (1.5 * body) and lower_wick > (total_range * 0.4)
    # Confirm: Green Close
    is_green = curr['close'] > curr['open']

    if is_uptrend and did_retest and has_wick and is_green:
        msg = (
            "🎯 *SNIPER BUY SIGNAL*\n"
            f"💰 Price: ${curr['close']:.2f}\n"
            f"📐 Angle: {angle:.1f}°\n"
            "🔥 Setup: EMA 9 Retest + Rejection"
        )
        send_telegram_msg(msg)
        print(f"[{time.strftime('%H:%M:%S')}] ✅ Signal Sent")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] 🔭 Scanning... (No Setup)")

# --- MAIN LOOP ---
while True:
    try:
        sniper_logic()
        time.sleep(60)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
