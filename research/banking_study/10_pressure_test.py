"""
Pressure-test the one result that cleared significance.

Item 1A cosine similarity at 12 months gives +7.98% (t=2.48) in the direction the
Lazy Prices paper predicts. That emerged from 24 specifications, so before it can
be called a finding it has to survive the checks that usually kill a spurious
result:

  per-year        does it hold in each cross-section, or is it one year?
  cohort          does it survive dropping the crisis banks?
  terminal        does it survive dropping the -100% failed-bank returns?
  winsorised      does it survive trimming return outliers?
  rank            does a rank correlation agree with the quintile spread?
  decile / median does it survive a different portfolio cut?
  permutation     how often does chance produce a t this large?

The permutation test is the decisive one. It is run twice: naively for this
specification alone, and family-wise across all 24 specifications, which is the
honest correction given that 24 were examined before this one was singled out.

Usage:
    python research/banking_study/10_pressure_test.py
"""
import sys
import json
import math
import random
import logging
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("pressure")

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR / "results"
REPORT = RESULTS_DIR / "pressure_test.md"

PRIMARY_FIELD = "sim_1a"
PRIMARY_HORIZON = "ex_12m"
N_PERM = 5000
SEED = 20260827


def welch_t(a: List[float], b: List[float]) -> float:
    a = [x for x in a if x is not None]
    b = [x for x in b if x is not None]
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    se = math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))
    if se == 0:
        return float("nan")
    return (statistics.mean(a) - statistics.mean(b)) / se


