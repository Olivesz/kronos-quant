# KRONOS — Design Brainstorm & Architecture

*Regime-Aware Quantitative Alpha Platform. This document is the deep brainstorm written **before** building, with the explicit goal of anticipating every roadblock and designing around it.*

---

## 0. Philosophy & Constraints

**Environment constraints (hard rules):**
- Everything lives inside `Kronos/`. A project-local `.venv` (Python 3.12 — mature wheels; the system default 3.14 is too new for guaranteed binary wheel coverage). No global installs, no system changes, ever.
- Minimal dependency surface: `numpy`, `pandas`, `scipy`, `yfinance`. **No** `hmmlearn`, `cvxpy`, `pykalman`, `riskfolio-lib`, or plotting libs. Every model is implemented from scratch. This is deliberate: fewer wheels to break, and implementing Baum-Welch / Kalman / HRP / Black-Litterman ourselves is the whole point of a research platform — we control every number.
- The dashboard is a **single self-contained HTML file** with a hand-written vanilla-JS canvas charting engine. Zero CDN calls, works offline, opens with `open output/dashboard.html`. No server, no npm, no node.

**Research-integrity constraints (the rules that make the backtest honest):**
1. **No lookahead, anywhere.** Every model that learns from data (HMM, covariance, Kalman, signal z-scores) is fit walk-forward: at rebalance date *t*, only data through *t* is visible. Signals computed at close of *t* earn returns from *t+1* onward (T+1 execution).
2. **Costs are first-class.** Every backtest result is net of commission + slippage. We report gross vs. net so cost drag is visible.
3. **Determinism.** One global seed. Same inputs → same dashboard, bit for bit. Crucial for debuggability.

---

## 1. Anticipated Roadblocks & Pre-emptive Solutions

This is the section the user asked for: kill the errors before meeting them.

