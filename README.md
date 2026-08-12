# ValueVista Mini

ValueVista Mini is a Flask and MongoDB product-comparison demo. It contains a manually curated catalogue of 20 products across Smartphones, Laptops, Headphones, and Smartwatches. Prices, availability, specifications, and store links are demonstration data; they are not live retailer data.

## Run locally

1. Install and start [MongoDB Community Server](https://www.mongodb.com/try/download/community). The default connection is `mongodb://localhost:27017/` and the app uses the `valuevista_mini` database.
2. Open PowerShell in the project folder and create a virtual environment:

   ```powershell
   cd 'C:\yash\projects\mongoDB project\mongodb_small_project'
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   py -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

3. Adjust `.env` only if your MongoDB server uses a different URI or database name.
4. Import the idempotent sample catalogue:

   ```powershell
   py seed_data.py
   ```

5. Start the Flask site:

   ```powershell
   py app.py
   ```

6. Visit `http://127.0.0.1:5000`.

If seeding reports that MongoDB is unavailable, start the local MongoDB service (or `mongod`) and confirm `MONGO_URI` in `.env`. The normal application runtime intentionally uses MongoDB only; it does not switch to a local JSON or in-memory fallback.

## Environment settings

Copy `.env.example` to `.env` and set the following values as needed:

```dotenv
FLASK_SECRET_KEY=change-this-for-a-private-deployment
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=valuevista_mini
MONGO_SERVER_SELECTION_TIMEOUT_MS=5000
```

## Seed data

The seed script reads the following versioned JSON files:

- `data/sample_products.json` — 20 products, each with key features, category-specific specifications, and exactly three manual platform listings.
- `data/sample_categories.json` — four category records.
- `data/sample_platforms.json` — the manual retail platforms used by the listings.

`seed_data.py` validates the files and uses MongoDB upserts keyed by `product_id`, `category_id`, and `platform_id`. It is safe to run again after editing the sample records: matching records are updated rather than duplicated.

## Database interface

Flask routes should import the repository rather than embed MongoDB queries:

```python
from database import DatabaseUnavailableError, get_repository

repository = get_repository()
products = repository.get_products(
    filters={"category": "Laptops", "min_price": 30000, "min_rating": 4},
    sort="price_low",
    query="gaming",
)
```

`get_repository()` accepts no arguments or a Flask-style config mapping. Its public helpers are:

- `get_featured_products(limit)` and `get_popular_products(limit)`
- `get_products(filters=None, sort=None, query=None)`
- `get_product(product_id)` and `get_products_by_ids(ids)`
- `get_categories_with_counts()` and `get_category(name)`
- `get_deals(limit)` and `get_brands(category=None)`
- `ping()` and `ensure_indexes()`

Supported product filters are `category`, `brand`, `min_price`, `max_price`, and `min_rating`; supported sort keys are `price_low`, `price_high`, `rating`, `discount`, and `name`. Database operation failures are raised as `DatabaseUnavailableError`, allowing routes to present a friendly 503 page.
