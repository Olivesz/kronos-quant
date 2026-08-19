# KRONOS-LIVE — The Forward Ledger (pre-registered)

*Phase 1 of the post-closure agenda (panel-scored A′ → C → F). Every claim in
this repo is retrospective; DSR/PBO are in-sample corrections. The one proof
class money can't buy retroactively is a forward record: an append-only,
git-committed daily ledger of target weights and forecasts, judged by
congruence tests that were calibrated BEFORE the first live row existed. This
document was written before any live row; the calibration numbers below were
measured before the loop was built.*

## The red-team constraint this design obeys

A naive live-vs-backtest PnL tile is theater: at Sharpe ~1.05 and ~11.5% vol,
the measured power to detect even a TOTAL loss of edge is **18% at 90 days,
23% at 180 days** (calibration below). A congruence gate that cannot convict
has no power, and METHODS §0 makes that self-indicting. So the pre-registered
claims are the ones with measured power at weeks-to-months scale; PnL is
displayed, never claimed.

## The ledger

One row per trading day, committed by a scheduled GitHub Actions run (git
history on GitHub is the immutability mechanism — no laptop dependency):

- date; target weights; regime label + filtered probs; HAR portfolio-vol
  forecast; exposure and its components; estimated costs; and the **as-of
  input snapshot digest** (raw unadjusted closes used), so later
  reconstruction replays what the run actually saw — Yahoo's retroactive
  dividend/split revisions cannot masquerade as strategy drift.
- **Live runs fail loudly.** The current `deploy_today.py` silently falls
  back to cached data on fetch failure; in the loop that is forbidden — a
  failed fetch writes an explicit GAP row with the failure reason, never a
  stale row dressed as live. Gap rows are part of the record.

## Pre-registered congruence claims (and their measured power)

Calibrated on synthetic SV tracks matching the book's character (11.5% ann
vol, persistence 0.98); size = rejection rate on matched-world tracks, power =
rejection on planted-defect tracks; 95% critical values, 300-run nulls:

- **L1 — weight reproducibility (deterministic).** Recomputing targets from
  the archived snapshot must reproduce the ledger row exactly (tolerance 0).
  Power 1 against any corruption by construction.
- **L2 — vol-forecast tracking (the core claim, live).** Mean daily QLIKE of
  realized r² vs the ledger's forecast variance over the trailing window,
  against the matched-world null band. Measured (600-rep clean construction;
  supersedes the first-pass numbers whose null included a drift term — both
  measurements pre-date the first live row): size 4.5–6% at all horizons;
  power vs a 1.5× vol-engine failure **0.54 @ 60d / 0.68 @ 90d / 0.93 @
  180d**; vs a subtler 1.3× failure only 0.17–0.41 (disclosed: early
  detection is of gross failures).
- **L3 — exposure/cost bands.** Realized exposure within [floor, 1.5] always;
  realized cost drag within 2× the backtest's annualized estimate over any
  trailing quarter.

*Amendment (pre-first-row, 2026-08-16): the tracked system is KRONOS-TRADE
(DESIGN12's deployable, `recommend()`, no leverage), so L3's exposure band is
[floor, 1.0]. And the emit computes from the committed genesis snapshot plus
append-only daily bars — never from a fresh full-history fetch — making L1
exact by construction and vendor revisions structurally unable to touch the
record; detected corporate-action divergences become explicit, logged
re-anchor events rather than silent history changes.*
- **L4 — the PnL fan (display only).** Live NAV drawn inside the backtest's
  stationary-bootstrap fan, labeled with the measured power numbers above.
  No pass/fail claim before the pre-registered horizon (3 years).

## Gate X35 (before the first live row)

The congruence machinery must demonstrate, on synthetic tracks: (a) size ≈
5% on matched worlds for L2/L3; (b) power ≥ 0.6 at 90d against the 1.5×
vol-defect world (measured 0.68); (c) L1 exactness — a single perturbed weight or price must
be caught; (d) the gap-row path — a simulated fetch failure must produce a
GAP row and never a stale-as-live row.

## Kill criteria / honesty

- If the Actions scheduler proves unreliable (>10% missed weekdays over the
  first month), the loop is redesigned or reported as failed — gap-ridden
  ledgers read worse than none.
- L2/L3 breaches are reported on the dashboard when they occur, not
  explained away; a confirmed L2 breach at the calibrated threshold triggers
  a halt-and-diagnose, and the halt itself is a ledger event.
- This arm charges **zero** Sharpe-ledger entries (measurement
  infrastructure; no variant selection). PBO 0.45 restated wherever live
  performance is displayed.
