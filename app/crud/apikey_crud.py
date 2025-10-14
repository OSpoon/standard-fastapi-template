from datetime import datetime

from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.apikey_model import APIKey, APIKeyCreate, APIKeyUpdate
from app.utils import calculate_expiry_date, generate_api_key


async def create_api_key(
    *, session: AsyncSession, api_key_create: APIKeyCreate
) -> APIKey:
    """
    创建新的 API Key (异步版本)
    """
    # 生成 API Key
    full_key, key_prefix = generate_api_key()

    # 根据天数档位计算过期时间
    expires_at = calculate_expiry_date(api_key_create.expiry_days)

    # 创建数据库记录
    db_api_key = APIKey(
        email=api_key_create.email,
        name=api_key_create.name,
        is_active=api_key_create.is_active,
        expires_at=expires_at,
        key=full_key,
        key_prefix=key_prefix,
    )

    session.add(db_api_key)
    await session.commit()
    await session.refresh(db_api_key)

    return db_api_key


async def get_api_key_by_key(*, session: AsyncSession, key: str) -> APIKey | None:
    """
    根据 key 字符串获取 API Key (异步版本)
    """
    statement = select(APIKey).where(APIKey.key == key)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_api_keys_by_email(
    *, session: AsyncSession, email: EmailStr, skip: int = 0, limit: int = 100
) -> tuple[list[APIKey], int]:
    """
    根据邮箱获取 API Keys 列表 (异步版本)
    """
    from sqlalchemy import func

    # 获取总数
    count_statement = (
        select(func.count()).select_from(APIKey).where(APIKey.email == email)
    )
    count_result = await session.execute(count_statement)
    total_count = count_result.scalar() or 0

    # 获取分页数据
    statement = select(APIKey).where(APIKey.email == email).offset(skip).limit(limit)
    result = await session.execute(statement)
    api_keys = list(result.scalars())

    return api_keys, total_count


async def update_api_key(
    *, session: AsyncSession, db_api_key: APIKey, api_key_update: APIKeyUpdate
) -> APIKey:
    """
    更新 API Key (异步版本)
    """
    api_key_data = api_key_update.model_dump(exclude_unset=True)
    db_api_key.sqlmodel_update(api_key_data)
    session.add(db_api_key)
    await session.commit()
    await session.refresh(db_api_key)
    return db_api_key


async def delete_api_key_by_key(*, session: AsyncSession, key: str) -> bool:
    """
    删除 API Key (异步版本)
    """
    db_api_key = await get_api_key_by_key(session=session, key=key)
    if not db_api_key:
        return False

    await session.delete(db_api_key)
    await session.commit()
    return True


async def update_last_used(*, session: AsyncSession, api_key: APIKey) -> None:
    """
    更新 API Key 的最后使用时间 (异步版本)
    """
    api_key.last_used_at = datetime.now()
    session.add(api_key)
    await session.commit()
