# ProductHub Architecture

ProductHub is structured around a single ingestion-to-publishing pipeline:

1. Ingest supplier feeds from CSV or JSON files
2. Normalize fields into a canonical schema
3. Validate and reject invalid rows
4. Match products across suppliers
5. Resolve conflicts and publish the unified product catalogue
6. Record pipeline metrics, quality rejects, and history

## Components

- API layer: FastAPI routes
- Domain services: ingestion, standardization, matching, reports
- Persistence layer: SQLAlchemy models and PostgreSQL storage
- Frontend: React dashboard for operational visibility

## Judge-ready technical summary

ProductHub is a multi-supplier product data integration platform designed to ingest heterogeneous CSV and JSON feeds, reconcile them into a canonical model, and publish a single trusted catalogue. The system validates incoming rows, quarantines bad data for traceability, and applies deterministic matching rules to identify the same product across suppliers. Once matched, conflicts such as price, stock, and product metadata are resolved using explicit business rules rather than ad hoc logic. The result is an auditable pipeline with raw source preservation, publish-time history, and operational dashboards for quality, traceability, and reconciliation.
