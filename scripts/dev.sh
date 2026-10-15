#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

cd "$PROJECT_ROOT"
exec uv run --frozen uvicorn backend.main:app \
    --host "${BACKEND_HOST:-127.0.0.1}" \
    --port "${BACKEND_PORT:-9000}" \
    --reload
