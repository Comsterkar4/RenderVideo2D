# 04 — Tạo hình ảnh với ComfyUI hoặc Gemini

[← Storyboard](03-storyboard-ollama.md) · [Mục lục](../README.md) · [Tiếp theo: ViViBe →](05-giong-noi-vivibe.md)

## Vai trò

RenderVideo quản lý project, prompt, provider, trạng thái và file đầu ra. Người dùng chọn **ComfyUI local** hoặc **Gemini API** trên giao diện trước khi tạo tất cả ảnh hay tạo lại một cảnh.

Với ComfyUI, RenderVideo:

1. Nạp workflow JSON đã pin phiên bản.
2. Thay prompt, seed và kích thước.
3. Gửi workflow tới ComfyUI.
4. Lưu `prompt_id`.
5. Theo dõi queue/history.
6. Tải output vào thư mục project.

Với Gemini, backend gửi prompt và tỷ lệ khung hình tới Interactions API, giải mã ảnh trả về rồi lưu `interaction_id`. `GEMINI_API_KEY` chỉ được đọc từ môi trường backend, không được trả qua API hoặc đưa vào frontend.

## Cài đặt và khởi động

Toàn bộ source, Python package và model nằm trong repository:

```bash
./scripts/setup_comfyui.sh
./scripts/run_comfyui.sh
```

Các vị trí chính:

```text
third_party/ComfyUI-v0.40.0/
.venv-comfyui/
models/comfyui/checkpoints/
downloads/
```

