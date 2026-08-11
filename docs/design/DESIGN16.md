# KRONOS-EDGE2 — The Research-Licensed Performance Program (pre-registered)

*EDGE (DESIGN15) fixed what was broken. EDGE2 implements the two upgrades the
research has ALREADY licensed but production never received. No parameter
scans; each change is one pre-registered variant with a kill criterion,
charged to the trial ledger. Written before either variant was run on real
data.*

## The two variants

- **V1 — HAR forecast-vol lever.** The flagship lever sizes with *trailing*
  EWMA vol, but the project's strongest applied findings say forecast vol:
  HAR-RV beats EWMA decisively (QLIKE 0.417 vs 0.511, DM −7.1, p<0.001), and
  the TRADE system's pre-registered T1 confirmed forecast-vol targeting beats
  realized-vol targeting end-to-end. Change: `risk.exposure_series` gains a
  `lever_mode="har"` that drives m_vol with a causal walk-forward HAR forecast
  of the book's own variance (HAR features = 1/5/22-day mean squared book
  returns; OLS refit every 21 days on an expanding window; strictly T+1).
  EWMA remains available as `lever_mode="ewma"` for the control row.
  *Kill: if HAR-lever does not improve Sharpe or vol-tracking vs the EWMA
  lever on real data, default stays EWMA and the negative is reported.*
- **V2 — Student-t regime engine.** X² showed Gaussian HMMs hallucinate
  regimes from fat tails; the t-HMM family won the MCS. Production still runs
  the Gaussian. Change: `walkforward_regimes` accepts the model class;
  `regime_engine="thmm"` runs the walk-forward with StudentTHMM under
  identical features, hysteresis, and causality. *Kill: if the t-engine does
  not improve the book's Sharpe or drawdown on real data, default stays
  Gaussian (the fit advantage may not translate to the gating decision — an
  honest possible outcome the X² study itself anticipated).*

## Gates before real data

- **X28 — forecast-lever validity.** On a synthetic *persistent-SV* world
  (vol forecastable) the HAR lever must achieve lower vol-tracking error than
  the EWMA lever AND not degrade Sharpe; on an *iid-vol* world the two must
  tie (no false edge). Mirrors the TRADE gate's logic at the overlay level.
- **X29 — t-engine equivalence.** On a synthetic Gaussian-emission regime
  world, the t-walk-forward must match the Gaussian engine's filtered-state
  accuracy (no regression when the world IS Gaussian); on a t-emission world
  it must be at least as accurate. Causality identical to X2's standard.

## Trial accounting

Exactly two new real-data variants (V1, V2) plus their one joint combination
if both survive → at most 3 ledger entries under `design16_variants`. DSR/PBO
recomputed after.

## V2 measurement (worktree run)

Implementation: `walkforward_regimes` now resolves its model class from
`cfg.regime_engine` ("gaussian" default, "thmm" -> StudentTHMM); features,
refit cadence, hysteresis and causality are shared code, identical across
engines. Gate X29 (`tests/test_regime_engine.py`) passed: Gaussian world
t-engine acc 74.1% vs Gaussian 74.2% (gap −0.2pp, nus → [241, 300, 55]);
t(5) world acc 59.5% vs 60.2% (gap −0.7pp, within the pre-registered 1pp)
with held-out log-score 3.1461 vs 3.1286 (edge +0.0175); truncation
invariance exact (max filtered-prob diff 0.00e+00).

Real data (yahoo cache, 48 tickers × 4130 days, 2010-01-04 → 2026-06-04),
full v1 book = core net + pairs sleeve from warmup, 3368 traded days
(2013-01-14 → 2026-06-04), both
rows from the identical pipeline differing only in `regime_engine`. Both
rows use the trailing-EWMA vol lever (this worktree predates the V1 HAR
lever flip), so the engine comparison is like-for-like; the V1+V2 joint
row still needs its own run per the trial ledger:

| engine | CAGR | Vol | Sharpe | Sortino | MaxDD | CVaR95 |
|---|---|---|---|---|---|---|
| gaussian (control) | +10.91% | 11.60% | 0.951 | 1.228 | −21.26% | 1.759% |
| thmm (V2) | +11.18% | 11.59% | 0.972 | 1.253 | −20.67% | 1.758% |

The engines disagree on 43.0% of traded days, almost entirely
Bear↔Volatile relabeling (gaussian=Bear/thmm=Volatile 802d,
gaussian=Volatile/thmm=Bear 617d; Bull involved in only 28d). Longest
episodes: 2020-02→2020-12 (305d, gaussian Bear / thmm Volatile),
2022-01→2022-10 (266d, same direction), 2023-12→2024-05 and
2024-07→2024-12 (gaussian Volatile / thmm Bear). Final t-engine nus
[16.0, 4.2, 300.0] — the Volatile state is genuinely fat-tailed, Bear is
effectively Gaussian, exactly the X² mechanism: fat tails absorbed within
a state instead of hallucinated as Bear days.

**Kill-criterion read: NOT triggered.** The t-engine improves both Sharpe
(0.972 vs 0.951) and drawdown (−20.67% vs −21.26%), plus CAGR and Sortino,
at unchanged vol and CVaR. Margins are modest; per the trial ledger this is
one pre-registered variant, no scan. Default remains `gaussian` in this
change — flipping it is a main-session decision.

## Honesty constraints

Headline switches only if a variant survives its kill criterion; all rows
(control included) are reported side by side in FINDINGS; financing and
selection-risk caveats restated. The research arms launched alongside (FX law
battery; DECATHLON-2 anticipatory agents) are *measurement* studies with
their own pre-registrations (DESIGN17, DESIGN18) and do not touch the book.
