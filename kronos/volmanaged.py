"""Volatility-managed portfolios: the published constructions DESIGN29
replicates before KRONOS's own overlay is tested.

* Moreira & Muir (2017): f^σ_t = (c / RV²_{t-1}) f_t, c set on the full sample
  so std(f^σ) = std(f); spanning regression f^σ = α + β f + ε.
* Cederburg, O'Doherty, Wang & Yan (2020): the real-time combination of the
  original and managed factor (expanding window from K months, mean-variance
  weights at risk aversion γ, position |y_t| <= cap), against the real-time
  original factor alone; Jobson-Korkie (1981) test of the Sharpe difference.
* Liu, Tang & Zhou (2019): the managed factor with a real-time c_t in place of
  the full-sample constant.

All inputs are monthly Series on a PeriodIndex; RV² is kronos.factors.monthly_rv.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def ols(y: np.ndarray, X: np.ndarray, cov: str = "hc0", lags: int = 0) -> dict:
    """OLS with White (hc0) or Newey-West (nw, Bartlett kernel) covariance."""
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    if cov == "hc0":
        S = (X * e[:, None]).T @ (X * e[:, None])
    elif cov == "nw":
        u = X * e[:, None]
        S = u.T @ u
        for L in range(1, lags + 1):
            w = 1.0 - L / (lags + 1.0)
            G = u[L:].T @ u[:-L]
            S += w * (G + G.T)
    else:
        raise ValueError(cov)
    V = XtX_inv @ S @ XtX_inv
    r2 = 1.0 - (e @ e) / float(((y - y.mean()) ** 2).sum())
    return {"coef": b, "se": np.sqrt(np.diag(V)), "resid": e, "r2": r2, "n": n}


def _scaled(f: pd.Series, rv: pd.Series) -> tuple[pd.Series, pd.Series]:
    """(f_t, 1/RV²_{t-1}) over the months where both exist."""
    prev = rv.copy()
    prev.index = rv.index + 1                 # RV² of month t-1, known at t's start
    df = pd.concat([f, 1.0 / prev], axis=1, keys=["f", "inv"]).dropna()
    return df["f"], df["inv"]


def mm_managed(f: pd.Series, rv: pd.Series) -> tuple[pd.Series, float]:
    """Full-sample Moreira-Muir managed factor over the months where both f_t
    and RV²_{t-1} exist; returns (f^σ, c)."""
    fx, inv = _scaled(f, rv)
    raw = fx * inv
    c = float(fx.std(ddof=1) / raw.std(ddof=1))
    return c * raw, c


def spanning(managed: pd.Series, f: pd.Series, cov: str = "hc0", lags: int = 0) -> dict:
    """α (annualized, ×12), its SE, β, N, R², and MM's 'rmse' (monthly rmse ×12)."""
    idx = managed.index.intersection(f.index)
    y = managed.loc[idx].to_numpy()
    X = np.column_stack([np.ones(len(idx)), f.loc[idx].to_numpy()])
    r = ols(y, X, cov, lags)
    k = X.shape[1]
    rmse = float(np.sqrt(r["resid"] @ r["resid"] / (len(y) - k)))
    return {"alpha": 12 * r["coef"][0], "se": 12 * r["se"][0], "beta": r["coef"][1],
            "n": r["n"], "r2": r["r2"], "rmse": 12 * rmse,
            "span": [str(idx[0]), str(idx[-1])]}


def sharpe(x: pd.Series | np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(12) * x.mean() / x.std(ddof=1))


def jobson_korkie(a: np.ndarray, b: np.ndarray) -> float:
    """Two-sided p-value for SR(a) = SR(b) (Jobson & Korkie 1981, monthly moments)."""
    T = len(a)
    mi, mj = a.mean(), b.mean()
    si, sj = a.std(ddof=1), b.std(ddof=1)
    sij = np.cov(a, b, ddof=1)[0, 1]
    theta = (2 * si**2 * sj**2 - 2 * si * sj * sij + 0.5 * mi**2 * sj**2
             + 0.5 * mj**2 * si**2 - (mi * mj / (si * sj)) * sij**2) / T
    z = (sj * mi - si * mj) / np.sqrt(theta)
    return float(2 * stats.norm.sf(abs(z)))


def realtime_combination(f: pd.Series, rv: pd.Series, K: int = 120,
                         gamma: float = 5.0, cap: float = 5.0) -> dict:
    """Cederburg et al. Table 5 Panel A, one factor. For each out-of-sample
    month t (the (K+1)-th onward) the training window is every month before t:
      c_t      matches the variances of f/RV²_{-1} and f over the window;
      (xσ, x)  = Σ̂⁻¹ μ̂ / γ  on (c_t f/RV²_{-1}, f) over the window;
      y_t      = xσ c_t / RV²_{t-1} + x,  clipped to |y_t| <= cap;
    the original-only strategy uses x_t = μ̂ / (γ σ̂²), clipped the same way.
    Returns the two out-of-sample excess-return series and their positions."""
    fs, inv = _scaled(f, rv)
    fx, inv_rv = fs.to_numpy(), inv.to_numpy()
    sc = fx * inv_rv                          # f_t / RV²_{t-1}
    T = len(fx)
    comb, orig, y_c, y_o = [], [], [], []
    for t in range(K, T):
        ftr, rtr = fx[:t], sc[:t]
        c = ftr.std(ddof=1) / rtr.std(ddof=1)
        Z = np.column_stack([c * rtr, ftr])
        w = np.linalg.solve(np.cov(Z, rowvar=False, ddof=1), Z.mean(axis=0)) / gamma
        y = float(np.clip(w[0] * c * inv_rv[t] + w[1], -cap, cap))
        x = float(np.clip(ftr.mean() / (gamma * ftr.var(ddof=1)), -cap, cap))
        y_c.append(y)
        y_o.append(x)
        comb.append(y * fx[t])
        orig.append(x * fx[t])
    idx = fs.index[K:]
    return {"combination": pd.Series(comb, index=idx), "original": pd.Series(orig, index=idx),
            "y_combination": pd.Series(y_c, index=idx), "y_original": pd.Series(y_o, index=idx)}


def realtime_c_managed(f: pd.Series, rv: pd.Series, K: int = 120) -> pd.Series:
    """The managed factor with c_t estimated on the months before t only
    (expanding from K months): the look-ahead-free version of f^σ."""
    fs, inv = _scaled(f, rv)
    fx = fs.to_numpy()
    sc = fx * inv.to_numpy()
    out = [sc[t] * fx[:t].std(ddof=1) / sc[:t].std(ddof=1) for t in range(K, len(fx))]
    return pd.Series(out, index=fs.index[K:])


def max_drawdown(excess: pd.Series, rf: pd.Series) -> float:
    """Maximum drawdown of a total-return investor: NAV = Π(1 + excess + rf)."""
    nav = (1.0 + excess + rf.reindex(excess.index)).cumprod()
    return float((nav / nav.cummax() - 1.0).min())
