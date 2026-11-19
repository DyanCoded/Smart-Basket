# Smart Basket — Release Notes v1.0.0

> **Milestone:** Phase 1 Final Release  
> **Tag:** `v1.0.0`  
> **Date:** November 2026  
> **Commit:** `main` baseline  

---

## 🚀 Overview

Smart Basket v1.0.0 marks the completion of **Phase 1** of the Smart Basket project. It delivers a production-ready, containerized backend engine that tracks supermarket catalog items, compares prices across regional supermarket branches in real time, and computes optimal multi-store shopping splits to maximize consumer savings.

---

## 📦 What's New in v1.0.0

### 1. Catalog & Multi-Store Pricing
- **Taxonomy & Metadata:** Universal grocery catalog with standard packaging units (e.g. 2L, 500g, 1kg), brands, categories, and unique EAN-13 barcodes.
- **Store Branches:** Support for major South African supermarket chains (Checkers, Woolworths Food, Pick n Pay, SPAR, Shoprite) across regional locations.
- **Active Pricing:** Track active shelf prices, promotional sale indicators, and branch inventory stock status.

### 2. Smart Basket Optimization Engine (Journey 2)
- **Single-Store Ranking:** Ranks all monitored supermarket branches deterministically from lowest to highest total cart cost.
- **Smart Mode (2-Store Split):** Evaluates multi-store splits where buying staple items at two different stores yields lower total costs than any single store.
- **Missing Item Handling:** Alerts users if a specific store branch lacks one or more requested items with partial subtotal calculations.
- **Exact Precision Math:** All currency calculations utilize standard `Decimal` arithmetic to guarantee zero floating-point calculation error.

### 3. Price History & Trend Intelligence (Journey 3)
- **Historical Timeseries:** Chronological price observations across configurable date windows for chart rendering.
- **Analytics Metrics:** All-time highest, lowest, and average prices across monitored stores.
- **Discount Veracity Scoring:** Automated algorithm (0–100 score) assessing whether an active promotion is a genuine deal or a minor cosmetic discount.

### 4. Developer Experience & OpenAPI Documentation
- **Interactive Explorers:** Swagger UI accessible at `/docs` (alias `/api/docs`) and ReDoc at `/redoc` (alias `/api/redoc`).
- **Exported Specifications:** Pre-generated OpenAPI 3.1.0 specifications at [`docs/openapi.json`](openapi.json) and [`docs/openapi.yaml`](openapi.yaml).
- **Postman Collection v2.1.0:** Ready-to-import client collection at [`docs/postman_collection.json`](postman_collection.json).
- **Automated Export CLI:** Script [`scripts/export_openapi.py`](../scripts/export_openapi.py) for one-step documentation regeneration.

### 5. Automated CI/CD & Testing
- **GitHub Actions Pipeline:** [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) spins up a PostgreSQL 16 container, applies Alembic migrations, verifies catalog seeding, checks Ruff/Black rules, and executes the Pytest test suite.
- **Comprehensive Test Suite:** 56 integration and unit tests covering search, price comparisons, combinatorial basket calculations, and documentation validation.

---

## 🛠️ Quick Installation & Verification

```bash
# 1. Clone repository
git clone https://github.com/DyanCoded/Smart-Basket.git
cd Smart-Basket

# 2. Virtual environment & dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# 3. Environment configuration
cp .env.example .env

# 4. Start database container
docker compose up -d

# 5. Apply migrations & seed catalog data
alembic upgrade head
python scripts/seed.py --verify

# 6. Run verification suite
python scripts/check.py

# 7. Start API server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📊 Phase 1 Backlog Milestone Summary

| Phase | Milestone / Backlog Issue | Status |
| :--- | :--- | :---: |
| **01. Discovery** | `[Spec]` Core User Journeys & Smart Basket Requirements (#1) | 🟢 Completed |
| **02. Design** | `[Data]` Conceptual Domain Model & Entity Relationships (#2) | 🟢 Completed |
| **03. Architecture**| `[Arch]` Tech Stack Selection & Database Evaluation (#3) | 🟢 Completed |
| **04. Tooling** | `[Setup]` Scaffolding, Directory Layout & Local Env (#4) | 🟢 Completed |
| **05. Data Layer** | `[Data]` Physical Database Schema & Baseline Migrations (#5) | 🟢 Completed |
| **06. Testing Data**| `[Data]` Catalog Seeding Script & Test Data Fixtures (#6) | 🟢 Completed |
| **07. Core API** | `[Backend]` Product Search & Store Pricing Endpoints (#7) | 🟢 Completed |
| **08. Algorithms** | `[Backend]` Basket Calculation & Multi-Store Optimization (#8) | 🟢 Completed |
| **09. Analytics** | `[Backend]` Price History Tracking & Intelligence APIs (#9) | 🟢 Completed |
| **10. DevOps** | `[CI/CD]` GitHub Actions Pipeline for Linting & Tests (#10) | 🟢 Completed |
| **11. Specs** | `[Docs]` OpenAPI / Swagger Specs & API Explorer (#11) | 🟢 Completed |
| **12. Delivery** | `[Release]` Final Packaging, Documentation & Review (#12) | 🟢 Completed |
