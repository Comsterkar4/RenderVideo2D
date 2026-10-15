#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
fi

export XDG_CACHE_HOME="$PROJECT_ROOT/.cache"
export PIP_CACHE_DIR="$PROJECT_ROOT/.cache/pip"
export UV_CACHE_DIR="$PROJECT_ROOT/.cache/uv"
export UV_PROJECT_ENVIRONMENT="$PROJECT_ROOT/.venv"
export HF_HOME="$PROJECT_ROOT/models/huggingface"
export HUGGINGFACE_HUB_CACHE="$PROJECT_ROOT/models/huggingface/hub"
export TORCH_HOME="$PROJECT_ROOT/models/torch"
export OLLAMA_MODELS="$PROJECT_ROOT/models/ollama"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export OLLAMA_STORY_MODEL="${OLLAMA_STORY_MODEL:-qwen2.5:3b}"
export COMFYUI_BASE_URL="${COMFYUI_BASE_URL:-http://127.0.0.1:8188}"
export COMFYUI_VERSION="${COMFYUI_VERSION:-v0.40.0}"
export COMFYUI_DIR="$PROJECT_ROOT/third_party/ComfyUI-$COMFYUI_VERSION"
export COMFYUI_VENV="$PROJECT_ROOT/.venv-comfyui"
export COMFYUI_MODEL_ROOT="$PROJECT_ROOT/models/comfyui"
export COMFYUI_CHECKPOINT="${COMFYUI_CHECKPOINT:-v1-5-pruned-emaonly-fp16.safetensors}"
export TMPDIR="$PROJECT_ROOT/.runtime/tmp"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$PROJECT_ROOT/data/render_video.db}"

mkdir -p \
    "$PIP_CACHE_DIR" \
    "$UV_CACHE_DIR" \
    "$HUGGINGFACE_HUB_CACHE" \
    "$TORCH_HOME" \
    "$OLLAMA_MODELS" \
    "$TMPDIR" \
    "$PROJECT_ROOT/.runtime/logs" \
    "$PROJECT_ROOT/data/projects" \
    "$PROJECT_ROOT/downloads" \
    "$PROJECT_ROOT/models/comfyui" \
    "$PROJECT_ROOT/models/comfyui/checkpoints" \
    "$PROJECT_ROOT/.runtime/comfyui" \
    "$PROJECT_ROOT/third_party" \
    "$PROJECT_ROOT/tools" \
    "$PROJECT_ROOT/workflows"
