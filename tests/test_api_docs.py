"""Tests for OpenAPI / Swagger documentation and exported artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi import status
from fastapi.testclient import TestClient

from scripts.export_openapi import (
    DOCS_DIR,
    export_all,
    generate_openapi_spec,
    generate_postman_collection,
)
from src.main import app

client = TestClient(app)


def test_swagger_ui_html_endpoint() -> None:
    """Verify /docs serves Swagger UI HTML successfully."""
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]
    assert "swagger-ui" in response.text.lower()


def test_redoc_html_endpoint() -> None:
    """Verify /redoc serves ReDoc HTML successfully."""
    response = client.get("/redoc")
    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]
    assert "redoc" in response.text.lower()


def test_api_docs_redirect_endpoints() -> None:
    """Verify /api/docs and /api/redoc redirect to canonical doc URLs."""
    res_docs = client.get("/api/docs", follow_redirects=False)
    assert res_docs.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert res_docs.headers["location"] == "/docs"

    res_redoc = client.get("/api/redoc", follow_redirects=False)
    assert res_redoc.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert res_redoc.headers["location"] == "/redoc"

    res_openapi = client.get("/api/openapi.json", follow_redirects=False)
    assert res_openapi.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert res_openapi.headers["location"] == "/openapi.json"


def test_openapi_json_endpoint() -> None:
    """Verify /openapi.json returns valid OpenAPI 3.1.0 specification."""
    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["openapi"].startswith("3.")
    assert data["info"]["title"] == "Smart Basket API"
    assert "paths" in data
    assert "components" in data


def test_openapi_yaml_endpoint() -> None:
    """Verify /openapi.yaml returns valid OpenAPI specification in YAML."""
    response = client.get("/openapi.yaml")
    assert response.status_code == status.HTTP_200_OK
    assert "yaml" in response.headers["content-type"]
    parsed = yaml.safe_load(response.text)
    assert isinstance(parsed, dict)
    assert parsed["info"]["title"] == "Smart Basket API"
    assert parsed["openapi"].startswith("3.")


def test_openapi_endpoint_coverage() -> None:
    """Verify all required application routes are documented in OpenAPI."""
    schema = app.openapi()
    paths = schema.get("paths", {})

    expected_paths = [
        "/health",
        "/api/v1/products",
        "/api/v1/products/{product_id}",
        "/api/v1/products/{product_id}/prices",
        "/api/v1/products/{product_id}/history",
        "/api/v1/products/{product_id}/intelligence",
        "/api/v1/stores",
        "/api/v1/baskets/calculate",
    ]

    for expected in expected_paths:
        assert expected in paths, f"Path '{expected}' missing from OpenAPI paths"


def test_openapi_status_codes_and_descriptions() -> None:
    """Verify every endpoint documents summary, description, and key status codes."""
    schema = app.openapi()
    paths = schema.get("paths", {})

    for path_name, path_item in paths.items():
        for method_name, operation in path_item.items():
            if method_name not in ["get", "post", "put", "delete", "patch"]:
                continue
            assert operation.get(
                "summary"
            ), f"Summary missing for {method_name.upper()} {path_name}"
            assert operation.get(
                "description"
            ), f"Description missing for {method_name.upper()} {path_name}"

            responses = operation.get("responses", {})
            assert (
                "200" in responses
            ), f"Status 200 missing for {method_name.upper()} {path_name}"
            assert (
                "500" in responses
            ), f"Status 500 missing for {method_name.upper()} {path_name}"


def test_basket_calculation_payload_examples() -> None:
    """Verify basket calculation endpoint contains rich request payload examples."""
    schema = app.openapi()
    basket_post = schema["paths"]["/api/v1/baskets/calculate"]["post"]

    req_body = basket_post.get("requestBody", {})
    assert req_body.get("required") is True

    json_content = req_body.get("content", {}).get("application/json", {})
    assert "schema" in json_content

    examples = json_content.get("examples", {})
    assert "two_item_basket" in examples
    assert "family_pantry_basket" in examples

    two_item_val = examples["two_item_basket"]["value"]
    assert "items" in two_item_val
    assert len(two_item_val["items"]) >= 2

    # Verify response codes for basket calculation
    responses = basket_post["responses"]
    for code in ["200", "400", "404", "422", "500"]:
        assert code in responses, f"Response code {code} missing from basket calculate"


def test_exported_docs_artifacts_exist_and_match() -> None:
    """Verify exported documentation files in docs/ match live OpenAPI schema."""
    json_path = DOCS_DIR / "openapi.json"
    yaml_path = DOCS_DIR / "openapi.yaml"
    postman_path = DOCS_DIR / "postman_collection.json"

    assert json_path.exists(), "docs/openapi.json does not exist"
    assert yaml_path.exists(), "docs/openapi.yaml does not exist"
    assert postman_path.exists(), "docs/postman_collection.json does not exist"

    # Verify JSON spec parses and matches live app.openapi()
    with open(json_path, encoding="utf-8") as f:
        json_spec = json.load(f)
    live_schema = generate_openapi_spec()
    assert json_spec["info"]["title"] == live_schema["info"]["title"]
    assert set(json_spec["paths"].keys()) == set(live_schema["paths"].keys())

    # Verify YAML spec parses
    with open(yaml_path, encoding="utf-8") as f:
        yaml_spec = yaml.safe_load(f)
    assert yaml_spec["info"]["title"] == live_schema["info"]["title"]
    assert set(yaml_spec["paths"].keys()) == set(live_schema["paths"].keys())

    # Verify Postman collection format
    postman_live = generate_postman_collection()
    assert postman_live["info"]["name"] == "Smart Basket API"

    with open(postman_path, encoding="utf-8") as f:
        postman_coll = json.load(f)
    assert postman_coll["info"]["name"] == "Smart Basket API"
    assert "collection.json" in postman_coll["info"]["schema"]
    assert len(postman_coll["item"]) == 5  # 5 domain folders

    # Verify Postman collection includes basket calculate endpoint
    basket_folder = next(f for f in postman_coll["item"] if "Basket" in f["name"])
    assert len(basket_folder["item"]) >= 2


def test_export_all_script_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify export_all script executes cleanly and writes all artifacts."""
    monkeypatch.setattr("scripts.export_openapi.DOCS_DIR", tmp_path)
    result = export_all()

    assert result["openapi_json"].exists()
    assert result["openapi_yaml"].exists()
    assert result["postman_collection"].exists()

    assert result["openapi_json"].stat().st_size > 1000
    assert result["openapi_yaml"].stat().st_size > 1000
    assert result["postman_collection"].stat().st_size > 1000
