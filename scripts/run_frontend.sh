#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

cd "$PROJECT_ROOT"
exec uv run --frozen uvicorn frontend.app:app \
    --host "${FRONTEND_HOST:-127.0.0.1}" \
    --port "${FRONTEND_PORT:-9001}"
