from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
import requests
from bs4 import BeautifulSoup
import random
import uvicorn

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


@app.get("/", response_class=HTMLResponse)
async def home():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Random Technical Wiki</title>
        <style>
            body { font-family: sans-serif; text-align: center; padding-top: 50px; background-color: #f4f4f9; }
            .container { background: white; max-width: 600px; margin: auto; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #333; margin-bottom: 25px; }
            
            /* Dropdown Styling */
            select { padding: 10px; font-size: 16px; border-radius: 5px; border: 1px solid #ccc; margin-right: 10px; }
            
            button { background-color: #007bff; color: white; border: none; padding: 12px 25px; font-size: 16px; border-radius: 5px; cursor: pointer; transition: background 0.3s; }
            button:hover { background-color: #0056b3; }
            
            #result { margin-top: 30px; font-size: 18px; min-height: 40px;}
            a { color: #007bff; text-decoration: none; font-weight: bold; font-size: 20px; }
            a:hover { text-decoration: underline; }
            .meta { color: #666; font-size: 14px; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Random Technical Wiki</h1>
            
            <div>
                <select id="categorySelect">
                    <option value="physics">Physical Sciences</option>
                    <option value="technology">Engineering & Tech</option>
                    <option value="economics">Society & Economics</option>
                </select>
                <button onclick="fetchArticle()">Go</button>
            </div>

            <div id="result"></div>
        </div>

        <script>
            async function fetchArticle() {
                const category = document.getElementById("categorySelect").value;
                const resultDiv = document.getElementById("result");
                
                resultDiv.innerHTML = "Loading...";
                
                // Pass the selected category as a query parameter
                const response = await fetch(`/random?category=${category}`);
                const data = await response.json();
                
                if (data.url) {
                    // Extract readable title from URL
                    const title = data.url.split('/wiki/')[1].replace(/_/g, ' ');
                    resultDiv.innerHTML = `
                        <div>Read: <a href="${data.url}" target="_blank">${title}</a></div>
                        <div class="meta">Category: ${category}</div>
                        <div class="meta" style="margin-top: 12px;">
                            Download: <a href="/download?url=${encodeURIComponent(data.url)}&format=txt">Plain text</a> &middot; <a href="/download?url=${encodeURIComponent(data.url)}&format=pdf">PDF</a>
                        </div>
                    `;
                } else {
                    resultDiv.innerText = "Failed to fetch article (likely connection error).";
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content

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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)