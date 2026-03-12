import pandas as pd
import yfinance as yf
import requests

# --- CONFIGURATION ---
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
SYMBOL = "GC=F" # Gold (XAU/USD)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

def run_sentinel_bot():
    # Fetch 15-minute data
    df = yf.download(SYMBOL, period="2d", interval="15m")
    
    # Last 3 candles for FVG
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    
    # --- LOGIC 1: THE LIQUIDITY SWEEP (The Hunter) ---
    # Look back 20 candles for the retail "Bait"
    recent_low = df['Low'].iloc[-20:-3].min()
    recent_high = df['High'].iloc[-20:-3].max()
    
    if c1['Low'] < recent_low and c1['Close'] > recent_low:
        send_telegram("🚨 WHALE ALERT: Liquidity SWEEP (LOW) detected. Retail stops hit. Look for Buy.")
    
    if c1['High'] > recent_high and c1['Close'] < recent_high:
        send_telegram("🚨 WHALE ALERT: Liquidity SWEEP (HIGH) detected. Retail stops hit. Look for Sell.")

    # --- LOGIC 2: THE FAIR VALUE GAP (The Imbalance) ---
    # Bullish FVG: Gap between Candle 1 High and Candle 3 Low
    if c3['Low'] > c1['High']:
        gap_size = c3['Low'] - c1['High']
        send_telegram(f"⚖️ MARKET GAP: Bullish FVG detected. Size: {round(gap_size, 2)}. Market is imbalanced.")

    # Bearish FVG: Gap between Candle 1 Low and Candle 3 High
    if c3['High'] < c1['Low']:
        gap_size = c1['Low'] - c3['High']
        send_telegram(f"⚖️ MARKET GAP: Bearish FVG detected. Size: {round(gap_size, 2)}. Market is imbalanced.")

# Run the check
run_sentinel_bot()
