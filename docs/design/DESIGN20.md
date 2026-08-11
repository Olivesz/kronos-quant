# KRONOS-DECATHLON-3 — The Fixed Point of Mutual Anticipation

*Pre-registered. Question: DECATHLON-2 refuted "one anticipator" with a
mechanistic diagnosis — a single anticipator re-leaks the sign one derivative
earlier, because its own inventory rides the same public vol state as the flow
it front-runs. This experiment tests the successor claim that refutation
names: information-free prices require the FIXED POINT of mutual anticipation
— anticipators who also anticipate EACH OTHER'S flows, i.e. the anticipation
operator iterated until the forecastable component of TOTAL flow converges
toward zero. Method: iterate the DESIGN18 anticipation layer K times inside
the frozen DECA2 market, score the byte-untouched battery at K = 0, 1, 5.
The deliverable is the K-ladder: score, per-event flips, the E9
direction-bits trace, and the forecastable-flow fraction vs K.*

## The operator (mechanics, fixed before any run)

The DESIGN18 anticipator forecasts the integrated future mechanical flow from
the current public vol state, `F_hat = kV * mean(L_eq - L)`, and holds
`I = clip(kA * F_hat, ±capA)`. DECA2 measured why that fails: the
anticipator's own inventory is a function of the same slow public state — its
future unwind is exactly as forecastable as the flow it absorbs.

The fixed-point stack makes that unwind part of what is anticipated. Layer k
front-runs the RESIDUAL forecastable total flow — the mechanical flow PLUS
the deterministic future unwind of the k−1 layers beneath it (a layer holding
J will contribute future flow −J as the episode resolves):

    resid_0 = F_hat
    J_k     = clip(kA * resid_{k-1}, ±capA)   (layer k fronts the residual;
                                               each layer is a DECA2-
                                               capitalized cohort)
    resid_k = resid_{k-1} - J_k
    I_K     = J_1 + ... + J_K                  (bounded by K*capA)

Away from the caps this is `I_K = (1 - (1-kA)^K) * F_hat`, and the
model-implied forecastable residual of TOTAL flow contracts geometrically:
`resid_K / F_hat = (1-kA)^K` — toward zero as K grows, which is precisely
the fixed-point claim. K=0 is FCVM (no anticipation), K=1 is byte-for-byte
DECA2's single layer, K→∞ is the rational-expectations limit. The stack
trades as one aggregated flow with ONE execution-noise draw `sA * eps` per
step (so the RNG sequence — and hence the noise world — is identical across
K; only the deterministic flow differs). Causality is inherited: `I_K`
remains a pure function of the current public vol state.

The operator is linear with contraction factor `|1 - kA| = 0.75 < 1` (and
per-layer clipping only shrinks it), so it cannot diverge at any K; the
pre-committed damping rule below is therefore provably unreachable, and is
recorded anyway because it was fixed in advance.

## Fixed budgets (set BEFORE any run, non-negotiable)

- Fixed-point iteration count: K = 5 anticipation iterations exactly (plus
  K=0,1 as comparison points: K=0 is FCVM, K=1 is DECA2's single layer). No
  convergence-based stopping, no trying other K values. If the operator
  diverges at K=5, damp with factor 0.5 per iteration — fixed in advance,
  not tuned.
- Parameter budget: reuse DECA2's frozen anticipator parameters (kA=0.25,
  capA=0.01, sA=0.001) scaled 1/N per anticipator layer where needed; ONE
  pre-registered tuning pass over at most 6 candidate settings ONLY if the
  frozen carry-over scores below FCVM's 5/10 (a regression), with the
  tie-break rule "weakest anticipation wins" as in DESIGN18.
- Seeds: eval on seeds 100–107 (8 seeds, majority vote per event), T=6000 —
  identical to DECA2 so the ablation is comparable.
- Total battery runs are therefore bounded at 3 configs × 8 seeds (+ at most
  6×8 for the contingent tuning pass). More runs than that means the
  experiment is over and the refutation gets written instead.

Layer scaling note: every layer reuses DECA2's frozen (kA, capA) verbatim —
a stack of K DECA2-capitalized cohorts, capital bound K*capA in total. The
only aggregate that would inflate with K is execution noise, and there the
1/N clause bites: the stack posts one aggregate trade with ONE `sA` noise
draw per step, not K draws.

### Amendment (at the gate stage, BEFORE any battery run)

The first formulation clipped the stack's TOTAL inventory at the single
agent's ±capA. Gate X32c — pre-specified before implementation — failed it:
on the toy world the shared cap binds through the whole episode, the K=5
stack holds exactly the K=1 inventory and posts ZERO flow while capped, and
the measured forecastable-flow fraction came out {K=0: 1.000, K=1: 0.750,
K=5: 0.753} — no contraction. A total-capA stack is structurally identical
to DECA2's single agent in every large episode, i.e. it cannot express the
hypothesis it exists to test. The licensed formulation (above) caps EACH
layer at DECA2's capA instead. No battery seed had been run when this was
recorded; the frozen kA/capA/sA values are untouched.

