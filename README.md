# Grocery Store Management System

A POS-style billing system for small grocery/kirana stores. Staff log in,
manage products and stock, and check out bills that automatically calculate
totals and update inventory.

## Tech stack

- **Backend:** Flask (Python), REST API endpoints (GET/POST/PUT/DELETE)
- **Database:** SQLite by default (zero setup), schema written to be
  MySQL-compatible with minor changes — see "Switching to MySQL" below
- **Frontend:** Plain HTML5, CSS3, JavaScript (no framework) — the product
  and billing pages fetch data from the REST API and render it client-side
- **Auth:** Session-based login with hashed passwords (Werkzeug)

## Features

- **Login** — session-based auth, all pages protected
- **Dashboard** — total products, today's order count/revenue, low-stock alerts, recent orders
- **Products** — add, inline-edit, and delete products; live search
- **Billing** — click products to build a cart, quantities editable, auto-calculated totals, checkout creates an order and decrements stock
- **Orders** — full order history with itemized receipts
- **Settings** — change your password (current password verified before update)
- **Light/dark mode** — toggle in the nav, preference saved across visits

## Project structure

```
app.py              # Flask application factory
db.py                # SQLite connection helpers + seed data
auth.py              # Login/logout, login_required decorators
main.py              # Server-rendered pages (dashboard, products, billing, orders)
api.py                # REST JSON API (products, units, orders)
schema.sql            # Database schema
templates/            # Jinja2 templates
static/css/style.css   # All styling
static/js/
  products.js          # Product management page logic
  billing.js            # Billing/cart/checkout logic
```

## Running it locally

Requires Python 3.9+.

```bash
pip install -r requirements.txt

# Create the database and seed it with sample data + a default admin login
flask --app app init-db

# Run the dev server
flask --app app run
```

Visit `http://127.0.0.1:5000`. Default login: **admin / admin123**.

> Re-running `flask --app app init-db` wipes and reseeds the database —
> useful for resetting to a clean demo state.

## API reference

All endpoints require an active login session and return JSON.

| Method | Endpoint              | Description                        |
|--------|------------------------|-------------------------------------|
| GET    | `/api/units`            | List units of measure               |
| GET    | `/api/products`         | List products (`?q=` to search)     |
| POST   | `/api/products`         | Create a product                    |
| PUT    | `/api/products/<id>`    | Update a product                    |
| DELETE | `/api/products/<id>`    | Delete a product                    |
| GET    | `/api/orders`           | List orders                         |
| GET    | `/api/orders/<id>`      | Get one order with line items       |
| POST   | `/api/orders`           | Checkout a cart, decrements stock   |

## Switching to MySQL

The schema and queries use plain SQL, so moving to MySQL mainly means
swapping the connection layer:

1. Install a MySQL driver: `pip install mysql-connector-python`
2. In `schema.sql`, change `INTEGER PRIMARY KEY AUTOINCREMENT` to
   `INT AUTO_INCREMENT PRIMARY KEY`, and `REAL` to `DECIMAL(10,2)`.
3. In `db.py`, replace the `sqlite3.connect(...)` call in `get_db()` with a
   `mysql.connector.connect(host=..., user=..., password=..., database=...)`
   call, and use `dictionary=True` on cursors instead of `row_factory`.
4. Placeholders change from `?` to `%s` throughout `api.py` and `main.py`.

Kept as SQLite here so the project runs immediately with zero external
services — handy for local development and for a live demo deploy.

## Deploying a live demo

Render and Railway both support Flask apps directly:

1. Push this project to a GitHub repo.
2. On Render: New → Web Service → connect the repo.
   - Build command: `pip install -r requirements.txt && flask --app app init-db`
   - Start command: `gunicorn app:app` (add `gunicorn` to requirements.txt first)
3. Set the `SECRET_KEY` config value to something random before going live
   (currently `"dev"` in `app.py` — fine for local use, not for a public demo).

4. This application is live on render, just go and explore - https://grocery-store-8dsd.onrender.com

## Notes

- Passwords are hashed with Werkzeug's `generate_password_hash` — never
  stored in plain text.
- Order line items snapshot the product name and price at time of sale, so
  historical receipts stay accurate even if a product is later renamed,
  repriced, or deleted.
- Checkout runs as a single transaction — if anything fails partway through
  (e.g. a product goes out of stock mid-request), nothing is partially saved.
