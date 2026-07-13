"""Range-based realized volatility estimators (KRONOS-X).

Garman-Klass uses the intraday OHLC range and is ~7x more efficient than
close-to-close squared returns; we add the overnight gap term so the
estimator covers the full 24h return variance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def gk_variance(o: pd.DataFrame, h: pd.DataFrame, l: pd.DataFrame,
                c: pd.DataFrame, overnight: bool = True) -> pd.DataFrame:
    """Daily variance estimate per asset (in return^2 units)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        log_hl = np.log(h / l)
        log_co = np.log(c / o)
        gk = 0.5 * log_hl ** 2 - (2 * np.log(2) - 1) * log_co ** 2
        if overnight:
            log_oc = np.log(o / c.shift(1))
            gk = gk + log_oc ** 2
    gk = gk.where(np.isfinite(gk))
    # a zero range (stale quote) is missing data, not zero vol
    gk = gk.where(gk > 0)
    return gk


def realized_vol(gk_var: pd.Series | pd.DataFrame, window: int = 10,
                 ann: bool = True) -> pd.Series | pd.DataFrame:
    """Rolling RMS of daily GK variances -> (annualized) vol."""
    rv = gk_var.rolling(window, min_periods=max(2, window // 2)).mean()
    out = np.sqrt(rv)
    return out * np.sqrt(252) if ann else out


def c2c_variance(c: pd.DataFrame) -> pd.DataFrame:
    """Close-to-close squared returns — the noisy benchmark."""
    r = np.log(c / c.shift(1))
    return r ** 2


def simulate_gbm_ohlc(n_days: int, sigma_ann: float, seed: int,
                      n_intraday: int = 78) -> dict:
    """GBM with known vol, OHLC sampled from a fine intraday grid.

    Used by the verification gate: the truth is sigma_ann.
    """
    rng = np.random.default_rng(seed)
    sig_d = sigma_ann / np.sqrt(252)
    # split daily variance: ~30% overnight gap, 70% intraday (realistic)
    sig_on = sig_d * np.sqrt(0.30)
    sig_id = sig_d * np.sqrt(0.70)
    o = np.empty(n_days); h = np.empty(n_days)
    l = np.empty(n_days); c = np.empty(n_days)
    last_close = 0.0  # log price
    step = sig_id / np.sqrt(n_intraday)
    for t in range(n_days):
        op = last_close + rng.normal(0, sig_on)
        path = op + np.cumsum(rng.normal(0, step, n_intraday))
        o[t] = op
        h[t] = max(op, path.max())
        l[t] = min(op, path.min())
        c[t] = path[-1]
        last_close = c[t]
    idx = pd.bdate_range("2015-01-01", periods=n_days)
    e = np.exp
    return {"open": pd.DataFrame({"X": e(o)}, index=idx),
            "high": pd.DataFrame({"X": e(h)}, index=idx),
            "low": pd.DataFrame({"X": e(l)}, index=idx),
            "close": pd.DataFrame({"X": e(c)}, index=idx),
            "true_var": sig_d ** 2}
