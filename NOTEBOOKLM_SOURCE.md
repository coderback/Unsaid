# Unsaid — Project Source Document

## What is Unsaid?

Unsaid is a semantic disclosure analysis tool that reads two consecutive annual reports (10-K filings) from any publicly traded company and surfaces what the company quietly removed or softened in its risk disclosures between the two years.

The core insight is simple: companies broadcast good news loudly. They bury emerging risk quietly — not through outright lies, but through omission, softening of language, and the removal of quantitative details from year to year. The change is rarely visible to a casual reader. It requires reading both documents side by side and knowing exactly what disappeared.

Unsaid automates this process using a combination of large language models and semantic search. It was built for the Move 37 student AI × finance competition.

---

## The Problem It Solves

Every year, public companies file a 10-K with the SEC — a comprehensive annual report that includes a section called Item 1A (Risk Factors) and a section called Item 7A (Quantitative and Qualitative Disclosures About Market Risk). These sections are where companies are legally required to describe the risks they face.

The problem is that risk disclosures change year over year in ways that carry real signal. A company might describe a specific financial exposure in detail in one year and then drop the disclosure entirely the next year. They might replace a specific quantitative claim with vague qualitative language. They might remove a caveat, soften a qualifier, or restructure a table so that a damaging number disappears.

Academic research has documented that these changes are meaningful. A 2020 paper by Cohen, Malloy, and Nguyen called "Lazy Prices" demonstrated that when companies make significant changes to their risk disclosures — particularly removals and softening — future stock returns tend to underperform. The market, on average, does not price this signal at the time of filing. Institutional investors using tools like AlphaSense can detect these changes semantically. Retail investors and most analysts cannot.

Unsaid is an open-source implementation of that capability.

---

## How It Works

The pipeline has six steps.

**Step 1 — Fetch.** Unsaid retrieves two 10-K filings from SEC EDGAR using the edgartools library. You can specify a company by ticker symbol (e.g. AAPL) or by CIK number, which is required for companies that have been delisted. It matches filings by the fiscal year end date and falls back to the filing date if needed.

**Step 2 — Extract.** It extracts the text of Item 1A (Risk Factors) and Item 7A (Market Risk) from each filing. This is harder than it sounds — 10-K filings are HTML documents with complex table structures, boilerplate text, and inconsistent formatting. Unsaid uses BeautifulSoup to convert the HTML to clean prose, preserving quantitative statements (dollar figures, percentages, basis points) while filtering out pure numeric table noise.

**Step 3 — Segment.** Each section can be tens of thousands of words long. Before comparing anything, Unsaid breaks the text into discrete, self-contained disclosure units — each unit represents one coherent risk or topic, typically one to five paragraphs. This segmentation is done by Claude Sonnet using a structured tool call. Claude is instructed to produce units that are complete ideas, not sentences, and to preserve all quantitative figures verbatim. A typical filing produces between 5 and 30 units per section.

**Step 4 — Align.** With units from both years in hand, Unsaid uses a local sentence embedding model (all-mpnet-base-v2 from the sentence-transformers library) to compute cosine similarity between every Year-1 unit and every Year-2 unit. For each Year-1 unit, it identifies the top 5 most semantically similar Year-2 units as candidates. It also identifies Year-2 units that have no close match in Year-1 — these are candidates for genuinely new disclosures. The embeddings are used purely for candidate retrieval. They never make a classification decision.

**Step 5 — Judge.** Each Year-1 unit is then sent to Claude Opus along with its top candidate matches from Year-2. Claude reads both sides and classifies what happened to the risk. The possible classifications are: RETAINED (same risk, same language), REWORDED (same risk, different wording), SOFTENED (risk downgraded, hedged, or qualifiers weakened), REMOVED (genuinely absent from Year-2), or ABSORBED (folded into a broader Year-2 disclosure). Claude also provides a verbatim quote from Year-1, the corresponding Year-2 text or a null if removed, a one-to-two sentence reasoning explanation, and a confidence score. Year-2 units with no Year-1 match are classified as NEW.

**Step 6 — Cache.** Results are written to a JSON file. The frontend reads from this cache — no live pipeline runs during a demo. The cache includes the full list of classified changes, summary counts by classification, and metadata.

---

## The Architecture

**Backend:** A FastAPI server (Python) exposes four endpoints. `GET /demos` lists all pre-computed analyses. `GET /diff/{ticker}` returns the full cached result for a ticker. `POST /run` launches the live pipeline in a background thread for a new ticker and returns a job ID. `GET /run/{job_id}` polls the job status.

**Frontend:** A Next.js application with TailwindCSS. The design is a dark terminal aesthetic — black background, monospace font (IBM Plex Mono), zinc color palette. The landing page shows a ticker search box and a grid of pre-computed demo analyses. The diff page shows all classified changes sorted by signal priority (REMOVED first, then SOFTENED, NEW, ABSORBED, REWORDED, RETAINED). Signal findings are expanded by default; noise (reworded/retained) is collapsed behind a disclosure element. Users can filter by classification and by section (Item 1A or Item 7A).

**Infrastructure:** Docker Compose runs both the API and frontend containers. The frontend proxies API requests through a Next.js rewrite so the browser never needs direct access to the backend. The cache directory is mounted as a volume so it persists across container restarts.

---

## The SVB Demo

The headline demonstration uses Silicon Valley Bank (ticker: SIVB).

