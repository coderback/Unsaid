# Signal Comparison: Bag-of-Words vs LLM Classification

Long the quiet filers, short the changers. Both signals are reported in the 
same direction, so the numbers are directly comparable.


> Everything below is **in-sample**: FY2019-2023, the period every specification in this study was searched over. FY2023->24 is held out and appears only in the pre-registered section at the end.


**In-sample pairs**: 224  
**Pairs with both signals**: 205


## Quintile long/short spread, excess vs KRE

| Signal | Horizon | Spread | Welch t | n | corr |
|---|---|---|---|---|---|
| Sim_Cosine (1A+7A) | 1M | `-0.15%` | `-0.08` | 197 | `+0.012` |
| Sim_Cosine (1A+7A) | 3M | `+0.22%` | `+0.07` | 197 | `+0.015` |
| Sim_Cosine (1A+7A) | 6M | `-1.37%` | `-0.36` | 197 | `-0.011` |
| Sim_Cosine (1A+7A) | 12M | `+3.33%` | `+0.72` | 197 | `+0.016` |
| Sim_Jaccard (1A+7A) | 1M | `+0.78%` | `+0.43` | 197 | `+0.017` |
| Sim_Jaccard (1A+7A) | 3M | `+0.44%` | `+0.13` | 197 | `+0.015` |
| Sim_Jaccard (1A+7A) | 6M | `+1.23%` | `+0.30` | 197 | `+0.033` |
| Sim_Jaccard (1A+7A) | 12M | `+2.71%` | `+0.56` | 197 | `+0.076` |
| Sim_Simple (1A+7A) | 1M | `+0.63%` | `+0.35` | 197 | `+0.020` |
| Sim_Simple (1A+7A) | 3M | `+0.19%` | `+0.06` | 197 | `+0.015` |
| Sim_Simple (1A+7A) | 6M | `-1.14%` | `-0.29` | 197 | `+0.011` |
| Sim_Simple (1A+7A) | 12M | `+3.14%` | `+0.66` | 197 | `+0.093` |
| Sim_Cosine (Item 1A) | 1M | `+0.53%` | `+0.41` | 197 | `+0.066` |
| Sim_Cosine (Item 1A) | 3M | `+3.46%` | `+1.84` | 197 | `+0.072` |
| Sim_Cosine (Item 1A) | 6M | `+2.32%` | `+0.93` | 197 | `+0.041` |
| Sim_Cosine (Item 1A) | 12M | `+7.98%` | `+2.48` | 197 | `+0.019` |
| Sim_Cosine (Item 7A) | 1M | `+5.20%` | `+1.81` | 196 | `-0.051` |
| Sim_Cosine (Item 7A) | 3M | `+4.72%` | `+1.16` | 196 | `-0.128` |
| Sim_Cosine (Item 7A) | 6M | `+3.27%` | `+0.72` | 196 | `-0.153` |
| Sim_Cosine (Item 7A) | 12M | `+6.64%` | `+1.32` | 196 | `-0.073` |
| LLM removal score | 1M | `+0.36%` | `+0.12` | 182 | `-0.060` |
| LLM removal score | 3M | `-0.57%` | `-0.13` | 182 | `-0.020` |
| LLM removal score | 6M | `+1.08%` | `+0.22` | 182 | `-0.053` |
| LLM removal score | 12M | `-3.50%` | `-0.63` | 182 | `+0.002` |

## Extraction-stable subset only


Pairs where extracted length is within 2x between years (n=215 of 224). A length collapse depresses similarity for reasons unrelated to the issuer, so this removes the clearest extraction artifacts from both signals.

| Signal | Horizon | Spread | Welch t | n |
|---|---|---|---|---|
| Sim_Cosine (1A+7A) | 1M | `-0.24%` | `-0.13` | 188 |
| Sim_Cosine (1A+7A) | 3M | `+0.97%` | `+0.28` | 188 |
| Sim_Cosine (1A+7A) | 6M | `-1.08%` | `-0.27` | 188 |
| Sim_Cosine (1A+7A) | 12M | `+2.93%` | `+0.60` | 188 |
| Sim_Jaccard (1A+7A) | 1M | `+1.20%` | `+0.62` | 188 |
| Sim_Jaccard (1A+7A) | 3M | `+1.41%` | `+0.40` | 188 |
| Sim_Jaccard (1A+7A) | 6M | `+3.18%` | `+0.77` | 188 |
| Sim_Jaccard (1A+7A) | 12M | `+2.90%` | `+0.58` | 188 |
| Sim_Simple (1A+7A) | 1M | `+0.81%` | `+0.43` | 188 |
| Sim_Simple (1A+7A) | 3M | `+0.93%` | `+0.27` | 188 |
| Sim_Simple (1A+7A) | 6M | `-0.67%` | `-0.17` | 188 |
| Sim_Simple (1A+7A) | 12M | `+2.05%` | `+0.41` | 188 |
| Sim_Cosine (Item 1A) | 1M | `+0.26%` | `+0.20` | 188 |
| Sim_Cosine (Item 1A) | 3M | `+2.99%` | `+1.55` | 188 |
| Sim_Cosine (Item 1A) | 6M | `+1.85%` | `+0.72` | 188 |
| Sim_Cosine (Item 1A) | 12M | `+7.66%` | `+2.27` | 188 |
| Sim_Cosine (Item 7A) | 1M | `+4.75%` | `+1.54` | 188 |
| Sim_Cosine (Item 7A) | 3M | `+4.65%` | `+1.08` | 188 |
| Sim_Cosine (Item 7A) | 6M | `+3.06%` | `+0.64` | 188 |
| Sim_Cosine (Item 7A) | 12M | `+5.20%` | `+0.95` | 188 |
| LLM removal score | 1M | `-0.40%` | `-0.12` | 177 |
| LLM removal score | 3M | `-1.70%` | `-0.38` | 177 |
| LLM removal score | 6M | `-0.86%` | `-0.17` | 177 |
| LLM removal score | 12M | `-3.91%` | `-0.67` | 177 |

