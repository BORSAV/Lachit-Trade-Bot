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
last_signal_time = None 

def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

def get_signal():
    global last_signal_time
    # 1. FETCH DATA (5m for trend, but we check every minute)
    df = yf.download(SYMBOL, period="2d", interval="5m", progress=False)
    if df.empty or len(df) < 50: return
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]

    # 2. EMERGENCY VELOCITY CHECK (Detects crashes instantly)
    # Using 1m data for the emergency check
    df_1m = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
    if not df_1m.empty:
        df_1m.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df_1m.columns]
        m1_close = df_1m['close'].iloc[-1]
        m1_prev = df_1m['close'].iloc[-2]
        change = m1_close - m1_prev
        
        if abs(change) >= 4.0:
            alert_type = "📉 CRASH" if change < 0 else "🚀 PUMP"
            send_msg(f"⚠️ *VELOCITY ALERT: {alert_type}*\n💰 Price: ${m1_close:.2f}\n⚡ Move: ${change:.2f} in 60s!")

    # 3. 5M TREND ANALYSIS
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # Angle of 15 EMA
    y = df['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df['close'].mean() * 0.0001)))

    curr = df.iloc[-1]
    candle_time = df.index[-1]
    is_green = curr['close'] > curr['open']
    is_red = curr['close'] < curr['open']

    # 4. SNIPER LOGIC (Only on Candle Close)
    if candle_time != last_signal_time:
        # BUY: Price > 200 EMA + High Angle + Green Candle + Touch EMA 9
        if curr['close'] > curr['ema200'] and angle > 25 and is_green:
            if curr['low'] <= (curr['ema9'] + 0.15):
                send_msg(f"🚀 *5M BUY SIGNAL*\n💰 Gold: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°\n🎯 Target 90L")
                last_signal_time = candle_time

        # SELL: Price < 200 EMA + Negative Angle + Red Candle + Touch EMA 9
        elif curr['close'] < curr['ema200'] and angle < -25 and is_red:
            if curr['high'] >= (curr['ema9'] - 0.15):
                send_msg(f"📉 *5M SELL SIGNAL*\n💰 Gold: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°\n🎯 Target 90L")
                last_signal_time = candle_time

    print(f"[{time.strftime('%H:%M:%S')}] Scan Active. Angle: {angle:.1f}° | Price: {curr['close']:.2f}", flush=True)

# --- STARTUP ---
print("🚀 High-Velocity 5M Sniper Online.", flush=True)
send_msg("⚡ *Sniper V2 Online:* 5m Trend + Emergency Velocity Active.")

while (time.time() - START_TIME) < RUN_DURATION:
    try:
        get_signal()
        time.sleep(60) 
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(10)
