/**
 * Random Technical Wiki - Static client-side implementation
 * Fetches Vital Articles and Good Articles via MediaWiki API, parses content, supports text/PDF download.
 */

const VITAL_SOURCES = {
  vital_people: "Wikipedia:Vital_articles/Level/4/People",
  vital_history: "Wikipedia:Vital_articles/Level/4/History",
  vital_geography: "Wikipedia:Vital_articles/Level/4/Geography",
  vital_arts: "Wikipedia:Vital_articles/Level/4/Arts",
  vital_philosophy_religion: "Wikipedia:Vital_articles/Level/4/Philosophy_and_religion",
  vital_everyday_life: "Wikipedia:Vital_articles/Level/4/Everyday_life",
  vital_society_social_sciences: "Wikipedia:Vital_articles/Level/4/Society_and_social_sciences",
  vital_biology_health_sciences: "Wikipedia:Vital_articles/Level/4/Biology_and_health_sciences",
  vital_physical_sciences: "Wikipedia:Vital_articles/Level/4/Physical_sciences",
  vital_technology: "Wikipedia:Vital_articles/Level/4/Technology",
  vital_mathematics: "Wikipedia:Vital_articles/Level/4/Mathematics"
};

const GOOD_SOURCES = {
  "agriculture_food_drink": "Wikipedia:Good_articles/Agriculture,_food_and_drink",
  "art_architecture": "Wikipedia:Good_articles/Art_and_architecture",
  "engineering_technology": "Wikipedia:Good_articles/Engineering_and_technology",
  "geography_places": "Wikipedia:Good_articles/Geography_and_places",
  "history": "Wikipedia:Good_articles/History",
  "language_literature": "Wikipedia:Good_articles/Language_and_literature",
  "mathematics": "Wikipedia:Good_articles/Mathematics",
  "media_drama": "Wikipedia:Good_articles/Media_and_drama",
  "music": "Wikipedia:Good_articles/Music",
  "natural_sciences": "Wikipedia:Good_articles/Natural_sciences",
  "philosophy_religion": "Wikipedia:Good_articles/Philosophy_and_religion",
  "social_sciences_society": "Wikipedia:Good_articles/Social_sciences_and_society",
  "sports_recreation": "Wikipedia:Good_articles/Sports_and_recreation",
  "video_games": "Wikipedia:Good_articles/Video_games",
  "warfare": "Wikipedia:Good_articles/Warfare",
  "all_good": "Wikipedia:Good_articles/all"
};

const CATEGORY_LABELS = {
  vital_people: "People",
  vital_history: "History",
  vital_geography: "Geography",
  vital_arts: "Arts",
  vital_philosophy_religion: "Philosophy and religion",
  vital_everyday_life: "Everyday life",
  vital_society_social_sciences: "Society and social sciences",
  vital_biology_health_sciences: "Biology and health sciences",
  vital_physical_sciences: "Physical sciences",
  vital_technology: "Technology",
  vital_mathematics: "Mathematics",
  agriculture_food_drink: "Agriculture, food and drink",
  art_architecture: "Art and architecture",
  engineering_technology: "Engineering and technology",
  geography_places: "Geography and places",
  history: "History",
  language_literature: "Language and literature",
  mathematics: "Mathematics",
  media_drama: "Media and drama",
  music: "Music",
  natural_sciences: "Natural sciences",
  philosophy_religion: "Philosophy and religion",
  social_sciences_society: "Social sciences and society",
  sports_recreation: "Sports and recreation",
  video_games: "Video games",
  warfare: "Warfare",
  all_good: "All good articles"
};

const API_BASE = "https://en.wikipedia.org/w/api.php";
const HEADERS = {
  "User-Agent": "RandomTechnicalWiki/1.0 (https://github.com; contact via GitHub)",
  "Api-User-Agent": "RandomTechnicalWiki/1.0 (https://github.com)"
};

// Cache: { category: ["/wiki/Title1", "/wiki/Title2", ...] }
const ARTICLES_CACHE = {};

const READ_LOG_KEY = "random_wiki_read_log";

