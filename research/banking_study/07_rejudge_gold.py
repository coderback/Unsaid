"""
Re-judge the gold sample against a changed prompt, on identical evidence.

Because 04 persisted the exact judge inputs (Year-1 unit plus its retrieved Year-2
candidates), a prompt change can be evaluated without re-extracting or
re-segmenting. That matters: segmentation is an LLM step, and two runs over the
same filing pair previously produced 108 vs 112 units with almost no overlapping
titles, which made any before/after comparison meaningless. Holding the evidence
fixed isolates the prompt as the only variable.

Writes gold/answers.<tag>.json in the same shape as answers.json so 06 can score
it directly.

Usage:
    python research/banking_study/07_rejudge_gold.py --tag v2
"""
import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("rejudge")

SCRIPT_DIR = Path(__file__).resolve().parent
GOLD_DIR = SCRIPT_DIR / "gold"
INPUTS_DIR = GOLD_DIR / "inputs"
ANSWERS_FILE = GOLD_DIR / "answers.json"


def main():
    ap = argparse.ArgumentParser(description="Re-judge the gold sample on identical evidence")
    ap.add_argument("--tag", required=True, help="Label for this run, e.g. v2")
    ap.add_argument("--provider", default="azure_foundry", choices=["anthropic", "azure_foundry", "openai"])
    ap.add_argument("--model-judge")
    ap.add_argument("--azure-endpoint")
    ap.add_argument("--api-key")
    args = ap.parse_args()

    from unsaid.judge import judge_unit

    if not ANSWERS_FILE.exists():
        raise SystemExit(f"No sample at {ANSWERS_FILE}. Run 05_sample_gold_tasks.py first.")
    answers = json.loads(ANSWERS_FILE.read_text(encoding="utf-8"))["answers"]

    # Index the persisted evidence by (pair_key, unit_id).
    evidence: Dict[tuple, Dict[str, Any]] = {}
    meta: Dict[str, Dict[str, Any]] = {}
    for path in sorted(INPUTS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        meta[data["pair_key"]] = data
        for t in data.get("tasks", []):
            evidence[(data["pair_key"], t["unit_id"])] = t

    out_path = GOLD_DIR / f"answers.{args.tag}.json"
    state: Dict[str, Any] = {}
    if out_path.exists():
        try:
            state = json.loads(out_path.read_text(encoding="utf-8")).get("answers", {})
        except Exception:
            state = {}

    def save():
        out_path.write_text(json.dumps({
            "tag": args.tag,
            "rejudged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "Re-judged on the SAME persisted evidence as answers.json; only the judge prompt differs.",
            "answers": state,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    todo = [t for t in answers if t not in state]
    logger.info("Re-judging %d/%d sampled tasks under tag '%s'", len(todo), len(answers), args.tag)

    for i, tid in enumerate(sorted(answers), 1):
        if tid in state:
            continue
        ans = answers[tid]
        key = (ans["pair_key"], ans["unit_id"])
        task = evidence.get(key)
        if not task:
            logger.warning("%s: evidence not found for %s", tid, key)
            continue

        pair = meta[ans["pair_key"]]
        cands = [
            ({"title": c["title"], "text": c["text"], "section": c["section"]}, c["similarity"])
            for c in task["candidates"]
        ]
        unit = dict(task["unit"])
        unit["id"] = task["unit_id"]

        res = judge_unit(
            unit, cands, pair["year1"], pair["year2"],
            provider=args.provider, model=args.model_judge,
            api_key=args.api_key, azure_endpoint=args.azure_endpoint,
        )
        state[tid] = {
            "pair_key": ans["pair_key"],
            "unit_id": ans["unit_id"],
            "predicted": res.get("classification"),
            "confidence": res.get("confidence"),
            "reasoning": res.get("reasoning"),
            "judge_failed": bool(res.get("judge_failed")),
        }
        if i % 5 == 0 or i == len(answers):
            save()
            logger.info("  %d/%d", len(state), len(answers))

    save()

    import collections
    dist = collections.Counter(v["predicted"] for v in state.values())
    prev = collections.Counter(v["predicted"] for v in answers.values())
    logger.info("previous: %s", dict(prev))
    logger.info("     new: %s", dict(dist))
    logger.info("wrote %s", out_path)


if __name__ == "__main__":
    main()
