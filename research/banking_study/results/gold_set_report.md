# Gold Set Evaluation: Judge vs Human Labels

**Labelled**: 55 units scored, 5 marked UNSURE, 0 unlabelled

**Overall agreement**: 26/55 = 47.3%

**Cohen's kappa**: 0.198  
(poor (at or below chance))


> Sample is stratified by predicted class, so per-class **precision** is the supported metric. Recall is not estimable here, and overall agreement on this sample is **not** corpus accuracy.


## Per-class precision (when the judge says X, how often does the human agree?)

| Predicted class | n | Correct | Precision |
|---|---|---|---|
| **RETAINED** | 27 | 20 | `74%` |
| **REWORDED** | 1 | 0 | `0%` |
| **SOFTENED** | 16 | 1 | `6%` |
| **REMOVED** | 9 | 4 | `44%` |
| **ABSORBED** | 2 | 1 | `50%` |

**Signal-vs-noise precision**: 16/27 = `59%` — how often a unit the judge called REMOVED/SOFTENED/ABSORBED was judged by a human to be any signal class rather than RETAINED/REWORDED. This is the number the backtest actually depends on.


## Confusion matrix (rows = human, columns = judge)

| human \\ judge | RETAINED | REWORDED | SOFTENED | REMOVED | ABSORBED |
|---|---|---|---|---|---|
| **RETAINED** | 20 | 1 | 11 | · | · |
| **REWORDED** | · | · | · | · | · |
| **SOFTENED** | · | · | 1 | 3 | 1 |
| **REMOVED** | 1 | · | 3 | 4 | · |
| **ABSORBED** | 6 | · | 1 | 2 | 1 |

## Disagreements (29)

| Task | Human | Judge | Judge's reasoning |
|---|---|---|---|
| `T001` | **ABSORBED** | REMOVED | None of the Year-2020 candidates discloses the specific economic risk of actual or perceived manipulation of digital-currency markets. References to volatility, |
| `T003` | **ABSORBED** | SOFTENED | Year-2 retains the remote-work, technology-dependence, and business-continuity substance, but the explicit pandemic-driven heightened operational risk and disru |
| `T004` | **ABSORBED** | RETAINED | The Year-2022 CCAR disclosure retains the core economic risk and activity from Year-2021—regulatory capital stress testing—while adding specific CCAR frequency  |
| `T006` | **ABSORBED** | REMOVED | None of the Year-2020 candidates discloses the Year-2019 economic risk concerning exchanges’ deposit/withdrawal policies and practices, exchange liquidity, or i |
| `T007` | **RETAINED** | REWORDED | Candidate 1 preserves the underlying economic risk: increasing, sophisticated cyber threats from the same broad categories of malicious actors, with substantial |
| `T009` | **SOFTENED** | ABSORBED | The pandemic-specific continuity risk is no longer stated as such, but its core economic substance—business disruption caused by interruptions affecting the com |
| `T010` | **RETAINED** | SOFTENED | Year-2020 retains a general interest-rate/earnings risk, but it no longer presents the specific low-rate prolonged-environment scenario, repricing mismatch, mar |
| `T011` | **RETAINED** | SOFTENED | The core risk that the Federal Reserve could limit or prohibit dividends and repurchases remains in Candidate 2, but the Year-2 disclosure drops the Year-1 pand |
| `T012` | **RETAINED** | SOFTENED | Candidate 1 retains the core third-party information and misrepresentation risk, but omits the specific disclosure that the company generally bears the loss, th |
| `T015` | **REMOVED** | RETAINED | Year-2 continues to disclose the same economic risk from participation in pandemic and other government relief programs: government orders/actions, related liti |
| `T017` | **SOFTENED** | REMOVED | The Year-2020 candidates discuss regulatory examinations and interest-rate risk measurement, but none preserves the broader economic risk that faulty data, flaw |
| `T018` | **RETAINED** | SOFTENED | Year-2020 retains the examination risk and the possibility of adverse regulatory action, but omits the detailed enumeration of enforcement powers and consequenc |
| `T020` | **RETAINED** | SOFTENED | The general non-U.S. securities and emerging-market liquidity risk is retained, but the specific sovereign-debt disclosure is materially weakened: Year-2 does n |
| `T022` | **RETAINED** | SOFTENED | Candidate 1 retains the core funding-cost, interest-rate, credit-spread, volatility, and concentration risks, but drops the Year-1 quantified/specific causal qu |
| `T026` | **RETAINED** | SOFTENED | The core risk of rapid technological change and implementation challenges remains in Candidate 1, but Year-2020 omits the Year-2019 disclosures about evolving t |
| `T028` | **ABSORBED** | RETAINED | The Year-2 Macroeconomic Credit Portfolio Exposure disclosure retains the core economic risk: pandemic-related and broader macroeconomic deterioration can impai |
| `T030` | **ABSORBED** | RETAINED | Candidate 1 reproduces the Year-1 disclosure essentially verbatim and also retains the associated economic risks involving depositor and deposit-insurance prote |
| `T031` | **RETAINED** | SOFTENED | Year-2 retains the heightened-exposure disclosure and most listed drivers, but omits the material driver that cyber threats are evolving and pervasive. The digi |
| `T033` | **REMOVED** | SOFTENED | Year-2020 retains a general risk from regulatory changes, but it no longer specifically discloses the CFPB's broad consumer-protection rulemaking authority, its |
| `T034` | **ABSORBED** | RETAINED | The Year-2022 candidates continue to disclose all three underlying market risks: adverse financial-market and economic conditions, increased market volatility,  |
| `T038` | **ABSORBED** | RETAINED | Year-2020 continues to disclose the same underlying economic risk: legal and regulatory measures or changes may affect digital currencies and impair their use,  |
| `T043` | **ABSORBED** | RETAINED | Candidate 1 reproduces the Year-2021 disclosure essentially verbatim, including the effects of asset-price declines and market transaction availability, counter |
| `T044` | **REMOVED** | SOFTENED | Year-2020 retains a broad regulatory-compliance theme, but none of the candidates preserves the Year-2019 disclosure's specific consumer-protection laws (the Co |
| `T045` | **REMOVED** | SOFTENED | Year-2020 retains a general risk that funding may be unavailable or costly, but it no longer discloses the specific capital-injection scenario, the subsidiary-b |
| `T047` | **RETAINED** | SOFTENED | Year-2 retains the acquired-asset fair-value discount accretion, post-acquisition credit deterioration, and resulting earnings volatility, but omits the specifi |
| `T051` | **RETAINED** | SOFTENED | The core risk that changing accounting standards can materially affect reported results and require technology changes is retained. However, Year-2 drops the sp |
| `T052` | **SOFTENED** | REMOVED | None of the Year-2022 candidates discloses the specific short-term IRR modeling methodology: a 24-month net-interest-income forecast compared with a stable-rate |
| `T053` | **RETAINED** | SOFTENED | Candidate 1 retains the low-rate/net-interest-income downside, but no longer discloses the Year-1 realized adverse effect from a continued protracted low-rate p |
| `T060` | **SOFTENED** | REMOVED | None of the Year-2020 candidates discloses the specific economic risk that the board may issue preferred stock with superior rights, potentially delaying a chan |