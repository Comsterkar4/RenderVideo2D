#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

OLLAMA_BIN="$PROJECT_ROOT/tools/ollama-current/bin/ollama"
if [[ ! -x "$OLLAMA_BIN" ]]; then
    echo "Ollama is not installed. Run ./scripts/setup_ollama.sh first." >&2
    exit 1
fi

export HOME="$PROJECT_ROOT/.runtime/ollama-home"
mkdir -p "$HOME"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
exec "$OLLAMA_BIN" serve
