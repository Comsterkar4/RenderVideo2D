# 07 — Image-to-video với Wan2.2

[← FFmpeg](06-dung-video-ffmpeg.md) · [Mục lục](../README.md) · [Tiếp theo: Kế hoạch test →](08-ke-hoach-test.md)

## Thời điểm triển khai

Chỉ tích hợp Wan2.2 sau khi pipeline sau chạy ổn định:

```text
truyện → storyboard → ảnh → ViViBe → FFmpeg → MP4
```

Wan2.2 không phải điều kiện hoàn thành MVP.

Repository chính thức: [Wan-Video/Wan2.2](https://github.com/Wan-Video/Wan2.2).

## Cách tích hợp

Ưu tiên gọi Wan2.2 qua workflow ComfyUI thay vì chạy thêm một server riêng:

```text
ảnh cảnh đã duyệt
+ motion prompt
+ duration/config
→ ComfyUI workflow Wan2.2
→ clip cảnh
→ FFmpeg timeline
```

Source và model phải nằm trong project:

```text
third_party/Wan2.2/
models/comfyui/wan22/
workflows/scene-video-wan22.v1.json
```

Không tải model trước khi xác nhận GPU/VRAM và dung lượng ổ đĩa đáp ứng workflow đã chọn.

## Interface

```python
class SceneAnimator(Protocol):
    async def animate(
        self,
        image_path: Path,
        motion_prompt: str,
        duration_seconds: float,
    ) -> GeneratedAsset:
        ...
```

Implementations:

- `KenBurnsAnimator`: FFmpeg, dùng cho MVP.
- `WanAnimator`: ComfyUI + Wan2.2.

## Quy tắc prompt

Ảnh đã chứa nhân vật, phong cách và bố cục. Motion prompt tập trung vào:

- Chuyển động nhân vật.
- Chuyển động môi trường.
- Hướng/tốc độ camera.
- Các chuyển động cần tránh.

Ví dụ:

```text
The girl walks slowly along the forest path. Her red cape moves gently
in the wind. The camera tracks from the side. Stable face and clothing,
subtle natural movement, no camera shake.
```

## Test module

1. Dùng một ảnh cảnh đã được duyệt.
2. Tạo clip ngắn ở cấu hình thấp nhất phù hợp.
3. Lưu prompt, seed, model và workflow version.
4. Kiểm tra clip phát được bằng `ffprobe` và quan sát thực tế.
5. Xác nhận frame đầu không lệch đáng kể so với ảnh tham chiếu.
6. Xác nhận khuôn mặt, trang phục và số lượng nhân vật không biến dạng nghiêm trọng.
7. Ghép clip với narration và kiểm tra đồng bộ.

Nếu test thất bại, project vẫn phải render được bằng `KenBurnsAnimator`. Hệ thống phải báo lỗi Wan rõ ràng; không đánh dấu clip dự phòng là output của Wan.