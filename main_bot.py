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
RUN_DURATION = 3600  

# --- STATE MEMORY ---
last_candle_id = "" 
last_vel_alert_time = 0
VEL_COOLDOWN = 600 # 10-minute cooldown to stop spam

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
        # Fetching minimal data to reduce lag
        df_1m = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
        df_5m = yf.download(SYMBOL, period="1d", interval="5m", progress=False)
        if df_1m.empty or df_5m.empty: return
    except: return

    df_1m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1m.columns]
    df_5m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_5m.columns]

    # Current 1m state
    m1_now = df_1m.iloc[-1]
    m1_prev = df_1m.iloc[-2]
    velocity = m1_now['close'] - m1_prev['close']
    is_m1_green = m1_now['close'] > m1_now['open']

    # 1. EMERGENCY VELOCITY (With Anti-Spam & Green Candle Filter)
    if abs(velocity) >= 5.0:
        now = time.time()
        # FIX: Don't call it a crash if the current candle is green/recovering
        if velocity < 0 and is_m1_green:
            pass # Ignore "old" crash data if market is turning green
        elif (now - last_vel_alert_time) > VEL_COOLDOWN:
            alert = "📉 CRASH" if velocity < 0 else "🚀 PUMP"
            send_msg(f"⚠️ *{alert}*\nPrice: ${m1_now['close']:.2f}\nMove: ${abs(velocity):.2f}")
            last_vel_alert_time = now

    # 2. 5M STRATEGY
    df_5m['ema9'] = df_5m['close'].ewm(span=9, adjust=False).mean()
    df_5m['ema15'] = df_5m['close'].ewm(span=15, adjust=False).mean()
    df_5m['ema200'] = df_5m['close'].ewm(span=200, adjust=False).mean()

    # Angle
    y = df_5m['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df_5m['close'].mean() * 0.0001)))

    curr_5m = df_5m.iloc[-1]
    current_candle_id = str(df_5m.index[-1])

    # 3. SIGNAL LOCK (One per 5m candle)
    if current_candle_id != last_candle_id:
        # Only signal if market isn't in "Chaos Mode"
        if abs(velocity) < 2.0:
            if curr_5m['close'] < curr_5m['ema200'] and angle < -25:
                if curr_5m['close'] < curr_5m['open'] and curr_5m['high'] >= (curr_5m['ema9'] - 0.1):
                    send_msg(f"📉 *SELL*\nPrice: ${curr_5m['close']:.2f}\nAngle: {angle:.1f}°")
                    last_candle_id = current_candle_id
            
            elif curr_5m['close'] > curr_5m['ema200'] and angle > 25:
                if curr_5m['close'] > curr_5m['open'] and curr_5m['low'] <= (curr_5m['ema9'] + 0.1):
                    send_msg(f"✅ *BUY*\nPrice: ${curr_5m['close']:.2f}\nAngle: {angle:.1f}°")
                    last_candle_id = current_candle_id

    print(f"[{time.strftime('%H:%M:%S')}] ${m1_now['close']:.2f} | Vel: {velocity:.2f} | Green: {is_m1_green}")

# --- START ---
print("🚀 V7 Anti-Lag Sniper Online.")
while True:
    try:
        get_signal()
        time.sleep(50) 
    except:
        time.sleep(10)
