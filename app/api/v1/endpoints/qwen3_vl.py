"""
Qwen3-VL API 端点
"""

from api_exception import ResponseModel
from fastapi import APIRouter, File, UploadFile

from app.models.common_model import GroundingResponse
from app.services.qwen3_vl_service import process_grounding_request

router = APIRouter()


@router.post(
    "/grounding/2d",
    response_model=ResponseModel[GroundingResponse],
)
async def grounding_2d(
    location: str, file: UploadFile = File(...)
) -> ResponseModel[GroundingResponse]:
    """
    2D grounding 端点

    根据给定的短语在图像中定位对象并返回带有边界框的base64编码图片
    """
    contents = await file.read()
    location, base64_image = await process_grounding_request(location, contents)

    return ResponseModel(
        data=GroundingResponse(
            location=location,
            base64_image=base64_image,
        )
    )
