# Qwen3-VL grounding response
from pydantic import BaseModel


class GroundingResponse(BaseModel):
    """2D grounding 响应模型"""

    location: str
    base64_image: str | None
