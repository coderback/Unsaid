"""JSON cache reader/writer. Cache files live in cache/{TICKER}_{YEAR1}_{YEAR2}.json."""
import json
import os
import glob
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")


def _cache_path(ticker: str, year1: int, year2: int) -> str:
    return os.path.join(_CACHE_DIR, f"{ticker.upper()}_{year1}_{year2}.json")


def cache_exists(ticker: str, year1: int, year2: int) -> bool:
    return os.path.exists(_cache_path(ticker, year1, year2))


def write_cache(
    ticker: str,
    company_name: str,
    year1: int,
    year2: int,
    changes: List[Dict],
) -> str:
    """Write results to cache. Returns the cache file path."""
    os.makedirs(_CACHE_DIR, exist_ok=True)

    # Build summary counts
    counts: Dict[str, int] = {}
    for change in changes:
        cls = change.get("classification", "UNKNOWN")
        counts[cls] = counts.get(cls, 0) + 1

    payload: Dict[str, Any] = {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "year1": year1,
        "year2": year2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary_counts": counts,
        "changes": changes,
    }

    path = _cache_path(ticker, year1, year2)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info("Cache written to %s", path)
    return path


def read_cache(ticker: str, year1: Optional[int] = None, year2: Optional[int] = None) -> Optional[Dict]:
    """
    Read a cached result. If year1/year2 are None, returns the first match for the ticker.
    """
    if year1 and year2:
        path = _cache_path(ticker, year1, year2)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Search by ticker only
    pattern = os.path.join(_CACHE_DIR, f"{ticker.upper()}_*.json")
    matches = sorted(glob.glob(pattern))
    if not matches:
        return None
    with open(matches[-1], "r", encoding="utf-8") as f:
        return json.load(f)


def list_cached_demos() -> List[Dict]:
    """Return metadata for all cached results."""
    demos = []
    pattern = os.path.join(_CACHE_DIR, "*.json")
    for path in sorted(glob.glob(pattern)):
        if os.path.basename(path).startswith("."):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            demos.append({
                "ticker": data.get("ticker"),
                "company_name": data.get("company_name"),
                "year1": data.get("year1"),
                "year2": data.get("year2"),
                "summary_counts": data.get("summary_counts", {}),
            })
        except Exception as e:
            logger.debug("Could not read cache file %s: %s", path, e)
    return demos
