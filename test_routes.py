"""Lightweight Flask route checks that run without a real MongoDB server."""

from __future__ import annotations

import unittest
from copy import deepcopy

from app import create_app


def product(number: int, category: str, brand: str) -> dict:
    return {
        "product_id": f"PROD{number:03d}",
        "name": f"{brand} {category} {number}",
        "brand": brand,
        "model": f"Model {number}",
        "category": category,
        "description": "A deliberately small test product.",
        "image": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa7",
        "rating": 4.0 + (number / 10),
        "review_count": number * 100,
        "original_price": 50000 + (number * 1000),
        "lowest_price": 40000 + (number * 1000),
        "discount": 20,
        "featured": number % 2 == 0,
        "key_features": ["Useful test feature", "Second test feature"],
        "specifications": {"Display": "Test display", "RAM": "8 GB"},
        "listings": [{"platform": "Amazon", "price": 41000, "delivery": "2–3 Days", "availability": "In Stock", "product_url": "https://example.com"}],
    }


class FakeRepository:
    def __init__(self) -> None:
        self.items = [product(1, "Smartphones", "Samsung"), product(2, "Smartphones", "OnePlus"), product(3, "Laptops", "HP"), product(4, "Laptops", "Lenovo")]
        self.last_filters: dict = {}
        self.last_sort: str | None = None
        self.last_query: str | None = None

    def get_featured_products(self, limit=4): return deepcopy([item for item in self.items if item["featured"]][:limit])
    def get_popular_products(self, limit=4): return deepcopy(self.items[:limit])
    def get_deals(self, limit=24): return deepcopy(self.items[:limit])

    def get_products(self, filters=None, sort=None, query=None):
        self.last_filters, self.last_sort, self.last_query = dict(filters or {}), sort, query
        results = self.items
        if query:
            term = query.casefold()
            results = [item for item in results if term in " ".join((item["name"], item["brand"], item["model"], item["category"])).casefold()]
        if filters and filters.get("category"): results = [item for item in results if item["category"] == filters["category"]]
        if filters and filters.get("brand"): results = [item for item in results if item["brand"] == filters["brand"]]
        return deepcopy(results)

    def get_product(self, product_id): return deepcopy(next((item for item in self.items if item["product_id"] == product_id), None))

    def get_categories_with_counts(self):
        return [{"category_id": f"CAT{index:03d}", "name": name, "description": f"Browse {name.lower()}.", "icon": "✦", "product_count": sum(item["category"] == name for item in self.items)} for index, name in enumerate(("Smartphones", "Laptops", "Headphones", "Smartwatches"), start=1)]

    def get_category(self, name): return next((item for item in self.get_categories_with_counts() if item["name"] == name), None)
    def get_products_by_ids(self, identifiers):
        product_map = {item["product_id"]: item for item in self.items}
        return deepcopy([product_map[item] for item in identifiers if item in product_map])
    def get_brands(self, category=None): return sorted({item["brand"] for item in self.items if not category or item["category"] == category})


class ValueVistaRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeRepository()
        self.app = create_app(repository=self.repository)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_all_main_pages_render(self) -> None:
        for path in ("/", "/products", "/categories", "/deals", "/about"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_search_filters_and_sort_are_passed_to_repository(self) -> None:
        response = self.client.get("/search?q=samsung&category=Smartphones&brand=Samsung&min_price=30000&max_price=80000&min_rating=4&sort=rating")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.repository.last_query, "samsung")
        self.assertEqual(self.repository.last_filters["category"], "Smartphones")
        self.assertEqual(self.repository.last_filters["brand"], "Samsung")
        self.assertEqual(self.repository.last_filters["min_price"], 30000)
        self.assertEqual(self.repository.last_filters["max_price"], 80000)
        self.assertEqual(self.repository.last_sort, "rating")

    def test_product_and_category_routes_handle_found_and_missing_records(self) -> None:
        self.assertEqual(self.client.get("/product/PROD001").status_code, 200)
        self.assertEqual(self.client.get("/product/UNKNOWN").status_code, 404)
        self.assertEqual(self.client.get("/category/Smartphones").status_code, 200)
        self.assertEqual(self.client.get("/category/Unknown").status_code, 404)

    def test_compare_preserves_requested_product_order(self) -> None:
        response = self.client.get("/compare?ids=PROD002,PROD001,UNKNOWN,PROD003")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertLess(body.index("OnePlus Smartphones 2"), body.index("Samsung Smartphones 1"))
        self.assertIn("One or more selected products were not found", body)

    def test_invalid_filter_values_do_not_crash(self) -> None:
        response = self.client.get("/products?min_price=-99&max_price=not-a-number&sort=unknown")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.repository.last_filters["min_price"])
        self.assertIsNone(self.repository.last_filters["max_price"])
        self.assertIsNone(self.repository.last_sort)

    def test_product_detail_blocks_non_web_store_links(self) -> None:
        self.repository.items[0]["listings"][0]["product_url"] = "javascript:alert('unsafe')"
        response = self.client.get("/product/PROD001")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("javascript:alert", body)
        self.assertIn("Link unavailable", body)


if __name__ == "__main__":
    unittest.main()
