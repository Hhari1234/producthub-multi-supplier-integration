from __future__ import annotations

from typing import Optional

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import DataQualityReject, PipelineRun, Product, ProductHistory, RawProduct, Supplier, SupplierProductMapping
from app.schemas import HealthResponse, ProductOut, RejectOut, ReconciliationOut, RunOut, SupplierCreate, SupplierOut
from app.services.ingestion_service import ingest_supplier_file
from app.services.pipeline_service import generate_run_id, process_pipeline_run
from app.services.reports import build_quality_report, build_reconciliation_report, build_supplier_contribution_report, dashboard_summary

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        if db.query(Supplier).count() == 0:
            defaults = [
                ("SUPPLIER_A", "Supplier A", "csv"),
                ("SUPPLIER_B", "Supplier B", "json"),
                ("SUPPLIER_C", "Supplier C", "csv"),
            ]
            for code, name, fmt in defaults:
                db.add(Supplier(supplier_code=code, name=name, status="active", supported_format=fmt, total_imported_records=0))
            db.commit()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(settings.api_prefix + "/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return HealthResponse(status="ok", database="connected")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc


@app.post(settings.api_prefix + "/suppliers", response_model=SupplierOut)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.supplier_code == payload.supplier_code).first()
    if supplier:
        raise HTTPException(status_code=409, detail="supplier already exists")
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@app.get(settings.api_prefix + "/suppliers", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).order_by(Supplier.id).all()


@app.post(settings.api_prefix + "/ingestion/upload")
async def upload_feed(
    file: UploadFile = File(...),
    supplier_id: int = Form(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename is required")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="file is empty")
    try:
        result = ingest_supplier_file(db, supplier_id, file_bytes, file.filename)
        run = process_pipeline_run(db, supplier_id=supplier_id, run_id=result["run_id"])
        return {
            "supplier_id": supplier_id,
            "source_file": file.filename,
            "run_id": run.run_id,
            "imported_records": result["imported_records"],
            "valid_records": run.valid_records,
            "rejected_records": run.rejected_records,
            "status": run.status,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(settings.api_prefix + "/pipeline/run")
def run_pipeline(supplier_id: Optional[int] = None, db: Session = Depends(get_db)):
    run_id = generate_run_id()
    run = process_pipeline_run(db, supplier_id=supplier_id, run_id=run_id)
    return {"run_id": run.run_id, "status": run.status, "valid_records": run.valid_records, "rejected_records": run.rejected_records}


@app.get(settings.api_prefix + "/pipeline/runs", response_model=list[RunOut])
def list_pipeline_runs(db: Session = Depends(get_db)):
    return db.query(PipelineRun).order_by(PipelineRun.created_at.desc()).all()


@app.get(settings.api_prefix + "/pipeline/runs/{run_id}", response_model=RunOut)
def get_pipeline_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter(PipelineRun.run_id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.get(settings.api_prefix + "/products", response_model=list[ProductOut])
def list_products(
    brand: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    supplier: Optional[str] = Query(None),
    sort: str = Query("price_asc"),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if supplier:
        query = query.filter(Product.selected_supplier_name.ilike(f"%{supplier}%"))
    if sort == "price_desc":
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.price.asc())
    return query.all()


@app.get(settings.api_prefix + "/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@app.get(settings.api_prefix + "/products/{product_id}/traceability")
def get_traceability(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    mappings = db.query(SupplierProductMapping).filter(SupplierProductMapping.product_id == product_id).all()
    traceability = []
    for mapping in mappings:
        supplier = db.query(Supplier).filter(Supplier.id == mapping.supplier_id).first()
        raw = db.query(RawProduct).filter(
            RawProduct.supplier_id == mapping.supplier_id,
            RawProduct.source_record_key == mapping.source_record_key,
            RawProduct.source_file == mapping.source_file,
        ).first()
        traceability.append({
            "supplier": supplier.name if supplier else None,
            "supplier_product_id": mapping.supplier_product_id,
            "source_file": mapping.source_file,
            "source_record_key": mapping.source_record_key,
            "raw_payload": raw.source_payload if raw else None,
            "matched_value": mapping.matched_value,
        })
    return {"product_id": product_id, "product_name": product.product_name, "traceability": traceability}


@app.get(settings.api_prefix + "/quality/rejects", response_model=list[RejectOut])
def list_rejects(db: Session = Depends(get_db)):
    return db.query(DataQualityReject).order_by(DataQualityReject.created_at.desc()).all()


@app.get(settings.api_prefix + "/reports/reconciliation")
def reconciliation_report(db: Session = Depends(get_db)):
    return build_reconciliation_report(db)


@app.get(settings.api_prefix + "/reports/quality")
def quality_report(db: Session = Depends(get_db)):
    return build_quality_report(db)


@app.get(settings.api_prefix + "/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return dashboard_summary(db)


@app.get(settings.api_prefix + "/reports", response_model=dict)
def reports(db: Session = Depends(get_db)):
    return {
        "reconciliation": build_reconciliation_report(db),
        "quality": build_quality_report(db),
        "supplier_contribution": build_supplier_contribution_report(db),
    }


@app.get("/")
def root():
    return {"message": "ProductHub backend is running"}
