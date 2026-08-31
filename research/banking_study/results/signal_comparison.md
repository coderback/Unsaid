# Signal Comparison: Bag-of-Words vs LLM Classification

Long the quiet filers, short the changers. Both signals are reported in the 
same direction, so the numbers are directly comparable.


> Everything below is **in-sample**: FY2019-2023, the period every specification in this study was searched over. FY2023->24 is held out and appears only in the pre-registered section at the end.


**In-sample pairs**: 218  
**Pairs with both signals**: 199


## Quintile long/short spread, excess vs KRE

| Signal | Horizon | Spread | Welch t | n | corr |
|---|---|---|---|---|---|
| Sim_Cosine (1A+7A) | 1M | `+0.47%` | `+0.25` | 191 | `+0.047` |
| Sim_Cosine (1A+7A) | 3M | `+0.10%` | `+0.03` | 191 | `+0.031` |
| Sim_Cosine (1A+7A) | 6M | `-1.88%` | `-0.48` | 191 | `-0.016` |
| Sim_Cosine (1A+7A) | 12M | `+1.55%` | `+0.33` | 191 | `-0.004` |
| Sim_Jaccard (1A+7A) | 1M | `+1.33%` | `+0.68` | 191 | `+0.019` |
| Sim_Jaccard (1A+7A) | 3M | `-0.14%` | `-0.04` | 191 | `+0.003` |
| Sim_Jaccard (1A+7A) | 6M | `+0.77%` | `+0.19` | 191 | `+0.024` |
| Sim_Jaccard (1A+7A) | 12M | `+1.61%` | `+0.34` | 191 | `+0.053` |
| Sim_Simple (1A+7A) | 1M | `+0.54%` | `+0.29` | 191 | `+0.023` |
| Sim_Simple (1A+7A) | 3M | `-0.61%` | `-0.18` | 191 | `-0.008` |
| Sim_Simple (1A+7A) | 6M | `-1.59%` | `-0.41` | 191 | `-0.022` |
| Sim_Simple (1A+7A) | 12M | `+2.42%` | `+0.52` | 191 | `+0.043` |
| Sim_Cosine (Item 1A) | 1M | `+0.11%` | `+0.08` | 191 | `+0.042` |
| Sim_Cosine (Item 1A) | 3M | `+2.33%` | `+1.27` | 191 | `+0.041` |
| Sim_Cosine (Item 1A) | 6M | `+1.93%` | `+0.80` | 191 | `-0.002` |
| Sim_Cosine (Item 1A) | 12M | `+6.12%` | `+1.88` | 191 | `-0.001` |
| Sim_Cosine (Item 7A) | 1M | `+5.57%` | `+1.82` | 184 | `-0.046` |
| Sim_Cosine (Item 7A) | 3M | `+5.45%` | `+1.24` | 184 | `-0.130` |
| Sim_Cosine (Item 7A) | 6M | `+4.54%` | `+0.92` | 184 | `-0.171` |
| Sim_Cosine (Item 7A) | 12M | `+7.48%` | `+1.39` | 184 | `-0.075` |
| LLM removal score | 1M | `+0.02%` | `+0.00` | 176 | `-0.048` |
| LLM removal score | 3M | `-0.99%` | `-0.22` | 176 | `-0.002` |
| LLM removal score | 6M | `+0.34%` | `+0.07` | 176 | `-0.033` |
| LLM removal score | 12M | `-4.46%` | `-0.78` | 176 | `+0.013` |

## Extraction-stable subset only


Pairs where extracted length is within 2x between years (n=214 of 218). A length collapse depresses similarity for reasons unrelated to the issuer, so this removes the clearest extraction artifacts from both signals.

| Signal | Horizon | Spread | Welch t | n |
|---|---|---|---|---|
| Sim_Cosine (1A+7A) | 1M | `+0.28%` | `+0.15` | 187 |
| Sim_Cosine (1A+7A) | 3M | `-0.01%` | `-0.00` | 187 |
| Sim_Cosine (1A+7A) | 6M | `-1.61%` | `-0.41` | 187 |
| Sim_Cosine (1A+7A) | 12M | `+0.46%` | `+0.09` | 187 |
| Sim_Jaccard (1A+7A) | 1M | `+1.13%` | `+0.57` | 187 |
| Sim_Jaccard (1A+7A) | 3M | `+0.21%` | `+0.06` | 187 |
| Sim_Jaccard (1A+7A) | 6M | `+2.69%` | `+0.67` | 187 |
| Sim_Jaccard (1A+7A) | 12M | `+2.77%` | `+0.56` | 187 |
| Sim_Simple (1A+7A) | 1M | `+0.37%` | `+0.19` | 187 |
| Sim_Simple (1A+7A) | 3M | `-0.15%` | `-0.04` | 187 |
| Sim_Simple (1A+7A) | 6M | `-1.06%` | `-0.27` | 187 |
| Sim_Simple (1A+7A) | 12M | `+2.67%` | `+0.56` | 187 |
| Sim_Cosine (Item 1A) | 1M | `+0.42%` | `+0.33` | 187 |
| Sim_Cosine (Item 1A) | 3M | `+2.77%` | `+1.49` | 187 |
| Sim_Cosine (Item 1A) | 6M | `+2.29%` | `+0.94` | 187 |
| Sim_Cosine (Item 1A) | 12M | `+6.57%` | `+1.99` | 187 |
| Sim_Cosine (Item 7A) | 1M | `+5.56%` | `+1.81` | 183 |
| Sim_Cosine (Item 7A) | 3M | `+5.98%` | `+1.38` | 183 |
| Sim_Cosine (Item 7A) | 6M | `+5.53%` | `+1.16` | 183 |
| Sim_Cosine (Item 7A) | 12M | `+7.66%` | `+1.42` | 183 |
| LLM removal score | 1M | `-0.24%` | `-0.07` | 172 |
| LLM removal score | 3M | `-1.11%` | `-0.24` | 172 |
| LLM removal score | 6M | `-0.18%` | `-0.03` | 172 |
| LLM removal score | 12M | `-3.74%` | `-0.63` | 172 |

