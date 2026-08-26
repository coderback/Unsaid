"""
Gold Set Builder — persist judge inputs so classifications can be validated.

The cache stores only the judge's own output (its extracted quotes and its
reasoning). Hand-labelling from that is circular: you would be grading the judge
using its own summary of the evidence. To evaluate it honestly a human must see
exactly what the judge saw — the Year-1 disclosure unit and the Year-2 candidates
retrieved for it — and nothing else.

This script runs extract -> segment -> align -> judge over a set of filing pairs
and persists all of it. Because the inputs are saved, a later prompt change can
be re-scored against the same evidence without re-segmenting, which also removes
resegmentation as a confound when comparing two prompts.

Resumable: completed pairs are skipped, and judging checkpoints after each unit.

Usage:
    python research/banking_study/04_build_gold_set.py --pairs SI_2019_2020,BAC_2021_2022
    python research/banking_study/04_build_gold_set.py --pairs ... --judge-only
"""
import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gold_build")

SCRIPT_DIR = Path(__file__).resolve().parent
UNIVERSE_FILE = SCRIPT_DIR / "universe.json"
GOLD_DIR = SCRIPT_DIR / "gold"
INPUTS_DIR = GOLD_DIR / "inputs"


def load_universe_index() -> Dict[str, Dict[str, Any]]:
    with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {u["ticker"].upper(): u for u in data["universe"]}


def parse_pair(pair_key: str):
    ticker, y1, y2 = pair_key.rsplit("_", 2)
    return ticker.upper(), int(y1), int(y2)


def build_pair(pair_key: str, provider: str, model_judge: Optional[str],
               model_segmenter: Optional[str], azure_endpoint: Optional[str],
               api_key: Optional[str]) -> Dict[str, Any]:
    """Run the pipeline for one pair, persisting units, candidates and predictions."""
    from unsaid.fetcher import get_10k_filing
    from unsaid.extractor import extract_both_sections
    from unsaid.segmenter import segment_all_sections
    from unsaid.aligner import align_units, get_active_backend, get_thresholds
    from unsaid.judge import judge_unit

    ticker, year1, year2 = parse_pair(pair_key)
    universe = load_universe_index()
    cik = (universe.get(ticker) or {}).get("cik")

    out_path = INPUTS_DIR / f"{pair_key}.json"
    state: Dict[str, Any] = {}
    if out_path.exists():
        try:
            state = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            state = {}

    def save():
        INPUTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ---- stage 1: units + candidates (skipped if already persisted) ----------
    if not state.get("tasks"):
        logger.info("[%s] fetching and extracting…", pair_key)
        filing1, company = get_10k_filing(ticker=ticker, cik=cik, year=year1)
        filing2, _ = get_10k_filing(ticker=ticker, cik=cik, year=year2)
        sections1 = extract_both_sections(filing1)
        sections2 = extract_both_sections(filing2)

        logger.info("[%s] segmenting…", pair_key)
        units1 = segment_all_sections(
            sections1, provider=provider, model=model_segmenter,
            api_key=api_key, azure_endpoint=azure_endpoint,
        )
        units2 = segment_all_sections(
            sections2, provider=provider, model=model_segmenter,
            api_key=api_key, azure_endpoint=azure_endpoint,
        )
        if not units1:
            raise ValueError(f"[{pair_key}] no Year-1 units extracted")

        logger.info("[%s] aligning %d x %d units…", pair_key, len(units1), len(units2))
        candidates_per_y1, _new = align_units(units1, units2)
        cut = get_thresholds()["candidate"]

        tasks = []
        for unit, cands in zip(units1, candidates_per_y1):
            # Persist exactly the candidate set the judge is given, post-filter.
            kept = [
                {
                    "title": c.get("title"),
                    "text": c.get("text"),
                    "section": c.get("section"),
                    "similarity": round(float(sim), 4),
                }
                for c, sim in cands if sim >= cut
            ]
            tasks.append({
                "unit_id": unit.get("id"),
                "unit": {
                    "title": unit.get("title"),
                    "text": unit.get("text"),
                    "section": unit.get("section"),
                },
                "candidates": kept,
                "prediction": None,
            })

        state = {
            "pair_key": pair_key,
            "ticker": ticker,
            "company_name": company,
            "year1": year1,
            "year2": year2,
            "embed_backend": get_active_backend(),
            "candidate_cut": cut,
            "provider": provider,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tasks": tasks,
        }
        save()
        logger.info("[%s] persisted %d judge inputs", pair_key, len(tasks))

    # ---- stage 2: predictions (checkpointed per unit) ------------------------
    tasks = state["tasks"]
    todo = [t for t in tasks if not t.get("prediction")]
    logger.info("[%s] judging %d/%d remaining units…", pair_key, len(todo), len(tasks))

    for i, task in enumerate(tasks):
        if task.get("prediction"):
            continue
        cands = [
            ({"title": c["title"], "text": c["text"], "section": c["section"]},
             c["similarity"])
            for c in task["candidates"]
        ]
        unit = dict(task["unit"])
        unit["id"] = task["unit_id"]
        result = judge_unit(
            unit, cands, state["year1"], state["year2"],
            provider=provider, model=model_judge, api_key=api_key,
            azure_endpoint=azure_endpoint,
        )
        task["prediction"] = {
            "classification": result.get("classification"),
            "confidence": result.get("confidence"),
            "reasoning": result.get("reasoning"),
            "year1_quote": result.get("year1_quote"),
            "year2_quote_or_null": result.get("year2_quote_or_null"),
            "judge_failed": bool(result.get("judge_failed")),
        }
        if (i + 1) % 5 == 0 or i == len(tasks) - 1:
            save()
            logger.info("[%s]   judged %d/%d", pair_key, i + 1, len(tasks))

    state["judged_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    save()
    return state


def main():
    ap = argparse.ArgumentParser(description="Build gold-set judge inputs")
    ap.add_argument("--pairs", required=True, help="Comma-separated pair keys, e.g. SI_2019_2020,BAC_2021_2022")
    ap.add_argument("--provider", default="azure_foundry", choices=["anthropic", "azure_foundry", "openai"])
    ap.add_argument("--model-judge")
    ap.add_argument("--model-segmenter")
    ap.add_argument("--azure-endpoint")
    ap.add_argument("--api-key")
    args = ap.parse_args()

    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]
    done, failed = 0, 0

    for pk in pairs:
        try:
            st = build_pair(
                pk, args.provider, args.model_judge, args.model_segmenter,
                args.azure_endpoint, args.api_key,
            )
            n = len(st["tasks"])
            unjudged = sum(1 for t in st["tasks"] if not t.get("prediction"))
            logger.info("[%s] complete: %d tasks, %d unjudged", pk, n, unjudged)
            done += 1
        except Exception as e:
            logger.error("[%s] FAILED: %s: %s", pk, type(e).__name__, e)
            failed += 1

    logger.info("Gold inputs built for %d pair(s), %d failed. -> %s", done, failed, INPUTS_DIR)


if __name__ == "__main__":
    main()
