from datetime import date
from fastapi import APIRouter, HTTPException

try:
    from ..Dp import db_cursor
    from ..Schemas import IssueRequest, ReturnRequest
    from ..Auth import CurrentUser
    from ..Models import get_fine_calculator, loan_rules_for, compute_due_date, days_late, parse_date
except ImportError:
    from Dp import db_cursor
    from Schemas import IssueRequest, ReturnRequest
    from Auth import CurrentUser
    from Models import get_fine_calculator, loan_rules_for, compute_due_date, days_late, parse_date

router = APIRouter(prefix="/api/circulation", tags=["circulation"])


@router.post("/issue")
def issue_book(req: IssueRequest, user=CurrentUser):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM books WHERE isbn = ?", (req.isbn,))
        book = cur.fetchone()
        cur.execute("SELECT * FROM members WHERE member_id = ?", (req.member_id,))
        member = cur.fetchone()

        if not book:
            raise HTTPException(404, "Book not found")
        if not member:
            raise HTTPException(404, "Member not found")
        if book["copies_issued"] >= book["copies"]:
            raise HTTPException(400, f"All copies of '{book['title']}' are currently on loan")

        rules = loan_rules_for(member["type"])
        cur.execute(
            "SELECT COUNT(*) FROM loans WHERE member_id = ? AND returned_date IS NULL",
            (req.member_id,),
        )
        held = cur.fetchone()[0]
        if held >= rules["max_books"]:
            raise HTTPException(
                400, f"{member['name']} has reached the {rules['max_books']}-book limit for {member['type']}s"
            )

    today = date.today()
    due = compute_due_date(member["type"], today)
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO loans (isbn, member_id, issued_date, due_date) VALUES (?, ?, ?, ?)",
            (req.isbn, req.member_id, today.isoformat(), due.isoformat()),
        )
        cur.execute(
            "UPDATE books SET copies_issued = copies_issued + 1 WHERE isbn = ?", (req.isbn,)
        )

    return {
        "message": f"'{book['title']}' issued to {member['name']}.",
        "due_date": due.isoformat(),
    }


@router.post("/return")
def return_book(req: ReturnRequest, user=CurrentUser):
    with db_cursor() as cur:
        cur.execute(
            """SELECT * FROM loans WHERE isbn = ? AND member_id = ? AND returned_date IS NULL
               ORDER BY issued_date DESC LIMIT 1""",
            (req.isbn, req.member_id),
        )
        loan = cur.fetchone()
        cur.execute("SELECT * FROM books WHERE isbn = ?", (req.isbn,))
        book = cur.fetchone()
        cur.execute("SELECT * FROM members WHERE member_id = ?", (req.member_id,))
        member = cur.fetchone()

    if not loan or not book:
        raise HTTPException(404, "No active loan found for that book and member")

    today = date.today()
    due = parse_date(loan["due_date"])
    late = days_late(due, today)
    fine_calc = get_fine_calculator(member["type"] if member else "Member")
    fine = fine_calc.calculate(late)

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE loans SET returned_date = ?, fine_amount = ? WHERE id = ?",
            (today.isoformat(), fine, loan["id"]),
        )
        cur.execute(
            "UPDATE books SET copies_issued = copies_issued - 1 WHERE isbn = ?", (req.isbn,)
        )

    message = f"'{book['title']}' returned."
    message += f" {late} day(s) late, fine due: Rs.{fine:.2f}" if fine > 0 else " No fine."
    return {"message": message, "days_late": late, "fine_amount": fine}


@router.get("/overdue")
def overdue_loans(user=CurrentUser):
    today = date.today().isoformat()
    with db_cursor() as cur:
        cur.execute(
            """SELECT l.*, b.title, b.author, m.name AS member_name, m.email, m.type AS member_type
               FROM loans l
               JOIN books b ON b.isbn = l.isbn
               JOIN members m ON m.member_id = l.member_id
               WHERE l.returned_date IS NULL AND l.due_date < ?
               ORDER BY l.due_date ASC""",
            (today,),
        )
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["days_late"] = days_late(parse_date(r["due_date"]))
    return {"items": rows, "total": len(rows)}


@router.get("/active")
def active_loans(user=CurrentUser):
    with db_cursor() as cur:
        cur.execute(
            """SELECT l.*, b.title, m.name AS member_name
               FROM loans l
               JOIN books b ON b.isbn = l.isbn
               JOIN members m ON m.member_id = l.member_id
               WHERE l.returned_date IS NULL
               ORDER BY l.due_date ASC"""
        )
        rows = [dict(r) for r in cur.fetchall()]
    return {"items": rows, "total": len(rows)}