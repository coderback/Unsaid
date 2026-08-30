# Extension Run: FY2019–2025 under one pipeline version

Single unattended job that extends the study forward two years, activates the
staged extractor gate, and produces an out-of-sample test of the only result that
ever cleared significance.

Status: **scoped and staged.** Universe extended; extraction not yet run.

Availability confirmed against EDGAR for all 57 banks:

| Pair | Banks | Returns |
|---|---|---|
| FY2019->20 | 57 | complete |
| FY2020->21 | 57 | complete |
| FY2021->22 | 55 | complete |
| FY2022->23 | 53 | complete |
| **FY2023->24** | **53** | **complete - the holdout** |
| FY2024->25 | 50 | 1M/3M/6M only |

325 pairs available against 222 in use: **103 net new**. Attrition is banks that
ceased to exist (SIVB after FY2021, Silvergate after FY2020, PacWest after
FY2022), not extraction failure.

---

## Why one run rather than three

Three separate needs collapse into a single re-extraction:

1. **The extractor gate is staged and inert.** It changed the extractor hash
   (`ccdb69eb5c → 29c8f6adb9`), so all 245 cached filings are stale and the gate
   has no effect until extraction re-runs.
2. **The corpus spans multiple pipeline versions.** The 224 LLM results were
   ingested across five days while seven commits landed; cohort is confounded
   with code version.
3. **FY2024 and FY2025 filings exist and are unused.** `universe.json` was
   written 2026-08-21, after both were filed. Stopping at FY2023 was arbitrary.

Doing these separately means extracting the same filings two or three times and
leaving a corpus with mixed fingerprints in between — the exact defect this
branch removed. One run, one fingerprint.

---

## What changes

### `universe.json` — two new comparison pairs

```json
{"year1": 2023, "year2": 2024},
{"year1": 2024, "year2": 2025}
```

Takes 4 pairs/bank to 6. Ceiling rises 222 in use → **325 available** (confirmed above).

### Nothing else

`08_similarity_baseline.py`, `02_fetch_market_data.py` and `09_compare_signals.py`
read `comparison_pairs` from the universe and need no edits. `assert_unique_tickers`
already guards the duplicate-key failure. The gate is already committed.

---

## Return completeness

Measured from today (2026-08-30):

| Pair | Filed | Elapsed | Usable horizons |
|---|---|---|---|
| FY2023→24 | ~2025-02-14 | 562 d | 1M, 3M, 6M, **12M** |
| FY2024→25 | ~2026-02-13 | 198 d | 1M, 3M, 6M |

**FY2024→25 has no 12M return until Feb 2027.** Since the result under test lives
at 12M, the clean holdout is FY2023→24 alone — 53 observations, confirmed against EDGAR. Report FY2024→25 at shorter horizons only, and never
silently pool a partial 12M into a full-sample figure.

---

## The holdout test

This is the point of the run.

Every number in the study so far — including Item 1A cosine at 12M, `+7.98%`,
`t=2.48` — came from FY2019–2023. That result failed multiplicity correction
(family-wise `p = 0.131`, i.e. 13% of random draws produce a `|t|` that large
somewhere among 24 specifications). Correction can say the result is consistent
with chance; it cannot say whether it is real.

FY2023→24 is data no specification search has touched. Running **one
pre-specified test** on it answers what correction cannot:

- **Signal**: `sim_1a` (Item 1A cosine similarity)
- **Horizon**: 12M
- **Direction**: long the quiet filers, short the changers
- **Cut**: median split (at n=53 a quintile is ~10 per side; report the quintile
  too, but the median split is the honest read)
- **Decided in advance.** No other specification is run on this pair. Searching
  the holdout destroys what makes it a holdout.

Interpretation, also fixed in advance:

| Outcome | Reading |
|---|---|
| Positive, similar magnitude | Genuine out-of-sample replication. Strongest evidence in the project. |
| Near zero | In-sample result was a specification artifact. Null settles cleanly. |
| Negative | Same conclusion as near-zero; direction was not stable. |

---

## Execution

```bash
# 1. availability refresh  -- DONE, data/filing_dates_full.json
# 2. universe extended     -- DONE

# 3. extraction + similarity, single fingerprint
python research/banking_study/08_similarity_baseline.py --all --workers 2

# 4. market returns for the new pairs
python research/banking_study/02_fetch_market_data.py

# 5. comparison + holdout
python research/banking_study/09_compare_signals.py
```

`--workers 2`, not 8. Extraction is CPU-bound and ~238 MB per filing; on a 16 GB
machine 8 workers is an OOM kill and buys no speed because the GIL serialises the
work anyway.

**Cost**: 383 filings × ~60 s ≈ **6 hours**, unattended and resumable, **no API
spend**. Disable sleep first (`powercfg /change standby-timeout-ac 0`) — laptop
suspend drops in-flight fetches, though the failure mode is clean.

**No LLM re-ingest.** The bag-of-words baseline answers the holdout question, and
it is the measure that outperformed the LLM classifier on every cut. Re-judging
228+ pairs is a separate ~15 h decision that should wait on this result.

---

## What this run does NOT fix

- **Item 7A stays untestable.** 67% of the universe cross-references market risk
  into MD&A and has no standalone 7A. More years does not create sections that
  are not filed.
- **The LLM corpus stays version-mixed.** Only a full re-ingest fixes that.
- **Detection power stays short.** 325 pairs gives MDE ≈ 5.1% against a 3.5%
  effect. Reaching detection needs backward extension to FY2010 (855 pairs,
  MDE 3.2%, ~13 h). That is the *next* decision, and it should be informed by
  the holdout result rather than taken now.

---

## Verification

- Every result carries one `pipeline_version`; no mixed fingerprints.
- Pair count matches expectation from `filing_dates_full.json`; every shortfall
  is a bank with genuinely no filing for that year, not an extraction failure.
- Over-capture issuers (C, CFG, FITB, RF, TFC) now show either a plausible 7A or
  `None`, never a 200k+ char section.
- FY2024→25 rows carry no 12M return.
- The holdout number is reported once, from the pre-specified test above.
