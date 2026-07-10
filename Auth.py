"""
Sign-in for noivsenttrob is intentionally limited to two providers:
Google and GitHub. There is no username/password path.

Uses Authlib's Starlette client to run the OAuth2 authorization-code
flow, then stores a small user record in the encrypted session cookie
(via Starlette's SessionMiddleware) and mirrors it into the `users`
table for a persistent login history.
"""
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, HTTPException, Depends
from starlette.responses import RedirectResponse

try:
    from . import config
    from .Dp import db_cursor
except ImportError:
    import config
    from Dp import db_cursor

router = APIRouter(prefix="/auth", tags=["auth"])

oauth = OAuth()

if config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

if config.GITHUB_CLIENT_ID and config.GITHUB_CLIENT_SECRET:
    oauth.register(
        name="github",
        client_id=config.GITHUB_CLIENT_ID,
        client_secret=config.GITHUB_CLIENT_SECRET,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )

ALLOWED_PROVIDERS = {"google", "github"}


def _save_user(provider: str, provider_id: str, name: str, email: str, avatar_url: str) -> dict:
    user_id = f"{provider}:{provider_id}"
    with db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO users (id, provider, name, email, avatar_url, last_login)
               VALUES (?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, email=excluded.email,
                 avatar_url=excluded.avatar_url, last_login=datetime('now')""",
            (user_id, provider, name, email, avatar_url),
        )
    return {"id": user_id, "provider": provider, "name": name, "email": email, "avatar_url": avatar_url}


@router.get("/login/{provider}")
async def login(provider: str, request: Request):
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(404, "Unknown provider. Only google and github are supported.")
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(
            503,
            f"{provider.title()} sign-in isn't configured yet. "
            f"Set {provider.upper()}_CLIENT_ID / _SECRET in backend/.env",
        )
    redirect_uri = request.url_for("auth_callback", provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback/{provider}", name="auth_callback")
async def auth_callback(provider: str, request: Request):
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(404, "Unknown provider")
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(503, f"{provider.title()} sign-in isn't configured")

    token = await client.authorize_access_token(request)

    if provider == "google":
        profile = token.get("userinfo") or await client.userinfo(token=token)
        user = _save_user(
            "google", profile["sub"], profile.get("name", ""), profile.get("email", ""),
            profile.get("picture", ""),
        )
    else:  # github
        profile_resp = await client.get("user", token=token)
        profile = profile_resp.json()
        email = profile.get("email")
        if not email:
            emails_resp = await client.get("user/emails", token=token)
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary")), None)
            email = primary["email"] if primary else (emails[0]["email"] if emails else "")
        user = _save_user(
            "github", str(profile["id"]), profile.get("name") or profile.get("login", ""),
            email, profile.get("avatar_url", ""),
        )

    request.session["user"] = user
    return RedirectResponse(url=config.APP_URL)


@router.post("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return {"ok": True}


@router.get("/me")
async def me(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(401, "Not signed in")
    return user


def require_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(401, "Sign in with Google or GitHub to continue")
    return user


CurrentUser = Depends(require_user)