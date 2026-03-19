#!/usr/bin/env python3
"""
Trip Planner Comparison Server
-------------------------------
Serves the dashboard and runs both the Vanilla and SuperBrain SDK
implementations in parallel, streaming real-time logs via SSE.

Usage:
    python3 server.py
    → http://localhost:8787/dashboard/index.html
"""

import http.server
import json
import subprocess
import sys
import os
import threading
import time
from pathlib import Path

BASE_DIR   = Path(__file__).parent
VANILLA_DIR = BASE_DIR / "vanilla"
SDK_DIR    = BASE_DIR / "superbrain_sdk"

# ── Shared state ──────────────────────────────────────────────────
run_state = {
    "running": False,
    "done":    False,
    "error":   None,
    "vanilla_log": [],
    "sdk_log":     [],
    "vanilla_metrics": None,
    "sdk_metrics":     None,
}
state_lock = threading.Lock()

# Track active subprocesses so watchdog can kill them
active_procs: dict[str, subprocess.Popen] = {}
procs_lock = threading.Lock()

def reset_state():
    with state_lock:
        run_state.update({
            "running": True,
            "done":    False,
            "error":   None,
            "vanilla_log": [],
            "sdk_log":     [],
            "vanilla_metrics": None,
            "sdk_metrics":     None,
        })

