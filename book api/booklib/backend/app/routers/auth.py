import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from ..database import get_db
from .. import models, schemas
from ..security import (
    hash_password, verify_password, create_access_token, get_current_member,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8000")

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
oauth.register(
    name="github",
    client_id=os.environ.get("GITHUB_CLIENT_ID"),
    client_secret=os.environ.get("GITHUB_CLIENT_SECRET"),
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)


def _next_member_code(db: Session) -> str:
    count = db.query(models.Member).count()
    return f"M{count + 1:04d}"


def _issue_token(member: models.Member) -> schemas.Token:
    token = create_access_token({"member_id": member.id})
    return schemas.Token(access_token=token, member=schemas.MemberOut.model_validate(member))


# ---------- Email / password ----------

@router.post("/register", response_model=schemas.Token)
def register(payload: schemas.MemberRegister, db: Session = Depends(get_db)):
    existing = db.query(models.Member).filter(models.Member.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    member = models.Member(
        member_code=_next_member_code(db),
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        role=models.Role.student if payload.role == "student" else models.Role.faculty,
        roll_no=payload.roll_no if payload.role == "student" else None,
        department=payload.department if payload.role == "faculty" else None,
        password_hash=hash_password(payload.password),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return _issue_token(member)


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.MemberLogin, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.email == payload.email).first()
    if not member or not member.password_hash or not verify_password(payload.password, member.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return _issue_token(member)


@router.get("/me", response_model=schemas.MemberOut)
def me(current: models.Member = Depends(get_current_member)):
    return current


# ---------- Google OAuth ----------

@router.get("/google/login")
async def google_login(request: Request):
    if not oauth.google.client_id:
        raise HTTPException(status_code=503, detail="Google login is not configured on this server yet.")
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or await oauth.google.userinfo(token=token)
    email = userinfo["email"]
    name = userinfo.get("name", email.split("@")[0])
    picture = userinfo.get("picture")
    sub = userinfo["sub"]

    member = db.query(models.Member).filter(models.Member.email == email).first()
    if not member:
        member = models.Member(
            member_code=_next_member_code(db),
            name=name,
            email=email,
            role=models.Role.student,
            oauth_provider="google",
            oauth_id=sub,
            avatar_url=picture,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
    elif not member.oauth_provider:
        member.oauth_provider = "google"
        member.oauth_id = sub
        member.avatar_url = member.avatar_url or picture
        db.commit()

    jwt_token = create_access_token({"member_id": member.id})
    return RedirectResponse(url=f"{FRONTEND_URL}/?token={jwt_token}")


# ---------- GitHub OAuth ----------

@router.get("/github/login")
async def github_login(request: Request):
    if not oauth.github.client_id:
        raise HTTPException(status_code=503, detail="GitHub login is not configured on this server yet.")
    redirect_uri = request.url_for("github_callback")
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/github/callback", name="github_callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.github.authorize_access_token(request)
    resp = await oauth.github.get("user", token=token)
    profile = resp.json()

    email = profile.get("email")
    if not email:
        emails_resp = await oauth.github.get("user/emails", token=token)
        emails = emails_resp.json()
        primary = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
        email = primary["email"] if primary else f"{profile['login']}@users.noreply.github.com"

    name = profile.get("name") or profile.get("login")
    picture = profile.get("avatar_url")
    sub = str(profile["id"])

    member = db.query(models.Member).filter(models.Member.email == email).first()
    if not member:
        member = models.Member(
            member_code=_next_member_code(db),
            name=name,
            email=email,
            role=models.Role.student,
            oauth_provider="github",
            oauth_id=sub,
            avatar_url=picture,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
    elif not member.oauth_provider:
        member.oauth_provider = "github"
        member.oauth_id = sub
        member.avatar_url = member.avatar_url or picture
        db.commit()

    jwt_token = create_access_token({"member_id": member.id})
    return RedirectResponse(url=f"{FRONTEND_URL}/?token={jwt_token}")
