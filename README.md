# KRONOS / KRONOS-X — Regime-Aware Quant Alpha Platform & Research Lab

An institutional-grade quant platform (**KRONOS v1**) plus a frontier research
program on top of it (**KRONOS-X**) — built with essentially no third-party
ML/quant dependencies. Every model is hand-implemented and verified against
synthetic ground truth before touching real data: Baum-Welch EM, semi-Markov
HMMs, statistical jump models, Kalman filters, GJR-GARCH MLE, HAR-RV,
fractional-Gaussian-noise simulation, Marchenko-Pastur denoising,
Rockafellar-Uryasev LPs, Hedge/exponentiated-gradient learners, deflated
Sharpe ratios, CSCV, stationary bootstrap, HRP, Black-Litterman — and the
canvas charting engine of the dashboard.

## Quick start

```bash
.venv/bin/python run_kronos.py              # v1 pipeline -> output/dashboard.html
.venv/bin/python run_research.py all        # KRONOS-X: all 9 experiments (cached)
.venv/bin/python run_kronos.py --research   # dashboard with the RESEARCH tab
open output/dashboard.html
.venv/bin/python tests/run_all.py           # all 14 verification gates (~30s)
```

Everything is isolated in the project-local `.venv` (Python 3.12). Data:
~48 liquid US equities/ETFs, 2010–2026, Yahoo OHLC with local caching and a
synthetic regime-switching fallback.

## The KRONOS-X findings (six pre-registered research questions)

| Q | Question | Answer |
|---|----------|--------|
| Q1 | Does the market have more than 3 regimes? | **Mixed.** HMM predictive log-score rises through K=5, but the jump model peaks at K=3 — extra HMM states buy distributional flexibility (fat tails), not new economic regimes. |
| Q2 | Do explicit (semi-Markov) durations beat the HMM? | **No.** Duration-HMM ties plain HMM out of sample (3.1669 vs 3.1689 nats/day) — an honest negative; the test provably had power on synthetic semi-Markov worlds. |
| Q3a | Can we beat EWMA vol forecasts? | **Yes — HAR-RV**, decisively: QLIKE 0.417 vs 0.511, Diebold-Mariano −7.1 (p<0.001). GJR-GARCH ties HAR. |
| Q3b | Is volatility rough? | **Yes: H ≈ 0.10** (CI [0.08, 0.13]) on SPY Garman-Klass log-vol — replicating Gatheral-Jaisson-Rosenbaum on our own 16 years; stable across subwindows; cross-sectional median 0.07. |
| Q4 | Does online learning beat hand-made regime gates? | **All tie (Sharpe ≈ 0.99).** The sleeves are too correlated through the shared HRP backbone for blend weights to matter — the backbone does the work. |
| Q5a | Does RMT denoising beat Ledoit-Wolf? | **No** on this universe (LW 5.84% vs RMT 6.04% realized min-var vol): with N=48, T=252 the noise is mild; RMT is built for far wider universes. |
| Q5b | Does a min-CVaR LP beat HRP? | **Marginally yes**: it delivers what it optimizes (realized CVaR 1.24% vs 1.34%) at comparable Sharpe (1.07 vs 1.03). |
| Q6 | Is the strategy statistically real? | **Returns yes, selection no.** Bootstrap Sharpe CI [0.47, 1.45] excludes zero, but DSR = 0.60 after N=179 trials and PBO = 0.45: the edge over sibling configurations is not certifiable — the test most backtests never run, run on ourselves. |
| — | Does classic stat-arb still work? | **No — alpha decayed.** Avellaneda-Lee eigenportfolio stat-arb: −1.3%/yr (SR −0.24) despite the implementation extracting planted OU residuals at Sharpe 2.4 in its gate. Replicates the documented post-2008 decay. |

**Synthesis:** the regime-gated HRP core (Sharpe 0.95, maxDD −14%) beats both
stat-arb overlays; vs SPY it matches Sharpe at less than half the drawdown.
The science's biggest wins: HAR-RV for vol, the rough-vol replication, and
the forensic honesty about what is and isn't certifiable.

## KRONOS-X² — the mechanism studies (DESIGN3.md, pre-registered)

The headline result of the project. Q1's "mixed" answer is resolved by a
control experiment: a **Student-t HMM** (own ECM: latent gamma scale weights
inside forward-backward, per-state ν via the digamma equation) that models
fat tails *within* states.

