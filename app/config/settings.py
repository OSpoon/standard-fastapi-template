"""
应用程序设置
"""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用程序设置类"""

    PRODUCTION: bool = os.getenv("PRODUCTION", "false").lower() in ("true", "1")
    LOG_FILE_PATH: str = os.getenv("LOG_FILE_PATH", "service.log")


settings = Settings()
