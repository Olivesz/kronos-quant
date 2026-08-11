"""Walk-forward backtest engine.

Discipline, enforced in exactly one place (here):
  * weights decided at close of rebalance date t use data through t only;
  * they earn returns from t+1 (held constant, drifting with prices, until
    the next rebalance);
  * risk exposure multiplier computed through t applies from t+1;
  * costs charged on the turnover executed at t+1's open (approximated as
    t+1 close prices).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import REGIME_NAMES
from kronos.black_litterman import construct_portfolio
from kronos.covariance import shrunk_cov
from kronos.risk import exposure_series
from kronos.signals import SIGNAL_FNS, combined_signal


def _trade_costs(dw: pd.Series, daily_vol: pd.Series, cfg) -> float:
    """Cost in return units for a weight change vector."""
    adw = dw.abs()
    lin_bps = cfg.commission_bps + cfg.spread_bps
    impact_bps = (cfg.impact_coeff * daily_vol * np.sqrt(adw / 0.01)
                  ).clip(upper=cfg.impact_cap_bps)
    return float((adw * (lin_bps + impact_bps) / 1e4).sum())


def run_backtest(px: pd.DataFrame, regime: pd.Series, cfg) -> dict:
    """Core long book: regime-gated multi-signal -> HRP+BL -> T+1 execution."""
    rets = px.pct_change().fillna(0.0)
    daily_vol = rets.rolling(60).std()
    dates = px.index
    n = len(dates)

    warmup = max(cfg.mom_lookback + cfg.mom_skip + 5, cfg.cov_window + 5,
                 cfg.hmm_min_train + cfg.hmm_vol_window + 2)
    rebal_idx = list(range(warmup, n, cfg.rebalance_every))

    weights = pd.DataFrame(0.0, index=dates, columns=px.columns)
    target_log = {}            # date -> target weight Series (for dashboard)
    signal_log = {}            # date -> combined signal
    strategy_weight_log = {}   # date -> regime strategy weights
    current = pd.Series(0.0, index=px.columns)
    cost_total = 0.0
    costs = np.zeros(n)
    turnover = np.zeros(n)

    for i in rebal_idx:
        t = dates[i]
        reg = int(regime.reindex([t]).fillna(1).iloc[0]) if t in regime.index else 1
        if reg < 0:
            reg = 1
        combo = combined_signal(px, t, reg, cfg)
        cov = shrunk_cov(rets.loc[:t].iloc[-cfg.cov_window:],
                         cfg.cov_ewma_halflife, cfg.cov_window)
        port = construct_portfolio(cov, combo["combined"], cfg)
        target = port["weights"]

        # no-trade band: skip dust trades
        dw = target - current
        dw[dw.abs() < cfg.no_trade_band] = 0.0
        new = (current + dw).clip(lower=0.0)
        if new.sum() > 0:
            new /= new.sum()

        # execute at t+1: cost charged on that day, weights effective t+1
        if i + 1 < n:
            tc = _trade_costs(new - current, daily_vol.iloc[i].fillna(0.02), cfg)
            costs[i + 1] += tc
            turnover[i + 1] = float((new - current).abs().sum())
            cost_total += tc
        current = new

        target_log[t] = target
        signal_log[t] = combo["combined"]
        strategy_weight_log[t] = {"regime": REGIME_NAMES.get(reg, "?"),
                                  **combo["weights"]}

        # hold (drift) until next rebalance
        j_end = min(i + cfg.rebalance_every, n - 1)
        for j in range(i + 1, j_end + 1):
            weights.iloc[j] = current
            # drift weights with returns so the book is self-financing
            drifted = current * (1 + rets.iloc[j])
            s = drifted.sum()
            if s > 0:
                current = drifted / s

    gross_rets = (weights * rets).sum(axis=1)  # weights are start-of-day, t+1-aligned
    gross_rets.iloc[:warmup + 1] = 0.0

    # risk overlay: exposure from trailing gross book, applied T+1.
    # Leverage above 1 pays financing daily on the levered portion (DESIGN15).
    expo = exposure_series(gross_rets, cfg)
    exposure_lag = expo["exposure"].shift(1).fillna(1.0)
    fin_rate = getattr(cfg, "financing_rate_ann", 0.0)
    financing = (exposure_lag - 1.0).clip(lower=0.0) * (fin_rate / 252.0)
    net_rets = gross_rets * exposure_lag - costs - financing

    return {
        "dates": dates,
        "gross": gross_rets,
        "net": pd.Series(net_rets, index=dates),
        "costs": pd.Series(costs, index=dates),
        "turnover": pd.Series(turnover, index=dates),
        "weights": weights,
        "exposure": expo,
        "exposure_applied": exposure_lag,
        "targets": target_log,
        "signals": signal_log,
        "strategy_weights": strategy_weight_log,
        "warmup_end": dates[warmup],
        "cost_total": cost_total,
    }


def sleeve_backtests(px: pd.DataFrame, regime: pd.Series, cfg) -> dict[str, pd.Series]:
    """Stand-alone net-ish returns per signal sleeve (same machinery, one
    signal at a time, no risk overlay) for attribution."""
    rets = px.pct_change().fillna(0.0)
    daily_vol = rets.rolling(60).std()
    dates = px.index
    n = len(dates)
    warmup = max(cfg.mom_lookback + cfg.mom_skip + 5, cfg.cov_window + 5,
                 cfg.hmm_min_train + cfg.hmm_vol_window + 2)
    rebal_idx = list(range(warmup, n, cfg.rebalance_every))

    out = {}
    for name, fn in SIGNAL_FNS.items():
        weights = pd.DataFrame(0.0, index=dates, columns=px.columns)
        current = pd.Series(0.0, index=px.columns)
        costs = np.zeros(n)
        for i in rebal_idx:
            t = dates[i]
            sig = fn(px, t, cfg)
            cov = shrunk_cov(rets.loc[:t].iloc[-cfg.cov_window:],
                             cfg.cov_ewma_halflife, cfg.cov_window)
            port = construct_portfolio(cov, sig, cfg)
            new = port["weights"]
            if i + 1 < n:
                costs[i + 1] += _trade_costs(new - current, daily_vol.iloc[i].fillna(0.02), cfg)
            current = new
            j_end = min(i + cfg.rebalance_every, n - 1)
            for j in range(i + 1, j_end + 1):
                weights.iloc[j] = current
                drifted = current * (1 + rets.iloc[j])
                s = drifted.sum()
                if s > 0:
                    current = drifted / s
        r = (weights * rets).sum(axis=1) - costs
        r.iloc[:warmup + 1] = 0.0
        out[name] = r
    return out
