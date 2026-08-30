"""
Bag-of-words baseline — the Lazy Prices signal, computed without any LLM.

Cohen, Malloy & Nguyen (2020) obtain t=3.59 using plain term-frequency document
similarity. Unsaid's entire premise is that semantic LLM classification beats
that, and it has never been tested against it. This computes their measures on
the same filings so the two signals can be compared head to head:

  Sim_Cosine   cosine similarity of term-frequency vectors
  Sim_Jaccard  |intersection| / |union| of the term sets
  Sim_Simple   1 - (changed + added + deleted words) / average document size

Sim_MinEdit is omitted: word-level edit distance over 40k-word filings is
O(n*m) and intractable here. The paper reports the four measures as highly
correlated, so three is sufficient for a baseline.

Similarity is computed on the extracted Item 1A and Item 7A text rather than the
whole filing. That differs from the paper, which uses the full document, but it
matches what Unsaid actually scores -- so the comparison isolates the SIGNAL
(semantic vs bag-of-words) rather than confounding it with section selection.

No LLM calls. Cost is fetch + extract only, and results are cached per pair.

Usage:
    python research/banking_study/08_similarity_baseline.py --all --workers 8
"""
import os
import sys
import json
import time
import argparse
import logging
import threading
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, Optional, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("similarity")

SCRIPT_DIR = Path(__file__).resolve().parent
UNIVERSE_FILE = SCRIPT_DIR / "universe.json"
DATA_DIR = SCRIPT_DIR / "data"
SIM_FILE = DATA_DIR / "similarity_scores.json"

_LOCK = threading.Lock()
_WORD = re.compile(r"[a-z]{2,}")

# Boilerplate that appears in every filing carries no year-over-year signal and
# inflates similarity uniformly. The paper works on full documents; this keeps
# the measure comparable across issuers of very different sizes.
_STOP = frozenset("""the of and to in a for or is are was were be been being on at by with as that this
these those it its our we us their his her they them from will may can could would should shall not no
any all such other than then there here which who whom what when where how if but into under over per
have has had do does did each more most some many much very also""".split())


def _tokens(text: str) -> List[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOP]


def sim_cosine(a: List[str], b: List[str]) -> Optional[float]:
    if not a or not b:
        return None
    ca, cb = Counter(a), Counter(b)
    common = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in common)
    na = sum(v * v for v in ca.values()) ** 0.5
    nb = sum(v * v for v in cb.values()) ** 0.5
    return round(dot / (na * nb), 6) if na and nb else None


def sim_jaccard(a: List[str], b: List[str]) -> Optional[float]:
    if not a or not b:
        return None
    sa, sb = set(a), set(b)
    union = sa | sb
    return round(len(sa & sb) / len(union), 6) if union else None


def sim_simple(a: List[str], b: List[str]) -> Optional[float]:
    """
    1 - (changed + added + deleted words) / average document size.

    Mirrors the paper's description: count the words in the additions, deletions
    and modifications, then normalise by the mean length of the two documents.
    Multiset difference approximates a diff without paying for alignment.
    """
    if not a or not b:
        return None
    ca, cb = Counter(a), Counter(b)
    changed = sum((ca - cb).values()) + sum((cb - ca).values())
    avg_size = (len(a) + len(b)) / 2.0
    return round(max(0.0, 1.0 - changed / avg_size), 6) if avg_size else None


def measure_pair(y1_text: str, y2_text: str) -> Dict[str, Any]:
    a, b = _tokens(y1_text), _tokens(y2_text)
    return {
        "sim_cosine": sim_cosine(a, b),
        "sim_jaccard": sim_jaccard(a, b),
        "sim_simple": sim_simple(a, b),
        "words_y1": len(a),
        "words_y2": len(b),
    }


