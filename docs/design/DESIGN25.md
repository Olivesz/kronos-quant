# KRONOS-DECATHLON REFEREE PROGRAM — attribution and robustness of the closed line

*Pre-registered. Three independent referee reports on the DECATHLON paper
returned major-revision verdicts on the CONTENT: the depth/strength confound
in the K-ladder, the AC1 confound in the E9 statistic
(corr(AC1, dir_bits) = −0.89 across the archived grid), the 8-seed power of
the two surviving "leak grows" comparisons, the wildness ≡ forecastable-flow
identification, the frozen (never re-equilibrated) market, and integer scores
sitting on marginal thresholds. This document registers six experiments
(R1–R6) that answer them. Everything below — hypotheses, budgets, estimators,
decision rules — is declared BEFORE any run. Response variables (scores,
direction bits, MI components) have not been seen for any new configuration;
all previously archived numbers cited here are from the published JSONs.*

**The DESIGN8 closure clause stays closed.** R1–R6 are attribution and
robustness measurements of EXISTING published results. No new rationality
organ is proposed; no new attempt on the 5/10 ceiling is registered. R5
stress-tests whether the published structural claim survives re-equilibration
of a frozen parameter — if it does not, the published claim is RESCOPED, and
the closure clause (no DECATHLON-5, no new bolt-on-rationality hypotheses)
remains in force either way.

**Reporting standard (fixed now):** each experiment ends in a verdict about
WHICH CLAIM SURVIVES, not about how a sentence could be hedged. If an
analysis cannot separate a genuine effect from an artifact, that
inseparability is itself the reported result. If the surviving claim implies
a different headline than the published one, FINDINGS says so explicitly.

No Sharpe-ledger entries: every experiment is measurement, not backtesting.

## Fixed total budget (declared before any run)

Battery-scored simulations (T = 6000, full ten-event battery each):

| Item | Runs |
|---|---|
| R1 matched-strength arms, 2 × 32 seeds | 64 |
| R3 32-seed extensions, 2 × 32 seeds | 64 |
| R4 eval (FCVM-T3 control + FCVM-T3+Q1.0), 2 × 8 seeds | 16 |
| R5 tuning (2 arms × 6 kM candidates × 4 seeds) | 48 |
| R5 eval (2 winners × 8 seeds) | 16 |
| R6 reproduction reruns (8 configs without stored per-seed stats × 8 seeds) | 64 |
| **Total battery runs** | **272** |

Non-battery simulations: R2 re-generates 5 published worlds × 8 seeds = 40
sims (E9-family estimators only, no battery scores read); R4 calibration =
6 scales × 4 tuning seeds = 24 sims (kurtosis only, no battery). Grand total
336 simulations. More runs than this means the corresponding experiment is
over and its refutation branch gets written instead. (The parent estimate was
"well under 200 battery runs"; the R1 upgrade from archive-reanalysis to a
clean 2×32 matched-strength design, and R6's rerun clause for the eight
configs whose per-seed stats were never archived, account for the difference.
Wall-clock cost ≈ 0.45 s per battery run ≈ 2 minutes total; the budget is a
selection-control device, not a compute constraint.)

Seeds: evaluation 100–107 (the DESIGN8/18/20/22 protocol), extensions
100–131 (the DESIGN24 A2 protocol), tuning 900–903 (disjoint). Battery seed
= seed index within each run set, exactly as in the published experiments.

---

## R1 — strength vs depth: the exact matched-strength design

