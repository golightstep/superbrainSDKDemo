#!/usr/bin/env python3
import time
import random
import json
import argparse
import redis
import sys

# Attempt to load SuperBrain SDK, fallback to simulation mimic if unavailable
try:
    from superbrain import DistributedContextFabric
    print("✅ SuperBrain SDK loaded natively.")
except ImportError:
    from _sim_shared import MockFabric as DistributedContextFabric
    print("⚠️ SuperBrain SDK not found. Using local in-memory simulation for demo.")

def main():
    parser = argparse.ArgumentParser(description="Symbiosis Demo: Market Data Feed (SuperBrain Writer)")
    parser.add_argument("--tps", type=int, default=200, help="Target ticks per second")
    parser.add_argument("--symbol", type=str, default="SYM", help="Ticker symbol")
    parser.add_argument("--redis-host", type=str, default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    args = parser.parse_args()

    # 1. Initialize SuperBrain Fabric (The High-Speed Data Layer)
    fabric = DistributedContextFabric()
    shm_pool = fabric.create_context("live_market_data", size_mb=100)
    print(f"🧠 SuperBrain context 'live_market_data' created/attached.")

    # 2. Initialize Redis (The Coordination Layer)
    try:
        r = redis.Redis(host=args.redis_host, port=args.redis_port, decode_responses=True)
        r.ping()
        print(f"📦 Redis connected at {args.redis_host}:{args.redis_port}")
    except redis.ConnectionError:
        print(f"❌ Could not connect to Redis at {args.redis_host}:{args.redis_port}. Ensure Redis is running.")
        sys.exit(1)

    print(f"🚀 Starting market feed for {args.symbol} at {args.tps} TPS...")
    
    price = 100.0
    seq = 0
    sleep_interval = 1.0 / args.tps

    try:
        while True:
            start_ts = time.perf_counter()
            seq += 1
            
            # Random walk price update
            change = random.uniform(-0.05, 0.05)
            price += change
            
            # Tick data structure
            tick_data = {
                "symbol": args.symbol,
                "price": round(price, 4),
                "timestamp": time.time(),
                "seq": seq
            }

            # =====================================================================
            # ⚡ SUPERBRAIN: Write the heavy tick payload ONCE to Shared Memory
            # =====================================================================
            # NOTE: The REAL SDK is zero-copy (microsecond latency). 
            # If using the Redis-based mock, this will involve network round-trips.
            shm_pool.write(args.symbol, tick_data)

            # =====================================================================
            # 📦 REDIS: Publish significant alerts via Pub/Sub (Coordination)
            # =====================================================================
            # If the price jumps significantly, we use Redis to coordinate a global alert.
            # We don't use Redis for every tick, only for stateful events/alerts.
            if abs(change) > 0.045:
                # Big move! Publish to Redis
                alert = {"symbol": args.symbol, "price": round(price, 4), "event": "VOLATILITY_ALERT"}
                r.publish("market_alerts", json.dumps(alert))
                if seq % 10 == 0:
                    print(f"[Redis] Published Volatility Alert: {round(price, 4)}")

            if seq % (args.tps * 2) == 0:
                print(f"[SuperBrain] Wrote {seq} ticks for {args.symbol}. Current price: ${price:.4f}")

            # Pace the loop
            elapsed = time.perf_counter() - start_ts
            if elapsed < sleep_interval:
                time.sleep(sleep_interval - elapsed)
                
    except KeyboardInterrupt:
        print("\nStopping feed publisher.")

if __name__ == "__main__":
    main()
