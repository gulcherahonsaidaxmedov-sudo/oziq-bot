import sqlite3
import json
from datetime import datetime, timedelta


DB_PATH = "shop.db"


# =========================
# CONNECTION
# =========================

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# MIGRATION
# =========================

def _ensure_column(conn, table, column, coltype):
    """
    Eski shop.db bazalarida ham yangi ustunlar
    avtomatik qo'shilishini ta'minlaydi.
    """

    cols = [
        row["name"]
        for row in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    ]

    if column not in cols:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"
        )


# =========================
# INIT DATABASE
# =========================

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # PRODUCTS
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

    # ORDERS
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

    # USERS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_seen TEXT
        )
    """)

    # SETTINGS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # ---------------------------------
    # Eski bazalar uchun yangi ustunlar
    # ---------------------------------

    _ensure_column(
        conn,
        "products",
        "image_url",
        "TEXT"
    )

    _ensure_column(
        conn,
        "products",
        "old_price",
        "INTEGER"
    )

    _ensure_column(
        conn,
        "users",
        "phone",
        "TEXT"
    )

    _ensure_column(
        conn,
        "users",
        "full_name",
        "TEXT"
    )

    _ensure_column(
        conn,
        "users",
        "username",
        "TEXT"
    )

    _ensure_column(
        conn,
        "orders",
        "daily_number",
        "INTEGER"
    )

    conn.commit()
    conn.close()


# =========================
# USERS
# =========================

def add_user(
    user_id,
    username=None,
    full_name=None
):
    conn = get_conn()

    conn.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, first_seen)
        VALUES (?, ?)
        """,
        (
            user_id,
            datetime.now().isoformat()
        )
    )

    if username is not None or full_name is not None:
        conn.execute(
            """
            UPDATE users
            SET
                username = COALESCE(?, username),
                full_name = COALESCE(?, full_name)
            WHERE user_id = ?
            """,
            (
                username,
                full_name,
                user_id
            )
        )

    conn.commit()
    conn.close()


def set_user_phone(user_id, phone):
    conn = get_conn()

    conn.execute(
        """
        UPDATE users
        SET phone = ?
        WHERE user_id = ?
        """,
        (
            phone,
            user_id
        )
    )

    conn.commit()
    conn.close()


def get_user_phone(user_id):
    conn = get_conn()

    row = conn.execute(
        """
        SELECT phone
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    return row["phone"] if row else None


def get_all_user_ids():
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT user_id
        FROM users
        """
    ).fetchall()

    conn.close()

    return [
        row["user_id"]
        for row in rows
    ]


# =========================
# PRODUCTS
# =========================

def add_product(
    name,
    price,
    category,
    description,
    image_url=None,
    old_price=None
):
    conn = get_conn()

    conn.execute(
        """
        INSERT INTO products
        (
            name,
            price,
            old_price,
            category,
            description,
            image_url,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (
            name,
            price,
            old_price,
            category,
            description,
            image_url
        )
    )

    conn.commit()
    conn.close()


def get_products(active_only=True):
    conn = get_conn()

    query = "SELECT * FROM products"

    if active_only:
        query += " WHERE active = 1"

    query += " ORDER BY id DESC"

    rows = conn.execute(query).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def get_product(product_id):
    conn = get_conn()

    row = conn.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def deactivate_product(product_id):
    """
    Mahsulotni o'chirmaydi.
    Faqat do'kondan yashiradi.
    Shu sababli eski buyurtmalar buzilmaydi.
    """

    conn = get_conn()

    conn.execute(
        """
        UPDATE products
        SET active = 0
        WHERE id = ?
        """,
        (product_id,)
    )

    conn.commit()
    conn.close()


# =========================
# ORDERS
# =========================

def add_order(
    user_id,
    username,
    items,
    total
):
    conn = get_conn()

    now = datetime.now()

    today = now.strftime("%Y-%m-%d")

    # Bugungi oxirgi navbat raqami
    row = conn.execute(
        """
        SELECT COALESCE(
            MAX(daily_number),
            0
        ) AS max_number

        FROM orders

        WHERE substr(
            created_at,
            1,
            10
        ) = ?
        """,
        (today,)
    ).fetchone()

    daily_number = (
        row["max_number"] + 1
    )

    cur = conn.execute(
        """
        INSERT INTO orders
        (
            user_id,
            username,
            items,
            total,
            status,
            created_at,
            daily_number
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            username,
            json.dumps(
                items,
                ensure_ascii=False
            ),
            total,
            "new",
            now.isoformat(),
            daily_number
        )
    )

    conn.commit()

    order_id = cur.lastrowid

    conn.close()

    return order_id


def get_order(order_id):
    conn = get_conn()

    row = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE id = ?
        """,
        (order_id,)
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def find_order_by_daily_number(
    user_id,
    daily_number
):
    """
    Faqat shu foydalanuvchining
    buyurtmasini topadi.
    """

    conn = get_conn()

    row = conn.execute(
        """
        SELECT *
        FROM orders

        WHERE
            user_id = ?
            AND daily_number = ?

        ORDER BY id DESC
        LIMIT 1
        """,
        (
            user_id,
            daily_number
        )
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def update_order_status(
    order_id,
    status
):
    conn = get_conn()

    conn.execute(
        """
        UPDATE orders
        SET status = ?
        WHERE id = ?
        """,
        (
            status,
            order_id
        )
    )

    conn.commit()
    conn.close()


def get_user_orders(
    user_id,
    limit=10
):
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT *
        FROM orders

        WHERE user_id = ?

        ORDER BY id DESC

        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def get_recent_orders(limit=20):
    conn = get_conn()

    rows = conn.execute(
        """
        SELECT *
        FROM orders

        ORDER BY id DESC

        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================
# STATISTICS
# =========================

def get_sales_summary():
    """
    Kun, hafta, oy va yil savdosi.

    Bekor qilingan buyurtmalar
    hisobga olinmaydi.
    """

    conn = get_conn()

    now = datetime.now()

    periods = [
        (
            "kun",
            now - timedelta(days=1)
        ),
        (
            "hafta",
            now - timedelta(days=7)
        ),
        (
            "oy",
            now - timedelta(days=30)
        ),
        (
            "yil",
            now - timedelta(days=365)
        )
    ]

    result = {}

    for label, since in periods:

        row = conn.execute(
            """
            SELECT
                COALESCE(
                    SUM(total),
                    0
                ) AS total,

                COUNT(*) AS cnt

            FROM orders

            WHERE
                created_at >= ?
                AND status != 'cancelled'
            """,
            (since.isoformat(),)
        ).fetchone()

        result[label] = {
            "total": row["total"],
            "count": row["cnt"]
        }

    conn.close()

    return result


# =========================
# SETTINGS
# =========================

def get_setting(
    key,
    default=None
):
    conn = get_conn()

    row = conn.execute(
        """
        SELECT value
        FROM settings
        WHERE key = ?
        """,
        (key,)
    ).fetchone()

    conn.close()

    return (
        row["value"]
        if row
        else default
    )


def set_setting(
    key,
    value
):
    conn = get_conn()

    conn.execute(
        """
        INSERT INTO settings
        (
            key,
            value
        )
        VALUES (?, ?)

        ON CONFLICT(key)
        DO UPDATE SET
            value = excluded.value
        """,
        (
            key,
            value
        )
    )

    conn.commit()
    conn.close()
