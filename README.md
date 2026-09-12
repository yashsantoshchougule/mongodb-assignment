ValueVista Mini

ValueVista Mini is a product-comparison web application built for a MongoDB academic project. It lets users browse electronic products, filter the catalogue, view specifications and sample store prices, and compare up to three products side by side.

Demo project: Product information, ratings, prices, availability, and store links are manually prepared sample data. They are not live ecommerce data.

Project overview

The application stores its catalogue in MongoDB and displays it through a Flask website. The included seed data contains 120 products across six categories: Smartphones, Laptops, Headphones, Smartwatches, Tablets, and Cameras. It also defines five shopping platforms: Amazon, Flipkart, Croma, Reliance Digital, and Vijay Sales. Each product has three sample platform listings.

Users can:

Browse products and categories.

Filter by category, brand, price range, and minimum rating.

Sort by price, rating, discount, or name.

View a product's features, specifications, and store listings.

Compare up to three products in one table.

Register, log in, and log out.

Repository structure

mongodb-assignment/
├── app.py             # Flask application and page routes
├── database.py        # MongoDB access
├── config.py          # Application settings
├── seed_data.py       # Sample-data import
├── data/              # Product, category, and platform JSON files
├── templates/         # HTML pages
├── static/            # CSS and JavaScript
├── test_routes.py     # Route tests
├── requirements.txt   # Python dependencies
└── .env.example       # Example environment configuration

Tech stack

Layer

Technology

Backend

Python, Flask

Database

MongoDB, PyMongo

Frontend

HTML, CSS, JavaScript, Jinja templates

Authentication

Flask sessions, Werkzeug password hashing

Configuration

python-dotenv

Run locally (Windows PowerShell)

Install and start MongoDB Community Server. The default connection is mongodb://localhost:27017/.

Clone the repository and install its dependencies:

git clone https://github.com/yashsantoshchougule/mongodb-assignment.git
cd mongodb-assignment
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env

If necessary, change MONGO_URI, MONGO_DB_NAME, or FLASK_SECRET_KEY in .env.

Import the demonstration catalogue and start the site:

py seed_data.py
py app.py

Open http://127.0.0.1:5000 in your browser.

The default database name is valuevista_mini. Running py seed_data.py again updates matching sample records instead of duplicating them. If the import reports that MongoDB is unavailable, check that the MongoDB service is running and the URI in .env is correct.

Live demo walkthrough

For a presentation, show the project in this order:

GitHub: Introduce ValueVista Mini and briefly point out the top-level Python files, data/, templates/, and static/.

Tech stack: Explain Flask, MongoDB/PyMongo, HTML/CSS/JavaScript, and Jinja.

Website: Open the homepage to show categories, featured products, and popular products.

Catalogue: Open /products, apply a category or price filter, and change the sort order.

Product details: Open a product to show its specifications and three sample platform prices.

Comparison: Select two or three products and open /compare to show the side-by-side table. The browser remembers the comparison selection in localStorage.

Authentication: Briefly show the registration and login pages.

MongoDB Compass — last: Connect to mongodb://localhost:27017/, open valuevista_mini, and show the collections and one product document.

MongoDB collections

Collection

What it stores

products

Product details, category, prices, specifications, features, and embedded platform listings

categories

The six product categories

platforms

The five demonstration shopping platforms

users

Registered users and hashed passwords

Product specifications can vary by category. For example, a smartphone may contain RAM and battery specifications, while a camera may contain sensor and video specifications. This flexibility is one reason MongoDB is useful for the project.

Notes

Comparison selections are stored in the browser; catalogue and user records are stored in MongoDB.

This is a demonstration catalogue, not a live price-tracking or scraping system.

Some checks in test_routes.py reference older routes (/search, /deals, and /about) that are not defined in the current app.py. Those tests need updating before the complete test suite can pass.

Future scope

The project can be extended with verified retailer APIs or permitted data collectors for live pricing, and with updated tests for the current routes.
