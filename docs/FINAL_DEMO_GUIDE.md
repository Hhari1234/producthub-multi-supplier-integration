# ProductHub Final Demo Guide

## 1. Demo status and environment

This guide reflects the verified live setup used in the project:

- Backend: FastAPI running against PostgreSQL 17
- Frontend: Vite app served at `http://localhost:4173`
- API base: `http://localhost:8000/api/v1`
- Docker: not validated in this environment because the Docker engine is unavailable

## 2. Demo storyline for judges

### 2.1 Introduce the problem

What to open:
- The dashboard and supplier upload screen

What to do:
- Explain that different suppliers send the same product in different shapes and formats.

What result to show:
- Different fields like `product_id`, `sku`, or `item_code`

What to explain:
- ProductHub solves the inconsistency by normalizing supplier inputs into one canonical product model.

### 2.2 Introduce ProductHub

What to open:
- Dashboard and architecture overview

What to do:
- Show the stack summary: FastAPI, React, PostgreSQL, SQLAlchemy

What result to show:
- The app can ingest, validate, match, and report in one workflow.

What to explain:
- ProductHub is a practical integration layer between supplier feeds and a single trusted catalogue.

### 2.3 Show the architecture and technology stack

What to open:
- README and dashboard

What to do:
- Walk through the pipeline: ingest -> validate -> standardize -> match -> resolve -> report

What result to show:
- The app uses live API calls plus PostgreSQL persistence.

What to explain:
- Suppliers feed raw data, ProductHub stores raw payloads for traceability, then publishes a single canonical product view.

### 2.4 Open the dashboard

What to open:
- `http://localhost:4173`

What to do:
- Refresh the dashboard and point to the KPI cards.

What result to show:
- Supplier count, unified products, rejected records, and latest pipeline run

What to explain:
- The dashboard shows real operational metrics instead of mock data.

### 2.5 Upload Supplier A CSV

What to open:
- Suppliers tab and Upload tab

What to do:
- Upload `docs/demo-data/supplier_a_demo.csv` against Supplier A

What result to show:
- Successful upload status and a non-zero imported record count when applicable

What to explain:
- Supplier A uses a CSV structure with `product_id` and other supplier-specific columns that ProductHub maps to a standard model.

### 2.6 Upload Supplier B JSON

What to open:
- Upload tab

What to do:
- Upload `docs/demo-data/supplier_b_demo.json`

What result to show:
- Valid records ingested and some rows flagged as rejected if invalid

What to explain:
- Supplier B uses a different schema and JSON structure. ProductHub still maps fields consistently.

### 2.7 Upload Supplier C CSV

What to open:
- Upload tab

What to do:
- Upload `docs/demo-data/supplier_c_demo.csv`

What result to show:
- A successful import with product rows available in the catalogue

What to explain:
- The platform supports multiple suppliers without requiring each one to follow the same schema.

### 2.8 Show validation and rejected records

What to open:
- Quality tab and rejects view

What to do:
- Inspect rejected rows and reasons such as invalid price, unknown category, or missing brand

What result to show:
- A clean separation between accepted rows and data-quality failures

What to explain:
- ProductHub does not silently hide bad data; it preserves the reason and the raw payload.

### 2.9 Explain product standardization

What to open:
- Catalogue and product details

What to do:
- Compare fields from the supplier payload with the canonical product display

What result to show:
- Product name, brand, category, currency, price, stock, and GTIN are normalized

What to explain:
- ProductHub converts different supplier schemas into one clear, predictable structure.

### 2.10 Demonstrate GTIN-based matching

What to open:
- Product catalogue and traceability records

What to do:
- Point out identical or overlapping products that share GTIN values

What result to show:
- Records merge into one product entry when GTIN matches

What to explain:
- GTIN is the strongest identifier because it represents the product itself, not just the supplier listing.

### 2.11 Demonstrate matching using brand and model where appropriate

What to open:
- Product matching or traceability views

What to do:
- Show records without GTIN that still match using brand-plus-model logic

What result to show:
- The product is still united even when GTIN is missing or incomplete

What to explain:
- If GTIN is not present, ProductHub falls back to a deterministic match using trusted fields.

### 2.12 Explain duplicate prevention

What to open:
- Quality and raw records view

What to do:
- Call out duplicate supplier product IDs or repeated uploads

What result to show:
- Duplicate rows are rejected instead of creating a double-counted catalogue product

What to explain:
- Idempotency prevents repeated uploads from creating duplicate inventory.

### 2.13 Demonstrate conflict resolution and lowest valid price selection

What to open:
- Catalogue listing and price comparison in the report views

What to do:
- Compare the same product across suppliers with different prices or stock values

What result to show:
- The lowest valid price is selected for the canonical record

What to explain:
- This is a business rule: choose the best valid offer while keeping supplier traceability intact.

### 2.14 Open the unified product catalogue

What to open:
- Catalogue tab

What to do:
- Browse the final unified list

What result to show:
- Single canonical products rather than supplier-by-supplier duplicates

What to explain:
- The catalogue is the clean source of truth for downstream systems.

### 2.15 Show product traceability and original payloads

What to open:
- Traceability tab

What to do:
- Click a product and inspect original supplier payloads and source file details

What result to show:
- Full lineage from raw supplier data to final unified product

What to explain:
- Because every decision is traceable, auditing and support are straightforward.

### 2.16 Show product history

What to open:
- Product history or traceability panel

What to do:
- Review updates across runs and supplier changes

What result to show:
- History of product changes and matching decisions

What to explain:
- ProductHub keeps the record of how a product became the canonical version.

### 2.17 Show pipeline runs

What to open:
- Pipeline tab

What to do:
- Review the latest run IDs and timestamps

What result to show:
- Pipeline execution metadata, completion status, and run summary

What to explain:
- Every ingestion and match cycle is logged and reviewable.

### 2.18 Show data quality and reconciliation reports

What to open:
- Reports tab

What to do:
- Inspect reconciliation totals and quality metrics

What result to show:
- Valid, rejected, and reconciled row counts remain aligned

What to explain:
- Reconciliation validates that the business rules hold and nothing was silently lost.

### 2.19 Explain the PostgreSQL database design

What to open:
- Database schema or docs

What to do:
- Walk through tables such as suppliers, raw_products, products, product_history, data_quality_rejects, and pipeline_runs

What result to show:
- A relational backbone with auditability and operational reporting

What to explain:
- PostgreSQL gives reliable transactions, indexing, and traceability for a live product catalog.

### 2.20 Present actual performance benchmark results

What to open:
- README or benchmark notes

What to do:
- Summarize the verified benchmark numbers

What result to show:
- 100k dataset completed with `reconciled=True` and `status='completed'`

What to explain:
- ProductHub handles large supplier datasets efficiently while preserving data quality and reconciliation.

## 3. Demo command checklist

```powershell
# Backend
cd C:\Users\harir\Downloads\yottaflex-hackathon-project\backend
$env:DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/producthub'
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd C:\Users\harir\Downloads\yottaflex-hackathon-project\frontend
npm run dev -- --host 0.0.0.0
```

Open:
- `http://localhost:4173`

## 4. Validation checklist before demo

- Dashboard loads without a fetch error
- Suppliers page loads
- Upload works for CSV and JSON
- Product catalogue shows real records
- Quality rejects are visible
- Pipeline and reports are populated
- Reconciliation is consistent

## 5. Docker note

Docker is configured in the repository, but the Docker engine is not currently available in this environment. Until Docker Desktop or the engine is active, the verified live path remains the local PostgreSQL-backed mode.
