from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func

from app.models import DataQualityReject, PipelineRun, Product, Supplier


def dashboard_summary(db):
    total_suppliers = db.query(Supplier).count()
    total_products = db.query(Product).count()
    total_rejects = db.query(DataQualityReject).count()
    latest_run = db.query(PipelineRun).order_by(PipelineRun.created_at.desc()).first()
    return {
        "total_suppliers": total_suppliers,
        "total_products": total_products,
        "rejected_records": total_rejects,
        "latest_pipeline": latest_run.run_id if latest_run else None,
        "latest_duration": float(latest_run.processing_duration) if latest_run else 0.0,
        "status": latest_run.status if latest_run else "pending",
    }


def build_reconciliation_report(db):
    total_input = db.query(func.coalesce(func.sum(PipelineRun.total_input_records), 0)).scalar() or 0
    valid_records = db.query(func.coalesce(func.sum(PipelineRun.valid_records), 0)).scalar() or 0
    rejected_records = db.query(func.coalesce(func.sum(PipelineRun.rejected_records), 0)).scalar() or 0
    product_count = db.query(Product).count()
    supplier_totals = {}
    for supplier in db.query(Supplier).all():
        supplier_totals[supplier.supplier_code] = db.query(func.count()).select_from(Product).join(Product.selected_supplier).filter(Product.selected_supplier_id == supplier.id).scalar() or 0
    return {
        "total_input_records": int(total_input),
        "valid_records": int(valid_records),
        "rejected_records": int(rejected_records),
        "difference": int(total_input - (valid_records + rejected_records)),
        "supplier_totals": supplier_totals,
        "product_count": product_count,
    }


def build_quality_report(db):
    rows = db.query(DataQualityReject.rejection_reason, func.count(DataQualityReject.id)).group_by(DataQualityReject.rejection_reason).all()
    return {reason: count for reason, count in rows}


def build_supplier_contribution_report(db):
    supplier_map = defaultdict(int)
    for product in db.query(Product).all():
        if product.selected_supplier_name:
            supplier_map[product.selected_supplier_name] += 1
    return dict(sorted(supplier_map.items()))
