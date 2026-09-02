"""
Does SOFTENED look like softening, mechanically?

The judge and the model labeller disagree on 10 units: the judge says SOFTENED,
the labeller says RETAINED. Neither can adjudicate the other -- the labeller is
Claude, which also wrote the rubric the judge runs.

But SOFTENED is not only a judgment. It is a claim with textual consequences. If a
disclosure was genuinely softened, the year-2 text should be measurably shorter,
or hedgier, or less specific than the year-1 text. If the disputed units look the
same as the RETAINED controls on those measures, the judge is over-calling, and no
human opinion is required to see it.

Three measures, all computed on the year-1 unit against its closest year-2
candidate:

  length ratio    words(y2) / words(y1)          softening should shrink text
  hedge shift     hedge terms per 1k words, y2-y1 softening should hedge more
  specificity     numbers + dollar amounts + named entities per 1k words, y2-y1
                  softening should drop concrete detail

This is evidence, not a verdict. It cannot tell whether the risk itself changed --
only whether the language did what SOFTENED implies.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GOLD = ROOT / "gold"

HEDGES = re.compile(
    r"\b(may|might|could|possibly|potential(?:ly)?|approximately|generally|"
    r"substantially|materially|significant(?:ly)?|certain|various|among other|"
    r"including but not limited to|from time to time|no assurance|cannot predict|"
    r"believe|expect|anticipate|estimate|intend|seek to|attempt to)\b", re.I)
NUMERIC = re.compile(r"\$?\d[\d,\.]*%?")
PROPER = re.compile(r"\b[A-Z][a-z]{2,}\b")
WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")


def feats(text):
    w = WORD.findall(text or "")
    n = max(len(w), 1)
    return {
        "words": len(w),
        "hedge_k": 1000.0 * len(HEDGES.findall(text or "")) / n,
        "num_k": 1000.0 * len(NUMERIC.findall(text or "")) / n,
        "proper_k": 1000.0 * len(PROPER.findall(text or "")) / n,
    }


def best_candidate(unit_text, cands):
    """Closest year-2 passage by token overlap -- the one a reader would compare against."""
    ut = set(w.lower() for w in WORD.findall(unit_text or ""))
    best, bs = None, -1.0
    for c in cands or []:
        ct = set(w.lower() for w in WORD.findall(c.get("text", "")))
        if not ct:
            continue
        j = len(ut & ct) / max(len(ut | ct), 1)
        if j > bs:
            best, bs = c, j
    return best, bs


def main():
    tasks = {t["task_id"]: t for t in json.loads((GOLD / "tasks.json").read_text(encoding="utf-8"))["tasks"]}
    mine = {k: (v if isinstance(v, str) else v.get("label", "")).upper()
            for k, v in json.loads((GOLD / "labels.model.json").read_text(encoding="utf-8"))["labels"].items()}
    judge = {k: v["predicted"].upper()
             for k, v in json.loads((GOLD / "answers.v3.json").read_text(encoding="utf-8"))["answers"].items()}

    groups = {
        "DISPUTED (judge=SOFTENED, labeller=RETAINED)":
            [k for k in mine if k in judge and mine[k] == "RETAINED" and judge[k] == "SOFTENED"],
        "AGREED RETAINED (both)":
            [k for k in mine if k in judge and mine[k] == "RETAINED" and judge[k] == "RETAINED"],
        "AGREED REMOVED (both)":
            [k for k in mine if k in judge and mine[k] == "REMOVED" and judge[k] == "REMOVED"],
    }

    print("Mechanical signature of the disputed SOFTENED calls")
    print("=" * 74)
    rows = {}
    for label, ids in groups.items():
        vals = []
        for tid in ids:
            t = tasks.get(tid)
            if not t:
                continue
            cand, sim = best_candidate(t["unit_text"], t.get("candidates"))
            if not cand:
                continue
            a, b = feats(t["unit_text"]), feats(cand.get("text", ""))
            vals.append({
                "len_ratio": b["words"] / max(a["words"], 1),
                "hedge_shift": b["hedge_k"] - a["hedge_k"],
                "num_shift": b["num_k"] - a["num_k"],
                "proper_shift": b["proper_k"] - a["proper_k"],
                "overlap": sim,
            })
        if not vals:
            continue
        med = lambda k: sorted(v[k] for v in vals)[len(vals) // 2]
        rows[label] = {k: med(k) for k in ("len_ratio", "hedge_shift", "num_shift", "proper_shift", "overlap")}
        rows[label]["n"] = len(vals)

    hdr = ("group", "n", "len ratio", "hedge/1k", "numbers/1k", "proper/1k", "overlap")
    print("%-46s %3s %10s %10s %11s %10s %9s" % hdr)
    for label, r in rows.items():
        print("%-46s %3d %10.2f %+10.1f %+11.1f %+10.1f %9.3f" % (
            label[:46], r["n"], r["len_ratio"], r["hedge_shift"],
            r["num_shift"], r["proper_shift"], r["overlap"]))

    print()
    d = rows.get("DISPUTED (judge=SOFTENED, labeller=RETAINED)")
    c = rows.get("AGREED RETAINED (both)")
    if d and c:
        print("Reading:")
        shorter = d["len_ratio"] < c["len_ratio"] * 0.85
        hedgier = d["hedge_shift"] > c["hedge_shift"] + 2
        vaguer = d["num_shift"] < c["num_shift"] - 2
        for ok, msg in ((shorter, "disputed units are materially SHORTER than agreed-RETAINED"),
                        (hedgier, "disputed units gain MORE hedging than agreed-RETAINED"),
                        (vaguer, "disputed units lose MORE numeric detail than agreed-RETAINED")):
            print("   [%s] %s" % ("yes" if ok else " no", msg))
        n = sum([shorter, hedgier, vaguer])
        print()
        if n >= 2:
            print("=> The disputed calls carry a softening signature. Supports the JUDGE.")
        elif n == 0:
            print("=> The disputed units are textually indistinguishable from RETAINED.")
            print("   Supports the LABELLER: the judge is over-calling SOFTENED.")
        else:
            print("=> Mixed. One signal of three; too weak to adjudicate either way.")
        print()
        print("Caveat: this measures whether the LANGUAGE softened, not whether the RISK")
        print("did. A firm can hedge its wording while disclosing the same exposure, and")
        print("can drop a real exposure without changing tone. Evidence, not a verdict.")


if __name__ == "__main__":
    main()