// Auth state (set when backend is available and user is logged in)
let loggedInUser = null;
let readLogCache = null;

const fetchOpts = { credentials: "include" };

async function apiFetch(path, options = {}) {
  const res = await fetch(path, { ...fetchOpts, ...options });
  return res;
}

function getReadLog() {
  if (loggedInUser !== null && readLogCache !== null) {
    return readLogCache;
  }
  try {
    const raw = localStorage.getItem(READ_LOG_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveReadLog(log) {
  if (loggedInUser !== null) {
    readLogCache = [...log];
    apiFetch("/api/read-log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ log })
    }).catch((e) => console.error("Failed to sync read log:", e));
    return;
  }
  try {
    localStorage.setItem(READ_LOG_KEY, JSON.stringify(log));
  } catch (e) {
    console.error("Failed to save read log:", e);
  }
}

function logArticle(url, title, category) {
  const log = getReadLog();
  const categoryLabel = CATEGORY_LABELS[category] || category;
  const existing = log.findIndex((e) => e.url === url);
  const entry = { title, url, category: categoryLabel, date: new Date().toISOString() };
  if (existing >= 0) {
    log[existing] = entry;
  } else {
    log.unshift(entry);
  }
  saveReadLog(log);
  renderReadLog();
}

function removeFromLog(index) {
  const log = getReadLog();
  log.splice(index, 1);
  saveReadLog(log);
  renderReadLog();
}

function renderReadLog() {
  const container = document.getElementById("readLogList");
  if (!container) return;
  const log = getReadLog();
  if (!log.length) {
    container.innerHTML = '<p class="read-log-empty">No articles logged yet.</p>';
    return;
  }
  container.innerHTML = log
    .map(
      (e, i) => `
    <div class="read-log-entry">
      <a href="${escapeHtml(e.url)}" target="_blank">${escapeHtml(e.title)}</a>
      <span class="read-log-meta">${escapeHtml(e.category)} &middot; ${formatLogDate(e.date)}</span>
      <span class="read-log-remove" data-index="${i}">Remove</span>
    </div>`
    )
    .join("");
  container.querySelectorAll(".read-log-remove").forEach((el) => {
    el.addEventListener("click", () => removeFromLog(Number(el.dataset.index)));
  });
}

function formatLogDate(iso) {
  try {
    const d = new Date(iso);
    const dateStr = d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric"
    });
    const hours = d.getHours();
    const minutes = d.getMinutes();
    const ampm = hours >= 12 ? "PM" : "AM";
    const hour12 = hours % 12 || 12;
    const minStr = String(minutes).padStart(2, "0");
    return `${dateStr}, ${hour12}:${minStr} ${ampm}`;
  } catch {
    return iso;
  }
}

function getPageTitleForCategory(category) {
  return VITAL_SOURCES[category] || GOOD_SOURCES[category] || null;
}

/**
 * Fetch all article links from a Wikipedia list page via MediaWiki API.
 */
async function fetchArticleLinks(category) {
  const pageTitle = getPageTitleForCategory(category);
  if (!pageTitle) return [];

  const allLinks = [];
  let plcontinue = null;

  try {
    do {
      let url = `${API_BASE}?action=query&prop=links&titles=${encodeURIComponent(pageTitle)}&plnamespace=0&pllimit=500&format=json&origin=*`;
      if (plcontinue) url += `&plcontinue=${encodeURIComponent(plcontinue)}`;

      const response = await fetch(url, { headers: HEADERS, mode: "cors" });
      if (!response.ok) {
        console.error("Wikipedia API error:", response.status, response.statusText);
        return [];
      }
      const data = await response.json();
      if (data.error) {
        console.error("Wikipedia API error:", data.error);
        return [];
      }

      const pages = data.query?.pages || {};
      const page = Object.values(pages)[0];
      if (page?.missing !== undefined) {
        console.error("Wikipedia page not found:", pageTitle);
        return [];
      }
      const links = page?.links || [];
      for (const link of links) {
        if (link.ns === 0 && !link.title.includes(":")) {
          allLinks.push("/wiki/" + link.title.replace(/ /g, "_"));
        }
      }

      plcontinue = data.continue?.plcontinue || null;
    } while (plcontinue);
  } catch (err) {
    console.error("Fetch error:", err);
    return [];
  }

  return allLinks;
}

