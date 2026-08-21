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


def load_universe() -> Dict[str, Any]:
    with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_sec_filing_dates(ticker: str, cik: Optional[str]) -> Dict[int, str]:
    """Retrieve mapping of fiscal_year -> filing_date string from SEC EDGAR."""
    try:
        _, _, filings = list_available_10ks(ticker=ticker, cik=cik)
        return {f["fiscal_year"]: f["filing_date"] for f in filings if "fiscal_year" in f and "filing_date" in f}
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

    if sub_prices.empty or sub_bench.empty:
        # If delisted failed bank with no direct yfinance data, check if failure occurred after filing date
        if terminal_event:
            fail_date = pd.to_datetime(terminal_event["failure_date"])
            if fail_date >= ts_date:
                res["valid"] = True
                for h in HORIZON_DAYS:
                    res["nominal"][h] = -1.00
                    res["excess_kre"][h] = -1.00
                res["note"] = terminal_event["note"]
                return res
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
            if 0 <= days_to_fail <= (h_days * 1.5):
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
            # Partial horizon if latest data is shorter than 12M
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

    for idx, inst in enumerate(universe, 1):
        ticker = inst["ticker"].upper()
        cik = inst.get("cik")
        name = inst["name"]
        cohort = inst["cohort"]

        logger.info(f"[{idx}/{len(universe)}] Fetching SEC filing dates for {ticker} ({name})...")
        filing_dates = get_sec_filing_dates(ticker, cik)

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

        # Brief delay to respect SEC rate limits
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