def process_pair(inst: Dict[str, Any], year1: int, year2: int) -> Dict[str, Any]:
    from unsaid.fetcher import get_10k_filing
    from unsaid.extractor import extract_both_sections

    ticker = inst["ticker"]
    f1, company = get_10k_filing(ticker=ticker, cik=inst.get("cik"), year=year1)
    f2, _ = get_10k_filing(ticker=ticker, cik=inst.get("cik"), year=year2)
    s1 = extract_both_sections(f1)
    s2 = extract_both_sections(f2)

    out: Dict[str, Any] = {
        "ticker": ticker, "name": inst["name"], "cohort": inst["cohort"],
        "year1": year1, "year2": year2, "company_name": company,
        "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    for label, key in (("1A", "item1a"), ("7A", "item7a")):
        t1, t2 = s1.get(label), s2.get(label)
        out[key] = measure_pair(t1, t2) if (t1 and t2) else None
    # The combined score requires Item 1A on both sides. Item 7A alone is a
    # ~250-char cross-reference for two thirds of the universe, so without 1A
    # the concatenation would be a stub-to-stub comparison reported under the
    # same name as everyone else's 1A+7A -- a different measurement wearing the
    # same label, which is exactly what makes cross-bank cuts meaningless.
    both1 = " ".join(x for x in (s1.get("1A"), s1.get("7A")) if x)
    both2 = " ".join(x for x in (s2.get("1A"), s2.get("7A")) if x)
    has_1a = bool(s1.get("1A")) and bool(s2.get("1A"))
    out["combined"] = measure_pair(both1, both2) if (has_1a and both1 and both2) else None
    return out


def assert_unique_tickers(universe) -> None:
    """
    Fail fast if two entries would collide on the result key.

    A duplicate is never harmless: the pair count silently drops, half the work
    is discarded, and if the duplicates carry different CIKs the surviving record
    depends on thread scheduling.
    """
    import collections
    counts = collections.Counter(e["ticker"].upper() for e in universe)
    dupes = {t: n for t, n in counts.items() if n > 1}
    if dupes:
        detail = []
        for t in sorted(dupes):
            ciks = sorted({(e.get("cik") or "?") for e in universe if e["ticker"].upper() == t})
            detail.append("%s x%d (CIKs: %s)" % (t, dupes[t], ", ".join(ciks)))
        raise SystemExit(
            "Universe contains duplicate tickers, which collide on the "
            "{ticker}_{year1}_{year2} result key and silently overwrite each other: "
            + "; ".join(detail)
            + ". Remove the duplicates before running."
        )


def main():
    ap = argparse.ArgumentParser(description="Bag-of-words similarity baseline (no LLM)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--tickers", type=str)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    universe = json.loads(UNIVERSE_FILE.read_text(encoding="utf-8"))
    targets = universe["universe"]
    assert_unique_tickers(targets)
    if args.tickers:
        sel = {t.strip().upper() for t in args.tickers.split(",")}
        targets = [u for u in targets if u["ticker"].upper() in sel]
    pairs = universe["comparison_pairs"]

    state: Dict[str, Any] = {}
    if SIM_FILE.exists() and not args.force:
        try:
            state = json.loads(SIM_FILE.read_text(encoding="utf-8")).get("results", {})
        except Exception:
            state = {}

    def save():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SIM_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                   "results": state}, indent=2), encoding="utf-8")
        os.replace(tmp, SIM_FILE)

    tasks = [(u, p) for u in targets for p in pairs
             if f"{u['ticker']}_{p['year1']}_{p['year2']}" not in state]
    logger.info("Computing similarity for %d pair(s) across %d worker(s). No LLM calls.",
                len(tasks), args.workers)

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {pool.submit(process_pair, u, p["year1"], p["year2"]): (u, p) for u, p in tasks}
        for fut in as_completed(futs):
            u, p = futs[fut]
            key = f"{u['ticker']}_{p['year1']}_{p['year2']}"
            try:
                res = fut.result()
            except Exception as e:
                res = {"ticker": u["ticker"], "year1": p["year1"], "year2": p["year2"],
                       "error": f"{type(e).__name__}: {e}"}
            with _LOCK:
                state[key] = res
                save()
            done += 1
            c = (res.get("combined") or {}).get("sim_cosine")
            logger.info("[%d/%d] %-18s cosine=%s", done, len(tasks), key,
                        f"{c:.4f}" if c is not None else res.get("error", "n/a")[:40])

    ok = sum(1 for v in state.values() if v.get("combined"))
    logger.info("Done. %d/%d pairs have a combined similarity score -> %s", ok, len(state), SIM_FILE)


if __name__ == "__main__":
    main()
