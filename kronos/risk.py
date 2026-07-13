"""Risk engine: CVaR / vol-target / drawdown throttles and portfolio Greeks.

Exposure multiplier = EWMA( min(m_vol, m_cvar, m_dd) ), capped at 1 (no
leverage). All inputs are trailing — strictly causal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def historical_cvar(rets: np.ndarray, alpha: float) -> float:
    """Positive number: mean loss of the worst (1-alpha) tail."""
    if len(rets) < 50:
        return 0.0
    q = np.quantile(rets, 1 - alpha)
    tail = rets[rets <= q]
    return float(-tail.mean()) if len(tail) else 0.0


def exposure_series(port_rets: pd.Series, cfg) -> pd.DataFrame:
    """Causal exposure multipliers from the portfolio's own trailing returns.

    Returns DataFrame[m_vol, m_cvar, m_dd, exposure]; exposure at date t is
    computed from data through t and applied to t+1 returns by the backtester.
    """
    r = port_rets.fillna(0.0)
    ann = np.sqrt(252)

    ewma_vol = r.ewm(halflife=21).std() * ann
    m_vol = (cfg.vol_target / ewma_vol.replace(0, np.nan)).clip(upper=1.0).fillna(1.0)

    cvar = r.rolling(252).apply(lambda x: historical_cvar(x.to_numpy(), cfg.cvar_alpha),
                                raw=False)
    m_cvar = (cfg.cvar_target / cvar.replace(0, np.nan)).clip(upper=1.0).fillna(1.0)

    nav = (1 + r).cumprod()
    dd = nav / nav.cummax() - 1.0
    # linear de-risk from dd_start to dd_floor_at
    span = cfg.dd_floor_at - cfg.dd_start
    m_dd = 1.0 + (dd - cfg.dd_start) * (1 - cfg.dd_min_exposure) / span
    m_dd = m_dd.clip(lower=cfg.dd_min_exposure, upper=1.0)

    raw = pd.concat([m_vol, m_cvar, m_dd], axis=1).min(axis=1)
    exposure = raw.ewm(span=cfg.risk_smooth_days).mean().clip(0.0, 1.0)
    return pd.DataFrame({"m_vol": m_vol, "m_cvar": m_cvar, "m_dd": m_dd,
                         "exposure": exposure})


def portfolio_greeks(port_rets: pd.Series, mkt_rets: pd.Series,
                     cost_drag_ann: float) -> dict:
    """Factor-sensitivity 'Greeks' for an equity book (labeled honestly)."""
    df = pd.concat([port_rets, mkt_rets], axis=1, keys=["p", "m"]).dropna()
    p, m = df["p"].to_numpy(), df["m"].to_numpy()
    out = {}

    # Delta & Gamma: p ~ a + b*m + c*m^2 over trailing year
    n = min(len(df), 252)
    X = np.column_stack([np.ones(n), m[-n:], m[-n:] ** 2])
    coef, *_ = np.linalg.lstsq(X, p[-n:], rcond=None)
    out["delta"] = float(coef[1])
    out["gamma"] = float(2 * coef[2])

    # Vega: sensitivity of portfolio return to changes in market realized vol
    rv = pd.Series(m, index=df.index).rolling(21).std() * np.sqrt(252)
    dv = rv.diff().to_numpy()
    mask = ~np.isnan(dv)
    pv, dvv = p[mask][-252:], dv[mask][-252:]
    if len(pv) > 60 and np.nanstd(dvv) > 0:
        out["vega"] = float(np.polyfit(dvv, pv, 1)[0] / 100)  # per vol point
    else:
        out["vega"] = 0.0

    out["theta"] = -cost_drag_ann / 252  # daily expected cost drag
    # rolling 60d beta series for the dashboard
    roll = (df["p"].rolling(60).cov(df["m"]) / df["m"].rolling(60).var())
    out["rolling_beta"] = roll
    return out
