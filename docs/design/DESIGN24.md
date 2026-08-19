# KRONOS-DECATHLON ADDENDA — calibration audit and power addenda

*Pre-registered. This document registers five MEASUREMENT addenda to the
closed DESIGN8/18/20/22 line, motivated by the paper's review notes
(docs/paper/REVIEW-NOTES.md). None of them opens a new hypothesis about the
mechanism; each converts a narrative-sourced or single-point claim in the
paper into an executable, seed-fixed measurement — or establishes, with
arithmetic, that a claim cannot be certified with obtainable data. No
Sharpe-ledger entries: every addendum is measurement, not backtesting.
Everything below is declared BEFORE the corresponding run; screening data
(availability, real-range fractions) was inspected where noted, response
variables (scores, leverages, direction bits) were not.*

## A0 — DECA2 tuning-grid stat export (re-run, no new tuning)

The paper's §3 mechanism numbers (AC1 falling toward −0.35 as kA rises,
kurtosis eroding 8.8 → 4.6, direction bits up to 0.039 at kA = 1) trace to
the DESIGN18 tuning-grid narrative in FINDINGS, not to JSON fields — they are
the number-checker's declared skips. This addendum re-runs the SAME frozen
grid and exports per-setting statistics.

- **Protocol (identical to DESIGN18's one registered pass):** grid
  kA ∈ {0.25, 0.5, 1.0} × capA ∈ {0.01, 0.02, 0.05} × sA ∈ {0.001, 0.002}
  (18 settings), config FCVM+A, tuning seeds 900–903, T = 6000, majority
  vote. No selection is performed; the frozen parameters stay frozen.
- **Deliverable:** `tuning_grid_stats` in decathlon2.json — per setting, the
  score and the 4-seed median AC1(r), kurtosis, direction bits; plus per-kA
  pooled summaries.
- **Match criterion (the point of the addendum):** the exported numbers must
  reproduce the FINDINGS narrative at its cited precision. If any does not,
  the discrepancy is REPORTED as such — the paper is corrected to the
  executable numbers and the mismatch is recorded here; it is not papered
  over.

## A1 — multi-index calibration audit (the 10/10 anchor)

The battery's joint-10/10 anchor is one index (SPY). This addendum scores
the battery on a FIXED list of additional real indices — no swapping after
results, misses reported by name.

- **List (fixed now):** QQQ, DIA, IWM (US close panel, 2010–2026) and the
  three transfer-study local index ETFs — 1306.T (TOPIX), EXW1.DE (EURO
  STOXX 50), 2800.HK (Hang Seng tracker), 2010–2026 local close panels.
  Close-only battery, byte-identical code path to the SPY calibration run
  (`battery(px.pct_change().dropna())`, default seed).
- **Prediction:** every index scores ≥ 9/10, with any miss named and
  diagnosed; GBM stays 3/10 (unchanged, asserted from decathlon.json).
- **Honesty clause:** an index scoring below 9 is a finding about the
  battery's calibration breadth and goes in the paper as such.
- **Deliverable:** research/battery_audit.json (per-index events, scores,
  key statistics); appendix table + upgraded §2 calibration statement.
- **Result (recorded after the run; the prediction FAILED and is reported
  as such):** DIA 10/10, QQQ 8/10 (E7 E8), IWM 8/10 (E8 E10), 1306.T 6/10,
  EXW1.DE 7/10, 2800.HK 5/10 — foreign single indices miss E7/E8/E9
  systematically. Post-run hygiene probe (recorded honestly, after seeing
  scores): re-running each foreign index on its NATIVE trading calendar
  (raw cached closes, no union-calendar forward-fill) scores the same or
  LOWER (1306.T 4/10, EXW1.DE 7/10, 2800.HK 5/10), so the misses are not a
  calendar-padding artifact. Verdict: the battery's absolute 10/10 anchor
  extends to the large-cap US complex (DIA joins SPY at 10/10) but NOT
  across venues — the thresholds are US-calibrated, which the paper now
  states as a measured scope boundary instead of a single-anchor caveat.
- Also exported (calibration reference, closes a checker skip): the weekly
  clock AC8 of the gate suite's GJR-GARCH(1,1) world
  (`kronos/surge.simulate_gjr_world`, seeds 100–107, T = 6000) — the
  executable version of the "exponential memory fails E4" calibration note.
  The DESIGN8-era note recorded ≈ 0.06 from a calibration-phase run whose
  exact parameters were not preserved; the paper will cite whatever this
  fixed-seed measurement produces, with the pass/fail claim (below the 0.12
  bar) as the substantive assertion.

## A2 — E9 one-layer step: K0 vs K1 at 32 seeds

DECA3's K0-vs-K1 paired comparison (direction bits 0.0184 → 0.0200 in
medians) splits 4–4 on the 8 evaluation seeds — a point estimate inside
noise, disclosed as such in the paper. This addendum extends the paired
comparison to a FIXED larger seed set, once.

- **Budget (fixed now):** seeds 100–131 (32 seeds — the original 8 plus 24
  new), T = 6000, configs K = 0 (FCVM) and K = 1 (the frozen DECA2 layer),
  battery seed = seed index (0–31), one run, no further extension regardless
  of outcome. The first 8 seeds must reproduce decathlon3.json's stored
  per-seed bits exactly (byte-identity of the re-run).
- **Analysis (fixed now):** paired per-seed direction bits; two-sided
  Wilcoxon signed-rank (primary, α = 0.05) and two-sided sign test
  (secondary/descriptive) on K1 − K0.
