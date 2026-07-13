"""KRONOS-LAWS: invariance screens (DESIGN4.md, pre-registered).

L1  One-Clock: vol-standardized returns lose their tails, their hallucinated
    regimes, and their asset identity (universal distribution).
L2  Parameter-free kurtosis law: kurt = 3*exp(4*Var(log sigma)), with
    Var(log sigma) measured noise-robustly from lag-1 autocovariance.
L3  Multifractal universality: one intermittency parameter lambda^2 across
    all assets.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# L1: one-clock deformation
# ---------------------------------------------------------------------------

def standardized_returns(close: pd.DataFrame, gkvar: pd.DataFrame,
                         smooth: int = 1, lag: int = 0) -> pd.DataFrame:
    """z_t = r_t / GK vol.

    lag=0: same-day clock (the contemporaneous MDH statement) — absorbs
           everything the daily range can see, including jumps.
    lag=1: yesterday's clock — removes only the PREDICTABLE clock, so
           surviving tails are genuine surprises (jumps, vol innovations).
           This is the contagion-relevant deformation.
    """
    r = np.log(close / close.shift(1))
    v = gkvar.rolling(smooth).mean() if smooth > 1 else gkvar
    if lag > 0:
        v = v.shift(lag)
    z = r / np.sqrt(v)
    return z.replace([np.inf, -np.inf], np.nan)


def tail_report(x: pd.Series) -> dict:
    """Kurtosis + fitted Student-t nu for one series."""
    x = x.dropna()
    x = x[np.abs(x - x.mean()) < 12 * x.std()]      # guard data errors only
    kurt = float(x.kurtosis()) + 3.0                # raw kurtosis
    try:
        nu, loc, sc = stats.t.fit(x.to_numpy())
        nu = float(min(nu, 200.0))
    except Exception:
        nu = np.nan
    return {"kurt": kurt, "nu": nu, "n": len(x)}


def universality_collapse(z: pd.DataFrame, n_pairs: int = 300,
                          seed: int = 42) -> dict:
    """Pairwise two-sample KS distances between standardized assets,
    compared with the within-asset split-half KS (the sampling floor)."""
    rng = np.random.default_rng(seed)
    cols = list(z.columns)
    cross = []
    for _ in range(n_pairs):
        a, b = rng.choice(len(cols), 2, replace=False)
        xa = z[cols[a]].dropna().to_numpy()
        xb = z[cols[b]].dropna().to_numpy()
        # subsample to half-length so the KS sampling floor matches the
        # within-asset split-half benchmark exactly
        n2 = min(len(xa), len(xb)) // 2
        xa = rng.choice(xa, n2, replace=False)
        xb = rng.choice(xb, n2, replace=False)
        xa = (xa - xa.mean()) / xa.std()            # compare SHAPES
        xb = (xb - xb.mean()) / xb.std()
        cross.append(stats.ks_2samp(xa, xb).statistic)
    within = []
    for c in cols:
        x = z[c].dropna().to_numpy()
        x = (x - x.mean()) / x.std()
        h = rng.permutation(len(x))
        within.append(stats.ks_2samp(x[h[:len(x)//2]], x[h[len(x)//2:]]).statistic)
    return {"cross_ks_median": float(np.median(cross)),
            "cross_ks_q90": float(np.percentile(cross, 90)),
            "within_ks_median": float(np.median(within)),
            "ratio": float(np.median(cross) / np.median(within))}


# ---------------------------------------------------------------------------
# L2: parameter-free kurtosis law
# ---------------------------------------------------------------------------

def logvol_signal_variance(gkvar: pd.Series) -> float:
    """Var(log sigma) measured noise-robustly: the GK proxy's multiplicative
    measurement noise is serially independent, so the lag-1 autocovariance
    of log vol is pure signal; divide by the signal's lag-1 autocorrelation
    (estimated from the lag-1/lag-2 covariance ratio, geometric
    extrapolation) to recover the full signal variance."""
    lv = 0.5 * np.log(gkvar.dropna().to_numpy())
    lv = lv - lv.mean()
    c1 = float(np.mean(lv[1:] * lv[:-1]))
    c2 = float(np.mean(lv[2:] * lv[:-2]))
    if c1 <= 0 or c2 <= 0 or c2 >= c1:
        return max(c1, 0.0)
    rho = c2 / c1                                   # signal AR(1)-ish decay
    return float(c1 / rho)                          # extrapolate back to lag 0


def kurtosis_law(close: pd.Series, gkvar: pd.Series) -> dict:
    """Predicted kurt = 3*exp(4*s2) vs realized kurtosis of returns."""
    r = np.log(close / close.shift(1)).dropna()
    r = r[np.abs(r - r.mean()) < 12 * r.std()]
    s2 = logvol_signal_variance(gkvar)
    pred = 3.0 * np.exp(4.0 * s2)
    real = float(r.kurtosis()) + 3.0
    return {"s2": s2, "kurt_pred": float(pred), "kurt_real": real}


# ---------------------------------------------------------------------------
# L3: multifractal scaling of returns
# ---------------------------------------------------------------------------

def mrw_lambda2(close: pd.Series, delta_max: int = 50,
                qs=(0.5, 1.0, 1.5, 2.0, 2.5, 3.0)) -> dict:
    """Fit zeta(q) from moment scaling of |log returns|, then the MRW form
    zeta(q) = (1/2 + lambda^2) q - (lambda^2/2) q^2 by least squares."""
    lr = np.log(close / close.shift(1)).dropna().to_numpy()
    lr = lr - lr.mean()
    deltas = np.unique(np.round(np.exp(np.linspace(0, np.log(delta_max), 14))
                                ).astype(int))
    logd = np.log(deltas.astype(float))
    zeta = []
    for q in qs:
        m = []
        for d in deltas:
            agg = np.add.reduceat(lr, np.arange(0, len(lr) - d, d))
            m.append(np.mean(np.abs(agg) ** q))
        A = np.column_stack([np.ones_like(logd), logd])
        coef, *_ = np.linalg.lstsq(A, np.log(m), rcond=None)
        zeta.append(coef[1])
    zeta = np.array(zeta)
    qa = np.array(qs)
    # least squares for (a, lambda2) in zeta = a*q - (lambda2/2) q^2,
    # a = 1/2 + lambda2
    X = np.column_stack([qa, -0.5 * qa ** 2])
    coef, *_ = np.linalg.lstsq(X, zeta, rcond=None)
    a_hat, lam2 = float(coef[0]), float(coef[1])
    resid = float(np.abs(zeta - X @ coef).max())
    return {"zeta": zeta.tolist(), "qs": list(qs), "lambda2": lam2,
            "a": a_hat, "fit_resid": resid}


# ---------------------------------------------------------------------------
# simulation worlds for the L2 gate
# ---------------------------------------------------------------------------

def simulate_sv_world(T: int, s2: float = 0.12, rho: float = 0.98,
                      jumps: float = 0.0, seed: int = 0) -> dict:
    """Lognormal-SV returns with known Var(log sigma)=s2; optional jumps.
    Returns dict(close, gkvar, true_kurt_sv) — gkvar is a noisy proxy."""
    rng = np.random.default_rng(seed)
    # AR(1) log-vol with stationary variance s2
    eta = np.sqrt(s2 * (1 - rho ** 2))
    lv = np.zeros(T)
    for t in range(1, T):
        lv[t] = rho * lv[t - 1] + eta * rng.normal()
    sigma = np.exp(lv) * 0.01
    r = sigma * rng.normal(size=T)
    if jumps > 0:
        jmask = rng.random(T) < 0.01
        r = r + jmask * rng.normal(0, jumps * 0.01, T)
    close = pd.Series(100 * np.exp(np.cumsum(r)),
                      index=pd.bdate_range("2012-01-02", periods=T))
    gk = sigma ** 2 * rng.gamma(3.7, 1 / 3.7, T)
    gkvar = pd.Series(gk, index=close.index)
    return {"close": close, "gkvar": gkvar,
            "true_kurt_sv": 3 * np.exp(4 * s2)}
