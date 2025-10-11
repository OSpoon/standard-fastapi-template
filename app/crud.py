import uuid

from sqlmodel import Session, func, select

from app.models import Item, ItemCreate


def create_item(*, session: Session, item_in: ItemCreate) -> Item:
    db_item = Item.model_validate(item_in)
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
