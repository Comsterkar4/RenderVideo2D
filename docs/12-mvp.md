# 12 — Mục tiêu MVP

[← Kiến trúc mở rộng](11-kien-truc-mo-rong.md) · [Mục lục](../README.md)

## Định nghĩa hoàn thành

MVP hoàn thành khi một người dùng có thể đi từ truyện văn bản đến một video MP4 xem được mà không sửa database, JSON hoặc chạy lệnh thủ công ngoài thao tác khởi động dịch vụ.

```text
Nhập truyện
→ tạo và duyệt storyboard
→ tạo ảnh từng cảnh
→ tạo giọng đọc và SRT
→ dựng preview
→ tải MP4
```

Chỉ có backend hoặc storyboard chưa được xem là MVP hoàn chỉnh.

## Tiêu chí bắt buộc

1. Tạo, mở lại và xóa project.
2. Ollama tạo Character Bible và storyboard đúng schema.
3. Người dùng chỉnh sửa và duyệt storyboard trên UI.
4. Tạo một keyframe cho mỗi cảnh.
5. Người dùng duyệt hoặc tạo lại riêng từng keyframe.
6. ViViBe tạo narration và SRT cho từng cảnh.
7. Audio thực tế cập nhật thời lượng cảnh.
8. FFmpeg tạo chuyển động pan/zoom, ghép audio và phụ đề.
9. UI hiển thị preview và cho tải MP4.
10. Khởi động lại ứng dụng không làm mất project, job hoặc asset đã hoàn thành.

## Không thuộc MVP

- Wan2.2 image-to-video.
- Lip-sync.
- Nhiều giọng hội thoại trong cùng cảnh.
- Remotion template phức tạp.
- Tự động đăng YouTube/TikTok.
- Nhiều workflow và nhiều channel.
- Ledger xuất bản.
- Training LoRA hoặc model riêng.

Các phần này chỉ bắt đầu sau khi luồng ảnh tĩnh → MP4 hoạt động ổn định.

## Các mốc

| Mốc | Kết quả quan sát được | Trạng thái |
|---|---|---|
| A1 | FastAPI và SQLite chạy local | Hoàn thành |
| A2 | Project CRUD trên API | Hoàn thành |
| A3 | Ollama tạo và lưu storyboard | Hoàn thành |
| A4 | UI tạo project, phân tích, chỉnh sửa và duyệt storyboard | Hoàn thành |
| B1 | ComfyUI tạo một ảnh nhân vật và một ảnh cảnh | Chưa triển khai |
| B2 | UI duyệt/tạo lại ảnh | Chưa triển khai |
| C1 | ViViBe tạo audio và SRT | Hoàn thành |
| D1 | FFmpeg render preview một cảnh | Chưa triển khai |
| D2 | Render truyện ba cảnh thành MP4 | Chưa triển khai |
| E1 | UI preview và tải video | Chưa triển khai |

## Demo nghiệm thu MVP

Dùng một truyện ba cảnh ngắn. Demo đạt khi:

- Storyboard có thứ tự `1, 2, 3` và Character Bible nhất quán.
- Mỗi cảnh có ảnh, narration và phụ đề.
- Video có đúng thứ tự cảnh.
- Không có audio bị cắt hoặc khoảng đen.
- Phụ đề đọc được và khớp narration.
- Có thể tạo lại một ảnh mà không tạo lại audio hoặc toàn video.
- File cuối nằm tại `data/projects/<id>/renders/final.mp4` và tải được từ UI.