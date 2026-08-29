"""
Head-to-head: bag-of-words similarity vs the LLM removal score.

The question this answers is whether Unsaid's semantic classification earns its
cost. Cohen, Malloy & Nguyen reach t=3.59 with term-frequency similarity alone;
if that measure carries the signal in this sample and the LLM score does not,
the LLM is not adding value here. If neither shows anything, the sample is
simply too small to separate them -- which is itself the answer.

Sign convention. The paper sorts on similarity: Q1 is LEAST similar (the "big
changers", shorted) and Q5 is MOST similar (the "non-changers", held long), so
their spread is Q5 - Q1. Unsaid sorts on removal severity, where Q1 is cleanest
and Q5 heaviest, so its spread is Q1 - Q5. Both are therefore reported as
long-the-quiet-filers minus short-the-changers and are directly comparable.

Usage:
    python research/banking_study/09_compare_signals.py
"""
import sys
import json
import math
import argparse
import logging
import statistics
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("compare")

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
RESULTS_DIR = SCRIPT_DIR / "results"
REPORT = RESULTS_DIR / "signal_comparison.md"

HORIZONS = ["1m", "3m", "6m", "12m"]


def welch_t(a: List[float], b: List[float]) -> Tuple[float, int, int]:
    a = [x for x in a if x is not None and not math.isnan(x)]
    b = [x for x in b if x is not None and not math.isnan(x)]
    if len(a) < 2 or len(b) < 2:
        return float("nan"), len(a), len(b)
    va = statistics.variance(a); vb = statistics.variance(b)
    se = math.sqrt(va / len(a) + vb / len(b))
    if se == 0:
        return float("nan"), len(a), len(b)
    return (statistics.mean(a) - statistics.mean(b)) / se, len(a), len(b)


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pts) < 3:
        return None
    xs2 = [p[0] for p in pts]; ys2 = [p[1] for p in pts]
    mx, my = statistics.mean(xs2), statistics.mean(ys2)
    num = sum((x - mx) * (y - my) for x, y in pts)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs2) * sum((y - my) ** 2 for y in ys2))
    return num / den if den else None


def load() -> List[Dict[str, Any]]:
    sim = json.loads((DATA_DIR / "similarity_scores.json").read_text(encoding="utf-8"))["results"]
    man = json.loads((DATA_DIR / "ingest_manifest.json").read_text(encoding="utf-8"))["results"]
    ret = json.loads((DATA_DIR / "market_returns.json").read_text(encoding="utf-8"))["results"]

    sys.path.insert(0, str(SCRIPT_DIR))
    import importlib.util
    spec = importlib.util.spec_from_file_location("m3", SCRIPT_DIR / "03_portfolio_backtest.py")
    m3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m3)

    rows = []
    for key, s in sim.items():
        comb = s.get("combined")
        if not comb or comb.get("sim_cosine") is None:
            continue
        r = ret.get(key, {})
        mi = man.get(key, {})
        llm = m3.normalized_removal_score(mi.get("counts", {}), mi.get("total_disclosures", 0)) \
            if mi.get("status") == "completed" else None
        row = {
            "key": key, "ticker": s["ticker"], "cohort": s.get("cohort"), "year2": s["year2"],
            "sim_cosine": comb["sim_cosine"], "sim_jaccard": comb["sim_jaccard"],
            "sim_simple": comb["sim_simple"],
            "sim_1a": (s.get("item1a") or {}).get("sim_cosine"),
            "sim_7a": (s.get("item7a") or {}).get("sim_cosine"),
            # Item 7A length, used to tell a real section from a cross-reference
            # stub. Most banks route market risk into MD&A and leave a ~22-word
            # pointer behind; comparing two such stubs is not a measurement.
            "w7a_y1": (s.get("item7a") or {}).get("words_y1"),
            "w7a_y2": (s.get("item7a") or {}).get("words_y2"),
            "llm_score": llm,
            # Extraction-stability check. A collapse in extracted length between
            # years drives similarity down for reasons that have nothing to do
            # with the issuer -- CFG FY21->22 went 25,634 -> 6,144 words and looks
            # like a "big changer" purely from that. Both signals inherit it.
            "word_ratio": (min(comb["words_y1"], comb["words_y2"]) /
                           max(comb["words_y1"], comb["words_y2"]))
                          if comb.get("words_y1") and comb.get("words_y2") else None,
        }
        for h in HORIZONS:
            row[f"ex_{h}"] = r.get(f"excess_kre_{h}")
        rows.append(row)
    return rows


