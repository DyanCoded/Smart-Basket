# Release Notes v2.0.0 — Unified SmartBasket + KitchenSync Pantry & Mobile Baseline

**Release Date:** 2026-11-20  
**Tag:** `v2.0.0`  
**Phase:** Phase 2 Final Release (Pre-Phase 3 Baseline)

---

## What's New in v2.0.0

### 1. Unified Household & Pantry Data Model (Issues #13 & #14)
- Ported KitchenSync's household and pantry schema directly into Smart Basket's FastAPI + PostgreSQL 16 stack via Alembic migration `0002_add_pantry_and_households.py`:
  - `users`, `homes`, `memberships` (`buyer` / `consumer` RBAC roles)
  - `pantry_items` (nullable `product_id` catalog bridge, `Numeric(10, 2)` quantities & thresholds, `ok` / `low` / `finished` status, `is_deleted` tombstones)
  - `pantry_logs` (state transition audit trail) & `baskets.home_id` linkage.

### 2. Stateless JWT Auth & Household RBAC (Issue #15)
- Added `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, and `/api/v1/homes` household & member management routes with bcrypt password hashing and strict `verify_home_membership` dependency guards (`403 Forbidden` isolation).

### 3. Pantry CRUD, Offline LWW Delta-Sync & Auto-Basket Bridge (Issue #16)
- Added `/api/v1/homes/{home_id}/pantry`, `POST /api/v1/homes/{home_id}/pantry/sync` (Last-Write-Wins conflict resolution on `updated_at`, tombstone propagation, graceful degradation for unknown client `product_id`s), and `GET /api/v1/homes/{home_id}/basket`.
- Marking any catalog-linked pantry item `low` or `finished` automatically upserts it into the household's active Smart Basket for immediate price optimization.

### 4. Redis 7 Pub/Sub WebSocket Stream & FCM Buyer Push Alerts (Issue #17)
- Added `WS /api/v1/homes/{home_id}/ws` authenticated via JWT and household membership, backed by `redis.asyncio` Pub/Sub (`channel: home:{home_id}`) broadcasting `ITEM_UPDATED` and `ITEM_DELETED` events in real time.
- Added background Firebase Cloud Messaging (FCM) buyer alerts (`src/services/notification_service.py`) with graceful simulation fallback in local and CI environments.

### 5. Expo Mobile Client (`mobile/`), 5-Chain Alignment & Store Selection Checklist (Issue #18 & ADR-011/012)
- Migrated the KitchenSync React Native / Expo app into `mobile/` (Expo SDK 58) with dedicated `mobile/types/`, `mobile/db/` (`react-native-sqlite-storage` `pending_sync` queue + Web fallback), and `mobile/services/` layers.
- Collapsed seed fixtures, APIs, and UI to **5 canonical national supermarket chains** (**Shoprite**, **Checkers**, **Pick n Pay**, **Woolworths Food**, **SPAR**) with full catalog coverage (`18 products × 5 chains = 90 active prices`) and zero branch/inventory noise.
- Added the **Included Stores** multi-select pill checklist (`store_ids` / `retailer_slugs` filtering on `POST /api/v1/baskets/calculate`) and interactive **Smart Mode (Split Basket)** toggle on the Optimizer screen.

---

## Verification Summary
- **Backend Quality Gate (`python scripts/check.py`):** Ruff PASS, Black PASS, **97/97 Pytest tests passing**.
- **Mobile Static Verification (`mobile/`):** `npx tsc --noEmit` PASS (0 errors), `npm run lint` PASS (0 errors).
