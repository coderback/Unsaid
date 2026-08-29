# Gold Set Evaluation: Judge vs Human Labels

**Labelled**: 55 units scored, 5 marked UNSURE, 0 unlabelled

**Overall agreement**: 33/55 = 60.0%

**Cohen's kappa**: 0.397  
(fair)


> Sample is stratified by predicted class, so per-class **precision** is the supported metric. Recall is not estimable here, and overall agreement on this sample is **not** corpus accuracy.


## Per-class precision (when the judge says X, how often does the human agree?)

| Predicted class | n | Correct | Precision |
|---|---|---|---|
| **RETAINED** | 26 | 21 | `81%` |
| **SOFTENED** | 15 | 3 | `20%` |
| **NARROWED** | 1 | 0 | `0%` |
| **REMOVED** | 9 | 6 | `67%` |
| **ABSORBED** | 4 | 3 | `75%` |

**Signal-vs-noise precision**: 18/28 = `64%` — how often a unit the judge called REMOVED/SOFTENED/ABSORBED was judged by a human to be any signal class rather than RETAINED/REWORDED. This is the number the backtest actually depends on.


## Confusion matrix (rows = human, columns = judge)

| human \\ judge | RETAINED | SOFTENED | NARROWED | REMOVED | ABSORBED |
|---|---|---|---|---|---|
| **RETAINED** | 21 | 10 | 1 | · | · |
| **SOFTENED** | · | 3 | · | 2 | · |
| **NARROWED** | · | · | · | · | · |
| **REMOVED** | 1 | · | · | 6 | 1 |
| **ABSORBED** | 4 | 2 | · | 1 | 3 |

## Disagreements (22)

| Task | Human | Judge | Judge's reasoning |
|---|---|---|---|
| `T001` | **ABSORBED** | REMOVED | None of the Year-2020 candidates meaningfully discloses the specific economic risk of actual or perceived manipulation of digital-currency markets. They discuss |
| `T003` | **ABSORBED** | SOFTENED | Year-2 retains pandemic impacts in a general disclosure, but it no longer presents the specific heightened operational and business-continuity risk tied to pand |
| `T006` | **ABSORBED** | SOFTENED | Year-2 continues to disclose exchange-related deposit concentration and the possibility that an exchange’s withdrawal or failure could affect the Bank, but it d |
| `T007` | **RETAINED** | SOFTENED | Candidate 1 retains nearly all of the underlying cyber-threat exposure, attack methods, affected parties and consequences, but removes the explicit qualifier th |
| `T010` | **RETAINED** | SOFTENED | Year-2 retains a broad interest-rate/earnings risk, but omits the Year-1 disclosure's specific low-rate scenario, repricing mismatch, margin-compression mechani |
| `T011` | **RETAINED** | SOFTENED | The CCAR stress-testing and SCB exposure is retained and made more specific by the 90-basis-point increase. However, the Year-1 disclosure's pandemic-specific p |
| `T012` | **RETAINED** | NARROWED | Candidate 1 retains the core third-party-information and misrepresentation risk, including the same examples, underwriting consequences, detection timing, and d |
| `T015` | **REMOVED** | ABSORBED | Candidate 1 (Item 1A, Costs And Effects Of Litigation) preserves the Year-1 pandemic-relief exposure, government actions, related litigation, and potential judg |
| `T017` | **SOFTENED** | REMOVED | The Year-2020 candidates describe model use, interest-rate measurement, and regulatory examinations, but none preserves the Year-2019 economic risk that faulty  |
| `T018` | **RETAINED** | SOFTENED | The core examination and supervisory-action risk is retained, but the Year-2020 disclosure omits the specific remedial powers listed in Year-2019, including inj |
| `T020` | **RETAINED** | SOFTENED | The general non-U.S. securities and emerging-market liquidity risk is retained in Candidate 1, but Year-2 no longer discloses the specific pandemic/fiscal-respo |
| `T022` | **RETAINED** | SOFTENED | Candidate 1 retains the core market-driven funding-cost risk and adds investor behavior, debt-market disruption, and firm-specific concerns, but it materially d |
| `T026` | **RETAINED** | SOFTENED | The core risk of failing to keep pace with technological change is retained, but Year-2 omits the Year-1 disclosure that the business model may need to evolve,  |
| `T028` | **ABSORBED** | RETAINED | Candidate 3 reproduces the Year-1 economic risk that worsening macroeconomic conditions or a pandemic can impair consumer and commercial borrowers’ ability to p |
| `T030` | **ABSORBED** | RETAINED | Candidate 1 reproduces the Year-1 disclosure essentially verbatim, including the federal and state supervisory exposure, the entities through which it applies,  |
| `T031` | **RETAINED** | SOFTENED | Year-2 retains the size, brand, geographic, industry, third-party aggregator, and emerging-technology drivers, but omits the explicit exposure to the evolving a |
| `T034` | **ABSORBED** | RETAINED | Year-2 retains the same underlying broad market, fiscal, monetary, regulatory-policy, and general-economic risk. Although the wording is shorter and omits “busi |
| `T043` | **ABSORBED** | RETAINED | Year-2 Candidate 1 reproduces the Year-1 disclosure verbatim, including the specific risks from declining asset values, loss of observable transactions or indic |
| `T044` | **REMOVED** | RETAINED | Year-2 continues to disclose exposure to laws and regulations applicable to the financial industry, including compliance costs and potential adverse consequence |
| `T047` | **RETAINED** | SOFTENED | Candidate 1 retains the core acquired-asset accounting and discount-accretion risks, but omits the specifically disclosed earnings volatility from post-acquisit |
| `T051` | **RETAINED** | SOFTENED | Candidate 1 retains the core forward-looking risk that accounting-standard changes can materially affect reported financial results and require technology chang |
| `T060` | **SOFTENED** | REMOVED | None of the Year-2020 candidates addresses the specific economic risk that preferred stock, with board-determined superior voting, liquidation, dividend, or oth |