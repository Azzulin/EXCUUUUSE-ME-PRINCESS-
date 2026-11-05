#!/bin/bash
# Runs on the Steam Deck (copied to ~/aoc-run.sh): starts the game on the Deck's own screen for N seconds with a
# scripted input, saves a screenshot of the game image and keeps the log as logs/run.log.
# Usage: bash ~/aoc-run.sh <seconds> [input script] [extra env assignments...]
G=${AOC_DECK_DIR:-/run/media/deck/e3e0373c-4153-46c2-a60c-c5f97dd60eee/Games/aoc-deck}   # the folder on the Deck
S=${1:-60}; IN=${2:-}
shift 2 2>/dev/null
cd "$G" || exit 1
pkill -9 -x aoc 2>/dev/null; sleep 1
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DISPLAY=:0
export MESA_SHADER_CACHE_DIR="$G/mesa-cache"
[ -n "$IN" ] && export AOC_INPUT_SCRIPT="$IN"
rm -f shot.png
env "$@" ./aoc --seconds "$S" --shot "$G/shot.png" > logs/run.log 2>&1
echo "exit $?"
