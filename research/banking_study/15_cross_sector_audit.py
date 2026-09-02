"""
Does Item 1A extraction fail outside banking, and how would a naive pipeline see it?

The banking corpus had ~10% of pairs where "Item 1A" was not Item 1A, concentrated
at the extreme of the similarity ranking. Large banks are an unusually bad case --
they are the ones incorporating by reference into Exhibit 13 -- so the finding may
not generalise. If the cross-sector rate collapses, there is no methods paper.

Records two things per filing:

  naive   what edgartools returns unguarded, i.e. what most pipelines use
  gated   what this extractor returns after the plausibility bounds and the
          Exhibit 13 fallback

The difference between them is the point. A naive pipeline does not fail loudly;
it returns a pointer that scores a perfect similarity, or an over-capture that
scores a plausible one.
"""
import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent))

from unsaid.fetcher import get_10k_filing, edgar_call  # noqa: E402
from unsaid.extractor import extract_section, _html_to_prose  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("audit")
for noisy in ("httpx", "edgar", "urllib3", "unsaid.extractor"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

OUT = ROOT / "data" / "cross_sector_audit.json"

POINTER_MAX_CHARS = 8_000
OVERCAP_MIN_CHARS = 250_000

# ~50 large non-financial issuers spread across sectors. Deliberately not banks:
# the question is whether the banking failure rate is a sector artefact.
SAMPLE = [
    ("AAPL", "tech"), ("MSFT", "tech"), ("GOOGL", "tech"), ("META", "tech"),
    ("NVDA", "tech"), ("ORCL", "tech"), ("CRM", "tech"), ("ADBE", "tech"),
    ("INTC", "tech"), ("CSCO", "tech"), ("IBM", "tech"), ("QCOM", "tech"),
    ("JNJ", "health"), ("PFE", "health"), ("UNH", "health"), ("ABBV", "health"),
    ("MRK", "health"), ("TMO", "health"), ("ABT", "health"), ("LLY", "health"),
    ("PG", "consumer"), ("KO", "consumer"), ("PEP", "consumer"), ("WMT", "consumer"),
    ("MCD", "consumer"), ("NKE", "consumer"), ("HD", "consumer"), ("COST", "consumer"),
    ("TGT", "consumer"), ("SBUX", "consumer"),
    ("BA", "industrial"), ("CAT", "industrial"), ("GE", "industrial"), ("HON", "industrial"),
    ("UPS", "industrial"), ("LMT", "industrial"), ("MMM", "industrial"), ("DE", "industrial"),
    ("XOM", "energy"), ("CVX", "energy"), ("COP", "energy"), ("SLB", "energy"),
    ("T", "telecom"), ("VZ", "telecom"), ("DIS", "media"), ("CMCSA", "media"),
    ("NFLX", "media"),
    ("LIN", "materials"), ("NEE", "utilities"), ("DUK", "utilities"),
    ("AMT", "reit"), ("PLD", "reit"),
]

_LOCK = Lock()


def classify(n):
    if not n:
        return "none"
    if n < POINTER_MAX_CHARS:
        return "pointer"
    if n > OVERCAP_MIN_CHARS:
        return "overcapture"
    return "clean"


def naive_item1a(filing):
    """What an unguarded pipeline gets: edgartools' Item 1A, accepted as-is."""
    try:
        tenk = edgar_call(filing.obj)
    except Exception:
        return None
    for k in ("Item 1A", "item1a", "risk_factors", "1A"):
        try:
            raw = tenk[k]
        except Exception:
            raw = None
        if raw:
            try:
                return _html_to_prose(str(raw))
            except Exception:
                return None
    return None


def process(ticker, sector, year):
    out = {"ticker": ticker, "sector": sector, "year": year,
           "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        f, name = get_10k_filing(ticker=ticker, year=year)
        out["name"] = name
        nv = naive_item1a(f)
        out["naive_chars"] = len(nv) if nv else 0
        out["naive_class"] = classify(len(nv) if nv else 0)
        gt = extract_section(f, "1A")
        out["gated_chars"] = len(gt) if gt else 0
        out["gated_class"] = classify(len(gt) if gt else 0)
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, e)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    state = {}
    if OUT.exists():
        try:
            state = json.loads(OUT.read_text(encoding="utf-8")).get("results", {})
        except Exception:
            state = {}

    def save():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                   "year": args.year, "results": state}, indent=2),
                       encoding="utf-8")
        os.replace(tmp, OUT)

    todo = [(t, s) for t, s in SAMPLE if "%s_%d" % (t, args.year) not in state]
    logger.info("Auditing %d non-bank filings for FY%d across %d worker(s)",
                len(todo), args.year, args.workers)

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {pool.submit(process, t, s, args.year): (t, s) for t, s in todo}
        for fut in as_completed(futs):
            t, s = futs[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {"ticker": t, "sector": s, "year": args.year,
                       "error": "%s: %s" % (type(e).__name__, e)}
            with _LOCK:
                state["%s_%d" % (t, args.year)] = res
                save()
            done += 1
            logger.info("[%d/%d] %-6s naive=%-11s %7s   gated=%-11s %7s",
                        done, len(todo), t,
                        res.get("naive_class", "-"), res.get("naive_chars", "-"),
                        res.get("gated_class", "-"), res.get("gated_chars", "-"))

    logger.info("Done -> %s", OUT)


if __name__ == "__main__":
    main()
