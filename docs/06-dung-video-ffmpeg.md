# 06 — Dựng video với FFmpeg

[← ViViBe](05-giong-noi-vivibe.md) · [Mục lục](../README.md) · [Tiếp theo: Wan2.2 →](07-video-wan22.md)

## Trách nhiệm

FFmpeg xử lý:

- Chuẩn hóa kích thước, FPS và codec.
- Tạo pan/zoom từ ảnh.
- Ghép clip theo timeline.
- Đồng bộ narration.
- Mix nhạc và hiệu ứng âm thanh.
- Chèn phụ đề.
- Xuất MP4.

Logic render nằm trong worker/service, không nằm trong route FastAPI.

## Timeline trung gian

Trước khi chạy FFmpeg, tạo một file timeline có thể kiểm tra:

```json
{
  "width": 1920,
  "height": 1080,
  "fps": 24,
  "scenes": [
    {
      "id": "scene_001",
      "image": "scenes/scene_001/image.png",
      "audio": "scenes/scene_001/narration.wav",
      "subtitle": "scenes/scene_001/narration.srt",
      "duration_seconds": 8.32,
      "animation": "slow_zoom_in",
      "transition": "fade"
    }
  ],
  "output": "renders/final.mp4"
}
```

Mọi đường dẫn trong timeline là đường dẫn tương đối dưới thư mục project.

## Quy tắc đồng bộ

- Audio narration quyết định thời lượng tối thiểu của cảnh.
- Ảnh pan/zoom kéo dài đúng thời lượng audio.
- Clip Wan ngắn hơn audio có thể đóng băng frame cuối hoặc nối với pan/zoom; lựa chọn phải hiện trong metadata.
- Nhạc nền phải giảm âm lượng dưới narration.
- Audio đầu ra phải có sample rate và channel layout thống nhất.

## Output

```text
data/projects/<project_id>/
├── timeline.json
├── subtitles/final.srt
└── renders/
    ├── preview.mp4
    └── final.mp4
```

Preview dùng độ phân giải/bitrate thấp hơn để kiểm tra nhanh. Final chỉ chạy sau khi preview đạt.

## Test module

### Test A — một cảnh

Đầu vào:

- Một ảnh PNG.
- Một audio WAV từ ViViBe.
- Một file SRT.

Kết quả:

- MP4 phát được.
- Có chuyển động pan/zoom.
- Có tiếng và phụ đề.
- Thời lượng video không ngắn hơn narration.

### Test B — ba cảnh

- Ba cảnh có thời lượng khác nhau.
- Có chuyển cảnh.
- Không có khoảng đen hoặc audio bị cắt.
- Thứ tự cảnh đúng timeline.

### Kiểm tra bằng ffprobe

Xác nhận:

- Có một video stream.
- Có một audio stream.
- Codec và kích thước đúng cấu hình.
- Thời lượng gần với tổng timeline trong sai số encode cho phép.

Artifact:

```text
data/projects/test-render/timeline.json
data/projects/test-render/renders/preview.mp4
```

Không coi test là đạt chỉ vì FFmpeg trả exit code 0; phải mở hoặc probe file kết quả và kiểm tra stream/thời lượng.