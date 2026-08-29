"""
Batch SEC Ingestion & Disclosure Analysis Runner for Banking Universe.

Usage:
    python research/banking_study/01_batch_ingest.py --cohort crisis_distressed
    python research/banking_study/01_batch_ingest.py --tickers SIVB,FRC,WAL --provider azure_foundry
    python research/banking_study/01_batch_ingest.py --all --provider anthropic
"""
import os
import sys
import json
import time
import argparse
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Auto-load .env from project root if present
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

from unsaid.ingest import run_pipeline
from unsaid.cache import read_cache
from unsaid.version import pipeline_fingerprint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("batch_ingest")

SCRIPT_DIR = Path(__file__).resolve().parent
UNIVERSE_FILE = SCRIPT_DIR / "universe.json"
DATA_DIR = SCRIPT_DIR / "data"
MANIFEST_FILE = DATA_DIR / "ingest_manifest.json"


def assert_unique_tickers(universe) -> None:
    """
    Fail fast if two entries would collide on the result key.

    A duplicate is never harmless: the pair count silently drops, half the work
    is discarded, and if the duplicates carry different CIKs the surviving record
    depends on thread scheduling.
    """
    import collections
    counts = collections.Counter(e["ticker"].upper() for e in universe)
    dupes = {t: n for t, n in counts.items() if n > 1}
    if dupes:
        detail = []
        for t in sorted(dupes):
            ciks = sorted({(e.get("cik") or "?") for e in universe if e["ticker"].upper() == t})
            detail.append("%s x%d (CIKs: %s)" % (t, dupes[t], ", ".join(ciks)))
        raise SystemExit(
            "Universe contains duplicate tickers, which collide on the "
            "{ticker}_{year1}_{year2} result key and silently overwrite each other: "
            + "; ".join(detail)
            + ". Remove the duplicates before running."
        )


def load_universe() -> Dict[str, Any]:
    with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_manifest() -> Dict[str, Any]:
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "results": {}}


# Serialises manifest mutation and the write itself, so a checkpoint from one
# worker cannot interleave with another and truncate the file.
_MANIFEST_LOCK = threading.Lock()


