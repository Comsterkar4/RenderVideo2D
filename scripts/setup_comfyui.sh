#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required but was not found." >&2
    exit 1
fi

ARCHIVE="$PROJECT_ROOT/downloads/comfyui-${COMFYUI_VERSION}.tar.gz"
SOURCE_URL="https://api.github.com/repos/Comfy-Org/ComfyUI/tarball/${COMFYUI_VERSION}"
INSTALL_MARKER="$COMFYUI_VENV/.render-video-${COMFYUI_VERSION}-cu130"
CHECKPOINT_PATH="$COMFYUI_MODEL_ROOT/checkpoints/$COMFYUI_CHECKPOINT"
CHECKPOINT_URL="https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/resolve/main/$COMFYUI_CHECKPOINT"
CHECKPOINT_SHA256="e9476a13728cd75d8279f6ec8bad753a66a1957ca375a1464dc63b37db6e3916"

if [[ ! -f "$COMFYUI_DIR/main.py" ]]; then
    mkdir -p "$COMFYUI_DIR"
    curl --fail --location --retry 3 --output "$ARCHIVE" "$SOURCE_URL"
    tar -xzf "$ARCHIVE" --strip-components=1 -C "$COMFYUI_DIR"
fi

if [[ ! -f "$INSTALL_MARKER" ]]; then
    rm -rf "$COMFYUI_VENV"
    uv venv --python 3.12 "$COMFYUI_VENV"
    uv pip install \
        --python "$COMFYUI_VENV/bin/python" \
        torch torchvision torchaudio \
        --extra-index-url https://download.pytorch.org/whl/cu130
    uv pip install \
        --python "$COMFYUI_VENV/bin/python" \
        --requirement "$COMFYUI_DIR/requirements.txt"
    touch "$INSTALL_MARKER"
fi

mkdir -p "$(dirname "$CHECKPOINT_PATH")"
if [[ ! -f "$CHECKPOINT_PATH" ]]; then
    PARTIAL_PATH="$CHECKPOINT_PATH.part"
    curl --fail --location --retry 3 --continue-at - --output "$PARTIAL_PATH" "$CHECKPOINT_URL"
    printf '%s  %s\n' "$CHECKPOINT_SHA256" "$PARTIAL_PATH" | sha256sum --check --status
    mv "$PARTIAL_PATH" "$CHECKPOINT_PATH"
fi

printf '%s  %s\n' "$CHECKPOINT_SHA256" "$CHECKPOINT_PATH" | sha256sum --check --status

echo "ComfyUI ready: $COMFYUI_DIR"
echo "Checkpoint ready: $CHECKPOINT_PATH"
