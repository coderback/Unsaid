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
2. **Item 7A: mostly not a bug, and mostly not fixable.** Three distinct
   populations, by median extracted length per issuer:

   | | issuers | |
   |---|---|---|
   | Stub - no standalone 7A exists | 38 (67%) | BAC=22 words, CMA=27, ASB=30 |
   | Plausible 7A | 14 (25%) | BANC, BOH, BOKF, CATY, COLB, FCNCA |
   | Over-capture - a real bug | 5 (9%) | C=44,098 words, FITB=38,849, TFC=26,387 |

   Two thirds of the universe cross-references market risk into MD&A. No
   extractor recovers a section that is not there; you would have to locate the
   market-risk discussion inside Item 7 (400-500k chars), which is a larger
   problem than the original. **The 7A thesis therefore caps at ~56 observations
   against the ~725 the power analysis requires - untestable on this universe at
   any extraction quality.** SVB is the exception that made it look otherwise: it
   had a real 7A with a real EVE table, which is why the demo works.

   The over-capture bug is fixed (a plausibility gate in `extract_section`, 250k
   chars for 1A and 200k for 7A). **Staged but inert** - it changed the extractor
   hash, so the text cache is stale and nothing takes effect until `08` re-runs
   (~4-5h). Its value is upstream: it stops 220k-457k-char blobs entering
   segmentation, which is where CFG's 1,499-unit pathology came from.

   The restricted 7A cut (44 pairs with a real 7A in both years, 36 with returns)
   gives +5.09% at 1M (t=1.46) on the quintile and +3.99% at 3M (t=1.78) on the
   median split. Nothing significant, and at n=36 nothing could be - but the
   magnitude survived dropping 84% of the pairs, and unlike Item 1A the median
   split did not collapse.

3. **SOFTENED is a definitional dispute, and the labeller is probably on the
   weaker side of it.** The crux set established the judge is *factually correct*
   in all ten disputed cases — Year-2 really does omit the specifics it names,
   verified against the text, with the surviving passage at cosine 0.74–0.90.
   The labeller called these RETAINED because the loss was illustrative; the
   judge called them SOFTENED because content was dropped.

   On reflection, three things favour the judge:

   - **Cohen et al. apply no materiality filter.** Their signal is change
     *magnitude* — cosine, Jaccard, edit distance — and they never ask whether a
     change was substantive. It reaches t=3.59 anyway. The labeller's reading
     imposes a judgement the literature does not use.
   - **This study's own data agrees.** Bag-of-words beat the LLM classifier on
     every cut, and bag-of-words has no concept of materiality — it counts
     changed words. If raw change predicts better than semantic classification,
     that supports "content dropped = signal" over "only material losses count".
   - **Risk-factor prose is lawyered.** Dropping a named standard the firm had
     been warning about is a decision, not an accident, and may be informative
     whether or not the abstract risk changed.

   **Therefore SOFTENED at 7–20% precision probably understates the judge**, since
   it was scored against a labeller applying a filter the literature rejects.
   Treat those figures as a lower bound.

   The counter-argument, which is why this is not settled: if SOFTENED means only
   "the text got shorter", it is a worse version of what bag-of-words computes for
   free, which undercuts the premise that semantic classification adds anything.

   Three prompt interventions targeted this. v2 (narrowing rule 5b) made things
   worse. v3 added a NARROWED class for same-risk-less-detail: it fired **once in
   60 units** and eight of the ten crux cases stayed SOFTENED — the judge
   understood the distinction and declined to apply it. v3 still wins on kappa,
   but because of its net-disclosure rule, not the split.

   **Do not resolve this by re-labelling.** Revising the labels to agree with the
   judge fits the labels to the model — the same circularity pointed the other
   way. Two legitimate routes remain: human adjudication of
   `gold/tasks.crux.json` (15 units, textual overlap precomputed per case), or
   the empirical one — re-judge the corpus under v3 and test whether SOFTENED and
   RETAINED units behave differently in the cross-section. The second needs no
   one's opinion and is the better argument for the re-ingest than "refine the
   score".

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

- **Judge prompt is v3.** Three versions scored on the same 60 units and the same
  persisted evidence, so the prompt was the only variable:

  | | kappa | agreement | SOFTENED | REMOVED |
  |---|---|---|---|---|
  | v1 | 0.363 | 52.7% | 7% | 50% |
  | v2 | 0.239 | 49.1% | 12% | 50% |
  | **v3** | **0.397** | **60.0%** | **20%** | **67%** |

  Noise floor is 93.3% self-agreement (kappa 0.901) across two runs on identical
  evidence, so these differences are real prompt effects, not sampling noise.
  v2 was reverted. v3 is adopted — but its gain comes from the net-disclosure
  rule, which fixed a verified error, **not** from the NARROWED split, which
  fired once in 60 units and failed on its own terms.
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
