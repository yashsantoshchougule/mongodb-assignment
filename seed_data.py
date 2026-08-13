"""Idempotently load the ValueVista Mini demonstration catalogue into MongoDB.

Run this after MongoDB is available locally:

    python seed_data.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from pymongo import UpdateOne
from pymongo.errors import PyMongoError

from database import DatabaseUnavailableError, get_repository


DATA_DIR = Path(__file__).resolve().parent / "data"


def load_json(filename: str) -> list[dict[str, Any]]:
    """Read one seed file and ensure it contains a JSON array of documents."""
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as seed_file:
        records = json.load(seed_file)
    if not isinstance(records, list):
        raise ValueError(f"{filename} must contain a JSON array.")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"Every record in {filename} must be a JSON object.")
    return records


def _require_keys(record: dict[str, Any], keys: Iterable[str], label: str) -> None:
    missing = [key for key in keys if key not in record or record[key] in (None, "")]
    if missing:
        raise ValueError(f"{label} is missing required field(s): {', '.join(missing)}")


def validate_catalogue(
    products: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    platforms: list[dict[str, Any]],
) -> None:
    """Catch accidental seed-data edits before anything is written to MongoDB."""
    if len(products) != 120:
        raise ValueError("sample_products.json must contain exactly 120 products.")
    if len(categories) != 6:
        raise ValueError("sample_categories.json must contain exactly 6 categories.")

    product_ids = [product.get("product_id") for product in products]
    if len(set(product_ids)) != len(product_ids):
        raise ValueError("Product IDs must be unique.")

    category_names = {category.get("name") for category in categories}
    platform_names = {platform.get("name") for platform in platforms}
    for category in categories:
        _require_keys(category, ("category_id", "name", "description", "image"), "Category")

    for platform in platforms:
        _require_keys(platform, ("platform_id", "name", "website"), "Platform")

    required_product_keys = (
        "product_id",
        "name",
        "brand",
        "model",
        "category",
        "description",
        "image",
        "rating",
        "review_count",
        "original_price",
        "lowest_price",
        "discount",
        "specifications",
        "key_features",
        "listings",
    )
    required_listing_keys = ("platform", "price", "delivery", "availability", "product_url")
    for product in products:
        _require_keys(product, required_product_keys, f"Product {product.get('product_id', '<unknown>')}")
        if product["category"] not in category_names:
            raise ValueError(f"{product['product_id']} has an unknown category.")
        if not isinstance(product["specifications"], dict) or not product["specifications"]:
            raise ValueError(f"{product['product_id']} needs a non-empty specifications object.")
        if not isinstance(product["key_features"], list) or len(product["key_features"]) < 3:
            raise ValueError(f"{product['product_id']} needs at least three key features.")
        if not isinstance(product["listings"], list) or len(product["listings"]) != 3:
            raise ValueError(f"{product['product_id']} must have exactly three listings.")

        listing_prices: list[float] = []
        for listing in product["listings"]:
            _require_keys(listing, required_listing_keys, f"Listing for {product['product_id']}")
            if listing["platform"] not in platform_names:
                raise ValueError(f"{product['product_id']} references an unknown platform.")
            parsed_url = urlparse(str(listing["product_url"]).strip())
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                raise ValueError(
                    f"{product['product_id']} has a store URL that is not a valid http(s) link."
                )
            listing_prices.append(float(listing["price"]))
        if float(product["lowest_price"]) != min(listing_prices):
            raise ValueError(
                f"{product['product_id']} lowest_price must match its lowest listing price."
            )


def upsert_documents(collection: Any, key: str, documents: list[dict[str, Any]]) -> Any:
    """Upsert documents by their stable public IDs, avoiding duplicate seed rows."""
    operations = [
        UpdateOne({key: document[key]}, {"$set": document}, upsert=True)
        for document in documents
    ]
    return collection.bulk_write(operations, ordered=False) if operations else None


def _result_summary(label: str, result: Any) -> str:
    if result is None:
        return f"{label}: no records"
    return (
        f"{label}: {result.upserted_count} inserted, {result.modified_count} updated, "
        f"{result.matched_count} matched"
    )


def seed() -> int:
    """Validate then seed categories, platforms, and products into valuevista_mini."""
    products = load_json("sample_products.json")
    categories = load_json("sample_categories.json")
    platforms = load_json("sample_platforms.json")
    validate_catalogue(products, categories, platforms)

    repository = get_repository()
    if not repository.ping():
        print("MongoDB is unavailable. Start MongoDB and check MONGO_URI in .env before seeding.")
        return 1

    try:
        repository.ensure_indexes()
        category_result = upsert_documents(repository.categories, "category_id", categories)
        platform_result = upsert_documents(repository.platforms, "platform_id", platforms)
        product_result = upsert_documents(repository.products, "product_id", products)
    except (DatabaseUnavailableError, PyMongoError) as error:
        print(f"MongoDB seed failed: {error}")
        return 1

    print("ValueVista Mini seed completed successfully.")
    print(_result_summary("Categories", category_result))
    print(_result_summary("Platforms", platform_result))
    print(_result_summary("Products", product_result))
    return 0


def main() -> int:
    try:
        return seed()
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"Seed data validation failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
