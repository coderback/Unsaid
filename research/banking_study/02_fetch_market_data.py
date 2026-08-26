"""
Market Data & Filing Date-Aligned Forward Return Engine.

Calculates multi-horizon forward returns (1M, 3M, 6M, 12M) aligned strictly to SEC 10-K
filing acceptance dates (+1 trading day) to eliminate look-ahead bias. Computes both
nominal returns and excess alpha over the sector benchmark (KRE).

Usage:
    python research/banking_study/02_fetch_market_data.py
    python research/banking_study/02_fetch_market_data.py --tickers SIVB,FRC,WAL
"""
import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unsaid.fetcher import list_available_10ks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("market_data")

SCRIPT_DIR = Path(__file__).resolve().parent
UNIVERSE_FILE = SCRIPT_DIR / "universe.json"
DATA_DIR = SCRIPT_DIR / "data"
RETURNS_JSON = DATA_DIR / "market_returns.json"
RETURNS_CSV = DATA_DIR / "market_returns.csv"
# EDGAR filing dates are immutable once filed; cache them so re-runs skip the
# ~30 minutes of lookups and an interrupted run can resume where it stopped.
FILING_DATES_CACHE = DATA_DIR / "filing_dates.json"

# Known receivership/terminal events for failed institutions during the 2023 crisis
FAILED_BANK_TERMINAL_EVENTS: Dict[str, Dict[str, Any]] = {
    "SIVB": {"failure_date": "2023-03-10", "terminal_return": -1.00, "note": "FDIC Receivership March 10, 2023"},
    "SBNY": {"failure_date": "2023-03-12", "terminal_return": -1.00, "note": "FDIC Receivership March 12, 2023"},
    "SI":   {"failure_date": "2023-03-08", "terminal_return": -1.00, "note": "Voluntary Liquidation March 8, 2023"},
    "FRC":  {"failure_date": "2023-05-01", "terminal_return": -1.00, "note": "FDIC Receivership May 1, 2023 (Acquired by JPM)"},
}

HORIZON_DAYS = {
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "12M": 252,
}

# HORIZON_DAYS is in trading days; failure gaps are measured in calendar days.
# ~252 trading days per 365 calendar days.
TRADING_TO_CALENDAR = 1.45

# A price series trailing the benchmark by more than this many calendar days is
# treated as dead rather than merely incomplete.
STALE_SERIES_DAYS = 10


