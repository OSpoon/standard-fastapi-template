from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from api_exception import (
    ResponseFormat,
    add_file_handler,
    logger,
    register_exception_handlers,
)
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_limiter import FastAPILimiter
from starlette.middleware.cors import CORSMiddleware

from app.api.deps import get_redis_client
from app.api.v1.api import api_router_v1
from app.core.config import settings
from app.core.rate_limit import (
    http_default_callback,
    ws_default_callback,
)

# 根据环境设置日志级别
if settings.ENVIRONMENT == "production":
    logger.setLevel("ERROR")
else:
    logger.setLevel("INFO")

# 添加文件日志处理器
add_file_handler(settings.LOG_FILE_PATH, level=logger.level)


# 初始化 FastAPI 应用


# 启动前初始化
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Initializing FastAPI...")
    redis_client = await get_redis_client()
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    await FastAPILimiter.init(
        redis_client,
        http_callback=http_default_callback,
        ws_callback=ws_default_callback,
    )
    yield
    await FastAPICache.clear()
    await FastAPILimiter.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
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
