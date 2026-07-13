# KRONOS-TRADE — A Research-Grounded Trading System

*Pre-registered. Not "beat the market" — the research forbids that claim at
daily frequency. The mandate the findings actually license:*

## What the research dictates
- **BITS**: daily direction is ~unpredictable (direction-only Sharpe ceiling
  0.48 < beta). => DO NOT time direction at daily frequency. Trade only the
  slow (21d) cross-sectional tilts where the faint bits live.
- **Vol lab + BITS**: volatility magnitude IS predictable (HAR-RV the MCS
  winner, ~0.4 bits/day). => The edge is volatility forecasting & sizing.
- **CRITICAL**: crashes are unforecastable shocks. => No crash prediction;
  de-risk MECHANICALLY (forecast-vol targeting + drawdown throttle).
- **CONSTANTS**: leverage effect & one-clock collapse are permanent. => Safe
  structural priors; size in vol-standardized units.
- **Core book had the best Sharpe (0.95) at half SPY's drawdown.** =>
  Objective = risk-adjusted return (Sharpe, Calmar, drawdown), NOT CAGR.

## The system (all strictly causal, walk-forward)
1. **Vol forecast** (the engine): per-asset HAR-RV 1-step variance forecast on
   Garman-Klass realized vol, refit every 21d.
2. **Regime**: HMM-3, filtered (causal), the horse-race production winner.
3. **Signals**: 12-1 momentum, low-vol, short reversal — combined with
   regime-dependent weights (Bull->momentum; stress->low-vol/reversal).
4. **Portfolio**: shrunk-covariance HRP backbone + Black-Litterman tilt
   toward the combined signal, long-only, weight cap.
5. **Forecast-vol targeting (THE research-grounded edge)**: exposure =
   vol_target / sqrt(w' Sigma_forecast w), where Sigma_forecast uses the HAR
   variance forecasts on the diagonal and recent correlations off-diagonal.
   Because vol is forecastable, we size AHEAD of it rather than reacting to
   trailing realized vol.
6. **Mechanical crash control**: multiply exposure by a drawdown throttle and
   a CVaR cap; take the min; smooth; cap at 1 (no leverage).
7. Monthly rebalance, no-trade band, full transaction costs.

## Pre-registered hypotheses
- **T1**: forecast-vol targeting beats realized-vol targeting on Sharpe AND
  drawdown (the HAR forecast leads realized vol, so exposure cuts earlier).
- **T2**: the system delivers Sharpe > equal-weight and > SPY at materially
  lower max-drawdown than SPY (the honest, research-licensed win).
- **T3**: it does NOT beat SPY on CAGR (and we report that plainly).

## Gate (test_trade.py)
1. Strict causality: shifting all inputs forward by one day must not change
   any historical target weight (no look-ahead).
2. On a synthetic world with FORECASTABLE vol (persistent SV), forecast-vol
   targeting achieves lower realized-vol-tracking error and higher Sharpe
   than realized-vol targeting; on a world with UNFORECASTABLE vol (iid),
   the two tie (no false edge).
3. Weights valid (sum~1, >=0, capped); exposure in [floor, 1].

## Deliverable
`run_trade.py`: walk-forward backtest vs SPY / equal-weight / realized-vol
variant, the honest metrics table, and a live **TODAY'S PORTFOLIO**
recommendation (target weights, regime, forecast vol, exposure, $ allocation
for a notional account). A focused trade dashboard panel.
