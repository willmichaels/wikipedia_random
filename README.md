# Random Technical Wiki

A static web app that fetches random Vital Wikipedia articles by category (Physical Sciences, Engineering & Tech, Society & Economics) and lets you download them as plain text or PDF.

## Local Development

### Python (original backend)

```bash
pip install -r requirements.txt
python vital_article.py
```

Open http://127.0.0.1:8000

### Static (GitHub Pages)

```bash
npx serve docs
```

Open http://localhost:3000 (or the port shown)

**Note:** Do not open `docs/index.html` directly in a browser (file://). Wikipedia's API blocks requests from the null origin. Use a local server.

## Deploy to GitHub Pages

1. Push this repo to GitHub.

2. In the repo, go to **Settings > Pages** (under "Code and automation").

3. Under **Build and deployment**:
   - **Source**: Deploy from a branch
   - **Branch**: `main` (or your default branch)
   - **Folder**: `/docs`

4. Click **Save**. The site will be available at:
   `https://<username>.github.io/wikipedia_random/`
