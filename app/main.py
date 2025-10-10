from api_exception import add_file_handler, logger
from fastapi import FastAPI

from app.config import settings
from app.routers import api_app

# 根据环境设置日志级别
if settings.PRODUCTION:
    logger.setLevel("ERROR")
else:
    logger.setLevel("INFO")

# 添加文件日志处理器
add_file_handler(settings.LOG_FILE_PATH, level=logger.level)

# 初始化 FastAPI 应用
app = FastAPI(title="Standard FastAPI Template", docs_url=None, redoc_url=None)

# 挂载API路由
app.mount("/api/v1", api_app)
