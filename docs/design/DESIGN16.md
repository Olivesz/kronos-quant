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

## Honesty constraints

Headline switches only if a variant survives its kill criterion; all rows
(control included) are reported side by side in FINDINGS; financing and
selection-risk caveats restated. The research arms launched alongside (FX law
battery; DECATHLON-2 anticipatory agents) are *measurement* studies with
their own pre-registrations (DESIGN17, DESIGN18) and do not touch the book.