def save_manifest(manifest: Dict[str, Any]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    os.replace(tmp, MANIFEST_FILE)  # atomic: a kill mid-write cannot corrupt it


# A pair needs at least this many Year-1 disclosure units for a per-unit ratio to
# mean anything; below it the denominator is too small and the score is noise.
MIN_Y1_UNITS = 10


def compute_removal_score_raw(counts: Dict[str, int]) -> float:
    """
    Unnormalised weighted severity:
    2.0 * REMOVED + 1.0 * SOFTENED + 1.0 * ABSORBED - 0.5 * NEW

    Retained for reference only. This scales with how much text the extractor
    happened to pull, so it is NOT comparable across institutions -- use
    compute_removal_score() for anything cross-sectional.
    """
    removed = counts.get("REMOVED", 0)
    softened = counts.get("SOFTENED", 0)
    absorbed = counts.get("ABSORBED", 0)
    new_disc = counts.get("NEW", 0)
    return round((2.0 * removed) + (1.0 * softened) + (1.0 * absorbed) - (0.5 * new_disc), 2)


def compute_removal_score(counts: Dict[str, int], total_disclosures: int):
    """
    Removal severity per Year-1 disclosure unit.

    The raw weighted count scales with document length and extraction yield -- a
    filing segmented into 1,499 units will outscore one segmented into 114 on
    volume alone, which measures the extractor rather than the issuer. Dividing by
    the Year-1 unit count makes the score comparable across institutions.

    Returns None when the pair is too thin or too asymmetric to score honestly:
      - fewer than MIN_Y1_UNITS Year-1 units: denominator too small to be stable
      - more NEW units than Year-1 units: Year-1 extraction substantially failed,
        so the year-over-year comparison is not meaningful
      - no Year-1 unit matched anything in Year-2: every unit judged REMOVED with
        nothing retained, reworded, softened or absorbed means Year-2 extraction
        returned nothing, not that the issuer deleted its entire risk section
    """
    new_disc = counts.get("NEW", 0)
    y1_units = max(int(total_disclosures) - new_disc, 0)

    if y1_units < MIN_Y1_UNITS or new_disc > y1_units:
        return None

    matched = (
        counts.get("RETAINED", 0)
        + counts.get("REWORDED", 0)
        + counts.get("SOFTENED", 0)
        + counts.get("ABSORBED", 0)
    )
    if matched == 0:
        return None

    return round(compute_removal_score_raw(counts) / y1_units, 4)


def process_pair(
    ticker: str,
    cik: Optional[str],
    name: str,
    cohort: str,
    year1: int,
    year2: int,
    provider: str,
    model_judge: Optional[str],
    model_segmenter: Optional[str],
    azure_endpoint: Optional[str],
    api_key: Optional[str],
    force: bool = False,
) -> Dict[str, Any]:
    """Execute ingestion and diffing pipeline for a single consecutive year-pair."""
    pair_key = f"{ticker.upper()}_{year1}_{year2}"

    # Check cache first
    cached = read_cache(ticker, year1, year2) if not force else None
    if cached and not force:
        logger.info(f"[{ticker}] FY{year1}→FY{year2}: Found in cache, skipping execution.")
        analysis = cached
    else:
        logger.info(f"[{ticker}] FY{year1}→FY{year2}: Starting pipeline run via {provider}...")
        try:
            res_path = run_pipeline(
                ticker=ticker,
                year1=year1,
                year2=year2,
                cik=cik,
                provider=provider,
                model_judge=model_judge,
                model_segmenter=model_segmenter,
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                force=force,
            )
            analysis = read_cache(ticker, year1, year2) or {}
        except Exception as e:
            logger.error(f"[{ticker}] FY{year1}→FY{year2}: Ingestion failed: {e}")
            return {
                "ticker": ticker,
                "cik": cik,
                "name": name,
                "cohort": cohort,
                "year1": year1,
                "year2": year2,
                "status": "failed",
                "error": str(e),
            }

    if isinstance(analysis, str):
        analysis = read_cache(ticker, year1, year2) or {}

    counts = analysis.get("summary_counts", {})
    changes = analysis.get("changes", [])

    # Count Item 7A specific removals
    item7a_changes = [c for c in changes if "7A" in c.get("section", "")]
    item7a_removed = sum(1 for c in item7a_changes if c.get("classification") == "REMOVED")
    item7a_softened = sum(1 for c in item7a_changes if c.get("classification") == "SOFTENED")

    total_disclosures = len(changes)
    score = compute_removal_score(counts, total_disclosures)
    score_raw = compute_removal_score_raw(counts)

    return {
        "ticker": ticker,
        "cik": cik,
        "name": name,
        "cohort": cohort,
        "year1": year1,
        "year2": year2,
        "status": "completed",
        "model_provider": analysis.get("model_provider", provider),
        "model_judge": analysis.get("model_judge"),
        "total_disclosures": total_disclosures,
        "counts": counts,
        "item7a_removed": item7a_removed,
        "item7a_softened": item7a_softened,
        "removal_score": score,
        "removal_score_raw": score_raw,
        "embed_backend": analysis.get("embed_backend"),
        "pipeline_version": analysis.get("pipeline_version"),
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main():
    parser = argparse.ArgumentParser(description="Batch SEC Ingest Runner for Banking Universe")
    cohort_map = {
        "crisis_distressed": "crisis_distressed",
        "crisis": "crisis_distressed",
        "regional_midcap": "regional_midcap",
        "regional": "regional_midcap",
        "megabank_control": "megabank_control",
        "megabanks": "megabank_control",
        "megabank": "megabank_control",
        "all": "all",
    }
    parser.add_argument("--cohort", choices=list(cohort_map.keys()), default="all", help="Target cohort to process")
    parser.add_argument("--tickers", type=str, help="Comma-separated list of specific tickers (e.g. SIVB,FRC,WAL)")
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "azure_foundry", "openai"], help="Model inference provider")
    parser.add_argument("--model-judge", type=str, help="Judge model override")
    parser.add_argument("--model-segmenter", type=str, help="Segmenter model override")
    parser.add_argument("--azure-endpoint", type=str, help="Azure AI Foundry endpoint URL")
    parser.add_argument("--api-key", type=str, help="Optional direct API key")
    parser.add_argument("--force", action="store_true", help="Force re-run even if cached")
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Pairs to process concurrently. The bottleneck is API latency, not CPU; "
             "4-8 is typically safe. SEC fetches stay rate-limited regardless.",
    )
    parser.add_argument(
        "--allow-tfidf", action="store_true",
        help="Proceed even if dense embeddings failed to load. Off by default so a "
             "long ingest cannot silently run on bag-of-words.",
    )
    parser.add_argument(
        "--freeze", action="store_true",
        help="Re-ingest under the CURRENT pipeline version, skipping pairs already "
             "ingested under it. Unlike --force this is resumable: a killed run "
             "resumes instead of restarting. Use this to rebuild a homogeneous corpus.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan without running LLM pipeline")
    args = parser.parse_args()

    target_cohort = cohort_map.get(args.cohort, args.cohort)

    universe_data = load_universe()
    universe = universe_data["universe"]
    assert_unique_tickers(universe)
    pairs = universe_data["comparison_pairs"]

    # Filter universe
    if args.tickers:
        selected_tickers = {t.strip().upper() for t in args.tickers.split(",")}
        targets = [u for u in universe if u["ticker"].upper() in selected_tickers]
    elif target_cohort != "all":
        targets = [u for u in universe if u["cohort"] == target_cohort]
    else:
        targets = universe

    total_tasks = len(targets) * len(pairs)
    logger.info(f"Targeting {len(targets)} institutions across {len(pairs)} year-pairs = {total_tasks} total pairs.")

    if args.dry_run:
        print("\n--- DRY RUN PLAN ---")
        for u in targets:
            print(f"[{u['ticker']}] {u['name']} (CIK: {u['cik']}, Cohort: {u['cohort']})")
            for p in pairs:
                print(f"  |-- FY{p['year1']} -> FY{p['year2']}")
        print(f"Total tasks: {total_tasks}\n")
        return

    manifest = load_manifest()
    results = manifest.setdefault("results", {})

    # Resolve the embedding backend up front. It is part of the fingerprint, and
    # eager loading means a silent degrade to TF-IDF surfaces now rather than
    # after hours of ingestion.
    from unsaid.aligner import _get_model, get_active_backend
    _get_model()
    backend = get_active_backend()
    # Resolve model defaults BEFORE fingerprinting. run_pipeline stamps the cache
    # using resolved names, so hashing the literal None here would produce a
    # version that can never match what was recorded -- and --freeze would then
    # re-ingest the whole corpus on every restart instead of resuming.
    from unsaid.llm import get_default_model
    eff_judge = args.model_judge or get_default_model(args.provider, "judge")
    eff_segmenter = args.model_segmenter or get_default_model(args.provider, "segmenter")
    current_version = pipeline_fingerprint(
        args.provider, eff_judge, eff_segmenter, backend,
    )
    manifest["pipeline_version"] = current_version
    logger.info("Pipeline version: %s (embed backend: %s)", current_version, backend)
    if backend == "tfidf":
        msg = (
            "Dense embeddings unavailable - this run would use TF-IDF bag-of-words. "
            "That is not a cosmetic difference: on ZION the same filings yielded 28% "
            "and 11% spurious NEW units under TF-IDF versus 0% under mpnet, because "
            "the recall thresholds are calibrated for dense cosines. Refusing to spend "
            "a long ingest on it. Pass --allow-tfidf to override deliberately."
        )
        if not args.allow_tfidf:
            logger.error(msg)
            raise SystemExit(2)
        logger.warning("OVERRIDDEN: %s", msg)

    if args.freeze:
        stale = [
            k for k, v in results.items()
            if v.get("status") == "completed" and v.get("pipeline_version") != current_version
        ]
        logger.info(
            "Freeze mode: %d pair(s) already at this version, %d to (re)ingest.",
            sum(1 for v in results.values() if v.get("pipeline_version") == current_version),
            len(stale) + sum(1 for v in results.values() if v.get("status") != "completed"),
        )

    completed_count = 0
    failed_count = 0

    # Flatten to a task list so the pool can saturate regardless of pair sizes,
    # which vary by more than an order of magnitude.
    tasks = []
    for inst in targets:
        for p in pairs:
            pk = f"{inst['ticker']}_{p['year1']}_{p['year2']}"
            prior = results.get(pk)
            done = prior and prior.get("status") == "completed"

            if args.freeze:
                # Resumable: skip only what this exact pipeline version produced.
                if done and prior.get("pipeline_version") == current_version:
                    continue
            elif not args.force and done:
                continue

            tasks.append((inst, p, pk))

    logger.info("Dispatching %d pair(s) across %d worker(s).", len(tasks), args.workers)

    def run_task(task):
        inst, p, pk = task
        # In freeze mode every dispatched pair must actually re-run, so bypass the
        # cache short-circuit even though --force was not passed.
        return pk, process_pair(
            ticker=inst["ticker"],
            cik=inst.get("cik"),
            name=inst["name"],
            cohort=inst["cohort"],
            year1=p["year1"],
            year2=p["year2"],
            provider=args.provider,
            model_judge=args.model_judge,
            model_segmenter=args.model_segmenter,
            azure_endpoint=args.azure_endpoint,
            api_key=args.api_key,
            force=args.force or args.freeze,
        )

    done_n = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(run_task, t): t for t in tasks}
        for fut in as_completed(futures):
            inst, p, pk = futures[fut]
            try:
                _, res = fut.result()
            except Exception as e:
                res = {
                    "ticker": inst["ticker"], "cik": inst.get("cik"), "name": inst["name"],
                    "cohort": inst["cohort"], "year1": p["year1"], "year2": p["year2"],
                    "status": "failed", "error": f"{type(e).__name__}: {e}",
                }

            with _MANIFEST_LOCK:
                res.setdefault("pipeline_version", current_version)
                results[pk] = res
                save_manifest(manifest)

            done_n += 1
            if res.get("status") == "completed":
                completed_count += 1
                sd = res.get("removal_score")
                sd = f"{sd:.3f}" if sd is not None else "n/a (unreliable)"
                logger.info(
                    "[%d/%d] OK   %-18s score/unit=%-8s removed=%d",
                    done_n, len(tasks), pk, sd, res.get("counts", {}).get("REMOVED", 0),
                )
            else:
                failed_count += 1
                logger.warning("[%d/%d] FAIL %-18s %s", done_n, len(tasks), pk, res.get("error"))

    logger.info("\n========================================================")
    logger.info(f"Batch Ingestion Complete: {completed_count} succeeded, {failed_count} failed.")
    logger.info(f"Manifest saved to: {MANIFEST_FILE}")
    logger.info("========================================================\n")


if __name__ == "__main__":
    main()
