"""Initial ProductHub schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-10
"""

from alembic import op
import sqlalchemy as sa


revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("supported_format", sa.String(length=20), nullable=True),
        sa.Column("total_imported_records", sa.Integer(), nullable=False),
        sa.Column("last_ingestion_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_code"),
    )
    op.create_index(op.f("ix_suppliers_id"), "suppliers", ["id"], unique=False)
    op.create_index(op.f("ix_suppliers_supplier_code"), "suppliers", ["supplier_code"], unique=False)

    op.create_table(
        "raw_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("source_record_key", sa.String(length=255), nullable=False),
        sa.Column("source_payload", sa.JSON(), nullable=False),
        sa.Column("normalized_payload", sa.JSON(), nullable=True),
        sa.Column("run_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_id", "source_record_key", "source_file", name="uq_raw_supplier_record"),
    )
    op.create_index(op.f("ix_raw_products_id"), "raw_products", ["id"], unique=False)
    op.create_index(op.f("ix_raw_products_source_record_key"), "raw_products", ["source_record_key"], unique=False)
    op.create_index(op.f("ix_raw_products_run_id"), "raw_products", ["run_id"], unique=False)
    op.create_index(op.f("ix_raw_products_supplier_id"), "raw_products", ["supplier_id"], unique=False)

    op.create_table(
        "category_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("source_category", sa.String(length=100), nullable=False),
        sa.Column("mapped_category", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_id", "source_category", name="uq_supplier_category"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("brand", sa.String(length=200), nullable=False),
        sa.Column("model_number", sa.String(length=100), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("gtin", sa.String(length=50), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("selected_supplier_id", sa.Integer(), nullable=True),
        sa.Column("selected_supplier_name", sa.String(length=200), nullable=True),
        sa.Column("selection_reason", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["selected_supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_brand_category"), "products", ["brand", "category"], unique=False)
    op.create_index(op.f("ix_products_gtin"), "products", ["gtin"], unique=False)
    op.create_index(op.f("ix_products_id"), "products", ["id"], unique=False)

    op.create_table(
        "supplier_product_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("supplier_product_id", sa.String(length=200), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("source_record_key", sa.String(length=255), nullable=False),
        sa.Column("matched_value", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "supplier_id", "supplier_product_id", name="uq_product_supplier_product"),
    )
    op.create_index(op.f("ix_supplier_product_mappings_id"), "supplier_product_mappings", ["id"], unique=False)
    op.create_index(op.f("ix_supplier_product_mappings_product_id"), "supplier_product_mappings", ["product_id"], unique=False)
    op.create_index(op.f("ix_supplier_product_mappings_supplier_id"), "supplier_product_mappings", ["supplier_id"], unique=False)
    op.create_index(op.f("ix_supplier_product_mappings_supplier_product_id"), "supplier_product_mappings", ["supplier_product_id"], unique=False)

    op.create_table(
        "data_quality_rejects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("run_id", sa.String(length=50), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=False),
        sa.Column("original_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_quality_rejects_id"), "data_quality_rejects", ["id"], unique=False)
    op.create_index(op.f("ix_data_quality_rejects_run_id"), "data_quality_rejects", ["run_id"], unique=False)
    op.create_index(op.f("ix_data_quality_rejects_supplier_id"), "data_quality_rejects", ["supplier_id"], unique=False)

    op.create_table(
        "pipeline_runs",
        sa.Column("run_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_input_records", sa.Integer(), nullable=False),
        sa.Column("valid_records", sa.Integer(), nullable=False),
        sa.Column("rejected_records", sa.Integer(), nullable=False),
        sa.Column("inserted_records", sa.Integer(), nullable=False),
        sa.Column("updated_records", sa.Integer(), nullable=False),
        sa.Column("duplicate_records", sa.Integer(), nullable=False),
        sa.Column("processing_duration", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(op.f("ix_pipeline_runs_run_id"), "pipeline_runs", ["run_id"], unique=False)

    op.create_table(
        "product_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("run_id", sa.String(length=50), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_history_id"), "product_history", ["id"], unique=False)
    op.create_index(op.f("ix_product_history_product_id"), "product_history", ["product_id"], unique=False)
    op.create_index(op.f("ix_product_history_supplier_id"), "product_history", ["supplier_id"], unique=False)


def downgrade() -> None:
    op.drop_table("product_history")
    op.drop_table("pipeline_runs")
    op.drop_table("data_quality_rejects")
    op.drop_table("supplier_product_mappings")
    op.drop_table("products")
    op.drop_table("category_mappings")
    op.drop_table("raw_products")
    op.drop_table("suppliers")
