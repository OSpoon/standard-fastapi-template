from fastapi import APIRouter

from app.api.v1.endpoints import (
    items,
    utils,
)

api_router_v1 = APIRouter()

api_router_v1.include_router(items.router, prefix="/items", tags=["items"])
api_router_v1.include_router(utils.router, prefix="/utils", tags=["utils"])
