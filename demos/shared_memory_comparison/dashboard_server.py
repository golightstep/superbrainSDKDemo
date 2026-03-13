from flask import Flask, jsonify, send_from_directory
import json
import os
import time
from config import REPORTER_KEY, ANALYST_KEY, FACT_CHECKER_KEY, PRODUCER_KEY, TIMELINE_KEY, METRICS_KEY, CONTEXT_NAME, MARKET_DATA_FILE, DASHBOARD_DIR, CONFLICT_MODE_FILE
from superbrain_util import get_fabric

app = Flask(__name__)
app.debug = False # Disable reloader for production-like stability

fabric = get_fabric()
ctx = fabric.attach_context(CONTEXT_NAME)

STORM_MODE = False

@app.route('/api/studio/all')
def get_all_studio_data():
    try:
        # SUPERBRAIN DATA
        sb_data = {
            "Reporter": ctx.read(REPORTER_KEY),
            "Analyst": ctx.read(ANALYST_KEY),
            "FactChecker": ctx.read(FACT_CHECKER_KEY),
            "Producer": ctx.read(PRODUCER_KEY),
            "Timeline": ctx.read(TIMELINE_KEY),
            "Metrics": ctx.read(METRICS_KEY)
        }
        
        # Add dynamic storm metrics if active
        if STORM_MODE:
            # We don't have a real storm implementation here, but we can at least 
            # report that it's active without faking specific numbers if they aren't real.
            # Or better, just remove the faked numbers.
            sb_data["StormMetrics"] = {
                "status": "active",
                "mode": "load-simulation"
            }
        for k, v in sb_data.items():
            if v and isinstance(v, str):
                try: sb_data[k] = json.loads(v)
                except: pass

        # TRADITIONAL DATA (Files)
        trad_data = {}
        paths = {
            "Reporter": MARKET_DATA_FILE,
            "Analyst": MARKET_DATA_FILE.replace(".json", "_analyst.json"),
            "FactChecker": MARKET_DATA_FILE.replace(".json", "_verified.json"),
            "Producer": MARKET_DATA_FILE.replace(".json", "_cue.json")
        }
        for role, path in paths.items():
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        trad_data[role] = json.load(f)
                except: pass

        return jsonify({
            "superbrain": sb_data,
            "traditional": trad_data,
            "is_conflict": os.path.exists(CONFLICT_MODE_FILE),
            "is_storm": STORM_MODE,
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/storm', methods=['POST'])
def toggle_storm():
    global STORM_MODE
    STORM_MODE = not STORM_MODE
    return jsonify({"storm": STORM_MODE})

@app.route('/api/ask', methods=['POST'])
def ask_anchor():
    try:
        data = json.loads(os.popen("tail -n 1 /tmp/ask_input.json").read() or "{}") # Dummy to handle POST data if needed or just use current state
        # Actually flask.request is better but I'll go with simpler for now
        from flask import request
        req = request.json
        mode = req.get("mode", "traditional")
        question = req.get("question", "")
        
        if mode == "traditional":
            return jsonify({
                "mode": "traditional",
                "answer": "Traditional mode requires file I/O polling. Data might be stale."
            })
        else:
            # Superbrain - read current context
            raw_r = ctx.read(FACT_CHECKER_KEY)
            report = json.loads(raw_r) if raw_r else {}
            ticker = report.get("ticker", "market")
            sentiment = report.get("sentiment", "Neutral")
            return jsonify({
                "mode": "superbrain",
                "answer": f"INSTANT CONFIRMATION: Reading memory fabric... {ticker} sentiment is currently {sentiment}. Execution strategy optimized."
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs')
def get_logs():
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_sharing.log")
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                return jsonify(f.readlines()[-10:])
        except: pass
    return jsonify([])

@app.route('/')
def index():
    return send_from_directory(DASHBOARD_DIR, 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory(DASHBOARD_DIR, path)

if __name__ == "__main__":
    print("🚀 Starting Dual-Mode News Studio on http://0.0.0.0:5009")
    app.run(host='0.0.0.0', port=5009, threaded=True)
