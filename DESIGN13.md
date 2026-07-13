# KRONOS-TRANSFER — Does Market Structure Transfer? (Atlas IX.1)

*Pre-registered. Every law KRONOS measured — and the trading system built on
them — was validated on ONE universe: 48 US tickers, 2010-2026. If those laws
are properties of MARKETS, they must reappear, with the same values, in
markets that share none of our tickers, currencies, or trading hours. If they
are properties of THIS SAMPLE, this study is where that gets exposed.*

## The design

Three foreign universes, one timezone block each (mixing close times would
fake decorrelation), each with a locally-listed index ETF as market proxy:
- **Japan** — 29 TSE large caps + 1306.T (TOPIX ETF).
- **Europe** — 36 large caps across XETRA/Paris/London/Amsterdam/Madrid/Milan
  + EXW1.DE (EURO STOXX 50 ETF).
- **Asia-EM** — 29 large caps across HK/Korea/Taiwan/India + 2800.HK
  (Tracker Fund). Mixed holiday calendars => coverage threshold relaxed to
  0.90 with 5-day ffill (documented deviation from the US hygiene).

Two pillars, both pure reuse of validated machinery:

1. **The law battery across SPACE.** The CONSTANTS 7-quantity battery
   (roughness H, raw kurtosis, one-clock deformed kurtosis, leverage effect,
   clock commonality, raw & deformed Hawkes branching ratios), pooled over
   the full span of each universe with time-block-bootstrap sampling SDs.
   The CONSTANTS variance-ratio test then asks: does cross-UNIVERSE
   dispersion exceed within-universe sampling noise? Classification per law:
   TRANSFERS vs UNIVERSE-SPECIFIC, plus per-universe z vs the US estimate.
2. **The frozen system.** The core book (walk-forward HMM regimes ->
   regime-gated signals -> HRP+BL -> vol/CVaR/drawdown overlay) run on each
   foreign universe with EVERY hyperparameter exactly as tuned on the US.
   Zero re-tuning, zero re-fitting of config. Benchmarks: local index ETF
   and equal-weight. (Core book only — the synthesis showed overlays and
   pairs add nothing to it.)

## Pre-registered hypotheses

- **TR1**: at least 5 of the 7 laws classify TRANSFERS. (The mechanism
  claim: fat tails, one-clock collapse, roughness, leverage, near-critical
  branching are properties of markets, not of the S&P.)
- **TR2a**: the frozen system's net Sharpe is > 0 in EVERY foreign universe.
- **TR2b**: the frozen system's MaxDD is shallower than the local index's in
  EVERY foreign universe. (The honest transferable claim is risk control,
  not alpha — same as DESIGN12.)
- We report per-universe Sharpe vs equal-weight plainly, win or lose; no
  hypothesis is staked on it.

## Known caveats (declared before looking)

- The commonality quantity's block-bootstrap SD is anti-conservative (the
  gate shows the VR test can convict identical mechanisms on it once in
  three same-seed universes). A commonality conviction that is marginal
  (p just under 0.10) is weak evidence.
- One Hawkes debias curve (T = US span) is shared across universes; spans
  differ by <10%, bias difference is second-order.
- Survivorship: foreign tickers were chosen as today's large caps that
  existed in 2010 — fine for law measurement (laws are not return-level
  quantities), inflates frozen-system CAGR; another reason TR2, not CAGR,
  is the claim.

## Gate (test_transfer.py, X24)

1. SAME mechanism (three clock worlds, different seeds): >= 4/5 non-Hawkes
   laws must classify TRANSFERS and pairwise z's must be calibrated
   (median |z| < 2.5). False-positive control.
2. DIFFERENT mechanism (clock world vs constant-vol iid Gaussian world):
   kurtosis and commonality must classify UNIVERSE-SPECIFIC with |z| > 2.5.
   Power control.

## Deliverable

`run_research.py transfer` -> `research/transfer.json`: the law table
(per-universe values, VR, p, z vs US, class), the frozen-system table
(Sharpe/MaxDD/CVaR vs local index and equal-weight per universe), and the
TR1/TR2 verdicts.
