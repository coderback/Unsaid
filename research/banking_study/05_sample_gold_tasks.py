"""
Gold Set Sampler — draw a stratified, blind labelling sample.

Sampling is stratified by the judge's PREDICTED class so that the signal classes
(REMOVED / SOFTENED / ABSORBED) get enough mass to estimate precision. This makes
the sample deliberately non-representative of the corpus: it supports per-class
PRECISION ("when the judge says REMOVED, is it right?") but NOT recall, and the
overall agreement rate on this sample is not the corpus accuracy. That trade is
intentional and is recorded in the output so nobody reads it the wrong way later.

Two files are written:
  tasks.json    the evidence only, shuffled, with predictions stripped
  answers.json  the predictions, keyed by task id

Keeping them apart is the point. A labeller who can see the judge's answer is
not producing an independent label, and anchoring here would quietly invalidate
the whole exercise.

Usage:
    python research/banking_study/05_sample_gold_tasks.py --n 60
"""
import sys
import json
import random
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("gold_sample")

SCRIPT_DIR = Path(__file__).resolve().parent
GOLD_DIR = SCRIPT_DIR / "gold"
INPUTS_DIR = GOLD_DIR / "inputs"
TASKS_FILE = GOLD_DIR / "tasks.json"
ANSWERS_FILE = GOLD_DIR / "answers.json"

# Target composition, by predicted class.
DEFAULT_QUOTA = {
    "REMOVED": 15,
    "SOFTENED": 15,
    "ABSORBED": 15,
    "RETAINED": 10,
    "REWORDED": 5,
}


def load_all_tasks() -> List[Dict[str, Any]]:
    if not INPUTS_DIR.exists():
        raise FileNotFoundError(f"No gold inputs at {INPUTS_DIR}. Run 04_build_gold_set.py first.")
    out = []
    for path in sorted(INPUTS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for t in data.get("tasks", []):
            pred = t.get("prediction")
            if not pred or not pred.get("classification"):
                continue
            if pred.get("judge_failed"):
                continue  # a fallback label is not a real prediction
            out.append({
                "pair_key": data["pair_key"],
                "ticker": data["ticker"],
                "company_name": data.get("company_name"),
                "year1": data["year1"],
                "year2": data["year2"],
                "embed_backend": data.get("embed_backend"),
                "unit_id": t["unit_id"],
                "unit": t["unit"],
                "candidates": t.get("candidates", []),
                "prediction": pred,
            })
    return out


def main():
    ap = argparse.ArgumentParser(description="Draw a stratified blind labelling sample")
    ap.add_argument("--n", type=int, default=60, help="Target sample size")
    ap.add_argument("--seed", type=int, default=20260826, help="RNG seed (recorded for reproducibility)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    all_tasks = load_all_tasks()
    if not all_tasks:
        raise SystemExit("No judged tasks found. Run 04_build_gold_set.py first.")

    by_class: Dict[str, List[Dict[str, Any]]] = {}
    for t in all_tasks:
        by_class.setdefault(t["prediction"]["classification"], []).append(t)

    logger.info("Available by predicted class:")
    for cls, items in sorted(by_class.items()):
        logger.info("  %-10s %d", cls, len(items))

    # Scale the default quota to the requested n, then clamp to what exists.
    scale = args.n / sum(DEFAULT_QUOTA.values())
    quota = {c: max(1, round(v * scale)) for c, v in DEFAULT_QUOTA.items()}

    selected: List[Dict[str, Any]] = []
    shortfall: Dict[str, int] = {}
    for cls, want in quota.items():
        pool = by_class.get(cls, [])
        rng.shuffle(pool)
        take = pool[:want]
        selected.extend(take)
        if len(take) < want:
            shortfall[cls] = want - len(take)

    # Backfill any shortfall from the largest remaining pools so n is still met.
    if shortfall:
        logger.warning("Short of quota: %s — backfilling from other classes", shortfall)
        chosen_ids = {t["unit_id"] for t in selected}
        rest = [t for t in all_tasks if t["unit_id"] not in chosen_ids]
        rng.shuffle(rest)
        selected.extend(rest[: sum(shortfall.values())])

    rng.shuffle(selected)

    tasks_out, answers_out = [], {}
    for i, t in enumerate(selected, 1):
        tid = f"T{i:03d}"
        tasks_out.append({
            "task_id": tid,
            "ticker": t["ticker"],
            "company_name": t.get("company_name"),
            "year1": t["year1"],
            "year2": t["year2"],
            "section": t["unit"].get("section"),
            "unit_title": t["unit"].get("title"),
            "unit_text": t["unit"].get("text"),
            "candidates": [
                {"title": c.get("title"), "text": c.get("text"), "section": c.get("section")}
                for c in t["candidates"]
            ],
        })
        answers_out[tid] = {
            "pair_key": t["pair_key"],
            "unit_id": t["unit_id"],
            "predicted": t["prediction"]["classification"],
            "confidence": t["prediction"].get("confidence"),
            "reasoning": t["prediction"].get("reasoning"),
            "embed_backend": t.get("embed_backend"),
        }

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps({
        "generated_from": sorted({t["pair_key"] for t in selected}),
        "seed": args.seed,
        "n": len(tasks_out),
        "sampling": "stratified by PREDICTED class — supports per-class precision, NOT recall; "
                    "overall agreement on this sample is not corpus accuracy",
        "label_options": ["RETAINED", "REWORDED", "SOFTENED", "REMOVED", "ABSORBED", "UNSURE"],
        "tasks": tasks_out,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    ANSWERS_FILE.write_text(json.dumps({
        "seed": args.seed,
        "answers": answers_out,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    dist: Dict[str, int] = {}
    for a in answers_out.values():
        dist[a["predicted"]] = dist.get(a["predicted"], 0) + 1
    logger.info("Sampled %d tasks: %s", len(tasks_out), dist)
    logger.info("  blind tasks -> %s", TASKS_FILE)
    logger.info("  held-back predictions -> %s", ANSWERS_FILE)


if __name__ == "__main__":
    main()
