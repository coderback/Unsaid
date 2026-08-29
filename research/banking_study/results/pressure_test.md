# Pressure Test: Item 1A Similarity, 12-Month Horizon


**Baseline**: `+7.98%` spread, t = `+2.48`, n = 197


## 1. Per-year cross-sections

If one year carries the whole result it is an episode, not a signal.

| FY | Spread | t | n |
|---|---|---|---|
| 2020 | `+6.58%` | `+0.87` | 49 |
| 2021 | `+3.62%` | `+0.83` | 49 |
| 2022 | `+11.38%` | `+1.58` | 50 |
| 2023 | `+10.67%` | `+1.45` | 49 |

## 2. Subsample and outlier robustness

| Variant | Spread | t | n |
|---|---|---|---|
| All pairs (baseline) | `+7.98%` | `+2.48` | 197 |
| Excluding crisis cohort | `+8.49%` | `+2.33` | 172 |
| Crisis cohort only | `-23.42%` | `-1.24` | 25 |
| Excluding terminal (-100%) returns | `+7.98%` | `+2.48` | 197 |
| Extraction-stable only | `+7.66%` | `+2.27` | 188 |
| Winsorised returns (5/95) | `+6.17%` | `+2.20` | 197 |

## 3. Alternative portfolio cuts

| Cut | Spread | t | n |
|---|---|---|---|
| Decile (top/bottom 10%) | `+5.17%` | `+1.04` | 197 |
| Quintile (baseline) | `+7.98%` | `+2.48` | 197 |
| Median split | `+0.16%` | `+0.06` | 197 |

## 4. Rank correlation


Spearman rho between Item 1A similarity and 12M excess return: `+0.099` (n=197).


The quintile spread compares tails; rho uses the whole distribution. A spread with no matching monotone relationship is usually a tail artifact.


## 5. Permutation test


Returns shuffled against signals, 5000 draws.


- **This specification alone**: `p = 0.0118` (59 of 5000 draws reached |t| >= 2.48)

- **Family-wise across all 24 specifications**: `p = 0.1310` (131 of 1000 draws had ANY specification reach |t| >= 2.48)


The family-wise figure is the one that matters. 24 specifications were examined before this result was singled out, so the relevant question is how often chance produces a t this large SOMEWHERE among 24 tries, not how often it produces one in a pre-registered test.


## Verdict

**DOES NOT SURVIVE multiplicity correction** at the 5% level once the 24 specifications are accounted for (family-wise p = 0.1310).
