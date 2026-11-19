"""API version 1 consolidated router."""

from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.baskets import router as baskets_router
from src.api.v1.homes import router as homes_router
from src.api.v1.pantry import router as pantry_router
from src.api.v1.products import router as products_router
from src.api.v1.stores import router as stores_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(homes_router)
api_v1_router.include_router(pantry_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(stores_router)
api_v1_router.include_router(baskets_router)
