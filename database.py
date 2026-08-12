

from __future__ import annotations

import re
from functools import wraps
from threading import Lock
from typing import Any, Callable, Iterable, Mapping, Optional, TypeVar

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from config import Config


Product = dict[str, Any]
OperationResult = TypeVar("OperationResult")


class DatabaseUnavailableError(RuntimeError):
    pass


def _translate_database_errors(
    operation: Callable[..., OperationResult],
) -> Callable[..., OperationResult]:

    @wraps(operation)
    def wrapped(*args: Any, **kwargs: Any) -> OperationResult:
        try:
            return operation(*args, **kwargs)
        except PyMongoError as error:
            raise DatabaseUnavailableError(
            ) from error

    return wrapped


def _positive_limit(limit: Any, default: int, maximum: int = 100) -> int:
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, 1), maximum)


def _number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _exact_case_insensitive(value: str) -> dict[str, str]:
    return {"$regex": f"^{re.escape(value.strip())}$", "$options": "i"}


def _settings_from_mapping(config: Optional[Mapping[str, Any]]) -> tuple[str, str, int]:
    config = config or {}
    uri = str(config.get("MONGO_URI", Config.MONGO_URI))
    database_name = str(
        config.get("MONGO_DB_NAME", config.get("DATABASE_NAME", Config.MONGO_DB_NAME))
    )
    timeout = _number(
        config.get(
            "MONGO_SERVER_SELECTION_TIMEOUT_MS",
            Config.MONGO_SERVER_SELECTION_TIMEOUT_MS,
        )
    )
    timeout_ms = int(timeout) if timeout and timeout > 0 else Config.MONGO_SERVER_SELECTION_TIMEOUT_MS
    return uri, database_name, timeout_ms


