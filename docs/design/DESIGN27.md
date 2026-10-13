# DESIGN27 — The equal-weight bar: can any licensed configuration beat 1/N?

*Pre-registered before any code or run (2026-10-13). Owner mandate: the
shipped system's Sharpe (1.07, rf=0) sits below equal-weight on its own
48 names (1.10, rf=0; KRONOS-TRADE, FINDINGS). The owner's direction is
not to reframe but to find a better system. This program searches the
ALREADY-LICENSED machinery — no new alpha source, no tuning grids — and
reports whichever way it lands.*

## Convention change (owner decision D2, applied here first)

All evaluation in this program uses **excess-over-cash Sharpe**: daily
net returns minus the 3-month T-bill rate (FRED DTB3, committed at
`data/dtb3.csv`, forward-filled to trading days, ACT/360 to daily).
Raw-rf0 values are reported alongside for continuity. The global
convention switch for every other artifact happens in a later wave, on
the winning system, once.

## Hypothesis

KRONOS-TRADE showed the measured edge lives in the overlay (forecast-vol
lever X28, CVaR/DD brakes X27, momentum tilt X33), while the
construction backbone (regime-gated signals → HRP → Black–Litterman)
is what equal-weight beats. If true, the overlay mounted on an
equal-weight backbone should carry EW's Sharpe plus the vol-timing edge,
at the overlay's drawdown profile.

## Candidates — one registered variant each, no grids

- **C1 `ew_overlay`**: backbone = equal-weight 1/N over the tradable
  universe at each rebalance (same cadence, no-trade band, costs,
  drift); the full shipped overlay unchanged (HAR lever, brakes,
  mom_tilt 0.15, max_exposure 1.5, financing 3.5%/yr on the levered
  portion).
- **C2 `ew_overlay_untilted`**: C1 with mom_tilt = 0 (attribution
  control: how much is the tilt vs the lever).
- **C3 `shipped_hivol`**: the shipped system with `target_vol` set once
  to equal-weight's realized vol on the evaluation window (computed,
  not tuned; a single value) — the risk-matched comparison.

Benchmarks computed in the same run on the same days: equal-weight raw
(no overlay), SPY, and the shipped system (asserted against
`research/momtilt.json` before any candidate is read).

## Decision rule (fixed before any run)

A candidate **WINS** iff, on the common evaluation window, net of costs
and financing: excess-cash Sharpe ≥ equal-weight's excess-cash Sharpe,
AND MaxDD ≤ 0.85 × equal-weight's MaxDD. Secondary (reported, not
gating): CAGR within 1pp of equal-weight or better.

**Kill criterion:** if no candidate wins, the program is a FAILURE and
is reported as one: the licensed machinery cannot beat 1/N on these
names, the headline framing falls back to risk control, and further
progress requires a new licensed alpha source (the intraday dataset
lead is named but unlicensed — it needs its own quality gate first).
No additional variants, no grid, no retries.

## Trial accounting

Exactly three new variants → three `design27_*` entries in the
`exp_forensics` ledger dict; DSR/PBO recomputed and restated beside any
quoted Sharpe.

## Gate (X38, `tests/test_ewbar.py`, before results are read)

(a) EW-backbone identity: with the overlay disabled and costs zeroed,
the EW backbone's gross book equals the drifted-1/N book computed
independently (tolerance 1e-12). (b) Causality: shifting all inputs
forward one day changes no target weight (test_trade pattern).
(c) DTB3 loader: parses the committed CSV, forward-fills weekends only,
daily rate within [-1bp, 25bp] (2015 negative bill prints are real), and the excess-Sharpe helper reproduces a
hand-computed 3-day fixture. (d) The shipped-system row reproduces
`research/momtilt.json` shipped_tilted within 1e-6 before any candidate
runs.

## Reporting

`research/ewbar.json`: per-candidate and per-benchmark summary rows
(both Sharpe conventions), daily nav/drawdown series, spans, verdicts
against the registered rule. FINDINGS gains KRONOS-EWBAR. Results land
whichever way they fall; the README/site restatement happens in the
infra wave on the winner (or on the honest failure).

## Amendment (post-run, 2026-10-13): results

Run complete; artifact `research/ewbar.json`; gate X38 passed before
results were read. **Program verdict: FAILURE under the registered rule.**
C1 (`ew_overlay`) ties equal-weight's raw Sharpe (1.102) at 65% of its
drawdown (−19.2% vs −29.5%) and beats the shipped system on CAGR
(+13.5% vs +11.8%) and raw Sharpe (1.102 vs 1.068), but its excess-cash
Sharpe is 1.001 vs equal-weight's 1.020 — short by 0.019; C2 −0.039; C3
−0.066. The DD leg passes for all three (ratios 0.651 / 0.628 / 0.658).
The line closes per the kill criterion: no further variants, no grids.
The hypothesis (the backbone, not the overlay, is what 1/N beats) is
confirmed and recorded in FINDINGS (KRONOS-EWBAR). Whether C1 replaces
the shipped default despite failing the EW bar is the owner's decision,
outside this registration.

## Amendment (post-run, 2026-10-13): owner decision

The owner shipped C1 as the default despite the FAILURE verdict (it
beats the prior default on raw/excess Sharpe and CAGR). Recorded as an
owner selection after the registered verdict, not a registered outcome;
no new ledger entry (C1 already charged). `exp_ewbar` now pins both
backbones explicitly so the DESIGN27 record reproduces byte-identically
after the default moved.

## Amendment (2026-10-13): reproduced on the pinned snapshot

The data layer now reads the committed snapshot (`live/genesis`,
digest-verified) by default instead of the Yahoo cache. `exp_ewbar` was
re-run on it: every verdict is identical; the prior-default and C3 rows
moved by at most 0.002 Sharpe (the cache and the snapshot differ by
2.3e-6 relative in prices). Figures above and in FINDINGS are the pinned
reproduction.

## Amendment (2026-10-13): two measurement bugs fixed, verdict re-read

The DESIGN28 design panel found, and the code confirmed, that `dtb3_daily`
credited only ~70% of the bill rate (÷360 per trading day) and that the
overlay was fitted on the 762 zero-padded warmup days. Both are fixed and
gated (X38c, X42). Re-run on correctly computed inputs, every verdict is
unchanged — FAILURE. Corrected gaps to equal-weight's excess Sharpe: C1
−0.010, C2 −0.021, C3 −0.078; drawdown ratios 0.635 / 0.609 / 0.650. C1 now
beats equal-weight on raw Sharpe (1.122 vs 1.102) while still failing the
registered excess-cash bar.
