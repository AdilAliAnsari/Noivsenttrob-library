// ============================================================
// Noivsenttrob Library — SPA Javascript Controller
// ============================================================

const STATE = {
  user: null, // Logged in user profile
  mode: "portal", // "portal" | "storefront" | "admin"
  adminTab: "admin-books", // "admin-books" | "admin-members" | "admin-loans" | "admin-reports" | "admin-sql"
  books: [],
  members: [],
  loans: [],
  genres: ["All"]
};

// Toast notification helper
function showToast(message, type = "success") {
  const container = document.getElementById("toasts");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  
  // Auto-remove
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px) scale(0.95)";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// Generate realistic dynamic vintage book cover canvas
function generateCoverUrl(title, author) {
  const canvas = document.createElement("canvas");
  canvas.width = 180;
  canvas.height = 240;
  const ctx = canvas.getContext("2d");
  
  const colors = [
    ["#4A2E2B", "#321E1C"], // Deep Crimson
    ["#1C3345", "#101F2B"], // Deep Ocean Navy
    ["#193A24", "#0E2416"], // Dark Forest Green
    ["#4A3728", "#2E2117"], // Antique Brown Leather
    ["#33254A", "#1F162E"], // Velvet Purple
  ];
  const hash = title.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const colorPair = colors[hash % colors.length];
  
  // Draw base cover gradient
  const grad = ctx.createLinearGradient(0, 0, 180, 240);
  grad.addColorStop(0, colorPair[0]);
  grad.addColorStop(1, colorPair[1]);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 180, 240);
  
  // Spine shading
  ctx.fillStyle = "rgba(0,0,0,0.3)";
  ctx.fillRect(0, 0, 14, 240);
  ctx.fillStyle = "rgba(255,255,255,0.06)";
  ctx.fillRect(14, 0, 2, 240);
  
  // Gold accent lines (Spine detail)
  ctx.fillStyle = "#C9A24B";
  ctx.fillRect(0, 30, 14, 3);
  ctx.fillRect(0, 210, 14, 3);
  
  // Outer gold frame border
  ctx.strokeStyle = "rgba(201,162,75,0.35)";
  ctx.lineWidth = 2;
  ctx.strokeRect(22, 18, 140, 204);
  ctx.strokeRect(26, 22, 132, 196);
  
  // Gilt logo/crest
  ctx.fillStyle = "#C9A24B";
  ctx.font = "14px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("⚜", 90, 52);
  
  // Book title (wrap text)
  ctx.fillStyle = "#EDE6D6";
  ctx.font = "italic bold 12.5px 'Fraunces', serif";
  
  const words = title.split(" ");
  let line = "";
  let y = 80;
  for (let n = 0; n < words.length; n++) {
    let testLine = line + words[n] + " ";
    let metrics = ctx.measureText(testLine);
    if (metrics.width > 105 && n > 0) {
      ctx.fillText(line.trim(), 90, y);
      line = words[n] + " ";
      y += 16;
    } else {
      line = testLine;
    }
  }
  ctx.fillText(line.trim(), 90, y);
  
  // Author
  ctx.fillStyle = "#C9A24B";
  ctx.font = "500 9.5px 'Inter', sans-serif";
  ctx.fillText(author.toUpperCase(), 90, 194);
  
  return canvas.toDataURL();
}

// REST Client Helper
async function request(url, options = {}) {
  try {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    // Add Clerk token if available
    if (window.Clerk && window.Clerk.user) {
      const token = await window.Clerk.session?.getToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }

    const res = await fetch(url, {
      ...options,
      headers
    });
    
    if (res.status === 401) {
      STATE.user = null;
      updateAuthUI();
      return null;
    }
    
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.message || `API Error (${res.status})`);
    }
    
    // 204 No Content
    if (res.status === 204) return true;
    return await res.json();
  } catch (e) {
    showToast(e.message, "error");
    throw e;
  }
}

// Clerk initialization helper
async function initClerk() {
  const clerkConfigured = window.__CLERK_CONFIG__?.configured;
  if (!clerkConfigured || !window.Clerk) {
    console.info("Clerk is not configured; skipping initialization.");
    return;
  }
  
  try {
    await window.Clerk.load();
    console.log("Clerk initialized");
    
    // Render sign-in component in modal if needed
    if (document.getElementById("clerk-sign-in")) {
      window.Clerk.mountSignIn(document.getElementById("clerk-sign-in"));
    }
  } catch (e) {
    console.warn("Clerk initialization failed", e);
  }
}

// Check session
async function checkAuthSession() {
  try {
    // First check if Clerk user exists
    if (window.Clerk && window.Clerk.user) {
      const me = await request("/auth/me");
      if (me) {
        STATE.user = me;
      }
    } else {
      // Fallback to session auth
      const me = await request("/auth/me");
      if (me) {
        STATE.user = me;
      }
    }
  } catch (e) {
    STATE.user = null;
  }
  updateAuthUI();
}

