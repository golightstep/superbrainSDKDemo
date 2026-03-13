#!/bin/bash

# Configuration
PYTHON_PATH="../../venv/bin/python"
MODE=$1

# Default to both for comparison
if [ -z "$MODE" ]; then
    MODE="both"
fi

echo "🚀 Breaking News AI Studio - Launching in DUAL MODE ($MODE)..."

# Cleanup old data
rm -f market_data*.json knowledge_sharing.log
rm -rf /tmp/superbrain_mock/*
rm -f conflict_active.flag

# Kill existing processes
pkill -9 -f "python.*(reporter|analyst|fact_checker|producer|anchor|dashboard_server).py"
sleep 1

# Start Dashboard
echo "📡 Starting Dual-Mode Studio Dashboard on http://localhost:5009"
$PYTHON_PATH dashboard_server.py > dashboard.log 2>&1 &
sleep 1

start_agents() {
    local m=$1
    echo "🎙️ Starting $m agents..."
    $PYTHON_PATH reporter.py $m > /dev/null 2>&1 &
    sleep 0.2
    $PYTHON_PATH analyst.py $m > /dev/null 2>&1 &
    sleep 0.2
    $PYTHON_PATH fact_checker.py $m > /dev/null 2>&1 &
    sleep 0.2
    $PYTHON_PATH producer.py $m > /dev/null 2>&1 &
    sleep 0.2
    $PYTHON_PATH anchor.py $m > /dev/null 2>&1 &
}

if [ "$MODE" == "both" ] || [ "$MODE" == "superbrain" ]; then
    start_agents "superbrain"
fi

if [ "$MODE" == "both" ] || [ "$MODE" == "traditional" ]; then
    start_agents "traditional"
fi

echo "✨ Studio is LIVE. Dashboard: http://localhost:5009"
echo "--------------------------------------------------"
ps aux | grep -v grep | grep -E "python.*(reporter|analyst|fact_checker|producer|anchor|dashboard_server).py"
echo "--------------------------------------------------"

echo "STUDIO COMMANDS:"
echo "  [c] Toggle Conflict Simulation"
echo "  [q] Quit Studio"

while true; do
    if [ -t 0 ]; then
        read -n 1 -p "> " cmd
        echo ""
        case $cmd in
            c)
                if [ -f "conflict_active.flag" ]; then
                    rm "conflict_active.flag"
                    echo "🕊️  Conflict OFF"
                else
                    touch "conflict_active.flag"
                    echo "🔥 Conflict ON"
                fi
                ;;
            q)
                pkill -9 -f "python.*(reporter|analyst|fact_checker|producer|anchor|dashboard_server).py"
                echo "Terminated."
                exit
                ;;
        esac
    else
        sleep 10
    fi
done
