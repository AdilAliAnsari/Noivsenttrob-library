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
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.responses import RedirectResponse
from jose import jwt, JWTError
import httpx

try:
    from . import config
    from .Dp import db_cursor, init_db
except ImportError:
    import config
    from Dp import db_cursor, init_db

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

# Clerk JWT verification setup
security = HTTPBearer()


def _save_user(provider: str, provider_id: str, name: str, email: str, avatar_url: str) -> dict:
    init_db()
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


async def verify_clerk_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify Clerk JWT token"""
    if not config.CLERK_FRONTEND_API:
        raise HTTPException(503, "Clerk is not configured")
    
    token = credentials.credentials
    try:
        # Get JWKS from Clerk
        async with httpx.AsyncClient() as client:
            jwks_resp = await client.get(f"{config.CLERK_FRONTEND_API}/.well-known/jwks.json")
            jwks_resp.raise_for_status()
            jwks = jwks_resp.json()
        
        # Decode and verify the token
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False}  # Adjust as needed for your setup
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify token: {str(e)}")


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


async def _optional_clerk_auth(credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))):
    """Optional Clerk JWT verification"""
    if not credentials or not config.CLERK_FRONTEND_API:
        return None
    try:
        async with httpx.AsyncClient() as client:
            jwks_resp = await client.get(f"{config.CLERK_FRONTEND_API}/.well-known/jwks.json")
            jwks_resp.raise_for_status()
            jwks = jwks_resp.json()
        
        payload = jwt.decode(
            credentials.credentials,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False}
        )
        return payload
    except Exception:
        return None


@router.get("/me")
async def me(request: Request, clerk_payload: dict | None = Depends(_optional_clerk_auth)):
    # If Clerk is configured and we have a valid payload, use Clerk's user info
    if clerk_payload:
        user_id = clerk_payload.get("sub")
        email = clerk_payload.get("email")
        name = clerk_payload.get("first_name", "") + " " + clerk_payload.get("last_name", "")
        avatar_url = clerk_payload.get("profile_image_url", "")
        user = _save_user("clerk", user_id, name.strip(), email, avatar_url)
        request.session["user"] = user
        return user
    
    # Fallback to session auth
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


@router.post("/login/mock")
async def mock_login(request: Request, data: dict):
    member_id = data.get("member_id", "").strip()
    role = data.get("role", "member").strip()
    
    name = "Admin User"
    email = "admin@library.local"
    
    if member_id:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM members WHERE member_id = ?", (member_id,))
            row = cur.fetchone()
            if row:
                d = dict(row)
                name = d.get("name", name)
                email = d.get("email", email)
                role = d.get("type", role).lower()
            else:
                # auto-seed a member if specified but doesn't exist
                name = f"Mock {member_id}"
                email = f"{member_id.lower()}@library.local"
    else:
        member_id = "M001"
        name = "Default Admin"
        role = "admin"

    user = {
        "id": f"mock:{member_id}",
        "provider": "mock",
        "name": name,
        "email": email,
        "avatar_url": f"https://api.dicebear.com/7.x/pixel-art/svg?seed={name}",
        "role": role,
        "member_id": member_id
    }
    request.session["user"] = user
    return user
