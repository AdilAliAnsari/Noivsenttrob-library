"""
Lightweight SQLite persistence layer for noivsenttrob.

Kept dependency-free (stdlib sqlite3 only) so the app runs anywhere Python runs.
"""
import sqlite3
from contextlib import contextmanager

try:
    from .config import DB_PATH
except ImportError:
    from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    isbn TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    genre TEXT DEFAULT '',
    copies INTEGER NOT NULL DEFAULT 1,
    copies_issued INTEGER NOT NULL DEFAULT 0,
    added_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS members (
    member_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'Member',   -- Member | Student | Faculty
    roll_no TEXT,
    department TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn TEXT NOT NULL,
    member_id TEXT NOT NULL,
    issued_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    returned_date TEXT,
    fine_amount REAL DEFAULT 0,
    fine_paid INTEGER DEFAULT 0,
    FOREIGN KEY (isbn) REFERENCES books(isbn),
    FOREIGN KEY (member_id) REFERENCES members(member_id)
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,             -- "{provider}:{provider_id}"
    provider TEXT NOT NULL,
    name TEXT,
    email TEXT,
    avatar_url TEXT,
    last_login TEXT DEFAULT (datetime('now'))
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor(commit: bool = False):
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


def init_db():
    with db_cursor(commit=True) as cur:
        cur.executescript(SCHEMA)


def seed_if_empty():
    """Populate a few starter rows so the UI isn't empty on first run."""
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM books")
        has_books = cur.fetchone()[0] > 0
    if has_books:
        return

    starter_books = [
        ("ISBN-001", "Fluent Python", "Luciano Ramalho", "Programming", 2),
        ("ISBN-002", "Clean Code", "Robert C. Martin", "Programming", 1),
        ("ISBN-003", "Python Tricks", "Dan Bader", "Programming", 3),
        ("ISBN-004", "Automate the Boring Stuff", "Al Sweigart", "Programming", 2),
        ("ISBN-005", "The Pragmatic Programmer", "Hunt & Thomas", "Programming", 1),
    ]
    with db_cursor(commit=True) as cur:
        cur.executemany(
            "INSERT INTO books (isbn, title, author, genre, copies) VALUES (?, ?, ?, ?, ?)",
            starter_books,
        )