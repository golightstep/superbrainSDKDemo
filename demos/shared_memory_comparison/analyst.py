import time
import json
import os
from config import REPORTER_KEY, ANALYST_KEY, CONTEXT_NAME, MARKET_DATA_FILE, TRADITIONAL_POLL_INTERVAL, LOG_FILE, SUPERBRAIN_TICK, CONFLICT_MODE_FILE
from superbrain_util import get_fabric

def analyze(data):
    score = data.get("signal", 0)
    sentiment = "Bullish" if score > 0.2 else "Bearish" if score < -0.2 else "Neutral"
    confidence = abs(score) * 100
    return {
        "ticker": data.get("ticker"),
        "sentiment": sentiment,
        "confidence": round(confidence, 1),
        "source_ts_ns": data.get("timestamp_ns"),
        "processed_ts_ns": time.time_ns(),
        "agent": "Analyst"
    }

def log_event(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] ANALYST: {msg}\n")
    except: pass

def run_analyst(mode="traditional"):
    print(f"📊 [Analyst] Starting in {mode} mode...")
    fabric = get_fabric()
    ctx = fabric.attach_context(CONTEXT_NAME)
    last_ts = 0

    while True:
        data = None
        if mode == "traditional":
            if os.path.exists(MARKET_DATA_FILE):
                try:
                    with open(MARKET_DATA_FILE, "r") as f:
                        data = json.load(f)
                except: pass
            
            time.sleep(TRADITIONAL_POLL_INTERVAL)
        else:
            raw = ctx.read(REPORTER_KEY)
            if raw: data = json.loads(raw)
            
            # Check for conflict mode to increase tick rate
            is_conflict = os.path.exists(CONFLICT_MODE_FILE)
            tick = SUPERBRAIN_TICK / 2 if is_conflict else SUPERBRAIN_TICK
            time.sleep(tick)
        
        if data and data.get("timestamp_ns") != last_ts:
            report = analyze(data)
            if mode == "traditional":
                with open(MARKET_DATA_FILE.replace(".json", "_analyst.json"), "w") as f:
                    json.dump(report, f)
            else:
                ctx.write(ANALYST_KEY, json.dumps(report))
            
            is_conflict = os.path.exists(CONFLICT_MODE_FILE)
            conflict_msg = " [CONFLICT ACTIVE]" if is_conflict else ""
            log_event(f"Processed {report['ticker']} ({report['sentiment']}){conflict_msg}")
            print(f"✅ [Analyst-{mode}] {report['ticker']}: {report['sentiment']}{conflict_msg}")
            last_ts = data.get("timestamp_ns")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "traditional"
    run_analyst(mode)
