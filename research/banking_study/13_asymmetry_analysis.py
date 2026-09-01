"""
Does the added/removed decomposition carry information cosine similarity does not?

Cosine is symmetric. If additions and removals were interchangeable, the
decomposition would be redundant and this whole direction is dead. Three questions,
in the order that decides it:

  1. Are added and removed distinct?      If they correlate near 1, there is no
                                          decomposition to speak of.
  2. Is either orthogonal to cosine?      Cosine already prices "how much changed".
                                          A component that just reproduces it adds
                                          nothing.
  3. Do they predict differently?         The claim worth testing: removal predicts
                                          returns where addition does not.

EXPLORATORY. Nothing here is pre-registered, the sample is the same one whose
headline result failed out of sample, and the horizons are all reported rather
than selected. Treat any spread below |t| = 2 as description, not evidence.
"""
import json
import logging
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("asymmetry")

DATA = ROOT / "data"
RESULTS = ROOT / "results"
REPORT = RESULTS / "asymmetry.md"
HORIZONS = ["1m", "3m", "6m", "12m"]

# Signals, with the direction each is sorted in stated up front rather than chosen
# after seeing the spread. "long_low" means the long leg takes the LOW values.
SIGNALS = [
    ("bi_removed", "long_low", "Bigrams removed - share of last year's phrasing now gone"),
    ("bi_added", "long_low", "Bigrams added - share of this year's phrasing that is new"),
    ("bi_net_removed", "long_low", "Net removal - removed minus added"),
    ("len_change", "long_high", "Length change - Item 1A growth rate"),
]


def welch(a: List[float], b: List[float]):
    if len(a) < 3 or len(b) < 3:
        return None, 0, 0
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return ((ma - mb) / se if se else None), len(a), len(b)


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 4:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not sx or not sy:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def load() -> List[Dict[str, Any]]:
    dec = json.loads((DATA / "change_decomposition.json").read_text(encoding="utf-8"))["results"]
    sim = json.loads((DATA / "similarity_scores.json").read_text(encoding="utf-8"))["results"]
    mkt = json.loads((DATA / "market_returns.json").read_text(encoding="utf-8"))
    recs = mkt if isinstance(mkt, list) else list(mkt.get("results", mkt).values())

    ret_by = {}
    for r in recs:
        if not isinstance(r, dict):
            continue
        k = "%s_%s" % (str(r.get("ticker", "")).upper(), r.get("year2"))
        ret_by[k] = r

    rows = []
    for key, v in dec.items():
        d = v.get("item1a")
        if not d:
            continue
        s = (sim.get(key) or {}).get("item1a") or {}
        r = ret_by.get("%s_%s" % (v["ticker"].upper(), v["year2"])) or {}
        row = {"key": key, "ticker": v["ticker"], "year2": v["year2"],
               "sim_cosine": s.get("sim_cosine")}
        row.update({k: d[k] for k in
                    ("bi_added", "bi_removed", "bi_net_removed",
                     "uni_added", "uni_removed", "len_change", "jaccard")})
        for h in HORIZONS:
            row["ex_" + h] = r.get("excess_kre_%s" % h)
        rows.append(row)
    return rows


