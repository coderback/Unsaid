"""
Gold Set Scorer — measure judge quality against human labels.

Reports per-class precision (the metric this stratified sample supports),
agreement, Cohen's kappa, and a confusion matrix. Kappa matters more than raw
agreement: with six classes and an unbalanced sample, a judge that always said
RETAINED could still post a respectable-looking agreement rate.

Usage:
    python research/banking_study/06_score_gold_set.py
    python research/banking_study/06_score_gold_set.py --labels gold/labels.json
"""
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("gold_score")

SCRIPT_DIR = Path(__file__).resolve().parent
GOLD_DIR = SCRIPT_DIR / "gold"
ANSWERS_FILE = GOLD_DIR / "answers.json"
LABELS_FILE = GOLD_DIR / "labels.json"
REPORT_FILE = SCRIPT_DIR / "results" / "gold_set_report.md"

CLASSES = ["RETAINED", "REWORDED", "SOFTENED", "REMOVED", "ABSORBED"]
SIGNAL = {"REMOVED", "SOFTENED", "ABSORBED"}


def cohens_kappa(pairs: List[tuple], labels: List[str]) -> float:
    """Unweighted Cohen's kappa over (human, machine) label pairs."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    agree = sum(1 for a, b in pairs if a == b) / n
    ph = {c: sum(1 for a, _ in pairs if a == c) / n for c in labels}
    pm = {c: sum(1 for _, b in pairs if b == c) / n for c in labels}
    expected = sum(ph[c] * pm[c] for c in labels)
    if expected >= 1.0:
        return float("nan")
    return (agree - expected) / (1 - expected)


def main():
    ap = argparse.ArgumentParser(description="Score judge predictions against human labels")
    ap.add_argument("--labels", default=str(LABELS_FILE))
    ap.add_argument("--answers", default=str(ANSWERS_FILE))
    args = ap.parse_args()

    lp, apath = Path(args.labels), Path(args.answers)
    if not lp.exists():
        raise SystemExit(f"No labels at {lp}. Export them from the labelling page first.")
    if not apath.exists():
        raise SystemExit(f"No answers at {apath}. Run 05_sample_gold_tasks.py first.")

    raw_labels = json.loads(lp.read_text(encoding="utf-8"))
    # Accept either {"labels": {...}} or a bare {task_id: label} mapping.
    human: Dict[str, Any] = raw_labels.get("labels", raw_labels)
    answers = json.loads(apath.read_text(encoding="utf-8"))["answers"]

    pairs, unsure, missing = [], 0, 0
    for tid, ans in answers.items():
        h = human.get(tid)
        if isinstance(h, dict):
            h = h.get("label")
        if not h:
            missing += 1
            continue
        h = str(h).strip().upper()
        if h == "UNSURE":
            unsure += 1
            continue
        pairs.append((h, ans["predicted"], tid))

    if not pairs:
        raise SystemExit("No usable labels found.")

    scored = [(h, m) for h, m, _ in pairs]
    n = len(scored)
    agree = sum(1 for h, m in scored if h == m)
    kappa = cohens_kappa(scored, CLASSES)

    present = [c for c in CLASSES if any(h == c or m == c for h, m in scored)]

    md: List[str] = []
    md.append("# Gold Set Evaluation: Judge vs Human Labels\n")
    md.append(f"**Labelled**: {n} units scored, {unsure} marked UNSURE, {missing} unlabelled\n")
    md.append(f"**Overall agreement**: {agree}/{n} = {100*agree/n:.1f}%\n")
    md.append(f"**Cohen's kappa**: {kappa:.3f}  ")
    interp = ("poor (at or below chance)" if kappa < 0.2 else
              "fair" if kappa < 0.4 else
              "moderate" if kappa < 0.6 else
              "substantial" if kappa < 0.8 else "near-perfect")
    md.append(f"({interp})\n")
    md.append(
        "\n> Sample is stratified by predicted class, so per-class **precision** is the "
        "supported metric. Recall is not estimable here, and overall agreement on this "
        "sample is **not** corpus accuracy.\n"
    )

    md.append("\n## Per-class precision (when the judge says X, how often does the human agree?)\n")
    md.append("| Predicted class | n | Correct | Precision |")
    md.append("|---|---|---|---|")
    for c in present:
        sub = [(h, m) for h, m in scored if m == c]
        if not sub:
            continue
        ok = sum(1 for h, _ in sub if h == c)
        md.append(f"| **{c}** | {len(sub)} | {ok} | `{100*ok/len(sub):.0f}%` |")

    sig = [(h, m) for h, m in scored if m in SIGNAL]
    if sig:
        ok = sum(1 for h, m in sig if h in SIGNAL)
        md.append(
            f"\n**Signal-vs-noise precision**: {ok}/{len(sig)} = `{100*ok/len(sig):.0f}%` "
            f"— how often a unit the judge called REMOVED/SOFTENED/ABSORBED was judged by "
            f"a human to be any signal class rather than RETAINED/REWORDED. This is the "
            f"number the backtest actually depends on.\n"
        )

    md.append("\n## Confusion matrix (rows = human, columns = judge)\n")
    md.append("| human \\\\ judge | " + " | ".join(present) + " |")
    md.append("|---" * (len(present) + 1) + "|")
    for hc in present:
        row = [f"| **{hc}** "]
        for mc in present:
            cnt = sum(1 for h, m in scored if h == hc and m == mc)
            row.append(f"| {cnt if cnt else '·'} ")
        md.append("".join(row) + "|")

    dis = [(h, m, t) for h, m, t in pairs if h != m]
    if dis:
        md.append(f"\n## Disagreements ({len(dis)})\n")
        md.append("| Task | Human | Judge | Judge's reasoning |")
        md.append("|---|---|---|---|")
        for h, m, t in dis[:40]:
            r = (answers[t].get("reasoning") or "").replace("|", "/").replace("\n", " ")[:160]
            md.append(f"| `{t}` | **{h}** | {m} | {r} |")

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(md), encoding="utf-8")

    print("\n".join(md[:14]))
    logger.info("Full report -> %s", REPORT_FILE)


if __name__ == "__main__":
    main()
