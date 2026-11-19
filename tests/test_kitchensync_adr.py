"""Tests for KitchenSync architectural decisions and domain model specifications.

Verifies acceptance criteria for Issue #13:
- Redis 7 service in docker-compose.yml
- Redis and JWT authentication environment variables in .env.example
- ADR-007 entry and decision rationale in docs/DECISIONS.md
- Household & pantry entities in docs/domain-model.md
- Milestone 13 completion in README.md
"""

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_docker_compose_redis_configuration() -> None:
    """Verify docker-compose.yml declares Redis 7 service and persistent volume."""
    compose_path = PROJECT_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist"

    with compose_path.open("r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    assert "redis" in services, "Redis service must be declared in docker-compose.yml"

    redis_cfg = services["redis"]
    assert (
        redis_cfg.get("image") == "redis:7-alpine"
    ), "Redis must use redis:7-alpine image"
    assert (
        redis_cfg.get("container_name") == "smart_basket_redis"
    ), "Container name must be smart_basket_redis"

    ports = redis_cfg.get("ports", [])
    assert any("6379" in str(p) for p in ports), "Redis port 6379 must be exposed"

    healthcheck = redis_cfg.get("healthcheck", {})
    test_cmd = healthcheck.get("test", [])
    cmd_str = " ".join(test_cmd) if isinstance(test_cmd, list) else str(test_cmd)
    assert (
        "redis-cli" in cmd_str and "ping" in cmd_str
    ), "Healthcheck must run redis-cli ping"

    volumes = compose_data.get("volumes", {})
    assert "redis_data" in volumes, "redis_data volume must be declared"


def test_env_example_redis_and_jwt_configuration() -> None:
    """Verify .env.example defines Redis connection and JWT security variables."""
    env_path = PROJECT_ROOT / ".env.example"
    assert env_path.exists(), ".env.example must exist"
    content = env_path.read_text(encoding="utf-8")

    # Redis variables
    assert "REDIS_HOST=" in content, "REDIS_HOST must be present in .env.example"
    assert "REDIS_PORT=" in content, "REDIS_PORT must be present in .env.example"
    assert "REDIS_URL=" in content, "REDIS_URL must be present in .env.example"

    # JWT Authentication variables
    assert (
        "JWT_SECRET_KEY=" in content
    ), "JWT_SECRET_KEY must be present in .env.example"
    assert "JWT_ALGORITHM=" in content, "JWT_ALGORITHM must be present in .env.example"
    assert (
        "ACCESS_TOKEN_EXPIRE_MINUTES=" in content
    ), "ACCESS_TOKEN_EXPIRE_MINUTES must be present"
    assert (
        "REFRESH_TOKEN_EXPIRE_DAYS=" in content
    ), "REFRESH_TOKEN_EXPIRE_DAYS must be present"


def test_decisions_md_adr007_specification() -> None:
    """Verify docs/DECISIONS.md documents ADR-007 with all required decisions."""
    decisions_path = PROJECT_ROOT / "docs" / "DECISIONS.md"
    assert decisions_path.exists(), "docs/DECISIONS.md must exist"
    content = decisions_path.read_text(encoding="utf-8")

    # Log summary entry
    assert (
        "ADR-007" in content
    ), "docs/DECISIONS.md must reference ADR-007 in log summary or heading"
    assert re.search(
        r"2026-11-19.*ADR-007", content
    ), "Log summary must contain dated ADR-007 entry"

    # ADR-007 Section Header
    assert (
        "## ADR-007: KitchenSync Pantry Integration & Unified Household Schema"
        in content
    ), "ADR-007 heading must be explicitly defined"

    # Key Architectural Decisions
    assert "redis:7-alpine" in content, "ADR-007 must specify redis:7-alpine container"
    assert (
        "users" in content and "homes" in content and "memberships" in content
    ), "ADR-007 must document users, homes, and memberships entities"
    assert (
        "buyer" in content and "consumer" in content
    ), "ADR-007 must document buyer and consumer RBAC roles"
    assert (
        "pantry_items" in content and "product_id" in content
    ), "ADR-007 must document pantry_items and product_id linkage"
    assert (
        "custom_name" in content
    ), "ADR-007 must document custom_name for uncatalogued items"
    assert (
        "pantry_logs" in content
    ), "ADR-007 must document pantry_logs consumption trail"
    assert (
        "Expo SDK 53" in content or "React Native" in content
    ), "ADR-007 must document mobile client framework"
    assert (
        "mobile/" in content
    ), "ADR-007 must state mobile client location under mobile/"


def test_domain_model_md_kitchensync_entities() -> None:
    """Verify docs/domain-model.md defines household and pantry domain entities."""
    domain_path = PROJECT_ROOT / "docs" / "domain-model.md"
    assert domain_path.exists(), "docs/domain-model.md must exist"
    content = domain_path.read_text(encoding="utf-8")

    # Conceptual Entity Sections
    assert "### 7. User" in content, "User entity must be documented"
    assert "### 8. Home" in content, "Home entity must be documented"
    assert "### 9. Membership" in content, "Membership entity must be documented"
    assert "### 10. PantryItem" in content, "PantryItem entity must be documented"
    assert "### 11. PantryLog" in content, "PantryLog entity must be documented"

    # RBAC and Bridge Rules
    assert (
        "buyer" in content and "consumer" in content
    ), "buyer and consumer roles must be defined"
    assert (
        "product_id" in content and "custom_name" in content
    ), "Nullable product_id and custom_name bridge must be defined"

    # Mermaid ERD checks
    assert "USER ||--o{ MEMBERSHIP" in content, "Mermaid ERD must link USER-MEMBERSHIP"
    assert "HOME ||--o{ MEMBERSHIP" in content, "Mermaid ERD must link HOME-MEMBERSHIP"
    assert (
        "HOME ||--o{ PANTRY_ITEM" in content
    ), "Mermaid ERD must link HOME-PANTRY_ITEM"
    assert (
        "PRODUCT |o--o{ PANTRY_ITEM" in content
    ), "Mermaid ERD must link PRODUCT-PANTRY_ITEM"
    assert (
        "PANTRY_ITEM ||--o{ PANTRY_LOG" in content
    ), "Mermaid ERD must link PANTRY_ITEM-PANTRY_LOG"


def test_readme_milestone_13_entry() -> None:
    """Verify README.md records Milestone 13 as completed."""
    readme_path = PROJECT_ROOT / "README.md"
    assert readme_path.exists(), "README.md must exist"
    content = readme_path.read_text(encoding="utf-8")

    assert "**13. Architecture**" in content, "README.md must include Milestone 13 row"
    assert (
        "KitchenSync Pantry Integration & Unified Schema ADR" in content
    ), "Milestone 13 title must be present in README.md"
    assert (
        "[#13](https://github.com/DyanCoded/Smart-Basket/issues/13)" in content
    ), "Milestone 13 must link to Issue #13"
