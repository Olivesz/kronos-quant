# KRONOS-CRYPTO — Do the Mechanism Laws Survive Outside Equities? (Atlas IX.1b)

*Pre-registered. KRONOS-TRANSFER (DESIGN13) showed the mechanism laws reappear
across equity markets (Japan/Europe/Asia-EM) even when their exact values are
local. But every one of those markets shares the SAME microstructure: a
central limit-order book, an overnight gap, an institutional base, a leverage
system. Crypto breaks all four at once — 24/7 trading (no close auction, no
overnight gap), retail-momentum-dominated flow, and no financial leverage in
the equity sense. It is the sharpest available stress test of whether the laws
are properties of MARKETS or properties of the EQUITY microstructure.*

## The design

One new universe: **10 liquid, long-listed crypto assets** (BTC, ETH, XRP,
LTC, BCH, ADA, DOGE, LINK, XLM, ETC), Yahoo daily OHLC from 2017. Verified:
100% of days carry a real intraday high/low range, so Garman-Klass range
volatility — the vol proxy the whole battery rests on — is valid.

The **same 7-law battery** used by CONSTANTS and TRANSFER (roughness H, raw
kurtosis, one-clock deformed kurtosis, leverage effect, clock commonality,
Hawkes branching raw & deformed) is estimated on crypto and placed alongside
the four equity universes from TRANSFER. The CONSTANTS variance-ratio machinery
then asks, across all five, whether crypto sits inside or outside the
equity-cohort spread (pure reuse — no new estimator for the battery itself).

## Pre-registered hypotheses

- **C1 — the One-Clock law survives.** Deformed (vol-standardized) kurtosis
  lands in ~[3, 4] for crypto, as it does for every equity market — the
  conditional-Gaussianity collapse is microstructure-independent. *Kill:*
  deformed kurtosis > 5, i.e. the clock fails to gaussianize crypto returns.
- **C2 — the leverage effect weakens or INVERTS.** This is the differentiating
  prediction. Equities/bonds show a robust **negative** leverage effect
  (down → higher future vol) from financial/operating leverage and
  institutional de-risking. Crypto has neither, plus a retail FOMO dynamic, so
  we predict its leverage effect is **weaker than the equity cohort and may be
  positive (inverted)**. *Kill:* crypto's leverage is statistically
  indistinguishable in sign and magnitude from the equity cohort — in which
  case the leverage law is asset-class-universal after all (also a real
  result).
- **C3 — crypto is more reflexive.** Raw Hawkes branching ratio n ≥ the equity
  median (retail momentum → more self-excitation). Open question, reported
  either way: does the vol-deformation still collapse it toward the
  no-self-excitation null (as REFLEX found for equities)?
- **C4 — fatter raw tails.** Raw kurtosis exceeds the equity cohort (bigger,
  more frequent jumps). Low-stakes sanity prediction.

## The one new claim, and its gate

The battery machinery is already gated (X22 stability, X24 transfer). The only
NEW inferential weight this study puts on an estimator is reading the
**sign** of the leverage effect as an asset-class discriminator (C2). So that
is what gets a new gate.

**Gate X26 — leverage-sign recovery.** On three synthetic worlds with a KNOWN
leverage sign — equity-like (negative: down-moves raise next-day vol),
inverted (positive: up-moves raise vol), and symmetric (none) — the battery's
leverage estimator must recover the correct sign in each (negative, positive,
~0), with clear separation. This proves a crypto leverage reading of the
"wrong" sign is a real property of the data, not an estimator artifact.

## Scope / declared caveats

- **Laws only, not a trading system.** Crypto's enormous drift makes the frozen
  risk-control comparison (TRANSFER's TR2) uninformative; it is out of scope.
  This study is purely about mechanism transfer.
- **Shorter, later span** (2017–2026 vs equities' 2010–2026) and **survivorship**
  (today's surviving majors) — fine for distributional laws, which are not
  return-level quantities, and declared before looking.
- **Cross-crypto correlation is extreme**, so the "commonality" quantity is
  expected near its ceiling; it is reported, not hypothesised.

## Deliverable

`run_research.py crypto` → `research/crypto.json`: the 5-way law table
(4 equity universes + crypto, with per-law TRANSFERS / UNIVERSE-SPECIFIC
verdicts and crypto's z vs the equity cohort), a focused leverage-sign
contrast, and the C1–C4 verdicts. Plus a dashboard panel and a FINDINGS entry.
