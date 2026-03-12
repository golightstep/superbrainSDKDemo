#!/usr/bin/env bash
# =============================================================================
#  Redis + SuperBrain Symbiosis Demo — GCP Stop
# =============================================================================
set -euo pipefail

GCLOUD="$(which gcloud 2>/dev/null || echo /opt/homebrew/share/google-cloud-sdk/bin/gcloud)"

echo ""
echo "  🛑 Stopping Redis+SuperBrain Demo..."

"$GCLOUD" compute ssh sb-bench-1 --zone=us-central1-a --command='bash -s' << 'EOF'
pkill -f "dashboard_server|feed_publisher" 2>/dev/null; echo done
EOF

"$GCLOUD" compute ssh sb-bench-2 --zone=us-east1-b --command='bash -s' << 'EOF'
pkill -f "trading_engine" 2>/dev/null; echo done
EOF

"$GCLOUD" compute ssh sb-bench-3 --zone=us-west1-a --command='bash -s' << 'EOF'
pkill -f "trading_engine" 2>/dev/null; echo done
EOF

echo "  Stopping VMs..."
"$GCLOUD" compute instances stop sb-bench-1 --zone=us-central1-a --quiet &
"$GCLOUD" compute instances stop sb-bench-2 --zone=us-east1-b --quiet &
"$GCLOUD" compute instances stop sb-bench-3 --zone=us-west1-a --quiet &
wait

echo "  ✅ All stopped."
