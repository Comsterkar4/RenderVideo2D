# 01 — Thư mục và chính sách tải xuống

[← Tổng quan](00-tong-quan.md) · [Mục lục](../README.md) · [Tiếp theo: Kiến trúc →](02-kien-truc.md)

## Quy tắc bắt buộc

Mọi source, model, package cache, file tạm và kết quả được tải trong quá trình phát triển phải nằm bên trong thư mục dự án này.

Không tự động:

- Cài package vào Python hệ thống.
- Clone repository vào thư mục cha hoặc thư mục home.
- Lưu model vào cache mặc định của người dùng.
- Dùng `/tmp` cho tài nguyên cần giữ lại.
- Chạy `apt`, `dnf` hoặc lệnh cài đặt toàn hệ thống khi chưa được chấp thuận.

## Cấu trúc thư mục local

```text
RenderVideo/
├── .cache/               # Cache uv, pip, Hugging Face và tác vụ tạm
├── .runtime/             # PID, log và file tạm lúc chạy
├── .venv/                # Python virtual environment
├── .venv-comfyui/        # Python virtual environment riêng của ComfyUI
├── data/
│   └── projects/         # Tài nguyên của từng project
├── downloads/            # File tải về chưa giải nén/kiểm tra
├── models/
│   ├── comfyui/
│   ├── huggingface/
│   ├── ollama/
│   └── torch/
├── third_party/
│   ├── ComfyUI-v0.40.0/
│   └── Wan2.2/           # Chỉ thêm ở giai đoạn image-to-video
├── tools/                # Binary portable nếu cần
├── workflows/            # Workflow ComfyUI đã pin phiên bản
├── backend/
├── frontend/
└── docs/
```

Không commit `.cache`, `.runtime`, `.venv`, `.venv-comfyui`, `data`, `downloads`, `models`, binary trong `tools` hoặc nội dung tải trong `third_party`.

## Biến môi trường local

Mọi script cài đặt hoặc khởi động phải đặt các biến sau từ project root:

```bash
export PROJECT_ROOT="$PWD"
export XDG_CACHE_HOME="$PROJECT_ROOT/.cache"
export PIP_CACHE_DIR="$PROJECT_ROOT/.cache/pip"
export UV_CACHE_DIR="$PROJECT_ROOT/.cache/uv"
export HF_HOME="$PROJECT_ROOT/models/huggingface"
export HUGGINGFACE_HUB_CACHE="$PROJECT_ROOT/models/huggingface/hub"
export TORCH_HOME="$PROJECT_ROOT/models/torch"
export OLLAMA_MODELS="$PROJECT_ROOT/models/ollama"
export TMPDIR="$PROJECT_ROOT/.runtime/tmp"
```

Các đường dẫn phải được resolve từ project root, không phụ thuộc thư mục chạy hiện tại của worker.

Gemini key có thể nhập từ Web UI và chỉ được giữ trong RAM backend; `GEMINI_API_KEY` trong `.env` là phương án dự phòng. Không lưu key vào JavaScript, URL, database hoặc log. Khi chạy ngoài localhost, phải bảo vệ endpoint cấu hình bằng HTTPS và xác thực.

## Vị trí tải từng loại tài nguyên

| Tài nguyên | Đường dẫn |
|---|---|
| Source ComfyUI | `third_party/ComfyUI-v0.40.0/` |
| Source Wan2.2 | `third_party/Wan2.2/` |
| Model ComfyUI | `models/comfyui/` |
| Model Ollama | `models/ollama/` |
| Model Hugging Face | `models/huggingface/` |
| Python package | `.venv/`, `.venv-comfyui/` |
| Cache pip/uv | `.cache/pip/`, `.cache/uv/` |
| File tải tạm | `downloads/` |
| Output của project | `data/projects/<project_id>/` |
| Log/runtime | `.runtime/` |

## Quy trình tải dependency

1. Xác định repository chính thức và giấy phép.
2. Chọn release hoặc commit cụ thể.
3. Tải vào `downloads/` hoặc clone vào `third_party/`.
4. Lưu URL, version/commit và checksum vào manifest.
5. Đặt model vào `models/`, không đặt trong source backend.
6. Kiểm tra lệnh smoke của dependency.
7. Không tự động cập nhật dependency trong production.

Manifest đề xuất:

```yaml
name: comfyui
source: https://github.com/Comfy-Org/ComfyUI
revision: v0.40.0
local_path: third_party/ComfyUI-v0.40.0
license: GPL-3.0
```

## Kiểm tra đường dẫn

Một bước cài đặt đạt yêu cầu khi:

- Không tạo file model hoặc package bên ngoài project root.
- `git status` không chứa model hoặc output lớn.
- Worker đọc được đường dẫn từ cấu hình, không hard-code `/home/...`.
- Xóa `.runtime/` không làm mất project hoặc model.
- Xóa `.cache/` chỉ làm mất cache, không làm mất dữ liệu chính.