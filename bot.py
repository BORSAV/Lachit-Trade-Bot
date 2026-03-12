import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time

# --- CONFIGURATION ---
SYMBOL = "GC=F"  # Gold Futures (XAU/USD)
INTERVAL = "1m"
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
        requests.get(url)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_data():
    # Downloads recent data
    df = yf.download(tickers=SYMBOL, period='1d', interval=INTERVAL, progress=False)
    # Fix multi-index columns if necessary
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    return df

def sniper_logic():
    print(f"🔭 {time.strftime('%H:%M:%S')} - Scanning with Human Eye Logic...")
    df = get_data()
    
    if len(df) < 20:
        return

    # 1. Manual EMA Calculation (Fast & Reliable)
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema15'] = df['close'].ewm(span=15, adjust=False).mean()

    # 2. Angle/Slope Calculation (The 30° Rule)
    # We compare the current EMA to 5 minutes ago to see the "steepness"
    lookback = 5
    price_change = df['ema15'].iloc[-1] - df['ema15'].iloc[-lookback]
    # Normalizing price change to degrees (approximate)
    angle = np.degrees(np.arctan(price_change / (df['close'].mean() * 0.0001)))

    # 3. Candlestick Analysis (The Human Eye)
    current = df.iloc[-1]
    body = abs(current['open'] - current['close'])
    lower_wick = min(current['open'], current['close']) - current['low']
    total_range = current['high'] - current['low']

    # --- THE SNIPER RULES ---
    
    # RULE 1: Uptrend Check (9 above 15 + Angle must be steep, not flat)
    is_uptrend = current['ema9'] > current['ema15'] and angle > 20
    
    # RULE 2: The Retest (Price dipped to touch the 9 EMA)
    did_retest = current['low'] <= current['ema9']
    
    # RULE 3: Wick Rejection (Lower wick is > 2x the body = Hammer/Pin Bar)
    # This ensures the bot "sees" the bounce, not just a crash through the line
    has_rejection = lower_wick > (2 * body) and lower_wick > (total_range * 0.5)
    
    # RULE 4: Confirmation (Candle closed Green/Bullish)
    is_green = current['close'] > current['open']

    if is_uptrend and did_retest and has_rejection and is_green:
        msg = (
            "🎯 *SNIPER BUY SIGNAL*\n"
            f"💰 Entry Price: ${current['close']:.2f}\n"
            f"📐 Trend Angle: {angle:.1f}°\n"
            "🔥 Setup: 9 EMA Retest + Hammer Wick\n"
            "🛡️ SL: Below Signal Candle Low"
        )
        send_telegram_msg(msg)
        print("✅ Alert Sent to Telegram")

# --- EXECUTION LOOP ---
while True:
    try:
        sniper_logic()
        # Scan every minute for the 1m chart
        time.sleep(60)
    except Exception as e:
        print(f"Main Loop Error: {e}")
        time.sleep(10)
