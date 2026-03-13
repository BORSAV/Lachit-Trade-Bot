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

# --- STATE MEMORY (The Spam Fix) ---
last_candle_id = "" # Stores the ID of the last candle we sent a signal for
last_vel_alert_time = 0
VEL_COOLDOWN = 300 

def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

def get_signal():
    global last_candle_id, last_vel_alert_time
    
    try:
        # Optimization: period="1d" is faster to download than "5d"
        df_1m = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
        df_5m = yf.download(SYMBOL, period="1d", interval="5m", progress=False)
        if df_1m.empty or df_5m.empty: return
    except: return

    df_1m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1m.columns]
    df_5m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_5m.columns]

    m1_close = df_1m['close'].iloc[-1]
    m1_prev = df_1m['close'].iloc[-2]
    velocity = m1_close - m1_prev
    
    # 1. VELOCITY ALERT (With 5m Cooldown)
    if abs(velocity) >= 5.0: # Increased threshold to reduce noise
        now = time.time()
        if (now - last_vel_alert_time) > VEL_COOLDOWN:
            alert = "📉 CRASH" if velocity < 0 else "🚀 PUMP"
            send_msg(f"⚠️ *{alert}*\nPrice: ${m1_close:.2f}\nMove: ${abs(velocity):.2f}/min")
            last_vel_alert_time = now

    # 2. 5M TECHNICALS
    df_5m['ema9'] = df_5m['close'].ewm(span=9, adjust=False).mean()
    df_5m['ema15'] = df_5m['close'].ewm(span=15, adjust=False).mean()
    df_5m['ema200'] = df_5m['close'].ewm(span=200, adjust=False).mean()

    # Angle Calc
    y = df_5m['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df_5m['close'].mean() * 0.0001)))

    curr = df_5m.iloc[-1]
    is_green = curr['close'] > curr['open']
    is_red = curr['close'] < curr['open']
    
    # Create a unique ID for this candle (Timestamp)
    current_candle_id = str(df_5m.index[-1])

    # 3. SPAM-FREE SIGNAL LOGIC
    # Rule: Only send a new signal if we HAVEN'T already sent one for this specific 5m candle
    if current_candle_id != last_candle_id:
        if abs(velocity) < 2.5: # Market must be "stable" for these
            # BUY
            if curr['close'] > curr['ema200'] and angle > 25 and is_green:
                if curr['low'] <= (curr['ema9'] + 0.12):
                    send_msg(f"✅ *BUY*\nPrice: ${curr['close']:.2f}\nAngle: {angle:.1f}°")
                    last_candle_id = current_candle_id

            # SELL
            elif curr['close'] < curr['ema200'] and angle < -25 and is_red:
                if curr['high'] >= (curr['ema9'] - 0.12):
                    send_msg(f"📉 *SELL*\nPrice: ${curr['close']:.2f}\nAngle: {angle:.1f}°")
                    last_candle_id = current_candle_id

    print(f"[{time.strftime('%H:%M:%S')}] ${curr['close']:.2f} | Ang: {angle:.1f}° | Vel: {velocity:.2f}", flush=True)

# --- BOOT ---
print("🚀 Sniper V6 Online. Speed & Spam optimized.")
while (time.time() - START_TIME) < RUN_DURATION:
    try:
        get_signal()
        time.sleep(45) # Faster check (45s) but still safe from API limits
    except:
        time.sleep(10)
