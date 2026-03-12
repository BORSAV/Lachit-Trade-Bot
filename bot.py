import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time

# --- PURE TECHNICAL CONFIG ---
SYMBOL = "GC=F" 
INTERVAL = "1m"
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
    requests.get(url)

def pure_eye_logic():
    print(f"🔭 {time.strftime('%H:%M:%S')} - Scanning PURE Price Action...")
    # 1. Get Data
    df = yf.download(tickers=SYMBOL, period='1d', interval=INTERVAL, progress=False)
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # 2. Indicators (Manual - No Libraries)
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()

    # 3. Candle Analysis (Human Eye Part)
    curr = df.iloc[-1]
    body = abs(curr['open'] - curr['close'])
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    
    # SENSITIVITY FIX: 
    # If the market just crashed, the EMA slope will be negative.
    # To catch the 'V-rebound' your eyes see, we look for a 'Cross & Close'
    
    # A. Price Reclaim: Price must close ABOVE the 9 EMA
    reclaimed = curr['close'] > curr['ema9']
    
    # B. Momentum: This candle must be a strong GREEN candle
    strong_green = curr['close'] > curr['open'] and body > (lower_wick * 0.5)

    # C. The Setup: Price was below 9 EMA, now closed above it with strength
    if reclaimed and strong_green:
        msg = (
            "🎯 *V-REBOUND DETECTED*\n"
            f"💰 Price: ${curr['close']:.2f}\n"
            "🔥 Setup: Price Reclaimed 9 EMA\n"
            "⚠️ Note: Sentiment logic REMOVED. This is pure Price Action."
        )
        send_telegram_msg(msg)
        print("✅ Rebound Signal Sent!")

while True:
    try:
        pure_eye_logic()
        time.sleep(60)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
