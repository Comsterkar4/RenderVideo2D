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
if ! curl --fail --silent "$OLLAMA_BASE_URL/api/tags" >/dev/null; then
    echo "Ollama is not running. Start it with: ./scripts/run_ollama.sh" >&2
    exit 1
fi

"$OLLAMA_BIN" pull "$OLLAMA_STORY_MODEL"
