# Empirical Study: US Regional Banking 10-K Disclosure Removals (2019–2023)

## 1. Research Overview & Hypothesis

**Hypothesis**: *When financial institutions systematically delete or soften specific economic risk disclosures in Form 10-K Item 1A (Risk Factors) and Item 7A (Market Risk), the stock subsequently experiences negative abnormal forward returns relative to sector benchmarks (KRE / XLF).*

This study tests the **Lazy Prices anomaly** (Cohen, Malloy, Nguyen 2020) specifically within the volatile US regional banking sector before, during, and after the 2023 regional banking crisis.

---

## 2. Universe Definition (`universe.json`)

- **Universe Size**: **60 Institutions**
- **Temporal Horizon**: **5 Fiscal Years (FY2019 – FY2023)**
- **Comparison Pairs**: **240 consecutive year-over-year filing pairs** (`19→20`, `20→21`, `21→22`, `22→23`)
- **Stratification**:
  1. **Crisis & Stress Cohort (12 banks)**: Failed/delisted banks (`SIVB`, `FRC`, `SBNY`, `SI`), merged banks (`PACW`), and pressured regional institutions (`NYCB`, `WAL`, `CMA`, `ZION`, `KEY`, `FHN`, `OZK`).
  2. **Regional & Mid-Cap Banks (38 banks)**: Core constituents of the SPDR S&P Regional Banking ETF (`KRE`).
  3. **Megabanks & G-SIBs (10 banks)**: Large, diversified control institutions (`JPM`, `BAC`, `WFC`, `C`, `GS`, `MS`, `USB`, `BK`, `STT`, `COF`).

---

## 3. Data & Backtesting Pipeline Architecture

```
research/banking_study/
├── universe.json            # Structured dataset of 60 banks, CIKs, cohorts
├── 01_batch_ingest.py       # Automated SEC EDGAR fetch + vector alignment + multi-model judge
├── 02_fetch_market_data.py  # Historical daily prices & filing-date aligned forward returns
├── 03_portfolio_backtest.py # Quintile sorting, Long/Short spread, t-stats, Sharpe ratio
├── results/                 # Analysis cache, CSV outputs, and visual plots
└── README.md                # Methodology & study documentation
```

---

## 4. Bias Mitigation & Quant Safeguards

1. **Look-Ahead Bias Elimination**:
   - Trading start dates are anchored to the SEC EDGAR **Filing Acceptance Date + 1 Trading Day** (not period end dates).
2. **Survivorship Bias Mitigation**:
   - Includes failed banks that were subsequently delisted (`SIVB`, `FRC`, `SBNY`, `SI`) with terminal return handling.
3. **Beta vs. Alpha Disentanglement**:
   - Returns are evaluated both in **nominal terms** and **excess returns over the benchmark (`KRE` and `XLF`)**.
4. **Item 7A Weighting**:
   - Item 7A (Quantitative and Qualitative Disclosures About Market Risk) removals are analyzed independently from Item 1A boilerplate.

---

## 5. Video Series Blueprint

- **Video 1: The Thesis & The Challenge**
  - Hook: *Can an algorithm detect hidden bank collapse signals months in advance?*
  - The Lazy Prices anomaly explained.
  - Setting up the 60-bank 5-year test.
- **Video 2: The Ingestion & Pipeline**
  - Building the SEC EDGAR batch runner.
  - Sentence-transformer alignment + multi-model judging.
  - Spot-checking startling disclosure deletions in 2022/2023 filings.
- **Video 3: The Quantitative Backtest**
  - Portfolio construction (High Removal Quintile vs Low Removal Quintile).
  - The forward returns, KRE alpha spread, and statistical significance.
- **Video 4: Institutional Caveats & Takeaways**
  - Nuances in disclosure analysis, sample size limits, and production realities.
