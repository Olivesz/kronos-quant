# KRONOS-DECATHLON-4 — Price-Setting Rationality: The Quote-Skewing Maker

*Pre-registered. Question: DECATHLON's 5/10 ceiling has now survived two
flow-side attacks. DECA2: ONE anticipator trading against the forecastable
vol-targeting flow re-leaks the sign one derivative earlier. DECA3: ITERATING
anticipation (K=5) makes the leak grow — the K-stack is algebraically one
stronger anticipator, and open-loop contraction dies in closed-loop
equilibrium. The refutations share a diagnosis: any agent that TRADES against
forecastable flow adds its own forecastable flow, because its inventory rides
the same slow public state. This experiment tests the one hypothesis that
diagnosis leaves standing: the missing ingredient is PRICE-SETTING
rationality — a market maker who does not trade against the flow but QUOTES
against it, pre-adjusting the price by the expected impact of the forecastable
flow component, so the information is absorbed into the price LEVEL rather
than left in the return. Method: one new pricing rule added to the frozen
DESIGN8 market, ablated over {FCVM, FCVM+Q(1.0), FCVM+Q(0.5)}, scored on the
byte-untouched ten-event battery. This is the third and final attempt on the
expectation line; the closure clause below is part of the registration.*

## Where the line stands (measured)

FCVM fails exactly five events: E3 (slow vol clustering), E4 (long-memory
clock), E7 (clock up-jumps), E8 (arrow in the coupling), E9 (information-free
signs — 0.018 significant direction bits). The E9 leak's source is known: the
vol-targeters' de/re-leveraging drift is serially correlated and forecastable
from the tape. DECA2 and DECA3 established that no boundedly-capitalized
agent — nor any depth of mutual anticipation among such agents — can trade
the leak away: bits went 0.018 → 0.020 (one layer) → 0.026 (five layers)
while the model-space forecastable flow fell 1.00 → 0.24. Trading against the
flow moves the leak; it does not remove it.

## The quote-skewing maker (Q)

The failure mode of DECA2/3 was INVENTORY: an anticipator's position is a
function of the slow public vol state, so its own trades are exactly as
forecastable as the flow it absorbs. The maker here holds no directional
inventory and adds no flow. It is a pricing rule: it computes the same
causal public-state forecast of the vol-targeters' remaining mechanical flow
that DECA2's anticipator used (the `_ant_target` forecast machinery, WITHOUT
the kA/capA inventory rule), and skews its quotes so the price already
carries the expected impact of that flow:

    F_hat_t = kV * mean_cohorts(L_eq - L_t)      (DESIGN18's integrated
                                                  forecast: public mandate +
                                                  public EWMA state, causal)
    q_t     = quote_skew * lam * F_hat_t         (the quote adjustment)
    r_t     = lam * D_t + (q_t - q_{t-1})        (price formation, shifted
                                                  BEFORE flows execute)

with `q` initialized from the initial state (which is exactly 0 in
`simulate_abm`, whose world starts at the vol target). `quote_skew` is the
skew strength lambda; `quote_skew = 0` is byte-identical to today's
simulator (the branch adds no RNG draws and no float operations).

Why this is a different animal from DECA2/3, stated as the identity that
defines it: the maker's forecast state IS the targeters' state (the mandate
and the estimator are public), so the quote revision telescopes against the
mechanical flow exactly —

    q_t - q_{t-1} = -quote_skew * lam * f_mech,t

where `f_mech,t = kV * mean(L_t - L_{t-1})` is the vol-targeters' time-t
flow. At full skew the mechanical flow's ENTIRE price impact is absorbed
into the level (the price carries `quote_skew * lam * kV * mean(L_eq - L)`,
the expectations-augmented level); the realized return contains only the
unforecastable flow surprise. No inventory, no unwind, no cap, no execution
noise — nothing that could re-leak. The flow itself still executes and is
untouched; only WHERE its impact lands (level vs return) changes.

