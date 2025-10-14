from sqlmodel.ext.asyncio.session import AsyncSession

from app.crud import apikey_crud
from app.models.apikey_model import APIKeyCreate


async def init_db(session: AsyncSession) -> None:
    _, total_count = await apikey_crud.get_api_keys_by_email(
        session=session, email="admin@example.com"
    )
    if total_count == 0:
        await apikey_crud.create_api_key(
            session=session,
            api_key_create=APIKeyCreate(
                email="admin@example.com",
                name="APIKey",
                is_active=True,
                expiry_days=90,
            ),
        )
