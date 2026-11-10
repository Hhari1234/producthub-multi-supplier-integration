from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

OVERLAP_PRODUCTS = [
    {"name": "Alpha Phone", "brand": "Acme", "gtin": "GTIN-ALPHA-001", "category": "Smartphones"},
    {"name": "Beta Laptop", "brand": "Acme", "gtin": "GTIN-BETA-001", "category": "Laptops"},
    {"name": "Gamma Headset", "brand": "Northpeak", "gtin": "GTIN-GAMMA-001", "category": "Headphones"},
    {"name": "Delta Speaker", "brand": "Acme", "gtin": "GTIN-DELTA-001", "category": "Accessories"},
    {"name": "Echo Tablet", "brand": "Northpeak", "gtin": "GTIN-ECHO-001", "category": "Tablets"},
    {"name": "Fiber Dock", "brand": "Orion", "gtin": "GTIN-FIBER-001", "category": "Accessories"},
    {"name": "Harbor Monitor", "brand": "Acme", "gtin": "GTIN-HARBOR-001", "category": "Electronics"},
    {"name": "Iris Charger", "brand": "Orion", "gtin": "GTIN-IRIS-001", "category": "Accessories"},
    {"name": "Jet Keyboard", "brand": "Northpeak", "gtin": "GTIN-JET-001", "category": "Accessories"},
    {"name": "Keystone Mouse", "brand": "Acme", "gtin": "GTIN-KEYSTONE-001", "category": "Accessories"},
]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _supplier_a_record(base: dict[str, str], index: int, *, valid: bool) -> dict[str, Any]:
    price = 299.99 if valid else -10 if index % 7 == 0 else 89.99
    stock = 18 if valid else -5 if index % 9 == 0 else 4
    category = "Smartphones" if valid else "UnknownCategory" if index % 11 == 0 else "Accessories"
    if valid and index % 13 == 0:
        category = "Electronics"
    return {
        "product_id": f"A-{index}",
        "product_name": base["name"],
        "brand": base["brand"],
        "price": price,
        "category": category,
        "stock": stock,
        "updated_at": "2026-05-01 10:00:00",
        "currency": "USD",
        "gtin": base["gtin"],
    }


def _supplier_b_record(base: dict[str, str], index: int, *, valid: bool) -> dict[str, Any]:
    price = 269.99 if valid else -5 if index % 8 == 0 else 44.99
    qty = 30 if valid else -2 if index % 10 == 0 else 11
    category = "smartphone" if valid else "unknown_type" if index % 12 == 0 else "accessory"
    return {
        "sku": f"B-{index}",
        "name": base["name"],
        "manufacturer": base["brand"],
        "selling_price": price,
        "product_type": category,
        "quantity": qty,
        "last_modified": "2026-05-01T12:00:00",
        "currency": "USD",
        "gtin": base["gtin"],
    }


def _supplier_c_record(base: dict[str, str], index: int, *, valid: bool) -> dict[str, Any]:
    price = 279.99 if valid else 0 if index % 6 == 0 else 119.99
    stock = 25 if valid else -1 if index % 7 == 0 else 8
    category = "electronics" if valid else "unknowncategory" if index % 16 == 0 else "accessories"
    return {
        "item_code": f"C-{index}",
        "title": base["name"],
        "brand_name": base["brand"],
        "cost": price,
        "department": category,
        "available_stock": stock,
        "modified_at": "2026-05-01 16:00:00",
        "currency": "USD",
        "gtin": base["gtin"],
    }


def _build_supplier_rows(size: int, supplier_code: str, *, rng: random.Random):
    rows: list[dict[str, Any]] = []
    overlap_products = [
        {"name": base["name"], "brand": base["brand"], "gtin": base["gtin"]}
        for base in OVERLAP_PRODUCTS
        for _ in range(2)
    ]
    base_index = 0
    for idx in range(size):
        base = OVERLAP_PRODUCTS[idx % len(OVERLAP_PRODUCTS)]
        if idx % 17 == 0:
            base = overlap_products[(base_index + idx) % len(overlap_products)]
            base_index += 1
        valid = idx % 9 not in {0, 3, 6}
        if idx % 19 == 0:
            valid = False
        if supplier_code == "SUPPLIER_A":
            row = _supplier_a_record(base, idx, valid=valid)
            if idx % 23 == 0:
                row["product_id"] = f"A-{idx // 2}"
            rows.append(row)
        elif supplier_code == "SUPPLIER_B":
            row = _supplier_b_record(base, idx, valid=valid)
            if idx % 31 == 0:
                row["sku"] = f"B-{idx // 3}"
            rows.append(row)
        else:
            row = _supplier_c_record(base, idx, valid=valid)
            if idx % 27 == 0:
                row["item_code"] = f"C-{idx // 4}"
            rows.append(row)
    return rows


def generate_feed_set(size: int, base_dir: Path = DATA_DIR) -> dict[str, Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target_dir = base_dir / str(size)
    target_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42 + size)
    supplier_counts = {"SUPPLIER_A": max(1, int(size * 0.42)), "SUPPLIER_B": max(1, int(size * 0.35)), "SUPPLIER_C": max(1, size - max(1, int(size * 0.42)) - max(1, int(size * 0.35)))}
    if sum(supplier_counts.values()) != size:
        supplier_counts["SUPPLIER_C"] += size - sum(supplier_counts.values())
    files: dict[str, Path] = {}
    for name, count in supplier_counts.items():
        rows = _build_supplier_rows(count, name, rng=rng)
        file_key = name.lower().replace("supplier_", "")
        if name == "SUPPLIER_B":
            path = target_dir / f"supplier_{file_key}.json"
            _write_json(path, rows)
        else:
            path = target_dir / f"supplier_{file_key}.csv"
            _write_csv(path, rows)
        files[name] = path
    return files


def main() -> None:
    for size in (1000, 10000, 100000):
        generate_feed_set(size)
    print(f"Generated benchmark feeds under {DATA_DIR}")


if __name__ == "__main__":
    main()
