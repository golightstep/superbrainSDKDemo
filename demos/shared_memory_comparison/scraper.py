import time
import json
import random
import os
from config import MARKET_DATA_FILE, CONTEXT_NAME, MARKET_KEY, SCRAPER_INTERVAL
from superbrain_util import get_fabric

def generate_mock_data():
    tickers = ["AAPL", "GOOGL", "TSLA", "BTC", "ETH"]
    ticker = random.choice(tickers)
    price = round(random.uniform(100, 50000), 2)
    sentiment_score = round(random.uniform(-1, 1), 2)
    return {
        "ticker": ticker,
        "price": price,
        "raw_sentiment": sentiment_score,
        "timestamp": time.time()
    }

def run_scraper(mode="traditional"):
    print(f"🚀 [Scraper] Starting in {mode} mode...")
    
    fabric = get_fabric()
    ctx = fabric.attach_context(CONTEXT_NAME)
    
    while True:
        data = generate_mock_data()
        
        if mode == "traditional":
            with open(MARKET_DATA_FILE, "w") as f:
                json.dump(data, f)
            print(f"📡 [Scraper] Data written to JSON: {data['ticker']} @ {data['price']}")
        else:
            ctx.write(MARKET_KEY, json.dumps(data))
            print(f"🧠 [Scraper] Data written to Superbrain: {data['ticker']} @ {data['price']}")
            
        time.sleep(SCRAPER_INTERVAL)

if __name__ == "__main__":
    import sys
    mode = "traditional"
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    run_scraper(mode)