## Item 7A, restricted to pairs that have one


Only **47** of 218 pairs compare two genuine Item 7A sections (both years between 1,000 and 15,000 words). The rest are cross-reference stubs -- most banks route market risk into MD&A and leave a ~22-word pointer -- and two stubs are near-identical by construction, so the unrestricted 7A figures elsewhere in this report are largely measuring boilerplate against boilerplate.


**This subset is severely underpowered.** At n=47 a quintile is ~9 per side, so the median split is the more honest read. Neither is a basis for a claim.

| Cut | Horizon | Spread | Welch t | n |
|---|---|---|---|---|
| Quintile | 1M | `+3.60%` | `+1.23` | 39 |
| Quintile | 3M | `+1.33%` | `+0.31` | 39 |
| Quintile | 6M | `-0.86%` | `-0.13` | 39 |
| Quintile | 12M | `+1.22%` | `+0.14` | 39 |
| Median split | 1M | `+1.88%` | `+1.03` | 39 |
| Median split | 3M | `+2.69%` | `+1.21` | 39 |
| Median split | 6M | `-0.29%` | `-0.10` | 39 |
| Median split | 12M | `+5.11%` | `+1.14` | 39 |

## Do the signals agree?


Correlation between Sim_Cosine and the LLM removal score: `-0.240` (n=199).


Similarity is high when a filing barely changed; the removal score is high when much was deleted. A strongly NEGATIVE correlation means the two are measuring the same underlying thing. A correlation near zero means the LLM is measuring something bag-of-words does not capture -- which is either the value it adds, or noise.


---


## Pre-registered out-of-sample test


Specification fixed in `EXTENSION_PLAN.md` **before this data was generated**: signal `sim_1a`, horizon `12M`, median split, long the quiet filers. One test. No other specification is run on this pair, because searching a holdout is what destroys it.


**Holdout pairs**: 53 extracted, 52 with a genuine Item 1A on both sides, 48 with a 12-month return as well.


1 pairs were excluded by a data-quality filter declared and committed **before this test was run**: both years must carry at least 2,500 words of Item 1A. Risk Factors is never legitimately that short, so below the threshold the extractor has returned a cross-reference pointer rather than the section, and two pointers score cosine=1.0000 -- pure noise at the very top of the quiet-filer ranking. The filter reads extracted text length only and never touches returns.


| Excluded | Item 1A y1 | y2 | cosine |
|---|---|---|---|
| CFR | 1813 w | 4222 w | `0.8421` |

### The registered result


As run on 2026-08-30 under extractor fingerprint `29c8f6adb9`. This is the pre-registered out-of-sample test and it is reported as it was computed.


| Cut | Spread | Welch t | n |
|---|---|---|---|
| **Median split** &mdash; pre-registered | `-4.95%` | `-1.01` | 45 |

### Recomputed under the current extractor


The extractor was subsequently fixed to follow incorporation-by-reference into the Annual Report exhibit, which recovers a genuine Item 1A for WFC, USB and BK. Those three now pass the quality filter instead of being excluded, so the figures below are computed on a different sample from the registered one.


**This is a secondary analysis, not a second test.** The fix was motivated by extraction quality and settled before any post-fix figure existed, so it is not outcome-driven -- but it is a second look at the same holdout with a changed instrument, and a holdout is only untouched once. It is reported beside the registered result, never in place of it, whichever way it goes.


| Cut | Spread | Welch t | n |
|---|---|---|---|
| Median split &mdash; recomputed | `-3.91%` | `-0.85` | 48 |
| Quintile (reference) | `-1.09%` | `-0.13` | 48 |

**In-sample comparison**: the same signal and horizon gave `+7.98%` (t=2.48) on the quintile over FY2019-2023, which did not survive correction for the 24 specifications searched (family-wise p=0.131). Under the same filter applied here the in-sample figure is `+7.33%` (t=2.29, n=184) on the quintile and `-0.58%` (t=-0.22) on the median split, so the filter costs the in-sample result about 0.65pp and does not manufacture it. Those filtered figures are the like-for-like comparators.


Reading this, per the interpretation fixed in advance: a spread of similar magnitude and sign is a genuine out-of-sample replication and the strongest evidence in the project; near zero means the in-sample result was a specification artifact and the null settles cleanly; negative carries the same conclusion as near zero.


### Supplementary: FY2024->25


50 pairs. Filed Feb 2026, so **no complete 12-month return exists until Feb 2027** and none is reported here. Short horizons only, and this is not part of the pre-registered test.


| Horizon | Spread | Welch t | n |
|---|---|---|---|
| 1M | `-0.89%` | `-0.97` | 48 |
| 3M | `+4.00%` | `+1.84` | 48 |
| 6M | `+4.65%` | `+1.73` | 48 |