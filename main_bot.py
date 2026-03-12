import yfinance as yf
import pandas as pd
import numpy as np
import os
import time

# --- CONFIG ---
SYMBOL = "GC=F"
INTERVAL = "1m"
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
        import requests
        requests.get(url, timeout=5)
    except:
        pass

def human_knowledge_logic():
    # 1. FETCH DATA (Contextual Lookback)
    df = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
    if df.empty or len(df) < 20: return
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # 2. INDICATORS
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()

    # 3. THE "NEEDED DEGREE" (Linear Regression Slope)
    # We look at the last 5 minutes to judge the 'steepness'
    y = df['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1) 
    # Convert slope to a human-readable angle
    angle = np.degrees(np.arctan(slope / (df['close'].mean() * 0.0001)))

    # 4. THE "NEEDED CANDLE" (Power & Rejection)
    curr = df.iloc[-1]
    body = abs(curr['close'] - curr['open'])
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    # Human Knowledge: Is this candle stronger than the last 10?
    avg_body = abs(df['close'] - df['open']).tail(10).mean()

    # --- THE HUMAN DECISION ENGINE ---
    
    # RULE 1: Needed Degree (Trend must be > 15° or it's just noise)
    is_trending = angle > 15
    
    # RULE 2: Needed Location (Retest of the 9 EMA 'Pocket')
    is_at_ema = curr['low'] <= curr['ema9'] <= max(curr['open'], curr['close'])
    
    # RULE 3: Needed Strength (Power Candle + Wick Rejection)
    is_power = curr['close'] > curr['open'] and body > (avg_body * 0.8)
    has_rejection = lower_wick > (body * 0.5)

    if is_trending and is_at_ema and is_power and has_rejection:
        msg = (
            "🎯 *HUMAN EYE SETUP CONFIRMED*\n"
            f"💰 Price: ${curr['close']:.2f}\n"
            f"📐 Angle: {angle:.1f}° (Strong Trend)\n"
            "🔥 Setup: Power Rejection at 9 EMA"
        )
        send_telegram_msg(msg)
        print(f"[{time.strftime('%H:%M:%S')}] ✅ SIGNAL FIRED")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] 🔭 Watching... Angle: {angle:.1f}°")

while True:
    try:
        human_knowledge_logic()
        time.sleep(60)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
