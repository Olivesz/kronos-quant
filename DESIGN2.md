# KRONOS-X — Frontier Research Design Brainstorm

*Phase 2. KRONOS v1 is a working platform. KRONOS-X turns it into a research
lab: every addition below is a **falsifiable question**, not a feature. The
thrill is that we genuinely don't know the answers until the experiments run.*

---

## 0. Mission: six research questions

Each pillar exists to answer a question with a number attached. This is what
separates "frontier research" from "more indicators":

| # | Question | Module | How we'll know |
|---|----------|--------|----------------|
| Q1 | Does the market have **more than 3 regimes**, and do HMMs even describe them well? | Statistical Jump Models vs HMM vs duration-HMM | Walk-forward out-of-sample predictive log-likelihood + economic value |
| Q2 | Does **explicit regime duration** (semi-Markov) beat the HMM's memoryless geometric durations? | Expanded-state duration HMM | Same horse-race protocol |
| Q3 | Is volatility on our universe **rough** (Hurst H ≈ 0.1, Gatheral et al.)? And does HAR-RV/GARCH beat our EWMA risk inputs? | Vol lab | H estimate with CI; QLIKE + Diebold-Mariano tests |
| Q4 | Can an **online learner with regret guarantees** beat our hand-designed regime gates at blending sleeves? | Exponentiated-gradient meta-allocator | Net Sharpe + regret curve vs best-sleeve-in-hindsight |
| Q5 | Does **random-matrix denoising** of the correlation matrix beat Ledoit-Wolf? Does a **min-CVaR LP** beat HRP? | Covariance lab + Rockafellar-Uryasev optimizer | Realized vol / realized CVaR of walk-forward min-risk portfolios |
| Q6 | Is our final strategy **statistically real**, after accounting for every configuration we ever tried? | Overfitting forensics: Deflated Sharpe, PBO/CSCV, stationary bootstrap | DSR > 0.95? PBO < 20%? CI excludes 0? |

A seventh, woven through: replace the failed Kalman-pairs sleeve with the
**Avellaneda-Lee eigenportfolio stat-arb** — the canonical answer to "pairs
trading died, what does modern stat-arb actually look like?"

---

## 1. Pillar A — Regime science beyond the HMM

### 1.1 Statistical Jump Models (SJM) — the modern challenger

The hot alternative in the recent literature (Bemporad/Boyd's *Fitting Jump
Models*, 2018; Nystrup–Lindström–Madsen applications to regime investing).
No likelihood, no Gaussian assumption — fit states by penalized clustering:

```
minimize  Σ_t ||x_t − μ_{s_t}||²  +  λ · Σ_t 1[s_t ≠ s_{t−1}]
```

Alternating optimization: given state sequence → means are cluster averages;
given means → optimal sequence by dynamic programming over T×K (Viterbi with
switch cost λ). Converges in a handful of iterations, deterministic with
k-means++-style init, **O(T·K²) per pass** — even cheaper than EM.

Why it's exciting: robust to fat tails (no Gaussian emission), λ directly
controls regime persistence (vs our bolted-on hysteresis), and recent papers
report it beats HMMs out-of-sample. **We get to check that claim ourselves.**

Implementation notes:
- Features: same (return, log-RV) pair, standardized on the training window;
  later add downside-deviation & correlation-level features (cheap wins).
- λ selection is the crux — choose by **walk-forward OOS criterion** (next
  section), never by eyeballing the chart. Grid λ ∈ {2^k}.
- Online/causal inference: re-run DP on the trailing window each day but take
  only the *terminal* state (the filtered analog). DP is O(T·K²) ≈ microseconds.
- Probabilistic outputs for fair comparison: soft-assignment via distances
  (softmax with temperature fit on train) so it can produce a predictive
  density — needed for the horse race.

### 1.2 Duration HMM (semi-Markov) via the expanded-state trick

