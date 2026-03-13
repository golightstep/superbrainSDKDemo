import time
import json
import os
from config import FACT_CHECKER_KEY, PRODUCER_KEY, TIMELINE_KEY, METRICS_KEY, CONTEXT_NAME, MARKET_DATA_FILE, LOG_FILE, SUPERBRAIN_TICK, CONFLICT_MODE_FILE
from superbrain_util import get_fabric

def generate_cue(verified_report, mode):
    ready = verified_report.get("verified", False)
    return {
        "ticker": verified_report.get("ticker"),
        "ready": ready,
        "mode": mode,
        "cue_ts_ns": time.time_ns(),
        "source_ts_ns": verified_report.get("source_ts_ns"),
        "agent": "Producer"
    }

def update_metrics_and_timeline(ctx, mode):
    event = {
        "event": "Studio Cue Issued",
        "ts": time.time(),
        "mode": mode
    }
    raw = ctx.read(TIMELINE_KEY)
    events = json.loads(raw) if raw else []
    events.append(event)
    ctx.write(TIMELINE_KEY, json.dumps(events[-10:]))

def run_producer(mode="traditional"):
    print(f"🎬 [Producer] Starting in {mode} mode...")
    fabric = get_fabric()
    ctx = fabric.attach_context(CONTEXT_NAME)
    last_ts = 0

    while True:
        verified_report = None
        if mode == "traditional":
            path = MARKET_DATA_FILE.replace(".json", "_verified.json")
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        verified_report = json.load(f)
                except: pass
            time.sleep(TRADITIONAL_POLL_INTERVAL)
        else:
            raw = ctx.read(FACT_CHECKER_KEY)
            if raw: verified_report = json.loads(raw)
            
            is_conflict = os.path.exists(CONFLICT_MODE_FILE)
            tick = SUPERBRAIN_TICK / 2 if is_conflict else SUPERBRAIN_TICK
            time.sleep(tick)
        
        if verified_report and verified_report.get("verified_ts_ns") != last_ts:
            cue = generate_cue(verified_report, mode)
            
            # Calculate Latency (Exact)
            source_ts_ns = verified_report.get("source_ts_ns", 0)
            latency_s = (time.time_ns() - source_ts_ns) / 1e9 if source_ts_ns > 0 else 0
            
            if mode == "traditional":
                with open(MARKET_DATA_FILE.replace(".json", "_cue.json"), "w") as f:
                    json.dump(cue, f)
                # Traditional latency is shared via side-channel file or just calculated in UI
            else:
                ctx.write(PRODUCER_KEY, json.dumps(cue))
                update_metrics_and_timeline(ctx, mode)
                
                # Write real-time metrics for Superbrain
                metrics = {
                    "latency": latency_s,
                    "staleness": 0, # Superbrain is near 0
                    "is_conflict": os.path.exists(CONFLICT_MODE_FILE)
                }
                ctx.write(METRICS_KEY, json.dumps(metrics))
            
            print(f"🎞️ [Producer-{mode}] Broadcast Cue: {cue['ticker']} - Latency: {latency_s:.6f}s")
            last_ts = verified_report.get("verified_ts_ns")

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "traditional"
    run_producer(mode)