// Update authentication states
function updateAuthUI() {
  const portalUserStatus = document.getElementById("portal-user-status");
  const portalLoginBtn = document.getElementById("portal-login-btn");
  
  const userTrigger = document.getElementById("user-profile-menu-trigger");
  const userName = document.getElementById("user-name");
  const userRole = document.getElementById("user-role");
  const userAvatar = document.getElementById("user-avatar");
  
  const dropdownName = document.getElementById("dropdown-full-name");
  const dropdownEmail = document.getElementById("dropdown-email");
  
  const checkoutZoneMember = document.getElementById("detail-member-borrow-view");
  const checkoutZoneGuest = document.getElementById("detail-guest-borrow-view");
  const borrowerNameDisplay = document.getElementById("borrower-name-display");
  
  const menuLoansLink = document.getElementById("menu-btn-profile-loans");
  
  if (STATE.user) {
    // Session is alive
    const fName = STATE.user.name.split(" ")[0];
    portalUserStatus.innerHTML = `Signed in as <strong style="color:var(--gold-bright);">${STATE.user.name}</strong> (${STATE.user.role})`;
    portalLoginBtn.textContent = "Switch Account";
    
    userName.textContent = fName;
    userRole.textContent = STATE.user.role;
    userAvatar.src = STATE.user.avatar_url || `https://api.dicebear.com/7.x/pixel-art/svg?seed=${STATE.user.name}`;
    
    dropdownName.textContent = STATE.user.name;
    dropdownEmail.textContent = STATE.user.email;
    menuLoansLink.classList.remove("hidden");
    
    // Details checkout block
    if (STATE.user.member_id) {
      checkoutZoneMember.classList.remove("hidden");
      checkoutZoneGuest.classList.add("hidden");
      borrowerNameDisplay.textContent = STATE.user.name;
    } else {
      // Logged in as Admin but doesn't have a member_id
      checkoutZoneMember.classList.add("hidden");
      checkoutZoneGuest.classList.remove("hidden");
    }
  } else {
    // Visitor status
    portalUserStatus.textContent = "Not signed in.";
    portalLoginBtn.textContent = "Sign In / Setup Account";
    
    userName.textContent = "Guest";
    userRole.textContent = "Visitor";
    userAvatar.src = "https://api.dicebear.com/7.x/pixel-art/svg?seed=Guest";
    
    dropdownName.textContent = "Guest Visitor";
    dropdownEmail.textContent = "visitor@library.local";
    menuLoansLink.classList.add("hidden");
    
    checkoutZoneMember.classList.add("hidden");
    checkoutZoneGuest.classList.remove("hidden");
  }
}

// Mode & Tab Navigation
function setMode(mode) {
  STATE.mode = mode;
  const portal = document.getElementById("portal-view");
  const app = document.getElementById("app-view");
  const storefront = document.getElementById("view-storefront");
  const admin = document.getElementById("view-admin");
  const toggleBtn = document.getElementById("btn-toggle-app-mode");
  
  if (mode === "portal") {
    portal.classList.remove("hidden");
    app.classList.add("hidden");
    return;
  }
  
  portal.classList.add("hidden");
  app.classList.remove("hidden");
  
  if (mode === "storefront") {
    storefront.classList.remove("hidden");
    admin.classList.add("hidden");
    document.getElementById("app-main-heading").textContent = "Book Storefront";
    document.getElementById("app-sub-heading").textContent = "Noivsenttrob Repositories";
    toggleBtn.textContent = "Switch to Admin Desk";
    
    syncStorefront();
  } else if (mode === "admin") {
    storefront.classList.add("hidden");
    admin.classList.remove("hidden");
    document.getElementById("app-main-heading").textContent = "Library Admin Desk";
    document.getElementById("app-sub-heading").textContent = "Operations Center";
    toggleBtn.textContent = "Switch to Storefront";
    
    // Switch to active tab
    setAdminTab(STATE.adminTab);
  }
}

