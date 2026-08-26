# Empirical Backtest Results: US Banking 10-K Disclosure Removals

**Generated**: 2026-08-26 17:08:46 UTC

**Total Entity-Year Observations**: `224`


## 1. Long/Short Strategy Performance (Q1 Clean vs. Q5 Heavy Removals)

Strategy: **Long Q1 (Low/No Removals)** | **Short Q5 (High Deletions/Softened Disclosures)**


| Horizon | Long Q1 Return | Short Q5 Return | Long/Short Spread (Nominal) | Alpha vs KRE (Excess Spread) | Correlation (Score vs Return) | Welch t (Q1-Q5) | Sig. 95% |
|---|---|---|---|---|---|---|---|
| **1M** | `+2.63%` | `+1.13%` | **`+2.51%`** | **`+1.51%`** | `-0.054` | `+0.50` | no |
| **3M** | `+2.28%` | `+2.46%` | **`+0.43%`** | **`-0.18%`** | `-0.017` | `-0.04` | no |
| **6M** | `+3.14%` | `+2.06%` | **`+1.80%`** | **`+1.08%`** | `-0.053` | `+0.23` | no |
| **12M** | `+5.44%` | `+6.02%` | **`+1.36%`** | **`-0.58%`** | `-0.000` | `-0.11` | no |

Quintile sample sizes: Q1 n=39, Q5 n=37. t is Welch's two-sample statistic on excess-vs-KRE returns; |t| >= 1.96 is the 95% threshold.



## 2. Top Removal Cases & Subsequent Market Drawdowns


| Ticker | Institution Name | Year | Removal Score (per Y1 unit) | Y1 Units | Item 1A/7A Removals | 6M Excess Return vs KRE | Status / Note |
|---|---|---|---|---|---|---|---|
| **CFG** | Citizens Financial Group | FY2021→FY2022 | `1.720` | 364 | 308 Removed / 1 Softened | **`-5.64%`** | crisis_distressed |
| **TFC** | Truist Financial Corp | FY2021→FY2022 | `1.605` | 489 | 388 Removed / 2 Softened | **`-6.66%`** | regional_midcap |
| **RF** | Regions Financial Corp | FY2022→FY2023 | `1.411` | 336 | 230 Removed / 4 Softened | **`+5.42%`** | crisis_distressed |
| **SIVB** | SVB Financial Group | FY2021→FY2022 | `0.875` | 16 | 4 Removed / 4 Softened | **`-82.21%`** | crisis_distressed |
| **CFG** | Citizens Financial Group | FY2020→FY2021 | `0.853` | 1479 | 509 Removed / 24 Softened | **`-15.83%`** | crisis_distressed |
| **COLB** | Columbia Banking System | FY2022→FY2023 | `0.799` | 82 | 37 Removed / 0 Softened | **`+22.16%`** | regional_midcap |
| **FCNCA** | First Citizens BancShares | FY2021→FY2022 | `0.662` | 114 | 33 Removed / 7 Softened | **`+111.28%`** | regional_midcap |
| **SI** | Silvergate Capital Corp | FY2019→FY2020 | `0.644` | 94 | 20 Removed / 7 Softened | **`N/A`** | crisis_distressed |
| **ZION** | Zions Bancorporation | FY2020→FY2021 | `0.617` | 47 | 12 Removed / 6 Softened | **`-6.17%`** | crisis_distressed |
| **FCNCA** | First Citizens BancShares | FY2020→FY2021 | `0.615` | 135 | 41 Removed / 11 Softened | **`+17.17%`** | regional_midcap |


## 3. Key Findings & Empirical Takeaways


1. **No significant long/short spread**: the Q1-minus-Q5 excess-return spread is 1M +1.51%, 3M -0.18%, 6M +1.08%, 12M -0.58%, and no horizon reaches the 95% threshold (all |t| < 1.96). On this sample the hypothesis that disclosure removals predict negative forward excess returns is **not supported**.

2. **Removal score carries no linear signal**: correlations between removal score and excess return are 1M -0.054, 3M -0.017, 6M -0.053, 12M -0.000, all below |0.10| and indistinguishable from noise.

3. **Caveats bounding these numbers**: 27 of 224 observations have no usable return series and drop out of the cross-section, affecting 8 tickers (BK, CMA, IBTX, NYCB, PACW, SI, SIVB, SNV); 19 observations could not be scored reliably and are excluded (fewer than 10 Year-1 units, more NEW units than Year-1 units, or no Year-1 unit matching anything in Year-2 -- all of which indicate extraction failure rather than disclosure behaviour): BK, C, COLB, FHN, FITB, SSB, TFC, USB, WFC; extraction yield still varies widely across filings (1 to 1615 units per pair), so the per-unit score reduces but does not eliminate extractor-driven variance.
