from fastapi import APIRouter

from app.api.v1.endpoints import (
    items,
    login,
    users,
    utils,
)

api_router_v1 = APIRouter()

api_router_v1.include_router(items.router, prefix="/items", tags=["items"])
api_router_v1.include_router(login.router, prefix="/login", tags=["login"])
api_router_v1.include_router(users.router, prefix="/users", tags=["users"])
api_router_v1.include_router(utils.router, prefix="/utils", tags=["utils"])
