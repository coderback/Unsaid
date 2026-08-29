# Working Notes

Operational state of the pipeline and the banking study. Updated 27 Aug 2026.

Generated reports in `research/banking_study/results/` are outputs and get
overwritten on every run — this file is the durable record of decisions,
gotchas, and what is still broken.

---

## Status

**Banking study: null result, published.** No signal survives correction for the
24 specifications examined (family-wise `p = 0.131`). See
`results/null_writeup.html`. The study is underpowered by roughly 3× against the
effect it targets, so this is a weak null — it cannot distinguish "no effect"
from "too noisy to see one."

**Do not run the full re-ingest yet.** Nothing measured so far suggests either
signal would clear the bar at n=224. The binding constraint is sample size, not
code quality, and re-ingesting the same 228 pairs does not change it.

---

## Corpus

| | |
|---|---|
| Universe | 57 institutions (was 60 — three were duplicate tickers) |
| Pairs possible | 228 |
| LLM completed | 224 |
| Similarity scored | 224 |
| Unavailable | 4 — SIVB FY23, SI FY22/23, PACW FY23 (seizure, liquidation, merger) |
| Text cache | 241 filings, extraction already done |

The 4 unavailable pairs are filings that do not exist. They are not failures.

**Corpus is NOT homogeneous.** The 224 LLM results were ingested across five days
while seven pipeline commits landed, so cohort is confounded with pipeline
version. Only the four ZION pairs carry the current fingerprint
(`f0bd0681fca5`). Any cross-sectional claim over the LLM corpus inherits this.
The similarity corpus (224 pairs) is clean — single run, one code version.

---

## Fixed this session

Pipeline
- Dense embeddings never loaded — a stale HF token made the hub answer 401 for an
  optional file, and the loader silently fell back to TF-IDF. Now loads mpnet,
  and a TF-IDF fallback **aborts** the run unless `--allow-tfidf`.
- `embed_backend` and `pipeline_version` are recorded in every cache payload.
- Judge and segmenter fail loudly: `JudgeFailureRateExceeded` past a 10% fallback
  rate; config/auth errors propagate instead of returning `[]`.
- Recall thresholds are backend-specific (mpnet and TF-IDF cosines are not on the
  same scale).
- Every EDGAR request goes through `fetcher.edgar_call()` — previously ~13 of 14
  requests per pair bypassed the rate limiter entirely.
- Extractor selects the first *bounded* section slice rather than blindly taking
  the last heading match.
- Filing-level text cache keyed on accession + extractor fingerprint. 59.9s cold,
  0.00s warm.

Study
- Filing-date alignment (`fiscal_year` vs `year` key mismatch) — the look-ahead
  control had never engaged; every row used a hardcoded Feb-28 date.
- Terminal returns only fill horizons that actually span the failure.
- Guards against dead and reassigned price series.
- `--force` now propagates into `run_pipeline` (it never had).
- `removal_score` normalised per Year-1 unit, with three reliability guards.
- Backtest conclusions derived from data, not string literals.
- Universe deduplicated; both runners abort on duplicate tickers.

---

## Open issues, ranked

1. **Sample size.** ~725 observations needed to detect the published effect;
   224 available. And US banks nearly all file in February, so those 224 cluster
   into ~4 independent periods. Extending to FY2010–2023 is the only change that
   moves this.
2. **Item 7A is unusable.** Extracted length ranges 20 → 52,602 words, bimodal
   between cross-reference stubs and over-captures. This is the section the
   thesis depends on. Many banks have no standalone 7A at all — they
   cross-reference into MD&A, so Item 7 would have to be extracted instead. That
   is a design decision, not a bug fix.
3. **SOFTENED precision ~7%.** Measured against blind labels. It carries equal
   weight to ABSORBED in `removal_score`, so a large share of the signal mass is
   noise. Two prompt interventions failed to move it, which suggests the cause is
   not in those rules. **Human labels on `gold/tasks.crux.json` (15 units, ~22
   min) would settle whether this is real or an artifact of the model labeller.**
4. **No M&A control.** The paper excludes merger windows explicitly. Mergers
   dominate the top removal scores here (CFG, TFC, FCNCA) and were never
   controlled for.
5. **Returns are raw excess over KRE**, not factor-adjusted alpha. The paper
   reports value-weighted FF3 and 5-factor alphas.
6. **Segmenter is non-deterministic.** No provider in the stack accepts
   `temperature=0` — Azure Foundry and Anthropic both reject it. Two runs over the
   same filing pair gave 108 vs 112 units with 2 of 31 titles matching. The judge
   is stable at its default (93.3% self-agreement, kappa 0.901); the segmenter's
   variance is unmeasured.
7. **`gold/labels.model.json` are model labels, not ground truth.** Everything
   scored against them is inter-model agreement — a reliability check, not a
   validity check.

---

## Operational gotchas

**Worker counts differ by stage.** Extraction is CPU-bound Python, so the GIL
serialises it while memory scales linearly: ~238 MB and ~60s per filing. On a
16 GB machine `--workers 8` is an OOM kill and buys no speed. Judging is
I/O-bound and does scale.

```
extraction-heavy (08, fetch/extract)   --workers 2
LLM-heavy (01 judging)                 --workers 8
```

**Laptop sleep drops in-flight fetches.** Confirmed: two pairs failed that
extracted fine on retry. The failure mode is clean — `os.replace` on state
writes, and the text cache only stores a filing when something was recovered —
so you lose only what was in flight. `powercfg /change standby-timeout-ac 0`
before long runs.

**Everything is resumable.** `08` skips recorded pairs; `01 --freeze` skips pairs
already at the current pipeline version. `--force` is not resumable and restarts
from zero — use `--freeze` for re-ingests.

**The text cache is warm for all 241 filings**, so any re-ingest skips extraction
(~8h saved) as long as `extractor.py` is unchanged. Editing it invalidates the
cache by design.

---

## Decisions and why

- **Kept the v1 judge prompt.** A narrowed rule 5b (v2) scored worse against
  labels — kappa 0.363 → 0.239, replicated at 0.198 — by collapsing ABSORBED
  from 7 correct to 1 and dropping RETAINED precision 94% → 73%. Noise floor is
  93.3% agreement, so that degradation is a real prompt effect.
- **Item 1A + 7A, not full documents,** for the similarity baseline. Departs from
  the paper but isolates the variable under test rather than confounding it with
  section selection.
- **Universe left at 57** rather than backfilling three replacements. Whether to
  add banks is a study-design call.
- **`.mcp.json` untracked** — local PyCharm config with a machine-specific port.

---

## Claims to stop making

- ~~"First directional classification of disclosure changes."~~ The paper
  sentiment-signs changes, decomposes by section, and separates positive from
  negative. Verified in the source. What survives is a 6-way taxonomy at
  disclosure-unit level vs positive/negative at document level.
- ~~"60 institutions, 240 pairs."~~ 57 and 228.
- ~~"Claude Opus judge."~~ The corpus was judged by `gpt-5.6-luna` on Azure.
- The 86% negative-sentiment figure **does** check out — verified verbatim.
