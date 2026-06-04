"""EDGAR filing retrieval via edgartools."""
import time
import logging
import os
from typing import Optional, Tuple

import edgar

logger = logging.getLogger(__name__)

EDGAR_USER_AGENT = os.environ.get(
    "EDGAR_IDENTITY",
    "Unsaid/1.0 tobiojebiyi@gmail.com"
)

_last_request_time: float = 0.0
_MIN_INTERVAL = 0.12  # 10 req/s max; 120ms gives a safe margin


def _throttle():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.time()


def setup_edgar():
    edgar.set_identity(EDGAR_USER_AGENT)


def get_10k_filing(
    ticker: Optional[str] = None,
    cik: Optional[str] = None,
    year: int = 2022,
) -> Tuple[object, str]:
    """
    Fetch the 10-K filing whose period_of_report falls in `year`.
    Returns (filing, company_name).
    Either ticker or cik must be supplied.
    """
    setup_edgar()

    _throttle()
    if cik:
        cik_int = int(cik.lstrip("0") or "0")
        entity = edgar.get_entity(cik_int)
    elif ticker:
        entity = edgar.Company(ticker)
    else:
        raise ValueError("Must supply ticker or cik")

    company_name: str = getattr(entity, "name", str(ticker or cik))
    logger.info("Resolved entity: %s", company_name)

    _throttle()
    filings = entity.get_filings(form="10-K")
    if not filings or len(filings) == 0:
        raise ValueError(f"No 10-K filings found for {ticker or cik}")

    # Match by period_of_report (fiscal year end date, e.g. "2021-12-31")
    target = None
    for filing in filings:
        try:
            period = str(filing.period_of_report or "")
            if period.startswith(str(year)):
                target = filing
                break
        except Exception:
            continue

    # Fallback: match by filing date (FY N is typically filed in calendar year N+1)
    if target is None:
        filing_year = year + 1
        for filing in filings:
            try:
                fd = str(filing.filing_date or "")
                if fd.startswith(str(filing_year)):
                    target = filing
                    break
            except Exception:
                continue

    if target is None:
        raise ValueError(
            f"Could not find 10-K for fiscal year {year} "
            f"(entity: {company_name})"
        )

    logger.info(
        "Found 10-K: accession=%s period=%s filed=%s",
        getattr(target, "accession_no", "?"),
        getattr(target, "period_of_report", "?"),
        getattr(target, "filing_date", "?"),
    )
    return target, company_name