def load_universe() -> Dict[str, Any]:
    with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_filing_date_cache() -> Dict[str, Dict[str, str]]:
    if FILING_DATES_CACHE.exists():
        try:
            with open(FILING_DATES_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not read filing-date cache ({e}); rebuilding.")
    return {}


def save_filing_date_cache(cache: Dict[str, Dict[str, str]]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(FILING_DATES_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)


def get_sec_filing_dates(ticker: str, cik: Optional[str]) -> Dict[int, str]:
    """Retrieve mapping of fiscal_year -> filing_date string from SEC EDGAR."""
    try:
        _, _, filings = list_available_10ks(ticker=ticker, cik=cik)
        dates = {f["year"]: f["filing_date"] for f in filings if f.get("year") and f.get("filing_date")}
        if not dates:
            logger.warning(f"[{ticker}] SEC returned no usable filing dates; approximate fallback will be used.")
        return dates
    except Exception as e:
        logger.warning(f"[{ticker}] Could not query SEC filing dates: {e}")
        return {}


def download_historical_prices(symbols: List[str], start_date: str = "2019-01-01") -> pd.DataFrame:
    """Download daily adjusted close prices for given symbols using yfinance."""
    import yfinance as yf

    logger.info(f"Downloading historical price series for {len(symbols)} symbols from {start_date}...")
    df = yf.download(
        tickers=symbols,
        start=start_date,
        end=datetime.now().strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=True,
        progress=False,
    )

    if isinstance(df.columns, pd.MultiIndex):
        if "Close" in df.columns.levels[0]:
            return df["Close"]
        return df.xs("Close", level=0, axis=1)
    return df


def calculate_forward_returns(
    price_series: pd.Series,
    benchmark_series: pd.Series,
    trade_start_date: str,
    ticker: str,
) -> Dict[str, Any]:
    """
    Calculate forward returns over 1M, 3M, 6M, 12M windows starting from trade_start_date.
    Includes terminal failure handling for delisted banks.
    """
    res: Dict[str, Any] = {
        "trade_start_date": trade_start_date,
        "valid": False,
        "nominal": {},
        "excess_kre": {},
    }

    ts_date = pd.to_datetime(trade_start_date)

    # Check if this bank experienced failure during holding period
    terminal_event = FAILED_BANK_TERMINAL_EVENTS.get(ticker.upper())

    # Filter price series on or after start date
    sub_prices = price_series.loc[price_series.index >= ts_date].dropna()
    sub_bench = benchmark_series.loc[benchmark_series.index >= ts_date].dropna()

    if sub_bench.empty:
        return res

    # A usable series must exist AND actually begin at the trade start. A delisted
    # ticker later reassigned to a different instrument returns prices from years
    # after the window; reading iloc[0] there would fabricate a return from an
    # unrelated stock.
    series_covers_window = (
        not sub_prices.empty
        and (sub_prices.index[0] - ts_date).days <= STALE_SERIES_DAYS
    )

    if not series_covers_window:
        # No usable price data. A known failure still tells us the answer, but only
        # for horizons the failure actually spans -- a failure years beyond the
        # horizon says nothing about that horizon's return, so it stays missing.
        if terminal_event:
            fail_date = pd.to_datetime(terminal_event["failure_date"])
            days_to_fail = (fail_date - ts_date).days
            b0 = sub_bench.iloc[0]
            for h_name, h_days in HORIZON_DAYS.items():
                if 0 <= days_to_fail <= (h_days * TRADING_TO_CALENDAR):
                    bench_sub = sub_bench.loc[sub_bench.index <= fail_date]
                    b_ret = (bench_sub.iloc[-1] / b0) - 1.0 if not bench_sub.empty else 0.0
                    res["nominal"][h_name] = -1.00
                    res["excess_kre"][h_name] = round(float(-1.00 - b_ret), 4)
            if res["nominal"]:
                res["valid"] = True
                res["note"] = terminal_event["note"]
                return res
        res["note"] = "price series does not cover the trade window (delisted or reassigned ticker)"
        return res

    p0 = sub_prices.iloc[0]
    b0 = sub_bench.iloc[0]
    res["start_price"] = float(p0)
    res["valid"] = True

    for h_name, h_days in HORIZON_DAYS.items():
        # Check if failure occurred before the horizon ended
        if terminal_event:
            fail_date = pd.to_datetime(terminal_event["failure_date"])
            days_to_fail = (fail_date - ts_date).days
            if 0 <= days_to_fail <= (h_days * TRADING_TO_CALENDAR):
                res["nominal"][h_name] = -1.00
                # Benchmark return up to failure
                bench_sub = sub_bench.loc[sub_bench.index <= fail_date]
                b_ret = (bench_sub.iloc[-1] / b0) - 1.0 if not bench_sub.empty else 0.0
                res["excess_kre"][h_name] = round(-1.00 - b_ret, 4)
                continue

        if len(sub_prices) > h_days and len(sub_bench) > h_days:
            p_end = sub_prices.iloc[h_days]
            b_end = sub_bench.iloc[h_days]
            stock_ret = (p_end / p0) - 1.0
            bench_ret = (b_end / b0) - 1.0
            excess_ret = stock_ret - bench_ret

            res["nominal"][h_name] = round(float(stock_ret), 4)
            res["excess_kre"][h_name] = round(float(excess_ret), 4)
        elif len(sub_prices) > 0 and len(sub_bench) > 0:
            # Partial horizon: legitimate only when the series is still live and
            # simply has not reached the full horizon yet. A delisted series that
            # stopped long before the benchmark must not have its final price read
            # as a current one -- that fabricates a return for a stock that is gone.
            if (sub_bench.index[-1] - sub_prices.index[-1]).days > STALE_SERIES_DAYS:
                continue
            p_end = sub_prices.iloc[-1]
            b_end = sub_bench.iloc[-1]
            stock_ret = (p_end / p0) - 1.0
            bench_ret = (b_end / b0) - 1.0
            excess_ret = stock_ret - bench_ret

            res["nominal"][h_name] = round(float(stock_ret), 4)
            res["excess_kre"][h_name] = round(float(excess_ret), 4)

    return res


def main():
    parser = argparse.ArgumentParser(description="Market Data & Forward Return Alignment Engine")
    parser.add_argument("--tickers", type=str, help="Optional comma-separated tickers to filter")
    args = parser.parse_args()

    universe_data = load_universe()
    universe = universe_data["universe"]
    pairs = universe_data["comparison_pairs"]

    if args.tickers:
        selected = {t.strip().upper() for t in args.tickers.split(",")}
        universe = [u for u in universe if u["ticker"].upper() in selected]

    all_symbols = list({u["ticker"].upper() for u in universe} | {"KRE", "XLF", "SPY"})
    prices_df = download_historical_prices(all_symbols)

    kre_series = prices_df["KRE"] if "KRE" in prices_df else pd.Series(dtype=float)

    all_returns: Dict[str, Any] = {}
    rows_for_csv: List[Dict[str, Any]] = []

    logger.info(f"Computing filing date-aligned returns for {len(universe)} institutions...")

    date_cache = load_filing_date_cache()
    cached_hits = sum(1 for u in universe if u["ticker"].upper() in date_cache)
    logger.info(
        f"Filing-date cache: {cached_hits}/{len(universe)} institutions already resolved; "
        f"{len(universe) - cached_hits} require EDGAR lookups."
    )

    for idx, inst in enumerate(universe, 1):
        ticker = inst["ticker"].upper()
        cik = inst.get("cik")
        name = inst["name"]
        cohort = inst["cohort"]

        if ticker in date_cache:
            filing_dates = {int(y): d for y, d in date_cache[ticker].items()}
        else:
            logger.info(f"[{idx}/{len(universe)}] Fetching SEC filing dates for {ticker} ({name})...")
            filing_dates = get_sec_filing_dates(ticker, cik)
            # Persist after each institution so an interrupted run resumes here.
            date_cache[ticker] = {str(y): d for y, d in filing_dates.items()}
            save_filing_date_cache(date_cache)

        p_series = prices_df[ticker] if ticker in prices_df else pd.Series(dtype=float)

        for p in pairs:
            y1 = p["year1"]
            y2 = p["year2"]
            pair_key = f"{ticker}_{y1}_{y2}"

            filing_date_y2 = filing_dates.get(y2)
            if not filing_date_y2:
                # Fallback approximate filing date if EDGAR listing was incomplete (e.g. Feb 28 of year2+1)
                filing_date_y2 = f"{y2 + 1}-02-28"

            # Trading start date is +1 business day after filing date
            trade_start = (pd.to_datetime(filing_date_y2) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

            fwd_res = calculate_forward_returns(
                price_series=p_series,
                benchmark_series=kre_series,
                trade_start_date=trade_start,
                ticker=ticker,
            )

            record = {
                "ticker": ticker,
                "cik": cik,
                "name": name,
                "cohort": cohort,
                "year1": y1,
                "year2": y2,
                "filing_date": filing_date_y2,
                "trade_start_date": trade_start,
                "nominal_1m": fwd_res.get("nominal", {}).get("1M"),
                "nominal_3m": fwd_res.get("nominal", {}).get("3M"),
                "nominal_6m": fwd_res.get("nominal", {}).get("6M"),
                "nominal_12m": fwd_res.get("nominal", {}).get("12M"),
                "excess_kre_1m": fwd_res.get("excess_kre", {}).get("1M"),
                "excess_kre_3m": fwd_res.get("excess_kre", {}).get("3M"),
                "excess_kre_6m": fwd_res.get("excess_kre", {}).get("6M"),
                "excess_kre_12m": fwd_res.get("excess_kre", {}).get("12M"),
                "note": fwd_res.get("note", ""),
            }

            all_returns[pair_key] = record
            rows_for_csv.append(record)

        # Brief delay to respect SEC rate limits (only when we queried EDGAR)
        if ticker not in date_cache or not date_cache.get(ticker):
            time.sleep(0.15)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(RETURNS_JSON, "w", encoding="utf-8") as f:
        json.dump({"created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "results": all_returns}, f, indent=2)

    df_out = pd.DataFrame(rows_for_csv)
    df_out.to_csv(RETURNS_CSV, index=False)

    logger.info(f"Market returns computed and saved to:")
    logger.info(f"  - JSON: {RETURNS_JSON}")
    logger.info(f"  - CSV:  {RETURNS_CSV}")


if __name__ == "__main__":
    main()
