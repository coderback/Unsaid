# Unsaid — Semantic 10-K Disclosure-Removal Detector

Surface what companies quietly removed or softened in their annual SEC 10-K filings.
Year-over-year semantic diff of Item 1A (Risk Factors) and Item 7A (Market Risk),
powered by Claude as the judge.

> **Honest framing:** This tool democratises a capability available in institutional
> platforms like AlphaSense and Verity. It surfaces changes in risk-disclosure language.
> It does not make return predictions or claim to have invented the underlying signal
> (see: Cohen, Malloy & Nguyen 2020, "Lazy Prices").

---

## The headline demo — Silicon Valley Bank

SVB filed their FY2022 10-K on **24 Feb 2023**. The bank collapsed on **10 Mar 2023**.
The FY2022 filing quietly removed the **Economic Value of Equity (EVE) sensitivity table**
from Item 7A, which in FY2021 had shown EVE falling ~27% (~$5.7bn) on a +200bp rate move.
It also dropped all discussion of interest-rate hedges. Unsaid surfaces this as a REMOVED
disclosure tagged to Item 7A — derived automatically from the real SEC filings.

---

## Quick start — Docker (recommended)

The easiest way to run the app. No Python/Node setup needed.

### Prerequisites
- Docker Desktop
- An Anthropic API key
- Pre-computed cache files in `cache/` (run the ingest pipeline first, or copy existing `.json` files)

### Run

```bash
# 1. Set your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 2. Build images (first time ~10 min — downloads the embedding model)
docker compose build

# 3. Start
docker compose up

# Open http://localhost:3000
```

The `cache/` directory is bind-mounted, so pre-computed analyses load instantly.

To run the ingest pipeline inside Docker:
```bash
docker compose run --rm api python -m unsaid.ingest --ticker SIVB --cik 0000719739 --years 2021 2022
```

---

## Quick start — local (< 10 minutes)

### Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key

### 1. Clone and set up Python

```bash
git clone <repo>
cd Unsaid
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure your API key

```bash
cp .env.example .env
# Edit .env and set:
# ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run the SVB ingest pipeline

```bash
python -m unsaid.ingest --ticker SIVB --cik 0000719739 --years 2021 2022
```

This takes **5–15 minutes** (EDGAR downloads + Claude API calls).
When complete, `cache/SIVB_2021_2022.json` will contain the full analysis.

**Verify the headline finding:**

```bash
python -c "
import json
d = json.load(open('cache/SIVB_2021_2022.json'))
signals = [c for c in d['changes'] if c['classification'] in ('REMOVED','SOFTENED')]
for c in signals:
    print(f\"[{c['classification']}] [{c['section']}] {c['title']}\")
    print(f\"  {c['year1_quote'][:120]}...\")
    print()
"
```

You should see a REMOVED item tagged `7A` referencing EVE / interest-rate sensitivity.

### 4. (Optional) Pre-cache additional companies

```bash
python -m unsaid.ingest --ticker PTON --years 2021 2022
python -m unsaid.ingest --ticker META --years 2021 2022
```

### 5. Start the FastAPI backend

```bash
uvicorn api.main:app --port 8000 --reload
```

Verify: `http://localhost:8000/demos` should list cached tickers.

### 6. Start the Next.js frontend

```bash
cd frontend
npm install   # first time only
npm run dev
```

Open `http://localhost:3000` — you should see the landing page with the SVB demo card.
Click the SVB card to load the analysis from cache. REMOVED items appear at the top in red.

---

## Running the demo live

The default demo reads from `cache/` — no live API calls. The SVB card appears automatically
if `cache/SIVB_2021_2022.json` exists.

For a fresh ticker during the demo, use the ticker input box on the landing page. This calls
`POST /run` which runs the pipeline in the background (~5–15 min). A loading state is shown.

---

## Project structure

```
Unsaid/
├── unsaid/
│   ├── fetcher.py       # EDGAR retrieval (edgartools, rate-throttled)
│   ├── extractor.py     # Item 1A / 7A text extraction + HTML cleaning
│   ├── segmenter.py     # Claude Sonnet: section → discrete disclosure units
│   ├── aligner.py       # sentence-transformers: cosine top-K candidate matching
│   ├── judge.py         # Claude Opus: classify each Year-1 unit vs Year-2 candidates
│   ├── cache.py         # JSON cache read/write
│   └── ingest.py        # CLI orchestrator
├── api/
│   └── main.py          # FastAPI: /diff/{ticker}, /demos, /run
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Landing page
│   │   └── diff/[ticker]/page.tsx  # Results view
│   ├── components/                  # ChangeCard, SummaryBar, DemoCard, SectionTag
│   └── lib/                         # API client, types, constants
├── cache/               # Pre-computed JSON results
└── requirements.txt
```

## Architecture notes

**Rule 1 — Embeddings align, Claude judges.**
`sentence-transformers/all-mpnet-base-v2` is used only to find candidate Year-2 units for
each Year-1 unit. Claude Opus makes every classification call. Cosine similarity never
determines the outcome — this is essential because embeddings fail at negation.

**Rule 2 — Item 1A and Item 7A both extracted.**
The SVB demo finding (EVE removal) lives in Item 7A, not Item 1A. Every change card shows
which section it came from.

**Rule 3 — Demo runs from cache.**
`cache/*.json` files are pre-computed offline. The live app reads JSON from disk and renders
instantly. No EDGAR or LLM calls happen during a demo.

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (ingest only) | — | Anthropic API key |
| `EDGAR_IDENTITY` | No | `Unsaid/1.0 tobiojebiyi@gmail.com` | SEC EDGAR user-agent string |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | FastAPI base URL |

## CLI reference

```
python -m unsaid.ingest [OPTIONS]

Options:
  --ticker TEXT        Company ticker (e.g. SIVB, PTON)
  --cik TEXT           SEC CIK number (for delisted companies; e.g. 0000719739)
  --years YEAR1 YEAR2  Two fiscal years to compare (required)
  --force              Re-run even if cache file already exists
```
