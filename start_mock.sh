#!/bin/bash
# Verification environment: start mock Minecraft server + API together.
# Mock control API: http://localhost:8080
#   GET  /state              -> current state
#   POST /state {"state":"running"|"stopped"|"starting"|"unknown"}
#   GET  /config             -> current player data
#   POST /config {"online":5,"max":20,"motd":"..."}

# Start mock Minecraft server in background (run Python directly to get its PID)
MC_PORT="${MC_PORT:-25565}" \
CTRL_PORT="${CTRL_PORT:-8080}" \
MOCK_PLAYERS_ONLINE="${MOCK_PLAYERS_ONLINE:-3}" \
MOCK_PLAYERS_MAX="${MOCK_PLAYERS_MAX:-20}" \
MOCK_MOTD="${MOCK_MOTD:-Mock Minecraft Server}" \
python "$(dirname "$0")/mock/server.py" &
MOCK_PID=$!
echo "[mock] PID=$MOCK_PID (mc=:25565, ctrl=:8080)"
sleep 0.5

# API pointing at the mock
export HOST="localhost"
export PORT="25565"
export FRONTEND_ORIGIN="http://localhost:5173"
export WOL_TARGET_MAC_ADDRESS="00:00:00:00:00:00"
export WOL_FROM_IP_ADDRESS="127.0.0.1"
export API_USERNAME="admin"
export API_PASSWORD="CHANGE_ME"
export MOCK_CTRL_URL="http://localhost:8080"

trap "kill $MOCK_PID 2>/dev/null; wait $MOCK_PID 2>/dev/null" EXIT INT TERM

uvicorn app.index:app --host 0.0.0.0 --port 8000 --reload
