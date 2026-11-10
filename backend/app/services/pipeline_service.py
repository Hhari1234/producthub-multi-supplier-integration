from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_

from app.models import DataQualityReject, PipelineRun, Product, ProductHistory, RawProduct, Supplier, SupplierProductMapping
from app.services.matching_service import build_product_lookup, match_existing_product
from app.services.standardization import KNOWN_CATEGORIES, canonicalize_record


def json_safe(data):
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, Decimal):
        return str(data)
    if isinstance(data, dict):
        return {key: json_safe(value) for key, value in data.items()}
    if isinstance(data, list):
        return [json_safe(item) for item in data]
    return data


def generate_run_id():
    return datetime.now(timezone.utc).strftime("RUN-%Y%m%d-%H%M%S") + str(int(time.time() * 1000) % 100000)


def value_is_required(value):
    return value is not None and str(value).strip() != ""


def validate_record(canonical, supplier):
    reasons = []
    if not value_is_required(canonical.get("supplier_product_id")):
        reasons.append("missing_supplier_product_id")
    if not value_is_required(canonical.get("product_name")):
        reasons.append("missing_product_name")
    if not value_is_required(canonical.get("brand")):
        reasons.append("missing_brand")
    if canonical.get("price") is None or float(canonical.get("price", 0)) < 0:
        reasons.append("invalid_price")
    if canonical.get("stock") is None or int(canonical.get("stock", 0)) < 0:
        reasons.append("invalid_stock")
    if not value_is_required(canonical.get("category")):
        reasons.append("missing_category")
    elif canonical.get("category") not in KNOWN_CATEGORIES:
        reasons.append("unknown_category")
    if canonical.get("updated_at") is None:
        reasons.append("invalid_timestamp")
    if supplier is None:
        reasons.append("invalid_supplier_reference")
    if not reasons:
        return True, None
    return False, "; ".join(reasons)


def normalize_utc_datetime(value):
    if value is None:
        return None
    if not isinstance(value, datetime):
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def make_selection(product, canonical, supplier):
    incoming_updated_at = normalize_utc_datetime(canonical.get("updated_at"))
    existing_updated_at = normalize_utc_datetime(product.updated_at)
    if incoming_updated_at and existing_updated_at and incoming_updated_at < existing_updated_at:
        return product

    selected_supplier_updated = False
    if canonical.get("price") is not None:
        current_value = Decimal(str(product.price))
        incoming_value = Decimal(str(canonical["price"]))
        if incoming_value < current_value:
            product.price = incoming_value
            product.selection_reason = "lowest_valid_price"
            product.selected_supplier_id = supplier.id
            product.selected_supplier_name = supplier.name
            selected_supplier_updated = True
    if canonical.get("stock") is not None:
        product.stock = int(canonical["stock"])
    if canonical.get("product_name"):
        product.product_name = canonical["product_name"]
    if canonical.get("brand"):
        product.brand = canonical["brand"]
    if canonical.get("category"):
        product.category = canonical["category"]
    if canonical.get("gtin"):
        product.gtin = canonical["gtin"]
    if incoming_updated_at:
        product.updated_at = incoming_updated_at
    if not selected_supplier_updated and product.selected_supplier_id is None:
        product.selected_supplier_id = supplier.id
        product.selected_supplier_name = supplier.name
    product.selection_reason = "latest_valid_update" if product.selection_reason is None else product.selection_reason
    return product


