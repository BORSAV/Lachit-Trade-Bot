import os
import pandas as pd
import yfinance as yf
import requests

# --- CONFIGURATION (Uses GitHub Secrets) ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SYMBOL = "GC=F"  # Gold (XAU/USD)

def send_telegram(message):
    """Sends a notification to your Telegram bot."""
    if not TOKEN or not CHAT_ID:
        print("Error: Telegram credentials missing.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try:
        requests.get(url)
    except Exception as e:
        print(f"Telegram Error: {e}")

def run_sentinel_bot():
    """Main logic for tracking Whales and Market Gaps."""
    print(f"Fetching data for {SYMBOL}...")
    
    # Fetch 2 days of 15m data to ensure we have enough candles
    df = yf.download(SYMBOL, period="2d", interval="15m")
    
    # Safety check: We need at least 21 candles for the 20-period lookback
    if len(df) < 21:
        print("Not enough data to calculate liquidity levels yet.")
        return

    # EXTRACTING SCALAR VALUES (The fix for the ValueError)
    # c1 = Movement Candle | c2 = Displacement | c3 = Current/Confirmation
    c1_low = df['Low'].iloc[-3].item()
    c1_high = df['High'].iloc[-3].item()
    c1_close = df['Close'].iloc[-3].item()
    
    c3_low = df['Low'].iloc[-1].item()
    c3_high = df['High'].iloc[-1].item()
    
    # --- LOGIC 1: THE LIQUIDITY SWEEP (Strategy 1) ---
    # Look back 20 candles (excluding the most recent ones)
    recent_low = df['Low'].iloc[-20:-3].min().item()
    recent_high = df['High'].iloc[-20:-3].max().item()
    
    # Bullish Sweep: Price dipped below recent low but closed above it
    if c1_low < recent_low and c1_close > recent_low:
        send_telegram("🚨 WHALE ALERT: Liquidity SWEEP (LOW) detected. Retail stops hit. Look for Buy.")

    # Bearish Sweep: Price spiked above recent high but closed below it
    if c1_high > recent_high and c1_close < recent_high:
        send_telegram("🚨 WHALE ALERT: Liquidity SWEEP (HIGH) detected. Retail stops hit. Look for Sell.")

    # --- LOGIC 2: THE FAIR VALUE GAP (Strategy 3) ---
    # Bullish FVG: Gap between Candle 1 High and Candle 3 Low
    if c3_low > c1_high:
        gap_size = c3_low - c1_high
        send_telegram(f"⚖️ MARKET GAP: Bullish FVG detected. Size: {round(gap_size, 2)} points.")

    # Bearish FVG: Gap between Candle 1 Low and Candle 3 High
    if c3_high < c1_low:
        gap_size = c1_low - c3_high
        send_telegram(f"⚖️ MARKET GAP: Bearish FVG detected. Size: {round(gap_size, 2)} points.")

    print("Scan complete.")

if __name__ == "__main__":
    run_sentinel_bot()
