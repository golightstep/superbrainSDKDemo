#!/usr/bin/env bash
# =============================================================================
#  Redis + SuperBrain Symbiosis Demo — GCP Launcher
#  Usage: ./start_redis_demo.sh
# =============================================================================
set -euo pipefail

GCLOUD="$(which gcloud 2>/dev/null || echo /opt/homebrew/share/google-cloud-sdk/bin/gcloud)"
export CLOUDSDK_PYTHON="$(which python3)"

NODE1=sb-bench-1; ZONE1=us-central1-a
NODE2=sb-bench-2; ZONE2=us-east1-b
NODE3=sb-bench-3; ZONE3=us-west1-a

PORT=8081 # Using 8081 for this demo
DEMO_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_ip()  { "$GCLOUD" compute instances describe "$1" --zone="$2" --format='get(networkInterfaces[0].accessConfigs[0].natIP)'; }
_ssh() { "$GCLOUD" compute ssh "$1" --zone="$2" --command='bash -s'; }

echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║   SuperBrain + Redis Symbiosis Demo (GCP Mode)       ║"
echo "  ╚══════════════════════════════════════════════════════╝"

# 1. Start VMs
echo "  [1/6] Starting GCP instances..."
"$GCLOUD" compute instances start $NODE1 --zone=$ZONE1 --quiet &
"$GCLOUD" compute instances start $NODE2 --zone=$ZONE2 --quiet &
"$GCLOUD" compute instances start $NODE3 --zone=$ZONE3 --quiet &
wait
echo "  ✅ VMs running"

# 2. Fetch IPs
echo "  [2/6] Fetching IPs..."
IP1=$(_ip $NODE1 $ZONE1)
IP2=$(_ip $NODE2 $ZONE2)
IP3=$(_ip $NODE3 $ZONE3)
echo "        Iowa        $NODE1  →  $IP1"
echo "        S.Carolina  $NODE2  →  $IP2"
echo "        Oregon      $NODE3  →  $IP3"

"$GCLOUD" compute firewall-rules describe allow-symbiosis-demo &>/dev/null || \
  "$GCLOUD" compute firewall-rules create allow-symbiosis-demo --allow tcp:${PORT},tcp:6379 --source-ranges 0.0.0.0/0 --quiet

# 3. Code Sync
echo "  [3/6] Syncing demo code..."
_ssh $NODE1 $ZONE1 << 'EOF' &
mkdir -p ~/redis_demo/dashboard
EOF
_ssh $NODE2 $ZONE2 << 'EOF' &
mkdir -p ~/redis_demo/dashboard
EOF
_ssh $NODE3 $ZONE3 << 'EOF' &
mkdir -p ~/redis_demo/dashboard
EOF
wait

"$GCLOUD" compute scp --recurse --zone=$ZONE1 "$DEMO_SRC/." ${NODE1}:~/redis_demo &
"$GCLOUD" compute scp --recurse --zone=$ZONE2 "$DEMO_SRC/." ${NODE2}:~/redis_demo &
"$GCLOUD" compute scp --recurse --zone=$ZONE3 "$DEMO_SRC/." ${NODE3}:~/redis_demo &
wait
echo "  ✅ Code synced"

# 4. Install standard Python deps + Redis server (Iowa only)
echo "  [4/6] Installing dependencies..."
_ssh $NODE1 $ZONE1 << 'EOF' &
sudo apt-get update -qq && sudo apt-get install -y -qq redis-server
sudo systemctl enable redis-server && sudo systemctl restart redis-server
# Configure Redis to bind to all interfaces (for demo only)
sudo sed -i 's/^bind 127.0.0.1 ::1/bind 0.0.0.0/' /etc/redis/redis.conf || true
sudo sed -i 's/^bind 127.0.0.1 -::1/bind 0.0.0.0/' /etc/redis/redis.conf || true
sudo sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf || true
sudo systemctl restart redis-server

[ -d ~/sb_demo_env ] || python3 -m venv ~/sb_demo_env
source ~/sb_demo_env/bin/activate
pip install -q fastapi uvicorn websockets redis
EOF

_ssh $NODE2 $ZONE2 << 'EOF' &
[ -d ~/sb_demo_env ] || python3 -m venv ~/sb_demo_env
source ~/sb_demo_env/bin/activate
pip install -q fastapi uvicorn websockets redis
EOF

_ssh $NODE3 $ZONE3 << 'EOF' &
[ -d ~/sb_demo_env ] || python3 -m venv ~/sb_demo_env
source ~/sb_demo_env/bin/activate
pip install -q fastapi uvicorn websockets redis
EOF
wait
echo "  ✅ Dependencies and Redis cluster ready"

# 5. Launch services
echo "  [5/6] Launching services..."

# Iowa: Feed Publisher + Dashboard
_ssh $NODE1 $ZONE1 << ENDSSH
pkill -f 'dashboard_server|feed_publisher' 2>/dev/null || true
sleep 0.3
source ~/sb_demo_env/bin/activate
cd ~/redis_demo
nohup python3 feed_publisher.py --tps 200 --redis-host 127.0.0.1 > /tmp/feed.log 2>&1 &
sleep 0.5
export DASHBOARD_NODE1_IP=$IP1 DASHBOARD_NODE2_IP=$IP2 DASHBOARD_NODE3_IP=$IP3
export DASHBOARD_NODE1_REGION="Iowa (Feed + Redis + UI)"
export DASHBOARD_NODE2_REGION="S.Carolina (25 Strats)"
export DASHBOARD_NODE3_REGION="Oregon (25 Strats)"
nohup python3 dashboard_server.py --port $PORT --redis-host 127.0.0.1 > /tmp/dashboard.log 2>&1 &
echo iowa_ok
ENDSSH

# S.Carolina: 25 Strategies (Trading Engine)
_ssh $NODE2 $ZONE2 << ENDSSH
pkill -f 'trading_engine' 2>/dev/null || true
sleep 0.3
source ~/sb_demo_env/bin/activate
cd ~/redis_demo
export REDIS_HOST=$IP1
nohup python3 trading_engine.py --strategies 25 --redis-host $IP1 > /tmp/engine.log 2>&1 &
echo sc_ok
ENDSSH

# Oregon: 25 Strategies (Trading Engine)
_ssh $NODE3 $ZONE3 << ENDSSH
pkill -f 'trading_engine' 2>/dev/null || true
sleep 0.3
source ~/sb_demo_env/bin/activate
cd ~/redis_demo
export REDIS_HOST=$IP1
nohup python3 trading_engine.py --strategies 25 --redis-host $IP1 > /tmp/engine.log 2>&1 &
echo or_ok
ENDSSH

# ── Done ─────────────────────────────────────────────────────────────────────
sleep 2
echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║        🚀  REDIS + SUPERBRAIN DEMO IS LIVE 🚀        ║"
echo "  ╠══════════════════════════════════════════════════════╣"
echo "  ║                                                      ║"
printf   "  ║   📊 Dashboard →  http://%-28s║\n" "${IP1}:${PORT} "
echo "  ║                                                      ║"
echo "  ║   Iowa        $NODE1   $IP1   (Redis + UI)"
echo "  ║   S.Carolina  $NODE2   $IP2   (50% workload)"
echo "  ║   Oregon      $NODE3   $IP3   (50% workload)"
echo "  ║                                                      ║"
echo "  ║   To stop:  ./stop_redis_demo.sh                     ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""