## Item 7A, restricted to pairs that have one


Only **44** of 224 pairs compare two genuine Item 7A sections (both years between 1,000 and 15,000 words). The rest are cross-reference stubs -- most banks route market risk into MD&A and leave a ~22-word pointer -- and two stubs are near-identical by construction, so the unrestricted 7A figures elsewhere in this report are largely measuring boilerplate against boilerplate.


**This subset is severely underpowered.** At n=44 a quintile is ~8 per side, so the median split is the more honest read. Neither is a basis for a claim.

| Cut | Horizon | Spread | Welch t | n |
|---|---|---|---|---|
| Quintile | 1M | `+5.09%` | `+1.46` | 36 |
| Quintile | 3M | `+5.40%` | `+1.08` | 36 |
| Quintile | 6M | `+0.42%` | `+0.06` | 36 |
| Quintile | 12M | `+1.94%` | `+0.22` | 36 |
| Median split | 1M | `+1.71%` | `+0.94` | 36 |
| Median split | 3M | `+3.99%` | `+1.78` | 36 |
| Median split | 6M | `+2.18%` | `+0.65` | 36 |
| Median split | 12M | `+3.17%` | `+0.72` | 36 |

## Do the signals agree?


Correlation between Sim_Cosine and the LLM removal score: `-0.419` (n=205).


Similarity is high when a filing barely changed; the removal score is high when much was deleted. A strongly NEGATIVE correlation means the two are measuring the same underlying thing. A correlation near zero means the LLM is measuring something bag-of-words does not capture -- which is either the value it adds, or noise.


---


## Pre-registered out-of-sample test


Specification fixed in `EXTENSION_PLAN.md` **before this data was generated**: signal `sim_1a`, horizon `12M`, median split, long the quiet filers. One test. No other specification is run on this pair, because searching a holdout is what destroys it.


**Holdout pairs**: 53 extracted, 48 with a genuine Item 1A on both sides, 45 with a 12-month return as well.


5 pairs were excluded by a data-quality filter declared and committed **before this test was run**: both years must carry at least 2,500 words of Item 1A. Risk Factors is never legitimately that short, so below the threshold the extractor has returned a cross-reference pointer rather than the section, and two pointers score cosine=1.0000 -- pure noise at the very top of the quiet-filer ranking. The filter reads extracted text length only and never touches returns.


| Excluded | Item 1A y1 | y2 | cosine |
|---|---|---|---|
| BK | 9 w | 9 w | `1.0000` |
| USB | 17 w | 17 w | `1.0000` |
| WFC | 20 w | 20 w | `1.0000` |
| MS | 189 w | 186 w | `0.9962` |
| CFR | 1813 w | 4222 w | `0.8421` |

| Cut | Spread | Welch t | n |
|---|---|---|---|
| **Median split** (pre-registered) | `-4.95%` | `-1.01` | 45 |
| Quintile (reference) | `-2.75%` | `-0.33` | 45 |

**In-sample comparison**: the same signal and horizon gave `+7.98%` (t=2.48) on the quintile over FY2019-2023, which did not survive correction for the 24 specifications searched (family-wise p=0.131). Under the same filter applied here the in-sample figure is `+7.33%` (t=2.29, n=184) on the quintile and `-0.58%` (t=-0.22) on the median split, so the filter costs the in-sample result about 0.65pp and does not manufacture it. Those filtered figures are the like-for-like comparators.


Reading this, per the interpretation fixed in advance: a spread of similar magnitude and sign is a genuine out-of-sample replication and the strongest evidence in the project; near zero means the in-sample result was a specification artifact and the null settles cleanly; negative carries the same conclusion as near zero.


### Supplementary: FY2024->25


50 pairs. Filed Feb 2026, so **no complete 12-month return exists until Feb 2027** and none is reported here. Short horizons only, and this is not part of the pre-registered test.


| Horizon | Spread | Welch t | n |
|---|---|---|---|
| 1M | `-0.89%` | `-0.97` | 48 |
| 3M | `+4.00%` | `+1.84` | 48 |
| 6M | `+4.65%` | `+1.73` | 48 |