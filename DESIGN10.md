# KRONOS-REFLEX — How Endogenous Is the Market?

*Pre-registered. The quantity under every prior study's open question: the
Hawkes branching ratio n = fraction of extreme events that are aftershocks of
other events. n -> 1 is critical (infinite cascades, self-organized
reflexivity); n = 0 is pure exogenous news. Filimonov-Sornette report markets
near-critical (n ~ 0.7-0.9) and rising over decades. We add a decomposition
nobody has done: how much endogeneity survives removing the volatility clock?*

## The model
Exponential-kernel Hawkes on event times {t_i} (days):
  lambda(t) = mu + sum_{t_i < t} alpha * exp(-beta (t - t_i)),  n = alpha/beta.
Fit by Ogata-recursion MLE; stability n < 1 enforced via log-parameterization.

## Events (the novel part)
- **raw events**: |r_t| above its global 95% quantile — captures BOTH vol
  clustering and genuine jumps (the standard Filimonov-Sornette object).
- **deformed events**: |r_t / sigma_{t-1}| above its 95% quantile, sigma =
  5d GK vol (LAGGED so jumps survive — CLOCK/SURGE lesson). Same event count;
  these are vol-clock-adjusted SURPRISES, so their self-excitation measures
  GENUINE jump-triggers-jump reflexivity, purged of clustering.
The decomposition n_raw - n_deformed = endogeneity that is "merely" the
volatility clock; n_deformed = irreducible jump-cascade reflexivity.

## Pre-registered hypotheses
- **F1**: n_raw is high and near-critical (median across assets in [0.6, 0.95])
  — replicates the standard reflexivity finding on daily data.
- **F2 (THE TEST)**: n_deformed << n_raw. Most apparent market endogeneity is
  the volatility clock. Pre-registered: median n_deformed < 0.5 * median
  n_raw. If instead n_deformed ~ n_raw, there is a genuine jump-cascade
  beyond clustering (also a finding). If n_deformed ~ 0, jumps are
  conditionally independent given the clock — endogeneity IS the clock.
- **F3 (reflexivity grew?)**: compare n (raw and deformed) pre/post 2012
  (risk-parity/vol-targeting AUM era). Did endogeneity rise? Block-bootstrap
  CI on Delta-n.
- **F4 (systemic vs idiosyncratic)**: is the COMMON-factor jump series (events
  of the cross-sectional median |z|) more endogenous than the typical single
  asset? Novel: is systemic risk more reflexive than idiosyncratic risk?
- **F5 (link to CRITICAL)**: does per-asset n_raw correlate cross-sectionally
  with the faint CSD precursor (phi-shift) measured in KRONOS-CRITICAL?
  Near-critical assets (high n) should slow down more before crashes — the
  dynamical bridge between our two studies.

## Gates before real data (test_reflex.py)
1. Hawkes MLE recovers known n on simulated exponential-Hawkes with n in
   {0.3, 0.6, 0.9}, recovering both n and the kernel timescale 1/beta;
   the known finite-sample downward bias is measured (recovery curve) and
   used to debias real estimates.
2. Poisson process (n = 0): n_hat ~ 0 (size, no spurious endogeneity).
3. Simulated clustered-but-not-self-exciting events (a Cox process driven by
   an exogenous vol path) deform to n_hat ~ 0 while raw n_hat > 0 — proving
   F2's decomposition can attribute clustering correctly.

## Inference
Block bootstrap (resample inter-event intervals in blocks) for per-asset n
CIs; cluster bootstrap over assets for the pooled medians; the recovery-curve
debiasing applied consistently to raw and deformed (so the COMPARISON is
bias-robust even if the level isn't).

## Deliverable
The endogeneity decomposition (n_raw vs n_deformed), the time trend, the
systemic-vs-idiosyncratic contrast, and the n-vs-CSD bridge; dashboard panel
+ the recovery-curve gate proving the estimator is calibrated.
