"""
Decompose year-over-year disclosure change into ADDED and REMOVED components.

Cosine similarity is symmetric: it says how much a filing changed, never in which
direction. A firm that deleted a fifth of its risk factors and one that added a
fifth score the same. Those should not mean the same thing -- adding a risk factor
discloses bad news, while removing one either means the risk resolved or that
management stopped talking about something that did not.

That asymmetry is the part of the signal Lazy Prices cannot see, and it is
computable at bag-of-words cost:

    added   = |B \\ A| / |B|     share of THIS year's vocabulary that is new
    removed = |A \\ B| / |A|     share of LAST year's vocabulary that is gone
    net     = removed - added   positive means the disclosure shrank

Reported on unigrams and on bigrams. Bigrams are the better proxy for a passage
disappearing: deleting a risk factor removes many specific word pairs, whereas
reordering a sentence preserves most single words.

Reads the text cache, so it costs EDGAR filing lookups only, not re-extraction.
Resumable: rerun to fill in whatever is missing.
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
from typing import Any, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent))

from unsaid.fetcher import get_10k_filing  # noqa: E402
from unsaid.extractor import extract_both_sections, _extractor_fingerprint  # noqa: E402
from unsaid import textcache  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("decompose")
for noisy in ("httpx", "edgar", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

DATA = ROOT / "data"
OUT = DATA / "change_decomposition.json"
UNIVERSE = ROOT / "universe.json"

# Reuse the baseline's tokenizer so the decomposition and the cosine measure
# describe the same text.
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("m08", ROOT / "08_similarity_baseline.py")
_m08 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m08)
_tokens = _m08._tokens

# Item 1A below this is a cross-reference pointer, not the section.
MIN_1A_WORDS = 2_500

_LOCK = Lock()

# Fingerprints whose cached text is usable here, newest first. The extractor
# changed three times this branch; outside the over-capture path the output is
# byte-identical across them, verified by re-extracting ZION FY2022, WFC FY2024
# and CATY FY2023 and diffing. Newest-first means a filing that WAS corrected
# under the current extractor gets the corrected text.
_FINGERPRINTS = [_extractor_fingerprint(), "9e2f5cbe94", "29c8f6adb9"]


def cached_sections(filing) -> Dict[str, Optional[str]]:
    """Sections from cache if any fingerprint has them; extract only as a last resort."""
    acc = getattr(filing, "accession_no", None)
    if acc:
        for fp in _FINGERPRINTS:
            hit = textcache.load(acc, fp)
            if hit:
                return hit
    logger.warning("No cached text for %s; extracting (slow)", acc)
    return extract_both_sections(filing)


def _bigrams(toks: List[str]) -> Set[str]:
    return {toks[i] + "_" + toks[i + 1] for i in range(len(toks) - 1)}


def decompose(t1: str, t2: str) -> Optional[Dict[str, Any]]:
    """Directional change between two versions of the same section."""
    a, b = _tokens(t1), _tokens(t2)
    if len(a) < MIN_1A_WORDS or len(b) < MIN_1A_WORDS:
        return None
    sa, sb = set(a), set(b)
    ba, bb = _bigrams(a), _bigrams(b)
    if not sa or not sb or not ba or not bb:
        return None

    uni_add = len(sb - sa) / len(sb)
    uni_rem = len(sa - sb) / len(sa)
    bi_add = len(bb - ba) / len(bb)
    bi_rem = len(ba - bb) / len(ba)
    return {
        "words_y1": len(a), "words_y2": len(b),
        "len_change": (len(b) - len(a)) / len(a),
        "uni_added": round(uni_add, 5), "uni_removed": round(uni_rem, 5),
        "uni_net_removed": round(uni_rem - uni_add, 5),
        "bi_added": round(bi_add, 5), "bi_removed": round(bi_rem, 5),
        "bi_net_removed": round(bi_rem - bi_add, 5),
        "jaccard": round(len(sa & sb) / len(sa | sb), 5),
    }


def process(inst: Dict[str, Any], y1: int, y2: int) -> Dict[str, Any]:
    tk = inst["ticker"].upper()
    out = {"ticker": tk, "cohort": inst.get("cohort"), "year1": y1, "year2": y2,
           "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    f1, _ = get_10k_filing(ticker=tk, cik=inst.get("cik"), year=y1)
    f2, _ = get_10k_filing(ticker=tk, cik=inst.get("cik"), year=y2)
    s1, s2 = cached_sections(f1), cached_sections(f2)
    for label, key in (("1A", "item1a"), ("7A", "item7a")):
        t1, t2 = s1.get(label), s2.get(label)
        out[key] = decompose(t1, t2) if (t1 and t2) else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--tickers", type=str)
    args = ap.parse_args()

    uni = json.loads(UNIVERSE.read_text(encoding="utf-8"))
    targets = uni["universe"]
    if args.tickers:
        sel = {t.strip().upper() for t in args.tickers.split(",")}
        targets = [u for u in targets if u["ticker"].upper() in sel]
    pairs = uni["comparison_pairs"]

    state: Dict[str, Any] = {}
    if OUT.exists() and not args.force:
        try:
            state = json.loads(OUT.read_text(encoding="utf-8")).get("results", {})
        except Exception:
            state = {}

    def save():
        DATA.mkdir(parents=True, exist_ok=True)
        tmp = OUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                   "min_words": MIN_1A_WORDS, "results": state},
                                  indent=2), encoding="utf-8")
        os.replace(tmp, OUT)

    tasks = [(u, p) for u in targets for p in pairs
             if f"{u['ticker']}_{p['year1']}_{p['year2']}" not in state]
    logger.info("Decomposing %d pair(s) across %d worker(s). Text cache only, no re-extraction.",
                len(tasks), args.workers)

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = {pool.submit(process, u, p["year1"], p["year2"]): (u, p) for u, p in tasks}
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
            d = (res.get("item1a") or {})
            logger.info("[%d/%d] %-18s %s", done, len(tasks), key,
                        ("added=%.3f removed=%.3f net=%+.3f" % (
                            d["bi_added"], d["bi_removed"], d["bi_net_removed"]))
                        if d else res.get("error", "no usable Item 1A")[:44])

    ok = sum(1 for v in state.values() if v.get("item1a"))
    logger.info("Done. %d/%d pairs decomposed -> %s", ok, len(state), OUT)


if __name__ == "__main__":
    main()
