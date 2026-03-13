import yfinance as yf
import pandas as pd
import numpy as np
import os
import time
import requests

# --- CONFIG ---
SYMBOL = "GC=F" # Gold Futures (XAU/USD)
INTERVAL = "1m"
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_msg(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}&parse_mode=Markdown"
        requests.get(url, timeout=5)
    except: pass

def full_trade_room_logic():
    # 1. FETCH DATA
    df = yf.download(SYMBOL, period="1d", interval=INTERVAL, progress=False)
    if df.empty or len(df) < 200: return
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # 2. THE THREE EMAs (9, 15, 200)
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # 3. THE 30-DEGREE SLOPE (Linear Regression)
    y = df['ema15'].iloc[-5:].values
    x = np.arange(len(y))
    slope, _ = np.polyfit(x, y, 1)
    angle = np.degrees(np.arctan(slope / (df['close'].mean() * 0.0001)))

    # 4. CANDLE DATA
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    body = abs(curr['close'] - curr['open'])
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    upper_wick = curr['high'] - max(curr['open'], curr['close'])
    avg_body = abs(df['close'] - df['open']).tail(10).mean()

    # --- STRATEGY FILTERS ---
    is_bullish_trend = curr['close'] > curr['ema200'] and curr['ema9'] > curr['ema15']
    is_strong_angle = angle > 25  # Human Eye '30-degree' rule
    is_at_ema = curr['low'] <= curr['ema9'] # Retest of the 9 EMA
    
    # --- CANDLE PATTERNS ---
    # A. Pin Bar (Hammer)
    is_pinbar = lower_wick > (1.8 * body) and lower_wick > (abs(curr['high'] - curr['low']) * 0.6)
    
    # B. Bullish Engulfing
    is_engulfing = (curr['close'] > prev['open']) and (prev['close'] < prev['open']) and (curr['close'] > curr['open'])
    
    # C. Big Bar (Momentum)
    is_bigbar = body > (avg_body * 1.6) and upper_wick < (body * 0.2) and curr['close'] > curr['open']

    # --- EXECUTION ---
    if is_bullish_trend and is_strong_angle and is_at_ema:
        pattern = ""
        if is_pinbar: pattern = "📍 Pin Bar / Hammer"
        elif is_engulfing: pattern = "🔥 Bullish Engulfing"
        elif is_bigbar: pattern = "🚀 Momentum Big Bar"

        if pattern:
            msg = (
                f"🎯 *TRADE ROOM SNIPER*\n"
                f"💰 Price: ${curr['close']:.2f}\n"
                f"📐 Angle: {angle:.1f}°\n"
                f"📝 Setup: {pattern} at 9 EMA"
            )
            send_msg(msg)
            print(f"✅ SIGNAL: {pattern}")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] Monitoring... Angle: {angle:.1f}°")

while True:
    try:
        full_trade_room_logic()
        time.sleep(60)
    except Exception as e:
        time.sleep(10)
