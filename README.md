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
| **01. Discovery** | `[Spec]` Core User Journeys & Smart Basket Requirements | 🟡 In Progress |
| **02. Design** | `[Data]` Conceptual Domain Model & Entity Relationships | ⚪ Planned |
| **03. Architecture**| `[Arch]` Tech Stack Selection & Database Evaluation | ⚪ Planned |
| **04. Tooling** | `[Setup]` Scaffolding, Directory Layout & Local Env | ⚪ Planned |
| **05. Data Layer** | `[Data]` Physical Database Schema & Baseline Migrations | ⚪ Planned |
| **06. Testing Data**| `[Data]` Catalog Seeding Script & Test Data Fixtures | ⚪ Planned |
| **07. Core API** | `[Backend]` Product Search & Store Pricing Endpoints | ⚪ Planned |
| **08. Algorithms** | `[Backend]` Basket Calculation & Multi-Store Optimization | ⚪ Planned |
| **09. Analytics** | `[Backend]` Price History Tracking & Intelligence APIs | ⚪ Planned |
| **10. DevOps** | `[CI/CD]` GitHub Actions Pipeline for Linting & Tests | ⚪ Planned |
| **11. Specs** | `[Docs]` OpenAPI / Swagger Specs & API Explorer | ⚪ Planned |
| **12. Delivery** | `[Release]` Final Packaging, Documentation & Review | ⚪ Planned |

---

## 🚀 Getting Started

*(Setup instructions will be updated as tooling and container configurations are finalized in Issue #4).*

### Prerequisites
- Git
- Runtime environment (Node.js / Python / Docker — *TBD in Issue #3*)

### Local Setup
```bash
# Clone the repository
git clone https://github.com/DyanCoded/Smart-Basket.git
cd Smart-Basket

# Set up environment variables
cp .env.example .env