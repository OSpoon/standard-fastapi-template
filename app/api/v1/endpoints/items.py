import uuid

from api_exception import (
    APIException,
    APIResponse,
    ResponseModel,
)
from fastapi import APIRouter

from app import crud
from app.api.deps import SessionDep
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models import ItemCreate, ItemPublic, ItemsPublic

router = APIRouter()


@router.post(
    "/",
    response_model=ResponseModel[ItemPublic],
    responses=APIResponse.default(),  # type: ignore
    description="Create new item.",
)
def create_item(
    *, session: SessionDep, item_in: ItemCreate
) -> ResponseModel[ItemPublic]:
    """
    Create new item.
    """
    item = crud.create_item(session=session, item_in=item_in)
    return ResponseModel(data=ItemPublic.model_validate(item))


@router.get(
    "/",
    response_model=ResponseModel[ItemsPublic],
    responses=APIResponse.default(),  # type: ignore
    description="Retrieve items.",
)
def read_items(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> ResponseModel[ItemsPublic]:
    """
    Retrieve items.
    """

    items, count = crud.get_items(session=session, skip=skip, limit=limit)
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
def read_item(session: SessionDep, id: uuid.UUID) -> ResponseModel[ItemPublic]:
    """
    Get item by ID.
    """
    item = crud.get_item(session=session, item_id=id)
    if not item:
        raise APIException(
            error_code=SFExceptionCode.ITEM_NOT_FOUND,
            http_status_code=404,
        )
    return ResponseModel(data=ItemPublic.model_validate(item) if item else None)
