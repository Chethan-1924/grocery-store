from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from auth import login_required
from db import get_db

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    db = get_db()

    total_products = db.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]

    today_orders = db.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(total_amount), 0) AS total "
        "FROM orders WHERE date(created_at) = date('now')"
    ).fetchone()

    low_stock = db.execute(
        "SELECT p.id, p.name, p.stock_qty, u.name AS unit "
        "FROM products p JOIN units u ON p.unit_id = u.id "
        "WHERE p.stock_qty < 5 ORDER BY p.stock_qty ASC"
    ).fetchall()

    recent_orders = db.execute(
        "SELECT id, order_number, total_amount, created_at "
        "FROM orders ORDER BY created_at DESC LIMIT 5"
    ).fetchall()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        today_order_count=today_orders["c"],
        today_revenue=today_orders["total"],
        low_stock=low_stock,
        recent_orders=recent_orders,
    )


@bp.route("/products")
@login_required
def products_page():
    return render_template("products.html")


@bp.route("/billing")
@login_required
def billing_page():
    return render_template("billing.html")


@bp.route("/orders")
@login_required
def orders_page():
    db = get_db()
    orders = db.execute(
        "SELECT o.id, o.order_number, o.total_amount, o.created_at, u.username "
        "FROM orders o LEFT JOIN users u ON o.user_id = u.id "
        "ORDER BY o.created_at DESC"
    ).fetchall()
    return render_template("orders.html", orders=orders)


@bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    db = get_db()
    order = db.execute(
        "SELECT o.*, u.username FROM orders o LEFT JOIN users u ON o.user_id = u.id "
        "WHERE o.id = ?",
        (order_id,),
    ).fetchone()
    items = db.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    return render_template("order_detail.html", order=order, items=items)


@bp.route("/settings", methods=("GET", "POST"))
@login_required
def settings():
    if request.method == "POST":
        flash("Password changes are disabled on this public demo — see note below.")
        return redirect(url_for("main.settings"))

    return render_template("settings.html")



# @bp.route("/settings", methods=("GET", "POST"))
# @login_required
# def settings():
#     if request.method == "POST":
#         current_password = request.form.get("current_password", "")
#         new_password = request.form.get("new_password", "")
#         confirm_password = request.form.get("confirm_password", "")

#         db = get_db()
#         user = db.execute(
#             "SELECT * FROM users WHERE id = ?", (g.user["id"],)
#         ).fetchone()

#         error = None
#         if not check_password_hash(user["password_hash"], current_password):
#             error = "Current password is incorrect."
#         elif len(new_password) < 6:
#             error = "New password must be at least 6 characters."
#         elif new_password != confirm_password:
#             error = "New password and confirmation don't match."

#         if error:
#             flash(error)
#         else:
#             db.execute(
#                 "UPDATE users SET password_hash = ? WHERE id = ?",
#                 (generate_password_hash(new_password), g.user["id"]),
#             )
#             db.commit()
#             flash("Password updated successfully.")
#             return redirect(url_for("main.settings"))

#     return render_template("settings.html")
