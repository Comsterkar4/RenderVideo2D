#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

HOST="${BACKEND_HOST:-127.0.0.1}"
PORT="${BACKEND_PORT:-9000}"

exec "$PROJECT_ROOT/.venv/bin/uvicorn" backend.main:app \
    --app-dir "$PROJECT_ROOT" \
    --host "$HOST" \
    --port "$PORT"
