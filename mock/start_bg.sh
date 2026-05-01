#!/bin/bash
# Usage: mock/start_bg.sh <server_code> <mc_port> <ctrl_port>

SERVER_CODE=$1
MC_PORT=$2
CTRL_PORT=$3
PID_FILE="/tmp/mock_${SERVER_CODE}.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "[mock] $SERVER_CODE is already running (PID=$(cat "$PID_FILE"))"
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MC_PORT="$MC_PORT" CTRL_PORT="$CTRL_PORT" \
    python "$SCRIPT_DIR/server.py" &

echo $! > "$PID_FILE"
echo "[mock] $SERVER_CODE started (PID=$(cat "$PID_FILE"), mc=:$MC_PORT, ctrl=:$CTRL_PORT)"
