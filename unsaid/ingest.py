"""
CLI entry point for the Unsaid ingest pipeline.
Usage:
    python -m unsaid.ingest --ticker SIVB --cik 0000719739 --years 2021 2022
    python -m unsaid.ingest --ticker PTON --years 2021 2022
"""
import argparse
import logging
import os
import sys

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


from typing import Optional, Callable

def run_pipeline(
    ticker: str | None,
    cik: str | None,
    year1: int,
    year2: int,
    force: bool = False,
    provider: str = "anthropic",
    model_judge: Optional[str] = None,
    model_segmenter: Optional[str] = None,
    api_key: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
    azure_api_version: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int, str, Optional[str]], None]] = None,
) -> str:
    """
    Full ingest pipeline:
    1. Fetch 10-K filings from EDGAR
    2. Extract Item 1A + 7A text
    3. Segment into disclosure units (Claude Sonnet or Azure Foundry model)
    4. Embed + align units (sentence-transformers)
    5. Judge each unit (Claude Opus or Azure Foundry model e.g. gpt-5.6-luna)
    6. Write JSON cache with model provenance
    Returns the path to the cache file.
    """
    from unsaid.fetcher import get_10k_filing
    from unsaid.extractor import extract_both_sections
    from unsaid.segmenter import segment_all_sections
    from unsaid.aligner import align_units
    from unsaid.judge import judge_all
    from unsaid.cache import write_cache, cache_exists
    from unsaid.llm import get_default_model

    effective_ticker = (ticker or cik or "UNKNOWN").upper()
    effective_judge = model_judge or get_default_model(provider, "judge")
    effective_segmenter = model_segmenter or get_default_model(provider, "segmenter")

    def report(step: str, pct: int, msg: str, details: Optional[str] = None):
        logger.info("[PROGRESS %d%%] [%s] %s", pct, step, msg)
        if progress_callback:
            progress_callback(step, pct, msg, details)

    if cache_exists(effective_ticker, year1, year2) and not force:
        logger.info(
            "Cache already exists for %s %d→%d. Use --force to rerun.",
            effective_ticker, year1, year2,
        )
        report("caching", 100, "Loaded existing cached analysis", f"Using pre-computed cache for {effective_ticker}")
        from unsaid.cache import _cache_path
        return _cache_path(effective_ticker, year1, year2)

    # ── Step 1: Fetch ──────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 1  Fetching 10-K filings from EDGAR")
    logger.info("=" * 60)
    report("fetching", 10, f"Fetching FY{year1} and FY{year2} 10-K filings from SEC EDGAR…")

    filing1, company_name = get_10k_filing(ticker=ticker, cik=cik, year=year1)
    filing2, _ = get_10k_filing(ticker=ticker, cik=cik, year=year2)

    logger.info("Company: %s", company_name)
    logger.info("FY%d filing: %s", year1, getattr(filing1, "accession_no", "?"))
    logger.info("FY%d filing: %s", year2, getattr(filing2, "accession_no", "?"))
    report("fetching", 25, f"Retrieved 10-Ks for {company_name} (FY{year1} & FY{year2})")

    # ── Step 2: Extract ────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 2  Extracting Item 1A and Item 7A")
    logger.info("=" * 60)
    report("extracting", 30, "Extracting Item 1A (Risk Factors) and Item 7A (Market Risk)…")

    sections1 = extract_both_sections(filing1)
    sections2 = extract_both_sections(filing2)

    for label in ("1A", "7A"):
        t1 = sections1.get(label)
        t2 = sections2.get(label)
        logger.info(
            "Item %s: FY%d=%d chars, FY%d=%d chars",
            label,
            year1, len(t1) if t1 else 0,
            year2, len(t2) if t2 else 0,
        )
        if not t1:
            logger.warning("Item %s missing from FY%d — judgements will be skipped.", label, year1)
        if not t2:
            logger.warning("Item %s missing from FY%d — Year-2 candidates unavailable.", label, year2)

    report("extracting", 40, "Extracted and cleaned prose & quantitative tables")

    # ── Step 3: Segment ────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 3  Segmenting disclosures via %s (%s)", provider, effective_segmenter)
    logger.info("=" * 60)
    report("segmenting", 45, f"Segmenting disclosures via {provider} ({effective_segmenter})…")

    units1 = segment_all_sections(
        sections1,
        provider=provider,
        model=effective_segmenter,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        azure_api_version=azure_api_version,
    )
    units2 = segment_all_sections(
        sections2,
        provider=provider,
        model=effective_segmenter,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        azure_api_version=azure_api_version,
    )

    logger.info("FY%d: %d units total", year1, len(units1))
    logger.info("FY%d: %d units total", year2, len(units2))

    if not units1:
        report("error", 45, "No Year-1 units extracted from filing. Cannot continue.")
        raise ValueError(f"No Year-1 units extracted from FY{year1} filing for {effective_ticker}.")

    report("segmenting", 55, f"Segmented {len(units1)} Year-1 units and {len(units2)} Year-2 units")

    # ── Step 4: Align ──────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 4  Embedding + aligning units")
    logger.info("=" * 60)
    report("aligning", 60, "Computing dense sentence embeddings and cosine candidate matrix…")

    candidates_per_y1, new_candidates = align_units(units1, units2)
    logger.info("New Year-2 candidates (orphans): %d", len(new_candidates))
    report("aligning", 65, f"Aligned units — {len(new_candidates)} Year-2 candidate NEW disclosures")

    # ── Step 5: Judge ──────────────────────────────────────────────────────
    total_units = len(units1)
    logger.info("=" * 60)
    logger.info("STEP 5  Judging %d Year-1 units + %d NEW candidates via %s (%s)",
                total_units, len(new_candidates), provider, effective_judge)
    logger.info("=" * 60)

    def on_judge_unit(curr: int, tot: int, title: str):
        pct = 65 + int((curr / max(tot, 1)) * 30)  # 65% to 95%
        report("judging", pct, f"Classifying risk shifts ({curr}/{tot}): {title[:40]}…", title)

    report("judging", 65, f"Evaluating {total_units} disclosure units with {provider} ({effective_judge}) judge…")
    changes = judge_all(
        units1,
        candidates_per_y1,
        new_candidates,
        year1,
        year2,
        provider=provider,
        model=effective_judge,
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        azure_api_version=azure_api_version,
        progress_callback=on_judge_unit,
    )

    # Print summary
    counts: dict = {}
    for c in changes:
        cls = c.get("classification", "?")
        counts[cls] = counts.get(cls, 0) + 1
    logger.info("Classification summary: %s", counts)
    report("judging", 95, f"Completed judgments: {counts}")

    # ── Step 6: Cache ──────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 6  Writing cache")
    logger.info("=" * 60)
    report("caching", 98, "Writing analysis result to local cache…")

    path = write_cache(
        effective_ticker,
        company_name,
        year1,
        year2,
        changes,
        model_provider=provider,
        model_judge=effective_judge,
        model_segmenter=effective_segmenter,
    )
    logger.info("Done! Cache written to: %s", path)
    report("completed", 100, f"Analysis complete for {effective_ticker} (FY{year1} → FY{year2})", path)
    return path


