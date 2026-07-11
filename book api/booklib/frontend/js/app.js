/* ============ Config & state ============ */
const API = "https://fresh-hornets-yawn.loca.lt/api";
const state = {
  token: localStorage.getItem("pt_token") || null,
  member: null,
  books: [],
  categories: ["All"],
  currentCategory: "All",
  currentQuery: "",
};

/* ============ Fallback cover if Open Library has none ============ */
const FALLBACK_COVER =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='300' height='400'>
       <rect width='100%' height='100%' fill='#d9c9a3'/>
       <text x='50%' y='50%' font-family='Georgia' font-size='20' fill='#4a3b25' text-anchor='middle'>No cover</text>
     </svg>`
  );

/* ============ API helper ============ */
async function api(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || `Request failed (${res.status})`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

/* ============ Toast ============ */
let toastTimer;
function toast(msg, type = "success") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = `toast ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 3200);
}

/* ============ Theme ============ */
function initTheme() {
  const saved = localStorage.getItem("pt_theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  updateThemeIcon(saved);
}
function toggleTheme() {
  const cur = document.documentElement.getAttribute("data-theme");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("pt_theme", next);
  updateThemeIcon(next);
}
function updateThemeIcon(theme) {
  document.getElementById("themeToggle").textContent = theme === "dark" ? "☀️" : "🌙";
}

/* ============ Auth ============ */
function setSession(token, member) {
  state.token = token;
  state.member = member;
  if (token) localStorage.setItem("pt_token", token);
  else localStorage.removeItem("pt_token");
  renderAccountArea();
}

async function loadMe() {
  if (!state.token) return;
  try {
    state.member = await api("/auth/me", { auth: true });
  } catch (e) {
    setSession(null, null);
  }
  renderAccountArea();
}

function logout() {
  setSession(null, null);
  toast("Signed out", "success");
  Router.go("home");
}

function renderAccountArea() {
  const btn = document.getElementById("accountBtn");
  const menu = document.getElementById("accountMenu");
  const adminLink = document.getElementById("adminNavLink");

  if (state.member) {
    btn.querySelector(".account-greeting").textContent = `Hello, ${state.member.name.split(" ")[0]}`;
    btn.querySelector(".account-sub").textContent = "Account & Lists ▾";
    menu.innerHTML = `
      <a href="#" data-nav="loans">Your loans</a>
      <a href="#" id="logoutLink">Sign out</a>
    `;
    menu.querySelector("#logoutLink").addEventListener("click", (e) => { e.preventDefault(); logout(); });
    adminLink.classList.toggle("hidden", state.member.role !== "admin");
  } else {
    btn.querySelector(".account-greeting").textContent = "Hello, sign in";
    btn.querySelector(".account-sub").textContent = "Account & Lists ▾";
    menu.innerHTML = `
      <a href="#" data-nav="login">Sign in</a>
      <a href="#" data-nav="register">New here? Register</a>
    `;
    adminLink.classList.add("hidden");
  }
  bindNavLinks(menu);
  updateLoansCount();
}

async function updateLoansCount() {
  if (!state.member) { document.getElementById("loansCount").textContent = "0"; return; }
  try {
    const loans = await api("/my-loans", { auth: true });
    const active = loans.filter((l) => !l.returned_date).length;
    document.getElementById("loansCount").textContent = String(active);
  } catch (_) { /* ignore */ }
}

/* ============ Router ============ */
const Router = {
  go(view, params = {}) {
    location.hash = `${view}${params.id ? "/" + params.id : ""}${params.cat ? "?cat=" + encodeURIComponent(params.cat) : ""}`;
  },
  async render() {
    const hash = location.hash.replace("#", "") || "home";
    const [pathPart, queryPart] = hash.split("?");
    const [view, id] = pathPart.split("/");
    const params = new URLSearchParams(queryPart || "");
    document.getElementById("accountMenu").classList.add("hidden");
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });

    switch (view) {
      case "home": return Views.home();
      case "category": return Views.home(params.get("cat") || "All");
      case "book": return Views.bookDetail(id);
      case "login": return Views.login();
      case "register": return Views.register();
      case "loans": return Views.loans();
      case "admin": return Views.admin();
      default: return Views.home();
    }
  },
};

function bindNavLinks(scope = document) {
  scope.querySelectorAll("[data-nav]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      const view = el.dataset.nav;
      const cat = el.dataset.cat;
      if (view === "category") Router.go("category", { cat });
      else if (view === "loans" && !state.member) Router.go("login");
      else if (view === "admin" && (!state.member || state.member.role !== "admin")) Router.go("login");
      else Router.go(view);
    });
  });
}

/* ============ Views ============ */
const app = document.getElementById("app");

