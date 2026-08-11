# KRONOS-DECATHLON-2 — The Missing Organ Is Expectation

*Pre-registered. Question: DECATHLON (DESIGN8) ended at a 5/10 ceiling and
concluded that the minimal market's missing organ is EXPECTATION — anticipatory
agents who trade against predictable flows. This experiment builds that agent
and measures whether the ceiling breaks. Method: ONE new agent type added to
the frozen DESIGN8 market, ablated over {FCVM, FCVM+A, FV+A, F+A}, scored on
the byte-untouched ten-event battery. The deliverable is the ablation table
and the per-event diagnosis: WHICH events expectation buys.*

## Where the 5/10 ceiling stands (measured, decathlon.json)

The best flow-only config, FCVM, fails exactly five events: E3 (slow vol
clustering), E4 (long-memory clock), E7 (clock up-jumps, marginal at
skew −0.41 vs −0.35), E8 (arrow in the coupling), E9 (information-free
signs — it leaks 0.018 significant direction bits). The leak has a known
source: the vol-targeters' de/re-leveraging is serially correlated, and the
one-lag market maker cannot absorb a multi-day drift.

## The anticipatory agent (A)

The vol-targeters' flow is mechanical and forecastable from public
information alone: their leverage rule `L = min(Lmax, sigma*/sigma_hat)` and
their vol estimator (EWMA of squared returns at a known speed) are both
computable from the price tape. A real front-runner knows exactly this — the
mandate and the tape — and nothing else. The agent is handed the same.

At each step the anticipator:

1. reconstructs the targeters' estimate `sigma_hat^2` from the return
   history (the same EWMA recursion the targeters run — public information;
   gate X30b certifies this is causal via the truncation trick);
2. forecasts the INTEGRATED future mechanical flow under the one belief that
   defines it — vol reverts to the targeters' own target `sigma*` — so
   leverage ends at `L_eq = min(Lmax, 1)` and the total remaining flow the
   current vol state implies is

       F_hat_t = kV * mean_cohorts(L_eq - L_t)

3. holds inventory proportional to that forecast, capped by capital:
   `I*_t = clip(kA * F_hat_t, -capA, +capA)`;
4. trades the inventory change plus execution noise:
   `D_ant,t = (I*_t - I*_{t-1}) + sA * eps_t`.

No future prices, no future flows, no other agents' books: `I*` is a pure
function of the current vol state. The unwind is automatic — as vol reverts
and the targeters re-lever (a buying drift), the forecast decays to zero and
the anticipator sells its inventory into exactly that flow. This is
front-running as it actually works: buy into the panic-selling, sell into
the mechanical recovery bid. In quiet regimes the sign flips (targeters sit
levered above L_eq; the anticipator holds the capped short against the
eventual de-leveraging).

Three parameters, fixed BEFORE any battery run:

| param | value | meaning |
|---|---|---|
| kA | 0.5 | fraction of the integrated forecast flow front-run |
| capA | 0.02 | inventory cap — limited capital (~2 daily sigmas of impact) |
| sA | 0.002 | execution/forecast noise |

## Ablation ladder (DESIGN8 parameters byte-untouched)

    FCVM     best-old baseline, re-run (control)
    FCVM+A   the expectation hypothesis
    FV+A     anticipators replacing chartists+MM on the raw spiral
    F+A      anticipators WITHOUT vol-targeters — no flow to forecast

8 evaluation seeds (100–107), T=6000, majority vote per event — the DESIGN8
protocol, unchanged. In F+A the agent still trades its model (it cannot know
the targeters are absent); with no mechanical flow behind the forecast, its
trades should buy nothing.

## Pre-registered hypotheses

- **D2-1 (STAR):** adding anticipators to the best 5/10 config raises the
  score: FCVM+A > 5/10, prediction **>= 7/10**.
- **D2-2:** the specific events anticipation buys are the forecastable-flow
  ones: **E9** (information-free signs — the re-leveraging drift IS the sign
  leak, and the anticipator arbitrages it away; the sharpest single
  prediction) and **E3/E4** (long memory — front-loading plus the slow
  capped unwind stretch the vol episode). E8 may follow (anticipation is an
  arrow-in-the-coupling mechanism: expectations put the future into the
  present) but is not required for D2-2.
- **D2-3 (interaction):** anticipation WITHOUT vol-targeters buys nothing —
  F+A ≈ F (3/10). Anticipators need a predictable flow to trade against;
  expectation is an organ that only works attached to the body.

## Tuning budget and kill criterion

The parameters above are the first shot. If FCVM+A scores < 7/10 on the
TUNING seeds (900–903, disjoint from evaluation), ONE pre-registered pass
over the grid `kA in {0.25, 0.5, 1.0} x capA in {0.01, 0.02, 0.05} x
sA in {0.001, 0.002}` may be run on those tuning seeds, selecting on the
FCVM+A total score; **parameters are frozen after that one pass**, exactly
as DESIGN8 froze its own, and the evaluation seeds are only then read.

**KILL:** if the frozen FCVM+A does not EXCEED 5/10 on the evaluation
seeds, the expectation hypothesis is REFUTED and reported as such — a
refuted mechanism with a working gate is a full result.

## Amendment (after the tuning pass, BEFORE reading any evaluation seed)

The first shot scored 4/10 on the tuning seeds, so the one grid pass was
spent. Its best score was 5/10, tied across seven settings — all six
kA=0.25 combinations plus (0.5, 0.01, 0.001) — i.e. the score is flat
wherever the anticipator is weak. No tie-break was pre-specified; the rule
adopted (deterministically, before any evaluation seed was run) is the
lexicographically smallest tied setting: **kA=0.25, capA=0.01, sA=0.001**,
the weakest anticipator among the ties. That the selection lands on
"trade as little as possible" is recorded here because it is already
evidence about the hypothesis.

## Honesty constraints

The battery is byte-untouched; the DESIGN8 flow parameters are
byte-untouched; ablations toggle the flag, never retune. With
`anticipators=False` the simulator must reproduce the old market
byte-for-byte (gate X30a pins pre-change output hashes, protecting X19's
SPY-10 / GBM-3 calibration). The forecast must be causal: X30b tampers with
future returns and requires the trade prefix unchanged; X30c requires that
on a deterministic toy world with a perfectly predictable mechanical flow
the anticipator profits AND damps the flow's price impact — the mechanism
is licensed before any battery score is read.
