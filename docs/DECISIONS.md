# Architectural Decision Records (ADR)

## Log Summary
- **2026-11-19:** Implemented stateless JWT authentication (OAuth2PasswordBearer), bcrypt password hashing, and collaborative household management endpoints (users, homes, memberships with buyer/consumer RBAC) with membership dependency guards (Issue #15).
- **2026-11-19:** Implemented physical database schema and Alembic migration 0002_add_pantry_and_households for multi-user households (users, homes, memberships) and offline-capable pantry inventory tracking (pantry_items, pantry_logs, baskets.home_id) (Issue #14).
- **2026-11-19:** Adopted KitchenSync pantry synchronization architecture, unified household schema (users, homes, memberships with buyer/consumer RBAC, pantry_items, pantry_logs), Redis 7 Pub/Sub for real-time WebSockets, nullable product_id catalog-to-pantry replenishment bridge, and Expo SDK 53 mobile client under mobile/ (Issue #13, ADR-007).
- **2026-11-19:** Finalized Phase 1 milestone release packaging, system architecture diagrams, academic retrospective, query performance analysis, Release Notes v1.0.0, and tagged Git release v1.0.0 (Issue #12).
- **2026-11-18:** Configured OpenAPI 3.1.0 specifications, interactive Swagger UI (`/docs`, `/api/docs`) and ReDoc (`/redoc`, `/api/redoc`) explorers, YAML spec endpoints (`/openapi.yaml`), rich request/response payload examples for basket calculations, and automated export pipeline generating `docs/openapi.json`, `docs/openapi.yaml`, and `docs/postman_collection.json` (Issue #11).
- **2026-11-18:** Configured automated GitHub Actions CI pipeline (.github/workflows/ci.yml) with PostgreSQL 16 containerization, Alembic migration verification, catalog seed validation, Ruff/Black code quality gates, and automated test suite execution (Issue #10).
- **2026-11-18:** Implemented Price History Timeseries and Trend Intelligence endpoints with composite index query optimization, chronological ordering, inflation metrics, and promotional deal veracity scoring (Issue #9).
- **2026-11-18:** Implemented Smart Basket calculation and 2-store split optimization engine (Journey 2) with deterministic ranking, stock/missing item warnings, exact Decimal currency math, and sub-100ms benchmarked performance (Issue #8).
- **2026-11-17:** Implemented Core API endpoints for catalog product search, product details, store pricing comparison, and store branch listings with input validation and standard error formatting (Issue #7).
- **2026-11-17:** Implemented deterministic catalog seeding script (Python ORM & PostgreSQL raw SQL), multi-store price divergence verification query, and Pytest test fixtures (Issue #6).
- **2026-09-25:** Implemented baseline physical database schema (PostgreSQL 16) with Alembic migration 0001_baseline_schema and SQLAlchemy 2.0 declarative entities.
- **2026-09-25:** Established standard layered directory layout (`src/` with `core/`, `api/`, `models/`, `services/`), containerized PostgreSQL 16 with healthcheck via Docker Compose, environment variable templates (`.env.example`), and automated Ruff/Black/Pre-commit verification scripts.
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

---

## ADR-002: Backend Framework & API Protocol Selection

### Status
**Accepted** (2026-09-24)

### Context & Problem Statement
Smart Basket requires high-throughput API endpoints for product search, price lookups, multi-store basket calculations, and real-time client communication. The API layer must enforce contract fidelity ("Contract is Law") and eliminate runtime serialization discrepancies.

### Decision & Technical Rationale
- **FastAPI (Python 3.11+):** Leverages Starlette ASGI runtime and Pydantic v2 data models for request/response serialization and validation.
- **Automated OpenAPI 3.1.0 Generation:** Interactive Swagger UI and ReDoc explorers are auto-generated from Pydantic models, guaranteeing zero documentation drift.
- **Async Concurrency:** Native `async`/`await` support with `asyncpg` connection pools facilitates concurrent queries during multi-store evaluations.
- *Alternatives Evaluated:* Express/Node.js (lacked cohesive typing and declarative schema validation out of the box), Go/Gin (slower developer velocity for mathematical prototype and migration tooling), Django/DRF (heavier memory footprint and more complex async integration).

### Consequences & Trade-offs
- **Positive:** High developer velocity, automated OpenAPI specs, robust validation, native async capabilities.
- **Negative / Mitigations:** Fast-evolving ASGI ecosystem requires strict dependency version pinning (mitigated by `requirements.txt` and `pyproject.toml`).

---

## ADR-003: Financial Arithmetic & Currency Precision

### Status
**Accepted** (2026-09-24)

### Context & Problem Statement
Grocery price comparisons involve line-item multiplications, promotional discount subtractions, and multi-store split difference calculations. Standard IEEE 754 floating-point representations (`float` / `double`) introduce catastrophic rounding drift (e.g., `0.1 + 0.2 = 0.30000000000000004`), corrupting user trust and verification assertions.

### Decision & Technical Rationale
- **PostgreSQL `NUMERIC(10, 2)`:** All monetary values in the database (`current_price`, `promotional_price`, `price`) are stored with fixed 2-decimal precision.
- **Python `Decimal` Type:** Domain entities and Pydantic schemas enforce Python's standard library `decimal.Decimal` with explicit `ROUND_HALF_UP` quantization.
- *Alternatives Evaluated:* Integer cents (requires constant division and multiplication across display boundaries, introducing conversion friction; rejected in favor of native Decimal). Floating-point floats (rejected due to binary rounding inaccuracy).

### Consequences & Trade-offs
- **Positive:** Absolute financial precision, zero rounding drift, exact parity between unit tests and database queries.
- **Negative / Mitigations:** JSON serializers require explicit custom encoders or Pydantic decimal support (handled seamlessly by Pydantic v2).

---

## ADR-004: Primary Key & Entity Identification Strategy

### Status
**Accepted** (2026-09-25)

### Context & Problem Statement
The platform coordinates data across multiple stores, local catalog seed scripts, integration test runners, and client-side offline caches. Standard auto-incrementing integer keys (`SERIAL` / `BIGSERIAL`) lead to cross-environment ID collision, race conditions, and fragile test fixture assertions.

### Decision & Technical Rationale
- **Deterministic UUIDv5 & Random UUIDv4:** 
  - Catalog seeding scripts and integration fixtures utilize deterministic UUIDv5 with a fixed DNS namespace (`uuid.uuid5(NAMESPACE_URL, ...)`), guaranteeing identical primary keys across local, CI, and production database initializations.
  - Runtime dynamic entities (e.g., baskets, users, homes) utilize standard UUIDv4 primary keys.
- *Alternatives Evaluated:* Sequential integer IDs (predictable, susceptible to enumeration attacks, and prone to seed collision across test environments; rejected).

### Consequences & Trade-offs
- **Positive:** Collision-free multi-store ingestion, offline client fixture reproducibility, secure unguessable identifiers.
- **Negative / Mitigations:** 128-bit UUIDs occupy 16 bytes compared to 4 or 8 bytes for integers (negligible storage overhead given PostgreSQL native `UUID` indexing performance).

---

## ADR-005: Multi-Store Basket Split Optimization Algorithm

### Status
**Accepted** (2026-11-18)

### Context & Problem Statement
Shoppers seeking to minimize grocery expenses frequently split their shopping across two local stores (e.g., purchasing dairy at Store A and pantry staples at Store B). Evaluating all $2^N$ split combinations across $S$ stores for large baskets threatens exponential combinatorial explosion.

### Decision & Technical Rationale
- **Bounded 2-Store Split Optimization ($O(B \cdot S)$):** 
  - For each pairwise store combination $(S_i, S_j)$, the engine iterates through the basket items $B$, assigning each item to whichever store offers the lower unit price.
  - Store pairs are evaluated and ranked deterministically by total basket cost and net savings against the cheapest single-store alternative.
  - Partials and missing items are flagged with clear warnings rather than failing the calculation.
- *Alternatives Evaluated:* Full $k$-store Integer Linear Programming / Knapsack solver (introduced heavy external solver dependencies like PuLP/CBC with unacceptable latency for real-time mobile responses; rejected for practical 2-store real-world shopping patterns).

### Consequences & Trade-offs
- **Positive:** Sub-15ms response times for typical baskets (20+ items across 5 chains), predictable memory consumption, intuitive user explanations.
- **Negative / Mitigations:** Bounded to 2 stores simultaneously (aligned with real-world consumer travel willingness; multi-store splits beyond 2 chains yield diminishing returns after travel costs).

---

## ADR-006: Continuous Integration & Automated Quality Gates

### Status
**Accepted** (2026-11-18)

### Context & Problem Statement
With direct pushes to `main` without manual pull request reviews, the codebase requires automated, deterministic, and fast quality verification gates to prevent broken builds, formatting discrepancies, or contract regressions.

### Decision & Technical Rationale
- **GitHub Actions CI Pipeline (`.github/workflows/ci.yml`):** Automatically executes on all pushes and PRs targeting `main`.
- **PostgreSQL 16 Service Container:** CI spins up a native PostgreSQL 16 container, runs Alembic migrations (`alembic upgrade head`), and executes seed scripts with divergence verification (`python scripts/seed.py --verify`).
- **Ruff & Black Enforcement:** Sub-second static analysis and formatting verification enforced via `scripts/check.py`.
- *Alternatives Evaluated:* Manual testing before push (prone to human error and missed regressions; rejected).

### Consequences & Trade-offs
- **Positive:** Immediate failure notifications on contract violations or broken tests; branch protection enforces clean builds.
- **Negative / Mitigations:** Requires running Docker service containers in CI (mitigated by GitHub Actions native service containers).

---

## ADR-007: KitchenSync Pantry Integration & Unified Household Schema

### Status
**Accepted** (2026-11-19)

### Context & Problem Statement
Smart Basket Phase 1 established the core catalog, multi-store price comparison engine, and trend intelligence APIs. Phase 2 introduces **KitchenSync**—a household pantry tracking engine and cross-platform mobile frontend (Expo SDK 53 / React Native).
Historically, the KitchenSync blueprint (`docs/kitchenSync-blueprint.md`) proposed an isolated Django + DRF + Django Channels backend. Integrating this into Smart Basket as a separate microservice would introduce significant operational overhead: dual database maintenance, inter-service HTTP network latency, fragmented authentication, and synchronization anomalies between pantry items and store price comparisons.
Smart Basket requires a single, unified architectural design that preserves our high-performance FastAPI and PostgreSQL 16 foundation while delivering real-time household collaboration, granular role-based access control, and seamless pantry-to-basket replenishment.

### Decision & Technical Rationale

#### 1. Unified Backend Architecture (FastAPI + PostgreSQL over Django Monolith)
- Rather than running a separate Django service, the KitchenSync domain models, authentication routines, and WebSocket handlers are ported directly into Smart Basket's FastAPI backend (`src/`).
- This eliminates inter-service network hops, unifies database transactions under SQLAlchemy 2.0, and enables direct SQL joins between household inventory and retail pricing data.

#### 2. Redis 7 Infrastructure for Real-Time Pub/Sub & WebSockets
- **Component:** Redis 7 Alpine (`redis:7-alpine`) is added to `docker-compose.yml` (service: `redis`, container: `smart_basket_redis`, port: `6379`, healthcheck: `redis-cli ping`, volume: `redis_data`).
- **Role:** Backplane for WebSocket communication and background event dissemination.
- **Pub/Sub Channel Pattern:** Real-time state mutations publish to channel `home:{home_id}:pantry`. When a household member marks an item as `low` or `finished`, the event broadcasts instantly to all connected mobile devices in that home.
- **Environment Variables:** Configured via `REDIS_HOST`, `REDIS_PORT`, and `REDIS_URL` in `.env.example`.

#### 3. Domain Entities & Role-Based Access Control (RBAC)
- All new entities adopt UUID primary keys to ensure collision-free synchronization:
  - **`users`:** Core user profile storing authentication credentials, password hash, and full name.
  - **`homes`:** Shared household living space identified by a unique `invite_code` for simple family onboarding.
  - **`memberships`:** Join entity linking `users` and `homes` with a unique constraint on `(user_id, home_id)`.
- **RBAC Roles:**
  - `buyer`: Primary shopper authority. Can create, edit, and delete pantry items, trigger multi-store basket optimizations, and check off items during in-store shopping.
  - `consumer`: Household resident authority. Can view household pantry inventory and log item consumption (e.g., mark items `low` or `finished`).

#### 4. The Pantry-to-Product Replenishment Bridge (`pantry_items` & `pantry_logs`)
- **Nullable Foreign Key Linkage:**
  - `pantry_items.product_id` is a **nullable** foreign key referencing `products.id`.
  - **Catalogued Items (`product_id IS NOT NULL`):** Linked directly to the universal grocery catalog. When marked `low` or `finished`, the item automatically bridges into the household's active Smart Basket (`basket_items`), allowing immediate multi-store price evaluation and split optimization.
  - **Custom / Uncatalogued Items (`product_id IS NULL`):** Supported via `custom_name` and category tags, allowing users to track niche, artisanal, or homemade goods without failing catalog referential constraints.
- **Consumption Audit Trail (`pantry_logs`):**
  - Logs state transitions (`available` → `low` → `finished`), consumption timestamps, and quantity changes to power future predictive restocking algorithms and household activity feeds.

#### 5. JWT Authentication & Security
- Stateless JSON Web Tokens (JWT) using HMAC-SHA256 (`HS256`) configured via `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` (60 min), and `REFRESH_TOKEN_EXPIRE_DAYS` (30 days).
- Token payloads embed `user_id` and active `home_id`, validated via FastAPI dependency injection (`get_current_user`, `require_household_role("buyer")`).

#### 6. Mobile Client Adoption (Expo SDK 53 / React Native)
- Adopt the existing `kitchenSync-fe/GroceryApp` codebase under `mobile/`.
- Built on **Expo SDK 53** with React Native, providing:
  - In-aisle camera barcode scanning (`expo-camera`) mapping scanned EAN-13 barcodes to catalog `products.barcode`.
  - Offline-first cache with SQLite/WatermelonDB syncing state over WebSockets upon reconnect.
  - Platform-native notifications (APNs / FCM) with distinct audio cues for `low` vs `finished` grocery alerts.

---

### Consequences & Trade-offs
- **Positive:**
  - **Zero-Latency Integration:** Single database and runtime eliminates distributed network sync complexity between pantry and pricing engines.
  - **Seamless Consumer Loop:** The bridge from pantry depletion (`pantry_items`) to lowest-price shopping trip (`baskets/calculate`) directly solves the core user journey without manual list recreation.
  - **Real-Time Responsiveness:** Redis Pub/Sub provides sub-5ms event fanout to all active household WebSocket connections.
  - **Hybrid Catalog Flexibility:** Nullable `product_id` supports both barcode-scanned supermarket staples and custom family goods.
- **Negative / Mitigations:**
  - Additional infrastructure dependency on Redis (mitigated by lightweight Alpine Docker container and CI service container).
  - WebSockets in FastAPI require connection lifecycle management (mitigated by Redis connection pool singletons and heartbeat pings).

---

## ADR-008: Offline Delta-Sync & Pantry-to-Basket Auto-Replenishment Engine

### Status
**Accepted** (2026-11-19)

### Context & Problem Statement
Mobile pantry management operates under intermittent network connectivity (e.g. kitchen pantries, basements, or remote grocery stores). The mobile client maintains an offline SQLite store and queues local mutations. When reconnected, the client must reconcile changes with the backend deterministically without race conditions or data loss. Additionally, when pantry items deplete (`low` or `finished`), the household shopping basket must be automatically replenished to enable instant price optimization across retail chains.

### Decision & Technical Rationale
- **Last-Write-Wins (LWW) Conflict Resolution on `updated_at`:**
  - In `POST /api/v1/homes/{home_id}/pantry/sync`, incoming mutations provide client timestamps (`updated_at`).
  - If an existing item's server timestamp is strictly newer (`server.updated_at > mutation.updated_at`), the server record wins and the client mutation is rejected with conflict telemetry.
  - Otherwise, the mutation is applied and updated in the database.
- **Tombstone-Based Soft Deletion (`is_deleted`):**
  - Item deletions are recorded as soft deletes (`is_deleted = True`) with updated timestamps, ensuring sync responses include deleted items (`tombstones`) so offline clients can purge them locally.
- **Auto-Basket Replenishment Hook:**
  - When a pantry item transitions status to `low` or `finished` and references a valid catalog `product_id`, the system automatically upserts that product into the household's active Basket (`basket_items`).
  - If the item already exists in the basket, its quantity is incremented by the depleted quantity (default 1.00); otherwise, a new item is inserted.
  - Uncatalogued items (`product_id IS NULL`) are omitted from retail baskets but tracked in `pantry_logs`.

### Consequences & Trade-offs
- **Positive:** Deterministic offline reconciliation, idempotent batch sync, instant transition from pantry depletion to multi-store price comparison.
- **Negative / Mitigations:** Clock skew between client and server could influence LWW resolution; mitigated by clients synchronizing clock with server responses or fallback to server timestamp on creation.

---

## ADR-009: Redis Pub/Sub WebSocket Streaming & Buyer Push Alerts

### Status
**Accepted** (2026-11-19)

### Context & Problem Statement
Collaborative household grocery management requires instantaneous synchronization across multiple family members' mobile devices. When one member updates an inventory level or marks an item finished, other connected devices must update their view without manual pull-to-refresh. Furthermore, designated household buyers must receive high-priority push notifications when essential grocery staples reach `low` or `finished` status.

### Decision & Technical Rationale
- **Redis Pub/Sub WebSocket Backplane (`WS /api/v1/homes/{home_id}/ws`):**
  - WebSockets authenticate JWT tokens via query parameters or authorization headers and verify household membership before establishing the connection (rejecting unauthorized attempts with WebSocket policy violation code `1008`).
  - Upon connection, the server registers an asynchronous listener on Redis channel `home:{home_id}` via `redis.asyncio` Pub/Sub, broadcasting `ITEM_UPDATED` and `ITEM_DELETED` payloads.
  - An in-memory subscriber queue fallback is maintained to guarantee zero message loss during temporary Redis reconnections or in offline testing environments.
- **Asynchronous Buyer Push Notifications (FCM):**
  - When pantry items transition to `low` or `finished` status, a background task triggers Firebase Cloud Messaging (FCM) alerts dispatched to household buyer topics (`home_{home_id}_buyers`).
  - Missing or unconfigured Firebase service credentials in local development or CI environments are handled gracefully through a transparent simulation fallback, preventing test breakages.

### Consequences & Trade-offs
- **Positive:** Sub-10ms event dissemination to all active household clients; zero-friction buyer alerts; decoupled background notification execution.
- **Negative / Mitigations:** Active WebSocket connections require continuous network state tracking; mitigated through heartbeat pings (`ping`/`pong`) and clean connection teardown in finally blocks.

---

## ADR-010: Mobile Expo SDK 53 Client Migration, SQLite Offline Queue & SmartBasket View

### Status
**Accepted** (2026-11-19)

### Context & Problem Statement
To unify the KitchenSync mobile experience with the SmartBasket price optimization engine in a single monorepo, the Expo SDK 53 (`GroceryApp`) codebase must reside under `mobile/` and communicate directly with the FastAPI v1 REST and WebSocket endpoints. Mobile users frequently interact with pantry inventory in areas with poor connectivity, requiring local SQLite queuing (`react-native-sqlite-storage`) that seamlessly reconciles with `POST /api/v1/homes/{home_id}/pantry/sync` and feeds `POST /api/v1/baskets/calculate`.

### Decision & Technical Rationale
- **Monorepo Mobile Structure (`mobile/`):**
  - Migrated `kitchenSync-fe/GroceryApp` into `mobile/` with three dedicated domain layers:
    - `mobile/types/`: Strict TypeScript interfaces mirroring FastAPI Pydantic schemas (`PantryItemResponse`, `PantrySyncRequest`, `BasketCalculationResponse`, `WebSocketEventPayload`).
    - `mobile/db/`: Local SQLite persistence (`react-native-sqlite-storage`) managing `local_pantry_items`, `pending_sync` mutation queue, and `sync_meta` (`last_synced_at`), with an automatic in-memory fallback for Web and headless test environments.
    - `mobile/services/`: Unified FastAPI client (`api.ts`), offline-to-online sync & basket bridge (`sync.ts`), and real-time Redis Pub/Sub WebSocket stream (`websocket.ts`).
- **CI Quality Gates (`.github/workflows/ci.yml`):**
  - Added Node.js 20 setup, `npm ci`, TypeScript verification (`npm run typecheck` / `tsc --noEmit`), and ESLint checks (`npm run lint`) to the GitHub Actions pipeline.

### Consequences & Trade-offs
- **Positive:** End-to-end type safety across Python Pydantic schemas and TypeScript interfaces; offline-first resilience via SQLite `pending_sync`; single-tap price comparison for depleted pantry items.
- **Negative / Mitigations:** Monorepo CI execution time increases slightly with Node.js checks; mitigated via `actions/setup-node` npm dependency caching on `mobile/package-lock.json`.