**Referee concern (R1 #1, R2 #4):** away from caps the K-stack telescopes to
ONE anticipator of strength 1−(1−kA)^K, so the published K-ladder confounds
depth with effective strength; the archived near-matched pair (tuned K=5 at
0.226 vs K=1 at 0.25) already points the other way (0.0168 < 0.0200).

**Design (fixed now).** Fix effective strength s\* = 0.25 exactly and run
BOTH arms on seeds 100–131 (power aligned with R3):

- **Arm a (depth 1):** K = 1, kA = 0.25 — byte-identical config to DECA2's
  frozen layer (capA = 0.01, sA = 0.001). Its 32-seed per-seed bits must
  reproduce the stored DESIGN24 A2 vector (`decathlon3.json
  k01_extension.per_seed.K1_DECA2`) exactly — asserted at run time.
- **Arm b (depth 5):** K = 5, per-layer kA₅ = 1 − (1−0.25)^(1/5)
  = 1 − 0.75^0.2 ≈ **0.0559125**, so 1 − (1−kA₅)⁵ = 0.25 exactly.
  capA = 0.01 per layer, sA = 0.001, one aggregate noise draw — the DESIGN20
  stack mechanics, byte-untouched.
- **Cap caveat (stated now):** the telescoped equivalence is exact only away
  from the per-layer caps. Both arms therefore also report a REALIZED
  effective strength per seed: reconstruct the public vol state from the
  simulated returns (the same EWMA recursion the agents run), rebuild the
  F̂_t and I\*_t paths, and take β_realized = Σ(I\*_t·F̂_t)/Σ(F̂_t²). If the
  realized strengths of the two arms differ by more than 10% relative, the
  comparison is reported as approximately-matched with both values, not
  silently treated as exact.

**Analysis (fixed now):** paired per-seed direction bits, arm b − arm a;
two-sided Wilcoxon signed-rank (primary, α = 0.05), two-sided sign test
(secondary). Additionally, the full strength axis is assembled from archived
data (no new runs): eval-seed arms K0/K1/K5-frozen/K5-tuned at effective
strengths 0/0.25/0.7627/0.2262, the 18-setting DESIGN18 tuning grid at
strength = kA (tuning seeds, flagged as such), with Spearman ρ(strength,
bits) and the archived corr(AC1, bits) re-derived and stored.

**Decision rule (fixed now):** this establishes what the published K-axis
actually was. If depth-5 ≤ depth-1 at matched strength (Wilcoxon fails to
find depth-5 > depth-1), the published "deeper anticipation grows the sign
leak" attribution is DEAD: the finding becomes "iterated anticipation
collapses to a stronger single anticipator, and STRENGTH grows the leak" —
stated as such in FINDINGS, with the abstract-level implication named. If
depth-5 > depth-1 (p < 0.05, positive median), depth has an effect beyond
strength and the published attribution stands with the confound excluded.

**Prediction (honest):** the archived near-matched pair and the telescoping
algebra both say depth adds nothing; expected outcome is the attribution
dies.

**Deliverable:** `strength_depth` block in `research/robustness.json`
(per-seed bits both arms, realized strengths, tests, the assembled
strength-axis table).

## R2 — E9 attribution: is the "rise" induced reversal scored as sign information?

**Referee concern (all three):** E9's feature set includes sign(r_t); every
intervention that raises dir-bits also drives AC1(r) to ≈ −0.25; induced
one-lag reversal is mechanically sign information. The published "the market
re-creates sign information in price space" and the null "over-strong
intervention causes reversal, and E9 detects reversal" are currently
indistinguishable.

**Configs (fixed now):** FCVM control, K1 (context), K5-frozen, Q0.5
(context), Q1.0 — the five published worlds with stored per-seed dir-bits.
Seeds 100–107, worlds re-generated deterministically; the recomputed raw E9
bits must match the stored per-seed values (6 dp) for every config/seed —
asserted before any new estimator is read.

**Estimators (fixed now; all use the battery's E9 feature construction,
copied verbatim into `kronos/robustness.py` and gate-checked for identity):**

1. **Per-feature MI decomposition:** I(sign_t; y), I(mom21; y),
   I(vol_terc; y), each with its own 120-permutation null; the joint (the
   published statistic); and the conditional MI I(mom21, vol_terc; y |
   sign_t) computed by stratification over sign_t with a stratified
   permutation null (y permuted within sign_t strata, 120 shuffles) — the
   AC1-matched null the econometrician referee asked for.
2. **AR(1)-whitened recomputation:** per seed, φ̂ = lag-1 autocorrelation of
   r; e_t = (r_t − r̄) − φ̂(r_{t−1} − r̄); the FULL E9 block (features and
   target rebuilt from e) recomputed on the whitened series. Also recorded:
   AC1(r), AC1(sign r) per seed.

**New estimator ⇒ new gate (X36, `tests/test_robustness.py`), registered
now, passing BEFORE any R2 measurement is read:**
- (a) estimator identity: the copied E9 block reproduces
  `battery()["stats"]["dir_bits"]` exactly (in-process equivalence) on
  simulated worlds, and reproduces stored per-seed JSON values;
- (b) analytic calibration: on a synthetic AR(1) world (φ = −0.3) the
  sign_t-alone MI matches the closed form 1 − H₂(1/2 + arcsin(φ)/π) within
  tolerance, raw joint bits are significant, and whitened bits are NOT — the
  whitener removes exactly the linear channel;
- (c) orthogonality: on a synthetic world whose sign information rides the
  vol-tercile channel (not linear AC1), whitening PRESERVES significant
  bits — the whitener does not destroy nonlinear sign structure.

**Decision rule (fixed now).** For each arm ∈ {K5-frozen, Q1.0} vs control:
- **Primary:** two-sided Wilcoxon on per-seed whitened-bits differences
  (arm − control). The published rise survives whitening only if p < 0.05
  with positive median difference.
- **Secondary (attribution):** the share of the raw rise carried by the
  sign_t-alone component, and the conditional-MI difference.
- If the rise vanishes under whitening (primary fails) and the decomposition
  puts the majority of the raw rise in the sign_t-alone component, the
  published "re-created in price space" reading is **WITHDRAWN**; the
  licensed claim becomes "the leak never closes at any strength" and the
  bits-rise is attributed to intervention-induced linear reversal.
- If the rise survives whitening, the inversion stands with the confound
  excluded, and FINDINGS says so.
- **Control's own leak:** the same whitened measurement is reported for
  FCVM itself. If control's whitened bits are insignificant on a majority
  of seeds, the finding is stated at full strength: the minimal market's
  E9 failure is one-lag linear sign structure, full stop — whatever that
  implies for the published narrative gets said, not softened.
- If the estimators cannot separate the channels (e.g. whitening removes
  the control leak and the rise together in a way that leaves no residual
  to attribute), THAT INSEPARABILITY IS THE RESULT and is reported as such.

**Prediction (honest):** corr(AC1, bits) = −0.89 across the archived grid
says most of the rise is the linear channel; expected outcome is the
inversion dies and the licensed claim becomes non-closure.

**Deliverable:** `e9_attribution` block in `research/robustness.json`.

## R3 — 32-seed extensions of the two surviving "leak grows" comparisons

**Referee concern (all three):** the K5 and Q1.0 rises rest on 7-of-8 seeds;
the paper's own A2 precedent (K0→K1 extended to 32 seeds, came back flat,
claim retracted) sets the standard the surviving increments must meet.

