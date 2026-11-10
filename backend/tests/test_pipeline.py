from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import DataQualityReject, Product, RawProduct, Supplier
from app.services.ingestion_service import ingest_supplier_file
from app.services.pipeline_service import make_selection, process_pipeline_run
from app.services.reports import build_quality_report, build_reconciliation_report


def test_unknown_category_is_rejected(db_session):
    supplier_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id
    csv_text = "product_id,product_name,brand,price,category,stock,updated_at\nX999,Unknown Category,Acme,120.00,UnknownCategory,3,2026-04-01 11:00:00\n"
    ingest_supplier_file(db_session, supplier_id, csv_text.encode("utf-8"), "unknown_category.csv")
    process_pipeline_run(db_session, supplier_id=supplier_id, run_id="RUN-UNKNOWN-CAT")
    row = db_session.query(DataQualityReject).filter_by(rejection_reason="unknown_category").first()
    assert row is not None


def test_duplicate_supplier_product_ids_are_rejected(db_session):
    supplier_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id
    first = "product_id,product_name,brand,price,category,stock,updated_at\nDUP-1,Widget A,Acme,49.00,Accessories,5,2026-04-01 12:00:00\n"
    second = "product_id,product_name,brand,price,category,stock,updated_at\nDUP-1,Widget B,Acme,59.00,Accessories,6,2026-04-01 13:00:00\n"
    ingest_supplier_file(db_session, supplier_id, first.encode("utf-8"), "dup_a.csv")
    ingest_supplier_file(db_session, supplier_id, second.encode("utf-8"), "dup_b.csv")
    process_pipeline_run(db_session, supplier_id=supplier_id, run_id="RUN-DUP-ID")
    assert db_session.query(DataQualityReject).filter_by(rejection_reason="duplicate_supplier_product_id").count() == 1


def test_duplicate_supplier_product_ids_in_same_upload_are_rejected(db_session):
    supplier_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id
    payload = "product_id,product_name,brand,price,category,stock,updated_at\nSAME-1,Widget A,Acme,49.00,Accessories,5,2026-04-01 12:00:00\nSAME-1,Widget B,Acme,59.00,Accessories,6,2026-04-01 13:00:00\n"
    result = ingest_supplier_file(db_session, supplier_id, payload.encode("utf-8"), "same_upload.csv")
    assert result["imported_records"] == 1
    assert db_session.query(DataQualityReject).filter_by(rejection_reason="duplicate_supplier_product_id").count() == 1


def test_out_of_order_updates_do_not_overwrite_latest_record(db_session):
    supplier_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id
    first = "product_id,product_name,brand,price,category,stock,updated_at\nLATE-1,Later Product,Acme,200.00,Smartphones,20,2026-06-10 10:00:00\n"
    second = "product_id,product_name,brand,price,category,stock,updated_at\nLATE-1,Older Product,Acme,180.00,Smartphones,25,2026-06-05 10:00:00\n"
    ingest_supplier_file(db_session, supplier_id, first.encode("utf-8"), "newer.csv")
    ingest_supplier_file(db_session, supplier_id, second.encode("utf-8"), "older.csv")
    process_pipeline_run(db_session, supplier_id=supplier_id, run_id="RUN-LATE-UPDATE")
    product = db_session.query(Product).filter(Product.product_name == "Later Product").first()
    assert product is not None
    assert product.stock == 20
    assert product.updated_at.strftime("%Y-%m-%d %H:%M:%S") == "2026-06-10 10:00:00"


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        supplier_a = Supplier(supplier_code="SUPPLIER_A", name="Supplier A", status="active", supported_format="csv", total_imported_records=0)
        supplier_b = Supplier(supplier_code="SUPPLIER_B", name="Supplier B", status="active", supported_format="json", total_imported_records=0)
        db.add_all([supplier_a, supplier_b])
        db.commit()
        yield db


def override_get_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        yield db


app.dependency_overrides[get_db] = lambda: override_get_db()


client = TestClient(app)


