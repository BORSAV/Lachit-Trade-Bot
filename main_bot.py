import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
import requests

# --- CONFIG (Matches your GitHub Secrets) ---
SYMBOL = "GC=F"
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID') 
START_TIME = time.time()
RUN_DURATION = 3000  

# --- GLOBAL STATE ---
last_signal_time = None 
last_velocity_time = 0
VELOCITY_COOLDOWN = 300  # 5-minute cooldown for emergency alerts

def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

def get_signal():
    global last_signal_time, last_velocity_time
    
    # 1. FETCH DATA (Checking both 1m for speed and 5m for trend)
    try:
        df_1m = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
        df_5m = yf.download(SYMBOL, period="5d", interval="5m", progress=False)
        if df_1m.empty or df_5m.empty: return
    except: return

    # Clean Column Names
    df_1m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1m.columns]
    df_5m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_5m.columns]

    # 2. EMERGENCY VELOCITY TRIGGER (With Cooldown)
    m1_close = df_1m['close'].iloc[-1]
    m1_prev = df_1m['close'].iloc[-2]
    velocity = m1_close - m1_prev
    
    if abs(velocity) >= 4.0:
        current_time = time.time()
        if (current_time - last_velocity_time) > VELOCITY_COOLDOWN:
            direction = "📉 CRASH" if velocity < 0 else "🚀 PUMP"
            send_msg(f"⚠️ *VELOCITY ALERT: {direction}*\n💰 Price: ${m1_close:.2f}\n⚡ Volatility: ${abs(velocity):.2f}/min\n🛑 *Wait for 5m stabilization.*")
            last_velocity_time = current_time

    # 3. 5M STABILIZATION & TREND
    df_5m['ema9'] = df_5m['close'].ewm(span=9, adjust=False).mean()
    df_5m['ema15'] = df_5m['close'].ewm(span=15, adjust=False).mean()
    df_5m['ema200'] = df_5m['close'].ewm(span=200, adjust=False).mean()

    # Angle of 15 EMA
    y = df_5m['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df_5m['close'].mean() * 0.0001)))

    curr = df_5m.iloc[-1]
    candle_time = df_5m.index[-1]
    is_green = curr['close'] > curr['open']
    is_red = curr['close'] < curr['open']

    # 4. SNIPER LOGIC (Only if Velocity is Stable)
    if candle_time != last_signal_time and abs(velocity) < 2.0:
        # BUY: Price > 200 EMA + High Angle + Green + Pocket Retest
        if curr['close'] > curr['ema200'] and angle > 25 and is_green:
            if curr['low'] <= (curr['ema9'] + 0.15):
                send_msg(f"✅ *5M STABLE BUY*\n💰 Price: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°\n💼 Cap: ₹9L -> Target: ₹25L")
                last_signal_time = candle_time

        # SELL: Price < 200 EMA + Negative Angle + Red + Pocket Retest
        elif curr['close'] < curr['ema200'] and angle < -25 and is_red:
            if curr['high'] >= (curr['ema9'] - 0.15):
                send_msg(f"✅ *5M STABLE SELL*\n💰 Price: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°\n💼 Cap: ₹9L -> Target: ₹25L")
                last_signal_time = candle_time

    print(f"[{time.strftime('%H:%M:%S')}] Scan: {curr['close']:.2f} | Angle: {angle:.1f}° | Vel: {velocity:.2f}", flush=True)

# --- STARTUP ---
print("🚀 Sniper V3 Stable Online.", flush=True)
send_msg("🛡️ *Sniper V3 Live:* Market Stabilization Mode Active.")

while (time.time() - START_TIME) < RUN_DURATION:
    try:
        get_signal()
        time.sleep(60) 
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(10)
