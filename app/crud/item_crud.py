import uuid

from api_exception import (
    APIException,
)
from sqlmodel import Session, func, select

from app.exceptions.sf_exceptions import SFExceptionCode
from app.models.item_model import Item, ItemCreate, ItemUpdate


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def get_item(*, session: Session, item_id: uuid.UUID) -> Item | None:
    return session.get(Item, item_id)


def get_items(
    *, session: Session, skip: int = 0, limit: int = 100
) -> tuple[list[Item], int]:
    count_statement = select(func.count()).select_from(Item)
    count = session.exec(count_statement).one()
    statement = select(Item).offset(skip).limit(limit)
    items = session.exec(statement).all()
    return list(items), count


def get_items_by_owner(
    *, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> tuple[list[Item], int]:
    count_statement = (
        select(func.count()).select_from(Item).where(Item.owner_id == owner_id)
    )
    count = session.exec(count_statement).one()
    statement = select(Item).where(Item.owner_id == owner_id).offset(skip).limit(limit)
    items = session.exec(statement).all()
    return list(items), count


def update_item(*, session: Session, db_item: Item, item_in: ItemUpdate) -> Item:
    item_data = item_in.model_dump(exclude_unset=True)
    db_item.sqlmodel_update(item_data)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def delete_item(*, session: Session, item_id: uuid.UUID) -> None:
    item = session.get(Item, item_id)
    if not item:
        raise APIException(
            error_code=SFExceptionCode.ITEM_NOT_FOUND,
            http_status_code=404,
        )
    session.delete(item)
    session.commit()