const Views = {
  async home(category = state.currentCategory, query = state.currentQuery) {
    state.currentCategory = category;
    app.innerHTML = `
      <section class="hero">
        <div>
          <span class="hero-badge">Reading, on loan</span>
          <h1>Borrow more. Own less clutter.</h1>
          <p>Browse the full catalog, reserve a copy in one tap, and track every due date from "My Loans".</p>
        </div>
      </section>
      <h2 class="section-title" id="gridTitle">All books</h2>
      <div class="book-grid" id="bookGrid"><p>Loading books…</p></div>
    `;

    try {
      const qs = new URLSearchParams();
      if (query) qs.set("q", query);
      if (category && category !== "All") qs.set("category", category);
      const books = await api(`/books?${qs.toString()}`);
      state.books = books;
      document.getElementById("gridTitle").textContent =
        query ? `Results for "${query}"` : category !== "All" ? category : "All books";
      renderBookGrid(books);
    } catch (e) {
      document.getElementById("bookGrid").innerHTML = `<p>Could not load books: ${e.message}</p>`;
    }
  },

  async bookDetail(id) {
    app.innerHTML = `<p>Loading…</p>`;
    try {
      const book = await api(`/books/${id}`);
      const available = book.available_copies > 0;
      app.innerHTML = `
        <div class="book-detail">
          <div class="book-thumb">
            <img src="${book.image_url || FALLBACK_COVER}" onerror="this.src='${FALLBACK_COVER}'" alt="${escapeHtml(book.title)} cover">
          </div>
          <div>
            <h1>${escapeHtml(book.title)}</h1>
            <div class="meta-line">by <strong>${escapeHtml(book.author)}</strong> &middot; ${escapeHtml(book.category)} &middot; ★ ${book.rating.toFixed(1)} &middot; ISBN ${book.isbn}</div>
            <p class="desc">${escapeHtml(book.description || "No description available for this title yet.")}</p>
          </div>
          <div class="buy-box">
            <div class="price-line">₹${book.price.toFixed(2)}</div>
            <div class="avail-line ${available ? "in" : "out"}">
              ${available ? `${book.available_copies} of ${book.total_copies} copies available` : "Currently all copies are checked out"}
            </div>
            <button class="btn btn-primary btn-block" id="issueBtn" ${available ? "" : "disabled"}>
              ${available ? "Borrow this book" : "Join waitlist (unavailable)"}
            </button>
          </div>
        </div>
      `;
      document.getElementById("issueBtn").addEventListener("click", () => issueBook(book.id));
    } catch (e) {
      app.innerHTML = `<div class="empty-state"><span class="emoji">📕</span><p>${e.message}</p></div>`;
    }
  },

  login() {
    app.innerHTML = `
      <div class="form-shell">
        <h2>Sign in</h2>
        <p class="form-sub">Welcome back — sign in to borrow books and track loans.</p>
        <div id="formError"></div>
        <form id="loginForm">
          <div class="field"><label>Email</label><input type="email" name="email" required></div>
          <div class="field"><label>Password</label><input type="password" name="password" required></div>
          <button type="submit" class="btn btn-primary btn-block">Sign in</button>
        </form>
        <div class="divider">or continue with</div>
        <div class="oauth-row">
          <a class="oauth-btn" href="${API}/auth/google/login"><span class="g-icon">G</span> Continue with Google</a>
          <a class="oauth-btn" href="${API}/auth/github/login"><span class="gh-icon">🐙</span> Continue with GitHub</a>
        </div>
        <div class="form-switch">New to Pageturner? <a href="#" data-nav="register">Create your account</a></div>
      </div>
    `;
    bindNavLinks(app);
    document.getElementById("loginForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        const data = await api("/auth/login", {
          method: "POST",
          body: { email: fd.get("email"), password: fd.get("password") },
        });
        setSession(data.access_token, data.member);
        toast(`Welcome back, ${data.member.name.split(" ")[0]}!`);
        Router.go("home");
      } catch (err) {
        showFormError(err.message);
      }
    });
  },

  register() {
    app.innerHTML = `
      <div class="form-shell">
        <h2>Create account</h2>
        <p class="form-sub">Register as a student or faculty member to start borrowing.</p>
        <div id="formError"></div>
        <div class="role-toggle" id="roleToggle">
          <button type="button" data-role="student" class="active">🎓 Student</button>
          <button type="button" data-role="faculty">🧑‍🏫 Faculty</button>
        </div>
        <form id="registerForm">
          <div class="field"><label>Full name</label><input name="name" required></div>
          <div class="field"><label>Email</label><input type="email" name="email" required></div>
          <div class="field"><label>Phone (10 digits)</label><input name="phone" pattern="\\d{10}" maxlength="10" required></div>
          <div class="field" id="roleField"><label>Roll number</label><input name="roleValue" placeholder="e.g. R101" required></div>
          <div class="field"><label>Password</label><input type="password" name="password" minlength="6" required></div>
          <button type="submit" class="btn btn-primary btn-block">Create account</button>
        </form>
        <div class="divider">or continue with</div>
        <div class="oauth-row">
          <a class="oauth-btn" href="${API}/auth/google/login"><span class="g-icon">G</span> Continue with Google</a>
          <a class="oauth-btn" href="${API}/auth/github/login"><span class="gh-icon">🐙</span> Continue with GitHub</a>
        </div>
        <div class="form-switch">Already registered? <a href="#" data-nav="login">Sign in</a></div>
      </div>
    `;
    bindNavLinks(app);

    let role = "student";
    const roleField = document.getElementById("roleField");
    document.querySelectorAll("#roleToggle button").forEach((b) => {
      b.addEventListener("click", () => {
        role = b.dataset.role;
        document.querySelectorAll("#roleToggle button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        roleField.innerHTML =
          role === "student"
            ? `<label>Roll number</label><input name="roleValue" placeholder="e.g. R101" required>`
            : `<label>Department</label><input name="roleValue" placeholder="e.g. CSE" required>`;
      });
    });

    document.getElementById("registerForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = {
        name: fd.get("name"),
        email: fd.get("email"),
        phone: fd.get("phone"),
        password: fd.get("password"),
        role,
      };
      if (role === "student") payload.roll_no = fd.get("roleValue");
      else payload.department = fd.get("roleValue");

      try {
        const data = await api("/auth/register", { method: "POST", body: payload });
        setSession(data.access_token, data.member);
        toast(`Welcome, ${data.member.name.split(" ")[0]}! Account created.`);
        Router.go("home");
      } catch (err) {
        showFormError(err.message);
      }
    });
  },

  async loans() {
    if (!state.member) return Router.go("login");
    app.innerHTML = `<h2 class="section-title">My loans</h2><div id="loanList">Loading…</div>`;
    try {
      const loans = await api("/my-loans", { auth: true });
      const list = document.getElementById("loanList");
      if (loans.length === 0) {
        list.innerHTML = `<div class="empty-state"><span class="emoji">📚</span>No loans yet — go find something to read.</div>`;
        return;
      }
      list.innerHTML = loans.map(loanRowHtml).join("");
      loans.forEach((l) => {
        if (!l.returned_date) {
          const btn = document.getElementById(`return-${l.id}`);
          if (btn) btn.addEventListener("click", () => returnBook(l.id));
        }
      });
    } catch (e) {
      document.getElementById("loanList").innerHTML = `<p>${e.message}</p>`;
    }
  },

  admin() {
    if (!state.member || state.member.role !== "admin") return Router.go("login");
    app.innerHTML = `
      <div class="form-shell">
        <h2>Add a book</h2>
        <p class="form-sub">Admin only — add a new title to the catalog.</p>
        <div id="formError"></div>
        <form id="addBookForm">
          <div class="field"><label>Title</label><input name="title" required></div>
          <div class="field"><label>Author</label><input name="author" required></div>
          <div class="field"><label>ISBN</label><input name="isbn" required></div>
          <div class="field"><label>Category</label><input name="category" value="General"></div>
          <div class="field"><label>Price (₹)</label><input type="number" step="0.01" name="price" value="0"></div>
          <div class="field"><label>Copies</label><input type="number" name="total_copies" value="1" min="1"></div>
          <div class="field"><label>Cover image URL (optional)</label><input name="image_url" placeholder="https://…"></div>
          <div class="field"><label>Description</label><input name="description"></div>
          <button type="submit" class="btn btn-primary btn-block">Add to catalog</button>
        </form>
      </div>
    `;
    document.getElementById("addBookForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = Object.fromEntries(fd.entries());
      payload.price = parseFloat(payload.price || "0");
      payload.total_copies = parseInt(payload.total_copies || "1", 10);
      try {
        await api("/books", { method: "POST", auth: true, body: payload });
        toast("Book added to catalog!");
        Router.go("home");
      } catch (err) {
        showFormError(err.message);
      }
    });
  },
};

