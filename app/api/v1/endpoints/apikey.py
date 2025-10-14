from api_exception import APIException, ResponseModel
from fastapi import APIRouter, Depends, Query
from fastapi_cache.decorator import cache
from pydantic import EmailStr

from app.api.deps import AsyncSessionDep
from app.core.rate_limit import rate_limit_dependency
from app.crud import apikey_crud
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models.apikey_model import (
    APIKeyCreate,
    APIKeyPublic,
    APIKeysPublic,
    APIKeyUpdate,
    APIKeyWithKey,
)
from app.models.common_model import Message
from app.utils import (
    generate_delete_apikey_email,
    generate_new_apikey_email,
    generate_update_apikey_email,
    send_email,
)

router = APIRouter()


@router.post("/", response_model=ResponseModel[APIKeyWithKey])
async def create_api_key(
    *,
    session: AsyncSessionDep,
    api_key_in: APIKeyCreate,
    _: None = Depends(rate_limit_dependency),
) -> ResponseModel[APIKeyWithKey]:
    """
    创建新的 API Key
    """
    try:
        api_key = await apikey_crud.create_api_key(
            session=session, api_key_create=api_key_in
        )

        # 发送邮件通知用户
        try:
            expires_info = (
                api_key.expires_at.strftime("%Y年%m月%d日 %H:%M:%S")
                if api_key.expires_at
                else "永不过期"
            )
            email_data = generate_new_apikey_email(
                email_to=api_key.email,
                api_key_name=api_key.name,
                api_key=api_key.key,
                created_at=api_key.created_at.strftime("%Y年%m月%d日 %H:%M:%S"),
                expires_info=expires_info,
            )
            send_email(
                email_to=api_key.email,
                subject=email_data.subject,
                html_content=email_data.html_content,
            )
        except Exception as e:
            # 邮件发送失败不影响 API Key 创建，只记录日志
            from api_exception import logger

            logger.warning(f"Failed to send API key creation email: {e}")

        return ResponseModel(data=APIKeyWithKey.model_validate(api_key))
    except Exception:
        raise APIException(
            error_code=SFExceptionCode.CREATE_APIKEY_ERROR,
            http_status_code=500,
        )


@router.get("/", response_model=ResponseModel[APIKeysPublic])
@cache(expire=10)
async def read_api_keys(
    session: AsyncSessionDep,
    email: EmailStr = Query(..., description="邮箱地址"),
    skip: int = 0,
    limit: int = 100,
) -> ResponseModel[APIKeysPublic]:
    """
    根据邮箱获取 API Keys 列表
    """
    api_keys, count = await apikey_crud.get_api_keys_by_email(
        session=session, email=email, skip=skip, limit=limit
    )

    # 只返回指定字段，包含 key
    items = [
        APIKeyPublic(
            id=api_key.id,
            email=api_key.email,
            name=api_key.name,
            is_active=api_key.is_active,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
            last_used_at=api_key.last_used_at,
            key=api_key.key,
        )
        for api_key in api_keys
    ]
    return ResponseModel(
        data=APIKeysPublic(
            items=items,
            count=count,
        )
    )


