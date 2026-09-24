# Smart Basket — System Requirements & User Journeys Specification

## 1. System Overview
Smart Basket is a real-time grocery price intelligence and basket optimization engine. It enables shoppers to build shopping lists, compare total basket costs across regional supermarkets, evaluate historical pricing trends, and calculate whether splitting a basket across multiple stores yields meaningful cost savings.

---

## 2. Core User Personas

### Everyday Shopper
Needs to quickly look up items, check prices across different local supermarket chains, build a shopping list, and determine which store (or combination of stores) provides the cheapest total trip.

### Catalog Manager / Admin System
Manages catalog taxonomy (categories, universal barcodes/UPCs), audits store branch records, and oversees automated or bulk price updates.

---

## 3. Primary User Journeys & Acceptance Workflows

### Journey 1: Multi-Store Basket Comparison
- **List Construction:** Shopper adds $N$ grocery items with required quantities to their virtual basket (e.g., 2 × Milk 2L, 1 × Brown Bread 700g, 1 × Butter 500g).
- **Evaluation:** The engine aggregates active prices for all items across participating retailers (e.g., Checkers, Woolworths, Pick n Pay).
- **Single-Store Ranking:** The system displays a ranked list of stores from lowest to highest total cart cost.
- **Availability & Partial Matches:** If a store does not stock an item in the basket:
  - The store is flagged as `PARTIAL_MATCH`.
  - The subtotal of available items is calculated, accompanied by an explicit list of missing items.

### Journey 2: Smart Split-Basket Optimization
- Shopper selects the "Optimize Basket" option.
- The engine identifies the cheapest store for each individual item in the basket.
- The engine outputs a recommended split (e.g., *"Buy Item A & B at Checkers for R75, Buy Item C at Pick n Pay for R45. Total: R120, saving R18 compared to the best single-store option"*).

### Journey 3: Single-Item Search & Price History
- Shopper searches for a specific item (by brand, product name, or barcode).
- The system returns:
  - Current active prices across all nearby branches.
  - Unit-price normalization (e.g., price per 100g, per 100ml, or per kg).
  - 30-day/90-day price trend graphs, highlighting whether the current price is at an all-time low or flagged as a promotional discount.

---

## 4. System Boundaries & Constraints

### Unit Standardization
- Products must declare a base unit type (`g`, `ml`, `unit`, `kg`, `l`) and package quantity.
- Price comparisons calculate normalized unit prices ($Price / Unit$) to ensure fair comparisons across non-identical packaging sizes.

### Currency & Precision
- All currency amounts are stored in cents/integers (or two-decimal precision) to eliminate floating-point arithmetic errors.

### Out of Scope (Phase 1)
- E-commerce checkout, payment processing, or third-party delivery dispatch.
- Real-time GPS driver tracking.
- User authentication/social logins (Phase 1 focuses entirely on the core data engine and basket optimization APIs).
