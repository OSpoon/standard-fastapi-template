"""
Qwen3-VL 相关服务
"""

import ast
import base64
from io import BytesIO
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionUserMessageParam
from PIL import Image, ImageDraw

from app.core.config import settings
from app.utils import parse_json


def plot_bounding_boxes(
    im: Any,
    bounding_boxes: str | None,
    color: str = "red",
) -> str:
    """
    在图像上绘制边界框并返回base64字符串

    Args:
        im: PIL Image 对象
        bounding_boxes: 边界框JSON字符串
        color: 边界框颜色

    Returns:
        base64编码的图片字符串
    """
    # Load the image
    img = im.copy()  # 创建副本，避免修改原图
    width, height = img.size

    # Create a drawing object
    draw = ImageDraw.Draw(img)

    # Ensure we have a parsable string
    if bounding_boxes is None:
        bounding_boxes = "[]"

    # Parsing out the markdown fencing
    bounding_boxes = parse_json(bounding_boxes)

    try:
        json_output = ast.literal_eval(bounding_boxes)
    except Exception as _:
        end_idx = bounding_boxes.rfind('"}') + len('"}')
        truncated_text = bounding_boxes[:end_idx] + "]"
        json_output = ast.literal_eval(truncated_text)

    if not isinstance(json_output, list):
        json_output = [json_output]

    # Iterate over the bounding boxes
    for bounding_box in json_output:
        # Convert normalized coordinates to absolute coordinates
        abs_y1 = int(bounding_box["bbox_2d"][1] / 1000 * height)
        abs_x1 = int(bounding_box["bbox_2d"][0] / 1000 * width)
        abs_y2 = int(bounding_box["bbox_2d"][3] / 1000 * height)
        abs_x2 = int(bounding_box["bbox_2d"][2] / 1000 * width)

        if abs_x1 > abs_x2:
            abs_x1, abs_x2 = abs_x2, abs_x1

        if abs_y1 > abs_y2:
            abs_y1, abs_y2 = abs_y2, abs_y1

        # Draw the bounding box
        draw.rectangle(((abs_x1, abs_y1), (abs_x2, abs_y2)), outline=color, width=3)

    # 将图片转换为base64字符串
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=100)
    buffer.seek(0)
    base64_string = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return base64_string


async def inference_with_openai_api(
    base64_image: str,
    prompt: str,
    min_pixels: int = 64 * 32 * 32,
    max_pixels: int = 9800 * 32 * 32,
) -> str | None:
    """
    使用OpenAI API进行异步推理

    Args:
        base64_image: base64编码的图片
        prompt: 提示词
        min_pixels: 最小像素数
        max_pixels: 最大像素数

    Returns:
        API响应内容
    """
    client = AsyncOpenAI(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    messages: list[ChatCompletionUserMessageParam] = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    "min_pixels": min_pixels,  # type: ignore
                    "max_pixels": max_pixels,
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]
    completion = await client.chat.completions.create(
        model="qwen3-vl-235b-a22b-thinking",
        messages=messages,
    )
    return completion.choices[0].message.content


async def process_grounding_request(
    location: str, image_contents: bytes
) -> tuple[str, str]:
    """
    处理2D grounding请求

    Args:
        location: 要定位的位置描述
        image_contents: 图片内容字节

    Returns:
        (location, base64_image) 元组
    """
    # 调用API进行异步推理
    model_response = await inference_with_openai_api(
        base64_image=base64.b64encode(image_contents).decode("utf-8"),
        prompt=f"""
            Locate the position based on the location description and report the bbox coordinates in JSON format:
            Location description: {location}
            """,
    )

    # 处理图片并绘制边界框
    image = Image.open(BytesIO(image_contents))
    base64_image = plot_bounding_boxes(image, model_response)

    return location, base64_image
