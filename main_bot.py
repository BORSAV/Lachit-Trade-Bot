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
last_signal_time = None 
last_velocity_time = 0
VELOCITY_COOLDOWN = 300 

def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

def get_signal():
    global last_signal_time, last_velocity_time
    
    try:
        df_1m = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
        df_5m = yf.download(SYMBOL, period="5d", interval="5m", progress=False)
        if df_1m.empty or df_5m.empty: return
    except: return

    df_1m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1m.columns]
    df_5m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_5m.columns]

    m1_close = df_1m['close'].iloc[-1]
    m1_prev = df_1m['close'].iloc[-2]
    velocity = m1_close - m1_prev
    
    # 1. EMERGENCY ALERT (Cleaned)
    if abs(velocity) >= 4.0:
        current_time = time.time()
        if (current_time - last_velocity_time) > VELOCITY_COOLDOWN:
            alert = "📉 CRASH" if velocity < 0 else "🚀 PUMP"
            send_msg(f"⚠️ *{alert} DETECTED*\nPrice: ${m1_close:.2f}\nMove: ${abs(velocity):.2f}/min")
            last_velocity_time = current_time

    # 2. 5M CALCULATION
    df_5m['ema9'] = df_5m['close'].ewm(span=9, adjust=False).mean()
    df_5m['ema15'] = df_5m['close'].ewm(span=15, adjust=False).mean()
    df_5m['ema200'] = df_5m['close'].ewm(span=200, adjust=False).mean()

    # Angle Calc
    y = df_5m['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df_5m['close'].mean() * 0.0001)))

    curr = df_5m.iloc[-1]
    candle_time = df_5m.index[-1]
    is_green = curr['close'] > curr['open']
    is_red = curr['close'] < curr['open']

    # 3. SIGNAL LOGIC (Simplified Output)
    if candle_time != last_signal_time and abs(velocity) < 2.0:
        # BUY
        if curr['close'] > curr['ema200'] and angle > 25 and is_green:
            if curr['low'] <= (curr['ema9'] + 0.15):
                send_msg(f"✅ *BUY SIGNAL*\nPrice: ${curr['close']:.2f}\nAngle: {angle:.1f}°")
                last_signal_time = candle_time

        # SELL
        elif curr['close'] < curr['ema200'] and angle < -25 and is_red:
            if curr['high'] >= (curr['ema9'] - 0.15):
                send_msg(f"📉 *SELL SIGNAL*\nPrice: ${curr['close']:.2f}\nAngle: {angle:.1f}°")
                last_signal_time = candle_time

    print(f"[{time.strftime('%H:%M:%S')}] {curr['close']:.2f} | Angle: {angle:.1f}°", flush=True)

# --- BOOT ---
print("🚀 Sniper V4 Pro Online.", flush=True)
send_msg("🛰️ *Sniper V4 Live:* Monitoring Gold 5M.")

while (time.time() - START_TIME) < RUN_DURATION:
    try:
        get_signal()
        time.sleep(60) 
    except Exception as e:
        time.sleep(10)
