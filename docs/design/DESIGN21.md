# KRONOS-MOMTILT — Harvesting the Monthly Direction Bits (pre-registered)

*Orchestrator-cleared Sharpe arm (one ledger entry), licensed by
KRONOS-HARVEST: the monthly sign channel carries 0.021 unharvested bits and
the carrier is 21-day market momentum, which production uses only
cross-sectionally. This arm moves it into the book as a bounded market-level
exposure tilt. Written before any run; the tilt form below is frozen.*

## The frozen form (no scan)

`m_tilt_t = 1 + 0.15 · sign(Σ_{s=t-20..t} log r_mkt,s)` — a ±15% exposure
tilt on the sign of trailing 21-day market momentum, computed through t,
applied (like every overlay input) from t+1. Exposure becomes
`clip(lever × min(brakes) × m_tilt, 0, max_exposure)` — the tilt lives
INSIDE the existing cap, and per the orchestrator's addition this is
**verified, not assumed**: the gate asserts exposure ≤ max_exposure under
extreme tilts, and the real-data run reports max realized exposure. 0.15 is
a single pre-chosen value; adjusting it afterward kills the arm by
definition ("don't widen the band to rescue it").

## Gate X33 (X28 mould — the mechanism-disappears test)

- **Trending world** (regime-persistent drift, 21d momentum genuinely
  predicts sign): the tilt must add Sharpe over the untilted overlay.
- **Driftless world** (identical vol dynamics, sign-unpredictable): the two
  must tie (no false edge from vol interaction).
- **Cap safety**: with the tilt forced to its extremes, exposure never
  exceeds `max_exposure` and financing covers every levered day.
- **Causality**: future truncation leaves the tilt path bit-identical.

## Kill criteria (pre-declared)

- No Sharpe improvement over the shipped joint system (HAR lever + t-HMM,
  Sharpe 1.05), or
- split-half fails in either era (either half's Sharpe drops vs the joint
  system). Honest prior: BITS measured direction bits decaying post-2018, so
  H2 may kill this arm — if it does, **the kill ships as the result**.
- Ledger: one entry (`design21_momtilt`); DSR recomputed after; **PBO 0.45
  restated beside any claim** per standing rule.

## Baseline statement

All comparisons are against the shipped joint system (HAR lever + t-HMM
regimes, max_exposure 1.5, financing 3.5%/yr), same data, same pairs sleeve.
