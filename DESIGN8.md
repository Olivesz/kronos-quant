# KRONOS-DECATHLON — The Minimal Market

*Pre-registered. Question: what is the SMALLEST mechanism that reproduces
the deep stylized facts we measured? Method: a minimal agent-based market,
ablated ingredient by ingredient, scored on a ten-event battery built from
our own gate-validated estimators. The deliverable is the ablation table:
which ingredient buys which fact.*

## The ten events (close-only versions of our measured facts)
All computed identically on real data and simulated output. Thresholds are
ranges from our prior measurements, fixed BEFORE running any ABM:

| # | Event | Pass criterion |
|---|---|---|
| E1 | price efficiency | abs AC1(r) < 0.05 |
| E2 | fat tails | kurtosis(r) in [4.5, 40] |
| E3 | vol clustering | AC1(abs r) >= 0.12 AND mean AC(abs r, lags 5-20) >= 0.05 |
| E4 | rough clock | Hurst(log RV) in [0.0, 0.30]  (daily proxy biases down; real SPY lands here) |
| E5 | leverage effect | mean corr(r_t, RV_{t+1..10}) <= -0.03 |
| E6 | one-clock Gaussianization | kurtosis(r / sigma_5d) <= 5 |
| E7 | cascade termination (clock jumps) | kurtosis(weekly d log RV) >= 3.5 |
| E8 | arrow of time in the coupling | EP(r) significant AND EP(deformed r) not |
| E9 | no sign information | direction bits <= shuffle null95 |
| E10 | the clock's clock | AC1(abs weekly d log RV) >= 0.05 |

Calibration gate: real SPY (close-only) must pass >= 9/10; a pure GBM must
pass <= 4/10 (it passes E1/E6/E9 by construction — Gaussian worlds are
efficient and trivially one-clock). The spread GBM~3 vs SPY~10 is the
battery's dynamic range.

## The minimal market (aggregated flows, ~8 parameters)
Log price p_t moves by linear impact of four flows:

  r_t = lambda * [ D_fund + D_chart + D_voltarget + D_noise ]

  D_fund   = kF * (V_t - p_t),           V = random-walk log fundamental
  D_chart  = kC * tanh(m_t / s),         m = EWMA(returns)  (trend signal)
  D_volt   = kV * (L_t - L_{t-1}),       L = min(Lmax, sig*/sigma_hat)
  D_noise  = sN * eps_t
  sigma_hat^2 = EWMA(r^2)

The vol-targeting flow is the reflexivity ingredient: a vol spike forces
de-leveraging (selling), which moves price, which raises vol — the spiral
we conjectured (CLOCK/ATLAS IV.1) generates surges. Optional ingredient H:
heterogeneous timescales (chartists and vol estimators mix 3 horizons).

## Ablation ladder (parameters fixed across configs; ablations zero out flows)
  G      noise only (GBM benchmark)
  F      + fundamentalists
  FC     + chartists
  FV     fundamentalists + vol-targeters (no chartists)
  FCV    all three flows
  FCVH   + heterogeneous timescales — "the full minimal market"

8 seeds per config, T=6000; an event passes if a majority of seeds pass.

## Pre-registered hypotheses
- D1: F alone is efficient but Gaussian — fails everything stylized.
- D2: FC buys fat tails + clustering (E2, E3) but risks failing E9
  (chartists leak sign information unless fundamentalists discipline them).
- D3 (STAR): the vol-targeting flow is what buys the deep facts — leverage
  effect (E5), clock jumps (E7), the arrow in the coupling (E8) — because
  it is the only flow that reacts to vol and only in one direction.
- D4: roughness (E4 near H~0.1) requires timescale heterogeneity (FCVH);
  single-timescale configs give smooth (high-H) clocks. If E4 fails even
  in FCVH, that is the finding: roughness needs more than horizon mixing.

## Honesty constraints
Parameters are hand-set once on the full config to produce sane vol levels
and pass E1/E2/E3 only, and are NOT tuned per config or per event. The
ablation toggles flows to zero, nothing else. The battery code is identical
for SPY and ABM.

## Calibration-phase amendments (made BEFORE any ablation was run)
1. Battery events recalibrated against reality in gate X19 (SPY must score
   10/10, GBM 3/10): E1 allows the real index's mild daily reversal
   (ac1 in [-0.15, 0.05]); E4 uses 8-week clock-level autocorrelation
   (close-only Hurst is proxy-noise-fragile; notably GJR-GARCH FAILS this
   event — exponential memory cannot fake long memory); E7 uses AR(1)
   clock-innovation skew vs the log-chi2 noise floor (raw weekly differences
   carry an MA(1) artifact that even GBM's |diff| autocorrelates on); E10
   replaced vol-of-vol clustering (invisible close-only) with gain/loss
   tail asymmetry at 2.5 sigma.
2. Ingredient M (market makers / liquidity providers, flow = -kM * r_prev)
   added to the ladder after the tuning pass showed vol-targeting flows
   structurally leak momentum (their de-leveraging is serially correlated);
   in reality that flow is absorbed by liquidity provision. Prediction:
   M restores E1/E9 without destroying E2/E3 — efficiency and wildness are
   contributed by DIFFERENT agents.
