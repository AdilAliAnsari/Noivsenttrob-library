import re
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, field_validator

PHONE_RE = re.compile(r"^\d{10}$")


# ---------- Members ----------

class MemberRegister(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    role: str  # "student" | "faculty"
    roll_no: Optional[str] = None
    department: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not PHONE_RE.match(v):
            raise ValueError("Phone number must be exactly 10 digits")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("student", "faculty"):
            raise ValueError("role must be 'student' or 'faculty'")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class MemberLogin(BaseModel):
    email: EmailStr
    password: str


class MemberOut(BaseModel):
    id: int
    member_code: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    roll_no: Optional[str] = None
    department: Optional[str] = None
    avatar_url: Optional[str] = None
    max_books: int
    active_loan_count: int
    oauth_provider: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    member: MemberOut


# ---------- Books ----------

class BookOut(BaseModel):
    id: int
    isbn: str
    title: str
    author: str
    category: str
    description: str
    price: float
    rating: float
    image_url: Optional[str] = None
    total_copies: int
    available_copies: int
    is_available: bool

    class Config:
        from_attributes = True


class BookCreate(BaseModel):
    isbn: str
    title: str
    author: str
    category: str = "General"
    description: str = ""
    price: float = 0.0
    rating: float = 4.0
    image_url: Optional[str] = None
    total_copies: int = 1


# ---------- Loans ----------

class LoanOut(BaseModel):
    id: int
    book: BookOut
    issued_date: date
    due_date: Optional[date] = None
    returned_date: Optional[date] = None
    fine_amount: float
    days_late: int

    class Config:
        from_attributes = True


class ActionResult(BaseModel):
    success: bool
    message: str
    fine_amount: Optional[float] = None
