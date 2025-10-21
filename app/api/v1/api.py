from fastapi import APIRouter

from app.api.v1.endpoints import (
    qwen3_vl,
    utils,
)

api_router_v1 = APIRouter()

api_router_v1.include_router(qwen3_vl.router, prefix="/qwen3-vl", tags=["qwen3-vl"])
api_router_v1.include_router(utils.router, prefix="/utils", tags=["utils"])
