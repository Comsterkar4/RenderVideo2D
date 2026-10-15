# 13 — Giao diện MVP bằng Python

[← Mục tiêu MVP](12-mvp.md) · [Mục lục](../README.md)

## Công nghệ

- Backend API: FastAPI tại cổng `9000`.
- Frontend server: FastAPI + Jinja2 tại cổng `9001`.
- Tương tác trình duyệt: JavaScript thuần, không React, Node.js hoặc Bun.
- CSS nằm trong repository, không tải font hoặc tài nguyên ngoài.

Bun không còn là dependency của dự án.

## Khởi động

### API và frontend cùng lúc

```bash
./scripts/dev_all.sh
```

### Hoặc chạy riêng

Terminal API:

```bash
./scripts/dev.sh
```

Terminal frontend:

```bash
./scripts/dev_frontend.sh
```

Terminal Ollama, khi cần phân tích truyện:

```bash
./scripts/run_ollama.sh
```

Terminal ComfyUI, khi cần tạo ảnh:

```bash
./scripts/run_comfyui.sh
```

Địa chỉ:

| Dịch vụ         | URL                                                          |
| --------------- | ------------------------------------------------------------ |
| Giao diện       | [http://127.0.0.1:9001](http://127.0.0.1:9001)               |
| API docs        | [http://127.0.0.1:9000/docs](http://127.0.0.1:9000/docs)     |
| Backend health  | [http://127.0.0.1:9000/health](http://127.0.0.1:9000/health) |
| Frontend health | [http://127.0.0.1:9001/health](http://127.0.0.1:9001/health) |
| Ollama API      | [http://127.0.0.1:11434](http://127.0.0.1:11434)             |
| ComfyUI API     | [http://127.0.0.1:8188](http://127.0.0.1:8188)               |

## Chức năng hiện tại

- Xem danh sách project.
- Tạo project từ truyện và tỷ lệ khung hình; hình ảnh luôn là hoạt hình 2D vẽ tay, ngôn ngữ video luôn là tiếng Việt.
- Mở và làm mới project.
- Xóa project.
- Gọi Ollama phân tích truyện.
- Xem Character Bible.
- Xem các cảnh, narration, prompt và sound effects.
- Chỉnh storyboard JSON có backend validation.
- Duyệt storyboard.
- Xem trạng thái pipeline.
- Nhập, xóa và xem số lượng Gemini key đang giữ trong RAM; API không trả lại secret.
- Chọn ComfyUI local hoặc Gemini API khi tạo ảnh.
- Tạo tuần tự một ảnh cho mỗi cảnh bằng provider đã chọn.
- Xem ảnh cùng provider/model ngay trong project.
- Tạo mới hoặc tạo lại riêng từng cảnh bằng provider đang chọn.

## Quy trình thao tác

1. Mở `http://127.0.0.1:9001`.
2. Chọn **Tạo dự án đầu tiên**.
3. Nhập tiêu đề, truyện và chọn tỷ lệ khung hình. Giao diện hiển thị phong cách hoạt hình 2D vẽ tay và tiếng Việt dưới dạng thiết lập cố định.
4. Chọn **Tạo dự án**.
5. Chọn **Phân tích truyện**.
6. Kiểm tra nhân vật và từng cảnh.
7. Nếu cần, mở **Chỉnh sửa storyboard JSON** và lưu.
8. Chọn **Duyệt storyboard**.
9. Nếu dùng ComfyUI, khởi động bằng `./scripts/run_comfyui.sh`. Nếu dùng Gemini, chọn **Gemini keys** trên thanh đầu trang, nhập mỗi key trên một dòng rồi lưu.
10. Chọn **Nguồn tạo ảnh**, sau đó chọn **Tạo tất cả hình ảnh** hoặc tạo riêng từng cảnh.
11. Tạo lại ảnh chưa đạt rồi chọn **Duyệt hình ảnh**.

Backend tạo ảnh tuần tự, tái sử dụng ảnh đã hoàn thành và lưu từng lần tạo lại thành một asset riêng. Mỗi asset ghi provider, model và external request ID.

Key nhập trên giao diện chỉ tồn tại trong RAM của tiến trình backend. Backend tự thử key tiếp theo khi gặp lỗi key, quota hoặc lỗi server; khởi động lại backend thì phải nhập lại. Nếu triển khai ngoài localhost, cần HTTPS và xác thực vì trình duyệt phải gửi key tới backend khi lưu.

## Cấu trúc

```text
frontend/
├── app.py
├── templates/
│   └── index.html
└── static/
    ├── app.js
    └── styles.css
```

Frontend không truy cập SQLite. Mọi dữ liệu đi qua backend API.