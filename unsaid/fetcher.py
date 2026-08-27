"""EDGAR filing retrieval via edgartools."""
import time
import logging
import os
import threading
from typing import Optional, Tuple

import edgar

logger = logging.getLogger(__name__)

EDGAR_USER_AGENT = os.environ.get(
    "EDGAR_IDENTITY",
    "Unsaid/1.0 tobiojebiyi@gmail.com"
)

_last_request_time: float = 0.0
_MIN_INTERVAL = 0.12  # 10 req/s max; 120ms gives a safe margin
# Guards _last_request_time. Without it, concurrent workers each read a stale
# timestamp, all conclude no wait is needed, and burst past SEC's 10 req/s limit.
_THROTTLE_LOCK = threading.Lock()


def _throttle():
    global _last_request_time
    with _THROTTLE_LOCK:
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

    entity = None

    # If CIK is explicitly provided, prioritize CIK as the unique SEC identifier
    if cik:
        try:
            cik_int = int(cik.lstrip("0") or "0")
            e = edgar.Company(cik_int)
            test_filings = e.get_filings(form="10-K")
            if test_filings and len(test_filings) > 0:
                entity = e
            else:
                entity = edgar.get_entity(cik_int)
        except Exception:
            cik_int = int(cik.lstrip("0") or "0")
            entity = edgar.get_entity(cik_int)

    # Fall back to ticker lookup if no CIK or CIK lookup produced no entity
    if entity is None and ticker:
        try:
            e = edgar.Company(ticker)
            test_filings = e.get_filings(form="10-K")
            if test_filings and len(test_filings) > 0:
                entity = e
        except Exception:
            pass

    if entity is None:
        if cik:
            cik_int = int(cik.lstrip("0") or "0")
            entity = edgar.Company(cik_int)
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

    # 1. Prefer exact form == "10-K" matching period_of_report (avoids partial 10-K/A amendments)
    target = None
    for filing in filings:
        try:
            if str(getattr(filing, "form", "")).strip().upper() == "10-K":
                period = str(filing.period_of_report or "")
                if period.startswith(str(year)):
                    target = filing
                    break
        except Exception:
            continue

    # 2. If no exact 10-K, accept any 10-K variant matching period
    if target is None:
        for filing in filings:
            try:
                period = str(filing.period_of_report or "")
                if period.startswith(str(year)):
                    target = filing
                    break
            except Exception:
                continue

    # 3. Fallback: match by filing date (FY N is typically filed in calendar year N+1)
    if target is None:
        filing_year = year + 1
        for filing in filings:
            try:
                if str(getattr(filing, "form", "")).strip().upper() == "10-K":
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


def list_available_10ks(
    ticker: Optional[str] = None,
    cik: Optional[str] = None,
) -> Tuple[str, str, list[dict]]:
    """
    List all available 10-K filings for a company on SEC EDGAR.
    Returns (company_name, resolved_cik, list_of_filings).
    """
    setup_edgar()

    entity = None
    if cik:
        try:
            cik_int = int(cik.lstrip("0") or "0")
            e = edgar.Company(cik_int)
            test_filings = e.get_filings(form="10-K")
            if test_filings and len(test_filings) > 0:
                entity = e
            else:
                entity = edgar.get_entity(cik_int)
        except Exception:
            cik_int = int(cik.lstrip("0") or "0")
            entity = edgar.get_entity(cik_int)

    if entity is None and ticker:
        try:
            e = edgar.Company(ticker.upper())
            test_filings = e.get_filings(form="10-K")
            if test_filings and len(test_filings) > 0:
                entity = e
        except Exception:
            pass

    if entity is None:
        if cik:
            cik_int = int(cik.lstrip("0") or "0")
            entity = edgar.Company(cik_int)
        elif ticker:
            entity = edgar.Company(ticker.upper())
        else:
            raise ValueError("Must supply ticker or cik")

    company_name: str = getattr(entity, "name", str(ticker or cik))
    resolved_cik: str = str(getattr(entity, "cik", cik or ""))
    logger.info("Resolved entity for listing: %s (CIK: %s)", company_name, resolved_cik)

    _throttle()
    filings = entity.get_filings(form="10-K")
    if not filings or len(filings) == 0:
        return company_name, resolved_cik, []

    records = []
    seen_years = set()

    for filing in filings:
        try:
            period = str(getattr(filing, "period_of_report", "") or "")
            filing_date = str(getattr(filing, "filing_date", "") or "")
            accession = str(getattr(filing, "accession_no", "") or "")
            form = str(getattr(filing, "form", "10-K") or "10-K")

            year = None
            if period and len(period) >= 4 and period[:4].isdigit():
                year = int(period[:4])
            elif filing_date and len(filing_date) >= 4 and filing_date[:4].isdigit():
                year = int(filing_date[:4]) - 1

            if year and year not in seen_years:
                seen_years.add(year)
                records.append({
                    "year": year,
                    "period_of_report": period,
                    "filing_date": filing_date,
                    "accession_no": accession,
                    "form": form,
                })
        except Exception:
            continue

    records.sort(key=lambda x: x["year"], reverse=True)
    return company_name, resolved_cik, records