/**
 * Get a random article URL for the given category.
 */
async function getRandomArticle(category) {
  if (!getPageTitleForCategory(category)) return null;

  if (ARTICLES_CACHE[category]?.length) {
    const href = ARTICLES_CACHE[category][Math.floor(Math.random() * ARTICLES_CACHE[category].length)];
    return "https://en.wikipedia.org" + href;
  }

  const links = await fetchArticleLinks(category);
  if (!links.length) return null;

  ARTICLES_CACHE[category] = links;
  const href = links[Math.floor(Math.random() * links.length)];
  return "https://en.wikipedia.org" + href;
}

/**
 * Clean reference text (mirror wiki_content._clean_reference_text).
 */
function cleanReferenceText(raw) {
  let text = raw.trim();
  if (text.startsWith("^")) text = text.slice(1).trim();
  while (text) {
    let i = 0;
    while (i < text.length && "abcdefghijklmnopqrstuvwxyz ".includes(text[i])) i++;
    if (i > 0 && (i === text.length || text[i] === ">" || (text.slice(i, i + 1).trim() === "" && text.slice(0, 20).includes(">")))) {
      text = text.slice(i).trim().replace(/^>/, "").trim();
    } else {
      break;
    }
  }
  return text;
}

/**
 * Check if we should stop collecting body at this heading.
 */
function bodyStopsAtHeading(text) {
  const lower = text.trim().toLowerCase();
  return ["see also", "references", "further reading", "external links"].includes(lower);
}

/**
 * Fetch article content via MediaWiki action=parse API.
 * Returns { title, bodyBlocks, references } or null on failure.
 */
async function fetchArticleContent(articleUrl) {
  if (!articleUrl.startsWith("https://en.wikipedia.org/wiki/")) return null;

  const title = articleUrl.split("/wiki/")[1].replace(/_/g, " ");
  const url = `${API_BASE}?action=parse&page=${encodeURIComponent(title)}&prop=text|displaytitle&format=json&origin=*`;

  try {
    const response = await fetch(url, { headers: HEADERS });
    const data = await response.json();
    if (data.error) return null;

    const parse = data.query?.pages?.[Object.keys(data.query.pages)[0]]?.parse;
    if (!parse) return null;

    const html = parse.text["*"];
    const displayTitle = parse.displaytitle || title;

    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const content = doc.querySelector(".mw-parser-output") || doc.body;
    if (!content) return { title: displayTitle, bodyBlocks: [], references: [] };

    // Remove non-content elements
    for (const tag of content.querySelectorAll("script, style, nav, table, figure")) {
      tag.remove();
    }

    const bodyBlocks = [];
    const stopHeadings = new Set(["see also", "references", "further reading", "external links"]);

    for (const el of content.querySelectorAll("h2, h3, p")) {
      const text = el.textContent.replace(/\s+/g, " ").trim();
      if (!text) continue;

      if (el.tagName === "H2" || el.tagName === "H3") {
        if (stopHeadings.has(text.toLowerCase())) break;
        bodyBlocks.push({ type: el.tagName.toLowerCase(), text });
      } else {
        bodyBlocks.push({ type: "p", text });
      }
    }

    const references = [];
    for (const li of content.querySelectorAll('li[id^="cite_note-"]')) {
      const raw = li.textContent.replace(/\s+/g, " ").trim();
      const cleaned = cleanReferenceText(raw);
      if (cleaned) references.push(`[${references.length + 1}] ${cleaned}`);
    }

    return { title: displayTitle, bodyBlocks, references };
  } catch (e) {
    console.error("fetchArticleContent error:", e);
    return null;
  }
}

/**
 * Format plain text (mirror wiki_content.format_plain_text_with_references).
 */
