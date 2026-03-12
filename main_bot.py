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

def human_eye_logic():
    # 1. FETCH DATA
    df = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
    if df.empty or len(df) < 20: return
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # 2. INDICATORS (Human standard 9/15)
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()

    # 3. THE NEEDED DEGREE (Vector Slope)
    y = df['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1) 
    angle = np.degrees(np.arctan(slope / (df['close'].mean() * 0.0001)))

    # 4. THE NEEDED CANDLE (Anatomy)
    curr = df.iloc[-1]
    body = abs(curr['close'] - curr['open'])
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    avg_body = abs(df['close'] - df['open']).tail(10).mean()

    # --- HUMAN KNOWLEDGE RULES ---
    is_strong_trend = angle > 15  # The "Needed Degree"
    is_at_ema = curr['low'] <= curr['ema9']  # The "Needed Location"
    is_power_candle = curr['close'] > curr['open'] and body > (avg_body * 0.7) # "Needed Strength"

    if is_strong_trend and is_at_ema and is_power_candle:
        msg = f"🎯 *HUMAN EYE SIGNAL*\n💰 Price: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°\n🔥 Setup: Power Candle at 9 EMA"
        send_telegram_msg(msg)
        print(f"[{time.strftime('%H:%M:%S')}] ✅ SIGNAL SENT")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] 🔭 Watching... Angle: {angle:.1f}°")

while True:
    try:
        human_eye_logic()
        time.sleep(60)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