Causality: `q_t` is a pure function of the vol state through t (the EWMA
having absorbed returns through t−1 — the same alignment as the
anticipator's target in `simulate_abm`), computed before the time-t flows
execute. No look-ahead, no within-bar fixed point. Gate X34b enforces this
with the DECA2/3 tamper-and-truncate protocol.

## Fixed budgets (set BEFORE any run, non-negotiable)

- Skew strengths: lambda in {1.0, 0.5} only. 1.0 is the theory case — the
  price pre-moves by exactly the expected impact of the forecastable flow;
  0.5 is half. No other lambda values.
- Eval seeds 100–107, T=6000, majority vote per event — identical to
  DECA2/3 so the ablation is comparable.
- Configs: {FCVM control, FCVM+Q(1.0), FCVM+Q(0.5)} = 3 × 8 runs, plus ONE
  contingent 6-candidate × 4-seed pass ONLY if both lambda values REGRESS
  below FCVM's 5/10, with the tie-break rule "weakest skew wins" (smallest
  lambda among ties). The contingent candidates, fixed here: lambda in
  {0.05, 0.10, 0.15, 0.20, 0.30, 0.40}, scored on tuning seeds 900–903
  (majority of 4 — the DESIGN18/20 tuning protocol; disjoint from
  evaluation); selection on total score; the winner is frozen, then read
  once on the eval seeds.
- More runs than 24 + 24 means the experiment is over and the refutation
  gets written instead.

## Pre-registered hypotheses

- **D4-1 (STAR):** with the quote-skewing maker at full skew, the E9
  sign-information leak closes and the score exceeds 5/10: FCVM+Q(1.0)
  passes E9 and scores > 5/10.
- **D4-2:** the wild one-sided facts survive (E2 fat tails, E5 leverage,
  E6 one-clock) — the maker neutralizes only the forecastable MEAN of the
  flow, not the vol dynamics.
- **D4-3:** per-event diagnosis of whatever remains failed (expected
  residual: long memory E3/E4, arrow E8).

**THE CLOSURE CLAUSE:** This is the third and final attempt on the
expectation line. If D4-1 is refuted at this budget, the 5/10 ceiling is
declared STRUCTURAL for flow-based minimal markets with boundedly-rational
agents of any class here considered, and the DESIGN8 line CLOSES — no
DECATHLON-5.

## Measurements (estimators fixed before any run)

- Battery: byte-untouched DESIGN8 ten-event battery, majority vote over the
  8 eval seeds — the DECA2/3 protocol, unchanged.
- E9 direction-bits trace vs lambda in {0, 0.5, 1.0}: per-seed `dir_bits`
  plus the median, per config.
- Mechanism trace on the deterministic toy world (the X34c estimator, below):
  corr(forecastable-flow component, next-period return) at lambda 0 vs 1,
  plus the mechanical-flow invariance check.
- The wild-fact medians (kurt, leverage, tail_asym) vs lambda — D4-2's
  evidence either way.

## Implementation sketch

`kronos/decathlon.py`:

- `_flow_forecast(sig2, p)` — DESIGN18's forecast machinery factored out of
  `_ant_target` (float-identical; X30/X32 pins verify), shared by the
  anticipator and the maker.
- `simulate_abm(..., quote_skew: float = 0.0)` — default 0.0 = exactly
  today's behavior (no extra RNG draws, no extra float ops; byte-identity is
  gate X34a's contract). When nonzero, price formation becomes
  `r = lam*D + (q - q_prev)` as above.
- `maker_quote_path(r, params=None, hetero=False, quote_skew=1.0)` — the
  deterministic quote path against an EXOGENOUS return series (q[t] depends
  on r[:t] only; same alignment as `anticipator_flows`), for the causality
  gate.
- `CONFIGS4 = {FCVM, FCVM+Q1.0, FCVM+Q0.5}`.

Gate **X34** (`tests/test_decathlon4.py`, deterministic, < 60 s, registered
after X32):

- (a) byte-identity: with `quote_skew=0` the X30a flag-off pins AND the
  X32a anticipator-path pins must be reproduced exactly (this also verifies
  the `_flow_forecast` refactor changed no floats) — protecting X19's
  SPY-10/GBM-3 calibration and DECA2/3's published rows. The flag must be
  live (lambda=1 is a different world), deterministic, finite, sane vol.
- (b) causality: future-tamper (3 tampers) + truncation leave the
  `maker_quote_path` prefix bit-identical; the tail must differ (the quote
  actually uses the tape).
