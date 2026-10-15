# 09 — Vận hành, lỗi và rủi ro

[← Kế hoạch test](08-ke-hoach-test.md) · [Mục lục](../README.md)

## Nhân vật không nhất quán

Giảm rủi ro bằng:

- Character Bible là nguồn mô tả duy nhất.
- Prompt fragment cố định.
- Ảnh tham chiếu được duyệt trước.
- Lưu seed, model và workflow.
- Không tạo video trước khi duyệt keyframe.

## API ViViBe lỗi hoặc chậm

- Lưu `projectExportId` trước khi polling.
- Poll mỗi 2–3 giây, không polling liên tục.
- Retry kiểm tra trạng thái khi lỗi mạng tạm thời.
- Không gọi lại `ttsLongText` một cách mù quáng.
- Tải audio/SRT về local ngay khi hoàn thành.
- Hiển thị trạng thái `failed` và lỗi provider.

## Chi phí

- Chỉ gọi ViViBe sau khi narration đã được duyệt.
- Cache theo text, voice ID và speed.
- Chỉ gọi Wan sau khi ảnh được duyệt.
- Preview ở độ phân giải thấp.
- Cho phép tạo lại riêng một cảnh.
- Lưu số ký tự ViViBe trả về để đối soát.

## GPU và VRAM

- Một GPU worker tại một thời điểm.
- Không chạy Ollama model lớn và ComfyUI đồng thời trên cùng GPU.
- Bắt đầu bằng ảnh; Wan2.2 triển khai sau.
- Thiếu VRAM phải báo lỗi cấu hình, không lặp retry vô hạn.

## Khôi phục job

Sau khi worker restart:

1. Tìm job `submitted` hoặc `processing`.
2. Nếu có `external_job_id`, hỏi provider về trạng thái hiện tại.
3. Nếu provider hoàn thành, tải asset.
4. Nếu provider thất bại, lưu lỗi.
5. Không tạo một job mới trừ khi người dùng yêu cầu retry.

## Quản lý secret

- Secret nằm trong `.env` local hoặc secret manager production.
- `.env` không được commit.
- Log phải che Authorization header và API key.
- Frontend không nhận API key.
- Error response không chứa raw request header.

## Quản lý dependency

- Chỉ dùng repository chính thức hoặc fork đã đánh giá.
- Pin release/commit.
- Pin workflow và custom node ComfyUI.
- Lưu model ngoài Git.
- Ghi URL, checksum và giấy phép trong manifest.
- Không tự động nâng cấp production.

## Quyền sử dụng

Phải kiểm tra riêng:

- Giấy phép source code.
- Giấy phép model weights.
- Dataset/model có cho phép thương mại không.
- Quyền sử dụng giọng ViViBe.
- Bản quyền nhạc, hình tham chiếu và truyện đầu vào.

## Tiêu chí sẵn sàng production

- Job idempotent và có retry policy rõ ràng.
- Có giới hạn kích thước truyện và số cảnh.
- Có quota/chi phí theo project.
- Có backup database và asset storage.
- Có health check cho Ollama, ComfyUI, Redis và storage.
- Có timeout cho mọi HTTP request ngoài.
- Có cleanup policy cho file tạm nhưng không xóa asset đã duyệt.
- Render hoàn chỉnh vẫn hoạt động khi Wan2.2 bị tắt.