function showFormError(msg) {
  const el = document.getElementById("formError");
  if (el) el.innerHTML = `<div class="form-error">${escapeHtml(msg)}</div>`;
}

/* ============ Rendering helpers ============ */
function renderBookGrid(books) {
  const grid = document.getElementById("bookGrid");
  if (!books.length) {
    grid.innerHTML = `<div class="empty-state"><span class="emoji">🔎</span>No books matched your search.</div>`;
    return;
  }
  const tpl = document.getElementById("tpl-book-card");
  grid.innerHTML = "";
  books.forEach((book) => {
    const node = tpl.content.cloneNode(true);
    const card = node.querySelector(".book-card");
    const img = node.querySelector(".book-thumb img");
    img.src = book.image_url || FALLBACK_COVER;
    img.alt = `${book.title} cover`;
    img.onerror = () => { img.src = FALLBACK_COVER; };

    const badge = node.querySelector(".book-badge");
    badge.textContent = book.is_available ? "In stock" : "Checked out";
    badge.classList.toggle("out", !book.is_available);

    node.querySelector(".book-title").textContent = book.title;
    node.querySelector(".book-author").textContent = book.author;
    node.querySelector(".book-rating").textContent = `★ ${book.rating.toFixed(1)}`;
    node.querySelector(".book-price").textContent = book.price.toFixed(2);

    const issueBtn = node.querySelector(".book-issue-btn");
    issueBtn.disabled = !book.is_available;
    issueBtn.textContent = book.is_available ? "Borrow this book" : "Unavailable";
    issueBtn.addEventListener("click", (e) => { e.stopPropagation(); issueBook(book.id); });

    card.addEventListener("click", () => Router.go("book", { id: book.id }));
    grid.appendChild(node);
  });
}

