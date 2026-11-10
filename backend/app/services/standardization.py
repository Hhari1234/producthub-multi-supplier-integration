import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


CATEGORY_ALIASES = {
    "electronics": "Electronics",
    "smartphone": "Smartphones",
    "smartphones": "Smartphones",
    "phone": "Smartphones",
    "laptop": "Laptops",
    "laptops": "Laptops",
    "accessory": "Accessories",
    "accessories": "Accessories",
    "headphone": "Headphones",
    "headphones": "Headphones",
    "tablet": "Tablets",
    "tablets": "Tablets",
    "mobile": "Smartphones",
    "wireless": "Accessories",
    "audio": "Headphones",
    "computing": "Laptops",
}

KNOWN_CATEGORIES = {
    "Electronics",
    "Smartphones",
    "Laptops",
    "Accessories",
    "Headphones",
    "Tablets",
}

SUPPLIER_FIELD_MAP = {
    "SUPPLIER_A": {
        "supplier_product_id": "product_id",
        "product_name": "product_name",
        "brand": "brand",
        "model_number": "product_name",
        "price": "price",
        "currency": "currency",
        "category": "category",
        "stock": "stock",
        "gtin": "gtin",
        "updated_at": "updated_at",
    },
    "SUPPLIER_B": {
        "supplier_product_id": "sku",
        "product_name": "name",
        "brand": "manufacturer",
        "model_number": "name",
        "price": "selling_price",
        "currency": "currency",
        "category": "product_type",
        "stock": "quantity",
        "gtin": "gtin",
        "updated_at": "last_modified",
    },
    "SUPPLIER_C": {
        "supplier_product_id": "item_code",
        "product_name": "title",
        "brand": "brand_name",
        "model_number": "title",
        "price": "cost",
        "currency": "currency",
        "category": "department",
        "stock": "available_stock",
        "gtin": "gtin",
        "updated_at": "modified_at",
    },
}


def normalize_whitespace(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_name(value: Any) -> str:
    text = normalize_whitespace(value)
    return re.sub(r"\s+", " ", text)


def normalize_brand(value: Any) -> str:
    text = normalize_name(value)
    return text.title() if text else ""


def normalize_category(value: Any) -> str:
    text = normalize_name(value).lower()
    return CATEGORY_ALIASES.get(text, text.title())


def clean_numeric(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    text = str(value).replace("$", "").replace(",", "").strip()
    return float(text)


def normalize_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = normalize_whitespace(value)
        if not text:
            raise ValueError("timestamp is required")
        candidates = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
        ]
        for fmt in candidates:
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"unsupported datetime format: {text}")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def canonicalize_record(raw_record: dict[str, Any], supplier_code: str, source_file: str, run_id: str) -> dict[str, Any]:
    mapping = SUPPLIER_FIELD_MAP.get(supplier_code.upper(), {})
    canonical: dict[str, Any] = {
        "supplier_product_id": raw_record.get(mapping.get("supplier_product_id", "supplier_product_id")),
        "product_name": normalize_name(raw_record.get(mapping.get("product_name", "product_name"))),
        "brand": normalize_brand(raw_record.get(mapping.get("brand", "brand"))),
        "model_number": normalize_name(raw_record.get(mapping.get("model_number", "model_number"))) or None,
        "price": clean_numeric(raw_record.get(mapping.get("price", "price"))),
        "currency": normalize_whitespace(raw_record.get(mapping.get("currency", "currency"))) or "USD",
        "category": normalize_category(raw_record.get(mapping.get("category", "category"))),
        "stock": int(clean_numeric(raw_record.get(mapping.get("stock", "stock")))),
        "gtin": normalize_whitespace(raw_record.get(mapping.get("gtin", "gtin"))) or None,
        "updated_at": normalize_timestamp(raw_record.get(mapping.get("updated_at", "updated_at"))),
        "supplier_id": None,
        "source_file": source_file,
        "run_id": run_id,
    }
    canonical["model_number"] = canonical["model_number"] or canonical["product_name"]
    canonical["product_name"] = canonical["product_name"] or "Unknown Product"
    canonical["brand"] = canonical["brand"] or "Unknown Brand"
    return canonical


def normalize_supplier_payload(raw_record: dict[str, Any], supplier_code: str) -> dict[str, Any]:
    out = {
        "supplier_product_id": normalize_whitespace(raw_record.get("supplier_product_id") or raw_record.get("product_id") or raw_record.get("sku") or raw_record.get("item_code")),
        "product_name": normalize_name(raw_record.get("product_name") or raw_record.get("name") or raw_record.get("title")),
        "brand": normalize_brand(raw_record.get("brand") or raw_record.get("manufacturer") or raw_record.get("brand_name")),
        "category": normalize_category(raw_record.get("category") or raw_record.get("product_type") or raw_record.get("department")),
        "price": clean_numeric(raw_record.get("price") or raw_record.get("selling_price") or raw_record.get("cost")),
        "stock": int(clean_numeric(raw_record.get("stock") or raw_record.get("quantity") or raw_record.get("available_stock"))),
        "updated_at": normalize_timestamp(raw_record.get("updated_at") or raw_record.get("last_modified") or raw_record.get("modified_at")),
    }
    return out
