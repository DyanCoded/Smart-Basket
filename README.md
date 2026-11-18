# Smart Basket

> Real-time grocery price intelligence and basket optimization engine featuring multi-store comparison, shopping lists, and price tracking.

---

## 📌 Project Overview
Smart Basket is a data-driven platform designed to eliminate the manual effort of hunting across multiple supermarket chains for the best grocery prices. By tracking catalog metadata, price changes over time, and store inventory, the Smart Basket engine calculates the most cost-effective shopping strategy—whether buying everything from a single store or intelligently splitting the basket across multiple retailers.

---

## 🎯 Core Features
- **Catalog Search & Discovery:** Search and filter universal grocery items across categories, brands, and standard packaging sizes.
- **Multi-Store Price Comparison:** View current, real-time prices for any item across multiple supermarket chains and specific branches.
- **Smart Basket Optimization:**
  - **Single-Store Ranking:** Calculates total basket cost per retailer to identify the cheapest single location.
  - **Basket Splitter (Smart Mode):** Evaluates multi-store splits to maximize user savings on larger shopping runs.
  - **Missing Item Handling:** Alerts users if a specific store lacks an item in their basket.
- **Price History & Trend Intelligence:** Track price fluctuations, identify genuine discounts vs. artificial sales, and monitor price trends over time.

---

## 👥 User Personas & Core Journeys
1. **The Everyday Shopper:**
   - Searches for common household staples.
   - Builds a weekly grocery basket and requests an optimized store breakdown.
   - Checks historical price trends to decide whether to buy now or wait for promotions.
2. **The Catalog Admin / System:**
   - Ingests and maintains supermarket chains, store locations, and product taxonomies.
   - Updates store-specific prices and logs historical changes.

---

## 🏗️ Project Architecture & Status

This project is engineered iteratively following a structured backlog pipeline:

| Phase | Milestone / Issue | Status |
| :--- | :--- | :---: |
| **01. Discovery** | `[Spec]` Core User Journeys & Smart Basket Requirements | 🟢 Completed |
| **02. Design** | `[Data]` Conceptual Domain Model & Entity Relationships | 🟢 Completed |
| **03. Architecture**| `[Arch]` Tech Stack Selection & Database Evaluation | 🟢 Completed |
| **04. Tooling** | `[Setup]` Scaffolding, Directory Layout & Local Env | 🟢 Completed |
| **05. Data Layer** | `[Data]` Physical Database Schema & Baseline Migrations | 🟢 Completed |
| **06. Testing Data**| `[Data]` Catalog Seeding Script & Test Data Fixtures | 🟢 Completed |
| **07. Core API** | `[Backend]` Product Search & Store Pricing Endpoints | 🟢 Completed |
| **08. Algorithms** | `[Backend]` Basket Calculation & Multi-Store Optimization | 🟢 Completed |
| **09. Analytics** | `[Backend]` Price History Tracking & Intelligence APIs | 🟢 Completed |
| **10. DevOps** | `[CI/CD]` GitHub Actions Pipeline for Linting & Tests | 🟢 Completed |
| **11. Specs** | `[Docs]` OpenAPI / Swagger Specs & API Explorer | 🟢 Completed |
| **12. Delivery** | `[Release]` Final Packaging, Documentation & Review | ⚪ Planned |

---

## 🚀 Getting Started

### Prerequisites
- Git
- Python 3.11+
- Docker & Docker Compose (for PostgreSQL 16)

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/DyanCoded/Smart-Basket.git
   cd Smart-Basket
   ```

2. **Set up virtual environment & install dependencies:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   # Install development dependencies:
   pip install -r requirements-dev.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```

4. **Start local PostgreSQL 16 database:**
   ```bash
   docker compose up -d
   ```

5. **Apply database migrations & seed catalog data:**
   ```bash
   alembic upgrade head
   python scripts/seed.py
   # Or run via SQL directly:
   # psql -h localhost -U postgres -d smart_basket -f scripts/seed.sql
   ```

6. **Run test suite & code quality checks:**
   ```bash
   # Run automated verification suite (linter, formatter check, tests)
   python scripts/check.py

   # Or run individually:
   python -m pytest
   python -m ruff check .
   python -m black --check .
   ```

7. **Start local development API server:**
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## 📖 API Documentation & Interactive Explorer

Smart Basket includes auto-generated OpenAPI 3.1.0 specifications and interactive documentation explorers:

### Interactive Documentation UIs
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) (alias: [/api/docs](http://localhost:8000/api/docs))
- **ReDoc UI:** [http://localhost:8000/redoc](http://localhost:8000/redoc) (alias: [/api/redoc](http://localhost:8000/api/redoc))

### Exported Specifications & Client Collections
- **OpenAPI 3.1.0 JSON Spec:** [`docs/openapi.json`](docs/openapi.json) (live endpoint: `/openapi.json`)
- **OpenAPI 3.1.0 YAML Spec:** [`docs/openapi.yaml`](docs/openapi.yaml) (live endpoint: `/openapi.yaml`)
- **Postman Collection v2.1.0:** [`docs/postman_collection.json`](docs/postman_collection.json) — Ready for one-click import into Postman or Insomnia.

### Regenerating API Artifacts
Whenever routes, Pydantic schemas, or examples change, regenerate the documentation artifacts with:
```bash
python scripts/export_openapi.py
```

### Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service liveness and operational readiness check |
| `GET` | `/api/v1/products` | Search catalog by partial name, brand, barcode, or category |
| `GET` | `/api/v1/products/{id}` | Detailed product metadata including packaging unit size |
| `GET` | `/api/v1/products/{id}/prices` | Active prices and stock status across monitored stores |
| `GET` | `/api/v1/products/{id}/history` | Chronological price timeseries points for charting |
| `GET` | `/api/v1/products/{id}/intelligence` | Trend analytics, inflation metrics, and deal veracity score |
| `GET` | `/api/v1/stores` | Supermarket chains, retailer brands, and branch locations |
| `POST`| `/api/v1/baskets/calculate` | Single-store totals and Smart Mode multi-store split optimization |
