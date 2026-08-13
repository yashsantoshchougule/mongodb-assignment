

from __future__ import annotations

from datetime import datetime
from functools import wraps
from typing import Any
from urllib.parse import urlparse

from flask import Flask, abort, render_template, request, url_for, flash, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from database import DatabaseUnavailableError, get_repository


SORT_OPTIONS = {"price_low", "price_high", "rating", "discount", "name"}
MAX_QUERY_LENGTH = 80
MAX_COMPARE_PRODUCTS = 3


def create_app(repository: Any | None = None) -> Flask:
    """Create the Flask app, optionally accepting a repository for automated tests."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.extensions["valuevista_repository"] = repository or get_repository(app.config)

    @app.template_filter("inr")
    def inr(value: int | float | None) -> str:
        """Render an Indian Rupee amount with useful digit grouping."""
        if value is None:
            return "—"
        try:
            number = int(round(float(value)))
        except (TypeError, ValueError):
            return "—"

        sign = "-" if number < 0 else ""
        digits = str(abs(number))
        if len(digits) <= 3:
            formatted = digits
        else:
            tail = digits[-3:]
            head = digits[:-3]
            chunks: list[str] = []
            while head:
                chunks.append(head[-2:])
                head = head[:-2]
            formatted = ",".join(reversed(chunks)) + "," + tail
        return f"{sign}₹{formatted}"

    @app.template_filter("store_url")
    def store_url(value: Any) -> str | None:
        """Only permit normal web links for manually maintained store URLs."""
        url = str(value or "").strip()
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return url
        return None

    @app.context_processor
    def inject_global_context() -> dict[str, Any]:
        user = None
        if "username" in session:
            user = repo().get_user_by_username(session["username"])
        return {"current_year": datetime.now().year, "current_user": user}

    def repo() -> Any:
        return app.extensions["valuevista_repository"]

    def database_view(view):
        """Turn an unavailable local MongoDB service into a clear setup message."""

        @wraps(view)
        def wrapped(*args, **kwargs):
            try:
                return view(*args, **kwargs)
            except DatabaseUnavailableError:
                return render_template("database_unavailable.html"), 503

        return wrapped

    def clean_text(value: str | None, maximum: int = MAX_QUERY_LENGTH) -> str:
        return " ".join((value or "").split())[:maximum]

    def positive_number(key: str, *, integer: bool = False) -> int | float | None:
        value = clean_text(request.args.get(key), 15)
        if not value:
            return None
        try:
            parsed: int | float = int(value) if integer else float(value)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None

    def requested_filters(*, locked_category: str | None = None) -> dict[str, Any]:
        category = locked_category or clean_text(request.args.get("category"))
        return {
            "category": category,
            "brand": clean_text(request.args.get("brand")),
            "min_price": positive_number("min_price", integer=True),
            "max_price": positive_number("max_price", integer=True),
            "min_rating": positive_number("min_rating"),
        }

    def requested_sort() -> str | None:
        requested = clean_text(request.args.get("sort"), 20)
        return requested if requested in SORT_OPTIONS else None

    def catalogue_context(
        *,
        filters: dict[str, Any],
        sort: str | None,
        query: str | None = None,
        locked_category: str | None = None,
    ) -> dict[str, Any]:
        return {
            "products": repo().get_products(filters=filters, sort=sort, query=query),
            "categories": repo().get_categories_with_counts(),
            "brands": repo().get_brands(category=locked_category or filters.get("category")),
            "filters": filters,
            "sort": sort,
        }

    @app.get("/")
    @database_view
    def home():
        return render_template(
            "home.html",
            categories=repo().get_categories_with_counts(),
            featured_products=repo().get_featured_products(limit=4),
            popular_products=repo().get_popular_products(limit=4),
        )

    @app.get("/products")
    @database_view
    def products():
        filters = requested_filters()
        sort = requested_sort()
        context = catalogue_context(filters=filters, sort=sort)
        context.update(
            {
                "action_url": request.path,
                "clear_url": "/products",
                "search_query": "",
            }
        )
        return render_template("products.html", **context)

    @app.route("/login", methods=["GET", "POST"])
    @database_view
    def login():
        if "username" in session:
            return redirect(url_for("home"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not username or not password:
                flash("Please fill in all fields.", "error")
                return render_template("login.html")
            user = repo().get_user_by_username(username)
            if user and check_password_hash(user["password_hash"], password):
                session["username"] = user["username"]
                flash(f"Welcome back, {user['username']}!", "success")
                return redirect(url_for("home"))
            flash("Invalid username or password.", "error")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    @database_view
    def register():
        if "username" in session:
            return redirect(url_for("home"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if not username or not email or not password or not confirm:
                flash("Please fill in all fields.", "error")
                return render_template("register.html")
            if len(username) < 3 or len(username) > 20:
                flash("Username must be 3-20 characters.", "error")
                return render_template("register.html")
            if password != confirm:
                flash("Passwords do not match.", "error")
                return render_template("register.html")
            if len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
                return render_template("register.html")
            if repo().get_user_by_username(username):
                flash("Username already taken.", "error")
                return render_template("register.html")
            repo().create_user(username, email, generate_password_hash(password))
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.get("/logout")
    def logout():
        session.pop("username", None)
        flash("You have been logged out.", "success")
        return redirect(url_for("home"))

    @app.get("/product/<product_id>")
    @database_view
    def product_details(product_id: str):
        product = repo().get_product(clean_text(product_id, 32))
        if not product:
            abort(404)
        return render_template("product_details.html", product=product)

    @app.get("/category/<category_name>")
    @database_view
    def category_products(category_name: str):
        category_name = clean_text(category_name)
        category = repo().get_category(category_name)
        if not category:
            abort(404)
        filters = requested_filters(locked_category=category["name"])
        sort = requested_sort()
        context = catalogue_context(filters=filters, sort=sort, locked_category=category["name"])
        context.update(
            {
                "category": category,
                "locked_category": category["name"],
                "action_url": request.path,
                "clear_url": request.path,
                "search_query": "",
            }
        )
        return render_template("category_products.html", **context)

    @app.get("/categories")
    @database_view
    def categories():
        return render_template("categories.html", categories=repo().get_categories_with_counts())

    @app.get("/compare")
    @database_view
    def compare():
        raw_ids = clean_text(request.args.get("ids"), 200)
        identifiers: list[str] = []
        for identifier in raw_ids.split(","):
            cleaned = clean_text(identifier, 32)
            if cleaned and cleaned not in identifiers:
                identifiers.append(cleaned)
            if len(identifiers) == MAX_COMPARE_PRODUCTS:
                break

        products_to_compare = repo().get_products_by_ids(identifiers) if identifiers else []
        spec_keys: list[str] = []
        for product in products_to_compare:
            for key in product.get("specifications", {}):
                if key not in spec_keys:
                    spec_keys.append(key)

        compare_message = None
        if identifiers and len(products_to_compare) != len(identifiers):
            compare_message = "One or more selected products were not found and have been left out."
        elif len(products_to_compare) == 1:
            compare_message = "Add one more product for a side-by-side comparison."

        return render_template(
            "compare.html",
            products=products_to_compare,
            spec_keys=spec_keys,
            compare_message=compare_message,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("500.html"), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