function setAdminTab(tabId) {
  STATE.adminTab = tabId;
  // Manage CSS classes on tab buttons
  document.querySelectorAll(".shelf-nav .spine").forEach(btn => {
    if (btn.dataset.tab === tabId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
  
  // Manage CSS classes on tab panels
  document.querySelectorAll(".admin-tab-content").forEach(panel => {
    if (panel.id === `tab-${tabId}`) {
      panel.classList.remove("hidden");
    } else {
      panel.classList.add("hidden");
    }
  });
  
  // Fetch respective data
  if (tabId === "admin-books") syncAdminBooks();
  else if (tabId === "admin-members") syncAdminMembers();
  else if (tabId === "admin-loans") syncAdminLoans();
  else if (tabId === "admin-reports") syncAdminReports();
}

// ============================================================
// Data Operations & Renderers
// ============================================================

// STOREFRONT VIEW
async function syncStorefront() {
  const grid = document.getElementById("storefront-book-grid");
  const filter = document.getElementById("storefront-genre-filter");
  const query = document.getElementById("storefront-search").value;
  const genre = filter.value;
  const availableOnly = document.getElementById("storefront-available-only").checked;
  
  grid.innerHTML = `<div class="empty"><span class="empty-glyph">⏳</span>Loading catalog...</div>`;
  
  try {
    const qs = new URLSearchParams();
    if (query) qs.append("q", query);
    if (genre && genre !== "All") qs.append("genre", genre);
    if (availableOnly) qs.append("available_only", "true");
    
    const result = await request(`/api/books?${qs.toString()}`);
    if (!result) return;
    
    STATE.books = result.items;
    
    // Populate categories filter if it only contains All
    if (STATE.genres.length <= 1) {
      const genres = new Set(["All"]);
      STATE.books.forEach(b => { if (b.genre) genres.add(b.genre); });
      STATE.genres = Array.from(genres);
      filter.innerHTML = STATE.genres.map(g => `<option value="${g}">${g}</option>`).join("");
      filter.value = genre; // Restore selected
    }
    
    if (STATE.books.length === 0) {
      grid.innerHTML = `<div class="empty"><span class="empty-glyph">🔎</span>No books found matching this filter.</div>`;
      return;
    }
    
    grid.innerHTML = STATE.books.map(book => {
      const available = book.copies - book.copies_issued;
      const isAvailable = available > 0;
      const cover = generateCoverUrl(book.title, book.author);
      
      return `
        <div class="book-card" onclick="openBookDetail('${book.isbn}')">
          <div class="book-cover">
            <img src="${cover}" alt="${book.title}" style="width:100%; height:100%; object-fit:cover;">
          </div>
          <div class="book-info">
            <span class="book-tag">${book.genre || 'General'}</span>
            <div class="book-title" title="${book.title}">${book.title}</div>
            <div class="book-author">${book.author}</div>
          </div>
          <div class="book-footer">
            <span class="badge ${isAvailable ? 'available' : 'issued'}">
              ${isAvailable ? 'In Stock' : 'Checked Out'}
            </span>
            <span class="mono" style="font-size:11px; color:var(--parchment-dim);">${available}/${book.copies} Avail</span>
          </div>
        </div>
      `;
    }).join("");
  } catch (e) {
    grid.innerHTML = `<div class="empty"><span class="empty-glyph">❌</span>Failed to load books catalog.</div>`;
  }
}

// ADMIN BOOKS VIEW
async function syncAdminBooks() {
  const tbody = document.querySelector("#admin-books-table tbody");
  const query = document.getElementById("admin-books-search").value;
  
  tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">Loading inventory...</td></tr>`;
  
  try {
    const qs = new URLSearchParams();
    if (query) qs.append("q", query);
    
    const result = await request(`/api/books?${qs.toString()}`);
    if (!result) return;
    
    if (result.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">No books found in inventory.</td></tr>`;
      return;
    }
    
    tbody.innerHTML = result.items.map(book => {
      const avail = book.copies - book.copies_issued;
      return `
        <tr>
          <td class="mono">${book.isbn}</td>
          <td><strong>${book.title}</strong></td>
          <td>${book.author}</td>
          <td>${book.genre || 'General'}</td>
          <td class="mono">${book.copies}</td>
          <td class="mono">${book.copies_issued}</td>
          <td class="mono">${avail}</td>
          <td>
            <button class="btn small" onclick="openEditBookModal('${book.isbn}', ${book.copies})">Edit</button>
            <button class="btn small danger" onclick="deleteBookAction('${book.isbn}')">Delete</button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--danger-bright);">Failed to load inventory.</td></tr>`;
  }
}

// ADMIN MEMBERS VIEW
async function syncAdminMembers() {
  const tbody = document.querySelector("#admin-members-table tbody");
  const query = document.getElementById("admin-members-search").value;
  
  tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">Loading members list...</td></tr>`;
  
  try {
    const qs = new URLSearchParams();
    if (query) qs.append("q", query);
    
    const result = await request(`/api/members?${qs.toString()}`);
    if (!result) return;
    
    if (result.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">No library members registered.</td></tr>`;
      return;
    }
    
    tbody.innerHTML = result.items.map(m => {
      const details = m.type === "Student" ? `Roll: ${m.roll_no || 'N/A'}` : m.type === "Faculty" ? `Dept: ${m.department || 'N/A'}` : "General";
      return `
        <tr>
          <td class="mono"><strong>${m.member_id}</strong></td>
          <td>${m.name}</td>
          <td>${m.email}</td>
          <td class="mono">${m.phone}</td>
          <td><span class="badge ${m.type === 'Faculty' ? 'available' : 'issued'}" style="background:none; border-color:var(--line);">${m.type}</span></td>
          <td class="mono" style="font-size:11px;">${details}</td>
          <td class="mono">${m.books_held}</td>
          <td>
            <button class="btn small danger" onclick="deleteMemberAction('${m.member_id}')">Deregister</button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--danger-bright);">Failed to load members list.</td></tr>`;
  }
}

// ADMIN CIRCULATION VIEW
async function syncAdminLoans() {
  const tbody = document.querySelector("#admin-loans-table tbody");
  tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">Loading active circulation board...</td></tr>`;
  
  try {
    const result = await request("/api/circulation/active");
    if (!result) return;
    
    if (result.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;">No active books on loan currently.</td></tr>`;
      return;
    }
    
    tbody.innerHTML = result.items.map(l => {
      const fineText = l.fine_amount > 0 ? `Rs.${l.fine_amount.toFixed(2)}` : "None";
      const isOverdue = new Date(l.due_date) < new Date();
      return `
        <tr>
          <td class="mono">${l.id}</td>
          <td><strong>${l.title}</strong></td>
          <td class="mono">${l.isbn}</td>
          <td>${l.member_name}</td>
          <td class="mono">${l.member_id}</td>
          <td class="mono">${l.issued_date}</td>
          <td class="mono ${isOverdue ? 'danger' : ''}">${l.due_date} ${isOverdue ? '⚠️' : ''}</td>
          <td class="mono" style="color:${l.fine_amount > 0 ? 'var(--danger-bright)' : 'inherit'};">${fineText}</td>
        </tr>
      `;
    }).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--danger-bright);">Failed to load active loans.</td></tr>`;
  }
}

// ADMIN REPORTS VIEW
async function syncAdminReports() {
  try {
    const r = await request("/api/reports/dashboard");
    if (!r) return;
    
    document.getElementById("stat-titles").textContent = r.titles;
    document.getElementById("stat-copies-available").textContent = r.copies_available;
    document.getElementById("stat-active-loans").textContent = r.active_loans;
    document.getElementById("stat-overdue-loans").textContent = r.overdue_loans;
    
    // Render top borrowed books
    const topBooksContainer = document.getElementById("report-top-books");
    if (r.top_books.length === 0) {
      topBooksContainer.innerHTML = `<div class="empty">No issue records yet to analyze.</div>`;
    } else {
      topBooksContainer.innerHTML = r.top_books.map((b, idx) => `
        <div class="list-item-row">
          <span>${idx + 1}. <strong>${b.title}</strong></span>
          <span class="mono">${b.times_issued} issues</span>
        </div>
      `).join("");
    }
    
    // Render genre breakdown
    const genreContainer = document.getElementById("report-genres");
    if (r.by_genre.length === 0) {
      genreContainer.innerHTML = `<div class="empty">No categories to display.</div>`;
    } else {
      // Find max to scale bar sizes
      const max = Math.max(...r.by_genre.map(g => g.n));
      genreContainer.innerHTML = r.by_genre.map(g => {
        const percent = max > 0 ? (g.n / max) * 100 : 0;
        return `
          <div class="genre-chart-row">
            <div class="genre-chart-lbl">
              <span>${g.genre}</span>
              <span class="mono">${g.n} books</span>
            </div>
            <div class="genre-chart-bar-bg">
              <div class="genre-chart-bar-fill" style="width:${percent}%"></div>
            </div>
          </div>
        `;
      }).join("");
    }
  } catch (e) {
    showToast("Failed to compile dashboard reports", "error");
  }
}

// MY PERSONAL LOANS VIEW (MODAL)
async function openMyLoansModal() {
  const container = document.getElementById("my-loans-list");
  container.innerHTML = `<div class="empty">Loading your loans...</div>`;
  document.getElementById("modal-my-loans").classList.remove("hidden");
  
  if (!STATE.user || !STATE.user.member_id) {
    container.innerHTML = `<div class="empty">You must be logged in as a library member.</div>`;
    return;
  }
  
  try {
    // We can fetch user active loans. Since there's no endpoint /api/my-loans directly in this backend, 
    // we can filter loans in /api/circulation/active for this member_id.
    const result = await request("/api/circulation/active");
    if (!result) return;
    
    const myLoans = result.items.filter(l => l.member_id === STATE.user.member_id);
    
    if (myLoans.length === 0) {
      container.innerHTML = `
        <div class="empty">
          <span class="empty-glyph">📚</span>
          You have no books checked out currently.
        </div>
      `;
      return;
    }
    
    container.innerHTML = myLoans.map(l => {
      const isOverdue = new Date(l.due_date) < new Date();
      return `
        <div class="loan-item-box">
          <span class="loan-item-cover-icon">📕</span>
          <div class="loan-item-details">
            <span class="loan-item-title">${l.title}</span>
            <span class="loan-item-dates">Issued: ${l.issued_date} &middot; Due: <strong class="${isOverdue ? 'danger' : ''}">${l.due_date}</strong></span>
          </div>
          <button class="btn btn-outline small" onclick="returnBookAction('${l.isbn}', '${l.member_id}')">Return Book</button>
        </div>
      `;
    }).join("");
  } catch (e) {
    container.innerHTML = `<div class="empty">Failed to fetch borrowed books.</div>`;
  }
}

// ============================================================
// Actions & API Triggers
// ============================================================

// Borrow Book
async function borrowBookAction(isbn, memberId) {
  try {
    const payload = { isbn, member_id: memberId };
    const res = await request("/api/circulation/issue", {
      method: "POST",
      body: payload
    });
    if (res) {
      showToast(res.message, "success");
      document.getElementById("modal-book-detail").classList.add("hidden");
      syncStorefront();
    }
  } catch (e) {}
}

// Return Book
async function returnBookAction(isbn, memberId) {
  try {
    const payload = { isbn, member_id: memberId };
    const res = await request("/api/circulation/return", {
      method: "POST",
      body: payload
    });
    if (res) {
      showToast(res.message, res.fine_amount > 0 ? "error" : "success");
      
      // Refresh views
      if (document.getElementById("modal-my-loans").classList.contains("hidden") === false) {
        openMyLoansModal();
      }
      syncStorefront();
      syncAdminLoans();
    }
  } catch (e) {}
}

// Add Book Action
async function handleAddBook(e) {
  e.preventDefault();
  const isbn = document.getElementById("book-isbn").value;
  const title = document.getElementById("book-title").value;
  const author = document.getElementById("book-author").value;
  const genre = document.getElementById("book-genre").value;
  const copies = parseInt(document.getElementById("book-copies").value);
  
  try {
    const isEdit = document.getElementById("modal-add-book").dataset.mode === "edit";
    if (isEdit) {
      const payload = { title, author, genre, copies };
      await request(`/api/books/${isbn}`, {
        method: "PUT",
        body: payload
      });
      showToast("Book catalog updated successfully!");
    } else {
      const payload = { isbn, title, author, genre, copies };
      await request("/api/books", {
        method: "POST",
        body: payload
      });
      showToast("New book registered in inventory!");
    }
    
    document.getElementById("modal-add-book").classList.add("hidden");
    document.getElementById("add-book-form").reset();
    syncAdminBooks();
  } catch (e) {}
}

// Delete Book Action
async function deleteBookAction(isbn) {
  if (!confirm(`Are you sure you want to remove book with ISBN ${isbn}?`)) return;
  try {
    const ok = await request(`/api/books/${isbn}`, { method: "DELETE" });
    if (ok) {
      showToast("Book successfully removed from library catalog.");
      syncAdminBooks();
    }
  } catch (e) {}
}

// Open Edit Book Modal
function openEditBookModal(isbn, currentCopies) {
  const m = document.getElementById("modal-add-book");
  m.dataset.mode = "edit";
  document.getElementById("book-modal-title").textContent = "Edit Book Inventory";
  
  // Find book details in STATE
  const book = STATE.books.find(b => b.isbn === isbn);
  if (book) {
    document.getElementById("book-isbn").value = book.isbn;
    document.getElementById("book-isbn").disabled = true; // Cannot edit primary key
    document.getElementById("book-title").value = book.title;
    document.getElementById("book-author").value = book.author;
    document.getElementById("book-genre").value = book.genre || "";
    document.getElementById("book-copies").value = book.copies;
    m.classList.remove("hidden");
  }
}

// Add Member Action
async function handleAddMember(e) {
  e.preventDefault();
  const member_id = document.getElementById("member-id-input").value;
  const name = document.getElementById("member-name-input").value;
  const email = document.getElementById("member-email-input").value;
  const phone = document.getElementById("member-phone-input").value;
  const type = document.getElementById("member-type-input").value;
  const roll_no = document.getElementById("member-roll-input").value || null;
  const department = document.getElementById("member-dept-input").value || null;
  
  try {
    const payload = { member_id, name, email, phone, type, roll_no, department };
    const res = await request("/api/members", {
      method: "POST",
      body: payload
    });
    if (res) {
      showToast(`Member ${name} registered successfully!`);
      document.getElementById("modal-add-member").classList.add("hidden");
      document.getElementById("add-member-form").reset();
      syncAdminMembers();
    }
  } catch (e) {}
}

// Delete Member Action
async function deleteMemberAction(memberId) {
  if (!confirm(`Are you sure you want to deregister member ID ${memberId}?`)) return;
  try {
    const ok = await request(`/api/members/${memberId}`, { method: "DELETE" });
    if (ok) {
      showToast("Member successfully deregistered.");
      syncAdminMembers();
    }
  } catch (e) {}
}

// SQL Console Executer
async function handleSqlExecute() {
  const query = document.getElementById("sql-query-input").value.trim();
  const outPanel = document.getElementById("sql-output-panel");
  const outMsg = document.getElementById("sql-output-message");
  const wrapper = document.getElementById("sql-output-table-wrapper");
  const thead = document.getElementById("sql-output-cols");
  const tbody = document.getElementById("sql-output-rows");
  
  if (!query) {
    showToast("Please enter a SQL query to execute", "error");
    return;
  }
  
  outPanel.classList.remove("hidden");
  outMsg.className = "sql-output-message";
  outMsg.textContent = "Executing query against SQLite database...";
  wrapper.classList.add("hidden");
  thead.innerHTML = "";
  tbody.innerHTML = "";
  
  try {
    const res = await request("/api/reports/sql", {
      method: "POST",
      body: { query }
    });
    
    if (!res) return;
    
    if (res.success) {
      outMsg.className = "sql-output-message success";
      if (res.message) {
        outMsg.textContent = res.message;
      } else {
        outMsg.textContent = `Query executed successfully. Returned ${res.row_count} row(s).`;
      }
      
      if (res.columns && res.columns.length > 0) {
        wrapper.classList.remove("hidden");
        thead.innerHTML = res.columns.map(col => `<th>${col}</th>`).join("");
        
        tbody.innerHTML = res.rows.map(row => `
          <tr>
            ${row.map(val => `<td>${val !== null ? val : '<em style="color:var(--parchment-dim)">NULL</em>'}</td>`).join("")}
          </tr>
        `).join("");
      }
    } else {
      outMsg.className = "sql-output-message error";
      outMsg.textContent = `SQLite Error: ${res.error}`;
    }
  } catch (e) {
    outMsg.className = "sql-output-message error";
    outMsg.textContent = `Query failed to post: ${e.message}`;
  }
}

// Open Book details modal
function openBookDetail(isbn) {
  const book = STATE.books.find(b => b.isbn === isbn);
  if (!book) return;
  
  document.getElementById("detail-genre").textContent = book.genre || 'General';
  document.getElementById("detail-title").textContent = book.title;
  document.getElementById("detail-author").textContent = `By ${book.author}`;
  document.getElementById("detail-isbn").textContent = `ISBN: ${book.isbn}`;
  
  // Custom generated canvas cover
  const coverUrl = generateCoverUrl(book.title, book.author);
  const coverPlaceholder = document.getElementById("detail-cover-placeholder");
  coverPlaceholder.innerHTML = `<img src="${coverUrl}" alt="${book.title}" style="width:100%; height:100%; object-fit:cover;">`;
  
  // Set summary description
  document.getElementById("detail-description").textContent = 
    `${book.title} is a brilliant read compiled by ${book.author} listed in the ${book.genre || 'General'} category. Total of ${book.copies} copies maintained in repository inventory.`;
  
  const available = book.copies - book.copies_issued;
  const isAvailable = available > 0;
  const badge = document.getElementById("detail-status-badge");
  
  badge.className = `badge ${isAvailable ? 'available' : 'issued'}`;
  badge.textContent = isAvailable ? 'In Stock' : 'Checked Out';
  document.getElementById("detail-copies-count").textContent = `${available} of ${book.copies} copies currently available`;
  
  const actionBtn = document.getElementById("btn-borrow-book-action");
  if (isAvailable) {
    actionBtn.removeAttribute("disabled");
    actionBtn.textContent = "Borrow Book";
    actionBtn.onclick = () => borrowBookAction(book.isbn, STATE.user.member_id);
  } else {
    actionBtn.setAttribute("disabled", "true");
    actionBtn.textContent = "Unavailable";
  }
  
  document.getElementById("modal-book-detail").classList.remove("hidden");
}

// ============================================================
// Initialization & Listeners Setup
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  
  // Check theme preference
  const currentTheme = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", currentTheme);
  document.getElementById("themeToggle").textContent = currentTheme === "dark" ? "☀️" : "🌙";
  
  // Theme Toggle Button
  document.getElementById("themeToggle").addEventListener("click", () => {
    const active = document.documentElement.getAttribute("data-theme");
    const target = active === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", target);
    localStorage.setItem("theme", target);
    document.getElementById("themeToggle").textContent = target === "dark" ? "☀️" : "🌙";
  });
  
  // Portal Navigation
  document.getElementById("btn-goto-storefront").addEventListener("click", () => setMode("storefront"));
  document.getElementById("btn-goto-admin").addEventListener("click", () => setMode("admin"));
  document.getElementById("btn-back-to-portal").addEventListener("click", () => setMode("portal"));
  
  // App Switcher direct button in topbar
  document.getElementById("btn-toggle-app-mode").addEventListener("click", () => {
    const next = STATE.mode === "storefront" ? "admin" : "storefront";
    setMode(next);
  });
  
  // Sidebar spines (admin sub-tabs)
  document.querySelectorAll(".shelf-nav .spine").forEach(btn => {
    btn.addEventListener("click", () => setAdminTab(btn.dataset.tab));
  });
  
  // Search inputs debouncers/listeners
  document.getElementById("storefront-search").addEventListener("input", () => syncStorefront());
  document.getElementById("storefront-genre-filter").addEventListener("change", () => syncStorefront());
  document.getElementById("storefront-available-only").addEventListener("change", () => syncStorefront());
  
  document.getElementById("admin-books-search").addEventListener("input", () => syncAdminBooks());
  document.getElementById("admin-members-search").addEventListener("input", () => syncAdminMembers());
  
  // User Profile Trigger toggle menu
  document.getElementById("user-profile-menu-trigger").addEventListener("click", (e) => {
    e.stopPropagation();
    document.getElementById("profile-dropdown-menu").classList.toggle("hidden");
  });
  
  document.addEventListener("click", () => {
    document.getElementById("profile-dropdown-menu").classList.add("hidden");
  });
  
  // Modal opening handlers
  document.getElementById("btn-add-book-modal").addEventListener("click", () => {
    const m = document.getElementById("modal-add-book");
    m.dataset.mode = "add";
    document.getElementById("book-modal-title").textContent = "Add New Book";
    document.getElementById("book-isbn").disabled = false;
    document.getElementById("add-book-form").reset();
    m.classList.remove("hidden");
  });
  
  document.getElementById("btn-close-book-modal").addEventListener("click", () => {
    document.getElementById("modal-add-book").classList.add("hidden");
  });
  
  document.getElementById("btn-add-member-modal").addEventListener("click", () => {
    document.getElementById("add-member-form").reset();
    document.getElementById("member-extra-fields").classList.add("hidden");
    document.getElementById("modal-add-member").classList.remove("hidden");
  });
  
  document.getElementById("btn-close-member-modal").addEventListener("click", () => {
    document.getElementById("modal-add-member").classList.add("hidden");
  });
  
  document.getElementById("btn-close-book-detail").addEventListener("click", () => {
    document.getElementById("modal-book-detail").classList.add("hidden");
  });
  
  // My Loans triggers
  document.getElementById("menu-btn-profile-loans").addEventListener("click", (e) => {
    e.preventDefault();
    openMyLoansModal();
  });
  
  document.getElementById("btn-close-my-loans-modal").addEventListener("click", () => {
    document.getElementById("modal-my-loans").classList.add("hidden");
  });
  
  // Auth login triggers
  document.getElementById("portal-login-btn").addEventListener("click", () => {
    document.getElementById("modal-auth").classList.remove("hidden");
  });
  
  document.getElementById("btn-close-auth-modal").addEventListener("click", () => {
    document.getElementById("modal-auth").classList.add("hidden");
  });
  
  document.getElementById("btn-login-to-borrow").addEventListener("click", () => {
    document.getElementById("modal-book-detail").classList.add("hidden");
    document.getElementById("modal-auth").classList.remove("hidden");
  });
  
  // Tab toggle in auth modal
  document.getElementById("auth-tab-mock").addEventListener("click", () => {
    document.getElementById("auth-tab-mock").classList.add("active");
    document.getElementById("auth-tab-oauth").classList.remove("active");
    document.getElementById("auth-content-mock").classList.remove("hidden");
    document.getElementById("auth-content-oauth").classList.add("hidden");
  });
  
  document.getElementById("auth-tab-oauth").addEventListener("click", () => {
    document.getElementById("auth-tab-oauth").classList.add("active");
    document.getElementById("auth-tab-mock").classList.remove("active");
    document.getElementById("auth-tab-clerk").classList.remove("active");
    document.getElementById("auth-content-oauth").classList.remove("hidden");
    document.getElementById("auth-content-mock").classList.add("hidden");
    document.getElementById("auth-content-clerk").classList.add("hidden");
  });

  document.getElementById("auth-tab-clerk").addEventListener("click", () => {
    document.getElementById("auth-tab-clerk").classList.add("active");
    document.getElementById("auth-tab-mock").classList.remove("active");
    document.getElementById("auth-tab-oauth").classList.remove("active");
    document.getElementById("auth-content-clerk").classList.remove("hidden");
    document.getElementById("auth-content-mock").classList.add("hidden");
    document.getElementById("auth-content-oauth").classList.add("hidden");
  });
  
  // Conditional profile registration dropdown in mock auth login
  document.getElementById("mock-member-id").addEventListener("change", (e) => {
    const val = e.target.value;
    const extra = document.getElementById("mock-extra-fields");
    const roll = document.getElementById("mock-roll-field");
    const dept = document.getElementById("mock-dept-field");
    
    if (val === "NEW_STUDENT" || val === "NEW_FACULTY") {
      extra.classList.remove("hidden");
      if (val === "NEW_STUDENT") {
        roll.classList.remove("hidden");
        dept.classList.add("hidden");
      } else {
        roll.classList.add("hidden");
        dept.classList.remove("hidden");
      }
    } else {
      extra.classList.add("hidden");
    }
  });
  
  // Conditional fields in manual Register Member modal
  document.getElementById("member-type-input").addEventListener("change", (e) => {
    const val = e.target.value;
    const extra = document.getElementById("member-extra-fields");
    const roll = document.getElementById("reg-roll-field");
    const dept = document.getElementById("reg-dept-field");
    
    if (val === "Student" || val === "Faculty") {
      extra.classList.remove("hidden");
      if (val === "Student") {
        roll.classList.remove("hidden");
        dept.classList.add("hidden");
        document.getElementById("member-roll-input").setAttribute("required", "true");
        document.getElementById("member-dept-input").removeAttribute("required");
      } else {
        roll.classList.add("hidden");
        dept.classList.remove("hidden");
        document.getElementById("member-dept-input").setAttribute("required", "true");
        document.getElementById("member-roll-input").removeAttribute("required");
      }
    } else {
      extra.classList.add("hidden");
      document.getElementById("member-roll-input").removeAttribute("required");
      document.getElementById("member-dept-input").removeAttribute("required");
    }
  });
  
  // Submit handlers
  document.getElementById("add-book-form").addEventListener("submit", handleAddBook);
  document.getElementById("add-member-form").addEventListener("submit", handleAddMember);
  
  // Manual Circulation triggers
  document.getElementById("admin-issue-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const isbn = document.getElementById("issue-isbn").value.trim();
    const mId = document.getElementById("issue-member-id").value.trim();
    await borrowBookAction(isbn, mId);
    e.target.reset();
    syncAdminLoans();
  });
  
  document.getElementById("admin-return-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const isbn = document.getElementById("return-isbn").value.trim();
    const mId = document.getElementById("return-member-id").value.trim();
    await returnBookAction(isbn, mId);
    e.target.reset();
    syncAdminLoans();
  });
  
  // SQL console inputs
  document.getElementById("btn-execute-sql").addEventListener("click", handleSqlExecute);
  document.getElementById("btn-clear-sql").addEventListener("click", () => {
    document.getElementById("sql-query-input").value = "";
    document.getElementById("sql-output-panel").classList.add("hidden");
  });
  
  document.querySelectorAll(".sql-tpl-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById("sql-query-input").value = btn.dataset.sql;
    });
  });
  
  // Mock login form submission
  document.getElementById("mock-login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const mockId = document.getElementById("mock-member-id").value;
    
    let payload = {};
    if (mockId === "M001") {
      payload = { member_id: "M001", role: "student" };
    } else if (mockId === "M002") {
      payload = { member_id: "M002", role: "faculty" };
    } else if (mockId === "ADMIN_BYPASS") {
      payload = { member_id: "ADMIN", role: "admin", name: "Administrator" };
    } else {
      // NEW_STUDENT or NEW_FACULTY
      const type = mockId === "NEW_STUDENT" ? "Student" : "Faculty";
      const name = document.getElementById("mock-new-name").value.trim();
      const email = document.getElementById("mock-new-email").value.trim();
      const phone = document.getElementById("mock-new-phone").value.trim();
      const roll = document.getElementById("mock-new-roll").value.trim();
      const dept = document.getElementById("mock-new-dept").value.trim();
      
      if (!name || !email || !phone) {
        showToast("Please fill in name, email, and phone details", "error");
        return;
      }
      
      // Auto-generate random member ID for the mock
      const randId = "M" + Math.floor(100 + Math.random() * 900);
      
      // Register in backend first
      try {
        const regPayload = {
          member_id: randId,
          name,
          email,
          phone,
          type,
          roll_no: type === "Student" ? roll : null,
          department: type === "Faculty" ? dept : null
        };
        await request("/api/members", {
          method: "POST",
          body: regPayload
        });
        payload = { member_id: randId, role: type.toLowerCase() };
      } catch (err) {
        return; // error shown by request helper
      }
    }
    
    try {
      const user = await request("/auth/login/mock", {
        method: "POST",
        body: payload
      });
      if (user) {
        STATE.user = user;
        updateAuthUI();
        document.getElementById("modal-auth").classList.add("hidden");
        showToast(`Signed in successfully as ${user.name}!`);
        
        // Refresh grids
        syncStorefront();
        if (STATE.mode === "admin") {
          setAdminTab(STATE.adminTab);
        }
      }
    } catch (err) {}
  });
  
  // Logout action
  document.getElementById("menu-btn-logout").addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      const res = await request("/auth/logout", { method: "POST" });
      if (res) {
        STATE.user = null;
        updateAuthUI();
        showToast("Logged out successfully.");
        setMode("portal");
      }
    } catch (err) {}
  });
  
  // Check auth session on page load
  initClerk();
  
  // Listen for Clerk auth changes
  if (window.Clerk) {
    window.Clerk.addListener(async ({ user }) => {
      if (user) {
        await checkAuthSession();
        // Close auth modal when signed in
        document.getElementById("modal-auth").classList.add("hidden");
        showToast("Signed in successfully!");
      } else {
        STATE.user = null;
        updateAuthUI();
      }
    });
  }
  
  checkAuthSession();
  
  // Initial draw
  setMode("portal");
});
