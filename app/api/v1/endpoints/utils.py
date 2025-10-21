from api_exception import ResponseModel, logger
from fastapi import APIRouter

router = APIRouter()


@router.get("/health-check/")
async def health_check() -> ResponseModel[bool]:
    """健康检查端点，检查API是否运行"""
    logger.info("Health check request received")
    return ResponseModel(data=True)
