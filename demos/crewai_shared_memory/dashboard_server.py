import os
import json
import asyncio
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import random

# =============================================================================
# 1. ROBUST MEMORY MOCK
# =============================================================================

class MockContext:
    def __init__(self, store):
        self.store = store
    def write(self, k, v):
        print(f"[TRACE] Fabric Write: {k}")
        self.store[k] = v
    def read(self, k):
        val = self.store.get(k)
        print(f"[TRACE] Fabric Read: {k} -> {type(val)}")
        return val
    def list_keys(self):
        keys = list(self.store.keys())
        print(f"[TRACE] Fabric List Keys: {len(keys)} items")
        return keys

class MockFabric:
    def __init__(self):
        self._stores = {}
    def attach_context(self, name):
        if name not in self._stores:
            self._stores[name] = {}
        return MockContext(self._stores[name])

try:
    from superbrain import DistributedContextFabric
    # Test initialization to catch shared library errors
    _test = DistributedContextFabric()
    print("✅ Real SuperBrain SDK loaded.")
except Exception as e:
    print(f"⚠️ SuperBrain SDK simulated (Local initialization failed: {e}).")
    DistributedContextFabric = MockFabric

# =============================================================================
# 2. SERVER STATE
# =============================================================================

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

demo_state = {
    "phase": "idle",
    "crew1_logs": [],
    "crew2_logs": [],
    "shared_memory": [],
    "events": []
}

fabric = DistributedContextFabric()
shared_ctx = fabric.attach_context("crewai_shared_collective")

class ConnectionManager:
    def __init__(self): self.active_connections = []
    async def connect(self, ws):
        await ws.accept()
        self.active_connections.append(ws)
    def disconnect(self, ws): self.active_connections.remove(ws)
    async def broadcast(self, message):
        for connection in self.active_connections:
            try: await connection.send_json(message)
            except: pass

manager = ConnectionManager()

def log_event(phase, msg, type="info"):
    entry = {"ts": time.time(), "msg": msg, "type": type}
    if phase == "research": demo_state["crew1_logs"].append(entry)
    elif phase == "writing": demo_state["crew2_logs"].append(entry)
    demo_state["events"].append({"type": "log", "phase": phase, "data": entry})
    print(f"[{phase.upper()}] {msg}")

def save_to_memory(data, meta):
    start_time = time.perf_counter()
    key = f"mem_{time.time_ns()}"
    val = {"content": data, "meta": meta, "ts": time.time()}
    shared_ctx.write(key, json.dumps(val))
    latency_us = (time.perf_counter() - start_time) * 1_000_000
    
    demo_state["shared_memory"].append(val)
    demo_state["last_write_latency"] = round(latency_us, 2)
    demo_state["events"].append({"type": "memory_write", "data": val, "latency": round(latency_us, 2)})

# =============================================================================
# 3. CREW SIMULATION
# =============================================================================

async def run_crew_1():
    try:
        demo_state["phase"] = "research"
        log_event("research", "🚀 Crew 1 (Researchers) Initialized", "system")
        await asyncio.sleep(0.5)
        
        agents = ["Tech Analyst", "Hardware Expert"]
        for agent in agents:
            log_event("research", f"🕵️ {agent} is analyzing SuperBrain performance...", "agent")
            await asyncio.sleep(1.0)
            
        log_event("research", "💡 Found Key Fact: 13.5µs Latency", "discovery")
        save_to_memory("SuperBrain achieves 13.5 microseconds fan-out latency.", {"source": "Tech Analyst", "type": "fact"})
        await asyncio.sleep(0.5)
        
        log_event("research", "✅ Phase 1 Complete.", "system")
    finally:
        demo_state["phase"] = "idle"

async def run_crew_2():
    try:
        demo_state["phase"] = "writing"
        log_event("writing", "🚀 Crew 2 (Creative Team) Initialized", "system")
        await asyncio.sleep(1.0)
        
        log_event("writing", "🧠 Querying Shared Memory via SuperBrain...", "system")
        
        # Robust retrieval with metrics
        start_recall = time.perf_counter()
        keys = shared_ctx.list_keys()
        mems = []
        for k in keys:
            raw = shared_ctx.read(k)
            if raw:
                try:
                    mems.append(json.loads(raw))
                except Exception as e:
                    print(f"[ERR] JSON load fail for {k}: {e}")
        
        recall_latency = (time.perf_counter() - start_recall) * 1_000_000
        demo_state["last_recall_latency"] = round(recall_latency, 2)
        
        log_event("writing", f"📋 Found {len(mems)} memory entries (Recall time: {round(recall_latency, 1)}μs).", "system")
        await asyncio.sleep(1.0)
        
        for m in mems:
            demo_state["events"].append({"type": "memory_read", "data": m, "latency": round(recall_latency, 2)})
            log_event("writing", f"📥 Recalled: '{m['content'][:35]}...'", "recall")
            await asyncio.sleep(1.2)
            
        log_event("writing", "✍️ Copywriter is drafting the blog post...", "agent")
        await asyncio.sleep(1.5)
        
        log_event("writing", "✨ Blog Draft: '13.5µs latency is the future...'", "output")
        log_event("writing", "✅ Phase 2 Complete. Persistent memory verified.", "system")
        demo_state["phase"] = "finished"
    except Exception as e:
        log_event("writing", f"🔥 Error: {str(e)}", "system")
        print(f"[CRITICAL] Phase 2 Fail: {e}")
    finally:
        demo_state["phase"] = "idle"

# =============================================================================
# 4. API & SOCKETS
# =============================================================================

@app.websocket("/ws/state")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            state_to_send = demo_state.copy()
            await websocket.send_json(state_to_send)
            demo_state["events"] = [] 
            await asyncio.sleep(0.15)
    except WebSocketDisconnect: manager.disconnect(websocket)

class RunPhaseRequest(BaseModel):
    knowledge: str = ""

@app.post("/api/run/{phase}")
async def trigger_run(phase: str, request: RunPhaseRequest = None):
    if phase == "research":
        knowledge = request.knowledge if request else ""
        if knowledge:
            save_to_memory(knowledge, {"source": "User Injection", "type": "knowledge"})
            log_event("research", f"📥 Injected: '{knowledge[:20]}...'", "system")
        asyncio.create_task(run_crew_1())
    elif phase == "writing":
        asyncio.create_task(run_crew_2())
    elif phase == "reset":
        for k in shared_ctx.list_keys(): shared_ctx.write(k, None)
        demo_state.update({"crew1_logs": [], "crew2_logs": [], "shared_memory": [], "phase": "idle"})
    return {"status": "ok"}

app.mount("/", StaticFiles(directory="dashboard", html=True), name="dashboard")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8085, log_level="info")
