"""Compress the daily curve into an embeddable payload plus the summary stats."""
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "curve.json")))
s = pd.DataFrame(d["series"])
s["dt"] = pd.to_datetime(s["d"])
s = s.set_index("dt")

# weekly sampling keeps the shape and cuts the payload ~5x
w = s.resample("W-FRI").last().dropna()
start = w.index[0]

series = {
    "start": start.strftime("%Y-%m-%d"),
    "x": [round(v, 4) for v in w["x"]],
    "l": [round(v, 4) for v in w["l"]],
    "sh": [round(v, 4) for v in w["s"]],
    "n": [int(v) for v in w["nl"]],
    "dates": [t.strftime("%Y-%m-%d") for t in w.index],
}

# annual contribution to the spread
yr = s["x"].resample("YE").last()
annual, prev = [], 1.0
for dt, v in yr.items():
    annual.append({"y": int(dt.year), "r": round(100 * (v / prev - 1), 2)})
    prev = v
annual = [a for a in annual if abs(a["r"]) > 0.001]

# drawdown
mx = s["x"].cummax()
dd = s["x"] / mx - 1
dd_trough = dd.idxmin()
dd_peak = s.loc[:dd_trough, "x"].idxmax()

# counterfactual: strip the two positive episodes
keep = s[~s.index.year.isin([2023, 2026])]
r_ex = 1.0
for y in sorted(set(s.index.year)):
    if y in (2023, 2026):
        continue
    seg = s[s.index.year == y]["x"]
    if len(seg) > 1:
        r_ex *= float(seg.iloc[-1] / seg.iloc[0])

days_total = len(s)
days_flat = int((s["nl"] == 0).sum())
years = (s.index[-1] - s.index[0]).days / 365.25
final = float(s["x"].iloc[-1])

stats = {
    "final": round(100 * (final - 1), 2),
    "annualised": round(100 * (final ** (1 / years) - 1), 2),
    "years": round(years, 1),
    "maxdd": round(100 * float(dd.min()), 2),
    "dd_from": dd_peak.strftime("%Y-%m-%d"),
    "dd_to": dd_trough.strftime("%Y-%m-%d"),
    "flat_pct": round(100 * days_flat / days_total),
    "long_final": round(100 * (float(s["l"].iloc[-1]) - 1), 1),
    "short_final": round(100 * (float(s["s"].iloc[-1]) - 1), 1),
    "ex_episodes": round(100 * (r_ex - 1), 2),
    "pairs": d["meta"]["pairs"], "nlong": d["meta"]["long"], "nshort": d["meta"]["short"],
}

payload = {"series": series, "annual": annual, "stats": stats}
out = os.path.join(HERE, "payload.json")
json.dump(payload, open(out, "w"), separators=(",", ":"))
print("weekly points: %d   payload %d KB" % (len(series["x"]), os.path.getsize(out) // 1024))
print()
for k, v in stats.items():
    print("  %-14s %s" % (k, v))
print()
print("annual:", annual)
