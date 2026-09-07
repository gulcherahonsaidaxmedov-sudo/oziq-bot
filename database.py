import sqlite3
import json
from datetime import datetime

DB_PATH = "shop.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            category TEXT,
            description TEXT,
            active INTEGER DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            items TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT DEFAULT 'new',
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_seen TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_user(user_id):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, first_seen) VALUES (?, ?)",
        (user_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_all_user_ids():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


def add_product(name, price, category, description):
    conn = get_conn()
    conn.execute(
        "INSERT INTO products (name, price, category, description) VALUES (?, ?, ?, ?)",
        (name, price, category, description),
    )
    conn.commit()
    conn.close()


def get_products(active_only=True):
    conn = get_conn()
    q = "SELECT * FROM products"
    if active_only:
        q += " WHERE active = 1"
    q += " ORDER BY id DESC"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(product_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_order(user_id, username, items, total):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO orders (user_id, username, items, total, status, created_at) "
        "VALUES (?, ?, ?, ?, 'new', ?)",
        (user_id, username, json.dumps(items, ensure_ascii=False), total, datetime.now().isoformat()),
    )
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    return order_id


def get_order(order_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_order_status(order_id, status):
    conn = get_conn()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()


def get_user_orders(user_id, limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_orders(limit=20):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
  
