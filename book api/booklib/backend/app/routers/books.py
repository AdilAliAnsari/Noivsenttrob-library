from datetime import date, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..security import get_current_member, get_current_member_optional
from ..models import GRACE_PERIOD_DAYS

router = APIRouter(prefix="/api", tags=["books"])


@router.get("/books", response_model=List[schemas.BookOut])
def list_books(
    q: Optional[str] = Query(None, description="search title/author/isbn"),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Book)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(models.Book.title.ilike(like), models.Book.author.ilike(like), models.Book.isbn.ilike(like))
        )
    if category and category != "All":
        query = query.filter(models.Book.category == category)
    return query.order_by(models.Book.title).all()


@router.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    rows = db.query(models.Book.category).distinct().all()
    return sorted({r[0] for r in rows})


@router.get("/books/{book_id}", response_model=schemas.BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.post("/books", response_model=schemas.BookOut)
def create_book(
    payload: schemas.BookCreate,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    if current.role != models.Role.admin:
        raise HTTPException(status_code=403, detail="Only admins can add books")
    if db.query(models.Book).filter(models.Book.isbn == payload.isbn).first():
        raise HTTPException(status_code=400, detail="A book with this ISBN already exists")
    book = models.Book(**payload.model_dump(), available_copies=payload.total_copies)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.post("/books/{book_id}/issue", response_model=schemas.ActionResult)
def issue_book(
    book_id: int,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book.is_available:
        raise HTTPException(status_code=400, detail=f"'{book.title}' has no copies available right now")
    if current.active_loan_count >= current.max_books:
        raise HTTPException(
            status_code=400,
            detail=f"You've reached your limit of {current.max_books} books. Return one before borrowing another.",
        )

    loan = models.Loan(
        book_id=book.id,
        member_id=current.id,
        issued_date=date.today(),
        due_date=date.today() + timedelta(days=GRACE_PERIOD_DAYS),
    )
    book.available_copies -= 1
    db.add(loan)
    db.commit()
    return schemas.ActionResult(success=True, message=f"'{book.title}' issued to you. Due back in {GRACE_PERIOD_DAYS} days.")


@router.post("/loans/{loan_id}/return", response_model=schemas.ActionResult)
def return_book(
    loan_id: int,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan or loan.member_id != current.id:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.returned_date:
        raise HTTPException(status_code=400, detail="This book was already returned")

    loan.returned_date = date.today()
    fine = current.calculate_fine(loan.days_late)
    loan.fine_amount = fine
    loan.book.available_copies += 1
    db.commit()

    if fine > 0:
        return schemas.ActionResult(
            success=True, message=f"'{loan.book.title}' returned. Fine due: Rs.{fine:.2f}", fine_amount=fine
        )
    return schemas.ActionResult(success=True, message=f"'{loan.book.title}' returned. No fine.", fine_amount=0)


@router.get("/my-loans", response_model=List[schemas.LoanOut])
def my_loans(
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    return (
        db.query(models.Loan)
        .filter(models.Loan.member_id == current.id)
        .order_by(models.Loan.issued_date.desc())
        .all()
    )
