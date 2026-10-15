#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM
    kill "${API_PID:-}" "${UI_PID:-}" 2>/dev/null || true
    wait "${API_PID:-}" "${UI_PID:-}" 2>/dev/null || true
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

"$SCRIPT_DIR/dev.sh" &
API_PID=$!
"$SCRIPT_DIR/dev_frontend.sh" &
UI_PID=$!

wait -n "$API_PID" "$UI_PID"
