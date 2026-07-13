"""KRONOS-REFLEX: Hawkes self-excitation / market endogeneity (DESIGN10.md).

Exponential-kernel Hawkes:  lambda(t) = mu + sum_{t_i<t} alpha e^{-beta(t-t_i)}.
Branching ratio n = alpha/beta = expected aftershocks per event.
MLE via the Ogata recursion; stability n<1 via a logit parameterization;
simulation via Ogata thinning. Finite-sample bias measured by the gate's
recovery curve and used to debias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

# ---------------------------------------------------------------------------
# log-likelihood (Ogata recursion) and MLE
# ---------------------------------------------------------------------------

def _hawkes_nll(params: np.ndarray, t: np.ndarray, T: float) -> float:
    log_mu, logit_n, log_beta = params
    mu = np.exp(log_mu)
    beta = np.exp(log_beta)
    n = 1.0 / (1.0 + np.exp(-logit_n))           # in (0,1)
    alpha = n * beta
    # recursion for A_i = sum_{j<i} exp(-beta (t_i - t_j))
    A = 0.0
    ll = 0.0
    prev = t[0]
    ll += np.log(mu)                              # first event: A_0 = 0
    for i in range(1, len(t)):
        A = np.exp(-beta * (t[i] - prev)) * (1.0 + A)
        lam = mu + alpha * A
        if lam <= 0:
            return 1e12
        ll += np.log(lam)
        prev = t[i]
    # compensator integral
    comp = mu * T + n * np.sum(1.0 - np.exp(-beta * (T - t)))
    return -(ll - comp)


def fit_hawkes(times: np.ndarray, T: float | None = None,
               n_starts: int = 4, seed: int = 0) -> dict:
    """Returns dict(mu, alpha, beta, n, branching_timescale, ll)."""
    t = np.sort(np.asarray(times, dtype=float))
    if T is None:
        T = t[-1] + 1.0
    if len(t) < 20:
        return {"n": np.nan, "mu": np.nan, "beta": np.nan, "ll": np.nan}
    rate0 = len(t) / T
    rng = np.random.default_rng(seed)
    best = None
    for s in range(n_starts):
        x0 = np.array([np.log(rate0 * (0.5 + rng.random())),
                       rng.uniform(-1.0, 1.0),
                       np.log(1.0 / (5 + 20 * rng.random()))])
        try:
            res = minimize(_hawkes_nll, x0, args=(t, T), method="Nelder-Mead",
                           options={"maxiter": 2000, "xatol": 1e-4, "fatol": 1e-4})
            if best is None or res.fun < best.fun:
                best = res
        except Exception:
            continue
    if best is None:
        return {"n": np.nan, "mu": np.nan, "beta": np.nan, "ll": np.nan}
    log_mu, logit_n, log_beta = best.x
    n = 1.0 / (1.0 + np.exp(-logit_n))
    beta = np.exp(log_beta)
    return {"mu": float(np.exp(log_mu)), "beta": float(beta),
            "alpha": float(n * beta), "n": float(n),
            "timescale": float(1.0 / beta), "ll": float(-best.fun),
            "n_events": len(t)}


# ---------------------------------------------------------------------------
# simulation (Ogata thinning, exponential kernel)
# ---------------------------------------------------------------------------

def simulate_hawkes(mu: float, n: float, beta: float, T: float,
                    seed: int = 0) -> np.ndarray:
    alpha = n * beta
    rng = np.random.default_rng(seed)
    t = 0.0
    S = 0.0           # current excitation sum (decays between events)
    out = []
    while t < T:
        M = mu + S
        if M <= 0:
            break
        w = rng.exponential(1.0 / M)
        t += w
        if t >= T:
            break
        S *= np.exp(-beta * w)
        if rng.random() <= (mu + S) / M:
            out.append(t)
            S += alpha
    return np.array(out)


# ---------------------------------------------------------------------------
# events from returns
# ---------------------------------------------------------------------------

def exceedance_times(series: pd.Series, q: float = 0.95) -> np.ndarray:
    """Day-indices (0-based) where |series| exceeds its global q-quantile."""
    a = series.abs().dropna()
    thr = a.quantile(q)
    mask = a > thr
    pos = np.flatnonzero(mask.to_numpy())
    return pos.astype(float)


def raw_and_deformed_events(close: pd.Series, gkvar: pd.Series,
                            q: float = 0.95) -> dict:
    """raw = |return| exceedances; deformed = |return / lagged vol|
    exceedances (vol-clock-adjusted surprises). Same count, different timing."""
    r = np.log(close / close.shift(1))
    sig = np.sqrt(gkvar.rolling(5).mean().shift(1))
    z = r / sig
    idx = r.dropna().index.intersection(z.dropna().index)
    r, z = r.reindex(idx), z.reindex(idx)
    return {"raw": exceedance_times(r, q), "deformed": exceedance_times(z, q),
            "T": float(len(idx))}


# ---------------------------------------------------------------------------
# recovery curve (finite-sample debiasing)
# ---------------------------------------------------------------------------

def recovery_curve(n_grid=(0.2, 0.4, 0.6, 0.8), T: float = 4000.0,
                   rate: float = 0.05, n_rep: int = 12, seed: int = 0) -> dict:
    """Mean fitted n at each true n (for debiasing real estimates)."""
    out = {}
    for nt in n_grid:
        beta = 0.2
        mu = rate * (1 - nt)                       # baseline rate so total ~ rate*T
        ests = []
        for r in range(n_rep):
            ev = simulate_hawkes(mu, nt, beta, T, seed=seed + r)
            if len(ev) > 30:
                ests.append(fit_hawkes(ev, T, seed=r)["n"])
        out[nt] = float(np.nanmean(ests)) if ests else np.nan
    return out


def debias(n_hat: float, curve: dict) -> float:
    """Invert the recovery curve (piecewise-linear) to debias n_hat."""
    xs = np.array(sorted(curve))                   # true n
    ys = np.array([curve[x] for x in xs])          # mean fitted n
    if not np.isfinite(n_hat):
        return np.nan
    return float(np.clip(np.interp(n_hat, ys, xs), 0.0, 0.999))