def run_impl(path: Path, log_key: str, trip_params: dict):
    """Run one implementation, appending stdout lines to log_key."""
    venv_python = path / ".venv" / "bin" / "python"
    python_exec = str(venv_python) if venv_python.exists() else sys.executable

    env = os.environ.copy()
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    env[k.strip()] = v
    
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"]      = str(path)
    env["SUPERBRAIN_FORCE_MOCK"] = "1"
    # Ensure all env vars are strings (not lists from JSON)
    def to_str(v):
        if isinstance(v, list): return ", ".join(v)
        return str(v)

    env["TRIP_LOCATION"]  = to_str(trip_params.get("origin",    "Mumbai"))
    env["TRIP_CITIES"]    = to_str(trip_params.get("cities",    "London, Paris"))
    env["TRIP_DATES"]     = to_str(trip_params.get("dates",     "July 2026"))
    env["TRIP_INTERESTS"] = to_str(trip_params.get("interests", "History, Food, Art"))
    env["LITELLM_MAX_RETRIES"] = "0"
    env["OPENAI_MAX_RETRIES"] = "0"
    env["LLM_REQUEST_TIMEOUT"] = "25"

    with state_lock:
        msg = f"🚀 Starting {log_key.replace('_log','')}..."
        run_state[log_key].append({"type": "info", "text": msg})
        print(f"[{log_key.replace('_log','').upper()}] {msg}", flush=True)

    try:
        proc = subprocess.Popen(
            [python_exec, "-u", "main.py"],
            cwd=str(path),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        
        with procs_lock:
            active_procs[log_key] = proc
            
        # Non-blocking read loop
        os.set_blocking(proc.stdout.fileno(), False)
        
        while True:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
                
            line = line.strip()
            if line.startswith("METRICS:"):
                try:
                    m = json.loads(line[8:])
                    metrics_key = "vanilla_metrics" if log_key == "vanilla_log" else "sdk_metrics"
                    with state_lock:
                        run_state[metrics_key] = m
                        print(f"[{log_key.replace('_log','').upper()}] Metrics received.", flush=True)
                except Exception: pass
                continue

            if line and "WORKER_FINISHED" not in line:
                # Echo to terminal so manual runs aren't "silent"
                prefix = f"[{log_key.replace('_log','').upper()}]"
                print(f"{prefix} {line}", flush=True)
                
                with state_lock:
                    run_state[log_key].append({"type": "log", "text": line})

        proc.wait(timeout=2)
        rc = proc.returncode
        done_text = "✅ Finished successfully." if rc == 0 else f"❌ Exited with code {rc}"
        with state_lock:
            run_state[log_key].append({
                "type": "done",
                "rc":   rc,
                "text": done_text
            })
            print(f"[{log_key.replace('_log','').upper()}] {done_text}", flush=True)
    except Exception as exc:
        err_msg = f"Subprocess error: {str(exc)}"
        with state_lock:
            run_state[log_key].append({"type": "error", "text": err_msg})
            print(f"[{log_key.replace('_log','').upper()}] ❌ {err_msg}", flush=True)
            if not any(e.get("type") == "done" for e in run_state[log_key]):
                run_state[log_key].append({"type": "done", "rc": -1, "text": "❌ Terminated."})
    finally:
        with procs_lock:
            active_procs.pop(log_key, None)

def run_both(params: dict):
    """Run both implementations in parallel with watchdog."""
    print("\n--- Parallel Run Started ---", flush=True)
    t1 = threading.Thread(target=run_impl, args=(VANILLA_DIR, "vanilla_log", params), daemon=True)
    t2 = threading.Thread(target=run_impl, args=(SDK_DIR, "sdk_log", params), daemon=True)
    t1.start(); t2.start()
    
    start_wait = time.time()
    # 600s timeout (increased for local LLMs)
    while (t1.is_alive() or t2.is_alive()) and (time.time() - start_wait < 600):
        time.sleep(0.5)
    
    if t1.is_alive() or t2.is_alive():
        print("⚠️ Warning: Watchdog timeout reached. Killing processes.", flush=True)
        with procs_lock:
            for log_key in list(active_procs.keys()):
                p = active_procs.get(log_key)
                if p:
                    try:
                        p.kill()
                        print(f"Watchdog killed {log_key} subprocess.", flush=True)
                    except: pass

        # Short pause to allow threads to exit after kill
        time.sleep(1)

        with state_lock:
            for key in ["vanilla_log", "sdk_log"]:
                if not any(e.get("type") == "done" for e in run_state[key]):
                    run_state[key].append({
                        "type": "done",
                        "rc": -1,
                        "text": "❌ Execution timed out (120s limit)"
                    })

    with state_lock:
        if not (run_state["vanilla_metrics"] and run_state["sdk_metrics"]):
            run_state["error"] = "One or more implementations failed to report metrics in time."
        run_state["running"] = False
        run_state["done"]    = True
    print("--- Parallel Run Finished ---\n", flush=True)


# ── HTTP Handler ──────────────────────────────────────────────────
class Handler(http.server.SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self._cors(200)
        self.end_headers()

    # ── GET ──
    def do_GET(self):

        # SSE: /api/stream?impl=vanilla|sdk
        if self.path.startswith("/api/stream"):
            impl    = "vanilla" if "vanilla" in self.path else "sdk"
            log_key = f"{impl}_log"
            idx     = 0
            last_heartbeat = time.time()

            self.send_response(200)
            self._cors()
            self.send_header("Content-Type",  "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            try:
                while True:
                    with state_lock:
                        logs = list(run_state[log_key])
                    while idx < len(logs):
                        entry = logs[idx]
                        self._sse(json.dumps(entry))
                        idx += 1
                        if entry.get("type") == "done":
                            return
                    
                    # Heartbeat every 5s to keep connection alive
                    if time.time() - last_heartbeat > 5:
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
                        last_heartbeat = time.time()

                    # If run finished but no "done" yet (error), bail
                    with state_lock:
                        if not run_state["running"] and not run_state["done"]:
                            return
                    time.sleep(0.2)
            except (BrokenPipeError, ConnectionResetError):
                return

        # JSON results
        elif self.path.startswith("/api/results"):
            with state_lock:
                if run_state["vanilla_metrics"] and run_state["sdk_metrics"]:
                    data = json.dumps({
                        "vanilla": run_state["vanilla_metrics"],
                        "superbrain_sdk": run_state["sdk_metrics"]
                    }).encode()
                    self.send_response(200)
                    self._cors()
                    self.send_header("Content-Type",   "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self._json(404, {"error": "Metrics not available yet"})

        # Run status
        elif self.path.startswith("/api/status"):
            with state_lock:
                payload = {
                    "running": run_state["running"],
                    "done":    run_state["done"],
                    "error":   run_state["error"],
                }
            self._json(200, payload)

        else:
            super().do_GET()

    # ── POST /api/run ──
    def do_POST(self):
        if self.path != "/api/run":
            self._json(404, {"error": "Not found"})
            return

        with state_lock:
            if run_state["running"]:
                self._json(409, {"error": "Already running"})
                return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length else b"{}"
        try:
            params = json.loads(body)
        except Exception:
            params = {}

        reset_state()
        threading.Thread(target=run_both, args=(params,), daemon=True).start()

        self._json(200, {"ok": True})

    # ── helpers ──
    def _cors(self, code=None):
        if code:
            self.send_response(code)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _sse(self, data: str):
        self.wfile.write(f"data: {data}\n\n".encode())
        self.wfile.flush()

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress per-request noise


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    port = 8787
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("", port), Handler)
    server.directory = str(BASE_DIR)
    print(f"🧠 Trip Planner Comparison Server")
    print(f"   → http://localhost:{port}/dashboard/index.html")
    print(f"   Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
