import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import os

# --- CONFIGURATION ---
SYMBOL = "GC=F" 
INTERVAL = "1m"
# Uses GitHub Secrets for security
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
        requests.get(url)
    except:
        pass

def sniper_logic():
    # 1. Fetch Pure Market Data
    df = yf.download(tickers=SYMBOL, period='1d', interval=INTERVAL, progress=False)
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # 2. Manual EMA (No external libraries to cause errors)
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()

    # 3. Candle Analysis (Human Eye Rejection)
    curr = df.iloc[-1]
    body = abs(curr['open'] - curr['close'])
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    total_range = curr['high'] - curr['low']

    # 4. Slope/Angle (The 30° Logic)
    lookback = 5
    price_change = df['ema15'].iloc[-1] - df['ema15'].iloc[-lookback]
    # Calculate angle: If it's not sloping up, it's not a buy
    angle = np.degrees(np.arctan(price_change / (df['close'].mean() * 0.0001)))

    # --- THE SNIPER RULES ---
    # A. Trend: 9 is above 15 AND the slope is healthy (> 15 degrees)
    is_uptrend = curr['ema9'] > curr['ema15'] and angle > 15
    
    # B. The Retest: The "Human Eye" sees the candle touch the 9 EMA
    did_retest = curr['low'] <= curr['ema9']
    
    # C. The Rejection: Must have a long lower wick (Pin Bar)
    has_wick = lower_wick > (1.5 * body) and lower_wick > (total_range * 0.4)
    
    # D. Final Check: Candle must close GREEN
    is_green = curr['close'] > curr['open']

    if is_uptrend and did_retest and has_wick and is_green:
        msg = (
            "🎯 *SNIPER BUY SIGNAL*\n"
            f"💰 Price: ${curr['close']:.2f}\n"
            f"📐 Slope: {angle:.1f}°\n"
            "🔥 Setup: 9 EMA Retest + Rejection Wick"
        )
        send_telegram_msg(msg)

# --- THE LOOP ---
while True:
    try:
        sniper_logic()
        time.sleep(60) # Scan every 1 minute
    except Exception as e:
        print(f"Loop Error: {e}")
        time.sleep(10)
