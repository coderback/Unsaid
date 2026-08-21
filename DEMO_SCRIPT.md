# Unsaid — Demo Script (Move 37)

---

## Before you present

- Tab 1 open: `http://localhost:3000` (landing page)
- Tab 2 open: `http://localhost:3000/diff/SIVB` (EVE Hedging card pre-expanded)
- Filter set to: ALL SECTIONS, ALL classifications

---

## Opening (on landing page)

> "I want to show you something that happened 14 days before Silicon Valley Bank collapsed.
>
> SVB filed their FY2022 annual report — their 10-K — on February 24th, 2023. The bank failed on March 10th.
>
> The warning was in the filing. Not in the headlines, not in a press release — buried in a year-over-year change in how they described their risk. Something they said in 2021 that they quietly stopped saying in 2022.
>
> That's what Unsaid finds."

*[Click the SIVB card]*

---

## The finding (on diff page)

> "This is Unsaid's analysis of SVB's FY2021 versus FY2022 10-K. It read both filings, segmented every risk disclosure in Item 1A — that's Risk Factors — and Item 7A, which is Market Risk. Then it compared them semantically, using Claude as the judge.
>
> Four disclosures were completely removed. Four were softened. Here's the one that matters."

*[Expand "EVE Hedging — Interest Rate Swaps and Sensitivity Reduction" — REMOVED, conf 86%]*

> "In 2021, SVB disclosed that they had purchased interest rate swaps — hedges — specifically to offset their exposure to rising interest rates. Their own words: 'The addition of pay fixed swaps reduces this exposure to -13.9 percent in the same scenario.'
>
> In 2022? The Year-2 status shows one phrase: 'termination of our pay fixed swaps portfolio.'
>
> They terminated the hedges. And then they stopped disclosing the risk those hedges were protecting against."

*[Scroll to "EVE and NII Sensitivity Table" — SOFTENED, conf 72%]*

> "This is why that matters. In FY2021, SVB disclosed their EVE sensitivity table — Economic Value of Equity. Under a +200 basis point rate shock, their equity value drops 27.7 percent. That's $5.7 billion.
>
> In FY2022, the EVE column is gone. Completely removed from the table. They only show NII sensitivity — and even that collapsed from 22.9 percent down to 3.5 percent.
>
> So: they eliminated the hedges, the interest rate environment got dramatically worse, and the one table that quantified their exposure disappeared from the filing."

---

## What Unsaid is (close)

> "Unsaid does this for any public company. You give it a ticker, it pulls two consecutive 10-Ks from SEC EDGAR, segments every disclosure unit with Claude Sonnet, aligns them semantically using sentence embeddings, and then Claude Opus judges each one — was this risk retained, softened, removed, or is it new?
>
> The embeddings are only for finding candidates. Claude makes every classification. That distinction matters — keyword matching would have missed most of this.
>
> This kind of disclosure diffing exists in institutional platforms like AlphaSense. Hedge funds pay for it. Unsaid makes it free and open.
>
> The signal was there. Fourteen days before the bank run."

---

## If they ask about the model

> "Segmentation is Claude Sonnet — it breaks the raw filing text into discrete disclosure units, one coherent risk per unit. Classification is Claude Opus — it reads the Year-1 unit and the top semantic matches from Year-2 and decides what happened to that risk. The embeddings from all-mpnet-base-v2 are purely for candidate retrieval — they never determine the classification. That's a deliberate design choice. Cosine similarity can't tell you if a risk was softened."

## If they ask about false positives

> "Confidence scores are shown on every card. Claude gives a reasoning trace for each classification — you can read exactly why it called something REMOVED versus ABSORBED. The SVB EVE finding has 86% confidence on the hedging removal and 72% on the table softening. The lower confidence reflects genuine ambiguity — the NII table was restructured, not just deleted. That nuance is exactly what you want a judge to surface."

## If they ask what's next

> "Right now it covers Item 1A and Item 7A across any SEC-listed company. The pipeline runs in about five minutes on a new ticker. The obvious next step is a screener — run this across the Russell 1000 every earnings season and surface the companies with the most significant disclosure changes. That's the product."
