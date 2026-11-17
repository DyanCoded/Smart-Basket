"""API version 1 consolidated router."""

from fastapi import APIRouter

from src.api.v1.products import router as products_router
from src.api.v1.stores import router as stores_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(products_router)
api_v1_router.include_router(stores_router)
