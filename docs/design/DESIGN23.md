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

*Amendment (2026-10-13, registered before implementation): the 74-day hole.
The genesis snapshot ends 2026-06-04 — the research panel's end — but the
first archived bar is 2026-08-17, so `reconstruct_panel` read the gap as one
daily return: median |r| 4.2% per name (2.7 daily standard deviations), ORCL
+38% (13.8 sd), SPY +2.1% (2.5 sd). Every LIVE row since 2026-08-17 computed
its vol and correlation estimates from inputs containing that phantom day.
Repair: a one-time BACKFILL event appends the missing bars 2026-06-05 ..
2026-08-14, fetched once and level-matched per ticker to the existing bar of
2026-08-17; `live/bars.csv` gains a `recorded` date, and `reconstruct_panel`
can rebuild the panel from exactly the bars recorded by a given date, so
every earlier row still reproduces from the gapped input it actually used.
The event is a ledger row. Nothing in the record is re-computed: rows from
2026-08-17 to the backfill are reported as decisions made on gapped inputs.
No system parameter changes. The second stream (the shipped book, below)
starts only after the backfill.*

*Amendment (2026-10-13): a second stream for the shipped book. The ledger
above tracks KRONOS-TRADE (unlevered), not the backtest the README headlines
(the 1/N backbone with the levered overlay and the pairs sleeve). A separate
append-only file, `live/shipped_ledger.jsonl`, records that book's next-day
decision before each session: exposure, equity holdings, pair-sleeve legs,
the next day's trading cost and financing. Its realized return is the
decision applied to the next day's bars; gate X45 requires that replaying the
decisions day by day reproduces the backtest's net returns exactly, so the
stream measures the headlined system and nothing else. Same L1/L3 discipline;
L2 null bands recalibrated for its vol before its first row.*
