# Pageturner — Library Marketplace

A full-stack library/book-lending app, built out from your original `library.py`
(the `Book`, `Student`/`Faculty`, and `Fine` logic is now ported into a real
database + API instead of in-memory objects):

- **Backend**: FastAPI + SQLAlchemy + SQLite, JWT auth, Google & GitHub OAuth login
- **Frontend**: vanilla HTML/CSS/JS, Amazon-style storefront, light/dark theme toggle
- **Data**: 10 seeded books (real titles, with cover art pulled from Open Library) +
  a demo admin account

## 1. Install & run

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit .env (see OAuth setup below)

uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** — the backend serves the frontend directly, so
there's nothing else to start. The SQLite database (`backend/library.db`) and
the 10 seed books + demo admin are created automatically on first run.

Demo admin login: **admin@library.local / admin123** — lets you add new books
under "Add a Book" in the nav bar.

## 2. What's included

| Feature | Where |
|---|---|
| Book catalog, search, category filter | `GET /api/books`, `GET /api/categories` |
| Book detail page | `GET /api/books/{id}` |
| Borrow / return a book (fine logic ported from `Fine`/`StudentFine`/`FacultyFine`) | `POST /api/books/{id}/issue`, `POST /api/loans/{id}/return` |
| Student / Faculty registration (role picker, roll no. / department) | `POST /api/auth/register` |
| Email + password login | `POST /api/auth/login` |
| Google OAuth login | `GET /api/auth/google/login` |
| GitHub OAuth login | `GET /api/auth/github/login` |
| My Loans (active + history, fines, overdue status) | `GET /api/my-loans` |
| Admin: add a book | `POST /api/books` (role = admin only) |
| Dark / light theme toggle | top-right 🌙 button, persists across visits |

Borrowing rules mirror the original script: students can hold up to 3 books
(₹0.50/day late fee), faculty up to 10 (no late fee), with a 14-day loan
period — see `ROLE_MAX_BOOKS` / `ROLE_FINE_PER_DAY` in `backend/app/models.py`
if you want to change these.

## 3. Setting up Google & GitHub login

Both are optional — the app works fully with email/password without them. The
buttons will show a friendly error until you configure credentials.

**Google** — https://console.cloud.google.com/apis/credentials
1. Create an OAuth 2.0 Client ID (type: Web application).
2. Authorized redirect URI: `http://localhost:8000/api/auth/google/callback`
3. Put the client ID/secret into `backend/.env` as `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

**GitHub** — https://github.com/settings/developers → "New OAuth App"
1. Homepage URL: `http://localhost:8000`
2. Authorization callback URL: `http://localhost:8000/api/auth/github/callback`
3. Put the client ID/secret into `backend/.env` as `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`.

Restart `uvicorn` after editing `.env`.

## 4. Project layout

```
backend/
  app/
    main.py          FastAPI app, mounts routers + serves the frontend
    database.py       SQLite engine/session
    models.py          Book / Member / Loan (+ ported fine logic)
    schemas.py          Pydantic request/response models
    security.py           JWT + password hashing
    seed.py                 10 dummy books + demo admin
    routers/
      auth.py               register/login/me + Google & GitHub OAuth
      books.py                catalog, issue/return, my-loans
  requirements.txt
  .env.example
frontend/
  index.html
  css/style.css        Amazon-inspired UI, CSS variables for light/dark theme
  js/app.js              hash-router SPA: catalog, book detail, login/register, loans, admin
```

## 5. Notes & next steps

- Passwords are hashed with bcrypt; tokens are JWTs valid for 7 days, sent as
  `Authorization: Bearer <token>` and stored in the browser's `localStorage`.
- The database is a single SQLite file — delete `backend/library.db` to reset
  everything back to the 10 seed books.
- To swap in a different image for a book, add/change `image_url` when adding
  a book from the "Add a Book" admin page.
