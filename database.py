"""
database.py — SQLite database initialization and auth helpers
"""
import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = "travel_planner.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS itineraries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            input_source TEXT NOT NULL DEFAULT 'form',
            input_data TEXT,
            generated_plan TEXT,
            status TEXT NOT NULL DEFAULT 'generated',
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            detail TEXT,
            timestamp TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def signup_user(username: str, password: str, role: str, admin_secret: str = "") -> tuple[bool, str]:
    if role == "admin":
        expected = os.getenv("ADMIN_SECRET_KEY", "admin_secret_2024")
        if admin_secret != expected:
            return False, "Invalid admin secret key."
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), role, datetime.now().isoformat())
        )
        conn.commit()
        return True, "Signup successful."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def login_user(username: str, password: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Itinerary CRUD ---

def save_itinerary(user_id: int, input_source: str, input_data: str, generated_plan: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO itineraries (user_id, input_source, input_data, generated_plan, status, timestamp) VALUES (?,?,?,?,?,?)",
        (user_id, input_source, input_data, generated_plan, "generated", datetime.now().isoformat())
    )
    itin_id = cur.lastrowid
    conn.commit()
    conn.close()
    return itin_id


def update_itinerary(itin_id: int, generated_plan: str, status: str = "modified"):
    conn = get_conn()
    conn.execute(
        "UPDATE itineraries SET generated_plan=?, status=?, timestamp=? WHERE id=?",
        (generated_plan, status, datetime.now().isoformat(), itin_id)
    )
    conn.commit()
    conn.close()


def update_itinerary_status(itin_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE itineraries SET status=? WHERE id=?", (status, itin_id))
    conn.commit()
    conn.close()


def get_user_itineraries(user_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM itineraries WHERE user_id=? ORDER BY timestamp DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_itinerary(itin_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM itineraries WHERE id=?", (itin_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Logging ---

def log_action(user_id: int, action: str, detail: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO logs (user_id, action, detail, timestamp) VALUES (?,?,?,?)",
        (user_id, action, detail, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


# --- Admin analytics ---

def get_admin_stats() -> dict:
    conn = get_conn()
    stats = {}
    stats["total_users"] = conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0]
    stats["total_plans"] = conn.execute("SELECT COUNT(*) FROM itineraries").fetchone()[0]

    for status in ["generated", "accepted", "modified", "rejected"]:
        stats[f"plans_{status}"] = conn.execute(
            "SELECT COUNT(*) FROM itineraries WHERE status=?", (status,)
        ).fetchone()[0]

    source_rows = conn.execute(
        "SELECT input_source, COUNT(*) as cnt FROM itineraries GROUP BY input_source"
    ).fetchall()
    stats["by_source"] = {r["input_source"]: r["cnt"] for r in source_rows}

    user_rows = conn.execute("""
        SELECT u.username, COUNT(i.id) as cnt
        FROM users u LEFT JOIN itineraries i ON u.id=i.user_id
        WHERE u.role='user'
        GROUP BY u.id ORDER BY cnt DESC
    """).fetchall()
    stats["plans_per_user"] = [{"username": r["username"], "count": r["cnt"]} for r in user_rows]

    daily_rows = conn.execute("""
        SELECT substr(timestamp,1,10) as day, COUNT(*) as cnt
        FROM itineraries GROUP BY day ORDER BY day DESC LIMIT 30
    """).fetchall()
    stats["plans_per_day"] = [{"day": r["day"], "count": r["cnt"]} for r in daily_rows]

    total = stats["total_plans"]
    accepted = stats["plans_accepted"]
    stats["acceptance_rate"] = round(accepted / total * 100, 1) if total > 0 else 0

    conn.close()
    return stats