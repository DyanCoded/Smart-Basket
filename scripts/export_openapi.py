"""Export OpenAPI (Swagger) specifications and Postman Collection artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import app  # noqa: E402

DOCS_DIR = PROJECT_ROOT / "docs"

# Realistic seed fixture constants for Postman collection requests
SAMPLE_MILK_UUID = "6e2941e3-033d-5768-8143-5e7ebc24b874"
SAMPLE_BREAD_UUID = "ab9928f5-221a-5546-8b6c-c4ec04fbe933"
SAMPLE_EGGS_UUID = "4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382"
SAMPLE_CATEGORY_UUID = "dcda34e0-efd6-5f43-b188-db739a0deab7"
SAMPLE_RETAILER_UUID = "3ae15000-8907-5fb5-9904-c47dba4bcc3e"


def generate_openapi_spec() -> dict[str, Any]:
    """Generate OpenAPI 3.1.0 specification dictionary from FastAPI app."""
    return app.openapi()


def generate_postman_collection() -> dict[str, Any]:
    """Generate Postman Collection v2.1.0 containing all API endpoints."""
    return {
        "info": {
            "_postman_id": "d1e4c8b2-5678-90ab-cdef-1234567890ab",
            "name": "Smart Basket API",
            "description": (
                "Postman Collection for Smart Basket real-time grocery price "
                "intelligence and multi-store basket optimization platform."
            ),
            "schema": (
                "https://schema.getpostman.com/json/collection/v2.1.0/"
                "collection.json"
            ),
            "version": "0.1.0",
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": "http://localhost:8000",
                "type": "string",
            }
        ],
        "item": [
            {
                "name": "01. Health",
                "item": [
                    {
                        "name": "Check Service Health",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": "{{baseUrl}}/health",
                                "host": ["{{baseUrl}}"],
                                "path": ["health"],
                            },
                            "description": (
                                "Verify API service liveness and operational readiness."
                            ),
                        },
                        "response": [],
                    }
                ],
            },
            {
                "name": "02. Catalog & Products",
                "item": [
                    {
                        "name": "List Products (Search & Filter)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": (
                                    "{{baseUrl}}/api/v1/products"
                                    "?q=milk&limit=20&offset=0"
                                ),
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "products"],
                                "query": [
                                    {
                                        "key": "q",
                                        "value": "milk",
                                        "description": (
                                            "Search term for name, brand, or barcode"
                                        ),
                                    },
                                    {
                                        "key": "limit",
                                        "value": "20",
                                        "description": "Max items per page",
                                    },
                                    {
                                        "key": "offset",
                                        "value": "0",
                                        "description": "Pagination offset",
                                    },
                                ],
                            },
                            "description": (
                                "Retrieve catalog products with partial-match search."
                            ),
                        },
                        "response": [],
                    },
                    {
                        "name": "Filter Products by Category",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": (
                                    f"{{{{baseUrl}}}}/api/v1/products"
                                    f"?category_id={SAMPLE_CATEGORY_UUID}&limit=20"
                                ),
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "products"],
                                "query": [
                                    {
                                        "key": "category_id",
                                        "value": SAMPLE_CATEGORY_UUID,
                                        "description": "Category UUID (Dairy & Eggs)",
                                    },
                                    {
                                        "key": "limit",
                                        "value": "20",
                                        "description": "Max items per page",
                                    },
                                ],
                            },
                            "description": "Filter products by specific category UUID.",
                        },
                        "response": [],
                    },
                    {
                        "name": "Get Product Details",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": (
                                    f"{{{{baseUrl}}}}/api/v1/products/"
                                    f"{SAMPLE_MILK_UUID}"
                                ),
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "products", SAMPLE_MILK_UUID],
                            },
                            "description": (
                                "Retrieve detailed product metadata including barcode "
                                "and packaging unit size."
                            ),
                        },
                        "response": [],
                    },
                    {
                        "name": "Get Active Store Prices for Product",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": (
                                    f"{{{{baseUrl}}}}/api/v1/products/"
                                    f"{SAMPLE_MILK_UUID}/prices"
                                ),
                                "host": ["{{baseUrl}}"],
                                "path": [
                                    "api",
                                    "v1",
                                    "products",
                                    SAMPLE_MILK_UUID,
                                    "prices",
                                ],
                            },
                            "description": (
                                "List active prices and stock status across all "
                                "monitored supermarket store branches."
                            ),
                        },
                        "response": [],
                    },
                ],
            },
            {
                "name": "03. Price History & Intelligence",
                "item": [
                    {
                        "name": "Get Price History Timeseries",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": (
                                    f"{{{{baseUrl}}}}/api/v1/products/"
                                    f"{SAMPLE_MILK_UUID}/history?limit=100&offset=0"
                                ),
                                "host": ["{{baseUrl}}"],
                                "path": [
                                    "api",
                                    "v1",
                                    "products",
                                    SAMPLE_MILK_UUID,
                                    "history",
                                ],
                                "query": [
                                    {
                                        "key": "limit",
                                        "value": "100",
                                        "description": "Max history points",
                                    },
                                    {
                                        "key": "offset",
                                        "value": "0",
                                        "description": "Pagination offset",
                                    },
                                ],
                            },
                            "description": (
                                "Fetch chronological timestamped price entries "
                                "suitable for chart rendering."
                            ),
                        },
                        "response": [],
                    },
                    {
                        "name": "Get Price Trend Intelligence & Deal Veracity",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": (
                                    f"{{{{baseUrl}}}}/api/v1/products/"
                                    f"{SAMPLE_MILK_UUID}/intelligence"
                                ),
                                "host": ["{{baseUrl}}"],
                                "path": [
                                    "api",
                                    "v1",
                                    "products",
                                    SAMPLE_MILK_UUID,
                                    "intelligence",
                                ],
                            },
                            "description": (
                                "Compute all-time high/low, current vs historical "
                                "averages, and promotional deal veracity score."
                            ),
                        },
                        "response": [],
                    },
                ],
            },
            {
                "name": "04. Stores & Supermarkets",
                "item": [
                    {
                        "name": "List All Stores",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/stores?limit=50&offset=0",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "stores"],
                                "query": [
                                    {
                                        "key": "limit",
                                        "value": "50",
                                        "description": "Max stores per page",
                                    },
                                    {
                                        "key": "offset",
                                        "value": "0",
                                        "description": "Pagination offset",
                                    },
                                ],
                            },
                            "description": (
                                "List supermarket branches with chain relationships."
                            ),
                        },
                        "response": [],
                    },
                    {
                        "name": "Filter Stores by Retailer Chain",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Accept", "value": "application/json"}],
                            "url": {
                                "raw": (
                                    f"{{{{baseUrl}}}}/api/v1/stores"
                                    f"?retailer_id={SAMPLE_RETAILER_UUID}&limit=50"
                                ),
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "stores"],
                                "query": [
                                    {
                                        "key": "retailer_id",
                                        "value": SAMPLE_RETAILER_UUID,
                                        "description": (
                                            "Parent retailer UUID (Checkers)"
                                        ),
                                    },
                                    {
                                        "key": "limit",
                                        "value": "50",
                                        "description": "Max stores per page",
                                    },
                                ],
                            },
                            "description": (
                                "Filter branches by parent supermarket chain."
                            ),
                        },
                        "response": [],
                    },
                ],
            },
            {
                "name": "05. Basket Optimizer",
                "item": [
                    {
                        "name": "Calculate Basket & Smart Split (Standard 2 Items)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                },
                                {
                                    "key": "Accept",
                                    "value": "application/json",
                                },
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {
                                        "items": [
                                            {
                                                "product_id": SAMPLE_MILK_UUID,
                                                "quantity": 2.0,
                                            },
                                            {
                                                "product_id": SAMPLE_BREAD_UUID,
                                                "quantity": 1.0,
                                            },
                                        ]
                                    },
                                    indent=2,
                                ),
                                "options": {"raw": {"language": "json"}},
                            },
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/baskets/calculate",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "baskets", "calculate"],
                            },
                            "description": (
                                "Calculates ranked single-store totals and finds "
                                "the cheapest multi-store split for milk and bread."
                            ),
                        },
                        "response": [],
                    },
                    {
                        "name": "Calculate Basket (Pantry Essentials 3 Items)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                },
                                {
                                    "key": "Accept",
                                    "value": "application/json",
                                },
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {
                                        "items": [
                                            {
                                                "product_id": SAMPLE_MILK_UUID,
                                                "quantity": 2.0,
                                            },
                                            {
                                                "product_id": SAMPLE_BREAD_UUID,
                                                "quantity": 1.0,
                                            },
                                            {
                                                "product_id": SAMPLE_EGGS_UUID,
                                                "quantity": 1.0,
                                            },
                                        ]
                                    },
                                    indent=2,
                                ),
                                "options": {"raw": {"language": "json"}},
                            },
                            "url": {
                                "raw": "{{baseUrl}}/api/v1/baskets/calculate",
                                "host": ["{{baseUrl}}"],
                                "path": ["api", "v1", "baskets", "calculate"],
                            },
                            "description": (
                                "Evaluates a 3-item essentials basket (milk, bread, "
                                "eggs) across all stores with smart split savings."
                            ),
                        },
                        "response": [],
                    },
                ],
            },
        ],
    }


def export_all() -> dict[str, Path]:
    """Export openapi.json, openapi.yaml, and postman_collection.json to docs/."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    openapi_data = generate_openapi_spec()
    postman_data = generate_postman_collection()

    json_path = DOCS_DIR / "openapi.json"
    yaml_path = DOCS_DIR / "openapi.yaml"
    postman_path = DOCS_DIR / "postman_collection.json"

    # 1. Export openapi.json
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_data, f, indent=2)
        f.write("\n")

    # 2. Export openapi.yaml
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_data, f, sort_keys=False, allow_unicode=True)

    # 3. Export postman_collection.json
    with open(postman_path, "w", encoding="utf-8") as f:
        json.dump(postman_data, f, indent=2)
        f.write("\n")

    return {
        "openapi_json": json_path,
        "openapi_yaml": yaml_path,
        "postman_collection": postman_path,
    }


if __name__ == "__main__":
    print("Exporting Smart Basket API specifications and artifacts...")
    exported = export_all()
    for name, path in exported.items():
        size = path.stat().st_size
        print(f"  [OK] Exported {name} -> {path} ({size:,} bytes)")
    print("Done! All API artifacts up to date.")
