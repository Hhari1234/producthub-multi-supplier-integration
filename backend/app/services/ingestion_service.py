from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import DataQualityReject, RawProduct, Supplier
from app.services.pipeline_service import generate_run_id


def _hash_record(record: dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _read_records(file_obj, filename: str):
    if filename.lower().endswith(".csv"):
        if isinstance(file_obj, (bytes, bytearray)):
            text = file_obj.decode("utf-8-sig")
            data = list(csv.DictReader(io.StringIO(text)))
        else:
            file_obj.seek(0)
            data = list(csv.DictReader(io.TextIOWrapper(file_obj, encoding="utf-8-sig")))
        return data

    if filename.lower().endswith(".json"):
        if isinstance(file_obj, (bytes, bytearray)):
            payload = json.loads(file_obj.decode("utf-8"))
        else:
            file_obj.seek(0)
            payload = json.load(file_obj)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return [payload]
        raise ValueError("JSON payload must be an object or array")

    raise ValueError("Unsupported file type")


def ingest_supplier_file(db: Session, supplier_id: int, file_obj, filename: str):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if supplier is None:
        raise ValueError("Unknown supplier reference")

    run_id = generate_run_id()
    records = _read_records(file_obj, filename)
    if not records:
        raise ValueError("Input file is empty")

    inserted = 0
    existing_keys = {
        row[0] for row in db.query(RawProduct.source_record_key).filter(
            RawProduct.supplier_id == supplier.id,
            RawProduct.source_file == filename,
        ).all()
    }
    seen_source_keys: set[str] = set(existing_keys)
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            db.add(DataQualityReject(
                supplier_id=supplier.id,
                source_file=filename,
                run_id=run_id,
                rejection_reason="malformed_record",
                original_payload={"index": index, "value": record},
            ))
            continue

        source_key = str(
            record.get("supplier_product_id")
            or record.get("product_id")
            or record.get("sku")
            or record.get("item_code")
            or _hash_record(record)
        )
        source_file = filename

        if source_key in seen_source_keys:
            db.add(DataQualityReject(
                supplier_id=supplier.id,
                source_file=source_file,
                run_id=run_id,
                rejection_reason="duplicate_supplier_product_id",
                original_payload=record,
            ))
            continue
        seen_source_keys.add(source_key)

        raw = RawProduct(
            supplier_id=supplier.id,
            source_file=source_file,
            source_record_key=source_key,
            source_payload=record,
            run_id=run_id,
            status="uploaded",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        try:
            db.add(raw)
            db.flush()
        except IntegrityError:
            db.rollback()
            db.add(DataQualityReject(
                supplier_id=supplier.id,
                source_file=source_file,
                run_id=run_id,
                rejection_reason="duplicate_supplier_product_id",
                original_payload=record,
            ))
            continue
        inserted += 1

    supplier.total_imported_records += inserted
    supplier.last_ingestion_at = datetime.now(timezone.utc)
    db.commit()

    supplier_code = db.query(Supplier.supplier_code).filter(Supplier.id == supplier_id).scalar()
    return {"run_id": run_id, "imported_records": inserted, "supplier": supplier_code or supplier.supplier_code}
