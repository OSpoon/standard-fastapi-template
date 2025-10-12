import uuid

from api_exception import (
    APIException,
    APIResponse,
    ResponseModel,
)
from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.crud import item_crud
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models.common_model import Message
from app.models.item_model import ItemCreate, ItemPublic, ItemsPublic, ItemUpdate

router = APIRouter()


@router.post(
    "/",
    response_model=ResponseModel[ItemPublic],
    responses=APIResponse.default(),  # type: ignore
    description="Create new item.",
)
def create_item(
    *, session: SessionDep, current_user: CurrentUser, item_in: ItemCreate
) -> ResponseModel[ItemPublic]:
    """
    Create new item.
    """
    item = item_crud.create_item(
        session=session, item_in=item_in, owner_id=current_user.id
    )
    return ResponseModel(data=ItemPublic.model_validate(item))


@router.get(
    "/",
    response_model=ResponseModel[ItemsPublic],
    responses=APIResponse.default(),  # type: ignore
    description="Retrieve items.",
)
def read_items(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> ResponseModel[ItemsPublic]:
    """
    Retrieve items.
    """
    if current_user.is_superuser:
        items, count = item_crud.get_items(session=session, skip=skip, limit=limit)
    else:
        items, count = item_crud.get_items_by_owner(
            session=session, owner_id=current_user.id, skip=skip, limit=limit
        )
    if not items:
        raise APIException(
            error_code=SFExceptionCode.ITEM_NOT_FOUND,
            http_status_code=404,
        )
    return ResponseModel(data=ItemsPublic(items=items, count=count))


@router.get(
    "/{id}",
    response_model=ResponseModel[ItemPublic],
    responses=APIResponse.default(),  # type: ignore
    description="Retrieve item by ID.",
)
def read_item(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> ResponseModel[ItemPublic]:
    """
    Get item by ID.
    """
    item = item_crud.get_item(session=session, item_id=id)
    if not item:
        raise APIException(
            error_code=SFExceptionCode.ITEM_NOT_FOUND,
            http_status_code=404,
        )
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise APIException(
            error_code=SFExceptionCode.INSUFFICIENT_PRIVILEGES,
            http_status_code=400,
        )
    return ResponseModel(data=ItemPublic.model_validate(item) if item else None)


@router.put(
    "/{id}",
    response_model=ResponseModel[ItemPublic],
    responses=APIResponse.default(),  # type: ignore
    description="Update an item.",
)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> ResponseModel[ItemPublic]:
    """
    Update an item.
    """
    item = item_crud.get_item(session=session, item_id=id)
    if not item:
        raise APIException(
            error_code=SFExceptionCode.ITEM_NOT_FOUND,
            http_status_code=404,
        )
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise APIException(
            error_code=SFExceptionCode.INSUFFICIENT_PRIVILEGES,
            http_status_code=400,
        )
    item = item_crud.update_item(session=session, db_item=item, item_in=item_in)
    return ResponseModel(data=ItemPublic.model_validate(item))


@router.delete(
    "/{id}",
    response_model=ResponseModel[Message],
    responses=APIResponse.default(),  # type: ignore
    description="Delete an item.",
)
def delete_item(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> ResponseModel[Message]:
    """
    Delete an item.
    """
    item = item_crud.get_item(session=session, item_id=id)
    if not item:
        raise APIException(
            error_code=SFExceptionCode.ITEM_NOT_FOUND,
            http_status_code=404,
        )
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise APIException(
            error_code=SFExceptionCode.INSUFFICIENT_PRIVILEGES,
            http_status_code=400,
        )
    item_crud.delete_item(session=session, item_id=id)
    return ResponseModel(data=Message(message="Item deleted successfully"))