**Protocol (fixed now, identical to DESIGN24 A2):** seeds 100–131, T = 6000,
one run, no extension regardless of outcome. Arms: **K5-frozen**
(fixed_point_iters = 5, DECA2 frozen params) and **FCVM+Q1.0**. The first 8
seeds must reproduce the stored per-seed bits
(`decathlon3.json dir_bits_vs_K.K5_FIXEDPOINT`,
`decathlon4.json dir_bits_vs_lambda.FCVM+Q1.0`) exactly — asserted. The
32-seed control vector is the stored A2 K0 vector
(`k01_extension.per_seed.K0_FCVM`; same seeds, same battery-seed protocol —
not re-run).

**Analysis (fixed now):** paired per-seed bits vs control; two-sided
Wilcoxon signed-rank (primary, α = 0.05), two-sided sign test (secondary).
Per-seed bits emitted for both arms.

**Decision rule (fixed now):** per arm — Wilcoxon p < 0.05 with positive
median difference ⇒ the rise stands at 32 seeds (reported with the test);
otherwise the 7-of-8 rise DISSOLVES to "statistically flat at 32 seeds" and
every published "grows" statement resting on it is downgraded to "does not
close", exactly as A2 downgraded the one-layer step. R2 and R3 compose: the
"grows" language survives only if BOTH the 32-seed test passes AND the
whitened attribution (R2) leaves a non-artifact residual.

