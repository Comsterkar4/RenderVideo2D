#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

OLLAMA_VERSION="${OLLAMA_VERSION:-v0.40.4}"
ARCHIVE="$PROJECT_ROOT/downloads/ollama-linux-amd64-$OLLAMA_VERSION.tar.zst"
INSTALL_DIR="$PROJECT_ROOT/tools/ollama-$OLLAMA_VERSION"
CURRENT_LINK="$PROJECT_ROOT/tools/ollama-current"
URL="https://github.com/ollama/ollama/releases/download/$OLLAMA_VERSION/ollama-linux-amd64.tar.zst"

if [[ ! -f "$ARCHIVE" ]]; then
    echo "Downloading Ollama $OLLAMA_VERSION to $ARCHIVE"
    curl --fail --location --retry 3 --continue-at - \
        --output "$ARCHIVE.part" \
        "$URL"
    mv "$ARCHIVE.part" "$ARCHIVE"
fi

if [[ ! -x "$INSTALL_DIR/bin/ollama" ]]; then
    echo "Extracting Ollama to $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    tar --use-compress-program=unzstd -xf "$ARCHIVE" -C "$INSTALL_DIR"
fi

ln -sfn "$INSTALL_DIR" "$CURRENT_LINK"
"$CURRENT_LINK/bin/ollama" --version

echo "Ollama installed locally: $CURRENT_LINK"
