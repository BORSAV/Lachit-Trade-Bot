import yfinance as yf
import pandas as pd
import requests
import time
import numpy as np

# --- CONFIGURATION ---
SYMBOL = "GC=F"  # Gold
INTERVAL = "1m"
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
    requests.get(url)

def sniper_logic():
    print("🔭 Human Eye Scanning...")
    # Fetch data
    df = yf.download(tickers=SYMBOL, period='1d', interval=INTERVAL)
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # 1. Manual EMA calculation (No pandas-ta needed!)
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()

    # 2. Slope Calculation (The 30° Rule)
    # Using arctan to get the angle in degrees
    lookback = 5
    price_change = df['ema15'].iloc[-1] - df['ema15'].iloc[-lookback]
    # We normalize price change for better angle detection
    angle = np.degrees(np.arctan(price_change / (df['close'].mean() * 0.0001)))
    
    # 3. Candlestick "Human Eye" Detection
    current = df.iloc[-1]
    body = abs(current['open'] - current['close'])
    lower_wick = min(current['open'], current['close']) - current['low']
    upper_wick = current['high'] - max(current['open'], current['close'])
    total_range = current['high'] - current['low']

    # --- BUY SNIPER RULES ---
    # A. Trend: 9 EMA > 15 EMA + Angle > 20° (Adjustable)
    is_uptrend = current['ema9'] > current['ema15'] and angle > 20
    
    # B. The Touch: Low touched the 9 EMA
    did_retest = current['low'] <= current['ema9']
    
    # C. Pin Bar/Hammer Check: Lower wick is at least 2x the body
    is_rejection = lower_wick > (2 * body) and lower_wick > (total_range * 0.5)
    
    # D. Confirmation: Closed Green
    is_green = current['close'] > current['open']

    if is_uptrend and did_retest and is_rejection and is_green:
        msg = (
            "🎯 *MAYANK SNIPER: BUY ALERT*\n"
            f"💰 Price: ${current['close']:.2f}\n"
            f"📐 Angle: {angle:.1f}° (Bullish)\n"
            "🔥 Eye Detail: Pin Bar Rejection at 9 EMA"
        )
        send_telegram_msg(msg)
        print("✅ Signal Sent!")

# --- MAIN LOOP ---
while True:
    try:
        sniper_logic()
        time.sleep(60) 
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
