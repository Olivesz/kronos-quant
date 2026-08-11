# KRONOS-EDGE — Fixing the Engine's Structural Drag (pre-registered)

*Motivation: the flagship book posts Sharpe 0.94 at 6.9% realized vol — good
risk-adjusted, weak CAGR (6.4% vs SPY 15%). Before "optimizing" anything, we
diagnosed WHERE the return goes. This document pre-registers the findings, the
two structural repairs, the expected outcomes, and the kill criteria — written
BEFORE the repaired system was run.*

## The diagnosis (measured on the current build)

1. **The underlying book is strong.** At exposure = 1 the signal book runs
   Sharpe **1.04** at **10.45%** vol. The alpha engine is not the problem; the
   risk overlay is where CAGR dies.
2. **The drawdown throttle has an inverted sign — a genuine bug.** In
   `risk.py::exposure_series` (and duplicated in `trade.py`),
   `m_dd = 1 + (dd - dd_start)(1 - floor)/span` with `span = dd_floor_at -
   dd_start < 0` produces **m_dd = 0.50 at zero drawdown** (max braking at the
   high-water mark) and **1.0 at −20%** (full throttle open in a crash),
   because the erroneous side is hidden by the `clip(…, 1.0)`. Measured: m_dd
   binds on **93.6% of days**, mean 0.64 — a permanent brake that *releases*
   into crashes. The intended design (de-risk linearly from −8% to −20%, floor
   0.25) is exactly reversed. The gate suite missed it because no gate tests
   the overlay's *direction*.
3. **Vol targeting cannot reach its own target.** Target 13%, book vol 10.45%,
   exposure capped at 1.0 ⇒ the target is structurally unreachable; realized
   vol is 6.9% (half the budget), CAGR scales down with it.

## Pre-registered changes (no parameter search)

- **E1 — fix the m_dd sign bug** so the throttle matches its original design:
  m_dd = 1 for dd ≥ −8%, linear to 0.25 at −20%. No parameter changes.
  Applied to BOTH `risk.py` (v1 book) and `trade.py` (DESIGN12 system).
- **E2 — let vol targeting target (v1 book only).** Allow exposure up to
  `max_exposure = 1.5` (single pre-chosen value, not scanned), so the
  vol-target multiplier can lever the 10.45%-vol book toward its 13% target
  when trailing vol is low. Combination rule (decided while gating, before any
  real-data run): the vol multiplier is the LEVER (`vol_target/trailing_vol`,
  capped at `max_exposure`); the CVaR cap and drawdown throttle are BRAKES in
  `[floor, 1]`; `exposure = lever × min(brakes)`. The old `min()` of all three
  could never exceed 1 (the brakes top out there), which gate X27 exposed
  before any market data was touched. Leverage is not free: a financing cost of
  **3.5%/yr on the levered portion** (conservative flat proxy for
  2013–2026 broker margin ≈ fed funds + spread) is charged daily in the
  backtest. The DESIGN12 TRADE system **stays at no-leverage** — its
  pre-registration said "cap at 1", and we do not retro-edit pre-registrations;
  it receives only the bug fix.
- **New gate X27** (`tests/test_risk.py`): the overlay must (a) hold m_dd = 1
  at the high-water mark, (b) decrease monotonically with drawdown depth to the
  floor at `dd_floor_at` — the exact property whose absence hid the bug;
  (c) lever a low-vol world toward the vol target and cap at `max_exposure`;
  (d) de-lever a high-vol world below 1; (e) charge financing only when
  exposure > 1.

## Pre-registered expectations

- **Fix-only (cap 1.0):** mean exposure rises ~0.62 → ~0.9; realized vol
  → ~9–10%; CAGR up roughly ×1.4; Sharpe flat-to-up (we stop de-risking at
  peaks); MaxDD stays well inside SPY's −34%.
- **Fix + leverage 1.5:** realized vol approaches the 13% target; CAGR roughly
  ×1.7–1.9 minus ~0.5–1% financing drag; Sharpe within ±0.05 of baseline
  (vol-targeting scales both legs); MaxDD deepens roughly with vol, expected
  −18% to −23%, still far inside SPY.
- **Trial accounting:** exactly two new variants (fix-only, fix+lev) are added
  to the trials ledger; the deflated Sharpe is recomputed with the enlarged N.
  No other configurations will be run, scanned, or silently discarded.

## Kill criteria (declared before running)

- If the corrected system's Sharpe drops by > 0.05 vs baseline, the inverted
  throttle was accidentally protective; the bug fix still ships (a bug is a
  bug), but E2's leverage does NOT, and the result is reported as a negative.
- If financing costs erase ≥ half of E2's CAGR gain, E2 is reported as
  not-worth-it and the default `max_exposure` reverts to 1.0.

## Honesty constraints

The README/dashboard headline switches to the repaired system only WITH the
full before/after table and this document linked. The old numbers are not
deleted; they are the baseline row. PBO/DSR caveats from KRONOS-X Q6 continue
to apply and are restated wherever the new numbers appear.