def spread(rows, field, horizon, long_low: bool, frac: int = 5):
    sub = [r for r in rows if r.get(field) is not None and r.get("ex_" + horizon) is not None]
    if len(sub) < 3 * frac:
        return None
    sub.sort(key=lambda r: r[field])
    q = max(len(sub) // frac, 2)
    low = [r["ex_" + horizon] for r in sub[:q]]
    high = [r["ex_" + horizon] for r in sub[-q:]]
    lng, shrt = (low, high) if long_low else (high, low)
    t, n1, n2 = welch(lng, shrt)
    if t is None:
        return None
    return {"spread": 100 * (sum(lng) / len(lng) - sum(shrt) / len(shrt)), "t": t, "n": n1 + n2}


def main():
    rows = load()
    logger.info("Loaded %d pairs with a usable Item 1A decomposition", len(rows))
    md = ["# Added vs removed: does direction of change matter?\n"]
    md.append("\n> **Exploratory.** Nothing here is pre-registered. This is the same sample "
              "whose headline result failed out of sample, every horizon is reported rather "
              "than selected, and no multiplicity correction is applied. Read anything below "
              "|t| = 2 as description.\n")
    md.append("\n**Pairs**: %d\n" % len(rows))

    md.append("\n## Verdict\n")
    md.append("\n**The decomposition is a real measurement. It does not predict returns here.**\n")
    md.append(
        "\nNet removal correlates with cosine similarity at `r = +0.065` -- very nearly "
        "orthogonal to the symmetric measure, so it is not a repackaging of how much a filing "
        "changed. Added and removed correlate at `+0.62` on bigrams and `+0.30` on unigrams: "
        "related, but far from interchangeable. There is a genuine second dimension here.\n"
    )
    md.append(
        "\nNo cut below predicts returns. The largest statistic across 16 specifications is "
        "`|t| = 1.73`, about what 16 draws produce under the null, and it points the WRONG way "
        "for the concealment story -- heavier removers slightly outperformed at one month. "
        "Nothing here supports the hypothesis that removed disclosure is priced.\n"
    )
    md.append(
        "\nThat is the expected outcome on this sample rather than a surprise. The same "
        "universe, period and benchmark that could not detect the published Lazy Prices effect "
        "cannot detect a subtler one either. What this establishes is narrower and still worth "
        "having: the signal is **constructible and independent** -- the precondition for testing "
        "it somewhere with the power to answer.\n"
    )

    # --- 1. are the two components distinct? -------------------------------
    md.append("\n## 1. Are added and removed actually different?\n")
    md.append("\nIf they move together there is no decomposition here.\n")
    md.append("\n| Pair | Pearson r |")
    md.append("|---|---|")
    for a, b, lbl in (("bi_added", "bi_removed", "added vs removed (bigrams)"),
                      ("uni_added", "uni_removed", "added vs removed (unigrams)"),
                      ("bi_added", "sim_cosine", "added vs cosine similarity"),
                      ("bi_removed", "sim_cosine", "removed vs cosine similarity"),
                      ("bi_net_removed", "sim_cosine", "net removal vs cosine similarity")):
        xs = [r[a] for r in rows if r.get(a) is not None and r.get(b) is not None]
        ys = [r[b] for r in rows if r.get(a) is not None and r.get(b) is not None]
        p = pearson(xs, ys)
        md.append("| %s | `%s` |" % (lbl, ("%+.3f" % p) if p is not None else "-"))

    # --- 2. distribution ----------------------------------------------------
    md.append("\n## 2. What the components look like\n")
    md.append("\n| Measure | Mean | Median | Min | Max |")
    md.append("|---|---|---|---|---|")
    for f in ("bi_added", "bi_removed", "bi_net_removed", "len_change"):
        vs = sorted(r[f] for r in rows if r.get(f) is not None)
        if not vs:
            continue
        md.append("| %s | `%+.3f` | `%+.3f` | `%+.3f` | `%+.3f` |" %
                  (f, sum(vs) / len(vs), vs[len(vs) // 2], vs[0], vs[-1]))

    # --- 3. return predictability ------------------------------------------
    md.append("\n## 3. Return predictability, quintile spreads\n")
    md.append("\nEach signal's direction was fixed before running, and is stated in the table.\n")
    md.append("\n| Signal | Long leg takes | Horizon | Spread | Welch t | n |")
    md.append("|---|---|---|---|---|---|")
    for field, direction, _desc in SIGNALS:
        for h in HORIZONS:
            r = spread(rows, field, h, long_low=(direction == "long_low"))
            if not r:
                md.append("| %s | %s | %s | insufficient n | | |" % (field, direction, h.upper()))
                continue
            md.append("| %s | %s | %s | `%+.2f%%` | `%+.2f` | %d |" %
                      (field, direction.replace("_", " "), h.upper(), r["spread"], r["t"], r["n"]))

    md.append("\n### Benchmark: the symmetric measure on the same pairs\n")
    md.append("\n| Signal | Horizon | Spread | Welch t | n |")
    md.append("|---|---|---|---|---|")
    for h in HORIZONS:
        r = spread(rows, "sim_cosine", h, long_low=False)
        if r:
            md.append("| sim_cosine (long high similarity) | %s | `%+.2f%%` | `%+.2f` | %d |" %
                      (h.upper(), r["spread"], r["t"], r["n"]))

    RESULTS.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(md), encoding="utf-8")
    logger.info("Report -> %s", REPORT)


if __name__ == "__main__":
    main()
