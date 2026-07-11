import enum
from datetime import date, datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship

from .database import Base


class Role(str, enum.Enum):
    student = "student"
    faculty = "faculty"
    admin = "admin"


# Max books & fine-per-day mirror the original Student/Faculty/Fine classes.
ROLE_MAX_BOOKS = {Role.student: 3, Role.faculty: 10, Role.admin: 15}
ROLE_FINE_PER_DAY = {Role.student: 0.5, Role.faculty: 0.0, Role.admin: 1.0}
GRACE_PERIOD_DAYS = 14


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    member_code = Column(String, unique=True, index=True)  # e.g. M0001
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(Enum(Role), default=Role.student, nullable=False)

    # Student / Faculty specific fields (nullable — only one set is used)
    roll_no = Column(String, nullable=True)
    department = Column(String, nullable=True)

    password_hash = Column(String, nullable=True)  # null for OAuth-only accounts
    oauth_provider = Column(String, nullable=True)  # "google" | "github" | None
    oauth_id = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    loans = relationship("Loan", back_populates="member")

    @property
    def max_books(self):
        return ROLE_MAX_BOOKS.get(self.role, 2)

    @property
    def active_loan_count(self):
        return sum(1 for l in self.loans if l.returned_date is None)

    def calculate_fine(self, days_late: int) -> float:
        if days_late <= 0:
            return 0.0
        rate = ROLE_FINE_PER_DAY.get(self.role, 1.0)
        return round(days_late * rate, 2)


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    isbn = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    category = Column(String, default="General")
    description = Column(Text, default="")
    price = Column(Float, default=0.0)
    rating = Column(Float, default=4.0)
    image_url = Column(String, nullable=True)
    total_copies = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)

    loans = relationship("Loan", back_populates="book")

    @property
    def is_available(self):
        return self.available_copies > 0


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    issued_date = Column(Date, default=date.today)
    due_date = Column(Date, nullable=True)
    returned_date = Column(Date, nullable=True)
    fine_amount = Column(Float, default=0.0)
    fine_paid = Column(Boolean, default=False)

    book = relationship("Book", back_populates="loans")
    member = relationship("Member", back_populates="loans")

    @property
    def days_late(self) -> int:
        end = self.returned_date or date.today()
        if not self.due_date or end <= self.due_date:
            return 0
        return (end - self.due_date).days
