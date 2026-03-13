import time
import json
import random
import os
from config import REPORTER_KEY, CONTEXT_NAME, MARKET_DATA_FILE, SCRAPER_INTERVAL, CONFLICT_MODE_FILE
from superbrain_util import get_fabric

def generate_signal(conflict=False):
    tickers = ["NVDA", "AAPL", "GOOGL", "BTC"]
    ticker = random.choice(tickers)
    
    # In conflict mode, we might oscillate rapidly
    if conflict:
        price = round(random.uniform(100, 150), 2)
        sentiment = random.choice([-0.8, 0.8]) # Strong conflicting signals
    else:
        price = round(random.uniform(400, 500), 2)
        sentiment = round(random.uniform(-1, 1), 2)
        
    return {
        "ticker": ticker,
        "price": price,
        "signal": sentiment,
        "timestamp_ns": time.time_ns(),
        "agent": "Reporter"
    }

def run_reporter(mode="traditional"):
    print(f"🕵️ [Reporter] Starting in {mode} mode...")
    fabric = get_fabric()
    ctx = fabric.attach_context(CONTEXT_NAME)
    
    while True:
        is_conflict = os.path.exists(CONFLICT_MODE_FILE)
        data = generate_signal(is_conflict)
        
        if mode == "traditional":
            with open(MARKET_DATA_FILE, "w") as f:
                json.dump(data, f)
        else:
            ctx.write(REPORTER_KEY, json.dumps(data))
            
        print(f"📡 [Reporter] Update: {data['ticker']} @ ${data['price']}")
        
        # Conflict mode runs much faster to create race conditions
        sleep_time = 0.1 if is_conflict else SCRAPER_INTERVAL
        time.sleep(sleep_time)

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "traditional"
    run_reporter(mode)
