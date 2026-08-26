"""
Portfolio Construction, Statistical Testing & Backtest Evaluation Suite.

Merges Unsaid disclosure removal scores with filing-date aligned forward returns.
Constructs Quintile sorted portfolios (Q1: Lowest Removals vs. Q5: Highest Removals),
calculates Long/Short spreads, abnormal alpha over KRE, and t-test significance metrics.

Usage:
    python research/banking_study/03_portfolio_backtest.py
"""
import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backtest_eval")

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
RESULTS_DIR = SCRIPT_DIR / "results"
MANIFEST_FILE = DATA_DIR / "ingest_manifest.json"
RETURNS_FILE = DATA_DIR / "market_returns.json"


MIN_Y1_UNITS = 10


def normalized_removal_score(counts: Dict[str, int], total_disclosures: int):
    """
    Removal severity per Year-1 disclosure unit; None when the pair is too thin or
    too asymmetric to score. Mirrors compute_removal_score() in 01_batch_ingest.py,
    recomputed here so an existing manifest does not require a pipeline re-run.
    """
    new_disc = counts.get("NEW", 0)
    y1_units = max(int(total_disclosures or 0) - new_disc, 0)
    if y1_units < MIN_Y1_UNITS or new_disc > y1_units:
        return None

    matched = (
        counts.get("RETAINED", 0)
        + counts.get("REWORDED", 0)
        + counts.get("SOFTENED", 0)
        + counts.get("ABSORBED", 0)
    )
    if matched == 0:
        return None
    raw = (
        2.0 * counts.get("REMOVED", 0)
        + counts.get("SOFTENED", 0)
        + counts.get("ABSORBED", 0)
        - 0.5 * counts.get("NEW", 0)
    )
    return round(raw / y1_units, 4)