def process_pipeline_run(db, supplier_id=None, run_id=None):
    if run_id is None:
        run_id = generate_run_id()

    run = db.query(PipelineRun).filter(PipelineRun.run_id == run_id).first()
    if run is None:
        run = PipelineRun(run_id=run_id, status="pending", start_time=datetime.now(timezone.utc))
        db.add(run)

    run.status = "running"
    db.flush()

    start = time.perf_counter()
    query = db.query(RawProduct)
    if supplier_id:
        query = query.filter(RawProduct.supplier_id == supplier_id)

    raw_rows = query.filter(RawProduct.status == "uploaded").all()
    run.total_input_records = len(raw_rows)

    product_lookup = build_product_lookup(db)
    supplier_lookup = {supplier.id: supplier for supplier in db.query(Supplier).all()}
    existing_mapping_keys = {
        (mapping.supplier_id, mapping.supplier_product_id)
        for mapping in db.query(SupplierProductMapping).all()
    }

    pending_rejects: list[DataQualityReject] = []
    pending_mappings: list[SupplierProductMapping] = []
    pending_history: list[ProductHistory] = []
    flush_every = 1000

    for raw in raw_rows:
        supplier = supplier_lookup.get(raw.supplier_id)
        if supplier is None:
            pending_rejects.append(DataQualityReject(
                supplier_id=raw.supplier_id,
                source_file=raw.source_file,
                run_id=run_id,
                rejection_reason="invalid_supplier_reference",
                original_payload=raw.source_payload,
            ))
            raw.status = "rejected"
            run.rejected_records += 1
            continue

        canonical = canonicalize_record(raw.source_payload, supplier.supplier_code, raw.source_file, run_id)
        canonical["supplier_id"] = supplier.id
        valid, reason = validate_record(canonical, supplier)

        if not valid:
            pending_rejects.append(DataQualityReject(
                supplier_id=supplier.id,
                source_file=raw.source_file,
                run_id=run_id,
                rejection_reason=reason,
                original_payload=raw.source_payload,
            ))
            raw.status = "rejected"
            run.rejected_records += 1
            continue

        supplier_product_id = str(canonical.get("supplier_product_id") or raw.source_record_key)
        if (supplier.id, supplier_product_id) in existing_mapping_keys:
            pending_rejects.append(DataQualityReject(
                supplier_id=supplier.id,
                source_file=raw.source_file,
                run_id=run_id,
                rejection_reason="duplicate_supplier_product_id",
                original_payload=raw.source_payload,
            ))
            raw.status = "rejected"
            run.rejected_records += 1
            continue

        existing_product, match_method = match_existing_product(db, canonical, product_lookup)
        if existing_product is None:
            product = Product(
                product_name=canonical["product_name"],
                brand=canonical["brand"],
                model_number=canonical["model_number"],
                price=Decimal(str(canonical["price"])),
                currency=canonical["currency"],
                category=canonical["category"],
                stock=int(canonical["stock"]),
                gtin=canonical.get("gtin"),
                updated_at=canonical["updated_at"],
                selected_supplier_id=supplier.id,
                selected_supplier_name=supplier.name,
                selection_reason=f"new_record_{match_method}",
            )
            db.add(product)
            db.flush()
            run.inserted_records += 1
            product_saved = product
            if product.gtin:
                product_lookup["gtin"][product.gtin] = product
            if product.brand and product.model_number:
                product_lookup["brand_model"][(product.brand, product.model_number)] = product
            if product.brand and product.product_name:
                product_lookup["brand_name"][(product.brand, product.product_name)].append(product)
            if product.brand:
                product_lookup["brand"][product.brand].append(product)
        else:
            product = existing_product
            product = make_selection(product, canonical, supplier)
            run.updated_records += 1
            product_saved = product

        pending_mappings.append(SupplierProductMapping(
            product_id=product_saved.id,
            supplier_id=supplier.id,
            supplier_product_id=supplier_product_id,
            source_file=raw.source_file,
            source_record_key=raw.source_record_key,
            matched_value=match_method,
        ))
        existing_mapping_keys.add((supplier.id, supplier_product_id))

        pending_history.append(ProductHistory(
            product_id=product_saved.id,
            supplier_id=supplier.id,
            run_id=run_id,
            change_type="upsert" if existing_product else "insert",
            old_value=json.dumps(json_safe(existing_product.__dict__) if existing_product else {}, default=str),
            new_value=json.dumps(json_safe({
                "product_name": product_saved.product_name,
                "brand": product_saved.brand,
                "category": product_saved.category,
                "price": str(product_saved.price),
                "stock": product_saved.stock,
            }), default=str),
            details={"source_file": raw.source_file, "supplier_code": supplier.supplier_code, "match_method": match_method},
        ))
        raw.status = "processed"
        raw.normalized_payload = json_safe(canonical)
        run.valid_records += 1

        if len(pending_rejects) >= flush_every or len(pending_mappings) >= flush_every or len(pending_history) >= flush_every:
            db.add_all(pending_rejects)
            db.add_all(pending_mappings)
            db.add_all(pending_history)
            pending_rejects.clear()
            pending_mappings.clear()
            pending_history.clear()
            db.flush()

    if pending_rejects:
        db.add_all(pending_rejects)
    if pending_mappings:
        db.add_all(pending_mappings)
    if pending_history:
        db.add_all(pending_history)
    db.flush()
    run.status = "completed_with_errors" if run.rejected_records else "completed"
    run.end_time = datetime.now(timezone.utc)
    run.processing_duration = round(time.perf_counter() - start, 2)
    db.commit()
    db.refresh(run)
    return run
