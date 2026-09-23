import sqlite3
from datetime import datetime

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    """Open a new database connection for this request, if one doesn't
    already exist, and store it on Flask's application context (g)."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Wipe and recreate all tables from schema.sql."""
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))


def seed_db():
    """Add a default admin user plus starter units/products, so the app is
    usable immediately without manual setup."""
    db = get_db()

    db.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ("admin", generate_password_hash("admin123")),
    )

    unit_names = ["kg", "gram", "litre", "ml", "piece", "pack", "dozen"]
    unit_ids = {}
    for name in unit_names:
        cur = db.execute("INSERT INTO units (name) VALUES (?)", (name,))
        unit_ids[name] = cur.lastrowid

    products = [
        ("Basmati Rice", "Grains", "kg", 82.0, 120),
        ("Toor Dal", "Pulses", "kg", 145.0, 60),
        ("Sunflower Oil", "Cooking Oil", "litre", 168.0, 45),
        ("Full Cream Milk", "Dairy", "litre", 66.0, 80),
        ("Amul Butter", "Dairy", "piece", 58.0, 40),
        ("Tomato", "Vegetables", "kg", 34.0, 90),
        ("Onion", "Vegetables", "kg", 28.0, 110),
        ("Potato", "Vegetables", "kg", 24.0, 130),
        ("Maggi Noodles", "Packaged Food", "pack", 14.0, 200),
        ("Tata Salt", "Grocery", "kg", 24.0, 75),
        ("Sugar", "Grocery", "kg", 44.0, 95),
        ("Eggs", "Dairy", "dozen", 78.0, 50),
        ("Bread", "Bakery", "piece", 40.0, 35),
        ("Colgate Toothpaste", "Personal Care", "piece", 55.0, 4),
        ("Surf Excel Detergent", "Household", "kg", 130.0, 3),
    ]
    for name, category, unit, price, stock in products:
        db.execute(
            "INSERT INTO products (name, category, unit_id, price, stock_qty) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, category, unit_ids[unit], price, stock),
        )

    db.commit()


@click.command("init-db")
def init_db_command():
    """Flask CLI command: `flask --app app init-db`
    Creates fresh tables and seeds starter data."""
    init_db()
    seed_db()
    click.echo("Database initialized with seed data (login: admin / admin123).")


def next_order_number(db):
    today = datetime.now().strftime("%Y%m%d")
    row = db.execute(
        "SELECT COUNT(*) AS c FROM orders WHERE order_number LIKE ?",
        (f"ORD-{today}-%",),
    ).fetchone()
    seq = row["c"] + 1
    return f"ORD-{today}-{seq:03d}"


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