### 1.1 Data layer
| Roadblock | Pre-emptive solution |
|---|---|
| Yahoo Finance rate-limits / blocks / changes API; network may be sandboxed entirely | **Dual-source design.** Try `yfinance` batch download once, cache to CSV in `data/cache/`. If the fetch fails or returns garbage, fall back to a **synthetic market generator** — a regime-switching multivariate model producing statistically realistic data (fat tails, vol clustering, correlated cross-section, regime shifts). The whole platform runs identically on either source; a flag in the dashboard says which one was used. |
| Tickers with short history (IPO mid-sample) create ragged panels | Universe filter: require ≥ 95% coverage over the sample; forward-fill ≤ 3 day gaps; drop the rest. Align everything on the intersection calendar. |
| Adjusted vs. unadjusted prices (splits/dividends corrupt returns) | Use `auto_adjust=True` adjusted closes only. Sanity gate: any single-day return > 60% on a mega-cap → flag and clip. |
| Survivorship bias (today's S&P names backtested 15 years) | Can't fully fix without CRSP. **Acknowledge honestly** in dashboard fine print; mitigate by using a diversified multi-sector + multi-asset ETF/mega-cap universe rather than hot stocks. |
| yfinance MultiIndex column chaos (changes between versions) | One normalization choke point: `_normalize_yf(df)` that handles both single- and multi-ticker shapes and always emits a flat `(date × ticker)` close-price DataFrame. |

### 1.2 HMM regime detection
| Roadblock | Pre-emptive solution |
|---|---|
| Numerical underflow in forward-backward (products of tiny probabilities) | Implement in **log space** with `scipy.special.logsumexp`. Never multiply raw likelihoods. |
| Label switching (state 0 is "bull" in one fit, "bear" in the next) | After every fit, **canonicalize states**: sort by (mean return descending / volatility ascending) → Bull = highest Sharpe state, Bear = most negative-mean state, Volatile = highest-vol remainder. Regime IDs are then stable across refits. |
| Singular covariance when a state captures few points | Variance floors (`σ² ≥ 1e-10`) + Dirichlet-style pseudocounts on transition rows; re-seed a state from data quantiles if its responsibility mass collapses below a threshold. |
| EM local optima → garbage regimes | **Smart initialization**: k-means-style quantile split on (return, |return|) features instead of random init; multiple restarts, keep best log-likelihood. |
| Lookahead via smoothing: using the full-sample posterior γ_t leaks the future into date t | Two outputs: smoothed posteriors for *charts* (clearly labeled), but the **filtered probability** (forward pass only, data ≤ t) for *trading decisions*. Walk-forward refit on an expanding window every 21 trading days. |
| Whipsaw regime flips causing churn | Hysteresis: switch regime only when filtered probability of the new state exceeds 60% for 3 consecutive days. |
| Features: raw returns alone make states ≈ noise | 2-D observation vector: (daily log return of market proxy, log realized vol over 10d). Vol is the strongest regime separator; return sign disambiguates bull from bear. |

### 1.3 Alpha engine
| Roadblock | Pre-emptive solution |
|---|---|
| Momentum crashes in regime transitions (2009-style reversal) | This is the *thesis of the platform*: regime-aware gating. Momentum weight ↓ in Bear/Volatile, mean-reversion weight ↑. The regime → strategy-weight map is explicit config, shown in the dashboard. |
| Mean reversion picks falling knives | Trade z-score of price vs. 20d mean **within** the cross-section (relative reversal), cap z at ±3, and gate by regime. |
| Kalman pairs: non-cointegrated pairs drift forever | Pair selection on the formation window: correlation pre-filter, then an ADF-style stationarity check on the spread residual (implemented manually via OLS on Δspread vs lagged spread; t-stat threshold). Re-select pairs annually, walk-forward. |
| Kalman filter divergence (Q/R mis-tuned → β explodes) | State = [α, β] with small constant process noise (δ ≈ 1e-5 trick from Chan), observation noise estimated from formation window; clamp β to sane bounds; trade only |z| entry/exit bands with hard stop at |z| > 4.5 (structural break → kill the pair). |
| Low-vol factor is just a bond proxy / sector bet | Demean low-vol score within the cross-section and combine with the others — it diversifies momentum rather than dominating. |
| Signal scales differ (momentum in σ-units, reversal in z, low-vol in ranks) | Every strategy emits a **cross-sectionally z-scored signal** in [-3, +3], same interface: `signal(date) → Series[ticker]`. Combination is then a clean weighted sum. |

### 1.4 Portfolio construction
| Roadblock | Pre-emptive solution |
|---|---|
| Markowitz instability (tiny estimation error → wild weights) | That's *why* HRP: no matrix inversion at all. Correlation distance → single-linkage clustering → quasi-diagonalization → recursive bisection with inverse-variance splits. Implemented from López de Prado's algorithm directly. |
| HRP ignores expected returns (pure risk allocation) | **Two-stage marriage:** HRP gives the *risk backbone* w_HRP; Black-Litterman tilts it. BL prior π = implied returns from the HRP weights (reverse optimization, δΣw), views = combined alpha signal per asset, view uncertainty Ω scaled by signal confidence (|z| → tighter Ω, Idzorek-flavored). Posterior μ_BL feeds a constrained tilt: w = normalize(w_HRP ⊙ (1 + κ·standardized μ_BL)), long-only, max weight cap. This keeps HRP's stability and BL's Bayesian view-blending without a fragile optimizer. |
| Covariance estimation noise (N assets, short window) | Ledoit-Wolf-style shrinkage to constant-correlation target, implemented in ~30 lines (closed-form shrinkage intensity). EWMA-weighted sample cov as the base. |
| BL singularities (Ω⁻¹ with zero-confidence views) | Use the formulation that never inverts Ω alone; floor Ω diagonal; if no views that day, posterior = prior (graceful no-op). |
| Weights jitter at every rebalance → cost bleed | Rebalance monthly (21d), with a **no-trade band**: skip trades where |Δw| < 0.25%; turnover penalty reported. |

### 1.5 Risk engine
| Roadblock | Pre-emptive solution |
|---|---|
| CVaR from 252 points is noisy | Historical CVaR on the portfolio return distribution with a 1-year window at 95%, used as a *scaling* signal (target CVaR / realized CVaR, capped leverage), not a hard optimizer constraint. |
| Vol targeting amplifies into crashes (sells low) | Combine three multipliers — vol-target, CVaR, drawdown-throttle — take the **minimum**, smooth with 5d EWMA, cap leverage at 1.0 (long-only, no margin). Drawdown throttle: linear de-risking once DD < −8%, floor at 25% exposure by −20%. |
| "Greeks" for an equity portfolio (user asked for Greeks) | Reinterpret honestly as **portfolio sensitivities**: Delta = β to market proxy; Gamma = convexity from quadratic regression of portfolio vs market returns; Vega = sensitivity to Δ(realized vol); Theta = expected daily cost drag + carry; plus net/gross exposure. Label the panel "Portfolio Greeks (factor sensitivities)" so it's rigorous, not cosplay. |

### 1.6 Backtester
| Roadblock | Pre-emptive solution |
|---|---|
| Lookahead in execution | Signals at close *t* → weights effective close *t+1* (`weights.shift(1)` discipline enforced in one place, the backtest loop — not scattered). |
| Cost model too naive (flat bps) | Commission (1 bp) + spread cost (2 bp) + **square-root market impact**: `impact_bps = k·σ_daily·√(trade_size_proxy)` with conservative k. All parameters in config, all reported. |
| Backtest loop too slow in pure Python | Vectorized pandas for returns/PnL; the only true loop is over rebalance dates (~180 iterations for 15y monthly) — trivial. HMM EM is O(T·K²) numpy — fine. |
| Silent NaN propagation | Assertion gates at each pipeline stage: no NaNs in weights, weights sum to ≈1, |w|≤cap. Fail loudly. |
| Strategy attribution ambiguity | Track each sleeve's stand-alone net PnL *and* its marginal contribution within the combined book; both shown in the dashboard. |

### 1.7 Dashboard
| Roadblock | Pre-emptive solution |
|---|---|
| CDN dependence (plotly etc.) breaks offline | Hand-rolled canvas charting engine (~700 lines vanilla JS): line/area charts with crosshair + tooltip, regime ribbon, heatmaps, bar charts, donut. Data embedded as one JSON blob. One file, zero requests. |
| 15 years × daily × many series = huge HTML | Downsample chart series to ~1500 points (LTTB-style min/max-preserving decimation) — visually lossless, file stays ~1–2 MB. |
| Canvas blurry on retina | Scale canvas by `devicePixelRatio`, draw in logical pixels. |
| Timezone/date bugs in JS (`new Date('2020-01-03')` is UTC-midnight) | Never use JS Date parsing; dates are passed as ISO strings and plotted by index. |

---

## 2. Architecture

```
Kronos/
├── .venv/                      # isolated env (python3.12)
├── DESIGN.md                   # this document
├── config.py                   # every knob in one dataclass
├── run_kronos.py               # the pipeline entrypoint
├── kronos/
│   ├── __init__.py
│   ├── data.py                 # yfinance loader + cache + synthetic generator
│   ├── regime.py               # Gaussian HMM from scratch (log-space EM)
│   ├── signals.py              # momentum, mean-reversion, low-vol (+ combiner)
│   ├── pairs.py                # Kalman filter pairs engine
│   ├── covariance.py           # EWMA cov + Ledoit-Wolf shrinkage
│   ├── hrp.py                  # Hierarchical Risk Parity
│   ├── black_litterman.py      # BL posterior with signal views
│   ├── risk.py                 # CVaR / vol-target / drawdown throttle / Greeks
│   ├── backtest.py             # walk-forward engine + costs + attribution
│   ├── metrics.py              # Sharpe, Sortino, Calmar, etc.
│   └── dashboard.py            # JSON payload → self-contained HTML
├── tests/                      # pytest-free, plain-assert smoke tests
├── data/cache/                 # CSV price cache
└── output/dashboard.html       # the deliverable
```

**Pipeline flow (run_kronos.py):**
1. Load/cached/synthetic prices → returns panel.
2. Walk-forward HMM on (market return, realized vol) → filtered regime series.
3. Each rebalance date: compute 3 cross-sectional signals + pairs book.
4. Regime gates strategy weights → combined alpha per asset.
5. Shrunk EWMA covariance → HRP backbone → BL tilt with alpha views → target weights.
6. Risk engine scales gross exposure (vol target ∧ CVaR ∧ DD throttle).
7. Backtester executes T+1 with costs; pairs sleeve runs as overlay book.
8. Metrics + attribution + Greeks → JSON → dashboard.html.

## 3. Module Math (precise, so implementation is transcription)

### 3.1 Gaussian HMM (regime.py)
- Obs: x_t = [r_mkt,t , log RV_t(10d)] ∈ ℝ², K=3 states, full 2×2 covs.
- Forward: log α_t(j) = log B_j(x_t) + logsumexp_i(log α_{t-1}(i) + log A_ij); filtered P(s_t|x_{1:t}) = softmax(log α_t).
- Backward + γ, ξ for EM; M-step with pseudocount 1.0 on A rows, variance floor.
- Init: sort days by RV into terciles → initial state means/covs from those buckets (deterministic, no random restarts needed, but keep 3 jittered restarts for safety).
- Walk-forward: first fit needs ≥ 750 obs; refit every 21 days on expanding window; predict filtered probs out to next refit.

### 3.2 Signals (signals.py)
- **Momentum**: r_{t-252→t-21} (12-1 month, skip recent month to dodge reversal); z-score cross-sectionally.
- **Mean reversion**: −(P_t − SMA20)/σ20 per name, cross-sectional z, capped ±3.
- **Low-vol**: −rank(σ_60d) mapped to z via inverse-normal of rank (Blom). 
- **Combiner**: s = Σ_k w_k(regime)·z_k, re-z-scored. Regime map (config):
  - Bull: mom .55 / rev .15 / lowvol .30
  - Volatile: mom .20 / rev .40 / lowvol .40
  - Bear: mom .10 / rev .30 / lowvol .60

### 3.3 Kalman pairs (pairs.py)
- Formation (252d): top correlated pairs across sector-diverse universe, then Engle-Granger style residual stationarity t-test < −2.8.
- Kalman: state θ_t=[α_t, β_t], F=I, H_t=[1, x_t], Q=δ/(1−δ)·I with δ=1e-5, R from formation OLS residual var. Standard predict/update; spread e_t = y_t − ŷ_t, z = e_t/√S_t (innovation variance).
- Trade: enter |z|>2, exit |z|<0.5, hard stop |z|>4.5 or 60d max hold. Dollar-neutral, each pair risk-budgeted equally within a 20% gross overlay sleeve.

### 3.4 HRP (hrp.py)
- D_ij = √(½(1−ρ_ij)); single-linkage on condensed distance (scipy.cluster.hierarchy).
- Quasi-diagonalize by dendrogram leaf order; recursive bisection: split variance computed with inverse-variance weights within each half; α = 1 − V_left/(V_left+V_right).

### 3.5 Black-Litterman (black_litterman.py)
- Prior: π = δ·Σ·w_hrp (reverse-optimized from the HRP backbone, δ≈2.5).
- Views: P = I (absolute view per asset), Q = π + λ·z_signal·σ_asset (signal tilts expected return by up to λ σ).
- Ω = diag(τ·P Σ Pᵀ) / max(|z|,0.1) — confident signals → tighter Ω. τ=0.05.
- Posterior: μ = π + τΣPᵀ(PτΣPᵀ+Ω)⁻¹(Q−Pπ) (never inverts Ω alone).
- Tilt: w ∝ w_hrp·(1+κ·standardize(μ−π)), clip ≥0, cap 12%, renormalize.

### 3.6 Risk (risk.py)
- CVaR95: mean of worst 5% of trailing 252 daily portfolio returns. Multiplier m_cvar = min(1, CVaR_target/CVaR_realized), CVaR_target ≈ 1.8%.
- Vol target: m_vol = min(1, σ_target/σ_ewma,ann), σ_target = 10%.
- DD throttle: m_dd = 1 for DD>−8%; linear → 0.25 at DD=−20%; floor 0.25.
- Exposure = EWMA_5(min(m_vol, m_cvar, m_dd)).
- Greeks: β (60d OLS vs market), Gamma (quadratic term, 252d), Vega (Δport ret vs Δ realized vol, 252d), Theta (−annualized cost drag), gross/net exposure.

### 3.7 Backtest (backtest.py)
- Daily PnL: r_p,t = Σ_i w_i,t-1·r_i,t · exposure_{t-1} − costs_t.
- Costs at rebalance: Σ_i |Δw_i| · (1bp + 2bp + impact); impact_bps = 10·σ_i,daily·√(|Δw_i|/0.01) capped 25bp.
- Benchmarks: equal-weight buy&hold of universe + market proxy (SPY).
- Walk-forward only: warmup = max(HMM 750, momentum 252+21) → trading starts ~year 4 of data.

### 3.8 Metrics
CAGR, ann. vol, Sharpe (rf=0 stated), Sortino, Calmar, maxDD + duration, hit rate, skew, kurtosis, VaR/CVaR, turnover/yr, cost drag/yr, per-regime Sharpe table, monthly return matrix.

## 4. Dashboard Spec (single HTML)

Dark theme ("Bloomberg-after-midnight"): #0a0e17 bg, cyan/amber/rose accents, JetBrains-style mono numerals.

Layout (top → bottom):
1. **Header**: KRONOS wordmark, data-source badge (LIVE/SYNTHETIC), date range, current regime chip.
2. **Hero metric cards** (8): CAGR, Sharpe, Sortino, MaxDD, CVaR95, Vol, Turnover, Cost drag — each with sparkline.
3. **Equity curve** (log-scale toggle): KRONOS net vs gross vs SPY vs equal-weight; regime ribbon underlay (green/amber/red translucent bands); drawdown subchart linked on shared crosshair.
4. **Regime panel**: stacked filtered-probability area chart; transition matrix heatmap; per-regime stats table.
5. **Strategy attribution**: cumulative PnL per sleeve (mom/rev/lowvol/pairs); regime-conditioned weight allocation over time (stacked area).
6. **Portfolio panel**: latest weights bar chart colored by cluster; HRP dendrogram order strip; weight history heatmap.
7. **Risk panel**: exposure multiplier line with component breakdown; rolling vol vs target; CVaR gauge; return histogram with VaR/CVaR markers.
8. **Greeks panel**: Delta/Gamma/Vega/Theta cards + rolling beta chart.
9. **Pairs panel**: live pairs table (β, z, status) + example spread z-score chart with entry/exit bands.
10. **Monthly returns heatmap** + footer with honest-limitations note (survivorship, ETF universe, rf=0).

Interactions: crosshair tooltips everywhere, equity-curve zoom via drag-select with double-click reset, log toggle, sleeve show/hide legend toggles. All vanilla JS, one `<script>`.

## 5. Universe

~40 liquid names mixing sectors + asset classes for regime richness:
mega-caps across all 11 GICS sectors (AAPL MSFT NVDA AMZN GOOGL META JPM BAC GS UNH JNJ PFE XOM CVX CAT HON BA WMT PG KO PEP MCD HD DIS NFLX CRM ADBE INTC CSCO ORCL T VZ NEE DUK LIN FDX UPS), plus ETFs for diversification & pairs fodder (SPY QQQ IWM DIA XLF XLE XLK XLU GLD TLT HYG LQD). SPY = market proxy & benchmark. Daily, 2010 → present.

## 6. Build Order & Verification Gates

1. data.py → gate: clean panel, no NaNs, plausible stats printed.
2. regime.py → gate: synthetic HMM data with known params recovered (transition matrix within tolerance); real data regimes align with known history (2020 crash = Bear/Volatile, 2017 = Bull).
3. signals.py → gate: z-scores mean≈0 std≈1 cross-sectionally; momentum signal on synthetic trend data is positive.
4. hrp.py → gate: weights sum 1, all ≥0; toy 3-asset case matches hand computation; high-vol asset gets less weight.
5. black_litterman.py → gate: zero views ⇒ posterior=prior; positive view on asset ⇒ weight increases.
6. pairs.py → gate: on synthetic cointegrated pair, Kalman β converges to true β; z-score mean-reverts.
7. risk.py + backtest.py → gate: zero-cost equal-weight backtest ≈ benchmark arithmetic; costs reduce returns by plausible bps.
8. dashboard.py → gate: HTML opens, all charts render (verify via headless screenshot if available).

Each gate is a smoke test in `tests/` runnable via `.venv/bin/python tests/run_all.py`.

## 7. Stretch Goals (only after core is verified)
- Parameter sensitivity mini-grid (vol target × rebalance freq) shown as dashboard heatmap.
- Bootstrap confidence band on Sharpe (block bootstrap).
- Regime-conditional Monte Carlo fan chart for forward 1y.
