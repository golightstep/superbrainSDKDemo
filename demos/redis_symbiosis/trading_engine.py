#!/usr/bin/env python3
import time
import random
import json
import argparse
import redis
import asyncio
import sys

# Attempt to load SuperBrain SDK, fallback to simulation mimic if unavailable
try:
    from superbrain import DistributedContextFabric
    print("✅ SuperBrain SDK loaded natively.")
except ImportError:
    from _sim_shared import MockFabric as DistributedContextFabric
    print("⚠️ SuperBrain SDK not found. Using local in-memory simulation for demo.")

# Global metrics for the dashboard to read
metrics = {
    "total_reads": 0,
    "last_read_latencies": [],
    "total_orders": 0,
    "rate_limits_hit": 0,
    "active_strategies": 0,
    "last_price": 0.0,
    "last_seq": 0
}

async def run_strategy(strategy_id, symbol, r, shm_pool, poll_interval=0.01):
    """
    A single trading strategy running in the engine.
    Demonstrates SUPERBRAIN for high-speed reads, REDIS for coordination.
    """
    metrics["active_strategies"] += 1
    orders_placed = 0
    
    while True:
        # =====================================================================
        # ⚡ SUPERBRAIN: Microsecond Reads
        # =====================================================================
        # Read the latest tick directly from shared memory. Zero copies.
        # This takes ~15µs, allowing all 50 strategies to read 1000x a second.
        read_start = time.perf_counter()
        tick = shm_pool.read(symbol)
        latency_us = (time.perf_counter() - read_start) * 1_000_000
        
        if tick:
            metrics["total_reads"] += 1
            metrics["last_price"] = tick["price"]
            metrics["last_seq"] = tick["seq"]
            
            # Keep a rolling window of latencies (max 100 per strategy)
            metrics["last_read_latencies"].append(latency_us)
            if len(metrics["last_read_latencies"]) > 5000:
                metrics["last_read_latencies"] = metrics["last_read_latencies"][-5000:]
                
            # Random logic: occasionally decide to "Buy"
            # In a real app, this is MA crosses, ML inference, etc.
            if random.random() < 0.005:  # 0.5% chance per loop to want to trade
                
                # =====================================================================
                # 📦 REDIS: Coordination (Locks, Queues, Rate Limits)
                # =====================================================================
                # We want to place an order, but we must respect global rate limits.
                # Redis handles this perfectly.
                
                # Check rate limit (max 10 orders per second globally across all strategies)
                current_second = int(time.time())
                rl_key = f"rate_limit:orders:{current_second}"
                
                # Increment the counter
                current_count = r.incr(rl_key)
                if current_count == 1:
                    r.expire(rl_key, 2) # Clean up keys
                    
                if current_count <= 10:
                    # Rate limit OK. Submit order to the execution queue.
                    order = {
                        "strategy": strategy_id,
                        "action": "BUY",
                        "symbol": symbol,
                        "price": tick["price"],
                        "ts": time.time()
                    }
                    r.rpush("order_queue", json.dumps(order))
                    orders_placed += 1
                    metrics["total_orders"] += 1
                else:
                    # Rate limit hit! Redis prevented us from flooding the exchange.
                    metrics["rate_limits_hit"] += 1

        await asyncio.sleep(poll_interval)


async def reporter():
    """Prints occasional status to the console"""
    while True:
        await asyncio.sleep(2)
        avg_lat = 0
        if metrics["last_read_latencies"]:
            avg_lat = sum(metrics["last_read_latencies"]) / len(metrics["last_read_latencies"])
            
        print(f"[Engine] {metrics['active_strategies']} strats running | "
              f"Price: ${metrics['last_price']:.2f} | "
              f"Avg SHM Read: {avg_lat:.1f}µs | "
              f"Orders: {metrics['total_orders']} | "
              f"RL Hits: {metrics['rate_limits_hit']}")

async def main_async(args):
    # 1. Connect to SuperBrain (Data Plane)
    fabric = DistributedContextFabric()
    shm_pool = fabric.attach_context("live_market_data")
    print("🧠 Connected to SuperBrain shared memory fabric.")
    
    # 2. Connect to Redis (Control Plane)
    try:
        r = redis.Redis(host=args.redis_host, port=args.redis_port, decode_responses=True)
        r.ping()
        print(f"📦 Connected to Redis at {args.redis_host}:{args.redis_port}.")
    except redis.ConnectionError:
        print(f"❌ Could not connect to Redis at {args.redis_host}:{args.redis_port}.")
        sys.exit(1)
        
    print(f"🚀 Spawning {args.strategies} independent trading strategies...")
    
    # Optional: flush old redis queue for the demo
    r.delete("order_queue")
    
    tasks = []
    # Start the strategies
    for i in range(args.strategies):
        strat_id = f"Strat-{i+1}"
        # Start immediately
        task = asyncio.create_task(run_strategy(strat_id, args.symbol, r, shm_pool, poll_interval=0.01))
        tasks.append(task)
        
    # Start reporter
    tasks.append(asyncio.create_task(reporter()))
    
    # Run forever
    await asyncio.gather(*tasks)

def main():
    parser = argparse.ArgumentParser(description="Symbiosis Demo: Strategy Engine (SuperBrain Reader + Redis Writer)")
    parser.add_argument("--strategies", type=int, default=50, help="Number of concurrent strategies to spawn")
    parser.add_argument("--symbol", type=str, default="SYM", help="Ticker symbol to watch")
    parser.add_argument("--redis-host", type=str, default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    args = parser.parse_args()
    
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nStopping trading engine.")

if __name__ == "__main__":
    main()
