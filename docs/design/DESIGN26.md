# DESIGN26 — DECATHLON-R2: the referee-panel follow-up program (whitening order, whitened power, real-data benchmark, FX orientation)

*Pre-registered before any code or run. Answers the four experimental
findings that survived adversarial verification in the 2026-09-08
six-lens referee panel on the final preprint draft (39 agents, findings
verified one-by-one by independent skeptics; panel record in the session
archive). Each experiment names its kill criterion; per the standing
framing rule, the deliverable is WHICH CLAIM SURVIVES — never softened
language over a dead one.*

## Context

DESIGN25 (R1–R6) left standing: added rationality converts the sign leak
(whitened MI 0.0197 → 0.0036) but never closes it, paying with
flow-generated amplitude facts. The panel confirmed four threats to the
precision of that statement, all measurable:

1. **Whitening order (econometrician, major).** The AR(1) whitening is a
   lag-1 linear filter licensed on a lag-1 world (X36). The model's own
   leak mechanism is a multi-day drift, so lag-2..21 *linear* structure
   is not excluded from the "whitening-resistant" component. The paper
   now says "whitening-resistant", not "nonlinear" (limitation 5); this
   experiment decides which adjective the result deserves.
2. **Whitened power (econometrician, minor→experimental).** The 32-seed
   extensions covered the two raw rises (superseded as mechanism
   evidence by R2); the whitened falls that now carry the conversion
   reading sit at n=8 with every p at the 8-pair Wilcoxon floor
   (limitation 2 as revised).
3. **Real-data benchmark + criterion T-dependence (ABM + scope,
   major).** SPY's whitened bits were never computed, and the closure
   criterion's significance threshold scales with series length: the R5
   world is E9-significant at 0.0016 bits (T=6000) while SPY's raw
   0.0029 is certified information-free at T≈4100 (limitation 6).
4. **FX orientation (ABM, minor).** The FX leverage vertex averages
   signed values over market-convention quote orientations of what the
   paper itself identifies as one flight-to-quality flow; the Sec 7 text
   now scopes the claim, and this experiment measures the
   orientation-normalized value.

## Experiments

### W1 — AR(p) whitening ladder

For each of the five attribution configurations (FCVM, K1, K5-frozen,
Q0.5, Q1.0), 8 evaluation seeds, recompute whitened MI under: AR(5) and
AR(21) OLS residualization (fit per series, same convention as
`ar1_whiten`). Gate first (X37): on the analytic AR(1) world the AR(p)
filter must reproduce X36's exact-removal result; on a planted AR(3)
world it must remove the linear channel that AR(1) provably cannot,
while preserving a planted nonlinear sign channel (same construction as
X36's power world).

- **Licensed claim if the leak survives AR(21) whitening in the control
  and stays significant across the arm ladder:** "whitening-resistant"
  upgrades to "resistant to linear whitening through lag 21" and the
  conversion reading strengthens.
- **Kill criterion:** if AR(21) whitening drives the control's leak or
  the arms' floors to insignificance (permutation criterion, per-seed,
  majority), the "conversion of a leak beyond linear structure" claim
  DIES; the licensed statement becomes "conversion of multi-lag linear
  structure into one-lag reversal", the paper's limitation 5 is
  promoted into the abstract, and the title's mechanism clause is
  re-examined.

### W2 — 32-seed whitened extension

Extend the whitened comparisons (whitened falls vs control, and the
whitened-difference reversal tests) to seeds 100–131 for the two
strongest arms (K5-frozen, Q1.0), mirroring ext32's protocol exactly.
- **Licensed if:** falls hold (n_pos vs control ≤ per-seed criterion,
  p < 1e-3 attainable at n=32); limitation 2's floor caveat is then
  retired for these arms.
- **Kill criterion:** if either whitened fall loses significance at 32
  seeds, the conversion claim for that arm is DEAD as stated and the
  paper reports the survivor set.

### W3 — real-data whitened benchmark and matched-T closure verdicts

Compute whitened bits (same estimator, same AR(1) convention — and W1's
AR(p) if it licenses) for SPY and DIA over the battery window. Report,
at matched length: (a) the model floors' E9 verdicts on T≈4100
subsamples of the R5 world and the Q-arms (subsample per-seed, majority
rule); (b) SPY's raw and whitened verdicts at its native T.
- This experiment cannot kill "never closes within the model at
  T=6000"; it decides whether the criterion-vs-magnitude caveat
  (limitation 6) stays a caveat or must be promoted: **if the R5 world
  (or any attribution floor) is NOT significant at T≈4100**, the paper
  must state that at the real market's observation length the model's
  best worlds are indistinguishable from closure — and the title's
  "Cannot Close It" clause is re-examined under the standing retitle
  rule.

