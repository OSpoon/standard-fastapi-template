from api_exception import (
    APIException,
    APIResponse,
    ResponseFormat,
    ResponseModel,
    logger,
    register_exception_handlers,
)
from fastapi import FastAPI, Path

from app.config import settings
from app.exceptions import SFExceptionCode
from app.models import UserResponse

# 初始化 FastAPI 应用
api_app = FastAPI(title="Public API Service", version="1.0.0")

# 注册异常处理器
register_exception_handlers(
    app=api_app,
    response_format=ResponseFormat.RFC7807,
    log_traceback=not settings.PRODUCTION,
    log_traceback_unhandled_exception=not settings.PRODUCTION,
)


@api_app.get(
    "/ping",
    response_model=ResponseModel,
    responses=APIResponse.default(),  # type: ignore
    description="Ping endpoint to check if the API is running.",
)
async def ping() -> ResponseModel[str]:
    """Ping端点，检查API是否运行"""
    logger.info("Ping request received")
    return ResponseModel(data="pong")


# 定义GET /user/{user_id}路由
@api_app.get(
    "/user/{user_id}",
    response_model=ResponseModel[UserResponse],
    responses=APIResponse.default(),  # type: ignore
    description="Get user information by user ID.",
)
async def get_user(
    user_id: int = Path(..., description="The ID of the user"),
) -> ResponseModel[UserResponse]:
    """根据用户ID获取用户信息"""
    logger.info("Get user request received")
    if user_id == 1:
        raise APIException(
            error_code=SFExceptionCode.USER_NOT_FOUND,
            http_status_code=404,
        )
    if user_id == 2:
        raise TypeError("Invalid type provided.")
    if user_id == 3:
        raise RuntimeError("Unexpected runtime issue.")

    data = UserResponse(id=user_id, username="John Doe")
    return ResponseModel(data=data)
