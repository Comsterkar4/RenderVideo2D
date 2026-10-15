# 08 — Kế hoạch triển khai và test từng bước

[← Wan2.2](07-video-wan22.md) · [Mục lục](../README.md) · [Tiếp theo: Vận hành →](09-van-hanh.md)

Không chuyển bước khi bước hiện tại chưa tạo được artifact có thể quan sát.

## Bước 0 — Kiểm tra máy

Trạng thái đã quan sát:

| Thành phần | Trạng thái |
|---|---|
| Python | `3.12.3` |
| uv | `0.12.1` |
| FFmpeg/ffprobe | Chưa được cài; chặn Bước 4 |
| NVIDIA GPU | Driver hiện không giao tiếp được; chặn ComfyUI GPU ở Bước 5 |
| Dung lượng trống | Khoảng 67 GB trong phân vùng dự án |

Backend nhẹ vẫn triển khai được. Chưa tải FFmpeg, ComfyUI hoặc model ở bước này.

## Bước 1 — Backend tối thiểu

Đã xây dựng:

- FastAPI.
- Endpoint `GET /health`.
- Script cấu hình cache/model bên trong project.
- Virtual environment `.venv`.
- Lock file của `uv`.

Cài hoặc đồng bộ dependency:

```bash
./scripts/setup_backend.sh
```

Chạy API:

```bash
./scripts/run_api.sh
```

Kiểm tra trong terminal khác:

```bash
curl --fail --silent http://127.0.0.1:9000/health
```

Kết quả mong đợi:

```json
{"status":"ok","service":"render-video-api","version":"0.1.0"}
```

Bước đạt khi response đúng và API khởi động lại không lỗi.

## Bước 2A — Dữ liệu và API project

Đã xây dựng:

- Project, Character, Scene và Asset database schema.
- SQLite local và Alembic migration.
- Pydantic validation.
- API tạo, liệt kê, đọc, cập nhật và xóa project.

Chạy migration và xem hướng dẫn test tại [10-api-projects.md](10-api-projects.md).

Đạt khi hoàn thành vòng đời `create → list → get → update → delete → 404`.

## Bước 2B — Storyboard với Ollama

Xây dựng tiếp:

- Ollama adapter.
- Structured output theo Storyboard schema.
- Ghi Character Bible và Scene vào project.
- API duyệt storyboard.

Test bằng truyện hai câu. Artifact:

```text
data/projects/test-story/storyboard.json
```

Đạt theo tiêu chí trong [03-storyboard-ollama.md](03-storyboard-ollama.md).

## Bước 3 — ViViBe độc lập

Xây dựng:

- ViViBe adapter.
- Lưu `projectExportId`.
- Polling bằng worker.
- Download audio/SRT.
- Đo thời lượng bằng ffprobe.

Dùng một câu ngắn để tránh tốn credit. Artifact:

```text
data/projects/test-vivibe/scenes/scene_001/narration.wav
```

Đạt theo [05-giong-noi-vivibe.md](05-giong-noi-vivibe.md).

## Bước 4 — FFmpeg một cảnh

Không chờ ComfyUI. Dùng một ảnh test nhỏ và audio từ Bước 3.

Xây dựng:

- Timeline JSON.
- Pan/zoom.
- Audio.
- Phụ đề.

Artifact:

```text
data/projects/test-render/renders/preview.mp4
```

Phải mở/probe video thực tế.

## Bước 5 — ComfyUI một ảnh

Chỉ lúc này mới cài/tải ComfyUI và model vào đường dẫn local quy định.

Xây dựng:

- ComfyUI adapter.
- Workflow tạo ảnh nhỏ.
- Polling queue/history.
- Download output và metadata.

Đạt khi một ảnh được tạo, lưu và có thể tái sử dụng theo asset key.

## Bước 6 — Pipeline ba cảnh

Dùng một truyện rất ngắn:

1. Ollama tạo ba cảnh.
2. ComfyUI tạo ba ảnh.
3. ViViBe tạo narration từng cảnh.
4. FFmpeg render preview.
5. Kiểm tra thứ tự, tiếng, phụ đề và thời lượng.

Đây là mốc hoàn thành kỹ thuật của MVP.

## Bước 7 — UI duyệt

Xây dựng giao diện:

- Nhập truyện.
- Sửa/duyệt storyboard.
- Sửa/duyệt Character Bible.
- Duyệt và tạo lại ảnh cảnh.
- Theo dõi tiến trình.
- Xem/tải preview.

Đạt khi người dùng hoàn thành pipeline ba cảnh mà không chỉnh database hoặc file thủ công.

## Bước 8 — Wan2.2 tùy chọn

Chỉ thực hiện sau Bước 6 và khi phần cứng đáp ứng.

- Tải source/model vào project.
- Test một clip.
- Tích hợp một cảnh vào timeline.
- So sánh với phương án pan/zoom.

## Checklist sau mỗi bước

- [ ] Có artifact quan sát được.
- [ ] Đã chạy đúng đường đi vừa thay đổi.
- [ ] Lỗi được lưu và hiển thị rõ.
- [ ] Không có secret trong log.
- [ ] Không có file tải ngoài project.
- [ ] Không có model/output lớn bị Git theo dõi.
- [ ] Có thể chạy lại mà không tạo asset hoặc job trả phí trùng.