SVB filed their FY2022 10-K on February 24th, 2023. The bank collapsed on March 10th, 2023 — fourteen days later. It was the second-largest bank failure in US history.

Unsaid's analysis of the FY2021 versus FY2022 10-K found 16 classified changes across Item 1A and Item 7A. Four disclosures were completely removed. Four were softened. The most significant findings are as follows.

**EVE Hedging — REMOVED (confidence 86%)**
In FY2021, SVB disclosed that they had purchased interest rate swaps in March 2021 to offset their exposure to rising interest rates. Their own filing stated: "The addition of pay fixed swaps reduces this exposure to -13.9 percent in the same scenario." In FY2022, the only corresponding disclosure was: "termination of our pay fixed swaps portfolio." The hedges were gone, and there was no replacement hedging disclosure. The risk-mitigating activity simply disappeared.

**EVE and NII Sensitivity Table — SOFTENED (confidence 72%)**
In FY2021, SVB published a full sensitivity table showing both Economic Value of Equity (EVE) and Net Interest Income (NII) sensitivity under different interest rate shock scenarios. Under a +200 basis point shock, their EVE would decline by 27.7 percent — a loss of $5.722 billion. Under +100 basis points, EVE would decline 13.9 percent. In FY2022, the EVE column was removed from the table entirely. The table showed only NII sensitivity, which had itself collapsed from +22.9% to +3.5% at the +200 basis point level. The largest and most damaging number — the $5.7 billion EVE exposure — no longer appeared anywhere in the filing.

**EVE Sensitivity — SOFTENED (confidence 70%)**
FY2021 disclosed a specific, concrete mechanism: excess deposits that could not be deployed into loans had been invested in fixed-rate securities, and under upward rate shocks, the market value of those investments would fall more than the market value of deposits, resulting in negative EVE sensitivity. FY2022 replaced this specific risk framing with generic language about funding mix and portfolio extension, without restating the negative-EVE mechanism.

**NII Sensitivity — SOFTENED (confidence 86%)**
The NII sensitivity numbers themselves tell the story. FY2021: +22.9% NII sensitivity at +200 basis points, +10.9% at +100 basis points. FY2022: +3.5% at +200 basis points, +1.8% at +100 basis points. The same disclosure framework, the same table structure, but numbers that show the bank's asset sensitivity had nearly evaporated.

The pattern across all four findings is consistent: SVB terminated their interest rate hedges, the rate environment moved sharply against them, their EVE exposure became catastrophic, and the disclosures that had previously quantified that exposure were removed or restructured so the numbers no longer appeared. The FY2022 10-K, filed 14 days before the bank run, contains the evidence of each of these steps.

---

## Design Decisions

**Why Claude judges instead of the embeddings.** Cosine similarity measures semantic proximity, not risk change. A disclosure that says "we are no longer exposed to X" is semantically very similar to one that says "we are exposed to X" — the embedding distance would be small, but the economic meaning is opposite. Only a language model reading the actual text can catch negation, softened qualifiers, and the removal of specific quantitative claims.

**Why two models.** Claude Sonnet is used for segmentation because it is fast and the task is mechanical — splitting text into units. Claude Opus is used for judgment because the classification task requires nuanced financial reasoning and the cost of a wrong call (missing a REMOVED that matters) is higher than the cost of a slow one.

**Why pre-computed cache.** The pipeline takes approximately five minutes end-to-end for a new ticker. A live demo cannot afford that latency. All three demo datasets (SIVB, PTON, META) are pre-computed and served instantly from JSON files.

**Why Item 1A and Item 7A specifically.** Item 1A (Risk Factors) is the primary qualitative risk disclosure. Item 7A (Quantitative and Qualitative Disclosures About Market Risk) is the primary quantitative one. Together they represent the two most information-dense risk sections of a 10-K. The SVB signal is in 7A — a purely qualitative scan would have found softenings but would have missed the EVE table removal entirely.

---

## Pre-Computed Demos

Three analyses are included in the repository:

- **SIVB (SVB Financial Group)** — FY2021 vs FY2022. The headline demo. 4 REMOVED, 4 SOFTENED, 2 ABSORBED, 1 REWORDED, 5 RETAINED.
- **PTON (Peloton Interactive)** — FY2021 vs FY2022. A growth-to-distress transition.
- **META (Meta Platforms)** — FY2021 vs FY2022. A large-cap disclosure evolution during the metaverse pivot.

---

## What It Is Not

Unsaid surfaces changes in language. It does not make return predictions. It does not claim that every removed disclosure represents fraud or negligence — sometimes a disclosure is removed because the underlying risk genuinely resolved (e.g. Boston Private acquisition language disappearing after the integration completed). The tool flags the change and explains it. The judgment about whether that change is significant belongs to the analyst.

The confidence scores reflect Claude's uncertainty about the classification, not the materiality of the underlying risk. A REMOVED finding with 72% confidence may be more important than a SOFTENED finding with 90% confidence — the score only describes how certain the model is about which category applies.

---

## Academic Foundation

The project is grounded in "Lazy Prices" (Cohen, Malloy & Nguyen, 2020), which studied year-over-year textual changes in 10-K filings from 1995 to 2014. The paper found that firms making significant changes to their risk disclosures — particularly reductions in disclosure length and removal of specific risk language — subsequently underperformed the market. The effect was largest for small-cap firms and was not explained by known return factors. The paper's title refers to the finding that most firms, most of the time, barely change their disclosures at all — making the firms that do change stand out.