@router.patch("/{api_key_id}", response_model=ResponseModel[APIKeyPublic])
async def update_api_key(
    *,
    session: AsyncSessionDep,
    api_key_id: str,
    api_key_in: APIKeyUpdate,
) -> ResponseModel[APIKeyPublic]:
    """
    更新 API Key 信息
    """
    api_key = await apikey_crud.get_api_key_by_key(session=session, key=api_key_id)
    if not api_key:
        raise APIException(
            error_code=SFExceptionCode.APIKEY_NOT_FOUND,
            http_status_code=404,
        )

    try:
        updated_api_key = await apikey_crud.update_api_key(
            session=session, db_api_key=api_key, api_key_update=api_key_in
        )

        # 发送邮件通知用户API Key已更新
        try:
            # 生成更新变更摘要
            changes = []
            api_key_data = api_key_in.model_dump(exclude_unset=True)
            if "name" in api_key_data:
                changes.append(f"• 名称更新为: {api_key_data['name']}")
            if "is_active" in api_key_data:
                status = "激活" if api_key_data["is_active"] else "停用"
                changes.append(f"• 状态更新为: {status}")
            if "expiry_days" in api_key_data:
                changes.append(f"• 有效期更新为: {api_key_data['expiry_days']}天")

            changes_summary = "\n".join(changes) if changes else "• 基本信息更新"

            expires_info = (
                updated_api_key.expires_at.strftime("%Y年%m月%d日 %H:%M:%S")
                if updated_api_key.expires_at
                else "永不过期"
            )

            email_data = generate_update_apikey_email(
                email_to=updated_api_key.email,
                api_key_name=updated_api_key.name,
                api_key_prefix=updated_api_key.key_prefix,
                updated_at=updated_api_key.updated_at.strftime("%Y年%m月%d日 %H:%M:%S"),
                new_expires_info=expires_info,
                status="激活" if updated_api_key.is_active else "停用",
                changes_summary=changes_summary,
            )
            send_email(
                email_to=updated_api_key.email,
                subject=email_data.subject,
                html_content=email_data.html_content,
            )
        except Exception as e:
            # 邮件发送失败不影响API调用，只记录日志
            from api_exception import logger

            logger.warning(f"Failed to send API key update email: {e}")

        # 只返回指定字段，包含 key
        api_key_public = APIKeyPublic(
            id=updated_api_key.id,
            email=updated_api_key.email,
            name=updated_api_key.name,
            is_active=updated_api_key.is_active,
            expires_at=updated_api_key.expires_at,
            created_at=updated_api_key.created_at,
            updated_at=updated_api_key.updated_at,
            last_used_at=updated_api_key.last_used_at,
            key=updated_api_key.key,
        )
        return ResponseModel(data=api_key_public)
    except Exception:
        raise APIException(
            error_code=SFExceptionCode.UPDATE_APIKEY_ERROR,
            http_status_code=500,
        )


@router.delete("/{api_key_id}", response_model=ResponseModel[Message])
async def delete_api_key(
    *, session: AsyncSessionDep, api_key_id: str
) -> ResponseModel[Message]:
    """
    删除 API Key
    """
    # 先获取API Key信息用于发送邮件
    api_key = await apikey_crud.get_api_key_by_key(session=session, key=api_key_id)
    if not api_key:
        raise APIException(
            error_code=SFExceptionCode.APIKEY_NOT_FOUND,
            http_status_code=404,
        )

    # 保存邮件需要的信息
    email_to = api_key.email
    api_key_name = api_key.name
    api_key_prefix = api_key.key_prefix
    created_at = api_key.created_at.strftime("%Y年%m月%d日 %H:%M:%S")
    last_used_info = (
        api_key.last_used_at.strftime("%Y年%m月%d日 %H:%M:%S")
        if api_key.last_used_at
        else "从未使用"
    )

    # 删除API Key
    success = await apikey_crud.delete_api_key_by_key(session=session, key=api_key_id)
    if not success:
        raise APIException(
            error_code=SFExceptionCode.APIKEY_NOT_FOUND,
            http_status_code=404,
        )

    # 发送邮件通知用户API Key已删除
    try:
        from datetime import datetime

        email_data = generate_delete_apikey_email(
            email_to=email_to,
            api_key_name=api_key_name,
            api_key_prefix=api_key_prefix,
            deleted_at=datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),
            created_at=created_at,
            last_used_info=last_used_info,
        )
        send_email(
            email_to=email_to,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    except Exception as e:
        # 邮件发送失败不影响API调用，只记录日志
        from api_exception import logger

        logger.warning(f"Failed to send API key deletion email: {e}")

    return ResponseModel(data=Message(message="API Key 删除成功"))