function loanRowHtml(l) {
  const returned = !!l.returned_date;
  const overdue = !returned && l.due_date && new Date(l.due_date) < new Date();
  const statusClass = returned ? "returned" : overdue ? "overdue" : "active";
  const statusText = returned
    ? `Returned ${l.returned_date}${l.fine_amount > 0 ? ` · Fine ₹${l.fine_amount.toFixed(2)}` : ""}`
    : overdue
    ? `Overdue since ${l.due_date}`
    : `Due ${l.due_date}`;
  return `
    <div class="loan-row">
      <img src="${l.book.image_url || FALLBACK_COVER}" onerror="this.src='${FALLBACK_COVER}'">
      <div class="loan-info">
        <div class="loan-title">${escapeHtml(l.book.title)}</div>
        <div class="loan-sub">Issued ${l.issued_date}</div>
        <span class="status-pill ${statusClass}">${statusText}</span>
      </div>
      ${returned ? "" : `<button class="btn btn-outline" id="return-${l.id}">Return</button>`}
    </div>
  `;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

/* ============ Actions ============ */
async function issueBook(bookId) {
  if (!state.member) { toast("Sign in to borrow a book", "error"); return Router.go("login"); }
  try {
    const result = await api(`/books/${bookId}/issue`, { method: "POST", auth: true });
    toast(result.message, "success");
    updateLoansCount();
    Router.render();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function returnBook(loanId) {
  try {
    const result = await api(`/loans/${loanId}/return`, { method: "POST", auth: true });
    toast(result.message, result.fine_amount > 0 ? "error" : "success");
    updateLoansCount();
    Views.loans();
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ============ Category dropdown + search ============ */
async function loadCategories() {
  try {
    const cats = await api("/categories");
    state.categories = ["All", ...cats];
    const select = document.getElementById("categorySelect");
    select.innerHTML = state.categories.map((c) => `<option value="${c}">${c}</option>`).join("");
    select.addEventListener("change", () => Router.go("category", { cat: select.value }));
  } catch (_) { /* ignore */ }
}

function bindSearch() {
  const input = document.getElementById("searchInput");
  const doSearch = () => {
    state.currentQuery = input.value.trim();
    Views.home(document.getElementById("categorySelect").value, state.currentQuery);
  };
  document.getElementById("searchBtn").addEventListener("click", doSearch);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });
}

/* ============ Boot ============ */
function consumeOAuthTokenFromUrl() {
  const url = new URL(location.href);
  const token = url.searchParams.get("token");
  if (token) {
    setSession(token, null);
    url.searchParams.delete("token");
    history.replaceState({}, "", url.pathname + url.hash);
    loadMe().then(() => toast(`Welcome, ${state.member ? state.member.name.split(" ")[0] : ""}!`));
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  document.getElementById("themeToggle").addEventListener("click", toggleTheme);
  document.getElementById("accountBtn").addEventListener("click", () => {
    document.getElementById("accountMenu").classList.toggle("hidden");
  });
  document.addEventListener("click", (e) => {
    const area = document.getElementById("accountArea");
    if (!area.contains(e.target)) document.getElementById("accountMenu").classList.add("hidden");
  });
  bindNavLinks();
  bindSearch();
  await loadCategories();
  consumeOAuthTokenFromUrl();
  await loadMe();
  window.addEventListener("hashchange", Router.render);
  Router.render();
});
