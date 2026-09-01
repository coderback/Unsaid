# Added vs removed: does direction of change matter?


> **Exploratory.** Nothing here is pre-registered. This is the same sample whose headline result failed out of sample, every horizon is reported rather than selected, and no multiplicity correction is applied. Read anything below |t| = 2 as description.


**Pairs**: 315


## Verdict


**The decomposition is a real measurement. It does not predict returns here.**


Net removal correlates with cosine similarity at `r = +0.065` -- very nearly orthogonal to the symmetric measure, so it is not a repackaging of how much a filing changed. Added and removed correlate at `+0.62` on bigrams and `+0.30` on unigrams: related, but far from interchangeable. There is a genuine second dimension here.


No cut below predicts returns. The largest statistic across 16 specifications is `|t| = 1.73`, about what 16 draws produce under the null, and it points the WRONG way for the concealment story -- heavier removers slightly outperformed at one month. Nothing here supports the hypothesis that removed disclosure is priced.


That is the expected outcome on this sample rather than a surprise. The same universe, period and benchmark that could not detect the published Lazy Prices effect cannot detect a subtler one either. What this establishes is narrower and still worth having: the signal is **constructible and independent** -- the precondition for testing it somewhere with the power to answer.


## 1. Are added and removed actually different?


If they move together there is no decomposition here.


| Pair | Pearson r |
|---|---|
| added vs removed (bigrams) | `+0.615` |
| added vs removed (unigrams) | `+0.298` |
| added vs cosine similarity | `-0.319` |
| removed vs cosine similarity | `-0.280` |
| net removal vs cosine similarity | `+0.065` |

## 2. What the components look like


| Measure | Mean | Median | Min | Max |
|---|---|---|---|---|
| bi_added | `+0.163` | `+0.150` | `+0.008` | `+0.710` |
| bi_removed | `+0.132` | `+0.112` | `+0.002` | `+0.631` |
| bi_net_removed | `-0.031` | `-0.023` | `-0.389` | `+0.297` |
| len_change | `+0.052` | `+0.030` | `-0.344` | `+0.787` |

## 3. Return predictability, quintile spreads


Each signal's direction was fixed before running, and is stated in the table.


| Signal | Long leg takes | Horizon | Spread | Welch t | n |
|---|---|---|---|---|---|
| bi_removed | long low | 1M | `-1.84%` | `-1.73` | 112 |
| bi_removed | long low | 3M | `-0.58%` | `-0.36` | 112 |
| bi_removed | long low | 6M | `+0.73%` | `+0.33` | 112 |
| bi_removed | long low | 12M | `-2.60%` | `-0.95` | 112 |
| bi_added | long low | 1M | `-0.58%` | `-0.63` | 112 |
| bi_added | long low | 3M | `+0.32%` | `+0.22` | 112 |
| bi_added | long low | 6M | `+0.27%` | `+0.15` | 112 |
| bi_added | long low | 12M | `+0.01%` | `+0.00` | 112 |
| bi_net_removed | long low | 1M | `-0.70%` | `-0.61` | 112 |
| bi_net_removed | long low | 3M | `-0.61%` | `-0.40` | 112 |
| bi_net_removed | long low | 6M | `-0.99%` | `-0.54` | 112 |
| bi_net_removed | long low | 12M | `-2.79%` | `-1.10` | 112 |
| len_change | long high | 1M | `-0.49%` | `-0.43` | 112 |
| len_change | long high | 3M | `+0.67%` | `+0.43` | 112 |
| len_change | long high | 6M | `+0.95%` | `+0.48` | 112 |
| len_change | long high | 12M | `-2.28%` | `-0.94` | 112 |

### Benchmark: the symmetric measure on the same pairs


| Signal | Horizon | Spread | Welch t | n |
|---|---|---|---|---|
| sim_cosine (long high similarity) | 1M | `-1.39%` | `-1.53` | 112 |
| sim_cosine (long high similarity) | 3M | `+1.38%` | `+0.92` | 112 |
| sim_cosine (long high similarity) | 6M | `+1.44%` | `+0.71` | 112 |
| sim_cosine (long high similarity) | 12M | `+3.57%` | `+1.25` | 112 |