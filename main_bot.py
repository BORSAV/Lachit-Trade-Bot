import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
import requests

# --- CONFIG ---
SYMBOL = "GC=F" # Gold
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
START_TIME = time.time()
RUN_DURATION = 3000  # Runs for 50 minutes then exits for Green Tick

def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Error: Telegram Secrets missing in GitHub!", flush=True)
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"❌ Telegram Error: {response.text}", flush=True)
        else:
            print(f"📡 Telegram Delivered Successfully!", flush=True)
    except Exception as e:
        print(f"❌ Connection Error: {e}", flush=True)

def get_signal():
    # 1. Fetch Data
    df = yf.download(SYMBOL, period="1d", interval="1m", progress=False)
    if df.empty or len(df) < 200: return
    
    # 2. Fix Column Names
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]

    # 3. Indicators (9, 15, 200 EMA)
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # 4. Angle Calculation (Slope of 15 EMA)
    y = df['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df['close'].mean() * 0.0001)))

    # 5. Candle Anatomy
    curr, prev = df.iloc[-1], df.iloc[-2]
    body = abs(curr['close'] - curr['open'])
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    upper_wick = curr['high'] - max(curr['open'], curr['close'])
    avg_body = abs(df['close'] - df['open']).tail(10).mean()

    # --- BUY LOGIC (+30°) ---
    if curr['close'] > curr['ema200'] and curr['ema9'] > curr['ema15'] and angle > 25:
        if curr['low'] <= (curr['ema9'] + 0.1): # Retest
            is_pinbar = lower_wick > (1.8 * body)
            is_engulfing = (curr['close'] > prev['open']) and (prev['close'] < prev['open'])
            if is_pinbar or is_engulfing:
                p_type = "Pin Bar" if is_pinbar else "Engulfing"
                send_msg(f"🚀 *BUY SIGNAL (Gold)*\n💰 Price: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°\n📍 Type: {p_type} Retest")
                print(f"✅ BUY SIGNAL: {p_type}", flush=True)

    # --- SELL LOGIC (-30°) ---
    elif curr['close'] < curr['ema200'] and curr['ema9'] < curr['ema15'] and angle < -25:
        if curr['high'] >= (curr['ema9'] - 0.1): # Retest
            is_shooting_star = upper_wick > (1.8 * body)
            is_bearish_engulfing = (curr['close'] < prev['open']) and (prev['close'] > prev['open'])
            if is_shooting_star or is_bearish_engulfing:
                p_type = "Shooting Star" if is_shooting_star else "Bearish Engulfing"
                send_msg(f"📉 *SELL SIGNAL (Gold)*\n💰 Price: ${curr['close']:.2f}\n📐 Angle: {angle:.1f}°\n📍 Type: {p_type} Retest")
                print(f"✅ SELL SIGNAL: {p_type}", flush=True)

    else:
        print(f"[{time.strftime('%H:%M:%S')}] Monitoring... Angle: {angle:.1f}°", flush=True)

# --- LOOP FOR GREEN CHECKMARK ---
print("🚀 Bot Started. Monitoring Buys (>25°) and Sells (<-25°)...", flush=True)
while (time.time() - START_TIME) < RUN_DURATION:
    try:
        get_signal()
        time.sleep(60)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        time.sleep(10)

print("🏁 Finished run. Exiting for Green Checkmark.", flush=True)
