from typing import Optional
from fastapi import APIRouter, HTTPException, Query

try:
    from ..Dp import db_cursor
    from ..Schemas import MemberIn
    from ..Auth import CurrentUser
except ImportError:
    from Dp import db_cursor
    from Schemas import MemberIn
    from Auth import CurrentUser

router = APIRouter(prefix="/api/members", tags=["members"])


def _books_held_count(cur, member_id: str) -> int:
    cur.execute(
        "SELECT COUNT(*) FROM loans WHERE member_id = ? AND returned_date IS NULL", (member_id,)
    )
    return cur.fetchone()[0]


@router.get("")
def list_members(q: Optional[str] = None, type: Optional[str] = None, user=CurrentUser):
    sql = "SELECT * FROM members WHERE 1=1"
    params: list = []
    if q:
        like = f"%{q}%"
        sql += " AND (name LIKE ? OR member_id LIKE ? OR email LIKE ?)"
        params += [like, like, like]
    if type:
        sql += " AND type = ?"
        params.append(type)
    sql += " ORDER BY name COLLATE NOCASE"
    with db_cursor() as cur:
        cur.execute(sql, params)
        members = []
        for row in cur.fetchall():
            d = dict(row)
            d["books_held"] = _books_held_count(cur, d["member_id"])
            members.append(d)
    return {"items": members, "total": len(members)}


@router.get("/{member_id}")
def get_member(member_id: str, user=CurrentUser):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM members WHERE member_id = ?", (member_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Member not found")
        d = dict(row)
        d["books_held"] = _books_held_count(cur, member_id)
    return d


@router.post("", status_code=201)
def register_member(member: MemberIn, user=CurrentUser):
    with db_cursor() as cur:
        cur.execute("SELECT 1 FROM members WHERE member_id = ?", (member.member_id,))
        if cur.fetchone():
            raise HTTPException(409, f"Member ID {member.member_id} is already registered")
    with db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO members (member_id, name, email, phone, type, roll_no, department)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (member.member_id, member.name, member.email, member.phone,
             member.type, member.roll_no, member.department),
        )
    return get_member(member.member_id, user=user)


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: str, user=CurrentUser):
    member = get_member(member_id, user=user)
    if member["books_held"] > 0:
        raise HTTPException(400, "Cannot remove a member who still has books on loan")
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM members WHERE member_id = ?", (member_id,))
    return None