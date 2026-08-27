"""
Filing-level cache of extracted section text.

Extraction is the slow stage of the pipeline: edgartools parses the full 10-K
structure and the HTML fallback pulls multi-megabyte documents. Measured at
roughly 71 seconds per filing pair.

Two things make caching worth it beyond a single run:

1. Every filing is extracted TWICE across a corpus of consecutive year-pairs --
   once as Year-2 of one pair and again as Year-1 of the next. Caching by
   accession number removes that duplication outright.
2. Extraction is deterministic for a given filing and extractor version, so a
   cached result is exactly what a re-run would produce. The cache is keyed on
   the pipeline code fingerprint, so changing the extractor invalidates it
   automatically rather than serving stale text from an older parser.

Entries are content-addressed by SEC accession number, which is unique per
filing and stable across ticker changes and CIK reassignment.
"""
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "text"
_LOCK = threading.Lock()
_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def _key(accession: str, fingerprint: str) -> str:
    return "%s__%s" % (_SAFE.sub("_", str(accession)), fingerprint)


def _path(accession: str, fingerprint: str) -> Path:
    return _CACHE_DIR / ("%s.json" % _key(accession, fingerprint))


def load(accession: str, fingerprint: str) -> Optional[Dict[str, Optional[str]]]:
    """Return cached {'1A': ..., '7A': ...} for this filing, or None."""
    if not accession:
        return None
    p = _path(accession, fingerprint)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("sections")
    except Exception as e:
        logger.debug("Text cache read failed for %s: %s", accession, e)
        return None


def store(accession: str, fingerprint: str, sections: Dict[str, Optional[str]]) -> None:
    """Persist extracted sections. Never raises: a cache miss must not fail a run."""
    if not accession:
        return
    try:
        with _LOCK:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            p = _path(accession, fingerprint)
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(
                    {
                        "accession": str(accession),
                        "extractor_fingerprint": fingerprint,
                        "sections": sections,
                        "lengths": {k: (len(v) if v else 0) for k, v in sections.items()},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.replace(tmp, p)
    except Exception as e:
        logger.debug("Text cache write failed for %s: %s", accession, e)


def stats() -> Dict[str, int]:
    if not _CACHE_DIR.exists():
        return {"files": 0}
    return {"files": sum(1 for _ in _CACHE_DIR.glob("*.json"))}
