import secrets
import string
import uuid
from datetime import datetime, timedelta

from pydantic import EmailStr
from sqlmodel import Session, select

from app.core.config import settings
from app.models.apikey_model import APIKey, APIKeyCreate, APIKeyUpdate, ExpiryDays


def generate_api_key() -> tuple[str, str]:
    """
    生成 API Key 和其前缀
    格式: sk-<random_string>
    """
    # 使用项目设置中的前缀，如果没有设置则使用默认前缀
    prefix = getattr(settings, "API_KEY_PREFIX", "sk")

    # 生成随机字符串
    alphabet = string.ascii_letters + string.digits
    random_string = "".join(secrets.choice(alphabet) for _ in range(48))

    # 组合完整的 API Key
    full_key = f"{prefix}-{random_string}"

    return full_key, prefix


def calculate_expiry_date(expiry_days: ExpiryDays) -> datetime:
    """
    根据天数档位计算过期时间
    """
    return datetime.now() + timedelta(days=expiry_days.value)


def create_api_key(*, session: Session, api_key_create: APIKeyCreate) -> APIKey:
    """
    创建新的 API Key
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
    session.commit()
    session.refresh(db_api_key)

    return db_api_key


def get_api_key_by_id(*, session: Session, api_key_id: uuid.UUID) -> APIKey | None:
    """
    根据 ID 获取 API Key
    """
    statement = select(APIKey).where(APIKey.id == api_key_id)
    return session.exec(statement).first()


def get_api_key_by_key(*, session: Session, key: str) -> APIKey | None:
    """
    根据 key 字符串获取 API Key (用于验证)
    """
    statement = select(APIKey).where(APIKey.key == key)
    return session.exec(statement).first()


def get_api_keys_by_email(
    *, session: Session, email: EmailStr, skip: int = 0, limit: int = 100
) -> tuple[list[APIKey], int]:
    """
    根据邮箱获取 API Keys 列表
    """
    statement = select(APIKey).where(APIKey.email == email).offset(skip).limit(limit)
    api_keys = list(session.exec(statement).all())

    # 获取总数
    count_statement = select(APIKey).where(APIKey.email == email)
    count = len(list(session.exec(count_statement).all()))

    return api_keys, count


def update_api_key(
    *, session: Session, db_api_key: APIKey, api_key_update: APIKeyUpdate
) -> APIKey:
    """
    更新 API Key 信息
    """
    api_key_data = api_key_update.model_dump(exclude_unset=True)

    # 处理expiry_days字段，转换为expires_at
    if "expiry_days" in api_key_data:
        expiry_days = api_key_data.pop("expiry_days")
        db_api_key.expires_at = calculate_expiry_date(expiry_days)

    # 更新其他字段
    for field, value in api_key_data.items():
        setattr(db_api_key, field, value)

    # 更新修改时间
    db_api_key.updated_at = datetime.now()

    session.add(db_api_key)
    session.commit()
    session.refresh(db_api_key)

    return db_api_key


def delete_api_key(*, session: Session, api_key_id: uuid.UUID) -> bool:
    """
    删除 API Key
    """
    statement = select(APIKey).where(APIKey.id == api_key_id)
    api_key = session.exec(statement).first()

    if not api_key:
        return False

    session.delete(api_key)
    session.commit()

    return True


def delete_api_key_by_key(*, session: Session, key: str) -> bool:
    """
    根据 key 删除 API Key
    """
    statement = select(APIKey).where(APIKey.key == key)
    api_key = session.exec(statement).first()
    if not api_key:
        return False
    session.delete(api_key)
    session.commit()
    return True


def update_last_used(*, session: Session, api_key: APIKey) -> None:
    """
    更新 API Key 最后使用时间
    """
    api_key.last_used_at = datetime.now()
    session.add(api_key)
    session.commit()


def is_api_key_valid(api_key: APIKey) -> bool:
    """
    检查 API Key 是否有效
    """
    # 检查是否激活
    if not api_key.is_active:
        return False

    # 检查是否过期
    if api_key.expires_at and api_key.expires_at < datetime.now():
        return False

    return True