- (c) MECHANISM on the X30c deterministic toy world, extended with a small
  seeded ambient noise flow (sn=0.002, fixed rng seed) — needed because at
  lambda=1 the noiseless toy's returns are identically zero and the
  correlation is undefined; the noise is the "unforecastable surprise" the
  return should keep. Requirements, fixed here: at lambda=1.0 the
  correlation between the forecastable-flow component `f_mech,t` and the
  NEXT-period return collapses, |corr| < 0.1, where the unskewed corr is
  substantial (> 0.3; both printed) — while the mechanical-flow series
  itself is essentially unchanged (same noise draws; max |Δf| < 10% of peak
  |f| and total re-leveraging Σf within 5%): the leak is absorbed into the
  price level, NOT suppressed by killing the flow. At lambda=0 the toy run
  must match the no-maker baseline bit-identically (same corr exactly).

### Amendment (at the gate stage, BEFORE any battery run)

Two toy-world details in the X34c spec above were mis-set, discovered while
building the gate and fixed before any battery seed was run:

1. **Noise scale.** sn=0.002 is comparable to the re-leveraging drift's
   per-step magnitude (peak ~0.0015 under the frozen parameters), so the
   UNSKEWED correlation comes out 0.16 — below the 0.3 bar, i.e. the probe
   cannot see the leak it exists to measure. sn is lowered to 0.0005
   (measured unskewed corr 0.66; the skew mechanics are untouched).
2. **Initial leverage state.** X30c starts `L_prev = 1.0` against an
   already-shocked `sigma_hat = 3 sigma*`, which injects a one-time t=0
   de-leveraging impulse (|f| = 0.04, ~25x the drift scale). That impulse
   is an initialization artifact, and its V-turn pairing dominates and
   dilutes the correlation. For X34c the toy starts with
   `L_prev = L(sigma_hat_0)` — the leverage state already at its shocked
   value — so the measured object is exactly the forecastable
   RE-LEVERAGING DRIFT, which is the E9 leak. Everything else (T=150,
   shock 3 sigma*, the ambient sig2 floor, the frozen parameters) is
   X30c's world unchanged.

No battery seed had been run when this was recorded; the thresholds
(unskewed > 0.3, skewed |corr| < 0.1, flow invariance) are untouched.

Study: `exp_decathlon4` in `run_research.py` → `research/decathlon4.json`:
the 3-config × 8-seed majority table with per-event flips, per-seed
direction-bits traces, the toy mechanism trace, and — only if both lambdas
regress below 5/10 — the contingent pass record.

## Amendment (the contingent pass fired)

Recorded after the eval run, exactly as the protocol above allows: BOTH
lambda values regressed below FCVM's 5/10 on the eval seeds —
FCVM+Q(1.0) scored **1/10**, FCVM+Q(0.5) **3/10** — so the single
pre-registered 6-candidate pass was spent on tuning seeds 900–903:

| lambda | score |
|---|---|
| 0.05 | **5/10** |
| 0.10 | **5/10** |
| 0.15 | **5/10** |
| 0.20 | **5/10** |
| 0.30 | **5/10** |
| 0.40 | 4/10 |

Best 5/10, tied across every candidate up to lambda=0.30; the pre-declared
weakest-skew tie-break selected **lambda=0.05**. The winner was then read
once on the eval seeds: 5/10, failing exactly FCVM's five events. The
DECA2/DECA3 selection pattern repeats a third time, now for a pricing rule:
the battery pays for the LEAST intervention at every opportunity — the best
quote-skewing market is the one that barely skews. D4-1 is refuted; per the
closure clause, the numbers and the structural verdict live in FINDINGS and
`research/decathlon4.json`, and the DESIGN8 line is closed.

## Honesty constraints

The battery is byte-untouched; the DESIGN8/18/20 market, anticipator
parameters, and seeds are byte-untouched; `quote_skew` is the ONLY new
degree of freedom and it takes exactly the two pre-registered values (plus
the contingent ladder under its trigger). With `quote_skew=0` the simulator
must reproduce the old market byte-for-byte. The maker holds no inventory
and posts no flow — if closing the leak requires it to trade, the
hypothesis is dead by construction and DECA2/3 already wrote its obituary.
Either outcome is a full result: the ceiling breaks, or the line closes
with a structural claim — the closure clause above is not optional.
