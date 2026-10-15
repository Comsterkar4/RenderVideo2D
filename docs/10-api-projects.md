# 10 — API quản lý project

[← Kế hoạch test](08-ke-hoach-test.md) · [Mục lục](../README.md)

## Phạm vi đã triển khai

- SQLite local tại `data/render_video.db`.
- Alembic migration cho `Project`, `Character`, `Scene`, `Asset` và liên kết cảnh–nhân vật.
- Pydantic validation cho dữ liệu project.
- API tạo, liệt kê, đọc, cập nhật và xóa project.

Character, Scene và Asset đã có schema/database table nhưng endpoint chỉnh sửa riêng sẽ được thêm cùng bước storyboard và asset generation.

## Chuẩn bị database

Sau khi dependency hoặc migration thay đổi:

```bash
./scripts/setup_backend.sh
```

Lệnh này thực hiện:

```text
uv sync --frozen
→ alembic upgrade head
```

Database mặc định:

```text
data/render_video.db
```

Có thể đổi bằng biến `DATABASE_URL`.

## Chạy API

```bash
./scripts/dev.sh
```

Swagger: http://127.0.0.1:9000/docs

## Endpoints

| Method | Path | Chức năng |
|---|---|---|
| `POST` | `/api/projects` | Tạo project |
| `GET` | `/api/projects` | Liệt kê project mới nhất trước |
| `GET` | `/api/projects/{project_id}` | Đọc project và dữ liệu liên quan |
| `PATCH` | `/api/projects/{project_id}` | Cập nhật các trường được gửi |
| `DELETE` | `/api/projects/{project_id}` | Xóa project và dữ liệu con |

## Tạo project

```bash
curl --fail --silent \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
    "title": "Cô bé quàng khăn đỏ",
    "story": "Một cô bé mang giỏ bánh đi qua rừng để thăm bà.",
    "aspect_ratio": "16:9"
  }' \
  http://127.0.0.1:9000/api/projects
```

Giá trị `aspect_ratio` hợp lệ:

- `16:9`
- `9:16`
- `1:1`

Project mới luôn có trạng thái `draft`.

Backend tự đặt `language` thành `vi` và `visual_style` thành hoạt hình 2D vẽ tay. Hai trường này không thuộc request tạo/cập nhật project; gửi chúng trong request trả HTTP `422` để không thể đổi video sang ngôn ngữ hoặc phong cách khác.

## Liệt kê project

```bash
curl --fail --silent http://127.0.0.1:9000/api/projects
```

## Đọc project

Thay `<PROJECT_ID>` bằng `id` nhận được khi tạo:

```bash
curl --fail --silent \
  http://127.0.0.1:9000/api/projects/<PROJECT_ID>
```

Response chi tiết có ba danh sách:

```json
{
  "characters": [],
  "scenes": [],
  "assets": []
}
```

## Cập nhật project

```bash
curl --fail --silent \
  --request PATCH \
  --header 'Content-Type: application/json' \
  --data '{"aspect_ratio":"9:16"}' \
  http://127.0.0.1:9000/api/projects/<PROJECT_ID>
```

Không cho phép đặt trường thành `null` hoặc chuỗi rỗng. `language` và `visual_style` là thiết lập cố định, không thể cập nhật qua endpoint này.

## Xóa project

```bash
curl --fail --silent \
  --request DELETE \
  http://127.0.0.1:9000/api/projects/<PROJECT_ID>
```

Thành công trả HTTP `204`. Đọc lại ID đã xóa phải trả HTTP `404`.

## Migration

Chạy migration:

```bash
source scripts/env.sh
uv run --frozen alembic upgrade head
```

Xem revision hiện tại:

```bash
source scripts/env.sh
uv run --frozen alembic current
```

Không sửa cấu trúc SQLite thủ công. Mọi thay đổi schema phải có migration Alembic.