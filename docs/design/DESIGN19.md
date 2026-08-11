# KRONOS-HARVEST — Is the Monthly Direction Channel Fully Harvested? (pre-registered)

*Orchestrated arm 1 of the post-EDGE2 agenda; measurement study, zero
Sharpe-ledger entries. BITS left exactly one direction channel open: at the
21-day horizon the market leaks 0.016 bits/day of sign information
(significant), while the daily channel is closed. The production system's
only market-level direction-bearing state is the filtered regime label —
exposure is direction-blind by design (vol/CVaR/DD), and momentum enters
cross-sectionally, not as market timing. The question with value either way:
does the regime label already capture all the monthly sign information in
the feature set, or is money left on the table?*

## The quantity

**Harvest gap** ΔI = I(F ; s₂₁) − I(S ; s₂₁), where s₂₁ = sign of the
21-day-forward SPY return, F = the full BITS causal feature set
{sign_t, mom21, vol_terc, regime}, and S = {regime} alone (the production
market-state; the t-HMM engine's filtered label, matching the shipped
default). ΔI ≥ 0 by monotonicity; the question is whether it is
significantly > 0 after bias control. Both MIs use the X17-gated
Miller-Madow + permutation-null machinery; the gap's CI comes from a
stationary block bootstrap (63-day blocks) of the joint series, and the gap
must also exceed its own shuffle null. A drop-one decomposition attributes
any gap to features.

## Pre-registered hypotheses

- **HG1**: ΔI > 0 (bootstrap 95% CI excludes 0 AND gap > shuffle-null p95) —
  unharvested monthly sign information exists. Prior: plausible; mom21 is in
  F and the regime label is not built from it.
- **Kill**: CI includes 0 → the channel is **formally closed**: the regime
  label already harvests the monthly direction bits, and no direction-signal
  work is licensed. This outcome is as valuable as HG1 — it converts BITS's
  "channel open" into "channel open AND already spent."
- **Commitment either way**: this arm charges no Sharpe-ledger entry. If HG1
  holds, any follow-up arm that trades on the gap gets its own
  pre-registration, its own kill criterion, and its own ledger entry, with
  PBO 0.45 restated beside any Sharpe claim.

## Gate X31 (convict / exonerate / closed form)

Discrete synthetic worlds where MI is computable exactly by enumeration:
- **Harvested world**: a 3-state Markov regime drives P(up); features add
  junk columns. The gap estimator must EXONERATE (CI includes 0) and the
  estimated I(S; s) must match the enumerated truth within tolerance.
- **Unharvested world**: the sign additionally depends on a feature outside
  S. The estimator must CONVICT (CI > 0) and recover the true added MI
  within tolerance.
- **Noise calibration**: on pure noise, net gap ≈ 0 and the CI includes 0.

## Scope bound

Market-level (SPY), h = 21 only — the one channel BITS left open. No scans
over horizons or feature sets: F and S are fixed above, before running.
Runtime bounded: discrete MI + 300 bootstrap draws, minutes end to end.