| Study | Result |
|---|---|
| **K-hallucination Monte Carlo** (true K=3 worlds) | On the fat-tailed world, Gaussian-HMM model selection chooses K>3 in **88%** of seeds (6/8 pick K=5); the t-HMM overfits only 38% (vs a 50% base rate on Gaussian worlds for both). **Gaussian HMMs hallucinate regimes from fat tails.** |
| **Real data (walk-forward, eval 2019+)** | The Gaussian K-curve rises (3.169→3.189, K=3→5) exactly like the fat-world MC; the **t-HMM curve is flat at K=3** (T5 vs T3: AG +0.04, p=0.97). A two-state t-HMM (3.1895) matches the five-state Gaussian (3.1888). **Verdict: ~3 regimes + fat tails, not 5 regimes.** |
| **Market tail structure** (t-HMM K=3, per-state ν) | Bull ν≈17 (mildly fat), **Volatile ν≈3.7 (extremely heavy)**, Bear ν≈300 (≈Gaussian). The volatile regime carries the tail surprises; crash regimes are "predictably bad". |
| **Formal inference** | Amisano-Giacomini: t-HMM-3 beats SJM-3 (p=0.011), beats Gaussian-3 and DurHMM marginally (p≈0.06); Hansen-Lunde-Nason **Model Confidence Set** (α=10%) eliminates SJM-3, best member T5 (statistically tied with T3). |
| **Does roughness forecast?** (RFSV kernel forecaster) | RFSV crushes EWMA (AG +5.5), ties GARCH, **survives the vol-model MCS** — but HAR wins the pairwise test (AG −2.3, p=0.022). Roughness forecasts competitively at daily horizons; it doesn't dethrone HAR. The errors-in-variables lesson (the fBm kernel needs noise filtering on daily proxies) is part of the finding. |

New machinery, all gated on synthetic ground truth first: Student-t HMM ECM
(Gate X11: ν recovery ±0.6, ties Gaussian on Gaussian worlds), Amisano-
Giacomini tests (Gate X12: 4.5% empirical size), Model Confidence Set
(88% coverage / 88% power), RFSV fractional-kernel forecaster (Gate X13:
beats HAR on its home world, degrades gracefully off-model).

## KRONOS-LAWS — invariance hunting (DESIGN4.md, pre-registered screens)

Strategy shift: hunt laws, not alphas. Three killable screens, two survived:

| Screen | Verdict |
|---|---|
| **L1 — One-Clock Hypothesis** (returns are conditionally Gaussian given the realized-vol path) | **Survived spectacularly.** Median kurtosis across 48 assets: 12.6 → **2.60**; fitted ν: 3.3 → ~200; cross-asset KS distance only **1.10× the sampling floor** — after deformation, equities, bonds, gold, and credit share one distribution. |
| **P1b — the causal closure of the X² paper** | On deformed returns the Gaussian K-rise(3→5) goes **+0.0199 → −0.0042** and all t-HMM ν → Gaussian (56/300/300). The hallucinated regimes die with the tails: mechanism → cause → cure, one arc. |
| **L2 — parameter-free kurtosis law** (kurt = 3e^{4·Var(log σ)} from persistent SV) | **Killed, informatively**: log-corr 0.27, median excess +7.1 — most unconditional kurtosis is day-specific (jumps/gaps), not slow SV. Consistent with L1 because the daily *range* sees the jumps that slow SV misses. |
| **L3 — multifractal universality** | **Survived the pre-registered bar**: intermittency λ² median 0.079, IQR [0.063, 0.091] across all assets (rel. spread 0.36 < 0.5) — with the known tail-confound caveat noted. |

The gate for all of this (X14) first proved the machinery on simulated SV
worlds: parameter-free kurtosis recovery to +0.5%, deformation returning a
fat SV world to kurtosis 3.1, and the noise-injection trap (standardizing by
an unsmoothed proxy *adds* tails) identified and encoded before real data.

## KRONOS-CLOCK — is systemic risk just correlated clocks? (DESIGN5.md)

