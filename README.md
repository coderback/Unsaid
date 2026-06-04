# Unsaid
### Semantic 10-K Disclosure-Removal Detector

> Companies announce good news loudly. They bury bad news quietly — by removing or softening language in their annual SEC filings. Unsaid surfaces what they stopped saying.

---

## The problem

Every year, public companies file a 10-K with the SEC. Most of the attention goes to the numbers. Almost none goes to *what language disappeared* between one year and the next.

Academic research (Cohen, Malloy & Nguyen 2020 — "Lazy Prices") shows that ~86% of year-over-year textual changes in 10-Ks are negative in sentiment, and that markets systematically underprice them. Institutional platforms like AlphaSense and Verity charge enterprise rates to detect these changes. No free, open, *semantic* version exists.

Unsaid is that tool.

It fetches two consecutive 10-K filings from SEC EDGAR, semantically compares every risk disclosure in Item 1A (Risk Factors) and Item 7A (Market Risk), and classifies each Year-1 disclosure as **REMOVED**, **SOFTENED**, **REWORDED**, **RETAINED**, or **ABSORBED** — using Claude as the judge, not keyword matching.

---

## The demo — Silicon Valley Bank

SVB filed their FY2022 10-K on **24 February 2023**. The bank collapsed on **10 March 2023** — 14 days later.

Running Unsaid on the real EDGAR filings reveals what was quietly removed from Item 7A (Market Risk Disclosures):

```
[REMOVED] [Item 7A]  EVE Hedging — Interest Rate Swaps and Sensitivity Reduction
  confidence: 0.86

  Year-1 (FY2021):
  "In March 2021 we purchased interest rate swaps to offset some of the additional
  EVE sensitivity... The addition of pay fixed swaps reduces this exposure to
  -13.9 percent in the same scenario."

  Year-2 (FY2022): No corresponding disclosure found.

  Reasoning: The Year-1 disclosure described an active EVE hedge using pay fixed
  swaps that reduced rate-shock sensitivity. Year-2 explicitly states the pay fixed
  swaps portfolio was terminated, with no replacement hedging disclosed.

──────────────────────────────────────────────────────────────────────────────

[SOFTENED] [Item 7A]  EVE and NII Sensitivity Table — Rate Shock Scenarios
  confidence: 0.72

  Year-1 (FY2021):
  "December 31, 2021: +200bps → EVE $(5,722)M  (27.7)%  |  NII $981M  22.9%"

  Year-2 (FY2022): EVE column removed entirely. Only NII sensitivity shown.

  Reasoning: The FY2022 table drops the EVE sensitivity disclosure entirely —
  no longer quantifying the -27.7% / -$5.7bn EVE decline on a +200bp rate move.
  The same interest-rate risk persists but the EVE dimension is no longer disclosed.
```

This is not hand-coded. It is the raw output of the pipeline run against the actual SEC filings.

---

## What Unsaid does

Given a company ticker and two fiscal years, Unsaid:

1. Fetches both 10-K filings from SEC EDGAR
2. Extracts Item 1A (Risk Factors) and Item 7A (Market Risk) as clean prose
3. Segments each section into discrete disclosure units using Claude
4. Aligns Year-1 units to their closest Year-2 counterparts using semantic embeddings
5. Asks Claude to classify every Year-1 unit: was it retained, reworded, softened, removed, or absorbed?
6. Flags Year-2 units with no Year-1 match as NEW disclosures
7. Caches the result as JSON; the web app renders it instantly

The output is a prioritised feed of signal — REMOVED and SOFTENED findings first, with verbatim quotes and Claude's one-line reasoning for each.

**Three companies are pre-cached and load instantly:**
| Ticker | Company | Period | Signal |
|--------|---------|--------|--------|
| SIVB | SVB Financial Group | FY2021 → FY2022 | 4 REMOVED, 4 SOFTENED |
| PTON | Peloton Interactive | FY2021 → FY2022 | 1 SOFTENED |
| META | Meta Platforms | FY2021 → FY2022 | 1 SOFTENED |

---

## How it works

### Why Claude judges instead of embeddings

Vector embeddings are used only to find candidate matches between years — not to classify them. The reason: embeddings fail at negation and softening. *"We are exposed to significant interest-rate risk"* and *"We are no longer exposed to significant interest-rate risk"* score >0.90 cosine similarity despite being opposites. Detecting exactly that inversion is the entire point of the tool.

