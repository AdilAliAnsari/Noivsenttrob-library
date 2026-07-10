import csv
import io
from datetime import date

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

try:
    from ..Dp import db_cursor
    from ..Auth import CurrentUser
    from ..Models import days_late, parse_date
except ImportError:
    from Dp import db_cursor
    from Auth import CurrentUser
    from Models import days_late, parse_date

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/dashboard")
def dashboard(user=CurrentUser):
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n, COALESCE(SUM(copies),0) AS c, COALESCE(SUM(copies_issued),0) AS ci FROM books")
        b = cur.fetchone()

        cur.execute("SELECT COUNT(*) FROM members")
        member_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM loans WHERE returned_date IS NULL")
        active_loans = cur.fetchone()[0]

        today = date.today().isoformat()
        cur.execute("SELECT COUNT(*) FROM loans WHERE returned_date IS NULL AND due_date < ?", (today,))
        overdue_count = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(fine_amount),0) FROM loans WHERE fine_paid = 0")
        outstanding_fines = cur.fetchone()[0]

        cur.execute(
            """SELECT genre, COUNT(*) AS n FROM books
               WHERE genre != '' GROUP BY genre ORDER BY n DESC LIMIT 6"""
        )
        by_genre = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT b.title, COUNT(*) AS times_issued
               FROM loans l JOIN books b ON b.isbn = l.isbn
               GROUP BY l.isbn ORDER BY times_issued DESC LIMIT 5"""
        )
        top_books = [dict(r) for r in cur.fetchall()]

    return {
        "titles": b["n"],
        "total_copies": b["c"],
        "copies_on_loan": b["ci"],
        "copies_available": b["c"] - b["ci"],
        "members": member_count,
        "active_loans": active_loans,
        "overdue_loans": overdue_count,
        "outstanding_fines": round(outstanding_fines, 2),
        "by_genre": by_genre,
        "top_books": top_books,
    }


@router.get("/export.csv")
def export_csv(user=CurrentUser):
    with db_cursor() as cur:
        cur.execute(
            """SELECT l.id, b.title, b.isbn, m.name AS member_name, m.member_id,
                      l.issued_date, l.due_date, l.returned_date, l.fine_amount
               FROM loans l
               JOIN books b ON b.isbn = l.isbn
               JOIN members m ON m.member_id = l.member_id
               ORDER BY l.issued_date DESC"""
        )
        rows = cur.fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Loan ID", "Title", "ISBN", "Member", "Member ID",
                      "Issued", "Due", "Returned", "Fine (Rs.)"])
    for r in rows:
        writer.writerow(list(r))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=noivsenttrob_loans.csv"},
    )