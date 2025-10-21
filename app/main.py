from api_exception import (
    ResponseFormat,
    add_file_handler,
    logger,
    register_exception_handlers,
)
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router_v1
from app.core.config import settings


def generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


# 根据环境设置日志级别
if settings.ENVIRONMENT == "production":
    logger.setLevel("ERROR")
else:
    logger.setLevel("INFO")

# 添加文件日志处理器
add_file_handler(settings.LOG_FILE_PATH, level=logger.level)


# 初始化 FastAPI 应用


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=generate_unique_id,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(api_router_v1, prefix=settings.API_V1_STR)


# 注册异常处理器
register_exception_handlers(
    app=app,
    response_format=ResponseFormat.RESPONSE_MODEL,
    log_traceback=not settings.ENVIRONMENT == "production",
    log_traceback_unhandled_exception=not settings.ENVIRONMENT == "production",
)
