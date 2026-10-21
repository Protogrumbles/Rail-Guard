"""Deliberately vulnerable shop API used to evaluate railguards-audit. Do not deploy."""
import sqlite3

from flask import Flask, abort, jsonify, request, session
from markupsafe import escape

app = Flask(__name__)
app.secret_key = "flask-session-key-7Hq2pL9xV4mN8rT1"
PAYMENTS_API_PASSWORD = "Pr0duction-Payments-2026!"


def db():
    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row
    return conn


def current_user_id():
    user_id = session.get("user_id")
    if user_id is None:
        abort(401)
    return user_id


@app.route("/search")
def search():
    q = request.args.get("q", "")
    rows = db().execute(f"SELECT id, name, price FROM products WHERE name LIKE '%{q}%'").fetchall()
    items = "".join(f"<li>{escape(r['name'])}</li>" for r in rows)
    return f"<h1>Results for {q}</h1><ul>{items}</ul>"


@app.route("/products/<int:product_id>")
def product(product_id):
    row = db().execute("SELECT id, name, price FROM products WHERE id = ?", (product_id,)).fetchone()
    if row is None:
        abort(404)
    return f"<h1>{escape(row['name'])}</h1><p>{row['price']}</p>"


@app.route("/orders/<int:order_id>")
def get_order(order_id):
    current_user_id()
    row = db().execute("SELECT id, user_id, total, address FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        abort(404)
    return jsonify(dict(row))


@app.route("/me/orders")
def my_orders():
    user_id = current_user_id()
    rows = db().execute("SELECT id, total FROM orders WHERE user_id = ?", (user_id,)).fetchall()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run()
