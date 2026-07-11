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
        ("978-0134757599", "Fluent Python", "Luciano Ramalho", "Programming", 2),
        ("978-0132350884", "Clean Code", "Robert C. Martin", "Programming", 1),
        ("978-1593279288", "Python Tricks", "Dan Bader", "Programming", 3),
        ("978-1593275990", "Automate the Boring Stuff", "Al Sweigart", "Programming", 2),
        ("978-0201616224", "The Pragmatic Programmer", "Andrew Hunt", "Programming", 1),
        ("978-0743273565", "The Great Gatsby", "F. Scott Fitzgerald", "Classic", 2),
        ("978-0061120084", "To Kill a Mockingbird", "Harper Lee", "Classic", 2),
        ("978-1501171345", "Atomic Habits", "James Clear", "Self Help", 3),
        ("978-1408855652", "Harry Potter and the Philosopher's Stone", "J.K. Rowling", "Fantasy", 2),
        ("978-0345803481", "The Hobbit", "J.R.R. Tolkien", "Fantasy", 2),
    ]
    with db_cursor(commit=True) as cur:
        cur.executemany(
            "INSERT INTO books (isbn, title, author, genre, copies) VALUES (?, ?, ?, ?, ?)",
            starter_books,
        )