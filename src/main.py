"""Smart Basket FastAPI application entrypoint."""

from __future__ import annotations

import logging
from typing import Annotated, Any

import yaml
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from src.api.v1.router import api_v1_router
from src.api.v1.schemas import ErrorResponse
from src.core.database import get_db
from src.services import catalog_service

logger = logging.getLogger("smart_basket")

OPENAPI_TAGS = [
    {
        "name": "products",
        "description": (
            "Universal grocery catalog search, category filtering, "
            "barcode lookups, and packaging metadata."
        ),
    },
    {
        "name": "prices",
        "description": (
            "Active store-level product pricing, promotional discounts, "
            "and branch-level inventory status."
        ),
    },
    {
        "name": "history",
        "description": (
            "Chronological price observation timeseries across configurable "
            "date windows for inflation and price trend charting."
        ),
    },
    {
        "name": "intelligence",
        "description": (
            "Analytical trend intelligence, inflation metrics, and promotional "
            "deal veracity scoring."
        ),
    },
    {
        "name": "stores",
        "description": (
            "Supermarket chains, retail brands, and physical branch locations."
        ),
    },
    {
        "name": "baskets",
        "description": (
            "Multi-store basket total calculations and Smart Mode split "
            "optimization engine."
        ),
    },
    {
        "name": "auth",
        "description": "User registration, authentication, and JWT profile access.",
    },
    {
        "name": "homes",
        "description": (
            "Collaborative household spaces, pantry sharing, and role-based "
            "memberships."
        ),
    },
    {
        "name": "pantry",
        "description": (
            "Household pantry inventory tracking, offline SQLite delta-sync, "
            "and automated SmartBasket replenishment."
        ),
    },
    {
        "name": "health",
        "description": "Service liveness and readiness monitoring endpoints.",
    },
]

API_DESCRIPTION = """
# Smart Basket API 🛒

Welcome to the **Smart Basket API**, an automated price intelligence
and multi-store basket optimization platform designed to eliminate
the manual effort of hunting across multiple supermarket chains for
the best grocery prices.

---

## 🚀 Key Capabilities

1. **Catalog Search & Discovery (`/api/v1/products`)**
   - Search products by name, brand, barcode, or category with pagination.
   - Access packaging unit sizes (e.g. 2L, 500g, 1kg) and barcodes.

2. **Store-Level Pricing (`/api/v1/products/{id}/prices`)**
   - Compare active retail prices and stock availability across major
     supermarket chains (Checkers, Woolworths, Pick n Pay, SPAR, Shoprite).

3. **Smart Basket Optimizer (`/api/v1/baskets/calculate`)**
   - **Single-Store Ranking:** Ranks supermarket branches by total basket
     cost (lowest first).
   - **Smart Split Optimization:** Recommends optimal 2-store splits
     that yield maximum savings.
   - **Inventory Alerts:** Flags missing or out-of-stock items per store branch.

4. **Price History & Trend Intelligence (`/api/v1/products/{id}/history`)**
   - Chronological timeseries price data across configurable date ranges.
   - Inflation metrics, all-time high/low tracking, and promotional
     discount veracity scoring.

---

## 📖 Interactive Documentation & Specs
- **Swagger UI:** Accessible at `/docs` (alias `/api/docs`)
- **ReDoc:** Accessible at `/redoc` (alias `/api/redoc`)
- **OpenAPI 3.1 JSON Spec:** Available at `/openapi.json`
- **OpenAPI 3.1 YAML Spec:** Available at `/openapi.yaml`
- **Postman Collection:** Ready-to-import collection at `docs/postman_collection.json`
"""

app = FastAPI(
    title="Smart Basket API",
    summary="Real-time grocery price intelligence and basket optimization engine",
    description=API_DESCRIPTION,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=OPENAPI_TAGS,
    contact={
        "name": "Smart Basket Engineering Team",
        "url": "https://github.com/DyanCoded/Smart-Basket",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 1,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "filter": True,
    },
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_v1_router, prefix="/api")


# Interactive Documentation Aliases & Spec Endpoints
@app.get("/api/docs", include_in_schema=False)
def api_docs_redirect() -> RedirectResponse:
    """Redirect /api/docs to /docs for interactive Swagger UI."""
    return RedirectResponse(url="/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/api/redoc", include_in_schema=False)
def api_redoc_redirect() -> RedirectResponse:
    """Redirect /api/redoc to /redoc for ReDoc documentation."""
    return RedirectResponse(
        url="/redoc", status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@app.get("/api/openapi.json", include_in_schema=False)
def api_openapi_json_redirect() -> RedirectResponse:
    """Redirect /api/openapi.json to /openapi.json."""
    return RedirectResponse(
        url="/openapi.json", status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@app.get(
    "/openapi.yaml",
    include_in_schema=False,
    response_class=Response,
)
def get_openapi_yaml() -> Response:
    """Serve OpenAPI specification in YAML format."""
    schema = app.openapi()
    yaml_content = yaml.dump(schema, sort_keys=False, allow_unicode=True)
    return Response(content=yaml_content, media_type="application/x-yaml")


@app.get(
    "/health",
    tags=["health"],
    summary="Service health check & catalog freshness telemetry",
    description=(
        "Verify API service liveness and expose latest national chain price "
        "refresh telemetry for client freshness indicators."
    ),
    response_description="Liveness status, application name, and price sync telemetry.",
    responses={
        status.HTTP_200_OK: {
            "description": "Service is healthy and responding.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "app": "Smart Basket API",
                        "catalog_freshness": {
                            "status": "ok",
                            "last_price_sync_at": "2026-11-20T03:05:12+00:00",
                            "active_chains": 5,
                            "tracked_prices": 90,
                        },
                    }
                }
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error occurred.",
        },
    },
)
def health_check(db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    """Healthcheck endpoint exposing service liveness and catalog freshness."""
    try:
        freshness = catalog_service.get_catalog_freshness_telemetry(db)
    except Exception:  # noqa: BLE001
        logger.debug("Catalog freshness telemetry unavailable during /health check")
        freshness = {
            "status": "unavailable",
            "last_price_sync_at": None,
            "active_chains": 0,
            "tracked_prices": 0,
        }
    return {
        "status": "ok",
        "app": "Smart Basket API",
        "catalog_freshness": freshness,
    }


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Standardized HTTP exception response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format request validation errors cleanly with 422 or 400 status."""
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Invalid request parameters")
    loc = " -> ".join(str(part) for part in first_error.get("loc", []))
    detail = f"{loc}: {msg}" if loc else msg

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder({"detail": detail, "errors": errors}),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Graceful 500 fallback exception handler."""
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred"},
    )
