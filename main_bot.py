import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
import requests

# --- CONFIG ---
SYMBOL = "GC=F"
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
START_TIME = time.time()
RUN_DURATION = 3000  # 50 minutes

def send_msg(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}&parse_mode=Markdown"
        requests.get(url, timeout=5)
    except: pass

def get_signal():
    # Fetching 1m data
    df = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
    
    if df.empty or len(df) < 50: 
        return

    # FIX FOR 'CLOSE' ERROR: Force column names to be simple lowercase
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]

    # Double check if 'close' exists now
    if 'close' not in df.columns:
        print("Waiting for data columns...", flush=True)
        return

    # EMAs
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # Slope Calculation (Human Eye 30-Degree Rule)
    y = df['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df['close'].mean() * 0.0001)))

    # Candle Anatomy
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    body = abs(curr['close'] - curr['open'])
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    avg_body = abs(df['close'] - df['open']).tail(10).mean()

    # Strategy Filters
    is_uptrend = curr['close'] > curr['ema200'] and curr['ema9'] > curr['ema15']
    is_strong = angle > 25
    is_at_ema = curr['low'] <= (curr['ema9'] + 0.1)

    # Patterns
    is_pinbar = lower_wick > (1.8 * body)
    is_engulfing = (curr['close'] > prev['open']) and (prev['close'] < prev['open'])
    
    if is_uptrend and is_strong and is_at_ema:
        if is_pinbar or is_engulfing:
            p_type = "Pin Bar" if is_pinbar else "Engulfing"
            send_msg(f"🎯 *SNIPER {p_type}*\n💰 Gold: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°")
            print(f"✅ Signal Sent: {p_type}", flush=True)
    else:
        print(f"[{time.strftime('%H:%M:%S')}] Monitoring... Angle: {angle:.1f}°", flush=True)

# --- LOOP FOR GREEN STATUS ---
print("🚀 Bot Started. Human Eyes watching Gold...", flush=True)
while (time.time() - START_TIME) < RUN_DURATION:
    try:
        get_signal()
        time.sleep(60)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(10)

print("🏁 Finished run. Exiting for Green Checkmark.", flush=True)