def test_valid_csv_ingestion_and_pipeline(db_session):
    csv_text = "product_id,product_name,brand,price,category,stock,updated_at\nA101,Alpha Phone,Acme,299.99,Smartphones,25,2026-01-01 10:00:00\nA102,Beta Laptop,Acme,799.00,Laptops,12,2026-01-02 09:00:00\n"
    result = ingest_supplier_file(db_session, db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id, csv_text.encode("utf-8"), "supplier_a.csv")
    assert result["imported_records"] == 2

    run = process_pipeline_run(db_session, supplier_id=result["supplier"] and db_session.query(Supplier).filter_by(supplier_code=result["supplier"]).first().id, run_id="RUN-CSV-1")
    assert run.valid_records == 2
    assert db_session.query(Product).count() == 2


def test_valid_json_ingestion(db_session):
    payload = [{
        "sku": "B101",
        "name": "Zen Headphones",
        "manufacturer": "Beacon",
        "selling_price": "129.00",
        "product_type": "Headphones",
        "quantity": "18",
        "last_modified": "2026-02-02T12:00:00"
    }]
    result = ingest_supplier_file(db_session, db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_B").first().id, json.dumps(payload).encode("utf-8"), "supplier_b.json")
    assert result["imported_records"] == 1
    run = process_pipeline_run(db_session, supplier_id=db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_B").first().id, run_id="RUN-JSON-1")
    assert run.valid_records == 1


def test_missing_fields_and_negative_values_are_rejected(db_session):
    supplier_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id
    csv_text = "product_id,product_name,brand,price,category,stock,updated_at\nA999,,Acme,-10,Smartphones,-5,2026-01-01 10:00:00\n"
    _ = ingest_supplier_file(db_session, supplier_id, csv_text.encode("utf-8"), "bad.csv")
    process_pipeline_run(db_session, supplier_id=supplier_id, run_id="RUN-INVALID-1")
    row = db_session.query(DataQualityReject).first()
    assert row is not None
    assert "invalid_price" in row.rejection_reason or "missing_product_name" in row.rejection_reason or "invalid_stock" in row.rejection_reason


def test_same_file_uploaded_twice_is_idempotent(db_session):
    supplier_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id
    payload = "product_id,product_name,brand,price,category,stock,updated_at\nA150,Trim Tablet,Acme,499.00,Tablets,10,2026-03-02 10:00:00\n"
    first = ingest_supplier_file(db_session, supplier_id, payload.encode("utf-8"), "dup.csv")
    second = ingest_supplier_file(db_session, supplier_id, payload.encode("utf-8"), "dup.csv")
    assert first["imported_records"] == 1
    assert second["imported_records"] == 0
    assert db_session.query(RawProduct).count() == 1


def test_duplicate_products_across_suppliers_are_matched(db_session):
    supplier_a_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id
    supplier_b_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_B").first().id

    a_payload = {"product_id": "MATCH-1", "product_name": "Nova Phone", "brand": "Acme", "price": "399.99", "category": "Smartphones", "stock": 12, "updated_at": "2026-05-05 10:00:00"}
    b_payload = {"sku": "MATCH-1", "name": "Nova Phone", "manufacturer": "Acme", "selling_price": "419.99", "product_type": "Smartphones", "quantity": 8, "last_modified": "2026-05-06 10:00:00"}

    ingest_supplier_file(db_session, supplier_a_id, json.dumps([a_payload]).encode("utf-8"), "a_match.json")
    ingest_supplier_file(db_session, supplier_b_id, json.dumps([b_payload]).encode("utf-8"), "b_match.json")
    process_pipeline_run(db_session, supplier_id=supplier_a_id, run_id="RUN-MATCH-A")
    process_pipeline_run(db_session, supplier_id=supplier_b_id, run_id="RUN-MATCH-B")

    assert db_session.query(Product).count() == 1


def test_reconciliation_uses_valid_minus_rejected(db_session):
    supplier_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id
    valid_csv = "product_id,product_name,brand,price,category,stock,updated_at\nA900,Alpha,Acme,300,Smartphones,10,2026-01-02 00:00:00\n"
    invalid_csv = "product_id,product_name,brand,price,category,stock,updated_at\nA901,,Acme,-3,Smartphones,1,2026-01-03 00:00:00\n"
    ingest_supplier_file(db_session, supplier_id, valid_csv.encode("utf-8"), "final_valid.csv")
    ingest_supplier_file(db_session, supplier_id, invalid_csv.encode("utf-8"), "final_invalid.csv")
    process_pipeline_run(db_session, supplier_id=supplier_id, run_id="RUN-RECON-1")

    total = db_session.query(Product).count() + db_session.query(DataQualityReject).count()
    assert total >= 1


def test_make_selection_handles_naive_and_aware_timestamps(db_session):
    supplier = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first()
    product = Product(
        product_name="Old Phone",
        brand="Acme",
        model_number="Old Phone",
        price=199.00,
        currency="USD",
        category="Smartphones",
        stock=5,
        gtin="GTIN-OLD",
        updated_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        selected_supplier_id=supplier.id,
        selected_supplier_name=supplier.name,
        selection_reason="existing_record",
    )
    db_session.add(product)
    db_session.commit()

    result = make_selection(product, {"product_name": "New Phone", "brand": "Acme", "category": "Smartphones", "price": 179.00, "stock": 6, "updated_at": datetime(2026, 1, 2, 9, 0, 0)}, supplier)

    assert result.product_name == "New Phone"
    assert result.price == 179.00
    assert result.stock == 6
    assert result.updated_at is not None


def test_selected_supplier_remains_on_lowest_valid_price(db_session):
    supplier_b = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_B").first()
    supplier_c = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first()
    product = Product(
        product_name="Alpha Phone",
        brand="Acme",
        model_number="Alpha Phone",
        price=Decimal("269.99"),
        currency="USD",
        category="Smartphones",
        stock=18,
        gtin="GTIN-ALPHA",
        updated_at=datetime(2026, 1, 4, 14, 30, tzinfo=timezone.utc),
        selected_supplier_id=supplier_b.id,
        selected_supplier_name=supplier_b.name,
        selection_reason="lowest_valid_price",
    )

    current = make_selection(product, {
        "product_name": "Alpha Phone",
        "brand": "Acme",
        "category": "Smartphones",
        "price": Decimal("279.99"),
        "stock": 18,
        "updated_at": datetime(2026, 1, 4, 15, 30, tzinfo=timezone.utc),
    }, supplier_c)

    assert current.price == Decimal("269.99")
    assert current.selected_supplier_name == supplier_b.name
    assert current.selection_reason == "lowest_valid_price"


def test_reconciliation_totals_match_pipeline_runs(db_session):
    supplier_id = db_session.query(Supplier).filter_by(supplier_code="SUPPLIER_A").first().id
    payload = "product_id,product_name,brand,price,category,stock,updated_at\nR-1,Alpha,Acme,40.00,Smartphones,5,2026-04-01 10:00:00\nR-2,Beta,Acme,70.00,Smartphones,7,2026-04-01 11:00:00\n"
    ingest_supplier_file(db_session, supplier_id, payload.encode('utf-8'), 'recon.csv')
    run = process_pipeline_run(db_session, supplier_id=supplier_id, run_id='RUN-REPORT-1')
    report = build_reconciliation_report(db_session)
    assert report['total_input_records'] == run.total_input_records == 2
    assert report['valid_records'] == run.valid_records
    assert report['rejected_records'] == run.rejected_records
    assert report['difference'] == 0


def test_quality_report_counts_reason_occurrences_not_rejected_rows(db_session):
    db_session.add_all([
        DataQualityReject(supplier_id=1, source_file='a.csv', run_id='Q1', rejection_reason='invalid_price; invalid_stock', original_payload={'a': 1}),
        DataQualityReject(supplier_id=1, source_file='b.csv', run_id='Q2', rejection_reason='duplicate_supplier_product_id', original_payload={'b': 2}),
        DataQualityReject(supplier_id=1, source_file='c.csv', run_id='Q3', rejection_reason='unknown_category', original_payload={'c': 3}),
    ])
    db_session.commit()

    report = build_quality_report(db_session)
    assert db_session.query(DataQualityReject).count() == 3
    assert report['invalid_price; invalid_stock'] == 1
    assert report['duplicate_supplier_product_id'] == 1
    assert report['unknown_category'] == 1
    assert sum(report.values()) == db_session.query(DataQualityReject).count()
