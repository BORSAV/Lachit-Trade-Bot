import os
import asyncio
import pandas as pd
import yfinance as yf
import requests

# --- 1. CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SYMBOL = "GC=F"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}&parse_mode=Markdown"
    requests.get(url)

# --- 2. THE THREE LOGIC MODULES ---

async def strategy_whale_sweep():
    """Bot 1: Liquidity Sweeps"""
    df = yf.download(SYMBOL, period="2d", interval="15m")
    c1_low = df['Low'].iloc[-3].item()
    c1_close = df['Close'].iloc[-3].item()
    recent_low = df['Low'].iloc[-20:-3].min().item()
    
    if c1_low < recent_low and c1_close > recent_low:
        send_telegram("🚨 *WHALE ALERT*\n━━━━━━━━━━━━━━━\nType: Liquidity Sweep (LOW)\nStatus: Bullish Confirmation")

async def strategy_fvg_scanner():
    """Bot 2: Fair Value Gaps"""
    df = yf.download(SYMBOL, period="2d", interval="15m")
    c1_high = df['High'].iloc[-3].item()
    c3_low = df['Low'].iloc[-1].item()
    
    if c3_low > c1_high:
        gap = round(c3_low - c1_high, 2)
        send_telegram(f"⚖️ *MARKET GAP*\n━━━━━━━━━━━━━━━\nType: Bullish FVG\nSize: {gap} points")

async def strategy_sentiment():
    """Bot 3: Mayank Sir / Sentiment Logic"""
    # Put your specific sentiment or price-action score logic here
    # Example:
    score = 7 # Placeholder for your Mayank Sir logic
    if score > 5:
        send_telegram("🔥 *SENTIMENT SCORE*\n━━━━━━━━━━━━━━━\nScore: 7/10\nBias: STRONG BUY")

# --- 3. THE MASTER RUNNER ---

async def main():
    print("🚀 Lachit Multi-Bot is live...")
    # This runs all three functions at the same time
    await asyncio.gather(
        strategy_whale_sweep(),
        strategy_fvg_scanner(),
        strategy_sentiment()
    )

if __name__ == "__main__":
    asyncio.run(main())
