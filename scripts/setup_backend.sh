#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required but was not found." >&2
    exit 1
fi

cd "$PROJECT_ROOT"
uv sync --frozen
uv run --frozen alembic upgrade head

echo "Backend environment ready: $PROJECT_ROOT/.venv"
echo "Database ready: $DATABASE_URL"
