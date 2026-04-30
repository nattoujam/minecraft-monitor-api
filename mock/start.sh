#!/bin/bash

export MC_PORT="${MC_PORT:-25565}"
export CTRL_PORT="${CTRL_PORT:-8080}"
export INITIAL_STATE="${INITIAL_STATE:-running}"

export MOCK_PLAYERS_ONLINE="${MOCK_PLAYERS_ONLINE:-3}"
export MOCK_PLAYERS_MAX="${MOCK_PLAYERS_MAX:-20}"
export MOCK_MOTD="${MOCK_MOTD:-Mock Minecraft Server}"

python "$(dirname "$0")/server.py"
