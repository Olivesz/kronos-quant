# KRONOS-CRITICAL — Are Crashes Critical Transitions or Shocks?

*Pre-registered before running. The deepest falsifiable question we can reach
with daily data, and the one whose naive version is circular.*

## The question
Two theories of market crashes:
- **Critical transition** (Scheffer/Sornette): the market is a slowly-driven
  dynamical system approaching a bifurcation; the restoring force toward
  equilibrium weakens, producing universal early-warning signatures —
  critical slowing down (CSD): lag-1 autocorrelation -> 1, restoring rate
  kappa -> 0, variance and "flickering" rise — BEFORE the transition.
- **Shock**: crashes are exogenous jumps with no dynamical precursor
  (efficient-market-consistent; no free lunch).

## The trap (why most financial EWS papers are broken)
"Variance rises before a vol spike" is circular: vol predicting vol is
trivial. The ONLY non-circular question is whether the CSD *signature*
(restoring-rate decay, AC structure) predicts crashes **conditional on the
current volatility level**. We kill the confound by stratification and by
incremental-AUC tests against a volatility-only benchmark.

## Target (deliberately NOT vol-defined, to avoid circularity)
A **crash onset** at day t: the forward H-day cumulative log return
r_{t->t+H} falls below the asset's q-quantile of all H-day forward returns
(headline: H=20, q=0.05). A binary causal label, price-based, independent of
the vol *level* by construction (though correlated — that is the point).

## Early-warning indicators (rolling window L, strictly causal, known at t)
On the log-GK-volatility STATE variable x_t (the dynamical state):
1. **kappa**: restoring rate = -ln(phi_hat), phi_hat = AR(1) coef of x on L.
   CSD predicts kappa -> 0 (the cleanest, most physical signature).
2. **ac1_x**: lag-1 autocorrelation of x (CSD predicts -> 1).
3. **volofvol**: rolling SD of dx (rising = approaching instability).
4. **skew_dx**: skew of increments (flickering between basins).
5. **spectral_ratio**: low-freq / high-freq power of x (spectral reddening).
On returns: 6. **ac1_absr** (clustering intensification).
The **vol level** itself, v_level = mean x on L, is the confound benchmark.

## Pre-registered hypotheses
- **C1 (raw)**: CSD indicators rise before crashes (univariate AUC > 0.5).
  Expected true but uninformative (confounded by vol).
- **C2 (THE TEST)**: incremental out-of-sample AUC of {vol + CSD} over
  {vol only} for predicting crash onset. Walk-forward logistic, expanding
  window, refit yearly. Stationary-bootstrap CI on the AUC gain.
  - If CI excludes 0 -> tipping-point structure: CSD carries crash
    information beyond the vol level. Systemic-risk-relevant.
  - If CI includes 0 -> crashes are shocks; apparent EWS are a vol artifact.
- **C3 (stratified)**: within vol terciles, does elevated kappa-decay raise
  crash frequency? Lift T3/T1 of the kappa signal within the MIDDLE vol
  tercile (where the confound is weakest), bootstrap CI.
- **C4 (universality)**: is the EWS gain consistent across asset classes
  (equities / bonds / gold / credit), or equity-specific?
- **C5 (asymmetry)**: do EWS precede DOWN-crashes more than UP-spikes
  (symmetric forward-return tails)? Bifurcations need not be directional;
  a down-only signal points to leverage/liquidity mechanisms.

## The synthetic gate (test_critical.py) — the credibility anchor
1. **Fold-bifurcation world**: double-well potential
   dx = -dU/dx dt + sigma dW, U(x) = x^4/4 - x^2/2 - c_t x, with control
   c_t drifting slowly until the well the state sits in vanishes (a fold).
   CSD is PROVABLE here. "Crash" = the jump to the other well. The test
   MUST find positive incremental AUC (kappa decays before the fold).
2. **Shock world**: identical marginal vol path but transitions are a
   Poisson process independent of the state (vol jumps with no precursor).
   The test MUST find incremental AUC CI including 0 (exoneration).
3. **kappa estimator**: on an OU process with known mean-reversion theta,
   recover kappa ~ theta within tolerance; on a near-unit-root process,
   kappa -> 0.
Only after the gate convicts the bifurcation AND exonerates the shock do we
touch real data.

## Inference
Walk-forward AUC (no in-sample peeking); stationary bootstrap (mean block
63d) for all CIs because both features and crash labels are serially
dependent; Benjamini-Hochberg across the per-asset family for C4.

## Deliverable
The verdict (transition vs shock) with the incremental-AUC number and CI;
the stratified lift; the asset-class universality table; dashboard panel +
the synthetic-gate proof that the test can both convict and exonerate.
