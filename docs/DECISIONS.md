# Architectural Decision Records (ADR)

## Log Summary
- **2026-09-24:** Adopted Python 3.11+, FastAPI, PostgreSQL 16, SQLAlchemy, and Alembic for Smart Basket backend and data layer; enforced via Ruff/Black.

---

## ADR-001: Tech Stack Selection & Database Engine Evaluation

### Status
**Accepted** (2026-09-24)

### Context & Problem Statement
Smart Basket requires a robust data engine and API backend to power multi-store price comparisons, basket split optimizations, and historical price tracking. The platform must handle:
1. Strongly relational data structures (`Store` ↔ `Product` ↔ `StorePrice` ↔ `Basket`).
2. High-precision financial and unit calculations without floating-point drift.
3. Rapid schema migrations and contract verification.
4. Fast response times for real-time basket calculations and analytics.

---

### Decision & Technical Rationale

#### 1. Database Engine: PostgreSQL 16 (Relational over Document/MongoDB)
- **Relational Integrity & Foreign Keys:** Our domain model relies heavily on relationships (e.g., `Category -> Product`, `Product -> StorePrice`, `Store -> StorePrice`). Relational constraints guarantee referential integrity out of the box.
- **Unique Constraints:** Enforces a single active price per store-product pair via unique constraint `(store_id, product_id)`.
- **Exact Numeric Precision:** PostgreSQL's native `NUMERIC(10, 2)` and `INTEGER` (cents) ensure zero floating-point calculation errors during subtotal, discount, and unit-price calculations.
- **Relational Joins & Aggregations:** Multi-store basket evaluation involves joining basket items against active store prices across multiple chains and aggregating sums—workloads where relational query planners significantly outperform document stores.
- **Time-Series Efficiency:** PostgreSQL handles time-series records (`PriceHistory`) effectively via indexing (B-Tree, BRIN) and partitioning if needed in future scaling.
- *Considered & Rejected: MongoDB / Document Stores.* Denormalizing prices inside product documents would make store-wide price updates and cross-store basket joins inefficient and prone to sync anomalies.

#### 2. Backend Language & Framework: Python 3.11+ & FastAPI
- **Async Performance:** Built on Starlette and ASGI, FastAPI provides high-throughput asynchronous request handling.
- **Native OpenAPI & Pydantic:** Automatic OpenAPI schema generation and strict data validation using Pydantic, aligning directly with our "Contract is Law" principle (`AI_GUARDRAILS.md`).
- **Algorithm & Analytics Friendly:** Python's rich ecosystem and mathematical capabilities simplify the combinatorial algorithms required for the Smart Split-Basket optimizer (Journey 2).
- *Considered & Rejected: Node.js/Express (less native type safety without full TS setup; looser schema contract alignment) and Java/Spring Boot (heavier memory footprint and slower startup for early milestones).*

#### 3. ORM & Schema Migrations: SQLAlchemy 2.0 & Alembic
- **SQLAlchemy 2.0:** Provides modern 2.0-style declarative syntax with full typing support and async engine capabilities (`asyncpg`).
- **Alembic:** Industry-standard database migration tool for Python, providing reproducible, version-controlled schema evolution tracked in Git.

#### 4. Development Tooling & Quality Gates
- **Linter & Formatter:** **Ruff** (with **Black** formatting rules) to enforce PEP 8 standards, strict import ordering, and zero-tolerance linting gates before commits.
- **Testing:** **Pytest** with `pytest-asyncio` for unit, contract boundary, and integration testing.
- **Local Environment:** **Docker Compose** managing local PostgreSQL 16 instances for zero-friction developer setup and parity with CI.

---

### Consequences & Trade-offs
- **Positive:**
  - Guaranteed referential and financial integrity.
  - Automatic API documentation synced directly to implementation.
  - Reproducible database state across development environments via Alembic.
  - Fast feedback loop with lightweight, modern Python tooling.
- **Negative / Mitigations:**
  - Relational schema changes require formal migration scripts via Alembic (mitigated by automated migration generation).
  - Async Python/SQLAlchemy requires careful session management (mitigated by FastAPI dependency injection).