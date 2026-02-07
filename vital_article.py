from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
import requests
from bs4 import BeautifulSoup
import random
import uvicorn

from auth import (
    SESSION_COOKIE,
    get_log,
    login as auth_login,
    logout as auth_logout,
    register as auth_register,
    save_log,
    verify_session,
)
from wiki_content import (
    fetch_article_content,
    format_plain_text_with_references,
    safe_filename,
)
from pdf_builder import build_pdf

app = FastAPI()

# Configuration: Map categories to their Vital Article URLs
SOURCES = {
    "physics": "https://en.wikipedia.org/wiki/Wikipedia:Vital_articles/Level/4/Physical_sciences",
    "technology": "https://en.wikipedia.org/wiki/Wikipedia:Vital_articles/Level/4/Technology",
    "economics": "https://en.wikipedia.org/wiki/Wikipedia:Vital_articles/Level/4/Society_and_social_sciences"
}

# Global cache: {'physics': [url1, url2...], 'technology': [...]}
# We use a dict so we can lazy-load each category independently.
ARTICLES_CACHE = {}

def get_random_vital_article(category: str):
    global ARTICLES_CACHE
    
    # 1. Input Validation
    if category not in SOURCES:
        return None

    # 2. Check Cache
    if category in ARTICLES_CACHE and ARTICLES_CACHE[category]:
        return f"https://en.wikipedia.org{random.choice(ARTICLES_CACHE[category])}"

    # 3. Scrape if Cache Miss
    url = SOURCES[category]
    headers = {'User-Agent': 'VitalArticleScraper/1.0 (science_fan@example.com)'}
    
    try:
        print(f"Cache miss for '{category}'. Scraping Wikipedia...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        content_div = soup.find(id="mw-content-text")
        
        valid_links = []
        for link in content_div.find_all('a', href=True):
            href = link['href']
            # Standard Wikipedia Filters
            if (href.startswith("/wiki/") and 
                ":" not in href and 
                "Main_Page" not in href):
                valid_links.append(href)

        if not valid_links:
            return None
            
        # Update Cache
        ARTICLES_CACHE[category] = valid_links
        print(f"Cache populated for '{category}' with {len(valid_links)} articles.")
        
        return f"https://en.wikipedia.org{random.choice(ARTICLES_CACHE[category])}"

    except Exception as e:
        print(f"Error scraping {category}: {e}")
        return None


# --- Auth & read-log API ---


@app.post("/api/register")
async def api_register(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    err = auth_register(username, password)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return JSONResponse({"ok": True})


@app.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    session_id = auth_login(username, password)
    if not session_id:
        return JSONResponse({"error": "Invalid username or password"}, status_code=401)
    response = JSONResponse({"ok": True, "username": username})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@app.post("/api/logout")
async def api_logout(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)
    auth_logout(session_id)
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/api/me")
async def api_me(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)
    username = verify_session(session_id)
    if not username:
        return JSONResponse({"username": None})
    return JSONResponse({"username": username})


@app.get("/api/read-log")
async def api_get_read_log(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)
    username = verify_session(session_id)
    if not username:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    log = get_log(username)
    return JSONResponse({"log": log})


@app.post("/api/read-log")
async def api_save_read_log(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)
    username = verify_session(session_id)
    if not username:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    body = await request.json()
    log = body.get("log", [])
    if not isinstance(log, list):
        return JSONResponse({"error": "Invalid log"}, status_code=400)
    save_log(username, log)
    return JSONResponse({"ok": True})


# --- Legacy routes (for backward compatibility) ---


@app.get("/random")
async def random_article(category: str = "physics", format: str | None = None):
    url = get_random_vital_article(category)
    if not url:
        return {"url": None}

    if format == "txt" or format == "plaintext":
        title, body_blocks, references = fetch_article_content(url)
        if title is None:
            return {"url": url, "error": "Failed to fetch article content"}
        content = format_plain_text_with_references(title, body_blocks, references)
        return PlainTextResponse(
            content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename(title)}.txt"'},
        )

    if format == "pdf":
        title, body_blocks, references = fetch_article_content(url)
        if title is None:
            return {"url": url, "error": "Failed to fetch article content"}
        pdf_bytes = build_pdf(title, body_blocks, references)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename(title)}.pdf"'},
        )

    return {"url": url}


@app.get("/download")
async def download_article(url: str, format: str = "txt"):
    """Download a specific Wikipedia article as plaintext or PDF. Use url=...&format=txt or format=pdf."""
    if not url.startswith("https://en.wikipedia.org/wiki/"):
        return {"error": "Invalid Wikipedia URL"}
    title, body_blocks, references = fetch_article_content(url)
    if title is None:
        return {"error": "Failed to fetch article content"}

    if format == "pdf":
        pdf_bytes = build_pdf(title, body_blocks, references)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_filename(title)}.pdf"'},
        )
    content = format_plain_text_with_references(title, body_blocks, references)
    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename(title)}.txt"'},
    )


# Serve public app (must be last so API routes take precedence)
public_path = Path(__file__).resolve().parent / "public"
app.mount("/", StaticFiles(directory=str(public_path), html=True))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)