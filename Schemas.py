import re
from typing import Optional, Literal
from pydantic import BaseModel, field_validator

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\d{10}$")


class BookIn(BaseModel):
    isbn: str
    title: str
    author: str
    genre: str = ""
    copies: int = 1

    @field_validator("copies")
    @classmethod
    def copies_positive(cls, v):
        if v < 1:
            raise ValueError("copies must be at least 1")
        return v


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    copies: Optional[int] = None


class MemberIn(BaseModel):
    name: str
    member_id: str
    email: str
    phone: str
    type: Literal["Member", "Student", "Faculty"] = "Member"
    roll_no: Optional[str] = None
    department: Optional[str] = None

    @field_validator("email")
    @classmethod
    def valid_email(cls, v):
        if not EMAIL_RE.match(v):
            raise ValueError(f"Invalid email address: {v}")
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v):
        if not PHONE_RE.match(v):
            raise ValueError("Phone number must be exactly 10 digits")
        return v


class IssueRequest(BaseModel):
    isbn: str
    member_id: str


class ReturnRequest(BaseModel):
    isbn: str
    member_id: str