def spearman(xs: List[float], ys: List[float]) -> Optional[float]:
    pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pts) < 5:
        return None

    def ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx = ranks([p[0] for p in pts]); ry = ranks([p[1] for p in pts])
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def spread_t(rows: List[Dict[str, Any]], field: str, horizon: str,
             high_is_quiet: bool = True, frac: int = 5) -> Tuple[Optional[float], Optional[float], int]:
    """Return (spread_pct, t, n) for a top/bottom fractile sort."""
    sub = [r for r in rows if r.get(field) is not None and r.get(horizon) is not None]
    if len(sub) < 3 * frac:
        return None, None, len(sub)
    sub = sorted(sub, key=lambda r: r[field])
    k = max(len(sub) // frac, 2)
    low, high = sub[:k], sub[-k:]
    quiet, changer = (high, low) if high_is_quiet else (low, high)
    qr = [r[horizon] for r in quiet]; cr = [r[horizon] for r in changer]
    return (statistics.mean(qr) - statistics.mean(cr)) * 100, welch_t(qr, cr), len(sub)


def winsorise(rows: List[Dict[str, Any]], horizon: str, pct: float = 0.05) -> List[Dict[str, Any]]:
    vals = sorted(r[horizon] for r in rows if r.get(horizon) is not None)
    if len(vals) < 20:
        return rows
    lo = vals[int(len(vals) * pct)]
    hi = vals[int(len(vals) * (1 - pct)) - 1]
    out = []
    for r in rows:
        r2 = dict(r)
        v = r2.get(horizon)
        if v is not None:
            r2[horizon] = min(max(v, lo), hi)
        out.append(r2)
    return out


def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location("m9", SCRIPT_DIR / "09_compare_signals.py")
    m9 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m9)
    rows = m9.load()
    logger.info("Loaded %d pairs", len(rows))

    md: List[str] = []
    md.append("# Pressure Test: Item 1A Similarity, 12-Month Horizon\n")
    base_s, base_t, base_n = spread_t(rows, PRIMARY_FIELD, PRIMARY_HORIZON)
    md.append(f"\n**Baseline**: `{base_s:+.2f}%` spread, t = `{base_t:+.2f}`, n = {base_n}\n")

    # ---- 1. per-year --------------------------------------------------------
    md.append("\n## 1. Per-year cross-sections\n")
    md.append("If one year carries the whole result it is an episode, not a signal.\n")
    md.append("| FY | Spread | t | n |")
    md.append("|---|---|---|---|")
    for y in sorted({r["year2"] for r in rows}):
        sub = [r for r in rows if r["year2"] == y]
        s, t, n = spread_t(sub, PRIMARY_FIELD, PRIMARY_HORIZON)
        if s is None:
            md.append(f"| {y} | insufficient n | | {n} |")
        else:
            md.append(f"| {y} | `{s:+.2f}%` | `{t:+.2f}` | {n} |")

    # ---- 2/3/4. subsample robustness ---------------------------------------
    md.append("\n## 2. Subsample and outlier robustness\n")
    md.append("| Variant | Spread | t | n |")
    md.append("|---|---|---|---|")

    variants: List[Tuple[str, List[Dict[str, Any]]]] = [
        ("All pairs (baseline)", rows),
        ("Excluding crisis cohort", [r for r in rows if r.get("cohort") != "crisis_distressed"]),
        ("Crisis cohort only", [r for r in rows if r.get("cohort") == "crisis_distressed"]),
        ("Excluding terminal (-100%) returns",
         [r for r in rows if r.get(PRIMARY_HORIZON) is None or r[PRIMARY_HORIZON] > -0.99]),
        ("Extraction-stable only",
         [r for r in rows if r.get("word_ratio") is not None and r["word_ratio"] >= 0.5]),
        ("Winsorised returns (5/95)", winsorise(rows, PRIMARY_HORIZON)),
    ]
    for label, sub in variants:
        s, t, n = spread_t(sub, PRIMARY_FIELD, PRIMARY_HORIZON)
        md.append(f"| {label} | `{s:+.2f}%` | `{t:+.2f}` | {n} |" if s is not None
                  else f"| {label} | insufficient n | | {n} |")

    # ---- 5. portfolio cut ---------------------------------------------------
    md.append("\n## 3. Alternative portfolio cuts\n")
    md.append("| Cut | Spread | t | n |")
    md.append("|---|---|---|---|")
    for label, frac in (("Decile (top/bottom 10%)", 10), ("Quintile (baseline)", 5), ("Median split", 2)):
        s, t, n = spread_t(rows, PRIMARY_FIELD, PRIMARY_HORIZON, frac=frac)
        md.append(f"| {label} | `{s:+.2f}%` | `{t:+.2f}` | {n} |" if s is not None
                  else f"| {label} | insufficient n | | {n} |")

    # ---- 6. rank correlation ------------------------------------------------
    sub = [r for r in rows if r.get(PRIMARY_FIELD) is not None and r.get(PRIMARY_HORIZON) is not None]
    rho = spearman([r[PRIMARY_FIELD] for r in sub], [r[PRIMARY_HORIZON] for r in sub])
    md.append("\n## 4. Rank correlation\n")
    md.append(f"\nSpearman rho between Item 1A similarity and 12M excess return: "
              f"`{rho:+.3f}` (n={len(sub)}).\n")
    md.append("\nThe quintile spread compares tails; rho uses the whole distribution. A spread "
              "with no matching monotone relationship is usually a tail artifact.\n")

    # ---- 7. permutation -----------------------------------------------------
    rng = random.Random(SEED)
    vals = [r[PRIMARY_FIELD] for r in sub]
    rets = [r[PRIMARY_HORIZON] for r in sub]

    ge_single = 0
    for _ in range(N_PERM):
        shuffled = rets[:]
        rng.shuffle(shuffled)
        perm = [{PRIMARY_FIELD: v, PRIMARY_HORIZON: x} for v, x in zip(vals, shuffled)]
        _, t, _ = spread_t(perm, PRIMARY_FIELD, PRIMARY_HORIZON)
        if t is not None and not math.isnan(t) and abs(t) >= abs(base_t):
            ge_single += 1
    p_single = ge_single / N_PERM

    # Family-wise: 6 signals x 4 horizons were examined before this one was picked.
    fields = ["sim_cosine", "sim_jaccard", "sim_simple", "sim_1a", "sim_7a", "llm_score"]
    horizons = ["ex_1m", "ex_3m", "ex_6m", "ex_12m"]
    ge_family = 0
    for _ in range(N_PERM // 5):
        idx = list(range(len(rows)))
        rng.shuffle(idx)
        permuted = []
        for r, j in zip(rows, idx):
            r2 = dict(r)
            for h in horizons:
                r2[h] = rows[j].get(h)
            permuted.append(r2)
        best = 0.0
        for f in fields:
            for h in horizons:
                _, t, _ = spread_t(permuted, f, h, high_is_quiet=(f != "llm_score"))
                if t is not None and not math.isnan(t):
                    best = max(best, abs(t))
        if best >= abs(base_t):
            ge_family += 1
    p_family = ge_family / (N_PERM // 5)

    md.append("\n## 5. Permutation test\n")
    md.append(f"\nReturns shuffled against signals, {N_PERM} draws.\n")
    md.append(f"\n- **This specification alone**: `p = {p_single:.4f}` "
              f"({ge_single} of {N_PERM} draws reached |t| >= {abs(base_t):.2f})")
    md.append(f"\n- **Family-wise across all 24 specifications**: `p = {p_family:.4f}` "
              f"({ge_family} of {N_PERM // 5} draws had ANY specification reach |t| >= {abs(base_t):.2f})\n")
    md.append("\nThe family-wise figure is the one that matters. 24 specifications were examined "
              "before this result was singled out, so the relevant question is how often chance "
              "produces a t this large SOMEWHERE among 24 tries, not how often it produces one "
              "in a pre-registered test.\n")

    verdict = ("SURVIVES" if p_family < 0.05 else
               "DOES NOT SURVIVE multiplicity correction")
    md.append(f"\n## Verdict\n\n**{verdict}** at the 5% level once the 24 specifications "
              f"are accounted for (family-wise p = {p_family:.4f}).\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    logger.info("Report -> %s", REPORT)


if __name__ == "__main__":
    main()
