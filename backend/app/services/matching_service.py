from __future__ import annotations

from collections import defaultdict

from sqlalchemy import or_

from app.models import Product


def build_product_lookup(db):
    lookup = {
        "gtin": {},
        "brand_model": {},
        "brand_name": defaultdict(list),
        "brand": defaultdict(list),
    }
    for product in db.query(Product).all():
        gtin = product.gtin
        if gtin:
            lookup["gtin"][gtin] = product

        brand = product.brand
        model_number = product.model_number
        if brand and model_number:
            lookup["brand_model"][(brand, model_number)] = product

        if brand and product.product_name:
            lookup["brand_name"][(brand, product.product_name)].append(product)

        if brand:
            lookup["brand"][brand].append(product)
    return lookup


def match_existing_product(db, canonical, product_lookup=None):
    if product_lookup is None:
        product_lookup = build_product_lookup(db)

    if canonical.get("gtin"):
        match = product_lookup["gtin"].get(canonical["gtin"])
        if match:
            return match, "gtin"

    brand = canonical.get("brand")
    model_number = canonical.get("model_number")
    if brand and model_number:
        match = product_lookup["brand_model"].get((brand, model_number))
        if match:
            return match, "brand_model"

    if brand and canonical.get("product_name"):
        for match in product_lookup["brand_name"].get((brand, canonical["product_name"]), []):
            return match, "brand_name"

    fuzzy_name = canonical.get("product_name", "")
    if brand and fuzzy_name:
        for product in product_lookup["brand"].get(brand, []):
            if product.product_name and fuzzy_name.lower() in product.product_name.lower():
                return product, "fuzzy_brand_name"
            if product.model_number and fuzzy_name.lower() in product.model_number.lower():
                return product, "fuzzy_brand_name"

    return None, "none"