Contingent tuning pass (pre-registered HERE, before any run, used ONLY on a
regression, i.e. frozen K=5 scoring < 5/10 on the eval seeds): the 6
candidates are `kA ∈ {0.05, 0.10, 0.25} × capA ∈ {0.005, 0.01}` with
sA=0.001 fixed, all at K=5; scored on tuning seeds 900–903 (majority of 4,
the DESIGN18 tuning protocol; disjoint from evaluation); selection on total
K=5 score; ties broken by weakest anticipation = lexicographically smallest
(kA, capA). The winner is frozen, then read once on the eval seeds.

## Pre-registered hypotheses

- **D3-1 (STAR):** at (or near) the fixed point, the E9 sign-information
  leak closes and the score exceeds 5/10: K=5 passes E9 and scores > 5/10.
- **D3-2:** the tails/leverage/one-clock events (E2, E5, E6) survive
  fixed-point anticipation — rational front-running does not kill the wild
  facts, only the leaks.
- **D3-3 (the deep one):** if D3-1 holds, the events that REMAIN failed at
  K=5 characterize what flow-rationality alone cannot buy (expected
  residual: long memory E3/E4 and the arrow E8). Conditional on D3-1; if
  D3-1 dies, D3-3 is not evaluable and is reported as such.

**KILL:** if the score at K=5 (after the contingent pass, if it fires) is
still <= 5/10, the fixed-point hypothesis is REFUTED — iterating anticipation
does not close the leak, and flow-rationality alone cannot buy
information-free prices. Reported as loudly as a win.

## Measurements (estimators fixed before any run)

- Battery: byte-untouched DESIGN8 ten-event battery, majority vote over the
  8 eval seeds — the DECA2 protocol, unchanged.
- E9 direction-bits trace vs K: per-seed `dir_bits` for each K, plus the
  median.
- Forecastable-flow fraction vs K: on the deterministic X30c toy world
  (one de-levered vol-targeting cohort, no noise), the projection of the
  realized TOTAL flow onto the mechanical flow,
  `beta_K = <f_mech, D_K> / <f_mech, f_mech>` — beta_0 = 1 by construction;
  uncapped theory beta_K = (1-kA)^K. Both the measured and theoretical
  traces are reported.

## Implementation sketch

`kronos/decathlon.py`:

- `_ant_target_fp(sig2, p, iters)` — the iterated target; `iters <= 1`
  delegates to the untouched `_ant_target` (bit-identical single layer).
- `simulate_abm(..., fixed_point_iters=0)` — default 0 = exactly today's
  behavior (with `anticipators=True`, 0 and 1 are both the legacy single
  layer; the flag adds no RNG draws, so flag-off worlds are byte-identical
  to pre-DESIGN20 output).
- `anticipator_flows(..., fixed_point_iters=0)` — same extension for the
  causality gate.
- `CONFIGS3 = {K0_FCVM, K1_DECA2, K5_FIXEDPOINT}`.

Gate **X32** (`tests/test_decathlon3.py`, deterministic, < 60 s, registered
after X30):

- (a) byte-identity with the feature off: X30a's pinned flag-off hashes must
  still hold with `fixed_point_iters=0`, and the DECA2 anticipator path
  (pinned pre-change hashes of FCVM+A / FV+A / F+A) must be reproduced at
  `fixed_point_iters ∈ {0, 1}` — protecting X19's calibration and DECA2's
  published rows;
- (b) causality of the iterated path at K=5: future-tamper leaves the trade
  prefix unchanged, plus the truncation form (X30b extended);
- (c) mechanism sanity on the X30c toy world: `beta_K` non-increasing over
  K = 0 → 1 → 5 and `beta_5 < beta_1` — the operator actually contracts the
  forecastable flow.

Study: `exp_decathlon3` in `run_research.py` → `research/decathlon3.json`:
the 3-config × 8-seed majority table with per-event flips, per-seed
direction-bits traces, and the forecastable-flow fraction trace.

## Amendment (the contingent pass fired)

Recorded after the eval run, exactly as the protocol above allows: the
frozen carry-over at K=5 scored **3/10** on the eval seeds — below FCVM's
5/10 floor, a regression — so the single pre-registered 6-candidate pass was
spent on tuning seeds 900–903:

| kA | capA | score |
|---|---|---|
| 0.05 | 0.005 | **5/10** |
| 0.05 | 0.01 | **5/10** |
| 0.10 | 0.005 | **5/10** |
| 0.10 | 0.01 | 3/10 |
| 0.25 | 0.005 | 4/10 |
| 0.25 | 0.01 | 4/10 |

Best 5/10, tied across the three weakest settings; the pre-declared
tie-break selected **kA=0.05, capA=0.005** — effective stack strength
`1 − 0.95^5 = 0.226`, WEAKER than DECA2's single frozen layer (0.25). The
DECA2 selection pattern repeats one level up: the battery pays for LESS
anticipation, never more. The winner was then read once on the eval seeds
(the numbers live in FINDINGS and `research/decathlon3.json`).

## Honesty constraints

The battery is byte-untouched; the DESIGN8/DESIGN18 market and anticipator
parameters are byte-untouched; K is the ONLY thing that varies, and it takes
exactly the three pre-registered values. The K=1 rows must reproduce DECA2's
published FCVM+A rows exactly (same sims, same battery seeds) — a free
consistency check, asserted in the study output. No parameter is retuned
outside the contingent pass defined above, and that pass exists only on a
regression below FCVM's floor.
