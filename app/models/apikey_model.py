import uuid
from datetime import datetime
from enum import IntEnum

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class ExpiryDays(IntEnum):
    """API Key 过期天数档位枚举"""

    THIRTY_DAYS = 30
    SIXTY_DAYS = 60
    NINETY_DAYS = 90


# Shared properties
class APIKeyBase(SQLModel):
    email: EmailStr = Field(index=True, max_length=255)
    name: str = Field(min_length=1, max_length=255)  # API Key 名称/描述
    is_active: bool = True


# Properties to receive via API on creation
class APIKeyCreate(APIKeyBase):
    expiry_days: ExpiryDays = Field(description="API Key 过期天数档位：30、60、90天")


# Properties to receive via API on update
class APIKeyUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    expiry_days: ExpiryDays | None = Field(
        default=None, description="API Key 过期天数档位：30、60、90天"
    )


# Database model, database table inferred from class name
class APIKey(APIKeyBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=255)  # 实际的 API Key
    key_prefix: str = Field(max_length=10)  # API Key 前缀，用于快速识别
    expires_at: datetime | None = Field(
        default=None
    )  # 过期时间，由系统根据expiry_days计算
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_used_at: datetime | None = Field(default=None)  # 最后使用时间


# Properties to return via API
class APIKeyPublic(SQLModel):
    name: str
    key: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None


class APIKeysPublic(SQLModel):
    items: list[APIKeyPublic]
    count: int


# Properties to return when creating API key (包含完整的 key)
class APIKeyWithKey(APIKeyPublic):
    key: str  # 只在创建时返回完整的 key


# Properties to return for current API key info (用于 /user-info 端点)
class APIKeyInfo(SQLModel):
    """当前 API Key 的信息响应模型"""

    email: EmailStr
    key_name: str  # API Key 名称
    key_prefix: str  # API Key 前缀（用于识别，不暴露完整 key）
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