The HMM's hidden flaw: state durations are geometric (memoryless) —
P(stay k days) decays exponentially, while real bear markets have *humped*
duration distributions. Full HSMM forward-backward is O(T·K·D_max) and a lot
of new code. The elegant shortcut: **expand each regime into r tied sub-states
in a left-to-right chain** (1→2→…→r→exit). Total duration is then
negative-binomial(r, p) — humped, like reality. Emissions tied across
sub-states ⇒ we reuse the v1 EM verbatim with a structured transition mask
and K_eff = 3r states (r=3 ⇒ 9 states; with our matmul forward pass this is
still fast). Only new code: the transition-matrix mask and tied M-step for
emissions (sum responsibilities across sub-states).

This is the kind of trick that makes research fun: 30 lines buys a semi-Markov
model.

### 1.3 How many regimes? (model selection done honestly)

Sweep K = 2..6 for both HMM and SJM. Judge by:
- **BIC/ICL** in-sample (fast screen), and decisively:
- **Walk-forward 1-day-ahead predictive log-likelihood** of *returns* (not
  labels): each model emits p(r_{t+1} | data ≤ t) = Σ_k P(s_{t+1}=k|·)·N(μ_k,σ_k).
  This is the only label-free, model-agnostic, causally-fair metric — it
  sidesteps label-switching entirely.
- **Economic value**: plug each regime engine into the v1 pipeline (regime →
  strategy gates) and compare net Sharpe. Statistical winner ≠ economic
  winner; finding a divergence would itself be interesting.

### 1.4 The horse-race protocol (pre-registered, to keep us honest)

- Common walk-forward grid: refit every 21d, expanding window, min 750 obs —
  identical to v1.
- Metrics: (a) OOS predictive log-score, (b) regime-persistence stats,
  (c) crash detection latency (days to flag Mar-2020, Aug-2015, Feb-2018,
  2022), (d) net Sharpe when driving the platform.
- Decision rule written **before** running: the production regime engine for
  KRONOS-X is the winner on (a) unless (d) contradicts by > 0.15 Sharpe.

### 1.5 Stretch: covariate-driven transitions & Bayesian nonparametrics

- Time-varying transition probs: logistic link from (credit spread proxy
  HYG/LQD ratio, GLD/SPY, term proxy TLT return) into the transition matrix.
  Honest caveat: many parameters, real overfitting risk — only attempt with
  the Q6 forensics armed.
- Sticky HDP-HMM (Fox et al.) with weak-limit Gibbs to *infer* K nonparametrically
  — heaviest item in this doc; keep as stretch if the rest lands.

---

## 2. Pillar B — Alpha & volatility laboratory

### 2.1 Avellaneda–Lee eigenportfolio stat-arb (pairs trading, grown up)

v1's honest finding: Kalman pairs on liquid ETFs ≈ small loser. The canonical
modern fix (Avellaneda & Lee 2010, *Statistical Arbitrage in the US Equities
Market*):

1. Trailing 252d standardized returns → PCA on the correlation matrix.
2. Keep the top *m* eigenportfolios as factors — **m chosen by the
   Marchenko-Pastur edge** (Pillar C gives us this for free; the synergy is
   the point).
3. Residual of each stock vs factor basket → cumulative residual X_t →
   fit OU by AR(1): X_{t+1} = a + bX_t + ζ.
   κ = −252·ln b (mean-reversion speed), m_eq = a/(1−b), σ_eq = √(Var ζ/(1−b²)).
4. **s-score** = (X_t − m_eq)/σ_eq. Enter short s > +1.25, long s < −1.25,
   exit at ±0.5, *only for names with κ high enough that the half-life < 30d*.
5. Dollar-neutral overlay book (long stock / short factor basket), replacing
   the pairs sleeve, same 10% gross budget, same cost model.

