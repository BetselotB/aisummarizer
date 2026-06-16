# AI Study Guide Generator

Turn PDFs and notes into detailed, exam-ready study guides — styled like a professional ReportLab document (see `references/study_guide.py`).

## Architecture

```
PDF / text  →  extract  →  Gemini (outline)  →  Gemini (per chapter)  →  JSON  →  ReportLab PDF
                              ↑ key rotation on 429/quota
```

- **Template** (`template/`) — fixed ReportLab styles + JSON renderer (write once)
- **AI** — generates structured JSON only (outline → chapters → appendix)
- **Keys** — add many Gemini API keys; app round-robins on rate limits

## Quick start

```bash
cd aisummarizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build the React UI (first time + after frontend changes)
cd frontend && npm install && npm run build && cd ..

python run.py
```

Open **http://localhost:8000**

**UI dev mode** (hot reload): run `python run.py` in one terminal and `cd frontend && npm run dev` in another (proxies `/api` to :8000).

### App pages

- **Create** — upload PDFs, start new jobs (multiple jobs can run in parallel)
- **Tasks** — tabbed view for all running/failed/completed jobs with live logs
- **Keys** — Gemini API keys & model
- **Activity** — persisted event history

## Gemini keys

Get keys from [Google AI Studio](https://aistudio.google.com/apikey). Paste as many as you have — each chapter call can use the next key if one hits quota.

Optional env overrides in `app/config.py`:

- `GEMINI_MODEL_OUTLINE` / `GEMINI_MODEL_CHAPTER` (default: `gemini-2.0-flash`)

## Output

Intermediate files are saved under `data/jobs/<job-id>/`:

- `source.txt`, `outline.json`, `chapter_*.json`, `document.json`
- Final PDF in `data/outputs/`

Re-render without calling the API:

```bash
python -c "from template.render import render_pdf_from_json; render_pdf_from_json('data/jobs/JOB_ID/document.json', 'out.pdf')"
```

## JSON block types

`section`, `subsection`, `body`, `bullet`, `subbullet`, `numbered_list`, `note`, `key`, `code`, `table`, `table_3col`, `compare_table`, `spacer`

See `prompts/chapter.txt` for the schema the AI follows.

## Deploy on Vercel (single app)

The React UI and FastAPI backend deploy together as one Vercel project. Vercel auto-detects the FastAPI app at `app/main.py` and runs the frontend build from `pyproject.toml`.

### 1. Push to GitHub

Connect the repo in the [Vercel dashboard](https://vercel.com/new) or use the CLI:

```bash
npm i -g vercel
vercel login
vercel link
vercel deploy
```

### 2. Set environment variables

In **Project → Settings → Environment Variables**, add:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEYS` | Yes | One or more Gemini keys (`AIza…`), comma- or newline-separated |
| `INTERNAL_JOB_SECRET` | Yes | Random secret (e.g. `openssl rand -hex 32`) — secures the background job worker |

Optional overrides: `GEMINI_MODEL`, `GEMINI_MODEL_FALLBACKS`, `GEMINI_INTER_REQUEST_DELAY`, etc. (see `app/config.py`).

### 3. Redeploy

After setting env vars, redeploy (`vercel --prod` or push to main).

### Vercel limitations

- **Ephemeral storage** — SQLite and uploads live under `/tmp` and reset on cold starts. Use **Resume** on failed jobs when checkpoints still exist on the same instance; for production persistence, add Vercel Blob or a marketplace database.
- **300s timeout** — Long guides may need smaller PDFs or resume after timeout.
- **Keys via env** — On Vercel, add keys with `GEMINI_API_KEYS` (the Keys UI still works but won’t survive cold starts).

### Local Vercel dev

```bash
pip install -r requirements.txt
cd frontend && npm ci && npm run build && cd ..
export GEMINI_API_KEYS="AIza..."
export INTERNAL_JOB_SECRET="dev-secret"
vercel dev
```

