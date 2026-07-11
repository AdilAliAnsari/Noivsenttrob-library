from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import uvicorn

try:
    from . import config
    from .Dp import init_db, seed_if_empty
    from .Auth import router as auth_router
    from .Books import router as books_router
    from .Members import router as members_router
    from .Circulation import router as circulation_router
    from .Reports import router as reports_router
except ImportError:
    import config
    from Dp import init_db, seed_if_empty
    from Auth import router as auth_router
    from Books import router as books_router
    from Members import router as members_router
    from Circulation import router as circulation_router
    from Reports import router as reports_router

app = FastAPI(title="noivsenttrob", version="1.0.0")

app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET, same_site="lax")

app.include_router(auth_router)
app.include_router(books_router)
app.include_router(members_router)
app.include_router(circulation_router)
app.include_router(reports_router)


@app.on_event("startup")
def on_startup():
    init_db()
    seed_if_empty()


def render_frontend_index() -> HTMLResponse:
    html_path = config.FRONTEND_DIR / "index.html"
    html = html_path.read_text(encoding="utf-8")
    configured = bool(config.CLERK_PUBLISHABLE_KEY and config.CLERK_JS_SRC)
    html = html.replace("{{CLERK_PUBLISHABLE_KEY}}", config.CLERK_PUBLISHABLE_KEY)
    html = html.replace("{{CLERK_JS_SRC}}", config.CLERK_JS_SRC)
    html = html.replace("{{CLERK_CONFIGURED}}", "true" if configured else "false")
    return HTMLResponse(html)


if config.FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(config.FRONTEND_DIR)), name="static")

    @app.get("/")
    def index():
        return render_frontend_index()
else:
    @app.get("/")
    def index():
        return JSONResponse({"message": "Library API is running", "docs": "/docs"})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)