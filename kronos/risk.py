"""Risk engine: CVaR / vol-target / drawdown throttles and portfolio Greeks.

Exposure multiplier = EWMA( min(m_vol, m_cvar, m_dd) ), capped at
cfg.max_exposure (DESIGN15: modest leverage so vol-targeting can actually
reach the vol target; financing on the levered portion is charged by the
backtester). All inputs are trailing — strictly causal.
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


def har_vol_forecast(port_rets: pd.Series, refit_every: int = 21,
                     min_train: int = 252) -> pd.Series:
    """Causal walk-forward HAR forecast of the book's own vol (annualized).

    Value at index t is the forecast of t+1's vol using data through t only:
    features are the 1/5/22-day mean squared returns at t; OLS is refit every
    `refit_every` days on an expanding window of (features_s, r²_{s+1}) pairs
    with s+1 <= t. Before `min_train` observations, falls back to EWMA.
    (DESIGN16 V1 — HAR beats EWMA decisively on QLIKE per the vol lab; gate
    X28 pins that the lever inherits that edge without inventing one.)
    """
    r = port_rets.fillna(0.0).to_numpy()
    T = len(r)
    r2 = r ** 2
    rv1 = r2
    rv5 = pd.Series(r2).rolling(5).mean().to_numpy()
    rv22 = pd.Series(r2).rolling(22).mean().to_numpy()
    X = np.column_stack([np.ones(T), rv1, rv5, rv22])

    ann = np.sqrt(252)
    ewma = pd.Series(r, index=port_rets.index).ewm(halflife=21).std() * ann
    fc_var = np.full(T, np.nan)
    beta = None
    for t in range(T):
        if t >= min_train and (beta is None or t % refit_every == 0):
            # train rows s with features at s and target r²_{s+1}, s+1 <= t
            rows = np.arange(22, t)          # rv22 defined from index 21
            Xtr, ytr = X[rows - 1], r2[rows]
            beta, *_ = np.linalg.lstsq(Xtr, ytr, rcond=None)
        if beta is not None and np.isfinite(X[t]).all():
            fc_var[t] = max(float(X[t] @ beta), 1e-10)
    fvol = pd.Series(np.sqrt(fc_var * 252), index=port_rets.index)
    return fvol.fillna(ewma)


def exposure_series(port_rets: pd.Series, cfg,
                    tilt: pd.Series | None = None) -> pd.DataFrame:
    """Causal exposure multipliers from the portfolio's own trailing returns.

    Returns DataFrame[m_vol, m_cvar, m_dd, exposure]; exposure at date t is
    computed from data through t and applied to t+1 returns by the backtester.
    """
    r = port_rets.fillna(0.0)
    ann = np.sqrt(252)
    max_exp = getattr(cfg, "max_exposure", 1.0)

    # the LEVER: target / vol-estimate. lever_mode "har" sizes ahead of vol
    # with a causal HAR forecast (DESIGN16 V1); "ewma" reacts to trailing vol.
    if getattr(cfg, "lever_mode", "ewma") == "har":
        lever_vol = har_vol_forecast(r)
    else:
        lever_vol = r.ewm(halflife=21).std() * ann
    m_vol = (cfg.vol_target / lever_vol.replace(0, np.nan)).clip(upper=max_exp).fillna(1.0)

    cvar = r.rolling(252).apply(lambda x: historical_cvar(x.to_numpy(), cfg.cvar_alpha),
                                raw=False)
    m_cvar = (cfg.cvar_target / cvar.replace(0, np.nan)).clip(upper=1.0).fillna(1.0)

    nav = (1 + r).cumprod()
    dd = nav / nav.cummax() - 1.0
    # linear de-risk: full risk while dd >= dd_start, then down to the floor
    # at dd_floor_at. (DESIGN15 fixed an inverted sign here that braked at the
    # high-water mark and released into crashes; gate X27 pins the direction.)
    frac = ((cfg.dd_start - dd) / (cfg.dd_start - cfg.dd_floor_at)).clip(0.0, 1.0)
    m_dd = 1.0 - frac * (1.0 - cfg.dd_min_exposure)

    # m_vol is the LEVER (can exceed 1 up to max_exposure when the book runs
    # cool); m_cvar and m_dd are BRAKES in [floor, 1]. lever x min(brakes):
    # the old min() of all three could never exceed 1 (gate X27).
    brakes = pd.concat([m_cvar, m_dd], axis=1).min(axis=1)
    raw = m_vol * brakes
    if tilt is not None:                     # DESIGN21: bounded momentum tilt,
        raw = raw * tilt.reindex(raw.index).fillna(1.0)  # inside the cap (X33)
    exposure = raw.ewm(span=cfg.risk_smooth_days).mean().clip(0.0, max_exp)
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
