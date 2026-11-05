#!/bin/bash
# Repeats a short null-graphics run (WSL or Linux) with the first-boot A presses and reports the runs that stop
# presenting: a reproduction of the intermittent hang seen on the Deck around frames 550-610 (16-20 s, at the
# settings screens). A stuck run is left alive for gdb (its pid is printed) unless KILL=1.
# Usage: bash hang_repro.sh [runs] [seconds]
R="$(cd "$(dirname "$0")/../.." && pwd)"
EXE=${EXE:-$HOME/aoc-build/host/aoc}
RUNS=${1:-8}; SECS=${2:-35}
IN="$R/tools/deck/input-firstboot.txt"
for i in $(seq 1 "$RUNS"); do
  pkill -9 -x aoc; sleep 1
  log=/tmp/hang-$i.log
  (AOC_GPU=null AOC_TRACE=perf AOC_INPUT_SCRIPT="$IN" nohup "$EXE" > "$log" 2>&1 &)
  sleep "$SECS"
  last=$(grep -o "fps: 120 frames" "$log" | wc -l)
  frames=$((last * 120))
  if [ "$frames" -lt $(( (SECS - 6) * 30 - 240 )) ]; then
    echo "run $i: STUCK after ~$frames frames (pid $(pgrep -x aoc)) log $log"
    [ "${KILL:-0}" = 1 ] || exit 0
  else
    echo "run $i: ok (~$frames frames)"
  fi
done
pkill -9 -x aoc
