#!/bin/bash
# Usage: mock/stop_bg.sh <server_code>

SERVER_CODE=$1
PID_FILE="/tmp/mock_${SERVER_CODE}.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "[mock] $SERVER_CODE is not running"
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill "$PID" 2>/dev/null; then
    echo "[mock] $SERVER_CODE stopped (PID=$PID)"
else
    echo "[mock] $SERVER_CODE process not found (PID=$PID)"
fi
rm -f "$PID_FILE"
