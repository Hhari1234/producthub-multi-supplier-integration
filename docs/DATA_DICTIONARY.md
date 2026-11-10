# ProductHub Data Dictionary

## suppliers
- id: primary key
- supplier_code: stable supplier identifier
- name: supplier display name
- status: active/inactive state
- supported_format: csv or json
- total_imported_records: count of ingested records
- last_ingestion_at: last successful import timestamp
- created_at, updated_at: audit timestamps

## raw_products
- id: primary key
- supplier_id: reference to the supplier
- source_file: original filename
- source_record_key: deterministic record key used for idempotency
- source_payload: raw original JSON payload
- normalized_payload: canonicalized payload before validation
- run_id: pipeline run that ingested the record
- status: uploaded / processed / rejected

## category_mappings
- supplier_id: supplier identifier
- source_category: original category label
- mapped_category: standardized category

## products
- id: primary key
- product_name, brand, model_number, category
- price, currency, stock, gtin
- updated_at: latest relevant source update
- selected_supplier_id: active canonical source supplier
- selected_supplier_name: supplier display name
- selection_reason: deterministic business rule used

## supplier_product_mappings
- product_id: unified product id
- supplier_id: contributing supplier
- supplier_product_id: supplier-specific product key
- source_file and source_record_key: traceability fields
- matched_value: matching evidence used

## data_quality_rejects
- supplier_id, source_file, run_id
- rejection_reason: reason codes for validation failure
- original_payload: the rejected record as received

## pipeline_runs
- run_id: unique job identifier
- status: pending, running, completed, completed_with_errors, failed
- input, valid, rejected, inserted, updated, duplicate counts
- processing_duration, failure_reason

## product_history
- product_id, supplier_id, run_id
- change_type: insert/upsert
- old_value/new_value: before and after snapshots
- details: source metadata for each change