class MongoRepository:

    _SORT_OPTIONS = {
        "price_low": [("lowest_price", ASCENDING), ("rating", DESCENDING)],
        "lowest_price_asc": [("lowest_price", ASCENDING), ("rating", DESCENDING)],
        "price_high": [("lowest_price", DESCENDING), ("rating", DESCENDING)],
        "lowest_price_desc": [("lowest_price", DESCENDING), ("rating", DESCENDING)],
        "rating": [("rating", DESCENDING), ("review_count", DESCENDING)],
        "rating_desc": [("rating", DESCENDING), ("review_count", DESCENDING)],
        "discount": [("discount", DESCENDING), ("lowest_price", ASCENDING)],
        "discount_desc": [("discount", DESCENDING), ("lowest_price", ASCENDING)],
        "name": [("name", ASCENDING)],
        "name_asc": [("name", ASCENDING)],
    }

    def __init__(
        self,
        client: Optional[MongoClient] = None,
        db: Optional[Database] = None,
        config: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.uri, self.database_name, self.timeout_ms = _settings_from_mapping(config)
        if db is not None:
            self.client = db.client
            self.db = db
        else:
            self.client = client or MongoClient(
                self.uri,
                serverSelectionTimeoutMS=self.timeout_ms,
            )
            self.db = self.client[self.database_name]

    @property
    def products(self):
        return self.db["products"]

    @property
    def categories(self):
        return self.db["categories"]

    @property
    def platforms(self):
        return self.db["platforms"]

    @_translate_database_errors
    def ensure_indexes(self) -> None:
        """Create the indexes used by seeding, browsing, and filtering."""
        self.products.create_index("product_id", unique=True)
        self.products.create_index([("category", ASCENDING), ("brand", ASCENDING)])
        self.products.create_index([("lowest_price", ASCENDING)])
        self.products.create_index([("rating", DESCENDING)])
        self.products.create_index([("discount", DESCENDING)])
        self.products.create_index([("featured", DESCENDING), ("rating", DESCENDING)])
        self.categories.create_index("category_id", unique=True)
        self.categories.create_index("name", unique=True)
        self.platforms.create_index("platform_id", unique=True)
        self.platforms.create_index("name", unique=True)

    @staticmethod
    def _product_query(
        filters: Optional[Mapping[str, Any]] = None, query: Optional[str] = None
    ) -> dict[str, Any]:
        filters = filters or {}
        criteria: dict[str, Any] = {}

        category = filters.get("category")
        if isinstance(category, str) and category.strip():
            criteria["category"] = _exact_case_insensitive(category)

        brand = filters.get("brand")
        if isinstance(brand, str) and brand.strip():
            criteria["brand"] = _exact_case_insensitive(brand)

        price_filter: dict[str, float] = {}
        minimum_price = _number(filters.get("min_price"))
        maximum_price = _number(filters.get("max_price"))
        if minimum_price is not None and minimum_price >= 0:
            price_filter["$gte"] = minimum_price
        if maximum_price is not None and maximum_price >= 0:
            price_filter["$lte"] = maximum_price
        if price_filter:
            criteria["lowest_price"] = price_filter

        minimum_rating = _number(filters.get("min_rating", filters.get("rating")))
        if minimum_rating is not None and minimum_rating >= 0:
            criteria["rating"] = {"$gte": minimum_rating}

        search_term = query if isinstance(query, str) and query.strip() else filters.get("query")
        if isinstance(search_term, str) and search_term.strip():
            escaped_term = re.escape(search_term.strip())
            criteria["$or"] = [
                {field: {"$regex": escaped_term, "$options": "i"}}
                for field in ("name", "brand", "model", "category")
            ]

        return criteria

    @_translate_database_errors
    def get_featured_products(self, limit: Any = 8) -> list[Product]:
        return list(
            self.products.find({"featured": True})
            .sort([("rating", DESCENDING), ("lowest_price", ASCENDING)])
            .limit(_positive_limit(limit, 8))
        )

    @_translate_database_errors
    def get_popular_products(self, limit: Any = 8) -> list[Product]:
        return list(
            self.products.find({})
            .sort([("review_count", DESCENDING), ("rating", DESCENDING)])
            .limit(_positive_limit(limit, 8))
        )

    @_translate_database_errors
    def get_products(
        self,
        filters: Optional[Mapping[str, Any]] = None,
        sort: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[Product]:
        sort_key = str(sort or "").strip().lower()
        sort_fields = self._SORT_OPTIONS.get(
            sort_key, [("featured", DESCENDING), ("rating", DESCENDING), ("name", ASCENDING)]
        )
        return list(self.products.find(self._product_query(filters, query)).sort(sort_fields))

    @_translate_database_errors
    def get_product(self, product_id: Any) -> Optional[Product]:
        if product_id is None:
            return None
        value = str(product_id).strip()
        if not value:
            return None

        product = self.products.find_one({"product_id": value})
        if product is not None:
            return product
        if ObjectId.is_valid(value):
            return self.products.find_one({"_id": ObjectId(value)})
        return None

    @_translate_database_errors
    def get_categories_with_counts(self) -> list[dict[str, Any]]:
        category_docs = list(self.categories.find({}).sort("name", ASCENDING))
        for category in category_docs:
            category["product_count"] = self.products.count_documents(
                {"category": category["name"]}
            )
        return category_docs

    @_translate_database_errors
    def get_category(self, name: Any) -> Optional[dict[str, Any]]:
        if not isinstance(name, str) or not name.strip():
            return None
        return self.categories.find_one({"name": _exact_case_insensitive(name)})

    @_translate_database_errors
    def get_deals(self, limit: Any = 12) -> list[Product]:
        return list(
            self.products.find({"discount": {"$gt": 0}})
            .sort([("discount", DESCENDING), ("lowest_price", ASCENDING)])
            .limit(_positive_limit(limit, 12))
        )

    @_translate_database_errors
    def get_products_by_ids(self, ids: Iterable[Any]) -> list[Product]:
        if isinstance(ids, (str, bytes)):
            ids = str(ids).split(",")

        ordered_ids: list[str] = []
        for item in ids or []:
            value = str(item).strip()
            if value and value not in ordered_ids:
                ordered_ids.append(value)

        if not ordered_ids:
            return []
        products = self.products.find({"product_id": {"$in": ordered_ids}})
        products_by_id = {product["product_id"]: product for product in products}
        return [products_by_id[product_id] for product_id in ordered_ids if product_id in products_by_id]

    @_translate_database_errors
    def get_brands(self, category: Optional[str] = None) -> list[str]:
        criteria: dict[str, Any] = {}
        if isinstance(category, str) and category.strip():
            criteria["category"] = _exact_case_insensitive(category)
        brands = self.products.distinct("brand", criteria)
        return sorted((brand for brand in brands if isinstance(brand, str)), key=str.casefold)

    def ping(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except PyMongoError:
            return False

    def close(self) -> None:
        self.client.close()


_repository: Optional[MongoRepository] = None
_repository_settings: Optional[tuple[str, str, int]] = None
_repository_lock = Lock()


def get_repository(config: Optional[Mapping[str, Any]] = None) -> MongoRepository:
    
    global _repository, _repository_settings
    settings = _settings_from_mapping(config)
    if _repository is None or _repository_settings != settings:
        with _repository_lock:
            if _repository is None or _repository_settings != settings:
                _repository = MongoRepository(config=config)
                _repository_settings = settings
    return _repository


def get_database() -> Database:
    return get_repository().db
