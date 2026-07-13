"""Cross-sectional alpha signals with a unified interface.

Every signal maps (prices through date t) -> cross-sectionally z-scored
Series over tickers, capped at +/-cap. The combiner blends them with
regime-dependent weights and re-standardizes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from config import REGIME_NAMES, REGIME_STRATEGY_WEIGHTS


def _xz(s: pd.Series, cap: float) -> pd.Series:
    sd = s.std()
    if not np.isfinite(sd) or sd < 1e-12:
        return s * 0.0
    return ((s - s.mean()) / sd).clip(-cap, cap)


def momentum_signal(px: pd.DataFrame, t: pd.Timestamp, cfg) -> pd.Series:
    """12-1 momentum: return from t-252 to t-21, skipping the reversal month."""
    window = px.loc[:t]
    if len(window) < cfg.mom_lookback + 1:
        return pd.Series(0.0, index=px.columns)
    p_now = window.iloc[-1 - cfg.mom_skip]
    p_then = window.iloc[-1 - cfg.mom_lookback]
    raw = p_now / p_then - 1.0
    return _xz(raw, cfg.signal_cap)


def mean_reversion_signal(px: pd.DataFrame, t: pd.Timestamp, cfg) -> pd.Series:
    """Short-term reversal: fade z-score of price vs its 20d mean."""
    window = px.loc[:t].iloc[-(cfg.rev_window + 5):]
    if len(window) < cfg.rev_window:
        return pd.Series(0.0, index=px.columns)
    sma = window.iloc[-cfg.rev_window:].mean()
    sd = window.iloc[-cfg.rev_window:].std()
    z = (window.iloc[-1] - sma) / sd.replace(0, np.nan)
    raw = -z.fillna(0.0).clip(-cfg.signal_cap, cfg.signal_cap)
    return _xz(raw, cfg.signal_cap)


def low_vol_signal(px: pd.DataFrame, t: pd.Timestamp, cfg) -> pd.Series:
    """Low-volatility factor: prefer low realized vol, via Blom rank-normal."""
    window = px.loc[:t].iloc[-(cfg.lowvol_window + 5):]
    if len(window) < cfg.lowvol_window:
        return pd.Series(0.0, index=px.columns)
    vol = window.pct_change().iloc[-cfg.lowvol_window:].std()
    n = len(vol)
    ranks = vol.rank()  # low vol -> low rank
    # Blom transform; negate so low vol gets a high score
    raw = pd.Series(-norm.ppf((ranks - 0.375) / (n + 0.25)), index=vol.index)
    return _xz(raw, cfg.signal_cap)


SIGNAL_FNS = {
    "momentum": momentum_signal,
    "mean_reversion": mean_reversion_signal,
    "low_vol": low_vol_signal,
}


def combined_signal(px: pd.DataFrame, t: pd.Timestamp, regime_id: int, cfg) -> dict:
    """Blend signals using the regime's strategy weights.

    Returns {"combined": Series, "components": {name: Series},
             "weights": {name: float}}.
    """
    regime_name = REGIME_NAMES.get(int(regime_id), "Volatile")
    wmap = REGIME_STRATEGY_WEIGHTS[regime_name]
    comps, total = {}, None
    for name, fn in SIGNAL_FNS.items():
        sig = fn(px, t, cfg)
        comps[name] = sig
        part = wmap[name] * sig
        total = part if total is None else total + part
    return {"combined": _xz(total, cfg.signal_cap),
            "components": comps, "weights": dict(wmap)}
