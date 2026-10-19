"""Performance metrics. rf = 0 throughout (stated in the dashboard)."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from kronos.data import FLOAT_PARSE

ANN = 252


def cagr(rets: pd.Series) -> float:
    nav = (1 + rets).prod()
    years = len(rets) / ANN
    return float(nav ** (1 / years) - 1) if years > 0 and nav > 0 else 0.0


def ann_vol(rets: pd.Series) -> float:
    return float(rets.std() * np.sqrt(ANN))


def sharpe(rets: pd.Series) -> float:
    v = rets.std()
    return float(rets.mean() / v * np.sqrt(ANN)) if v > 0 else 0.0


def dtb3_daily(index: pd.DatetimeIndex, path: str = "data/dtb3.csv") -> pd.Series:
    """Daily cash return from the committed FRED DTB3 snapshot (DESIGN27).

    DTB3 is a bank-discount yield d (percent, 360-day basis). It is converted
    to the money-market yield y = d / (1 - d*91/360), and each trading day t
    accrues the rate known at the previous trading day over the CALENDAR days
    since then: y_{t-1} * days(t-1, t) / 360. A year therefore accrues about
    y * 365/360 — the full bill return, weekends and holidays included — and a
    rate print on day t only affects accrual from t+1. Raises if the snapshot
    does not cover the index; never substitutes zero."""
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
    df = pd.read_csv(path, parse_dates=[0], index_col=0,
                     float_precision=FLOAT_PARSE).iloc[:, 0]
    d = pd.to_numeric(df, errors="coerce").dropna() / 100.0
    if index.min() - pd.Timedelta(days=14) < d.index.min() or \
            index.max() > d.index.max() + pd.Timedelta(days=14):
        raise ValueError(f"DTB3 snapshot does not cover {index.min()}..{index.max()}")
    y = d / (1.0 - d * 91.0 / 360.0)
    rate = y.reindex(index.union(y.index)).ffill().reindex(index)
    days = index.to_series().diff().dt.days.fillna(1.0)
    prev = rate.shift(1).fillna(rate)
    return (prev * days / 360.0).rename("rf_daily")


def sharpe_excess(rets: pd.Series, rf_daily: pd.Series) -> float:
    """Annualized Sharpe of returns in excess of cash (DESIGN27 convention)."""
    ex = rets - rf_daily.reindex(rets.index).fillna(0.0)
    v = ex.std()
    return float(ex.mean() / v * np.sqrt(ANN)) if v > 0 else 0.0


def sortino(rets: pd.Series) -> float:
    down = rets[rets < 0].std()
    return float(rets.mean() / down * np.sqrt(ANN)) if down and down > 0 else 0.0


def drawdown_series(rets: pd.Series) -> pd.Series:
    nav = (1 + rets).cumprod()
    return nav / nav.cummax() - 1.0


def max_drawdown(rets: pd.Series) -> tuple[float, int]:
    dd = drawdown_series(rets)
    mdd = float(dd.min())
    # longest underwater spell in days
    underwater = dd < 0
    longest = cur = 0
    for u in underwater:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return mdd, longest


def calmar(rets: pd.Series) -> float:
    mdd, _ = max_drawdown(rets)
    return float(cagr(rets) / abs(mdd)) if mdd < 0 else 0.0


def var_cvar(rets: pd.Series, alpha: float = 0.95) -> tuple[float, float]:
    q = float(np.quantile(rets, 1 - alpha))
    tail = rets[rets <= q]
    return -q, float(-tail.mean()) if len(tail) else 0.0


def summary(rets: pd.Series, name: str = "") -> dict:
    mdd, uw = max_drawdown(rets)
    var, cv = var_cvar(rets)
    return {
        "name": name,
        "cagr": cagr(rets),
        "vol": ann_vol(rets),
        "sharpe": sharpe(rets),
        "sortino": sortino(rets),
        "calmar": calmar(rets),
        "max_dd": mdd,
        "underwater_days": uw,
        "hit_rate": float((rets > 0).mean()),
        "skew": float(rets.skew()),
        "kurtosis": float(rets.kurtosis()),
        "var95": var,
        "cvar95": cv,
        "total_return": float((1 + rets).prod() - 1),
    }


def monthly_table(rets: pd.Series) -> pd.DataFrame:
    m = (1 + rets).resample("ME").prod() - 1
    return pd.DataFrame({"year": m.index.year, "month": m.index.month, "ret": m.values})
