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
last_signal_time = None # To avoid double-sending on the same 5m candle

def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

def get_signal():
    global last_signal_time
    # 1. FETCH 5M DATA
    df = yf.download(SYMBOL, period="5d", interval="5m", progress=False)
    if df.empty or len(df) < 50: return
    
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]

    # 2. INDICATORS (Optimized for 5m)
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # 3. ANGLE (Inertia of the 15 EMA)
    y = df['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df['close'].mean() * 0.0001)))

    curr = df.iloc[-1]
    prev = df.iloc[-2]
    candle_time = df.index[-1] # Current candle timestamp

    # 4. COLOR FILTERS
    is_green = curr['close'] > curr['open']
    is_red = curr['close'] < curr['open']

    # --- BUY LOGIC (Green Candle + Uptrend + Touch) ---
    if candle_time != last_signal_time:
        if curr['close'] > curr['ema200'] and angle > 25 and is_green:
            if curr['low'] <= (curr['ema9'] + 0.15): # "Pocket" touch
                send_msg(f"🚀 *5M BUY SIGNAL*\n💰 Gold: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°\n✅ Logic: Bullish Retest")
                last_signal_time = candle_time

        # --- SELL LOGIC (Red Candle + Downtrend + Touch) ---
        elif curr['close'] < curr['ema200'] and angle < -25 and is_red:
            if curr['high'] >= (curr['ema9'] - 0.15): # "Pocket" touch
                send_msg(f"📉 *5M SELL SIGNAL*\n💰 Gold: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°\n✅ Logic: Bearish Retest")
                last_signal_time = candle_time

    print(f"[{time.strftime('%H:%M:%S')}] 5m Scan... Angle: {angle:.1f}°", flush=True)

# --- STARTUP ---
print("🚀 5-Minute Sniper Online. Scanning high-probability 5m setups...", flush=True)
send_msg("🤖 *5m Sniper Online:* Scanning 5-minute Gold candles.")

while (time.time() - START_TIME) < RUN_DURATION:
    try:
        get_signal()
        time.sleep(60) # Still checking every 60s to catch the close
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(10)

print("🏁 Finished run. Exiting for Green Checkmark.", flush=True)
