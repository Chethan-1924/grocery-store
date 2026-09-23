import sqlite3

from flask import Blueprint, jsonify, request

from auth import api_login_required
from db import get_db, next_order_number

bp = Blueprint("api", __name__, url_prefix="/api")


def row_to_dict(row):
    return dict(row) if row else None


# ---------------------------------------------------------------- Units ----
@bp.route("/units", methods=["GET"])
@api_login_required
def list_units():
    db = get_db()
    rows = db.execute("SELECT id, name FROM units ORDER BY name").fetchall()
    return jsonify([row_to_dict(r) for r in rows])


# ------------------------------------------------------------- Products ----
@bp.route("/products", methods=["GET"])
@api_login_required
def list_products():
    db = get_db()
    q = request.args.get("q", "").strip()
    if q:
        rows = db.execute(
            "SELECT p.id, p.name, p.category, p.price, p.stock_qty, "
            "u.id AS unit_id, u.name AS unit_name "
            "FROM products p JOIN units u ON p.unit_id = u.id "
            "WHERE p.name LIKE ? ORDER BY p.name",
            (f"%{q}%",),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT p.id, p.name, p.category, p.price, p.stock_qty, "
            "u.id AS unit_id, u.name AS unit_name "
            "FROM products p JOIN units u ON p.unit_id = u.id "
            "ORDER BY p.name"
        ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@bp.route("/products", methods=["POST"])
@api_login_required
def create_product():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    unit_id = data.get("unit_id")
    price = data.get("price")
    stock_qty = data.get("stock_qty", 0)
    category = (data.get("category") or "").strip()

    if not name or unit_id is None or price is None:
        return jsonify({"error": "name, unit_id, and price are required"}), 400

    try:
        price = float(price)
        stock_qty = float(stock_qty)
    except (TypeError, ValueError):
        return jsonify({"error": "price and stock_qty must be numbers"}), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO products (name, category, unit_id, price, stock_qty) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, category, unit_id, price, stock_qty),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)}), 400

    new_id = cur.lastrowid
    row = db.execute(
        "SELECT p.id, p.name, p.category, p.price, p.stock_qty, "
        "u.id AS unit_id, u.name AS unit_name "
        "FROM products p JOIN units u ON p.unit_id = u.id WHERE p.id = ?",
        (new_id,),
    ).fetchone()
    return jsonify(row_to_dict(row)), 201


@bp.route("/products/<int:product_id>", methods=["PUT"])
@api_login_required
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    existing = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if existing is None:
        return jsonify({"error": "Product not found"}), 404

    name = data.get("name", existing["name"])
    category = data.get("category", existing["category"])
    unit_id = data.get("unit_id", existing["unit_id"])
    price = data.get("price", existing["price"])
    stock_qty = data.get("stock_qty", existing["stock_qty"])

    try:
        price = float(price)
        stock_qty = float(stock_qty)
    except (TypeError, ValueError):
        return jsonify({"error": "price and stock_qty must be numbers"}), 400

    db.execute(
        "UPDATE products SET name=?, category=?, unit_id=?, price=?, stock_qty=? WHERE id=?",
        (name, category, unit_id, price, stock_qty, product_id),
    )
    db.commit()

    row = db.execute(
        "SELECT p.id, p.name, p.category, p.price, p.stock_qty, "
        "u.id AS unit_id, u.name AS unit_name "
        "FROM products p JOIN units u ON p.unit_id = u.id WHERE p.id = ?",
        (product_id,),
    ).fetchone()
    return jsonify(row_to_dict(row))


@bp.route("/products/<int:product_id>", methods=["DELETE"])
@api_login_required
def delete_product(product_id):
    db = get_db()
    existing = db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
    if existing is None:
        return jsonify({"error": "Product not found"}), 404

    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    return jsonify({"deleted": product_id})


# --------------------------------------------------------------- Orders ----
@bp.route("/orders", methods=["GET"])
@api_login_required
def list_orders():
    db = get_db()
    rows = db.execute(
        "SELECT id, order_number, total_amount, created_at FROM orders "
        "ORDER BY created_at DESC"
    ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@bp.route("/orders/<int:order_id>", methods=["GET"])
@api_login_required
def get_order(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        return jsonify({"error": "Order not found"}), 404
    items = db.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    result = row_to_dict(order)
    result["items"] = [row_to_dict(i) for i in items]
    return jsonify(result)


@bp.route("/orders", methods=["POST"])
@api_login_required
def create_order():
    """Checkout: takes a cart of {product_id, quantity}, validates stock,
    snapshots prices, creates the order + order_items, and decrements stock —
    all in a single transaction so a failure partway through rolls back
    cleanly instead of leaving stock or totals inconsistent."""
    from flask import g

    data = request.get_json(silent=True) or {}
    items = data.get("items", [])

    if not items:
        return jsonify({"error": "Cart is empty"}), 400

    db = get_db()
    total = 0.0
    resolved_items = []

    for item in items:
        product_id = item.get("product_id")
        try:
            quantity = float(item.get("quantity", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid quantity"}), 400

        if quantity <= 0:
            return jsonify({"error": "Quantity must be greater than zero"}), 400

        product = db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if product is None:
            return jsonify({"error": f"Product {product_id} not found"}), 404
        if product["stock_qty"] < quantity:
            return jsonify({
                "error": f"Not enough stock for {product['name']} "
                         f"(have {product['stock_qty']}, need {quantity})"
            }), 400

        line_total = round(product["price"] * quantity, 2)
        total += line_total
        resolved_items.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "quantity": quantity,
            "unit_price": product["price"],
            "line_total": line_total,
        })

    total = round(total, 2)
    order_number = next_order_number(db)

    try:
        cur = db.execute(
            "INSERT INTO orders (order_number, user_id, total_amount) VALUES (?, ?, ?)",
            (order_number, g.user["id"], total),
        )
        order_id = cur.lastrowid

        for ri in resolved_items:
            db.execute(
                "INSERT INTO order_items "
                "(order_id, product_id, product_name, quantity, unit_price, line_total) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (order_id, ri["product_id"], ri["product_name"], ri["quantity"],
                 ri["unit_price"], ri["line_total"]),
            )
            db.execute(
                "UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?",
                (ri["quantity"], ri["product_id"]),
            )

        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Checkout failed: {e}"}), 500

    return jsonify({
        "id": order_id,
        "order_number": order_number,
        "total_amount": total,
        "items": resolved_items,
    }), 201