### W4 — FX orientation-normalized leverage

Recompute the FX cohort leverage with every pair re-signed to a common
risk-orientation (risk currency in the numerator; registered mapping
fixed before the run from the paper's own flight-to-quality axis:
JPY, CHF, USD = funding/safe; AUD, NZD, CAD, NOK, SEK, GBP, EUR, MXN =
risk). Report cohort mean ± the same time-block bootstrap SD under both
conventions.
- **Licensed if |orientation-normalized mean| is materially nonzero
  (z ≥ 2):** Sec 7's rescoped sentence gains the measured value — FX
  hosts one signed flight-to-quality flow, and the market-convention
  zero is an orientation average.
- **Kill criterion:** if the normalized mean is also ≈0 (z < 2), the
  original venue-level reading survives unqualified and the rescope
  sentence is simplified back.

## Amendment (pre-run, before any code): operational pins

- **W1 filter spec:** AR($p$) whitening is a single OLS regression of the
  demeaned return on its lags $1..p$ jointly; the residual series starts
  at index $p{+}1$; $p \in \{5, 21\}$. `arp_whiten(r, 1)` must equal
  `ar1_whiten(r)` exactly (asserted in X37).
- **W2 protocol:** control and both arms regenerated for all of seeds
  100–131 and asserted against the stored per-seed raw bits
  (`k01_extension.per_seed.K0_FCVM` and `ext32.arms.*.per_seed`) before
  the whitened estimator is read — every simulation is an asserted
  regeneration; none is new.
- **W3 subsample convention:** matched-$T$ verdicts use the LAST 4100
  observations of each seed's series (mirroring real data as a trailing
  window); the E9 verdict at any $T$ is `e9_bits`'s permutation
  criterion with the same `n_shuffle=120` and seed convention as R2;
  configuration verdict = majority over its seeds. Configs tested at
  matched $T$: Q0.5, Q1.0 (8 seeds) and the R5 re-equilibrated world
  ($k_M{=}0.10$ + Q1.0, its evaluation seeds).
- **W4 pair rule:** the registered class map applies per leg; a pair is
  re-signed so the RISK-class currency is the base. Pairs whose two legs
  fall in the same class carry no orientation under this map — they are
  EXCLUDED from the orientation-normalized cohort and reported
  separately; the exclusion count is stated. Cohort statistic and
  bootstrap SD constructed exactly as the market-convention cohort's.

## Amendment 2 (gate construction, before any W1 measurement was read)

Building X37 revealed a boundary of the AR(21) license: on the X36c
vol-tercile world — a channel generated by a nonlinear mechanism — the
AR(21) filter preserves SIGNIFICANCE (3/3 seeds) but retains only 0.31–0.47
of the raw bits, because a persistent drift channel has a genuine linear
projection onto 21 lags. Consequence, fixed before W1 runs: W1's criterion
is survival of the permutation significance, not magnitude retention; a
kill verdict ("AR(21) drives the leak to insignificance") licenses "the
leak is linearly explainable at horizons ≤ 21 days", and a survival
verdict licenses "resistant to linear whitening through lag 21" — neither
speaks to magnitude, and X37d reports the retention boundary on ground
truth. This is recorded here rather than discovered post hoc.

## Budgets

W1: 5 configs × 8 seeds × 2 filters, deterministic re-simulation of the
archived worlds (asserted against stored per-seed values before any new
estimator is read, as in R2) — no new market simulations. W2: 24 new
simulations per arm × 2 arms (seeds 108–131; 100–107 archived). W3: data
only + subsampling of archived per-seed series. W4: data only. Total new
market simulations: 48. One registered calibration shot each for the W1
gate worlds; no tuning anywhere.

## Trial-ledger note

No backtest variants are touched; nothing charges the DSR ledger. Gate
X37 joins `tests/run_all.py` (gate count moves 40 → 41 with the
implementation commit; all count surfaces move in the same commit, which
`check_surfaces.py` enforces).

## Reporting

Results land in `research/robustness2.json`, FINDINGS gains
DECATHLON-R2, and the paper's limitations 2/5/6 and (if any kill fires)
its abstract/title move in the same reconciliation commit. Verdicts are
stated per the framing rule: which claim survives.
