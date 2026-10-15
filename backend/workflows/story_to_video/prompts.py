import json

from backend.config import VIDEO_LANGUAGE, VIDEO_LANGUAGE_NAME, VISUAL_STYLE
from backend.models import Project
from backend.workflows.story_to_video.schemas import StoryboardPlan

SYSTEM_PROMPT = """Bạn là biên kịch và storyboard artist cho video truyện kể.
Nhiệm vụ duy nhất của bạn là chuyển truyện thành JSON đúng schema được cung cấp.
Không thêm markdown, giải thích hoặc trường ngoài schema.
Giữ nguyên ý nghĩa truyện. Không thêm năng lực, bộ phận cơ thể, đồ vật hoặc tình tiết trái với nguồn.
Khi nguồn không mô tả ngoại hình, chỉ bổ sung chi tiết đơn giản, phù hợp tuổi và giải phẫu tự nhiên.
Lời kể luôn phải bằng tiếng Việt. Không dịch hoặc chuyển lời kể sang ngôn ngữ khác.
Mỗi cảnh có đúng một hành động chính, kéo dài 4 đến 10 giây và dùng tối đa 3 nhân vật.
ID dùng chữ thường ASCII và dấu gạch dưới. Mô tả ngoại hình nhân vật phải ổn định giữa các cảnh.
Mọi nhân vật được nhắc trong narration, image_prompt hoặc motion_prompt phải có ID trong character_ids.
image_prompt không được mô tả nhân vật ngoài character_ids.
"""


def build_storyboard_prompt(project: Project) -> str:
    schema = json.dumps(StoryboardPlan.model_json_schema(), ensure_ascii=False)
    return f"""Hãy tạo storyboard cho project sau.

Tiêu đề: {project.title}
Ngôn ngữ lời kể bắt buộc: {VIDEO_LANGUAGE_NAME} ({VIDEO_LANGUAGE})
Phong cách hình ảnh bắt buộc: {VISUAL_STYLE}
Tỷ lệ khung hình: {project.aspect_ratio}

Truyện nguồn:
---
{project.story}
---

Yêu cầu:
- Trả title phù hợp với truyện.
- visual_style phải giữ đúng phong cách bắt buộc ở trên.
- narration, appearance và location phải bằng tiếng Việt để hiển thị cho người dùng.
- prompt_fragment phải bằng tiếng Anh và chỉ mô tả thiết kế hình ảnh ổn định của nhân vật.
- image_prompt phải hoàn toàn bằng tiếng Anh, tự chứa địa điểm, hành động, góc máy và nhấn mạnh phong cách 2D hand-drawn animation.
- motion_prompt và sound_effects phải bằng tiếng Anh.
- Tạo Character Bible trước rồi tham chiếu ID nhân vật trong từng cảnh.
- Không thêm cánh, phép thuật, vũ khí hoặc phụ kiện nếu truyện không nêu.
- Trang phục trẻ em phải phù hợp tuổi và hoạt động; không dùng giày cao gót.
- Scene order phải liên tục từ 1.
- Chia cảnh tại nơi hành động hoặc địa điểm thay đổi; location phải đúng với hành động.
- narration ngắn gọn, tự nhiên và phù hợp thời lượng cảnh.
- character_ids chỉ bao gồm nhân vật thực sự nhìn thấy trong keyframe.
- image_prompt chỉ mô tả keyframe của một khoảnh khắc; motion_prompt chỉ mô tả chuyển động và camera.
- sound_effects là danh sách tên hiệu ứng ngắn bằng tiếng Anh.

JSON Schema bắt buộc:
{schema}
"""
