# 03 — Phân tích truyện với Ollama

[← Kiến trúc](02-kien-truc.md) · [Mục lục](../README.md) · [Tiếp theo: ComfyUI →](04-hinh-anh-comfyui.md)

## Trách nhiệm

Ollama chỉ tạo dữ liệu có cấu trúc:

- Character Bible.
- Danh sách cảnh.
- Lời kể tiếng Việt.
- Prompt ảnh và chuyển động bằng tiếng Anh.
- Gợi ý hiệu ứng âm thanh.

Ngôn ngữ lời kể được khóa ở tiếng Việt trong backend và prompt hệ thống, kể cả khi truyện nguồn dùng ngôn ngữ khác. `image_prompt` và `prompt_fragment` dùng tiếng Anh để CLIP hiểu đúng chủ thể, đồng thời nhấn mạnh phong cách `2D hand-drawn animation`.

Ollama không ghi database và không gọi ComfyUI. `StoryToVideo` workflow validate output bằng Pydantic rồi service mới lưu Character và Scene trong một transaction.

## Cài Ollama local

Ollama chưa có sẵn trong hệ thống nên được cài hoàn toàn bên trong project:

```bash
./scripts/setup_ollama.sh
```

Vị trí:

```text
downloads/ollama-linux-amd64-v0.40.4.tar.zst
tools/ollama-v0.40.4/
tools/ollama-current -> tools/ollama-v0.40.4
models/ollama/
```

Không dùng installer hệ thống và không ghi vào `/usr` hoặc thư mục home.

## Khởi động và tải model

Terminal thứ nhất:

```bash
./scripts/run_ollama.sh
```

Terminal thứ hai:

```bash
./scripts/pull_story_model.sh
```

Model mặc định:

```text
qwen2.5:3b
```

Model được chọn vì hỗ trợ đa ngôn ngữ và đủ nhỏ để thử trên CPU. Máy hiện không sử dụng được NVIDIA driver nên phân tích có thể chậm. Context được giới hạn ở 4096 token để giảm bộ nhớ.

Biến cấu hình:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_STORY_MODEL=qwen2.5:3b
```

## Storyboard schema

```json
{
  "title": "Cô bé quàng khăn đỏ",
  "visual_style": "hoạt hình 2D vẽ tay, màu phẳng, đường nét rõ, thân thiện với trẻ em",
  "characters": [
    {
      "id": "little_red",
      "name": "Cô bé quàng khăn đỏ",
      "appearance": "bé gái 8 tuổi, tóc nâu, áo choàng đỏ, váy trắng",
      "prompt_fragment": "8-year-old girl, brown hair, red hooded cape, white dress"
    }
  ],
  "scenes": [
    {
      "id": "scene_001",
      "order": 1,
      "duration_seconds": 7,
      "character_ids": ["little_red"],
      "location": "đường mòn trong rừng",
      "narration": "Ngày xửa ngày xưa...",
      "image_prompt": "A little girl walking through a warm fairy-tale forest...",
      "motion_prompt": "The girl walks slowly while the camera tracks from the side...",
      "sound_effects": ["birds", "soft_wind"]
    }
  ]
}
```

Validation bắt buộc:

- Không có field ngoài schema.
- Character ID và Scene ID không trùng.
- ID chỉ dùng chữ thường ASCII, chữ số và `_`.
- Scene order liên tục từ 1.
- Mọi `character_ids` tồn tại trong Character Bible.
- Mỗi cảnh có 1–3 nhân vật.
- Thời lượng mỗi cảnh 4–10 giây.
- `visual_style` được service chuẩn hóa về phong cách hoạt hình 2D vẽ tay cố định trước khi lưu.

## API

| Method | Path | Chức năng |
|---|---|---|
| `POST` | `/api/projects/{id}/analyze` | Gọi Ollama, validate và lưu storyboard |
| `GET` | `/api/projects/{id}/storyboard` | Đọc storyboard hiện tại |
| `PUT` | `/api/projects/{id}/storyboard` | Thay storyboard đã chỉnh sửa |
| `POST` | `/api/projects/{id}/storyboard/approve` | Duyệt và chuyển sang tạo assets |

### Phân tích

Tạo project trước, sau đó:

```bash
curl --fail --silent \
  --request POST \
  http://127.0.0.1:9000/api/projects/<PROJECT_ID>/analyze
```

Trong lúc phân tích, status là `analyzing`. Thành công chuyển thành `awaiting_storyboard_review`.

Lỗi provider:

- Ollama không chạy hoặc timeout → HTTP `503`.
- Ollama trả lỗi/JSON không hợp lệ → HTTP `502`.
- Project không ở trạng thái cho phép sửa storyboard → HTTP `409`.

### Duyệt storyboard

```bash
curl --fail --silent \
  --request POST \
  http://127.0.0.1:9000/api/projects/<PROJECT_ID>/storyboard/approve
```

Sau khi duyệt, project chuyển sang `generating_assets` và không thể phân tích lại. Điều này ngăn việc vô tình xóa Character/Scene khi assets đang được tạo.

## Dữ liệu lưu lại

Database:

- Character Bible.
- Scene và thứ tự.
- Quan hệ cảnh–nhân vật.
- Narration, prompt, sound effects và thời lượng.

Artifact:

```text
data/projects/<project_id>/story.txt
data/projects/<project_id>/storyboard.json
```

File được thay thế atomically qua file `.tmp` cùng thư mục.

## Tiêu chí test

1. Ollama trả JSON đúng schema.
2. Pydantic validation thành công.
3. Character và Scene được lưu vào SQLite.
4. `GET storyboard` trả lại cùng dữ liệu.
5. File `story.txt` và `storyboard.json` tồn tại.
6. Approve chuyển status sang `generating_assets`.
7. Analyze lại sau approve trả `409`.
8. Lỗi Ollama không làm mất storyboard cũ.