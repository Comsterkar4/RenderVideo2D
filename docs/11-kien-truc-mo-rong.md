# 11 — Kiến trúc mở rộng nhiều workflow

[← API project](10-api-projects.md) · [Mục lục](../README.md)

## Kết luận

RenderVideo có thể mở rộng đến quy mô nhiều engine, workflow, channel và renderer như cấu trúc tham khảo. Không nên sao chép nguyên cấu trúc JavaScript đó vì RenderVideo hiện dùng FastAPI/Python, chạy job nền và tập trung vào truyện → video.

Quy tắc chính cần giữ:

- Engine dùng chung không biết workflow cụ thể nào đang gọi.
- Workflow sở hữu prompt, schema, rule và pipeline riêng.
- Provider cô lập Ollama, ComfyUI, ViViBe, Wan và FFmpeg.
- Channel chỉ chứa danh tính, logo, giọng và nhạc.
- Renderer nhận props đã validate, không tự đọc dữ liệu nghiệp vụ.
- Output sinh ra không commit; manifest và ledger có thể commit.

## Cấu trúc đích

```text
RenderVideo/
├── backend/
│   ├── api/                         # HTTP routes
│   ├── domain/                      # Project, Character, Scene, Asset
│   ├── engine/                      # Dùng chung, không import workflow cụ thể
│   │   ├── jobs.py
│   │   ├── paths.py
│   │   ├── timeline.py
│   │   ├── captions.py
│   │   ├── ledger.py
│   │   └── checks.py
│   ├── providers/                   # Adapter dịch vụ ngoài/local
│   │   ├── llm/ollama.py
│   │   ├── media/comfyui.py
│   │   ├── speech/vivibe.py
│   │   ├── video/wan.py
│   │   └── render/ffmpeg.py
│   ├── workflows/
│   │   ├── story_to_video/
│   │   │   ├── workflow.py
│   │   │   ├── schemas.py
│   │   │   ├── prompts/
│   │   │   └── checks.py
│   │   └── story_to_short/
│   ├── storage/
│   └── workers/
├── renderer/                        # Thêm khi visual phức tạp
│   ├── package.json
│   └── src/
│       ├── shared/
│       └── templates/storybook/
├── channels/
│   └── default/
│       ├── channel.json
│       ├── logos/
│       └── bgm/
├── workflows/                       # Workflow assets/config có thể chỉnh ngoài code
│   ├── story-to-video/
│   │   ├── README.md
│   │   ├── workflow.yaml
│   │   └── references/
│   └── story-to-short/
├── ledger/                          # Lịch sử video đã xuất bản
├── migrations/
├── models/                          # Model local, gitignored
├── data/                            # Database và project assets, gitignored
└── output/                          # Video xuất ra, gitignored
```

## Ranh giới dependency

```text
api → workflow service → engine → provider
                       → domain/storage
                       → renderer contract

engine ─X→ story_to_video
engine ─X→ story_to_short
provider ─X→ workflow
renderer ─X→ database
```

`X` là import bị cấm.

Workflow đăng ký vào registry qua interface, không để engine chứa `if workflow == ...`.

```python
class Workflow(Protocol):
    name: str

    def validate_input(self, project_id: str) -> None:
        ...

    def plan(self, project_id: str) -> list[JobSpec]:
        ...

    def build_render_props(self, project_id: str) -> RenderProps:
        ...
```

## Những phần nên áp dụng ngay

1. Domain model độc lập provider.
2. Provider adapter cho từng dịch vụ.
3. Dữ liệu sinh ra nằm trong `data/` và `output/`.
4. Workflow-specific prompt/check không đặt trong engine.
5. Render props phải có schema và được validate trước render.
6. Mỗi job lưu provider, model, input hash và output asset.

## Những phần chưa nên tạo ngay

- Năm workflow rỗng chỉ để có cấu trúc.
- `SKILL.md` và symlink agent nếu sản phẩm chưa dùng agent skill runtime.
- Ledger riêng cho từng channel trước khi có chức năng xuất bản.
- Remotion trước khi FFmpeg MVP một cảnh hoạt động.
- OmniVoice local vì dự án đã quyết định dùng ViViBe API.
- Bộ kiểm riêng cho workflow chưa tồn tại.

Tạo các phần này quá sớm làm tăng dependency và tạo code không có đường chạy thực tế.

## Khi nào thêm Remotion

FFmpeg tiếp tục làm nhiệm vụ chuẩn hóa media và encode. Thêm Remotion khi cần:

- Caption động theo từ.
- Template nhiều loại visual.
- Brand frame phức tạp.
- Layout React có thể tái sử dụng giữa workflow.
- Preview visual trên trình duyệt.

Backend tạo `render-props.json`; renderer chỉ nhận file đó và xuất video. Renderer không gọi Ollama, ViViBe hoặc database.

## Lộ trình mở rộng

### Giai đoạn 1

Một workflow thật: `story_to_video`. Hoàn thành project API, storyboard, ảnh, audio và render.

### Giai đoạn 2

Tách interface `Workflow`, `Provider`, `Renderer`; thêm queue và idempotency.

### Giai đoạn 3

Thêm `story_to_short`, channel config và ledger xuất bản.

### Giai đoạn 4

Thêm Remotion templates và kiểm boundary tự động khi có ít nhất hai workflow dùng chung engine.

Nguyên tắc: chỉ trích xuất engine dùng chung sau khi có ít nhất hai workflow thật chứng minh phần nào thực sự dùng chung.