# Signal Comparison: Bag-of-Words vs LLM Classification

Long the quiet filers, short the changers. Both signals are reported in the 
same direction, so the numbers are directly comparable.


**Pairs with similarity scores**: 222  
**Pairs with both signals**: 202


## Quintile long/short spread, excess vs KRE

| Signal | Horizon | Spread | Welch t | n | corr |
|---|---|---|---|---|---|
| Sim_Cosine (1A+7A) | 1M | `-0.35%` | `-0.20` | 195 | `+0.014` |
| Sim_Cosine (1A+7A) | 3M | `+0.28%` | `+0.08` | 195 | `+0.017` |
| Sim_Cosine (1A+7A) | 6M | `-1.09%` | `-0.28` | 195 | `-0.010` |
| Sim_Cosine (1A+7A) | 12M | `+4.27%` | `+0.91` | 195 | `+0.016` |
| Sim_Jaccard (1A+7A) | 1M | `+0.97%` | `+0.52` | 195 | `+0.018` |
| Sim_Jaccard (1A+7A) | 3M | `+0.25%` | `+0.07` | 195 | `+0.016` |
| Sim_Jaccard (1A+7A) | 6M | `+1.49%` | `+0.37` | 195 | `+0.033` |
| Sim_Jaccard (1A+7A) | 12M | `+2.88%` | `+0.60` | 195 | `+0.074` |
| Sim_Simple (1A+7A) | 1M | `+0.36%` | `+0.20` | 195 | `+0.024` |
| Sim_Simple (1A+7A) | 3M | `-0.03%` | `-0.01` | 195 | `+0.020` |
| Sim_Simple (1A+7A) | 6M | `-1.69%` | `-0.44` | 195 | `+0.014` |
| Sim_Simple (1A+7A) | 12M | `+2.45%` | `+0.52` | 195 | `+0.094` |
| Sim_Cosine (Item 1A) | 1M | `+0.38%` | `+0.30` | 195 | `+0.065` |
| Sim_Cosine (Item 1A) | 3M | `+3.07%` | `+1.67` | 195 | `+0.071` |
| Sim_Cosine (Item 1A) | 6M | `+2.04%` | `+0.82` | 195 | `+0.040` |
| Sim_Cosine (Item 1A) | 12M | `+7.49%` | `+2.32` | 195 | `+0.019` |
| Sim_Cosine (Item 7A) | 1M | `+5.03%` | `+1.71` | 194 | `-0.051` |
| Sim_Cosine (Item 7A) | 3M | `+4.56%` | `+1.10` | 194 | `-0.129` |
| Sim_Cosine (Item 7A) | 6M | `+3.62%` | `+0.77` | 194 | `-0.154` |
| Sim_Cosine (Item 7A) | 12M | `+7.28%` | `+1.40` | 194 | `-0.074` |
| LLM removal score | 1M | `+0.29%` | `+0.09` | 179 | `-0.060` |
| LLM removal score | 3M | `-0.23%` | `-0.05` | 179 | `-0.022` |
| LLM removal score | 6M | `+1.35%` | `+0.27` | 179 | `-0.054` |
| LLM removal score | 12M | `-3.46%` | `-0.61` | 179 | `+0.002` |

## Extraction-stable subset only


Pairs where extracted length is within 2x between years (n=214 of 222). A length collapse depresses similarity for reasons unrelated to the issuer, so this removes the clearest extraction artifacts from both signals.

| Signal | Horizon | Spread | Welch t | n |
|---|---|---|---|---|
| Sim_Cosine (1A+7A) | 1M | `-0.40%` | `-0.22` | 187 |
| Sim_Cosine (1A+7A) | 3M | `+0.56%` | `+0.16` | 187 |
| Sim_Cosine (1A+7A) | 6M | `-1.37%` | `-0.35` | 187 |
| Sim_Cosine (1A+7A) | 12M | `+2.41%` | `+0.50` | 187 |
| Sim_Jaccard (1A+7A) | 1M | `+1.04%` | `+0.54` | 187 |
| Sim_Jaccard (1A+7A) | 3M | `+0.79%` | `+0.22` | 187 |
| Sim_Jaccard (1A+7A) | 6M | `+2.81%` | `+0.68` | 187 |
| Sim_Jaccard (1A+7A) | 12M | `+2.82%` | `+0.56` | 187 |
| Sim_Simple (1A+7A) | 1M | `+0.66%` | `+0.35` | 187 |
| Sim_Simple (1A+7A) | 3M | `+0.31%` | `+0.09` | 187 |
| Sim_Simple (1A+7A) | 6M | `-1.04%` | `-0.26` | 187 |
| Sim_Simple (1A+7A) | 12M | `+1.97%` | `+0.40` | 187 |
| Sim_Cosine (Item 1A) | 1M | `-0.18%` | `-0.14` | 187 |
| Sim_Cosine (Item 1A) | 3M | `+2.42%` | `+1.27` | 187 |
| Sim_Cosine (Item 1A) | 6M | `+1.35%` | `+0.53` | 187 |
| Sim_Cosine (Item 1A) | 12M | `+7.48%` | `+2.22` | 187 |
| Sim_Cosine (Item 7A) | 1M | `+4.69%` | `+1.52` | 187 |
| Sim_Cosine (Item 7A) | 3M | `+4.28%` | `+1.00` | 187 |
| Sim_Cosine (Item 7A) | 6M | `+3.06%` | `+0.64` | 187 |
| Sim_Cosine (Item 7A) | 12M | `+4.77%` | `+0.87` | 187 |
| LLM removal score | 1M | `-0.38%` | `-0.11` | 174 |
| LLM removal score | 3M | `-1.57%` | `-0.34` | 174 |
| LLM removal score | 6M | `-0.95%` | `-0.19` | 174 |
| LLM removal score | 12M | `-4.70%` | `-0.79` | 174 |

## Do the signals agree?


Correlation between Sim_Cosine and the LLM removal score: `-0.424` (n=202).


Similarity is high when a filing barely changed; the removal score is high when much was deleted. A strongly NEGATIVE correlation means the two are measuring the same underlying thing. A correlation near zero means the LLM is measuring something bag-of-words does not capture -- which is either the value it adds, or noise.
