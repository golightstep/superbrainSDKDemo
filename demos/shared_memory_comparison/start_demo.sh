#!/bin/bash

# Configuration
PYTHON_PATH="../../venv/bin/python"
MODE=$1

if [ -z "$MODE" ]; then
    MODE="both"
fi

echo "🚀 Launching Core Multi-Agent Simulation (No Audio) in $MODE mode..."

# Cleanup old data
rm -f market_data.json market_data_metrics.json market_data_report.json knowledge_sharing.log
rm -f /tmp/superbrain_mock_fabric.json

# Kill existing processes
pkill -f "python.*scraper.py"
pkill -f "python.*analyst.py"
pkill -f "python.*anchor.py"
pkill -f "python.*dashboard_server.py"
sleep 1

# Start Dashboard
$PYTHON_PATH dashboard_server.py > dashboard.log 2>&1 &
sleep 1

if [ "$MODE" == "superbrain" ] || [ "$MODE" == "both" ]; then
    $PYTHON_PATH scraper.py superbrain > /dev/null 2>&1 &
    sleep 0.5
    $PYTHON_PATH analyst.py superbrain > /dev/null 2>&1 &
    sleep 0.5
fi

if [ "$MODE" == "traditional" ] || [ "$MODE" == "both" ]; then
    $PYTHON_PATH scraper.py traditional > /dev/null 2>&1 &
    sleep 0.5
    $PYTHON_PATH analyst.py traditional > /dev/null 2>&1 &
    sleep 0.5
fi

# Optional: Start ONE anchor to see if it survives
$PYTHON_PATH anchor.py superbrain > /dev/null 2>&1 &

echo "Core components started. Dashboard: http://localhost:5001"
ps aux | grep -v grep | grep -E "python.*(scraper|analyst|anchor|dashboard_server)"