function formatPlainText(title, bodyBlocks, references) {
  const parts = [];
  for (const b of bodyBlocks) {
    if (b.type === "h2" || b.type === "h3") parts.push("\n\n" + b.text + "\n");
    else parts.push(b.text);
  }
  const body = parts.join("\n").trim();
  const sections = [title, "=".repeat(title.length), "", body];
  if (references.length) sections.push("", "References", "", references.join("\n\n"));
  return sections.join("\n");
}

/**
 * Safe filename (mirror wiki_content.safe_filename).
 */
function safeFilename(title, maxLen = 80) {
  return title
    .split("")
    .map((c) => (/[a-zA-Z0-9 \-_]/.test(c) ? c : "_"))
    .join("")
    .slice(0, maxLen);
}

/**
 * Trigger download of a blob.
 */
function downloadBlob(blob, filename) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

/**
 * Build PDF with jsPDF (title, TOC, body, references).
 */
function buildPdf(title, bodyBlocks, references) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  const margin = 20;
  const pageWidth = doc.internal.pageSize.getWidth();
  const lineWidth = pageWidth - 2 * margin;
  let y = margin;

  // Title
  doc.setFontSize(18);
  doc.setFont("helvetica", "bold");
  const titleLines = doc.splitTextToSize(title, lineWidth);
  doc.text(titleLines, margin, y);
  y += titleLines.length * 8 + 10;

  // Table of Contents
  const tocEntries = bodyBlocks.filter((b) => b.type === "h2" || b.type === "h3");
  if (tocEntries.length || references.length) {
    doc.setFontSize(14);
    doc.text("Table of Contents", margin, y);
    y += 10;
    doc.setFontSize(11);
    doc.setFont("helvetica", "normal");
    for (const b of tocEntries) {
      const indent = b.type === "h3" ? 8 : 0;
      doc.text("  ".repeat(b.type === "h3" ? 2 : 0) + b.text, margin + indent, y);
      y += 6;
    }
    if (references.length) {
      doc.text("References", margin, y);
      y += 6;
    }
    y += 10;
  }

  doc.setFontSize(11);
  doc.setFont("helvetica", "normal");

  for (const b of bodyBlocks) {
    if (y > 270) {
      doc.addPage();
      y = margin;
    }
    if (b.type === "h2") {
      doc.setFontSize(14);
      doc.setFont("helvetica", "bold");
      doc.text(b.text, margin, y);
      y += 8;
      doc.setFontSize(11);
      doc.setFont("helvetica", "normal");
    } else if (b.type === "h3") {
      doc.setFontSize(12);
      doc.setFont("helvetica", "bold");
      doc.text(b.text, margin, y);
      y += 7;
      doc.setFontSize(11);
      doc.setFont("helvetica", "normal");
    } else {
      const lines = doc.splitTextToSize(b.text, lineWidth);
      doc.text(lines, margin, y);
      y += lines.length * 5 + 3;
    }
  }

  if (references.length) {
    if (y > 250) {
      doc.addPage();
      y = margin;
    }
    y += 10;
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("References", margin, y);
    y += 8;
    doc.setFontSize(11);
    doc.setFont("helvetica", "normal");
    for (const ref of references) {
      if (y > 270) {
        doc.addPage();
        y = margin;
      }
      const lines = doc.splitTextToSize(ref, lineWidth);
      doc.text(lines, margin, y);
      y += lines.length * 5 + 4;
    }
  }

  return doc;
}

/**
 * Download as plain text.
 */
async function downloadTxt(url) {
  const resultDiv = document.getElementById("result");
  const prevHtml = resultDiv.innerHTML;
  resultDiv.innerHTML = "Loading...";
  const content = await fetchArticleContent(url);
  resultDiv.innerHTML = prevHtml;
  if (!content) {
    alert("Failed to fetch article content.");
    return;
  }
  const text = formatPlainText(content.title, content.bodyBlocks, content.references);
  const blob = new Blob([text], { type: "text/plain; charset=utf-8" });
  downloadBlob(blob, safeFilename(content.title) + ".txt");
}

/**
 * Download as PDF.
 */
