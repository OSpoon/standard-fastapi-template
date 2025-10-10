"""
User相关的数据模型
"""

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """用户响应模型"""

    id: int = Field(..., examples=[1], description="Unique identifier of the user")
    username: str = Field(
        ..., examples=["Micheal Alice"], description="Username or full name of the user"
    )