def welch_t(a, b):
    """Welch's t-statistic for the difference in means of two unequal-variance samples."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return float("nan"), len(a), len(b)
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    if se == 0:
        return float("nan"), len(a), len(b)
    return float((a.mean() - b.mean()) / se), len(a), len(b)


def load_dataset() -> pd.DataFrame:
    """Merge ingestion manifest scores with market return data into a unified DataFrame."""
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_FILE}. Run 01_batch_ingest.py first.")
    if not RETURNS_FILE.exists():
        raise FileNotFoundError(f"Market returns not found at {RETURNS_FILE}. Run 02_fetch_market_data.py first.")

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest_data = json.load(f).get("results", {})
    with open(RETURNS_FILE, "r", encoding="utf-8") as f:
        returns_data = json.load(f).get("results", {})

    merged_rows = []

    for pair_key, m_item in manifest_data.items():
        if m_item.get("status") != "completed":
            continue
        r_item = returns_data.get(pair_key, {})

        row = {
            "pair_key": pair_key,
            "ticker": m_item["ticker"],
            "name": m_item.get("name", ""),
            "cohort": m_item.get("cohort", "regional_midcap"),
            "year1": m_item["year1"],
            "year2": m_item["year2"],
            "removal_score": normalized_removal_score(
                m_item.get("counts", {}), m_item.get("total_disclosures", 0)
            ),
            "removal_score_raw": m_item.get("removal_score_raw", m_item.get("removal_score")),
            "total_disclosures": m_item.get("total_disclosures", 0),
            "removed_count": m_item.get("counts", {}).get("REMOVED", 0),
            "softened_count": m_item.get("counts", {}).get("SOFTENED", 0),
            "new_count": m_item.get("counts", {}).get("NEW", 0),
            "reworded_count": m_item.get("counts", {}).get("REWORDED", 0),
            "item7a_removed": m_item.get("item7a_removed", 0),
            "item7a_softened": m_item.get("item7a_softened", 0),
            "filing_date": r_item.get("filing_date"),
            "trade_start_date": r_item.get("trade_start_date"),
            "nominal_1m": r_item.get("nominal_1m"),
            "nominal_3m": r_item.get("nominal_3m"),
            "nominal_6m": r_item.get("nominal_6m"),
            "nominal_12m": r_item.get("nominal_12m"),
            "excess_kre_1m": r_item.get("excess_kre_1m"),
            "excess_kre_3m": r_item.get("excess_kre_3m"),
            "excess_kre_6m": r_item.get("excess_kre_6m"),
            "excess_kre_12m": r_item.get("excess_kre_12m"),
        }
        merged_rows.append(row)

    df = pd.DataFrame(merged_rows)
    scored = int(df["removal_score"].notna().sum()) if "removal_score" in df.columns else 0
    logger.info(
        f"Loaded {len(df)} merged analysis-return observations "
        f"({scored} with a reliable normalized removal score, "
        f"{len(df) - scored} excluded as too thin or asymmetric)."
    )
    return df


def run_cross_sectional_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Sort cross-sections into quintiles and compute long/short spread performance."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results_summary: Dict[str, Any] = {
        "total_observations": len(df),
        "horizons": {},
        "quintile_means": {},
    }

    horizons = ["1m", "3m", "6m", "12m"]

    # Quintile Sort on removal_score
    df_valid = df.dropna(subset=["removal_score", "nominal_6m"]).copy()

    if df_valid.empty:
        logger.warning("No valid observations with returns for backtest calculation.")
        return results_summary

    # Assign quintiles per comparison year
    df_valid["quintile"] = df_valid.groupby("year2")["removal_score"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 5, labels=["Q1_Lowest", "Q2", "Q3", "Q4", "Q5_Highest"])
        if len(x) >= 5 else ["Q3"] * len(x)
    )

    # Compute mean returns by quintile
    for h in horizons:
        excess_col = f"excess_kre_{h}"
        nom_col = f"nominal_{h}"

        q_excess = df_valid.groupby("quintile", observed=False)[excess_col].mean().to_dict()
        q_nom = df_valid.groupby("quintile", observed=False)[nom_col].mean().to_dict()

        q1_excess = q_excess.get("Q1_Lowest", 0.0)
        q5_excess = q_excess.get("Q5_Highest", 0.0)
        spread_excess = q1_excess - q5_excess

        q1_nom = q_nom.get("Q1_Lowest", 0.0)
        q5_nom = q_nom.get("Q5_Highest", 0.0)
        spread_nom = q1_nom - q5_nom

        # Correlation between removal score and forward return
        corr = df_valid["removal_score"].corr(df_valid[excess_col])

        q1_vals = df_valid.loc[df_valid["quintile"] == "Q1_Lowest", excess_col]
        q5_vals = df_valid.loc[df_valid["quintile"] == "Q5_Highest", excess_col]
        t_stat, n_q1, n_q5 = welch_t(q1_vals, q5_vals)

        results_summary["horizons"][h] = {
            "spread_excess_kre": round(float(spread_excess) * 100, 2),
            "spread_nominal": round(float(spread_nom) * 100, 2),
            "q1_lowest_removals_mean": round(float(q1_excess) * 100, 2),
            "q5_highest_removals_mean": round(float(q5_excess) * 100, 2),
            "correlation_score_vs_excess": round(float(corr), 4) if not np.isnan(corr) else 0.0,
            "t_stat_q1_minus_q5": round(t_stat, 3) if not np.isnan(t_stat) else None,
            "n_q1": int(n_q1),
            "n_q5": int(n_q5),
            "significant_at_95": bool(not np.isnan(t_stat) and abs(t_stat) >= 1.96),
        }

    return results_summary


def derive_findings(summary: Dict[str, Any], df: pd.DataFrame) -> List[str]:
    """
    State what the computed numbers actually show.

    This must never assert a direction the data does not support: the hypothesis
    is on trial here, and a null result is a legitimate outcome to report.
    """
    horizons = summary.get("horizons", {})
    if not horizons:
        return ["1. **No result**: no horizon produced enough valid observations to evaluate."]

    findings: List[str] = []

    sig = [h for h, d in horizons.items() if d.get("significant_at_95")]
    spreads = {h: d["spread_excess_kre"] for h, d in horizons.items()}
    positive = [h for h, v in spreads.items() if v > 0]
    negative = [h for h, v in spreads.items() if v < 0]

    if not sig:
        span = ", ".join(f"{h.upper()} {v:+.2f}%" for h, v in spreads.items())
        findings.append(
            f"1. **No significant long/short spread**: the Q1-minus-Q5 excess-return spread is "
            f"{span}, and no horizon reaches the 95% threshold (all |t| < 1.96). On this sample "
            f"the hypothesis that disclosure removals predict negative forward excess returns is "
            f"**not supported**."
        )
    elif len(positive) >= len(negative):
        span = ", ".join(f"{h.upper()} {spreads[h]:+.2f}%" for h in sig)
        findings.append(
            f"1. **Spread in the hypothesised direction**: Q1 (clean) outperforms Q5 (heavy "
            f"removals) at {span}, significant at 95%. Directionally consistent with the Lazy "
            f"Prices anomaly."
        )
    else:
        span = ", ".join(f"{h.upper()} {spreads[h]:+.2f}%" for h in sig)
        findings.append(
            f"1. **Spread significant but inverted**: Q5 (heavy removals) *outperforms* Q1 at "
            f"{span}. This is the opposite of the hypothesised direction and is evidence against "
            f"the thesis as currently operationalised, not a tradable signal."
        )

    corrs = {h: d["correlation_score_vs_excess"] for h, d in horizons.items()}
    max_abs = max(abs(v) for v in corrs.values())
    corr_span = ", ".join(f"{h.upper()} {v:+.3f}" for h, v in corrs.items())
    if max_abs < 0.10:
        findings.append(
            f"2. **Removal score carries no linear signal**: correlations between removal score "
            f"and excess return are {corr_span}, all below |0.10| and indistinguishable from noise."
        )
    else:
        findings.append(f"2. **Removal score correlation**: {corr_span} (peak |r| = {max_abs:.3f}).")

    caveats = []
    if "nominal_6m" in df.columns and "ticker" in df.columns:
        dropped = df.loc[df["nominal_6m"].isna()]
        if not dropped.empty:
            affected = sorted(dropped["ticker"].unique())
            caveats.append(
                f"{len(dropped)} of {len(df)} observations have no usable return series and drop "
                f"out of the cross-section, affecting {len(affected)} tickers "
                f"({', '.join(affected)})"
            )
    if "removal_score" in df.columns and not df.empty:
        unscored = df.loc[df["removal_score"].isna()]
        if not unscored.empty:
            affected = sorted(unscored["ticker"].unique())
            caveats.append(
                f"{len(unscored)} observations could not be scored reliably and are excluded "
                f"(fewer than {MIN_Y1_UNITS} Year-1 units, more NEW units than Year-1 units, or "
                f"no Year-1 unit matching anything in Year-2 -- all of which indicate extraction "
                f"failure rather than disclosure behaviour): "
                f"{', '.join(affected)}"
            )
        spread_units = df["total_disclosures"].replace(0, pd.NA).dropna()
        if not spread_units.empty:
            caveats.append(
                f"extraction yield still varies widely across filings "
                f"({int(spread_units.min())} to {int(spread_units.max())} units per pair), so the "
                f"per-unit score reduces but does not eliminate extractor-driven variance"
            )
    if caveats:
        findings.append("3. **Caveats bounding these numbers**: " + "; ".join(caveats) + ".")

    return findings


def generate_markdown_report(summary: Dict[str, Any], df: pd.DataFrame):
    """Write executive backtest report to results/backtest_summary.md."""
    md_path = RESULTS_DIR / "backtest_summary.md"

    md = []
    md.append("# Empirical Backtest Results: US Banking 10-K Disclosure Removals\n")
    md.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    md.append(f"**Total Entity-Year Observations**: `{summary['total_observations']}`\n\n")

    md.append("## 1. Long/Short Strategy Performance (Q1 Clean vs. Q5 Heavy Removals)\n")
    md.append("Strategy: **Long Q1 (Low/No Removals)** | **Short Q5 (High Deletions/Softened Disclosures)**\n\n")
    md.append("| Horizon | Long Q1 Return | Short Q5 Return | Long/Short Spread (Nominal) | Alpha vs KRE (Excess Spread) | Correlation (Score vs Return) | Welch t (Q1-Q5) | Sig. 95% |")
    md.append("|---|---|---|---|---|---|---|---|")

    for h, data in summary.get("horizons", {}).items():
        t_val = data.get("t_stat_q1_minus_q5")
        t_disp = f"`{t_val:+.2f}`" if t_val is not None else "`n/a`"
        sig_disp = "**yes**" if data.get("significant_at_95") else "no"
        md.append(
            f"| **{h.upper()}** | `{data['q1_lowest_removals_mean']:+.2f}%` | `{data['q5_highest_removals_mean']:+.2f}%` | "
            f"**`{data['spread_nominal']:+.2f}%`** | **`{data['spread_excess_kre']:+.2f}%`** | `{data['correlation_score_vs_excess']:+.3f}` | "
            f"{t_disp} | {sig_disp} |"
        )

    n_ref = next(iter(summary.get("horizons", {}).values()), {})
    if n_ref:
        md.append(
            f"\nQuintile sample sizes: Q1 n={n_ref.get('n_q1')}, Q5 n={n_ref.get('n_q5')}. "
            "t is Welch's two-sample statistic on excess-vs-KRE returns; |t| >= 1.96 is the 95% threshold." + chr(10)
        )

    md.append("\n\n## 2. Top Removal Cases & Subsequent Market Drawdowns\n\n")
    md.append("| Ticker | Institution Name | Year | Removal Score (per Y1 unit) | Y1 Units | Item 1A/7A Removals | 6M Excess Return vs KRE | Status / Note |")
    md.append("|---|---|---|---|---|---|---|---|")

    top_removals = df.dropna(subset=["removal_score"]).sort_values(
        by="removal_score", ascending=False
    ).head(10)
    for _, row in top_removals.iterrows():
        excess_6m = f"{row['excess_kre_6m'] * 100:+.2f}%" if pd.notna(row['excess_kre_6m']) else "N/A"
        md.append(
            f"| **{row['ticker']}** | {row['name']} | FY{row['year1']}→FY{row['year2']} | "
            f"`{row['removal_score']:.3f}` | {int(row['total_disclosures']) - int(row['new_count'])} | "
            f"{row['removed_count']} Removed / {row['softened_count']} Softened | "
            f"**`{excess_6m}`** | {row['cohort']} |"
        )

    md.append("\n\n## 3. Key Findings & Empirical Takeaways\n\n")
    for line in derive_findings(summary, df):
        md.append(line + chr(10))

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    logger.info(f"Markdown summary report saved to {md_path}")


def main():
    logger.info("Running portfolio backtest and statistical evaluation...")
    df = load_dataset()
    summary = run_cross_sectional_analysis(df)
    generate_markdown_report(summary, df)
    logger.info("Backtest evaluation complete.")


if __name__ == "__main__":
    main()
