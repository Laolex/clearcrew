#!/usr/bin/env bash
# Repeat the n=36 benchmark N times on the CURRENT architecture, so the headline
# number comes with a spread instead of a single lucky run.
#
#   scripts/bench_repeat.sh 10
#
# Every run is archived to runs/ — including the ones we lose. Reads
# DASHSCOPE_API_KEY from .env. Anchors each run's head hash to a real TSA.
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

N="${1:-10}"
cd src
for i in $(seq 1 "$N"); do
  echo "=== run $i/$N · $(date -u +%H:%M:%SZ) ==="
  BATCH_N=36 CLEARCREW_ANCHOR=tsa ../.venv/bin/python -m clearcrew.bench 2>&1 \
    | grep -E "^(society|monolith)|run archived" || echo "run $i FAILED"
done
echo "=== done · $(date -u +%H:%M:%SZ) ==="
