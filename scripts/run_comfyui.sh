#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

COMFYUI_PYTHON="$COMFYUI_VENV/bin/python"
CHECKPOINT_PATH="$COMFYUI_MODEL_ROOT/checkpoints/$COMFYUI_CHECKPOINT"
MODEL_PATHS_CONFIG="$PROJECT_ROOT/.runtime/comfyui-model-paths.yaml"
RUNTIME_ROOT="$PROJECT_ROOT/.runtime/comfyui"

if [[ ! -x "$COMFYUI_PYTHON" || ! -f "$COMFYUI_DIR/main.py" || ! -f "$CHECKPOINT_PATH" ]]; then
    echo "ComfyUI is not ready. Run ./scripts/setup_comfyui.sh first." >&2
    exit 1
fi

mkdir -p "$RUNTIME_ROOT/input" "$RUNTIME_ROOT/output" "$RUNTIME_ROOT/temp" "$RUNTIME_ROOT/user"
cat > "$MODEL_PATHS_CONFIG" <<EOF
render_video:
  base_path: $COMFYUI_MODEL_ROOT
  checkpoints: checkpoints
EOF

DEVICE="${COMFYUI_DEVICE:-auto}"
if [[ "$DEVICE" == "auto" ]]; then
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
        DEVICE="gpu"
    else
        DEVICE="cpu"
    fi
fi

case "$DEVICE" in
    gpu)
        DEVICE_ARGS=(--lowvram --cpu-vae --reserve-vram 0.5)
        ;;
    cpu)
        DEVICE_ARGS=(--cpu)
        echo "NVIDIA runtime unavailable; ComfyUI is using the slower CPU mode." >&2
        ;;
    *)
        echo "COMFYUI_DEVICE must be auto, gpu, or cpu." >&2
        exit 1
        ;;
esac

cd "$COMFYUI_DIR"
exec "$COMFYUI_PYTHON" main.py \
    --listen "${COMFYUI_HOST:-127.0.0.1}" \
    --port "${COMFYUI_PORT:-8188}" \
    --disable-auto-launch \
    "${DEVICE_ARGS[@]}" \
    --extra-model-paths-config "$MODEL_PATHS_CONFIG" \
    --input-directory "$RUNTIME_ROOT/input" \
    --output-directory "$RUNTIME_ROOT/output" \
    --temp-directory "$RUNTIME_ROOT/temp" \
    --user-directory "$RUNTIME_ROOT/user"