# A genuine Item 7A in a bank 10-K runs a few thousand words. Below this is a
# cross-reference stub; above it the extractor has swallowed adjacent sections.
_REAL_7A_MIN_WORDS = 1_000
_REAL_7A_MAX_WORDS = 15_000


def has_real_7a(r: Dict[str, Any]) -> bool:
    """True when BOTH years carry a plausible standalone Item 7A."""
    w1, w2 = r.get("w7a_y1"), r.get("w7a_y2")
    if not w1 or not w2:
        return False
    return all(_REAL_7A_MIN_WORDS <= w <= _REAL_7A_MAX_WORDS for w in (w1, w2))


def quintile_spread(rows: List[Dict[str, Any]], field: str, horizon: str,
                    high_is_quiet: bool, frac: int = 5) -> Optional[Dict[str, Any]]:
    """
    Sort on `field`, then compare the quiet-filer quintile against the changer
    quintile. high_is_quiet is True for similarity (high = unchanged) and False
    for the removal score (high = heavy change).
    """
    sub = [r for r in rows if r.get(field) is not None and r.get(f"ex_{horizon}") is not None]
    if len(sub) < 3 * frac:
        return None
    sub.sort(key=lambda r: r[field])
    q = max(len(sub) // frac, 2)
    low, high = sub[:q], sub[-q:]
    quiet, changer = (high, low) if high_is_quiet else (low, high)
    qr = [r[f"ex_{horizon}"] for r in quiet]
    cr = [r[f"ex_{horizon}"] for r in changer]
    t, n1, n2 = welch_t(qr, cr)
    return {
        "spread": (statistics.mean(qr) - statistics.mean(cr)) * 100,
        "t": t, "n": len(sub), "n_side": q,
        "corr": pearson([r[field] for r in sub], [r[f"ex_{horizon}"] for r in sub]),
    }


def main():
    argparse.ArgumentParser(description="Compare bag-of-words and LLM signals").parse_args()
    rows = load()
    logger.info("Loaded %d pairs with a similarity score", len(rows))
    withllm = [r for r in rows if r["llm_score"] is not None]
    logger.info("  %d also have a usable LLM removal score", len(withllm))

    md: List[str] = []
    md.append("# Signal Comparison: Bag-of-Words vs LLM Classification\n")
    md.append("Long the quiet filers, short the changers. Both signals are reported in the ")
    md.append("same direction, so the numbers are directly comparable.\n")
    md.append(f"\n**Pairs with similarity scores**: {len(rows)}  ")
    md.append(f"**Pairs with both signals**: {len(withllm)}\n")

    # Extraction-stable subset: both years within 2x of each other in length.
    stable = [r for r in rows if r.get("word_ratio") is not None and r["word_ratio"] >= 0.5]
    logger.info("  %d of %d pairs are extraction-stable (word ratio >= 0.5)", len(stable), len(rows))

    specs = [
        ("Sim_Cosine (1A+7A)", "sim_cosine", True),
        ("Sim_Jaccard (1A+7A)", "sim_jaccard", True),
        ("Sim_Simple (1A+7A)", "sim_simple", True),
        ("Sim_Cosine (Item 1A)", "sim_1a", True),
        ("Sim_Cosine (Item 7A)", "sim_7a", True),
        ("LLM removal score", "llm_score", False),
    ]

    md.append("\n## Quintile long/short spread, excess vs KRE\n")
    md.append("| Signal | Horizon | Spread | Welch t | n | corr |")
    md.append("|---|---|---|---|---|---|")
    for label, field, hq in specs:
        for h in HORIZONS:
            r = quintile_spread(rows, field, h, hq)
            if not r:
                continue
            c = f"{r['corr']:+.3f}" if r["corr"] is not None else "n/a"
            md.append(f"| {label} | {h.upper()} | `{r['spread']:+.2f}%` | `{r['t']:+.2f}` | {r['n']} | `{c}` |")

    md.append("\n## Extraction-stable subset only\n")
    md.append(
        f"\nPairs where extracted length is within 2x between years "
        f"(n={len(stable)} of {len(rows)}). A length collapse depresses similarity for "
        f"reasons unrelated to the issuer, so this removes the clearest extraction "
        f"artifacts from both signals.\n"
    )
    md.append("| Signal | Horizon | Spread | Welch t | n |")
    md.append("|---|---|---|---|---|")
    for label, field, hq in specs:
        for h in HORIZONS:
            r = quintile_spread(stable, field, h, hq)
            if not r:
                continue
            md.append(
                "| {} | {} | `{:+.2f}%` | `{:+.2f}` | {} |".format(
                    label, h.upper(), r["spread"], r["t"], r["n"]
                )
            )


    # ---- Item 7A restricted to pairs that actually have an Item 7A -----------
    real7 = [r for r in rows if has_real_7a(r)]
    logger.info("  %d of %d pairs have a real Item 7A in BOTH years", len(real7), len(rows))

    md.append("\n## Item 7A, restricted to pairs that have one\n")
    md.append(
        "\nOnly **{}** of {} pairs compare two genuine Item 7A sections (both years "
        "between {:,} and {:,} words). The rest are cross-reference stubs -- most banks "
        "route market risk into MD&A and leave a ~22-word pointer -- and two stubs are "
        "near-identical by construction, so the unrestricted 7A figures elsewhere in this "
        "report are largely measuring boilerplate against boilerplate.\n".format(
            len(real7), len(rows), _REAL_7A_MIN_WORDS, _REAL_7A_MAX_WORDS)
    )
    md.append(
        "\n**This subset is severely underpowered.** At n={} a quintile is ~{} per side, "
        "so the median split is the more honest read. Neither is a basis for a claim.\n".format(
            len(real7), max(len(real7) // 5, 2))
    )
    md.append("| Cut | Horizon | Spread | Welch t | n |")
    md.append("|---|---|---|---|---|")
    for cut_label, frac in (("Quintile", 5), ("Median split", 2)):
        for h in HORIZONS:
            r = quintile_spread(real7, "sim_7a", h, True, frac=frac)
            if not r:
                md.append("| {} | {} | insufficient n | | {} |".format(
                    cut_label, h.upper(), len(real7)))
                continue
            md.append("| {} | {} | `{:+.2f}%` | `{:+.2f}` | {} |".format(
                cut_label, h.upper(), r["spread"], r["t"], r["n"]))

    # Do the two signals even agree with each other?
    both = [(r["sim_cosine"], r["llm_score"]) for r in withllm]
    if len(both) >= 3:
        c = pearson([b[0] for b in both], [b[1] for b in both])
        md.append(f"\n## Do the signals agree?\n")
        md.append(f"\nCorrelation between Sim_Cosine and the LLM removal score: "
                  f"`{c:+.3f}` (n={len(both)}).\n")
        md.append("\nSimilarity is high when a filing barely changed; the removal score is high "
                  "when much was deleted. A strongly NEGATIVE correlation means the two are "
                  "measuring the same underlying thing. A correlation near zero means the LLM "
                  "is measuring something bag-of-words does not capture -- which is either the "
                  "value it adds, or noise.\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    logger.info("Report -> %s", REPORT)


if __name__ == "__main__":
    main()
