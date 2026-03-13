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
RUN_DURATION = 3000  

# --- STATE ---
# We use strings for candle times to ensure exact matching
last_processed_candle = "" 
last_velocity_alert = 0
VEL_COOLDOWN = 300 

def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

def get_signal():
    global last_processed_candle, last_velocity_alert
    
    try:
        # Optimization: Fetching only what is strictly necessary
        df_1m = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
        df_5m = yf.download(SYMBOL, period="1d", interval="5m", progress=False)
        if df_1m.empty or df_5m.empty: return
    except: return

    df_1m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1m.columns]
    df_5m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_5m.columns]

    m1_close = df_1m['close'].iloc[-1]
    m1_prev = df_1m['close'].iloc[-2]
    velocity = m1_close - m1_prev
    
    # 1. CLEAN VELOCITY ALERT
    if abs(velocity) >= 5.0: # Increased threshold to 5.0 to reduce noise
        now = time.time()
        if (now - last_velocity_alert) > VEL_COOLDOWN:
            alert = "📉 CRASH" if velocity < 0 else "🚀 PUMP"
            send_msg(f"⚠️ *{alert}*\nPrice: ${m1_close:.2f}\nMove: ${abs(velocity):.2f}")
            last_velocity_alert = now

    # 2. 5M STRATEGY
    df_5m['ema9'] = df_5m['close'].ewm(span=9, adjust=False).mean()
    df_5m['ema15'] = df_5m['close'].ewm(span=15, adjust=False).mean()
    df_5m['ema200'] = df_5m['close'].ewm(span=200, adjust=False).mean()

    # Angle Calc
    y = df_5m['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df_5m['close'].mean() * 0.0001)))

    curr = df_5m.iloc[-1]
    # String format for the timestamp to prevent repeat errors
    current_candle_id = str(df_5m.index[-1])
    is_green = curr['close'] > curr['open']
    is_red = curr['close'] < curr['open']

    # 3. NO-SPAM SIGNAL LOGIC
    # Only process if we haven't sent a signal for this 5-minute candle yet
    if current_candle_id != last_processed_candle:
        # Stabilize check: don't signal during crazy velocity
        if abs(velocity) < 2.5:
            # BUY
            if curr['close'] > curr['ema200'] and angle > 25 and is_green:
                if curr['low'] <= (curr['ema9'] + 0.12):
                    send_msg(f"✅ *BUY*\nPrice: ${curr['close']:.2f}\nAngle: {angle:.1f}°")
                    last_processed_candle = current_candle_id

            # SELL
            elif curr['close'] < curr['ema200'] and angle < -25 and is_red:
                if curr['high'] >= (curr['ema9'] - 0.12):
                    send_msg(f"📉 *SELL*\nPrice: ${curr['close']:.2f}\nAngle: {angle:.1f}°")
                    last_processed_candle = current_candle_id

    print(f"[{time.strftime('%H:%M:%S')}] ${curr['close']:.2f} | {angle:.1f}° | Vel: {velocity:.2f}", flush=True)

# --- BOOT ---
print("🚀 Pro-Stabilizer V5 Online.")
while (time.time() - START_TIME) < RUN_DURATION:
    try:
        get_signal()
        time.sleep(45) # Faster check, but within API limits
    except Exception:
        time.sleep(10)