Checkpoint mặc định là `dreamshaper_8.safetensors` (DreamShaper 8, Stable Diffusion 1.5, khoảng 2.08 GB). Tải từ [trang model của tác giả Lykon trên Civitai](https://civitai.com/models/4384/dreamshaper) theo giấy phép CreativeML OpenRAIL-M; mã SHA-256: `879db523c30d3b9017143d56705015e15a2cb5628762c11d086fed9538abd7fd`. `COMFYUI_CHECKPOINT` vẫn có thể ghi đè tên file. Launcher tự chọn GPU hoặc CPU; máy hiện tại không nhận NVIDIA nên dùng CPU, chậm hơn.

## Cấu hình Gemini

Trên thanh đầu trang, chọn **Gemini keys**, nhập tối đa 20 key — mỗi dòng một key — rồi chọn **Lưu keys**. Backend loại key trùng và chỉ giữ key trong RAM:

- Key không được trả lại frontend sau khi lưu.
- Khởi động lại backend sẽ xóa các key nhập từ Web UI.
- Khi key bị từ chối xác thực, hết quota (`429`) hoặc Gemini trả lỗi server, backend thử key tiếp theo.
- Key thành công được ưu tiên cho request sau để không lặp lại key hỏng.
- Lỗi prompt/model (`400` không liên quan API key) không chuyển key vì đổi key không sửa được request.

Nhiều key không đảm bảo tăng quota: các key thuộc cùng Google Cloud project có thể dùng chung hạn mức. Failover chủ yếu giúp khi một key bị thu hồi, bị giới hạn riêng hoặc dịch vụ trả lỗi tạm thời.

`GEMINI_API_KEY` trong `.env` là cấu hình dự phòng tùy chọn khi chưa nhập key trên Web UI. Các biến không chứa secret:

- `GEMINI_API_BASE_URL`: mặc định `https://generativelanguage.googleapis.com/v1beta`.
- `GEMINI_IMAGE_TIMEOUT_SECONDS`: mặc định `300`.
- `GEMINI_IMAGE_MODEL`: model tạo ảnh; mặc định `gemini-nano-banana-2.1`.

Không commit `.env`. Nếu frontend/backend được mở ra ngoài localhost, phải dùng HTTPS và lớp xác thực trước khi nhập key.

## Workflow trong repository

```text
workflows/
├── character-reference.v1.json
├── scene-image.v1.json
├── scene-image-to-image.v1.json
├── scene-video-wan22.v1.json
└── upscale.v1.json
```

Không tạo workflow bằng nối chuỗi JSON. Adapter chỉ được thay các input cho phép.

```python
class SceneImageWorkflow:
    POSITIVE_PROMPT_NODE = "6"
    SEED_NODE = "25"
    LATENT_NODE = "31"

    def build(self, prompt: str, seed: int, width: int, height: int) -> dict:
        workflow = load_workflow("scene-image.v1.json")
        workflow[self.POSITIVE_PROMPT_NODE]["inputs"]["text"] = prompt
        workflow[self.SEED_NODE]["inputs"]["seed"] = seed
        workflow[self.LATENT_NODE]["inputs"]["width"] = width
        workflow[self.LATENT_NODE]["inputs"]["height"] = height
        return workflow
```

## Thứ tự tạo ảnh

```text
Storyboard đã duyệt
→ chọn ComfyUI hoặc Gemini trên giao diện
→ nếu dùng ComfyUI, dỡ model Ollama khỏi RAM/VRAM
→ tạo tuần tự ảnh từng cảnh
→ nếu dùng ComfyUI, giải phóng model ảnh
→ người dùng xem provider, model và tạo lại từng ảnh
→ duyệt ảnh
→ chuyển sang bước âm thanh
```

Prompt ảnh cảnh được ghép theo thứ tự:

```text
2D cartoon illustration for a children's picture book, hand-drawn storybook art,
bold clean ink outlines, flat cel shading, simple rounded shapes, warm vibrant colors
+ scene.image_prompt (mô tả duy nhất địa điểm và hành động của cảnh)
+ single coherent scene, one animation frame, clear focal subject, no text
```

`scene.image_prompt` phải tự chứa chủ thể, hành động và địa điểm. Backend không nối `character.prompt_fragment` vào prompt cảnh vì fragment cũ có thể lẫn hành động/địa điểm và làm sai bối cảnh.

Với ComfyUI, danh sách loại trừ được gửi vào negative prompt của Stable Diffusion. Với Gemini, provider nối thêm:

```text
Do not include any of the following: photorealistic, realistic photo,
live action, photography, 3d, cgi, ..., text, watermark, collage, ...
```

Gemini nhận tỷ lệ khung hình qua `response_format.aspect_ratio`. Seed vẫn được lưu trong metadata để theo dõi asset nhưng Gemini Interactions API hiện không nhận seed này, nên cùng prompt có thể cho kết quả khác nhau.

## Lưu output

Mỗi lần tạo hoặc tạo lại sinh một asset riêng:

```text
data/projects/<project_id>/scenes/<scene_id>/
├── <asset_id>.png                 # ComfyUI
├── <asset_id>.jpg                 # Gemini
└── <asset_id>.metadata.json
```

API phục vụ ảnh qua `GET /api/assets/<asset_id>/content`; frontend không đọc đường dẫn file trực tiếp.

Metadata phải có:

- Provider và model trên bản ghi asset.
- Prompt, negative prompt và seed.
- ID request bên ngoài (`prompt_id` của ComfyUI hoặc `interaction_id` của Gemini).
- Tỷ lệ khung hình hoặc kích thước đầu ra.
- Workflow/checkpoint và tên output gốc khi dùng ComfyUI.

ComfyUI được lưu và phục vụ dưới dạng `image/png`. Gemini Interactions API hiện chỉ hỗ trợ `response_format.mime_type=image/jpeg`; backend lưu file `.jpg` và trả đúng HTTP `Content-Type: image/jpeg`.

## Test module

### Test A — kết nối

- Gửi workflow nhỏ tới ComfyUI.
- Nhận `prompt_id`.
- Theo dõi đến trạng thái hoàn thành.

### Test B — ảnh cảnh

- Tạo một ảnh cảnh ở độ phân giải thấp.
- File phải được tải vào `data/projects/<project_id>/scenes/<scene_id>/`.
- Metadata phải đủ prompt, seed, checkpoint và workflow version.

### Test C — tái sử dụng

- Chạy lại **Tạo tất cả hình ảnh**.
- Ảnh đã hoàn thành phải được tái sử dụng, không tạo job GPU mới.

### Test D — tạo lại

- Tạo lại riêng một cảnh.
- Asset mới dùng seed mới; các cảnh còn lại không thay đổi.

### Test E — Gemini

- Nhập nhiều key trên UI; API trạng thái chỉ trả số lượng và nguồn, không trả secret.
- Cho key đầu trả `429` và key sau thành công; chỉ tạo một asset hoàn chỉnh.
- Chọn **Gemini API** và tạo một cảnh; asset phải ghi `provider=gemini`, model, `interaction_id`, đúng tỷ lệ, lưu `.jpg` và phục vụ với `Content-Type: image/jpeg`.
- Khi không có key Web UI hoặc `GEMINI_API_KEY`, API tạo ảnh phải trả HTTP `503`.

MVP ảnh đạt khi toàn bộ cảnh có ảnh, có thể chọn ComfyUI/Gemini, xem provider/model, tạo lại trên UI và project chuyển sang `awaiting_asset_review`.