"""Performance metrics. rf = 0 throughout (stated in the dashboard)."""
from __future__ import annotations

import numpy as np
import pandas as pd

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
    """Daily cash rate from the committed FRED DTB3 snapshot (DESIGN27).

    Discount yields in percent, forward-filled to the given trading days,
    ACT/360 to a daily simple rate. Raises if the file is missing or the
    span does not cover the index — never silently substitutes zero."""
    df = pd.read_csv(path, parse_dates=[0], index_col=0).iloc[:, 0]
    df = pd.to_numeric(df, errors="coerce").dropna()
    if index.min() < df.index.min() or index.max() > df.index.max() + pd.Timedelta(days=14):
        raise ValueError(f"DTB3 snapshot does not cover {index.min()}..{index.max()}")
    daily = (df / 100.0 / 360.0).reindex(index.union(df.index)).ffill().reindex(index)
    return daily.rename("rf_daily")


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