- **Decision rule:** Wilcoxon p < 0.05 → the paper states the one-layer step
  separates at 32 seeds (with p); otherwise the paper states the step is
  statistically flat at 32 seeds and only the depth trend (K = 5) is
  licensed. Either way the per-seed scatter figure is updated to 32 seeds.
- **Deliverable:** `k01_extension` in decathlon3.json.

## A3 — battery-score standard errors (seed-level bootstrap)

Battery scores are sums of 10 binary majority-vote events over 8 seeds and
carry no formal SE in the paper. This addendum computes one, per config, by
resampling the only replicated unit — the evaluation seed.

- **Method (fixed now):** for each published configuration, the 8 × 10
  per-seed event matrix is recomputed (deterministic; must reproduce the
  published majority score exactly, asserted loudly), then seeds are
  resampled with replacement 2000 times (numpy default_rng seed 0), the
  majority-vote score recomputed per resample, and the SE is the SD of the
  2000 resampled scores.
- **Scope:** all configs in decathlon.json (G, F, FC, FV, FCV, FCVM, FCVMH)
  and every row of the three experiment tables (FCVM+A, FV+A, F+A; K5
  frozen, K5 tuned; Q1.0, Q0.5, Q0.05 tuned). Shared configs (FCVM = K0;
  K1 = FCVM+A) are computed once and asserted identical.
- **Deliverable:** research/score_se.json; ± values beside the scores in the
  paper's tables and a methods sentence replacing "no formal SE".

## A4 — the FX–crypto edge: widened universe + certification arithmetic

DESIGN17's one failed criterion is FX–crypto separation: z = 1.44 < 1.645,
crypto's sampling SD (0.0158) dominating the denominator. This addendum
(a) states the certification arithmetic explicitly, and (b) widens the
crypto universe with every obtainable major, pre-declared, to measure how
far widening actually moves the z.

**Certification arithmetic (from the stored estimates, before any new
run):** z = (ℓ_c − ℓ_f)/√(s_f² + s_c²) with ℓ_c = 0.0312, ℓ_f = 0.0049,
s_f = 0.0086, s_c = 0.0158. Holding point estimates, z ≥ 2 requires
√(s_f² + s_c²) ≤ 0.01315, i.e. s_c ≤ 0.0099 — a 1.59× reduction. The SDs
are time-block bootstrap SDs, scaling ∼1/√T: reaching it through history
alone needs ≈ 2.5 × the current 8.6 years ≈ 22 years of crypto history,
which does not exist (Yahoo daily majors: BTC from 2014, nearly all others
from 2017-11-09). Cross-sectional widening attacks s_c only through
averaging highly correlated coins, so the expectation is a partial
reduction; this addendum measures it.

- **Candidate list (fixed before any leverage was computed):** TRX-USD,
  XMR-USD, EOS-USD, NEO-USD, DASH-USD, ZEC-USD, BAT-USD, ATOM-USD — the
  liquid 2017-era majors beyond DESIGN14's 10.
- **Screen (availability + range only, inspected before this registration;
  no response variable seen):** all 8 pass the DESIGN17 real-range bar
  (worst 99.81%); 7 have full history from the joint panel start
  (2017-11-09); ATOM-USD lists 2019-03-14.
- **Exclusion rules (fixed now, the only ones):** (i) real intraday range on
  > 95% of days (the DESIGN17 gate); (ii) first data date ≤ the original
  panel start 2017-11-09 — because the panel intersects dates, a late
  lister would TRUNCATE T for all coins, and the arithmetic above says T is
  the binding constraint; a widening that shortens T is self-defeating.
  Applying (ii): ATOM-USD is excluded. **Widened universe = the original 10
  + {TRX, XMR, EOS, NEO, DASH, ZEC, BAT} = 17 coins**, span identical to
  DESIGN14 (request window 2017-01-01 → 2026-06-05).
- **Protocol:** the DESIGN14 battery, byte-identical machinery
  (`kronos.transfer.battery` on the widened close/GK panels, recovery-curve
  debiasing, n_boot = 40), leverage contrast against the STORED equity and
  FX vertices (fx.json / transfer.json are not re-run; the FX vertex is
  frozen).
- **Prediction:** the widened ℓ_c stays positive with the retail end most
  inverted; s_c falls but by less than 1.59×; z(crypto vs FX) rises yet
  stays < 2.
- **Decision rule (fixed now):** if z ≥ 2, the paper reports the FX–crypto
  edge as certified on the widened pre-declared universe. If z < 2, the
  paper's §7 gains a short argued passage: the edge is inherently
  underpowered at current history — bounded by T, not by prose, with the
  arithmetic above and the measured widened z as evidence — and the
  triangle's epistemic status (consistency, not proof) is stated in the
  body rather than listed as a weakness.
- **Deliverable:** research/crypto_wide.json. The published 10-coin vertex
  (crypto.json) is NOT replaced; the widened run is reported beside it as a
  registered robustness/power addendum.
- **Result (recorded after the run):** 17 coins × 3130 days, real-range
  audit min 99.81%, panel start preserved at 2017-11-09. Widened leverage
  +0.0260 (sd 0.0161), 14/17 coins positive, z vs equities 3.71 (edge still
  certified), z vs FX 1.44 → **1.16** — the widened point estimate moved
  toward zero while the SD did not shrink at all (0.0158 → 0.0161),
  confirming the prediction's mechanism: the block-bootstrap SD is bound by
  T, not by the cross-section. Certification is arithmetically unreachable
  with obtainable data (≈ 22 years of history needed vs 8.6 obtainable);
  per the decision rule, the paper argues the T-bound in §7's body.
