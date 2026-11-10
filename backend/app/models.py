from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    supplier_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    status = Column(String(50), default="active")
    supported_format = Column(String(20), default="csv")
    total_imported_records = Column(Integer, default=0, nullable=False)
    last_ingestion_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    raw_products = relationship("RawProduct", back_populates="supplier")
    category_mappings = relationship("CategoryMapping", back_populates="supplier")
    quality_rejects = relationship("DataQualityReject", back_populates="supplier")
    mappings = relationship("SupplierProductMapping", back_populates="supplier")
    products = relationship("Product", back_populates="selected_supplier")


class RawProduct(Base):
    __tablename__ = "raw_products"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    source_file = Column(String(255), nullable=False)
    source_record_key = Column(String(255), nullable=False, index=True)
    source_payload = Column(JSON, nullable=False)
    normalized_payload = Column(JSON, nullable=True)
    run_id = Column(String(50), nullable=False, index=True)
    status = Column(String(50), default="uploaded", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    supplier = relationship("Supplier", back_populates="raw_products")

    __table_args__ = (
        UniqueConstraint("supplier_id", "source_record_key", "source_file", name="uq_raw_supplier_record"),
        Index("ix_raw_records_supplier_run", "supplier_id", "run_id"),
    )


class CategoryMapping(Base):
    __tablename__ = "category_mappings"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    source_category = Column(String(100), nullable=False)
    mapped_category = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    supplier = relationship("Supplier", back_populates="category_mappings")

    __table_args__ = (UniqueConstraint("supplier_id", "source_category", name="uq_supplier_category"),)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(255), nullable=False)
    brand = Column(String(200), nullable=False)
    model_number = Column(String(100), nullable=True)
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    category = Column(String(100), nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    gtin = Column(String(50), nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    selected_supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    selected_supplier_name = Column(String(200), nullable=True)
    selection_reason = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    selected_supplier = relationship("Supplier", back_populates="products")
    supplier_mappings = relationship("SupplierProductMapping", back_populates="product")
    histories = relationship("ProductHistory", back_populates="product")

    __table_args__ = (Index("ix_products_brand_category", "brand", "category"),)


class SupplierProductMapping(Base):
    __tablename__ = "supplier_product_mappings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    supplier_product_id = Column(String(200), nullable=False, index=True)
    source_file = Column(String(255), nullable=False)
    source_record_key = Column(String(255), nullable=False)
    matched_value = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    product = relationship("Product", back_populates="supplier_mappings")
    supplier = relationship("Supplier", back_populates="mappings")

    __table_args__ = (
        UniqueConstraint("product_id", "supplier_id", "supplier_product_id", name="uq_product_supplier_product"),
        Index("ix_supplier_mapping_supplier_source", "supplier_id", "source_record_key"),
    )


class DataQualityReject(Base):
    __tablename__ = "data_quality_rejects"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    source_file = Column(String(255), nullable=False)
    run_id = Column(String(50), nullable=False, index=True)
    rejection_reason = Column(Text, nullable=False)
    original_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    supplier = relationship("Supplier", back_populates="quality_rejects")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    run_id = Column(String(50), primary_key=True, index=True)
    status = Column(String(30), default="pending", nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    total_input_records = Column(Integer, default=0, nullable=False)
    valid_records = Column(Integer, default=0, nullable=False)
    rejected_records = Column(Integer, default=0, nullable=False)
    inserted_records = Column(Integer, default=0, nullable=False)
    updated_records = Column(Integer, default=0, nullable=False)
    duplicate_records = Column(Integer, default=0, nullable=False)
    processing_duration = Column(Numeric(10, 2), default=0, nullable=False)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ProductHistory(Base):
    __tablename__ = "product_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)
    run_id = Column(String(50), nullable=False, index=True)
    change_type = Column(String(50), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    product = relationship("Product", back_populates="histories")