Guardrails (learned from the literature and from v1's pairs autopsy):
- Skip names with b ≥ 0.997 (no mean reversion) or κ half-life > 30d.
- Sign-fix eigenvectors (largest-|loading| component forced positive);
  rotation across windows is irrelevant because s-scores are window-local.
- Entry/exit bands wide relative to costs; no-trade band on book updates.
- Pre-registered expectation: the 2010 paper's returns decayed post-2008;
  if our walk-forward shows decay too, **that replication of alpha decay is
  itself a publishable-grade finding** — and the honest result stands.

### 2.2 Volatility lab: HAR-RV, GJR-GARCH, and the EWMA incumbent

The risk engine currently runs on EWMA vol. Upgrade the *inputs* and measure
whether it matters:

- **Better realized-vol estimator first**: we have OHLC from yfinance — use
  **Garman-Klass** (or Yang-Zhang) daily variance instead of close-to-close
  squared returns. ~7× efficiency gain, pure arithmetic, improves *every*
  downstream vol estimate including the regime features. Easiest big win in
  this entire document.
- **HAR-RV** (Corsi): log RV_{t+1} on (log RV_d, log RV_w(5d), log RV_m(22d)).
  Three-coefficient OLS, absurdly strong benchmark in the literature.
- **GJR-GARCH(1,1)-t** fit by our own MLE: parameter transforms for
  positivity/stationarity, variance targeting for ω, multi-start L-BFGS.
  The leverage term (γ·r²·1[r<0]) is the part EWMA can't see.
- **Evaluation**: QLIKE loss (the robust one for vol), **Diebold–Mariano**
  tests with Newey-West HAC errors, 1d/5d/21d horizons, walk-forward.
  Winner feeds the risk engine's vol-target throttle; measure end-to-end
  Sharpe/maxDD delta.

### 2.3 Rough volatility: estimate the Hurst exponent ourselves

Gatheral–Jaisson–Rosenbaum's *Volatility is Rough*: log-vol increments scale
as E[|log σ_{t+Δ} − log σ_t|^q] ∝ Δ^{qH} with H ≈ 0.1 (much rougher than
Brownian H=0.5). With GK realized vol we can run the m(q,Δ) regressions on
our 16 years across Δ = 1..50, q ∈ {0.5, 1, 1.5, 2, 3}:

- Check linearity of ζ_q in q (monofractal) and read H from the slope.
- Stationary-bootstrap CI on H.
- Known pitfall, stated upfront: measurement noise in daily RV proxies biases
  Ĥ — report both raw and a noise-aware version (subsample/average estimator),
  and frame the finding accordingly.
- Dashboard payoff: the log-log scaling fan — one of the prettiest plots in
  empirical finance — plus "H = 0.xx on our universe" as a headline stat.
  If H comes out rough, optionally feed log-RV forecasts from a fractional
  kernel as an extra HAR feature (rough-HAR hybrid).

### 2.4 Online ensemble vs hand-made regime gates (Q4, the philosophical one)

v1 hard-codes regime → sleeve weights. The learning-theory alternative needs
no regime engine at all: **exponentiated gradient / Hedge** over the four
sleeves:

```
w_{k,t+1} ∝ w_{k,t} · exp(η · r_{k,t} / scale)     (η from regret theory)
```

- Provable regret bound vs the best sleeve in hindsight: O(√(T ln K)).
- Variants: plain Hedge, EG with fixed share (handles regime shifts!), and a
  regime-*conditioned* Hedge (separate expert weights per detected regime —
  the hybrid).
- Verdict metric: net Sharpe + cumulative-regret plot + turnover. If the
  fixed-share learner matches the hand-tuned gates, the gates aren't adding
  information; if regime-conditioned Hedge wins, regimes + learning beat
  either alone. **Any outcome is informative.** Nearly free to compute on
  stored sleeve returns.

---

## 3. Pillar C — Portfolio engines & overfitting forensics

### 3.1 Random Matrix Theory covariance denoising (vs Ledoit-Wolf)

Marchenko-Pastur: for pure noise, correlation eigenvalues live in
[(1−√q)², (1+√q)²], q = N/T. Recipe (López de Prado's): eigendecompose,
fit the MP bulk, **replace below-edge eigenvalues with their average**
(trace-preserving), rebuild. Optionally *detone* (remove market mode) for
clustering inputs.

The experiment: walk-forward **minimum-variance portfolios** (the purest
covariance test — no expected returns to muddy it) under (a) sample, (b) LW
shrinkage (v1), (c) RMT-denoised, (d) LW+RMT. Score by realized portfolio
vol and turnover. Also: dashboard gets the eigenvalue spectrum with the MP
density overlaid and the "number of true factors" = # eigenvalues above the
edge — which doubles as the *m* for Avellaneda-Lee (2.1). One experiment,
two consumers.

### 3.2 Min-CVaR portfolio via the Rockafellar–Uryasev LP

CVaR minimization is an LP — and scipy ships HiGHS:

```
min_{w,α,u}  α + 1/((1−β)S) Σ_s u_s
s.t.  u_s ≥ −w·r_s − α,  u ≥ 0,  Σw = 1,  0 ≤ w ≤ cap
```

S=252 scenarios × N=48 assets ⇒ ~300 variables: milliseconds. Variants:
historical scenarios, EWMA-weighted scenarios, regime-conditional scenarios
(use only days whose regime matches the current filtered regime — the
KRONOS twist that ties Pillars A and C together).

Bake-off vs HRP and BL-tilted HRP: realized CVaR (did it deliver what it
optimizes?), Sharpe, maxDD, turnover (LP solutions can be jumpy — expect to
need a turnover penalty: it stays linear, so still an LP).

### 3.3 Overfitting forensics (the rigor engine — Q6)

This is the section that makes everything else trustworthy:

- **Deflated Sharpe Ratio** (Bailey & López de Prado): adjusts the observed
  Sharpe for skew, kurtosis, track length, and — critically — **N, the number
  of strategy configurations we tried**. We will *actually count* our trials
  (the param sweeps from v1 and v2 are in the transcripts/configs; keep a
  ledger file `research/trials.json` from now on). DSR = P(true SR > 0).
- **PBO via CSCV** (combinatorially symmetric cross-validation): build a
  family of ~100–1000 strategy variants *cheaply* — because sleeve daily
  returns are precomputed, a "variant" (blend weights × risk params ×
  rebalance) is pure algebra on stored series. Split the sample into S=16
  blocks, all C(16,8)=12,870 IS/OOS pairings (vectorizable), PBO = fraction
  of splits where the IS winner ranks below-median OOS.
- **Stationary bootstrap** (Politis–Romano, expected block ≈ 63d) → CI on
  Sharpe and maxDD; fan chart on the equity curve.
- **White's Reality Check / Hansen SPA** (stretch): does the best variant
  beat SPY after accounting for the whole search?

Dashboard verdict panel: DSR gauge, PBO histogram, bootstrap CI — KRONOS-X
grading its own homework, publicly.

---

## 4. Dashboard v2 — two-tab single file

Keep one self-contained HTML; add a tab bar: **OVERVIEW** (v1 panels) and
**RESEARCH**. New research panels:

1. Regime horse-race: OOS log-score table + crash-latency table + per-model
   regime ribbons stacked for visual comparison (HMM vs SJM vs duration-HMM).
2. "How many regimes?" — log-score vs K curve.
3. Vol lab: QLIKE table with DM p-values; forecast-vs-realized scatter.
4. Rough-vol panel: the m(q,Δ) log-log scaling fan + Ĥ with CI.
5. Eigenvalue spectrum + MP overlay; min-var bake-off table.
6. Stat-arb panel: s-score distribution, live book, sleeve equity (replaces
   the pairs panel; keep the Kalman post-mortem as a footnote — honest
   archaeology).
7. Ensemble panel: expert-weight river chart + regret curve vs best sleeve.
8. Forensics: DSR gauge, PBO histogram, bootstrapped equity fan chart.
9. Final: KRONOS-X vs KRONOS v1 vs SPY equity curves — did the science move
   the needle?

Engine reuse: LineChart/StackedArea/heatmaps cover almost everything; new
primitives needed: scatter (trivial), fan/band fill (small extension to
LineChart), gauge (canvas arc).

---

## 5. Pre-empted roadblocks (the v1 trick, applied again)

| Roadblock | Pre-emption |
|---|---|
| Label switching wrecks model comparison | Compare models on **predictive density of returns**, never on labels; canonicalize only for display |
| SJM λ chosen by eyeball = self-deception | λ on the same walk-forward predictive criterion as the horse race; grid pre-registered in config |
| Expanded-state EM degeneracy (sub-states drift apart) | Emissions *hard-tied* in the M-step (sum γ across sub-states before updating μ,Σ); left-to-right mask frozen |
| GARCH MLE blows up | Parameter transforms (sigmoid for persistence, exp for scale), variance targeting for ω, 5 multistarts, fall back to HAR if not converged — and log it |
| Daily RV proxy too noisy for Hurst | Garman-Klass OHLC estimator (do this first); report noise-bias caveat; bootstrap CI; sensitivity over Δ_max |
| PCA factor instability across windows | Sign-fix by max-|loading|; s-scores are window-local; m from MP edge each window, capped 1..15 |
| OU fits on non-stationary residuals | Skip b ≥ 0.997; require half-life < 30d; both thresholds in config, counted in the trials ledger |
| LP portfolio turnover explosion | Linear turnover penalty inside the LP; no-trade band outside it |
| CSCV variants secretly share lookahead | Variants are functions of *causally generated* sleeve returns only; blend/risk algebra can't peek |
| Trial-count (N) for DSR is fudgeable | `research/trials.json` ledger appended by every sweep script; DSR cites it |
| Runtime creep (it's all walk-forward) | Budget: regime race ~2–3 min (warm-start EM, DP is trivial), GARCH ~1 min (market series only), CSCV vectorized ~1 min, bootstrap seconds. Full `run_kronos.py --research` target: **< 10 min** |
| pandas 3 / numpy 2 quirks | Same discipline as v1 (`.ffill()`, `'ME'`, no chained assignment) |

---

## 6. Build order & verification gates

Dependency-aware sequence, each with a gate before moving on:

1. **OHLC + Garman-Klass vol** (feeds everything) — gate: GK vol correlates
   ≈0.9 with close-to-close on overlapping windows but ~half the sampling noise
   (variance-of-variance check on synthetic GBM where truth is known).
2. **SJM** — gate: on synthetic HMM data, ≥ HMM's state accuracy at the
   OOS-chosen λ; runtime < 1ms/fit.
3. **Duration-HMM (expanded states)** — gate: on synthetic *semi-Markov* data
   with negative-binomial durations, beats plain HMM's predictive log-score;
   on geometric-duration data, ties (no false win).
4. **Horse race** (Q1, Q2 answered) — gate: protocol of §1.4 executed, table
   written to research payload.
5. **Vol lab + DM tests** (Q3a) — gate: on synthetic GARCH data, GARCH-MLE
   recovers parameters; DM machinery validates on known-different forecasters.
6. **Hurst/rough vol** (Q3b) — gate: on synthetic fBm log-vol with known H
   (circulant-embedding simulation), estimator recovers H ± 0.05.
7. **RMT denoising + min-var bake-off** (Q5a) — gate: on synthetic
   factor-model data with known #factors, MP edge finds it.
8. **Avellaneda-Lee sleeve** — gate: on synthetic data with planted
   mean-reverting residuals, s-scores extract them profitably net of costs;
   then real-data walk-forward (whatever it shows).
9. **Min-CVaR LP** (Q5b) — gate: optimizer's in-sample CVaR ≤ HRP's by
   construction; OOS comparison recorded.
10. **Online ensemble** (Q4) — gate: regret curve sublinear; fixed-share
    tracks the best sleeve through the 2022 regime change.
11. **Forensics** (Q6) — gate: DSR/PBO validated on a known-overfit toy
    (random strategies: PBO ≈ 50%, DSR ≈ uninformative) before pointing them
    at ourselves.
12. **Dashboard v2 tabs + research panels** — gate: pixel-paint check + zero
    console errors, as v1.
13. **Final synthesis run**: `run_kronos.py --research`, answers to Q1–Q6
    written into the dashboard, README updated with the findings table.

## 7. Stretch shelf (only if the core lands)
- Sticky HDP-HMM with weak-limit Gibbs (infer K nonparametrically).
- Covariate-driven (logistic) transition probabilities.
- Lead-lag network alpha (lagged cross-correlation graph, trade followers).
- Almgren-Chriss optimal execution layer for the cost model.
- Regime-conditional block-bootstrap market generator for stress testing.

---

*The standard for "done": every research question gets a quantitative answer
on the dashboard, with the negative results displayed as proudly as the
positive ones. That's what makes it research instead of marketing.*