The One-Clock result raised the systemic question: raw returns crash
*together* far more than any Gaussian copula allows. Contagion — or just
correlated volatility clocks? Method: all 1,128 pairs tested against
finite-sample Gaussian-copula nulls (rank-calibrated — Pearson correlation
is contaminated by the very jumps under test), under two deformations that
bracket the answer. Gate X15 proved the test can both exonerate (correlated
clocks, no jumps → 0% false convictions) and convict (joint-jump world →
87% detection).

| Version | pairs above null 95% (q=5%) | median excess λ |
|---|---|---|
| raw returns | **93%** (equities 97%) | +0.109 |
| ÷ same-day clock | **15%** | +0.012 |
| ÷ lagged clock | **71%** | +0.058 |

**Verdict: systemic tail risk IS correlated clocks — but the clocks
themselves crash together unpredictably.** Conditional on the realized vol
paths, cross-asset dependence is ~Gaussian copula (clocks explain ~89% of
the joint-tail excess). Relative to yesterday's information, 71% of pairs
still exceed the null: joint crashes are common *volatility surges* no
single-asset model can forecast — vol-of-vol risk, not residual contagion.

Two more answers along the way: **the "universal multifractality" (L3) was
entirely the clock** — λ² goes 0.079 → −0.006 after deformation (deformed
returns are monofractal; the universality was the clock's universality).
And the **market clock alone** removes 79% of non-equity kurtosis but
*worsens* single-stock tails (−13%): asset classes share one clock; single
names need their own.

## KRONOS-SURGE — the structure of the surges themselves (DESIGN6.md)

CLOCK's irreducible object — the common, unpredictable clock surge —
interrogated directly (gate X16 first proved each estimator's size & power,
catching en route that *trailing* smoothing mechanically manufactures a
false arrow of time; time-symmetry tests need centered windows):

| Screen | Verdict |
|---|---|
| **S1 — does the clock have a clock?** | Yes, it clusters (AC₁\|u\| = +0.15, kurt 3.9) — **but the one-clock law does NOT recurse**: meta-deformation fails to gaussianize clock innovations (kurt 4.25 after). Returns are conditionally Gaussian given vol; vol is *not* conditionally Gaussian given vol-of-vol. The cascade terminates after one level — volatility has irreducible jumps. |
| **S2 — the arrow of time (Zumbach)** | **Faint in daily bars**: median Z +0.11, only 4% of assets individually significant (the estimator provably detects strong asymmetry in its gate). The leverage class structure is textbook: SPY L(1–10) = −0.121, GLD ≈ 0, TLT = +0.030 — equities leverage, safe havens inverse. |
| **S3 — surge intensity forecastable?** (auditing our own CLOCK verdict) | Joint-tail days are **2.1× more frequent** after high meta-clock terciles (3.2% → 6.8%) — but the block-bootstrap CI [0.97, 6.74] *narrowly includes 1*. The pre-registered audit fails to overturn CLOCK by a whisker; reported as suggestive, not significant. |

## KRONOS-BITS — the information budget of the market (DESIGN7.md)

How many bits/day does the past leak about the future, and what Sharpe could
ANY strategy achieve? (Kelly: the maximum log-growth edge equals the mutual
information.) Estimators gated against closed-form Gaussian/AR truth (X17).

| Channel | bits/day | meaning |
|---|---|---|
| direction, h=1 (SPY) | **0.0007** (not significant; 6/48 assets pass) | the daily sign channel is **closed** |
| direction, h=21 | 0.016 (significant) | slow trend/regime information exists at monthly horizon |
| **magnitude (vol), SPY** | **0.397** (era-stable: 0.33 pre / 0.40 post-2018) | the market broadcasts how big tomorrow will be, ~600× louder than which way |
| total next-day return | 0.199 | almost entirely magnitude information |

Ceilings: the **direction-only Sharpe ceiling is 0.48** — below buy-and-hold
beta; even a perfect daily sign-reader of our feature set loses to the index.
The vol channel's SR-equivalent (~13) explains why volatility desks exist.
KRONOS's realized Sharpe consumes ~0.003 bits/day — its edge is slow tilts
plus vol-targeting (the magnitude channel), not timing. Direction bits that
existed pre-2018 (0.009) are **zero post-2018** — the sign channel closed
within our own sample. Bounds are feature-conditional (lower bounds on true I).

## KRONOS-ARROW — entropy production: where time's arrow lives

The general irreversibility measure EP = KL(forward paths ‖ reversed paths),
of which SURGE's Zumbach statistic was a weak projection. Estimator
calibrated on a cyclic Markov chain with closed-form EP (2.04 measured vs
2.10 true bits) and exact size on reversible worlds; the coin-flip
block-reversal surrogate (and the two failed surrogate designs it replaced)
are documented in gate X18.

| Series | assets with an arrow | median net EP |
|---|---|---|
| raw returns | **14/48** (SPY: 0.019 bits, strongly significant) | 0.0005 |
| vol clock (weekly innovations) | **11/48** | 0.0030 |
| deformed returns | 6/48 (≈ false-positive rate) | **0.0000** |

**Verdict: the arrow of time lives in the return↔clock coupling and the
clock's own fast-up/slow-down asymmetry — vol-deformation erases it.**
One more costume the clock wears, now with the proper physics measure.

## KRONOS-CRITICAL — are crashes critical transitions or shocks? (DESIGN9.md)

The project's most paper-shaped result, on the contested Sornette/Scheffer
question. Naive financial early-warning-signal (EWS) studies are circular —
"variance rises before a vol spike" is trivially true. The non-circular
question: does the **critical-slowing-down signature** (restoring force
φ→1) predict crashes *beyond the contemporaneous volatility level*?

**Method (the contribution as much as the result):**
- Crash onset = forward 20-day return below a causal 5% quantile — price-
  based, deliberately not vol-defined.
- EWS indicators (φ, AC1, spectral reddening, flickering) on the log-vol
  state, vs a volatility-magnitude benchmark (level + dispersion).
- **Incremental walk-forward AUC** of {vol + CSD} over {vol}, embargoed
  (purged CV, no label leakage), with stationary-bootstrap and cluster-
  bootstrap CIs.
- **A synthetic fold/shock gate (X20)** proving the pipeline both convicts
  and exonerates: on a known double-well fold bifurcation it detects
  incremental AUC **+0.63**; on a known shock process it finds **+0.03**
  (CI includes 0).

**Result — shock-dominated, with a vestigial tipping signature:**
- Median incremental AUC across 48 assets ≈ **0** (−0.0018); only 48% of
  assets positive (sign-test **p = 0.67**). No asset class robust (equities
  −0.002, indices +0.013, bonds −0.030, gold −0.096).
- **True null, not low power**, proven two ways: the benchmark itself
  predicts crashes (the pipeline has signal), and the measured pre-crash φ
  precursor is **+0.10 std — ~8× weaker than the fold bifurcation's +0.84
  std**. Markets show a *real but economically dead* slowing-down whisper.
- Robustness: the (insignificant) signal only appears at the longest
  horizon (H=60: +0.011) and slightly favors down-crashes over up-spikes.

**Conclusion:** after the volatility confound is removed, critical-slowing-
down indicators carry no robust incremental crash-prediction information.
**Market crashes are statistically closer to shocks than to critical
transitions** — a rigorous resolution (debunking) of EWS-in-markets, with a
methodology — confound-killing incremental AUC + a convict/exonerate
synthetic gate + effect-size-vs-bifurcation calibration — that the existing
contested literature lacks.

## KRONOS-REFLEX — how endogenous is the market? (DESIGN10.md)

The quantity under every prior open question (CLOCK's surge trigger, SURGE's
cascade, CRITICAL's jumps): the **Hawkes branching ratio** n — the fraction
of extreme events that are aftershocks of other events. n→1 is critical
self-organized reflexivity; n=0 is pure exogenous news. The novel move:
decompose it by **volatility deformation**.

- **Raw** extreme-return events give median **n = 0.68** [0.61, 0.73] across
  48 assets — near-critical, **replicating Filimonov–Sornette**.
- **Vol-clock-deformed** events (genuine surprises, clustering removed)
  collapse to **n = 0.25** [0.20, 0.30] — sitting *at* a no-self-excitation
  null (0.35 on a pure stochastic-vol process). **64% of the market's
  famous near-criticality is volatility clustering, not reflexivity.**
- Genuine day-scale jump-cascade reflexivity is statistically **absent** (at
  or below the non-self-exciting null), did **not** rise post-2018
  (deformed n fell 0.52→0.24, the GFC aftermath fading — opposite to the
  "vol-targeting-grew-reflexivity" hypothesis), and is **no higher for
  systemic than idiosyncratic** events (0.21 vs 0.25).

Gate X21 anchors it: the estimator recovers known branching ratios (0.3/0.6/
0.9), reads Poisson as ~0, and — decisively — a pure stochastic-vol world
with *zero* self-excitation registers raw n = 0.74 that deformation reveals
as 0.15, proving the decomposition attributes clustering correctly. **At the
daily horizon, the market's apparent self-organized criticality is a
volatility-clustering illusion** — a direct, quantitative reframing of an
influential systemic-risk result.

## KRONOS-CONSTANTS — which market laws are actually constant? (DESIGN11.md)

The capstone, and the *Adaptive Markets* question: are the regularities KRONOS
found fundamental constants or era-dependent fashions? Each law is estimated
across 5 era-windows and classified by a variance-ratio + bootstrapped-trend
test (gate X22: 8% false-drift rate, 100% real-drift detection).

| Law | Verdict | Across eras |
|---|---|---|
| Leverage effect | **CONSTANT** | ~−0.05 every era |
| Branching ratio (raw) | **CONSTANT** | ~0.65 every era (remarkably stable) |
| Branching ratio (deformed) | **CONSTANT** | noisy but no trend |
| Roughness H | regime-varying | ~0.06, spikes to 0.12 in 2020 |
| One-clock kurtosis | regime-varying | always in [3.2, 3.7] — the law *always* holds |
| Clock commonality | regime-varying | peaks 0.81 in 2020, falls to 0.53 — **crisis-driven, not secular** |
| Fat-tail kurtosis | drifting | 5.6→12.2 (COVID-step), the only secular mover |

**Verdict: the market's *mechanism* constants are constant** — the leverage
effect, the self-excitation ratio, and the one-clock collapse (deformed
kurtosis stays near 3 in every era while raw kurtosis swings 5.6–12.2).
**What varies is crisis *intensity*, peaking in 2020 and reverting — not a
secular trend.** Clock commonality even *fell* after 2020, refuting the
ETF-ization hypothesis (and my own pre-registered C4). **No support for the
Adaptive-Markets view of secularly-evolving structure: markets are
stable-with-crisis-regimes, with a fixed mechanism and time-varying volume.**

## KRONOS-DECATHLON — the minimal market (DESIGN8.md)

The generative question only a lab with a validated battery can ask: what is
the smallest mechanism that scores like a real market? Ten events distilled
from our findings — calibrated so **real SPY scores 10/10 and GBM exactly
3/10** (gate X19, which also caught three estimator artifacts: differencing-
induced MA(1) autocorrelation, the log-χ² skew floor, close-only Hurst
fragility). A minimal flow-based agent market (fundamentalists, chartists,
vol-targeters, market makers, multi-horizon cohorts; parameters frozen after
one pre-registered tuning pass), ablated ingredient by ingredient:

| Config | Score | What it buys |
|---|---|---|
| G / F (noise, fundamentals) | 3/10 | the Gaussian events come free (efficiency, one-clock, no sign info) |
| FC (+ chartists) | **1/10** | chartists alone are toxic — momentum leak destroys even efficiency |
| FV (+ **vol-targeters**) | 5/10 | **the star hypothesis confirmed**: the de-leveraging spiral buys exactly the wild one-sided facts — fat tails, leverage effect, clock up-jumps, crash asymmetry |
| FCVM (+ market makers) | 5/10 | liquidity provision buys efficiency back without destroying the wildness — efficiency and wildness come from *different agents* |
| FCVMH (+ multi-horizon) | 4/10 | heterogeneity fails in both implementations (averaging damps the spiral; flow-conserving parallel cohorts fall below threshold) — **D4 refuted** |

**The ceiling is 5/10, and the five missing events are diagnostic:** no flow
configuration buys long memory (E3 slow-decay, E4), the arrow-in-the-coupling
(E8), or information-free signs in vol-targeting configs (E9). Mechanical
flows leak forecastable structure that real markets price away. The minimal
market's missing organ is **expectation** — anticipatory agents who trade
against predictable flows. That is the sharpest mechanism statement this
project has produced about what makes real markets real.

## Architecture

```
config.py                 every knob; pre-registered parameters
run_kronos.py             v1 pipeline -> dashboard (+ --research tab)
run_research.py           KRONOS-X experiments, cached in research/*.json
kronos/
  data.py                 prices + OHLC, caching, synthetic fallback
  volest.py               Garman-Klass range vol (+ GBM-OHLC simulator)
  regime.py               Gaussian HMM (log-space EM, walk-forward, hysteresis)
  sjm.py                  statistical jump model (penalized-clustering regimes)
  dhmm.py                 semi-Markov duration-HMM via expanded tied states
  horserace.py            pre-registered regime-model race (Q1, Q2)
  vollab.py               HAR-RV, GJR-GARCH-t MLE, QLIKE, Diebold-Mariano (Q3a)
  rough.py                Hurst scaling estimator + Davies-Harte fGn (Q3b)
  signals.py              momentum / mean-reversion / low-vol, regime-gated
  pairs.py                Kalman pairs (v1; retired by the stat-arb autopsy)
  statarb.py              Avellaneda-Lee eigenportfolio stat-arb
  covariance.py           EWMA + Ledoit-Wolf shrinkage
  rmt.py                  Marchenko-Pastur fit, denoising, min-var bake-off (Q5a)
  hrp.py                  Hierarchical Risk Parity
  black_litterman.py      BL tilt with signal views
  cvar_opt.py             min-CVaR LP, Rockafellar-Uryasev (Q5b)
  ensemble.py             Hedge / fixed-share / regime-Hedge learners (Q4)
  risk.py                 vol-target / CVaR / drawdown throttles, Greeks
  forensics.py            deflated Sharpe, CSCV-PBO, stationary bootstrap (Q6)
  backtest.py             walk-forward T+1 engine with costs
  metrics.py              performance statistics
  dashboard.py            self-contained 2-tab HTML dashboard, zero deps
tests/                    14 gates, all on synthetic ground truth first
research/                 cached experiment results + trials.json ledger
DESIGN.md / DESIGN2.md    the pre-build brainstorms (v1 / X)
```

## KRONOS-TRADE — the deployable system the research licenses (DESIGN12.md)

`run_trade.py` turns the findings into trading software. The design is dictated
by the research, not by hope:

- **No daily direction timing** (BITS: that channel is closed, ceiling Sharpe
  0.48 < beta). The alpha comes only from the **forecastable** channel.
- **HAR volatility forecasting drives position sizing** — *forecast*-vol
  targeting (size ahead of vol, since vol is predictable) rather than reacting
  to trailing realized vol.
- **Regime-gated risk-parity core** (HMM-3 filtered → shrunk-cov HRP →
  Black-Litterman tilt), the best-Sharpe configuration from the research.
- **Mechanical crash control** (drawdown throttle + CVaR cap), because
  CRITICAL proved crashes are unforecastable — you can't predict them, only
  de-risk into them.

**Walk-forward backtest (net of costs), 2013–2026:**

| Strategy | CAGR | Sharpe | MaxDD | CVaR95 |
|---|---|---|---|---|
| **KRONOS-TRADE (forecast-vol)** | 6.4% | **0.94** | **−14%** | 1.04% |
| Realized-vol control | 6.3% | 0.91 | −14% | 1.06% |
| SPY (buy & hold) | 15.0% | 0.91 | −34% | 2.55% |
| Equal-weight | 16.6% | 1.10 | −31% | 2.24% |

**Verdict (honest, as the research demands):** forecast-vol targeting beats the
realized-vol control (Sharpe 0.94 vs 0.91 — the magnitude channel *is* the
edge); the system matches SPY's risk-adjusted return at **less than half the
drawdown**; and it **does not** beat SPY on CAGR — stated plainly, because
claiming otherwise is the exact overfitting lie this whole project exists to
avoid. It is gate-verified causal (X23: exact truncation-invariance) and ships
a live `recommend()` that outputs today's target weights, regime, forecast
vol, exposure, and dollar allocation for a notional account.

## Research integrity

No lookahead anywhere (filtered probabilities, frozen betas, T+1 execution,
walk-forward refits); costs everywhere; every estimator gated on synthetic
data with known truth before real data; negative results reported as
prominently as positive ones; a trial ledger feeds the deflated Sharpe; and
the dashboard's RESEARCH tab shows the platform grading its own homework.
