import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time

# --- CONFIGURATION ---
SYMBOL = "GC=F"  # Gold Futures (XAU/USD equivalent)
INTERVAL = "1m"  # Mayank Sir uses 1m or 5m for Snipers
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
    requests.get(url)

def get_data():
    df = yf.download(tickers=SYMBOL, period='1d', interval=INTERVAL)
    # Ensure column names are standard
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    return df

def calculate_slope(series, period=5):
    """Calculates the change over time to emulate a degree angle"""
    diff = series.iloc[-1] - series.iloc[-1 - period]
    return diff

def sniper_logic():
    print("🔭 Scanning for Mayank Sniper setup...")
    df = get_data()
    
    # 1. Calculate EMAs
    df['ema9'] = ta.ema(df['close'], length=9)
    df['ema15'] = ta.ema(df['close'], length=15)
    
    if len(df) < 20: return

    # Get the latest two candles
    current = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 2. The 30-Degree Rule (Slope)
    # We check if the 15 EMA is actually moving, not flat
    slope_15 = calculate_slope(df['ema15'], period=5)
    
    # 3. Identify the setup (Bullish Example)
    # Filter A: Trend Direction (9 above 15 and 15 is sloping up)
    is_uptrend = current['ema9'] > current['ema15'] and slope_15 > 0.1
    
    # Filter B: The "Virtual Eye" (Retest of 9 EMA)
    # Candle low must touch or cross the 9 EMA
    did_retest = current['low'] <= current['ema9']
    
    # Filter C: The Confirmation (Green Candle Close)
    is_bullish_close = current['close'] > current['open']
    
    # Filter D: Rejection Wick (Lower wick should be significant)
    body_size = abs(current['close'] - current['open'])
    lower_wick = min(current['open'], current['close']) - current['low']
    has_rejection = lower_wick > (body_size * 0.5)

    if is_uptrend and did_retest and is_bullish_close and has_rejection:
        msg = (
            "🎯 *MAYANK SNIPER: BUY ALERT*\n"
            f"💰 Price: {current['close']:.2f}\n"
            "📈 Trend: Bullish (9/15 EMA)\n"
            f"📐 Slope: {slope_15:.4f} (Confirmed)\n"
            "🔥 Signal: 9 EMA Retest + Wick Rejection"
        )
        send_telegram_msg(msg)
        print("✅ Signal Sent!")

# --- MAIN LOOP ---
while True:
    try:
        sniper_logic()
        time.sleep(60) # Scan every minute
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
