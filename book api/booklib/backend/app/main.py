import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # load backend/.env before anything reads os.environ

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import Base, engine
from .routers import auth, books
from . import seed

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

app = FastAPI(title="Book Library API")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)  # required by Authlib for OAuth state
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed.run()


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")
