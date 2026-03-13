import time
import json
import os
from config import ANALYST_KEY, FACT_CHECKER_KEY, CONTEXT_NAME, MARKET_DATA_FILE, FACT_CHECK_INTERVAL, LOG_FILE, SUPERBRAIN_TICK, CONFLICT_MODE_FILE
from superbrain_util import get_fabric

def verify(report):
    is_valid = report.get("confidence", 0) > 40
    return {
        "ticker": report.get("ticker"),
        "verified": is_valid,
        "sentiment": report.get("sentiment"),
        "confidence": report.get("confidence"), # Passing through for UI vis
        "verified_ts_ns": time.time_ns(),
        "source_ts_ns": report.get("source_ts_ns"),
        "agent": "Fact Checker"
    }

def log_event(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] FACT CHECKER: {msg}\n")
    except: pass

def run_fact_checker(mode="traditional"):
    print(f"🧐 [Fact Checker] Starting in {mode} mode...")
    fabric = get_fabric()
    ctx = fabric.attach_context(CONTEXT_NAME)
    last_ts = 0

    while True:
        report = None
        if mode == "traditional":
            path = MARKET_DATA_FILE.replace(".json", "_analyst.json")
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        report = json.load(f)
                except: pass
            time.sleep(FACT_CHECK_INTERVAL)
        else:
            raw = ctx.read(ANALYST_KEY)
            if raw: report = json.loads(raw)
            
            # Check for conflict mode to increase tick rate
            is_conflict = os.path.exists(CONFLICT_MODE_FILE)
            tick = SUPERBRAIN_TICK / 2 if is_conflict else SUPERBRAIN_TICK
            time.sleep(tick)
        
        if report and report.get("processed_ts_ns") != last_ts:
            verified_report = verify(report)
            if mode == "traditional":
                with open(MARKET_DATA_FILE.replace(".json", "_verified.json"), "w") as f:
                    json.dump(verified_report, f)
            else:
                ctx.write(FACT_CHECKER_KEY, json.dumps(verified_report))
            
            is_conflict = os.path.exists(CONFLICT_MODE_FILE)
            status_symbol = "🔥" if is_conflict else "🔍"
            log_event(f"Verified {verified_report['ticker']} - Status: {verified_report['verified']}")
            print(f"{status_symbol} [Fact Checker-{mode}] Verified {verified_report['ticker']}: {verified_report['verified']}")
            last_ts = report.get("processed_ts_ns")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "traditional"
    run_fact_checker(mode)
