#!/usr/bin/env bash

set -euo pipefail

echo "══════════════════════════════════════════════════════"
echo " proctrace CLI usage examples"
echo "══════════════════════════════════════════════════════"
echo


# ── 1. proctrace run — measure a subprocess ─────────────────────

echo "[ 1 ] proctrace run — human-readable output"
echo "      Command: python -c \"import time; time.sleep(0.1)\""
echo

proctrace run -- python -c "import time; time.sleep(0.1)"

echo
echo "─────────────────────────────────────────────────────"
echo

echo "[ 2 ] proctrace run --json — structured JSON output"
echo "      Command: python -c \"x = list(range(1_000_000))\""
echo

proctrace run --json -- python -c "x = list(range(1_000_000))"

echo
echo "─────────────────────────────────────────────────────"
echo


# ── 2. proctrace watch — live memory polling ────────────────────
#
# Start a background process to watch, then poll it for 5 seconds.

echo "[ 3 ] proctrace watch — live memory polling (5 s)"
echo

# Launch a target process in the background
python -c "
import time, os
print(os.getpid(), flush=True)
time.sleep(10)
" &
TARGET_PID=$!

# Give it a moment to print its PID
sleep 0.2

echo "      Watching pid=${TARGET_PID} for 5 seconds…"
proctrace watch --pid "${TARGET_PID}" --interval 0.5 --duration 5 || true

kill "${TARGET_PID}" 2>/dev/null || true
wait "${TARGET_PID}" 2>/dev/null || true

echo
echo "─────────────────────────────────────────────────────"
echo


# ── 3. proctrace dump — trigger a stack dump ────────────────────
#
# Start a process that has install_signal_handler(), send SIGUSR1.

echo "[ 4 ] proctrace dump — trigger a thread dump"
echo

python - <<'PYEOF' &
import proctrace, time, os, sys
proctrace.install_signal_handler(sig="SIGUSR1")
print(os.getpid(), flush=True)
time.sleep(5)
PYEOF
DUMP_PID=$!

sleep 0.3

echo "      Sending SIGUSR1 to pid=${DUMP_PID} …"
proctrace dump --pid "${DUMP_PID}" --signal SIGUSR1

# Give the daemon thread a moment to write the dump, then clean up
sleep 0.5
kill "${DUMP_PID}" 2>/dev/null || true
wait "${DUMP_PID}" 2>/dev/null || true

echo
echo "══════════════════════════════════════════════════════"
echo " Done."
echo "══════════════════════════════════════════════════════"
