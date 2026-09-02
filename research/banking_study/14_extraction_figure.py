"""Where in the similarity distribution do extraction failures land?

The claim the figure has to make visible is not "some data was bad" but "the bad
data sat exactly where a quintile sort draws its signal". So: classify every
pre-fix observation, place it in that year's ranking, and count how many landed in
the long leg.
"""
import json
import os

import pandas as pd

D = "C:/Users/tobio/AppData/Local/Temp/claude/C--Users-tobio-PycharmProjects-Unsaid/91f816a4-7c0b-4451-986a-a7174f7dc92f/scratchpad/"
ROOT = "research/banking_study/data/"

pre = json.load(open(D + "similarity_scores.PRE-EX13.json", encoding="utf-8"))["results"]
post = json.load(open(ROOT + "similarity_scores.json", encoding="utf-8"))["results"]

POINTER_MAX = 2_500      # below this, Item 1A is a cross-reference pointer
OVERCAP_MIN = 40_000     # above this, the extractor swallowed adjacent sections


def classify(w1, w2):
    if not w1 or not w2:
        return "missing"
    if min(w1, w2) < POINTER_MAX:
        return "pointer"
    if max(w1, w2) > OVERCAP_MIN:
        return "overcapture"
    return "clean"


rows = []
for k, v in pre.items():
    a = v.get("item1a") or {}
    if a.get("sim_cosine") is None:
        continue
    rows.append({
        "key": k, "ticker": v["ticker"], "year2": v["year2"],
        "sim": a["sim_cosine"], "w1": a.get("words_y1"), "w2": a.get("words_y2"),
        "cls": classify(a.get("words_y1"), a.get("words_y2")),
    })
df = pd.DataFrame(rows)

# rank within each filing year, exactly as the backtest sorts
df["pct"] = df.groupby("year2")["sim"].rank(pct=True)
df["q"] = df.groupby("year2")["sim"].transform(
    lambda s: pd.qcut(s.rank(method="first"), 5, labels=False) + 1)

print("PRE-FIX corpus: %d pairs with an Item 1A similarity" % len(df))
print()
print(df["cls"].value_counts().to_string())
print()
print("share of each quintile that is NOT a real Item 1A:")
print("  quintile        n   pointer  overcapture   bad%")
for q in range(1, 6):
    sub = df[df.q == q]
    p = int((sub.cls == "pointer").sum())
    o = int((sub.cls == "overcapture").sum())
    tag = "  <-- LONG leg" if q == 5 else ("  <-- SHORT leg" if q == 1 else "")
    print("  Q%d %14d %7d %10d %6.1f%%%s" % (q, len(sub), p, o, 100 * (p + o) / len(sub), tag))
print()

top = df[df.q == 5]
print("THE HEADLINE: %d of %d long-leg observations (%.0f%%) were not Item 1A"
      % (int((top.cls != "clean").sum()), len(top), 100 * (top.cls != "clean").mean()))
print()
ptr = df[df.cls == "pointer"]
print("pointers: %d, of which %d score exactly 1.0000 (identical stubs)"
      % (len(ptr), int((ptr.sim >= 0.99995).sum())))
print("  their mean similarity %.4f vs %.4f for clean pairs"
      % (ptr.sim.mean(), df[df.cls == "clean"].sim.mean()))

payload = {
    "points": [{"s": round(r.sim, 4), "p": round(r.pct, 4), "c": r.cls,
                "t": r.ticker, "y": int(r.year2), "q": int(r.q)}
               for r in df.itertuples()],
    "counts": {k: int(v) for k, v in df["cls"].value_counts().items()},
    "quintiles": [{"q": q,
                   "n": int((df.q == q).sum()),
                   "bad": int(((df.q == q) & (df.cls != "clean")).sum())}
                  for q in range(1, 6)],
    "before": {"spread": 7.98, "t": 2.48, "n": 197},
    "after": {"spread": 6.15, "t": 1.83, "n": 186},
}
json.dump(payload, open(D + "extraction_payload.json", "w"), separators=(",", ":"))
print()
print("payload -> %d KB" % (os.path.getsize(D + "extraction_payload.json") // 1024))
