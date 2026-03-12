import asyncio
import json
import time
import random
import redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import argparse
import sys
import threading

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os

# Global state
demo_state = {
    "superbrain": {
        "price": 0.0,
        "seq": 0,
        "latency_us": 0.0,
        "consumers": 50
    },
    "redis": {
        "queue_length": 0,
        "rate_limit_hits": 0,
        "orders_processed": 0,
        "latest_alert": None
    },
    "topology": {
        "cluster_status": "active",
        "activity_log": [],
        "nodes": [
            {
                "name": "sb-bench-1",
                "ip": os.environ.get("DASHBOARD_NODE1_IP", "127.0.0.1"),
                "region": os.environ.get("DASHBOARD_NODE1_REGION", "Local (Feed + Redis + UI)"),
                "status": "online",
                "role": "coordinator"
            },
            {
                "name": "sb-bench-2",
                "ip": os.environ.get("DASHBOARD_NODE2_IP", "127.0.0.1"),
                "region": os.environ.get("DASHBOARD_NODE2_REGION", "Local (25 Strats)"),
                "status": "online",
                "role": "follower"
            },
            {
                "name": "sb-bench-3",
                "ip": os.environ.get("DASHBOARD_NODE3_IP", "127.0.0.1"),
                "region": os.environ.get("DASHBOARD_NODE3_REGION", "Local (25 Strats)"),
                "status": "online",
                "role": "follower"
            }
        ]
    }
}

# Serve the HTML dashboard
@app.get("/")
async def get_dashboard():
    print("Dashboard requested")
    with open("dashboard/index.html", "r") as f:
        return HTMLResponse(f.read())

# WebSocket to stream data to the frontend
@app.websocket("/ws/state")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send current state 10 times a second
            await websocket.send_json(demo_state)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass

# Background thread to monitor Redis and SuperBrain directly
def metrics_monitor(redis_host, redis_port):
    try:
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        r.ping()
    except:
        print("Metrics monitor could not connect to Redis.")
        return

    # Attempt to attach to SuperBrain to get the real live price
    try:
        from superbrain import DistributedContextFabric
        fabric = DistributedContextFabric()
        shm_pool = fabric.attach_context("live_market_data")
        is_sim = False
    except ImportError:
        from _sim_shared import MockFabric as DistributedContextFabric
        fabric = DistributedContextFabric()
        shm_pool = fabric.attach_context("live_market_data")
        is_sim = True

    # Pubsub for alerts
    pubsub = r.pubsub()
    pubsub.subscribe("market_alerts")

    # Tracking for simulated latency if needed
    avg_lat = 0.0

    while True:
        if demo_state["topology"]["cluster_status"] != "active":
            time.sleep(0.1)
            continue
            
        # Calculate active consumers
        total_consumers = 0
        for node in demo_state["topology"]["nodes"]:
            if node["status"] == "online":
                if "Strat" in node["region"]:
                    total_consumers += 25
        demo_state["superbrain"]["consumers"] = total_consumers
            
        # Update Redis stats
        demo_state["redis"]["queue_length"] = r.llen("order_queue")
        
        # Check alerts
        message = pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            alert = json.loads(message["data"])
            demo_state["redis"]["latest_alert"] = f"VOLATILITY SPIKE: ${alert['price']}"
            
        # Update SuperBrain stats
        read_start = time.perf_counter()
        tick = shm_pool.read("SYM")
        lat = (time.perf_counter() - read_start) * 1_000_000
        
        # Smooth actual latency for display
        if avg_lat == 0: avg_lat = lat
        else: avg_lat = (avg_lat * 0.9) + (lat * 0.1)
        
        if tick:
            demo_state["superbrain"]["price"] = tick["price"]
            demo_state["superbrain"]["seq"] = tick["seq"]
            demo_state["superbrain"]["latency_us"] = round(avg_lat, 1)

        time.sleep(0.05)


# Background thread to "process" the order queue so it doesn't grow infinitely forever
def order_processor(redis_host, redis_port):
    try:
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    except:
        return
        
    while True:
        if demo_state["topology"]["cluster_status"] != "active":
            time.sleep(0.1)
            continue
            
        # Process 1 order from the queue every ~100ms
        item = r.lpop("order_queue")
        if item:
            demo_state["redis"]["orders_processed"] += 1
            time.sleep(0.1) # Simulate execution time
        else:
            time.sleep(0.5)

def log_activity(msg):
    ts = time.strftime("%H:%M:%S")
    demo_state["topology"]["activity_log"].append(f"[{ts}] {msg}")
    if len(demo_state["topology"]["activity_log"]) > 100:
        demo_state["topology"]["activity_log"].pop(0)

def run_raft_election():
    demo_state["topology"]["cluster_status"] = "election"
    log_activity("⚠️ Heartbeat timeout! Coordinator lost.")
    log_activity("🗳️ Triggering Raft leadership election...")
    
    time.sleep(2.0) # Simulate election duration
    
    # Pick first online node as new leader
    online_nodes = [n for n in demo_state["topology"]["nodes"] if n["status"] == "online"]
    if not online_nodes:
        log_activity("🚨 CLUSTER OFFLINE: No available nodes for quorum.")
        demo_state["topology"]["cluster_status"] = "offline"
        return
        
    new_leader = online_nodes[0]
    new_leader["role"] = "coordinator"
    
    log_activity(f"👑 Node {new_leader['name']} elected as new Coordinator.")
    log_activity("✅ Quorum restored. Workload resuming.")
    demo_state["topology"]["cluster_status"] = "active"

@app.get("/api/node/{node_name}/{action}")
async def action_node(node_name: str, action: str):
    print(f"DEBUG: action_node hit -> node={node_name}, action={action}")
    node = next((n for n in demo_state["topology"]["nodes"] if n["name"] == node_name), None)
    if not node: 
        print(f"DEBUG: node {node_name} not found")
        return {"error": "Node not found"}
    
    if action == "crash":
        if node["status"] == "offline": return {"status": "ok"}
        node["status"] = "offline"
        log_activity(f"💥 Node {node_name} CRASHED.")
        print(f"DEBUG: {node_name} status -> offline")
        
        # If coordinator crashed, trigger election
        if node["role"] == "coordinator":
            node["role"] = "follower"
            threading.Thread(target=run_raft_election, daemon=True).start()
            
    elif action == "recover":
        if node["status"] == "online": return {"status": "ok"}
        node["status"] = "online"
        node["role"] = "follower"
        log_activity(f"🔧 Node {node_name} RECOVERED and joined as Follower.")
        print(f"DEBUG: {node_name} status -> online")
        
        if demo_state["topology"]["cluster_status"] == "offline":
            threading.Thread(target=run_raft_election, daemon=True).start()

    return {"status": "ok"}

def main():
    parser = argparse.ArgumentParser("Symbiosis Dashboard Server")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--redis-host", type=str, default="localhost")
    parser.add_argument("--redis-port", type=int, default=6379)
    args = parser.parse_args()
    
    import random
    
    # Start background threads
    t1 = threading.Thread(target=metrics_monitor, args=(args.redis_host, args.redis_port), daemon=True)
    t1.start()
    
    t2 = threading.Thread(target=order_processor, args=(args.redis_host, args.redis_port), daemon=True)
    t2.start()

    print(f"Starting API Server on port {args.port}...")
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="error")

if __name__ == "__main__":
    main()
