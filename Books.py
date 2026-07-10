from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends

try:
    from ..Dp import db_cursor
    from ..Schemas import BookIn, BookUpdate
    from ..Auth import CurrentUser
except ImportError:
    from Dp import db_cursor
    from Schemas import BookIn, BookUpdate
    from Auth import CurrentUser

router = APIRouter(prefix="/api/books", tags=["books"])


def _row_to_book(row) -> dict:
    d = dict(row)
    d["available"] = d["copies"] - d["copies_issued"]
    return d


@router.get("")
def list_books(
    q: Optional[str] = Query(None, description="Search title/author (regex-friendly)"),
    genre: Optional[str] = None,
    available_only: bool = False,
    page: int = 1,
    page_size: int = 20,
    user=CurrentUser,
):
    sql = "SELECT * FROM books WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like]
    if genre:
        sql += " AND genre = ?"
        params.append(genre)
    if available_only:
        sql += " AND copies > copies_issued"
    sql += " ORDER BY title COLLATE NOCASE"

    with db_cursor() as cur:
        cur.execute(sql, params)
        rows = [_row_to_book(r) for r in cur.fetchall()]

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]
    return {"items": page_rows, "total": total, "page": page, "page_size": page_size}


@router.get("/{isbn}")
def get_book(isbn: str, user=CurrentUser):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM books WHERE isbn = ?", (isbn,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Book not found")
    return _row_to_book(row)


@router.post("", status_code=201)
def add_book(book: BookIn, user=CurrentUser):
    with db_cursor() as cur:
        cur.execute("SELECT 1 FROM books WHERE isbn = ?", (book.isbn,))
        if cur.fetchone():
            raise HTTPException(409, f"A book with ISBN {book.isbn} already exists")
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO books (isbn, title, author, genre, copies) VALUES (?, ?, ?, ?, ?)",
            (book.isbn, book.title, book.author, book.genre, book.copies),
        )
    return get_book(book.isbn, user=user)


@router.put("/{isbn}")
def update_book(isbn: str, patch: BookUpdate, user=CurrentUser):
    existing = get_book(isbn, user=user)
    updates = patch.model_dump(exclude_unset=True)
    if not updates:
        return existing
    if "copies" in updates and updates["copies"] < existing["copies_issued"]:
        raise HTTPException(400, "copies cannot be lower than copies currently issued")
    fields = ", ".join(f"{k} = ?" for k in updates)
    with db_cursor(commit=True) as cur:
        cur.execute(f"UPDATE books SET {fields} WHERE isbn = ?", (*updates.values(), isbn))
    return get_book(isbn, user=user)


@router.delete("/{isbn}", status_code=204)
def delete_book(isbn: str, user=CurrentUser):
    existing = get_book(isbn, user=user)
    if existing["copies_issued"] > 0:
        raise HTTPException(400, "Cannot delete a book that currently has copies on loan")
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM books WHERE isbn = ?", (isbn,))
    return None