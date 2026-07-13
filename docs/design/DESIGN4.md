# KRONOS-LAWS — Hunting Invariances (pre-registered screens)

*Strategy change: stop building better widgets, start hunting laws. A "law"
here = a parameter-free or universal quantitative relation that holds across
assets and asset classes, with its violations being interpretable. Each
screen below is designed to be KILLABLE today. Pre-registered before running.*

## The unifying candidate: the One-Clock Hypothesis

All of our findings so far point at a single suspect: **the volatility path
is the only clock that matters.** Returns are conditionally Gaussian given
the (rough, fat-tail-generating) volatility path; everything else we and the
literature observe — regimes, conditional fat tails, hallucinated HMM states,
leverage tails — is the volatility path wearing costumes.

This is the Clark (1973) mixture-of-distributions hypothesis sharpened by
our own results, and it makes three *quantitative, falsifiable* predictions
we can test on 48 assets across equities/bonds/gold/credit:

### Screen L1 — Deformation kills the tails (and the hallucinated regimes)
Standardize each asset's daily return by its same-day Garman-Klass vol:
z_t = r_t / sqrt(GKvar_t).
- **P1a:** kurtosis of z collapses toward 3 for EVERY asset (raw kurtosis
  ~6-25). Fit a Student-t to z: nu should explode vs raw returns.
- **P1b (ours, new):** refit the t-HMM on standardized features — the
  per-state nu's (17 / 3.7 / 300 on raw data) should all blow up toward
  Gaussian, AND the Gaussian-HMM K-curve (which rose to K=5 on raw data)
  should flatten. I.e. the hallucinated regimes die with the tails.
  This directly connects the X² mechanism paper to a *cause*.
- **P1c (universality):** after deformation, all 48 assets' z-distributions
  collapse onto ONE curve (pairwise KS distances ~ sampling noise),
  regardless of asset class. One clock, one distribution.
- Failure modes are data: where z stays fat (overnight gaps? specific
  assets?) is the residual structure a one-clock law can't explain.

### Screen L2 — A parameter-free kurtosis law
If r_t = sigma_t * eps_t with eps Gaussian and log sigma ~ Gaussian with
variance s², then unconditional kurtosis = 3*exp(4s²) — **no free
parameters**. Measure s² per asset from the lag-1 autocovariance of log GK
vol (lag-1 kills the iid measurement noise; rough-vol persistence keeps the
signal), predict kurtosis, compare with realized kurtosis per asset.
- **P2:** the 48 (predicted, realized) pairs lie near the 45° line.
- The vertical deviation (realized > predicted) measures the JUMP component
  — itself a quantity of interest per asset class.
- Gate first: on a simulated lognormal-SV world the procedure must recover
  the law exactly; on an SV+jumps world it must under-predict by the known
  jump contribution.

### Screen L3 — Multifractal universality of return scaling
Moment scaling of returns: E|r_Delta|^q ~ Delta^zeta(q). The multifractal
random walk (Bacry-Muzy) predicts zeta(q) = (q/2)(1 + lambda²) - lambda²q²/2
with ONE intermittency parameter lambda². 
- **P3:** lambda² is tightly clustered across all 48 assets (literature
  folklore: lambda² ≈ 0.02-0.05 "universal"). A tight cross-sectional
  distribution = universality; a wide one kills it.

## What would constitute "legs"
- L1: median |kurt(z) - 3| < 1 across assets AND t-HMM nus > 20 everywhere
  after deformation AND Gaussian K-curve flattens (delta logscore K=3->5
  shrinks by >70%).
- L2: cross-sectional correlation(predicted, realized kurtosis) > 0.6 with
  slope within [0.5, 1.5] — given kurtosis estimation noise this would be
  remarkable for a zero-parameter prediction.
- L3: IQR(lambda²)/median(lambda²) < 0.5.

Any screen that survives gets the full treatment (bootstrap CIs, subperiod
stability, asset-class breakdown, the works). Any that dies gets reported
dead — the kill is information.
