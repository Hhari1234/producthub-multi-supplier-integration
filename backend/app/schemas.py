from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class SupplierCreate(BaseModel):
    supplier_code: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    status: str = "active"
    supported_format: str = "csv"

    @field_validator("supplier_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper().replace(" ", "_")


class SupplierOut(BaseModel):
    id: int
    supplier_code: str
    name: str
    status: str
    supported_format: str
    total_imported_records: int
    last_ingestion_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UploadFileRequest(BaseModel):
    supplier_id: int


class PipelineRunCreate(BaseModel):
    supplier_id: Optional[int] = None


class ProductOut(BaseModel):
    id: int
    product_name: str
    brand: str
    model_number: Optional[str] = None
    price: float
    currency: str
    category: str
    stock: int
    gtin: Optional[str] = None
    updated_at: datetime
    selected_supplier_name: Optional[str] = None
    selection_reason: Optional[str] = None


class RejectOut(BaseModel):
    id: int
    supplier_id: int
    source_file: str
    run_id: str
    rejection_reason: str
    original_payload: dict[str, Any]
    created_at: datetime


class RunOut(BaseModel):
    run_id: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_input_records: int
    valid_records: int
    rejected_records: int
    inserted_records: int
    updated_records: int
    duplicate_records: int
    processing_duration: float
    failure_reason: Optional[str] = None


class ReconciliationOut(BaseModel):
    total_input_records: int
    valid_records: int
    rejected_records: int
    difference: int
    supplier_totals: dict[str, int]
    product_count: int


class HealthResponse(BaseModel):
    status: str
    database: str
