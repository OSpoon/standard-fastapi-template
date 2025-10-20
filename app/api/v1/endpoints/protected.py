"""
受保护的 API 接口示例，演示如何使用 API Key 验证
"""

from api_exception import ResponseModel
from fastapi import APIRouter, Depends

from app.api.deps import CurrentAPIKeyAsync
from app.core.rate_limit import rate_limit_dependency
from app.models.apikey_model import APIKeyInfo
from app.models.common_model import Message

router = APIRouter()


@router.get("/protected", response_model=ResponseModel[Message])
async def protected_endpoint(
    current_api_key: CurrentAPIKeyAsync,
    _: None = Depends(rate_limit_dependency),
) -> ResponseModel[Message]:
    """
    受保护的端点示例，需要有效的 API Key，并受频率限制
    """
    return ResponseModel(
        data=Message(message=f"Hello! Your API Key belongs to: {current_api_key.email}")
    )


@router.get("/user-info", response_model=ResponseModel[APIKeyInfo])
async def get_api_key_info(
    current_api_key: CurrentAPIKeyAsync,
    _: None = Depends(rate_limit_dependency),
) -> ResponseModel[APIKeyInfo]:
    """
    获取当前 API Key 的信息
    """
    return ResponseModel(
        data=APIKeyInfo(
            email=current_api_key.email,
            key_name=current_api_key.name,
            key_prefix=current_api_key.key_prefix,
            is_active=current_api_key.is_active,
            created_at=current_api_key.created_at,
            last_used_at=current_api_key.last_used_at,
            expires_at=current_api_key.expires_at,
        )
    )
