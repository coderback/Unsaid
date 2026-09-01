"""Build a daily calendar-time equity curve for the disclosure-similarity strategy.

The stored returns are only 1M/3M/6M/12M snapshots, which cannot show HOW a
spread accumulates -- steadily, or in two or three episodes. That distinction is
the point of the exercise, so this rebuilds daily paths from prices.

Construction, deliberately the same as the backtest being visualised:
  - within each filing year, rank banks by Item 1A cosine similarity
  - long the top quintile (quiet filers), short the bottom quintile
  - equal weight, each position held 12 months from ITS OWN filing date
  - overlapping cohorts, so the portfolio on any day is whatever is still open

Only pairs passing the Item 1A quality filter are used, matching the analysis.
"""
import json
import os
import sys
from datetime import timedelta

import pandas as pd
import yfinance as yf

sys.path.insert(0, "C:/Users/tobio/PycharmProjects/Unsaid")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "C:/Users/tobio/PycharmProjects/Unsaid/research/banking_study"

MIN_1A_WORDS = 2_500
QUINTILE_FRAC = 5

sim = json.load(open(ROOT + "/data/similarity_scores.json", encoding="utf-8"))["results"]
dates = json.load(open(ROOT + "/data/filing_dates_full.json", encoding="utf-8"))

rows = []
for k, v in sim.items():
    a = v.get("item1a") or {}
    if a.get("sim_cosine") is None:
        continue
    if not (a.get("words_y1") and a.get("words_y2")):
        continue
    if min(a["words_y1"], a["words_y2"]) < MIN_1A_WORDS:
        continue
    tk, y2 = v["ticker"].upper(), v["year2"]
    fd = (dates.get(tk) or {}).get(str(y2))
    if not fd:
        continue
    rows.append({"ticker": tk, "year2": y2, "sim": a["sim_cosine"], "filed": pd.Timestamp(fd)})

df = pd.DataFrame(rows)
print("usable pairs: %d across years %s" % (len(df), sorted(df.year2.unique())))

tickers = sorted(df.ticker.unique())
cache = os.path.join(HERE, "prices.pkl")
if os.path.exists(cache):
    px = pd.read_pickle(cache)
else:
    raw = yf.download(tickers + ["KRE"], start="2019-06-01", end="2026-09-01",
                      auto_adjust=True, progress=False)
    px = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    px.to_pickle(cache)
print("price series: %d symbols x %d days" % (px.shape[1], px.shape[0]))

ret = px.pct_change()

# assign quintiles within each filing year
df["q"] = df.groupby("year2")["sim"].transform(
    lambda s: pd.qcut(s.rank(method="first"), QUINTILE_FRAC, labels=False) + 1)
legs = {}
for _, r in df.iterrows():
    if r.q not in (1, QUINTILE_FRAC) or r.ticker not in ret.columns:
        continue
    side = "long" if r.q == QUINTILE_FRAC else "short"   # top quintile = quiet = long
    legs.setdefault(side, []).append((r.ticker, r.filed, r.filed + timedelta(days=365)))
print("positions: %d long, %d short" % (len(legs.get("long", [])), len(legs.get("short", []))))

days = ret.index[(ret.index >= pd.Timestamp("2020-01-01"))]
out = []
cum_l = cum_s = cum_spread = 1.0
for d in days:
    parts = {}
    for side in ("long", "short"):
        vals = []
        for tk, start, end in legs.get(side, []):
            if start < d <= end:
                v = ret.at[d, tk] if tk in ret.columns else None
                if v is not None and pd.notna(v):
                    vals.append(float(v))
        parts[side] = (sum(vals) / len(vals)) if vals else 0.0
        parts[side + "_n"] = len(vals)
    spread = parts["long"] - parts["short"]
    cum_l *= (1 + parts["long"]); cum_s *= (1 + parts["short"]); cum_spread *= (1 + spread)
    out.append({
        "d": d.strftime("%Y-%m-%d"),
        "l": round(cum_l, 5), "s": round(cum_s, 5), "x": round(cum_spread, 5),
        "nl": parts["long_n"], "ns": parts["short_n"],
    })

json.dump({"series": out,
           "meta": {"pairs": len(df), "long": len(legs.get("long", [])),
                    "short": len(legs.get("short", [])),
                    "years": sorted(int(y) for y in df.year2.unique())}},
          open(os.path.join(HERE, "curve.json"), "w"), separators=(",", ":"))

print()
print("final cumulative:  long %.3f   short %.3f   spread %.3f" % (cum_l, cum_s, cum_spread))
print("total return:      long %+.1f%%  short %+.1f%%  spread %+.1f%%"
      % (100 * (cum_l - 1), 100 * (cum_s - 1), 100 * (cum_spread - 1)))
print("days: %d  -> %s" % (len(out), os.path.join(HERE, "curve.json")))
