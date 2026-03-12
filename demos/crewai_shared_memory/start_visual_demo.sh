#!/bin/bash

# SuperBrain + CrewAI Visual Demo Launcher
# This script starts the dashboard server for the multi-agent shared memory demo.

DEMO_DIR="demos/crewai_shared_memory"
PORT=8082

echo "----------------------------------------------------"
echo "🚀 Starting CrewAI + SuperBrain Visual Demo..."
echo "----------------------------------------------------"

# Check if dashboard server exists
if [ ! -f "$DEMO_DIR/dashboard_server.py" ]; then
    echo "❌ Error: dashboard_server.py not found in $DEMO_DIR"
    exit 1
fi

# Kill any existing server on this port
pkill -f "uvicorn.*8082" 2>/dev/null

# Start the server in the background
cd "$DEMO_DIR"
python3 dashboard_server.py > /tmp/crewai_dashboard.log 2>&1 &

# Wait for server to start
sleep 3

echo "✅ Dashboard is live at: http://localhost:$PORT"
echo "Check /tmp/crewai_dashboard.log for server logs."
echo "----------------------------------------------------"