**Prediction (honest):** the 8-seed effects (+0.005, Wilcoxon ≈ 0.016) are
≈ 5× the K0→K1 step that dissolved; genuinely uncertain — either branch is
a full result.

**Deliverable:** `ext32` block in `research/robustness.json`.

## R4 — a second wildness source: Student-t(3) fundamental innovations

**Referee concern (R1 #4, R2 #1, R3 #3):** in the published model the ONLY
wildness generator is the vol-targeting spiral, which is also the only
forecastable flow — so "absorption deletes the wildness" is close to entailed.
A second wildness source not forecastable from the public vol state breaks
the identity.

**Design (fixed now).** New simulator flag `fund_t3_scale` (default 0.0 =
byte-identical draw path, gate-checked): when nonzero, the fundamental
innovation becomes `V += fund_t3_scale · t(3)` in place of
`V += sV · N(0,1)`. df = 3 fixed. The t-shocks enter returns through the
fundamentalist flow kF(V − price) — outside the span of F̂, so the
quote-skewing maker cannot absorb them by construction.

**Calibration (ONE pre-registered shot, fixed now, no tuning):** scale
ladder {0.5, 0.75, 1.0, 1.5, 2.0, 3.0} × (sV/√3) — the 1.0 point is
variance-matching, Var(t₃) = 3 — run ONCE on tuning seeds 900–903 (FCVM-T3,
kurtosis of returns only; no battery score, no E9 statistic is read).
Selected scale: the one whose 4-seed median return kurtosis is closest to
FCVM's stored 8.786. The selection statistic is a calibration target
(wildness magnitude), not a response variable. Frozen thereafter.

**Eval (fixed now):** seeds 100–107, majority vote — **FCVM-T3** (control)
and **FCVM-T3+Q1.0** (full absorption), the DESIGN22 protocol otherwise
unchanged. Report full battery rows, per-seed dir-bits, kurt/tail/clustering
stats.

**Decision rule (fixed now):**
- If in FCVM-T3+Q1.0 the tails survive absorption (E2 passes by majority)
  while the leak persists (E9 fails by majority), then absorption
  demonstrably does NOT delete wildness once wildness has a non-flow source
  — the wildness-deletion half of the published Experiment III was
  parameterization-bound, and the non-closure of the leak is thereby
  demonstrated in a world where wildness ≢ forecastable flow. The
  joint-production claim survives ONLY in the rescoped form the data
  licenses (see below).
- If wildness still dies (E2 fails), the published claim is structural to
  flow-generated wildness only, and is scoped to exactly that.
- Either way, the ASYMMETRIC wild facts (E5 leverage, E10 crash asymmetry,
  E7) are reported separately from symmetric tails (E2): the pre-stated
  expectation is that symmetric t-tails cannot rescue the one-sided events,
  in which case the surviving claim is: **sign-efficiency and the
  asymmetric wild facts are jointly produced by state-riding flows;
  symmetric fat tails alone can be exogenous** — and FINDINGS states that
  as the claim, replacing the broader published phrasing if that is what
  the data shows.

**Deliverable:** `t3_absorption` block in `research/robustness.json`
(calibration table + eval rows).

## R5 — bounded re-equilibration: does the ceiling survive letting kM adapt?

**Referee concern (R1 #5):** every published regression is proximately the
frozen one-lag maker's reversion dominating once the spiral is damped; the
market was never allowed to re-equilibrate around the added rationality, so
"bolt-on rationality fails" is partly "hand-set balance breaks".

**Design (fixed now, mirroring DESIGN18's tuning discipline).** Joint
re-tune of **kM only** (all other parameters byte-frozen), alongside:
- **Arm a:** FCVM+A — the K = 1 anticipator at DECA2's frozen parameters;
- **Arm b:** FCVM+Q1.0 — the full-skew maker.

Candidates (fixed now): kM ∈ {0.0, 0.10, 0.20, 0.30, 0.45, 0.60} — removal,
two damped values, the frozen value, and two strengthened values. Tuning
seeds 900–903, T = 6000, majority-of-4 battery score, selection on total
score. Tie-break (fixed now): among tied best scores, smallest |kM − 0.30|
wins (least re-equilibration); residual ties (0.0 vs 0.60) → the smaller kM.
Each winner is frozen, then read ONCE on eval seeds 100–107 with per-seed
export.

**Decision rule (fixed now):** if either re-equilibrated arm EXCEEDS 5/10 on
the eval seeds, the published structural-ceiling claim is WRONG AS STATED —
the ceiling was partly an artifact of frozen liquidity provision — and
FINDINGS reports the corrected claim (what rationality + adapted liquidity
buys, and what it still cannot). If both arms remain ≤ 5/10, the ceiling
survives re-equilibration of the liquidity parameter and the structural
claim strengthens; the winning kM values and their event patterns are
reported either way. (Scope note, stated now: this re-equilibrates ONE
parameter of one agent. A full general-equilibrium re-tune is out of scope
and the claim will be scoped to what was tested.)

**Prediction (honest):** the three published tuning passes all selected the
least intervention available; expected outcome is kM stays at or near 0.30
in arm a, moves lower in arm b, and the ceiling holds — but the kill branch
is live: this is the referee concern with the best mechanistic case for an
upset.

**Deliverable:** `requilibration` block in `research/robustness.json`
(both grids, winners, eval rows).

## R6 — threshold robustness of the integer scores

**Referee concern (R3 #5, R1 minor, R2 #6):** the 5/10 ceiling and the
comparative structure inherit the placement of individual thresholds;
seed-bootstrap SEs (DESIGN24 A3) measure seed noise, not threshold
fragility.

**Design (fixed now).** The battery has 12 numeric thresholds: E1 band
(−0.15, 0.05), E2 band (4.5, 40), E3 pair (0.12, 0.05), E4 (0.12), E5
(−0.03), E6 (5.0), E7 (−0.35), E8 ratio (0.75), E10 (1.25). Each is
perturbed ONE AT A TIME by δ ∈ {−20%, −10%, +10%, +20%} of its magnitude
(48 perturbed scorings per config + baseline). E9 has NO numeric threshold —
its verdict is a permutation test — so it is held fixed at the published
per-config verdict and stated as non-perturbable. E8's significance flag is
likewise held fixed; only its 0.75 ratio is perturbed.

Rescoring is a pure function of per-seed statistics (majority vote of
perturbed per-seed events) — **no re-simulation**:
- Stored per-seed stats are used for the 7 configs that have them
  (FCVM = K0, K1 = FCVM+A, K5-frozen, K5-tuned, Q1.0, Q0.5, Q-tuned) and
  for SPY (single stored series stats, from decathlon.json).
- The 8 published configs WITHOUT archived per-seed stats (G, F, FC, FV,
  FCV, FCVMH, FV+A, F+A) get ONE deterministic reproduction rerun each
  (8 seeds, per-seed export), which must reproduce the published majority
  score exactly — asserted, exactly as DESIGN24 A3 asserted.
- Baseline check: at δ = 0 the rescorer must reproduce every published
  score from the per-seed stats — asserted before any perturbed score is
  read.

**Analysis (fixed now):** per config, the score band [min, max] over all
single-threshold perturbations at |δ| = 10% and 20%; per perturbation, the
comparative invariants: (i) does any simulated config exceed FCVM's score
under the SAME perturbation; (ii) does any intervention arm (A, K5, Q)
exceed its control FCVM; (iii) SPY's 10/10 and G's 3/10 anchor stability;
(iv) the identity of FCVM's failure set. Knife-edge (config, threshold)
pairs are named.

**Decision rule (fixed now):** the published integer rhetoric ("the ceiling
is 5/10"; "no configuration exceeds 5/10") survives only if invariants
(i)–(ii) hold under every ±20% single-threshold perturbation. Individual
integer scores are expected to move; if the comparative structure breaks
anywhere, the specific perturbation and the corrected statement are
reported, and the ceiling language is replaced by whatever ordering
actually survives.

**Deliverable:** `threshold_robustness` block in
`research/robustness.json`.

---

## Gates (registered now)

- **X36** (`tests/test_robustness.py`, deterministic, synthetic, < 60 s):
  (a) E9-block identity with `battery()` (in-process) and with stored JSON
  per-seed bits; (b) whitened-MI calibration on the analytic AR(1) world
  (closed-form sign-MI, linear channel removed); (c) orthogonal-channel
  preservation (nonlinear sign structure survives whitening); (d) the
  `fund_t3_scale` flag — flag-off byte-identity to the pinned X30a hashes,
  flag-on live/deterministic/finite with measurably heavier fundamental
  tails. X36 must pass before any R2 or R4 response variable is read.
- No existing gate is modified; the battery, the simulator's default path,
  and every published JSON row are byte-untouched. `kM` enters R5 through
  the existing `params` override — no simulator change.

## Deliverables

- `kronos/robustness.py` (estimators), `exp_robustness` in
  `run_research.py` → `research/robustness.json` (blocks: strength_depth,
  e9_attribution, ext32, t3_absorption, requilibration,
  threshold_robustness).
- FINDINGS section "KRONOS-DECATHLON — referee-driven robustness and
  attribution (DESIGN25)" reporting every outcome under the reporting
  standard above, including any dissolution of published claims.
- Results recorded in this file's amendment section after the runs, as in
  DESIGN18/20/22/24.

## Results (recorded after the runs; budgets held — 272 battery runs + 64
## non-battery sims, exactly as registered; gate X36 green first)

- **R1 — the depth attribution is DEAD.** At effective strength 0.25 on
  both arms (seeds 100–131), depth-5 leaks LESS than depth-1: medians
  0.017572 vs 0.019372, Wilcoxon p = 0.0028, depth-5 > depth-1 on only 6/32
  seeds. Realized-strength caveat (registered): the caps bind for the single
  strong layer but never for the five weak ones — realized strengths 0.2237
  (depth 1) vs 0.2500 (depth 5), a 10.5% relative gap whose direction
  STRENGTHENS the verdict (the depth-5 arm ran slightly stronger and still
  leaked less). The published K-axis was a strength axis
  (grid Spearman ρ(kA, bits) = 0.892, corr(AC1, bits) = −0.893). Depth-1
  arm reproduced the stored A2 K1 vector exactly (asserted).
- **R2 — the inversion is an artifact; the rise is induced reversal.**
  Control FCVM's leak is NOT linear: whitened bits 0.0197 ≈ raw 0.0184,
  significant 8/8 (φ̂ = +0.036). Every intervention CONVERTS the leak:
  whitened (nonlinear) bits fall monotonically 0.0197 → 0.0112 (K1) →
  0.0038 (K5) / 0.0036 (Q1.0), while the sign_t-alone component rises
  0.0101 → 0.0147 → 0.0220 / 0.0206 with AC1 driven to −0.25. The raw rises
  vanish under whitening — in fact reverse: whitened diffs vs control are
  NEGATIVE on 0/8 positive seeds, p = 0.0078, for K1, K5, Q0.5 AND Q1.0;
  the sign-component share of the raw rise exceeds 1 (2.21 K5, 1.84 Q1.0);
  conditional MI given sign_t falls in every arm (p = 0.0078). Per the
  decision rule: the "re-created in price space" reading is **WITHDRAWN**;
  the licensed claims are (i) the leak never closes — whitened bits stay
  significant 8/8 in every configuration, floor ≈ 0.0033 — and (ii) the
  interventions actually absorb MOST of the genuine nonlinear leak while
  manufacturing one-lag reversal that the E9 statistic scores higher.
- **R3 — the raw rises are real and well-powered, and R2 says what they
  are.** K5-frozen: 32-seed median 0.025761 vs control 0.019459, 28/32,
  Wilcoxon p < 1e-4. Q1.0: 0.023851, 26/32, p < 1e-4. Both rises STAND at
  32 seeds — the referees' power concern is answered — and by R2 they are
  measured E1-breakage (induced linear reversal), not sign information.
  Composed verdict per the registered rule: "grows" is replaced by
  "converts"; "does not close" stands.
- **R4 — wildness still dies; the claim scopes to flow-generated
  wildness.** Calibration selected the variance-matching scale (mult 1.0,
  median kurt 8.82 vs target 8.79; ladder non-monotone — larger t3 scales
  LOWER total kurtosis by drowning the spiral). FCVM-T3 control: 5/10,
  fails exactly FCVM's five events, kurt 7.93, bits 0.0201. FCVM-T3+Q1.0:
  1/10 (E6 only), kurt 3.06, bits 0.0229 — the t(3) tails do NOT survive
  absorption because the fundamentalist channel (kF = 0.15) spreads a
  V-jump over ~7 days: it is a structural tail filter. Registered branch 3
  fires: the joint-production claim is structural to FLOW-GENERATED
  wildness and is scoped to exactly that. The stronger separation the
  referees hypothesized (efficiency and wildness separately purchasable)
  remains UNTESTED by this design — a fundamental-channel t3 source cannot
  express one-day wildness at any registered scale; testing it would need a
  different injection point (e.g. heavy-tailed noise-trader flow), which is
  outside this registration.
- **R5 — the ceiling survives re-equilibration.** Arm a (K1 anticipator):
  grid {5,4,5,5,4,4}, tie-break keeps kM = 0.30 (the frozen value), eval
  5/10, FCVM's failure set. Arm b (Q1.0): grid {2,2,1,1,1,1}, winner
  kM = 0.10, eval 2/10 (E1, E6) — and its bits collapse to median 0.0016
  (per-seed 0.0007–0.0032, still E9-significant): with adapted liquidity,
  full absorption comes within a hair of closing the sign leak and the
  price is EVERYTHING ELSE — the cleanest joint-production demonstration in
  the program. Ceiling survives; claim scoped to the one parameter tested.
- **R6 — the integer rhetoric survives; knife edges named.** Baseline
  reproduced for all 15 configs + SPY. Under all 48 single-threshold
  perturbations (±10/20%): FCVM stays the maximum simulated score
  (ceiling invariant HOLDS in 48/48), FCVM's failure set never changes,
  G stays 3/10, SPY stays 10/10 at ±10% and drops to 9 only at
  e8_ratio −20%. Headline rows are frozen at ±10% (FCVM, FCVM+A, K5-tuned,
  Q-tuned, FV, FCV all [5,5]); knife edges at ±10% are confined to
  non-headline rows: Q0.5 (e1_lo +10%, e2_lo −10%), FCVMH (e1_lo/e2_lo
  −10%), K5-frozen (e5 −10%). Full ±20% bands in
  research/robustness.json.

**Composed verdict (the reporting standard applied):** the published
centerpiece — "deeper anticipation grows the sign leak; the market
re-creates the information in price space" — is DEAD, on the paper's own
archived data plus the registered extensions: the K-axis was a strength
axis (R1) and the bits-rise is induced one-lag reversal scored as sign
information by a statistic that conditions on sign_t (R2), robustly so at
32 seeds (R3). What SURVIVES is stronger than what was lost: bolt-on
rationality CONVERTS a genuine multi-day sign leak into microstructure
reversal — absorbing most of it, never closing it (whitened floor
≈ 0.0033 bits, significant 8/8 everywhere, down from control's 0.0197) —
and pays for the conversion with the wild facts, which are flow-generated
(R4) and cannot be rescued by re-equilibrating liquidity provision (R5);
the 5/10 ceiling and both calibration anchors are threshold-robust (R6).
If the surviving claim retitles the paper, the honest title is about
CONVERSION and JOINT PRODUCTION, not about a leak that grows.
