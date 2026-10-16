# 05 — Tạo giọng nói với ViViBe API

[← ComfyUI](04-hinh-anh-comfyui.md) · [Mục lục](../README.md) · [Tiếp theo: FFmpeg →](06-dung-video-ffmpeg.md)

Tài liệu API chính thức: [ViViBe API Documentation](https://www.vivibe.app/api-docs.html).

## Quyết định

ViViBe chạy ngoài máy. RenderVideo không tải hoặc chạy model TTS local.

API key được gửi tới backend và giữ trong RAM. Frontend đồng thời lưu tạm key trong `sessionStorage` của phiên trình duyệt để tự gửi lại nếu backend khởi động lại. Đóng phiên trình duyệt hoặc chọn **Xóa key đã lưu** sẽ xóa bản lưu tạm. Key không được ghi vào database, URL, log hoặc response trạng thái.

Có thể dùng `VIVIBE_API_KEY` trong `.env` làm cấu hình dự phòng khi chưa nhập key trên Web UI:

```env
VIVIBE_API_URL=https://api.lucylab.io/json-rpc
VIVIBE_API_KEY=replace-with-secret
VIVIBE_TIMEOUT_SECONDS=60
VIVIBE_MAX_DOWNLOAD_BYTES=104857600
```

Không commit file `.env`. Xóa key nhập từ giao diện sẽ quay về dùng `VIVIBE_API_KEY` nếu biến này có giá trị.

## Luồng xử lý

```text
narration của cảnh
→ ttsLongText
→ projectExportId
→ lưu database
→ getExportStatus mỗi 2–3 giây
→ completed
→ tải audio và SRT về project
→ ffprobe đo thời lượng audio
```

### Giọng đọc cố định

Mọi narration dùng giọng **Adam**, voice ID `mhsL3CPLxmLYdSTKp3GANj`. Backend giữ giá trị này trong `backend/config.py`; API và frontend không nhận voice ID tùy ý.

### Tạo audio

```json
{
  "method": "ttsLongText",
  "input": {
    "text": "Ngày xửa ngày xưa...",
    "userVoiceId": "mhsL3CPLxmLYdSTKp3GANj",
    "speed": 1.0
  }
}
```

Lưu ngay các trường trả về:

- `projectExportId`.
- `characterCount`.
- `blockCount`.

### Theo dõi trạng thái

```json
{
  "method": "getExportStatus",
  "input": {
    "projectExportId": "EXPORT_ID"
  }
}
```

Các trạng thái: `pending`, `processing`, `completed`, `failed`.

Khi hoàn thành, tải cả:

- `url` → `narration.wav`.
- `srtUrl` → `narration.srt`, nếu có.

Không phụ thuộc lâu dài vào URL của provider vì URL có thể thay đổi hoặc hết hạn.

## Adapter và API nội bộ

`VivibeSpeechProvider` gửi `ttsLongText`, đọc `getExportStatus` và tải URL kết quả. Backend cung cấp:

```text
POST /api/projects/<project_id>/audio/generate
POST /api/projects/<project_id>/audio/refresh
POST /api/projects/<project_id>/scenes/<scene_id>/audio
```

`audio/generate` gửi một job tại một thời điểm vì ViViBe không chấp nhận job mới khi đã có export đang chạy. Sau mỗi lần hoàn tất, `audio/refresh` tự gửi job kế tiếp và lưu `projectExportId`; request HTTP không chờ quá trình tạo audio. Frontend gọi `audio/refresh` mỗi 3 giây. Job đang xử lý nằm trong database nên có thể tiếp tục theo dõi sau khi tải lại trang bằng nút **Tạo âm thanh**.

Nếu backend dừng đúng lúc `ttsLongText` đã gửi nhưng chưa lưu được `projectExportId`, asset chuyển sang `failed` khi refresh. Hệ thống không tự gửi lại vì có nguy cơ trừ credit hai lần; người dùng phải chủ động thử lại.

## Retry và chi phí

- Có thể retry `getExportStatus` khi timeout mạng.
- Có thể retry tải file nếu checksum/file không hợp lệ.
- Không tự động gọi lại `ttsLongText` khi chưa biết request trước đã tạo job hay chưa; việc này có thể trừ credit hai lần.
- Không tạo lại audio nếu narration, voice ID và speed không thay đổi.

## Thời lượng cảnh

Sau khi tải audio:

1. Đọc số frame và sample rate của WAV để lấy thời lượng thật.
2. Cập nhật `scene.duration_seconds`.
3. Điều chỉnh clip hình ảnh theo audio.
4. Không cắt câu chỉ để giữ thời lượng do LLM dự đoán.

## Test module

Dùng một câu ngắn để hạn chế credit:

```text
Xin chào, đây là bài kiểm tra giọng kể của RenderVideo.
```

Đạt khi:

1. `ttsLongText` trả `projectExportId`.
2. Backend lưu ID trước lần gọi `getExportStatus` đầu tiên.
3. Job chuyển đến `completed` hoặc hiển thị `failed` rõ ràng.
4. Audio được tải vào project và phát được trên Web UI.
5. Thời lượng WAV lớn hơn 0 và cập nhật `scene.duration_seconds`.
6. SRT được tải nếu API trả `srtUrl`.
7. API key không xuất hiện trong log, response frontend hoặc metadata asset.

Artifact:

```text
data/projects/test-vivibe/scenes/scene_001/narration.wav
data/projects/test-vivibe/scenes/scene_001/narration.srt
```