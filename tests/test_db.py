import sqlite3
from datetime import date

import pytest
from werkzeug.security import check_password_hash

from database import db

CATEGORIES = {"Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"}


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def query(sql, params=()):
    conn = db.get_db()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def test_tables_exist(tmp_db):
    names = {r["name"] for r in query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "expenses"} <= names


def test_init_idempotent(tmp_db):
    db.init_db()
    db.init_db()


def test_foreign_keys_enforced(tmp_db):
    conn = db.get_db()
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (999, 1.0, "Food", "2026-01-01"),
            )
    finally:
        conn.close()


def test_unique_email(tmp_db):
    conn = db.get_db()
    try:
        sql = "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)"
        conn.execute(sql, ("A", "a@x.com", "h"))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, ("B", "a@x.com", "h"))
    finally:
        conn.close()


def test_seed_creates_demo_user(tmp_db):
    db.seed_db()
    rows = query("SELECT * FROM users WHERE email = ?", ("demo@spendly.com",))
    assert len(rows) == 1
    assert rows[0]["password_hash"] != "demo123"
    assert check_password_hash(rows[0]["password_hash"], "demo123")


def test_seed_idempotent(tmp_db):
    db.seed_db()
    db.seed_db()
    assert query("SELECT COUNT(*) AS c FROM users")[0]["c"] == 1
    assert query("SELECT COUNT(*) AS c FROM expenses")[0]["c"] == 8


def test_seed_expenses(tmp_db):
    db.seed_db()
    user_id = query("SELECT id FROM users")[0]["id"]
    rows = query("SELECT * FROM expenses")
    assert len(rows) == 8
    assert {r["category"] for r in rows} == CATEGORIES
    month = date.today().strftime("%Y-%m")
    assert all(r["date"].startswith(month) for r in rows)
    assert all(r["user_id"] == user_id for r in rows)