async function downloadPdf(url) {
  const resultDiv = document.getElementById("result");
  const prevHtml = resultDiv.innerHTML;
  resultDiv.innerHTML = "Loading...";
  const content = await fetchArticleContent(url);
  resultDiv.innerHTML = prevHtml;
  if (!content) {
    alert("Failed to fetch article content.");
    return;
  }
  const doc = buildPdf(content.title, content.bodyBlocks, content.references);
  doc.save(safeFilename(content.title) + ".pdf");
}

/**
 * Main: fetch random article and display.
 */
async function fetchArticle() {
  const category = document.getElementById("categorySelect").value;
  const resultDiv = document.getElementById("result");

  resultDiv.innerHTML = "Loading...";

  let url;
  try {
    url = await getRandomArticle(category);
  } catch (err) {
    console.error("fetchArticle error:", err);
    resultDiv.innerHTML = `Failed to fetch article. Check the browser console (F12) for details. If testing locally, try <code>npx serve docs</code> instead of opening the file directly.`;
    return;
  }

  if (!url) {
    resultDiv.innerHTML = `Failed to fetch article. Check the browser console (F12) for details. If testing locally, try <code>npx serve docs</code> instead of opening the file directly.`;
    return;
  }

  const title = url.split("/wiki/")[1].replace(/_/g, " ");
  const categoryLabel = CATEGORY_LABELS[category] || category;
  resultDiv.innerHTML = `
    <div>Read: <a href="${url}" target="_blank">${escapeHtml(title)}</a></div>
    <div class="meta">Category: ${escapeHtml(categoryLabel)}</div>
    <div class="meta" style="margin-top: 12px;">
      Download: <span class="download-link" data-url="${escapeHtml(url)}" data-format="txt">Plain text</span> &middot; <span class="download-link" data-url="${escapeHtml(url)}" data-format="pdf">PDF</span>
    </div>
    <div class="meta" style="margin-top: 8px;">
      <span class="download-link log-article-link" data-url="${escapeHtml(url)}" data-title="${escapeHtml(title)}" data-category="${escapeHtml(category)}">Log article</span>
    </div>
  `;

  resultDiv.querySelectorAll(".download-link").forEach((el) => {
    el.addEventListener("click", () => {
      if (el.classList.contains("log-article-link")) {
        logArticle(el.dataset.url, el.dataset.title, el.dataset.category);
      } else if (el.dataset.format === "txt") {
        downloadTxt(el.dataset.url);
      } else {
        downloadPdf(el.dataset.url);
      }
    });
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// --- Auth ---

function updateAuthUI() {
  const loggedOut = document.getElementById("authLoggedOut");
  const loggedIn = document.getElementById("authLoggedIn");
  const usernameEl = document.getElementById("authUsername");
  if (loggedOut && loggedIn && usernameEl) {
    if (loggedInUser) {
      loggedOut.style.display = "none";
      loggedIn.style.display = "";
      usernameEl.textContent = loggedInUser;
    } else {
      loggedOut.style.display = "";
      loggedIn.style.display = "none";
    }
  }
}

async function initAuth() {
  try {
    const res = await apiFetch("/api/me");
    if (!res.ok) return;
    const data = await res.json();
    if (data.username) {
      loggedInUser = data.username;
      const logRes = await apiFetch("/api/read-log");
      if (logRes.ok) {
        const logData = await logRes.json();
        const serverLog = logData.log || [];
        const localLog = (() => {
          try {
            const raw = localStorage.getItem(READ_LOG_KEY);
            return raw ? JSON.parse(raw) : [];
          } catch {
            return [];
          }
        })();
        if (localLog.length && !serverLog.length) {
          readLogCache = localLog;
          saveReadLog(localLog);
        } else {
          readLogCache = serverLog;
        }
      } else {
        readLogCache = [];
      }
    }
  } catch {
    // No backend (e.g. static serve)
  }
  updateAuthUI();
  renderReadLog();
}

function openAuthModal(mode) {
  const modal = document.getElementById("authModal");
  const title = document.getElementById("authModalTitle");
  const submitBtn = document.getElementById("authSubmit");
  const form = document.getElementById("authForm");
  const errorEl = document.getElementById("authError");
  if (!modal || !title || !submitBtn) return;
  errorEl.style.display = "none";
  errorEl.textContent = "";
  form.dataset.mode = mode;
  if (mode === "login") {
    title.textContent = "Log in";
    submitBtn.textContent = "Log in";
  } else {
    title.textContent = "Create account";
    submitBtn.textContent = "Create account";
  }
  modal.classList.add("visible");
}

function closeAuthModal() {
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.remove("visible");
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const form = document.getElementById("authForm");
  const usernameInput = document.getElementById("authUsernameInput");
  const passwordInput = document.getElementById("authPasswordInput");
  const errorEl = document.getElementById("authError");
  const submitBtn = document.getElementById("authSubmit");
  const title = document.getElementById("authModalTitle");
  if (!form || !usernameInput || !passwordInput || !errorEl) return;
  const username = usernameInput.value.trim();
  const password = passwordInput.value;
  const mode = form.dataset.mode || "login";
  errorEl.style.display = "none";
  submitBtn.disabled = true;
  try {
    const path = mode === "login" ? "/api/login" : "/api/register";
    const res = await apiFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json().catch(() => ({}));
    if (mode === "register") {
      if (!res.ok) {
        const noBackend = res.status === 404 || res.status === 0;
        errorEl.textContent = noBackend
          ? "Login requires the Python backend. Run `python vital_article.py` instead of `npx serve docs`."
          : (data.error || "Registration failed");
        errorEl.style.display = "block";
        return;
      }
      const loginRes = await apiFetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      if (!loginRes.ok) {
        errorEl.textContent = "Account created. Please log in.";
        errorEl.style.display = "block";
        form.dataset.mode = "login";
        title.textContent = "Log in";
        submitBtn.textContent = "Log in";
        return;
      }
      const loginData = await loginRes.json();
      loggedInUser = loginData.username || username;
      const logRes = await apiFetch("/api/read-log");
      if (logRes.ok) {
        const logData = await logRes.json();
        readLogCache = logData.log || [];
      } else {
        readLogCache = [];
      }
      closeAuthModal();
      updateAuthUI();
      renderReadLog();
      return;
    }
    if (!res.ok) {
      const noBackend = res.status === 404 || res.status === 0;
      errorEl.textContent = noBackend
        ? "Login requires the Python backend. Run `python vital_article.py` instead of `npx serve docs`."
        : (data.error || "Login failed");
      errorEl.style.display = "block";
      return;
    }
    loggedInUser = data.username || username;
    const logRes = await apiFetch("/api/read-log");
    if (logRes.ok) {
      const logData = await logRes.json();
      readLogCache = logData.log || [];
    } else {
      readLogCache = [];
    }
    closeAuthModal();
    updateAuthUI();
    renderReadLog();
  } catch (err) {
    errorEl.textContent = "Could not connect. Run the Python backend for login.";
    errorEl.style.display = "block";
  } finally {
    submitBtn.disabled = false;
  }
}

async function handleLogout() {
  try {
    await apiFetch("/api/logout", { method: "POST" });
  } catch {
    // ignore
  }
  loggedInUser = null;
  readLogCache = null;
  updateAuthUI();
  renderReadLog();
}

// Wire up when DOM ready
document.addEventListener("DOMContentLoaded", () => {
  window.fetchArticle = fetchArticle;
  initAuth();
  document.getElementById("authLoginLink")?.addEventListener("click", (e) => {
    e.preventDefault();
    openAuthModal("login");
  });
  document.getElementById("authRegisterLink")?.addEventListener("click", (e) => {
    e.preventDefault();
    openAuthModal("register");
  });
  document.getElementById("authLogout")?.addEventListener("click", (e) => {
    e.preventDefault();
    handleLogout();
  });
  document.getElementById("authModalClose")?.addEventListener("click", (e) => {
    e.preventDefault();
    closeAuthModal();
  });
  document.getElementById("authForm")?.addEventListener("submit", handleAuthSubmit);
  document.getElementById("authModal")?.addEventListener("click", (e) => {
    if (e.target.id === "authModal") closeAuthModal();
  });
});
