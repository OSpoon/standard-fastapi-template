from fastapi import APIRouter

from app.api.v1.endpoints import (
    apikey,
    protected,
    utils,
)

api_router_v1 = APIRouter()

api_router_v1.include_router(apikey.router, prefix="/apikey", tags=["apikey"])
api_router_v1.include_router(protected.router, prefix="/protected", tags=["protected"])
api_router_v1.include_router(utils.router, prefix="/utils", tags=["utils"])