def main():
    parser = argparse.ArgumentParser(
        description="Unsaid ingest pipeline — fetch, compare, and cache 10-K disclosure changes."
    )
    parser.add_argument("--ticker", help="Company ticker symbol (e.g. SIVB, PTON)")
    parser.add_argument("--cik", help="SEC CIK number (e.g. 0000719739); use for delisted companies")
    parser.add_argument(
        "--years", nargs=2, type=int, metavar=("YEAR1", "YEAR2"),
        required=True,
        help="Two fiscal years to compare (e.g. --years 2021 2022)"
    )
    parser.add_argument(
        "--provider", default="anthropic", choices=["anthropic", "azure_foundry", "openai"],
        help="Model provider (anthropic, azure_foundry, openai)"
    )
    parser.add_argument("--model-judge", help="Model name for judge (e.g. gpt-5.6-luna or claude-opus-4-8)")
    parser.add_argument("--model-segmenter", help="Model name for segmenter (e.g. gpt-5.6-luna or claude-sonnet-4-6)")
    parser.add_argument("--azure-endpoint", help="Azure AI Foundry endpoint URL")
    parser.add_argument("--azure-api-version", help="Azure API version")
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run even if a cache file already exists"
    )

    args = parser.parse_args()

    if not args.ticker and not args.cik:
        parser.error("Must supply at least one of --ticker or --cik")

    year1, year2 = args.years[0], args.years[1]
    if year1 >= year2:
        parser.error("YEAR1 must be less than YEAR2")

    run_pipeline(
        ticker=args.ticker,
        cik=args.cik,
        year1=year1,
        year2=year2,
        force=args.force,
        provider=args.provider,
        model_judge=args.model_judge,
        model_segmenter=args.model_segmenter,
        azure_endpoint=args.azure_endpoint,
        azure_api_version=args.azure_api_version,
    )


if __name__ == "__main__":
    main()

