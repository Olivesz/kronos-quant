# KRONOS-CONSTANTS — Which Market Laws Are Actually Constant?

*Pre-registered capstone. Across nine studies KRONOS measured a set of
"laws" (H, conditional tail index, clock commonality, leverage, branching
ratio, the bits, one-clock kurtosis). Are they FUNDAMENTAL CONSTANTS (stable
across eras) or era-dependent FASHIONS (Adaptive Markets Hypothesis)? We
estimate each in rolling windows, formally test stability against its own
sampling noise, and report which constants of the market are actually
constant.*

## The quantities (each a prior KRONOS finding)
1. **H** — roughness of log-vol (rough-vol).
2. **kurtosis(raw r)** — fat tails.
3. **kurtosis(r / vol)** — the one-clock collapse (should be ~3 every era if
   the deformation law is universal).
4. **leverage** — mean corr(r_t, vol_{t+1..10}) (the leverage effect).
5. **clock commonality** — first-eigenvalue share of the cross-asset log-vol
   correlation matrix (how "one-clock" the market is).
6. **n_raw** — Hawkes branching ratio of raw extreme returns.
7. **n_deformed** — branching ratio of vol-deformed events (genuine reflexivity).

## Method
- Non-overlapping (or 50%-overlap) windows of W ≈ 3 years; estimate each
  quantity per window (pooled across assets where cross-sectional).
- **Stability test**: is cross-window variance larger than within-window
  sampling noise? Block-bootstrap each window to get its sampling SD;
  compare the dispersion of window point-estimates to the pooled bootstrap
  SD via a variance-ratio statistic VR = Var(window means) /
  mean(within-window bootstrap variance). VR ~ 1 => constant; VR >> 1 =>
  genuine drift. Bootstrap p-value for VR > 1.
- Also report the linear time-trend slope per quantity with bootstrap CI
  (does it monotonically drift?).
- Classify each: CONSTANT (VR not significant, no trend), DRIFTING
  (significant trend), REGIME-VARYING (high VR, no monotone trend).

## Pre-registered expectations
- C1: the **one-clock kurtosis** (deformed) is a true constant (~3 every
  era) — the deepest law, should be the most stable.
- C2: **H** and **leverage** are constants (structural, mechanism-driven).
- C3: **direction-related** quantities drift (we already saw direction bits
  fall to 0 post-2018); **n_deformed** drifts down (GFC fading, from REFLEX).
- C4: **clock commonality** rises over time (markets more synchronized /
  ETF-ization) — a DRIFTING law.

## Gate (test_constants.py)
1. A synthetic series with a CONSTANT parameter across windows: VR test must
   NOT reject (correct size, ~5%).
2. A synthetic series with a KNOWN LINEAR DRIFT: VR test must reject and the
   trend CI must exclude 0 (power).
3. The variance-ratio must be calibrated: pure-noise windows give VR ~ 1.

## Deliverable
The "periodic table of market constants": each law tagged CONSTANT /
DRIFTING / REGIME-VARYING with its VR, trend, and per-era values; dashboard
panel; the single cleanest statement of what is and isn't permanent about
markets.