Claude Opus receives the Year-1 disclosure and its top-5 Year-2 candidates and classifies the change. Every classification in the output passed through the LLM judge. Cosine similarity never makes the final call.

### Why Item 7A as well as Item 1A

The SVB finding lives in Item 7A (Market Risk), not Item 1A (Risk Factors). A tool that only diffs Item 1A would miss it entirely. Unsaid extracts both sections and tags every finding with its source.

### Why results are cached

EDGAR rate-limits requests and LLM calls take time. The pipeline (fetch → segment → align → judge) runs offline and writes a single JSON file. The web app reads from disk and renders in milliseconds. The demo cannot fail due to network or API latency.

### Pipeline

```
SEC EDGAR
    │
    ▼
edgartools          fetch 10-K filings (rate-throttled, ≤10 req/s)
    │
    ▼
extractor.py        pull Item 1A + Item 7A as clean prose text
    │
    ▼
segmenter.py        Claude Sonnet (claude-sonnet-4-6)
                    section text → discrete disclosure units [{id, title, text, section}]
    │
    ▼
aligner.py          all-mpnet-base-v2 (sentence-transformers, local)
                    embed all units → cosine similarity matrix → top-5 candidates per Year-1 unit
    │
    ▼
judge.py            Claude Opus (claude-opus-4-8)
                    Year-1 unit + top-5 Year-2 candidates → classification + reasoning
    │
    ▼
cache/{TICKER}_{YEAR1}_{YEAR2}.json
```

---

## Running the demo

### Docker (recommended)

```bash
# Clone and start
git clone <repo> && cd Unsaid
docker compose up
```

Open `http://localhost:3000`. The SVB demo loads from cache instantly — no API key needed.

To analyse a new ticker (requires `ANTHROPIC_API_KEY` in `.env`):
```bash
docker compose run --rm api python -m unsaid.ingest --ticker AAPL --years 2022 2023
```

### Local

```bash
# Python setup
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start API (demo cache works without an API key)
uvicorn api.main:app --port 8000 --reload

# Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000`.

**To run ingest on a new ticker**, add `ANTHROPIC_API_KEY` to `.env` first:
```bash
python -m unsaid.ingest --ticker MSFT --years 2022 2023
# Runs in ~10–15 min; result cached to cache/MSFT_2022_2023.json
```

---

## Project structure

```
Unsaid/
├── unsaid/
│   ├── fetcher.py       # EDGAR retrieval (edgartools, rate-throttled)
│   ├── extractor.py     # Item 1A / 7A extraction + HTML cleaning
│   ├── segmenter.py     # Claude Sonnet segmentation
│   ├── aligner.py       # Embedding alignment (all-mpnet-base-v2)
│   ├── judge.py         # Claude Opus classification
│   ├── cache.py         # JSON cache read/write
│   └── ingest.py        # CLI orchestrator
├── api/
│   ├── Dockerfile
│   └── main.py          # FastAPI: /diff/{ticker}, /demos, /run
├── frontend/
│   ├── Dockerfile
│   ├── app/page.tsx               # Landing page
│   ├── app/diff/[ticker]/page.tsx # Results view
│   ├── components/                # ChangeCard, SummaryBar, DemoCard, SectionTag
│   └── lib/                       # API client, types, constants
├── cache/               # Pre-computed results (SIVB, PTON, META committed)
├── docker-compose.yml
└── requirements.txt
```

---

## What this is not

This tool surfaces changes in disclosure language. It does not predict stock returns, guarantee alpha, or claim to have invented the underlying signal. The "Lazy Prices" anomaly is published academic research. Unsaid makes it accessible without an enterprise contract.

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Ingest only | — | Only needed to analyse new tickers |
| `EDGAR_IDENTITY` | No | `Unsaid/1.0 tobiojebiyi@gmail.com` | SEC EDGAR user-agent |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | FastAPI base URL |

## CLI

```
python -m unsaid.ingest --ticker TICKER --years YEAR1 YEAR2 [--cik CIK] [--force]

  --ticker    Company ticker (e.g. PTON, META)
  --cik       SEC CIK — use for delisted companies (e.g. 0000719739 for SIVB)
  --years     Two fiscal years to compare
  --force     Overwrite existing cache file
```
