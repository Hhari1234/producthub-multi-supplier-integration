from __future__ import annotations

import json
import os
import platform
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/producthub_bench")

from app.database import Base, get_db
from app.models import Supplier
from app.services.ingestion_service import ingest_supplier_file
from app.services.pipeline_service import process_pipeline_run

BENCHMARK_DIR = Path(__file__).resolve().parent
DATA_DIR = BENCHMARK_DIR / "data"
RESULTS_DIR = BENCHMARK_DIR / "results"


def ensure_benchmark_database(db_name: str = "producthub_bench") -> Any:
    admin_url = "postgresql://postgres:postgres@localhost:5432/postgres"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cur.fetchone()
            if not exists:
                cur.execute(f'CREATE DATABASE "{db_name}"')
    return create_engine(f"postgresql+psycopg://postgres:postgres@localhost:5432/{db_name}", pool_pre_ping=True)


@dataclass
class BenchmarkRunResult:
    dataset_size: int
    attempt: int
    total_input_records: int
    valid_record_count: int
    rejected_record_count: int
    inserted_products: int
    updated_products: int
    total_processing_seconds: float
    records_per_second: float
    peak_memory_mb: float
    reconciled: bool
    status: str
    suppliers_processed: list[str]
    created_at: str


def load_supplier_names() -> dict[str, str]:
    return {"SUPPLIER_A": "Supplier A", "SUPPLIER_B": "Supplier B", "SUPPLIER_C": "Supplier C"}


def reset_benchmark_db(db: Session) -> None:
    db.execute(text("TRUNCATE TABLE data_quality_rejects, product_history, supplier_product_mappings, raw_products, products, pipeline_runs, suppliers RESTART IDENTITY CASCADE"))
    db.commit()


def seed_suppliers(db: Session) -> dict[str, int]:
    suppliers = [
        Supplier(supplier_code="SUPPLIER_A", name="Supplier A", status="active", supported_format="csv", total_imported_records=0),
        Supplier(supplier_code="SUPPLIER_B", name="Supplier B", status="active", supported_format="json", total_imported_records=0),
        Supplier(supplier_code="SUPPLIER_C", name="Supplier C", status="active", supported_format="csv", total_imported_records=0),
    ]
    db.add_all(suppliers)
    db.commit()
    mapping = {s.supplier_code: s.id for s in suppliers}
    return mapping


def benchmark_dataset(size: int, attempt: int, db_engine: Any) -> BenchmarkRunResult:
    feed_dir = DATA_DIR / str(size)
    supplier_files = {
        "SUPPLIER_A": feed_dir / "supplier_a.csv",
        "SUPPLIER_B": feed_dir / "supplier_b.json",
        "SUPPLIER_C": feed_dir / "supplier_c.csv",
    }
    if not all(path.exists() for path in supplier_files.values()):
        raise FileNotFoundError(f"Missing benchmark feeds for size {size}: {supplier_files}")

    with Session(bind=db_engine) as db:
        reset_benchmark_db(db)
        supplier_ids = seed_suppliers(db)
        db.commit()

        total_input = 0
        valid_total = 0
        rejected_total = 0
        inserted_total = 0
        updated_total = 0
        start = time.perf_counter()
        tracemalloc.start()
        process_start = time.perf_counter()

        for supplier_code, file_path in supplier_files.items():
            supplier_id = supplier_ids[supplier_code]
            file_bytes = file_path.read_bytes()
            ingest_result = ingest_supplier_file(db, supplier_id, file_bytes, file_path.name)
            run = process_pipeline_run(db, supplier_id=supplier_id, run_id=ingest_result["run_id"])
            db.refresh(run)
            total_input += int(run.total_input_records)
            valid_total += int(run.valid_records)
            rejected_total += int(run.rejected_records)
            inserted_total += int(run.inserted_records)
            updated_total += int(run.updated_records)
            db.commit()

        elapsed = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / (1024 * 1024)
        rps = total_input / elapsed if elapsed > 0 else 0.0
        reconciled = total_input == (valid_total + rejected_total)
        result = BenchmarkRunResult(
            dataset_size=size,
            attempt=attempt,
            total_input_records=total_input,
            valid_record_count=valid_total,
            rejected_record_count=rejected_total,
            inserted_products=inserted_total,
            updated_products=updated_total,
            total_processing_seconds=elapsed,
            records_per_second=rps,
            peak_memory_mb=peak_mb,
            reconciled=reconciled,
            status="completed" if reconciled else "reconciliation_failed",
            suppliers_processed=[supplier_code for supplier_code in supplier_files],
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return result


def run_all_benchmarks() -> list[BenchmarkRunResult]:
    db_engine = ensure_benchmark_database()
    Base.metadata.create_all(bind=db_engine)
    results: list[BenchmarkRunResult] = []
    for size in (1000, 10000, 100000):
        for attempt in (1, 2):
            results.append(benchmark_dataset(size, attempt, db_engine))
    return results


def write_result_files(results: list[BenchmarkRunResult], report_path: Path) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RESULTS_DIR / "benchmark_results.json"
    raw_path.write_text(json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8")
    report_lines = [
        "# ProductHub Performance Benchmark Report",
        "",
        f"- Timestamp: {datetime.now(timezone.utc).isoformat()}",
        f"- Platform: {platform.platform()}",
        f"- Python: {platform.python_version()}",
        f"- PostgreSQL: 17.11 on x86_64-windows",
        f"- Benchmark database: {os.environ.get('DATABASE_URL', 'postgresql+psycopg://postgres@localhost:5433/producthub_bench')}",
        "",
        "## Summary",
        "",
        "| Dataset | Attempt | Input | Valid | Rejected | Inserted | Updated | Time (s) | RPS | Peak Memory (MB) | Reconciled |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        report_lines.append(f"| {r.dataset_size} | {r.attempt} | {r.total_input_records} | {r.valid_record_count} | {r.rejected_record_count} | {r.inserted_products} | {r.updated_products} | {r.total_processing_seconds:.3f} | {r.records_per_second:.2f} | {r.peak_memory_mb:.2f} | {'Yes' if r.reconciled else 'No'} |")
    report_lines.extend(["", "## Notes", "- Benchmark runs used a dedicated PostgreSQL database: producthub_bench.", "- The workload included valid rows, duplicates, invalid prices, invalid stock, unknown categories, and overlapping product identities across supplier schemas.", "- Reconciliation check: input = valid + rejected."])
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    results = run_all_benchmarks()
    write_result_files(results, BENCHMARK_DIR / "performance_report.md")
    print(json.dumps([asdict(r) for r in results], indent=2))
