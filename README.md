# Random Technical Wiki

A web app that fetches random Vital Wikipedia articles by category and lets you download them as plain text or PDF. Log in to sync your article read log across devices.

## Local Development

### Vercel (recommended for Vercel deployment parity)

```bash
pip install -r requirements.txt
vercel dev
```

Open http://localhost:3000 (or the port shown). Add a Redis database in the Vercel dashboard for login to work, or it falls back to JSON file storage when Redis env vars are not set.

### Python backend (JSON file storage, no Redis)

```bash
pip install -r requirements.txt
python vital_article.py
```

Open http://127.0.0.1:8000

Use **Log in** / **Create account** to save your article log. When logged in, your read log syncs across devices.

### Static (no login)

```bash
npx serve public
```

Open http://localhost:3000 (or the port shown). Login will not work without a backend.

**Note:** Do not open `public/index.html` directly in a browser (file://). Wikipedia's API blocks requests from the null origin. Use a local server.

## Deploy to Vercel

1. Push this repo to GitHub and [import to Vercel](https://vercel.com/new).

2. Add a Redis database:
   - In your Vercel project, go to **Storage** > **Create Database** > **Redis** (Upstash)
   - Connect it to your project so env vars (e.g. `KV_REST_API_URL`, `KV_REST_API_TOKEN`) are set

3. Deploy. Vercel detects the FastAPI app and serves static files from `public/`.

Your app will be available at `https://your-project.vercel.app`.

## Deploy to GitHub Pages (static only, no login)

1. Push this repo to GitHub.

2. In the repo, go to **Settings** > **Pages** (under "Code and automation").

3. Under **Build and deployment**:
   - **Source**: Deploy from a branch
   - **Branch**: `main` (or your default branch)
   - **Folder**: `/public`

4. Click **Save**. The site will be available at:
   `https://<username>.github.io/wikipedia_random/`

Login will not work on GitHub Pages (no backend).
