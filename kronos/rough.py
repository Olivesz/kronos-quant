"""Rough volatility analysis (KRONOS-X, Q3b).

Estimates the Hurst exponent of log realized volatility by the
Gatheral-Jaisson-Rosenbaum scaling method: the q-th absolute moment of
log-vol increments over lag Delta scales as Delta^(q*H). If H << 0.5 the
vol process is 'rough'.

Includes an exact fractional-Gaussian-noise simulator (Davies-Harte
circulant embedding) so the estimator is gated against known H.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# estimator
# ---------------------------------------------------------------------------

def scaling_moments(log_vol: np.ndarray, deltas: np.ndarray,
                    qs: tuple = (0.5, 1.0, 1.5, 2.0, 3.0)) -> dict:
    """m(q, Delta) = mean |logvol_{t+D} - logvol_t|^q, plus the fits."""
    x = np.asarray(log_vol, dtype=float)
    x = x[np.isfinite(x)]
    m = np.zeros((len(qs), len(deltas)))
    for j, d in enumerate(deltas):
        inc = np.abs(x[d:] - x[:-d])
        for i, q in enumerate(qs):
            m[i, j] = (inc ** q).mean()
    logd = np.log(deltas.astype(float))
    zeta = np.zeros(len(qs))
    intercepts = np.zeros(len(qs))
    for i in range(len(qs)):
        A = np.column_stack([np.ones_like(logd), logd])
        coef, *_ = np.linalg.lstsq(A, np.log(m[i]), rcond=None)
        intercepts[i], zeta[i] = coef
    # H = slope of zeta_q vs q through the origin
    qarr = np.array(qs)
    H = float((qarr @ zeta) / (qarr @ qarr))
    # monofractality check: residual of the linear fit
    resid = zeta - H * qarr
    return {"H": H, "zeta": zeta, "qs": list(qs), "deltas": deltas.tolist(),
            "log_m": np.log(m), "intercepts": intercepts,
            "monofractal_resid": float(np.abs(resid).max())}


def estimate_hurst(gk_var: pd.Series, smooth: int = 1,
                   delta_max: int = 50) -> dict:
    """H estimate from a daily GK variance series; smooth>1 averages the
    variance over `smooth` days first (reduces measurement noise, biases H
    up — report multiple values and say so)."""
    v = gk_var.dropna()
    if smooth > 1:
        v = v.rolling(smooth).mean().dropna()
    log_vol = 0.5 * np.log(v.to_numpy())
    deltas = np.unique(np.round(np.exp(np.linspace(0, np.log(delta_max), 16))
                                ).astype(int))
    return scaling_moments(log_vol, deltas)


def subwindow_hursts(gk_var: pd.Series, window_years: int = 4,
                     smooth: int = 1) -> list[float]:
    """H per rolling (non-overlapping-ish) subwindow — stability check."""
    v = gk_var.dropna()
    W = window_years * 252
    out = []
    for start in range(0, len(v) - W + 1, W // 2):
        sub = v.iloc[start:start + W]
        out.append(estimate_hurst(sub, smooth=smooth)["H"])
    return out


def block_bootstrap_ci(gk_var: pd.Series, n_boot: int = 300,
                       block: int = 252, smooth: int = 1,
                       seed: int = 42) -> tuple[float, float]:
    """Circular block bootstrap CI for H. Caveat (stated in the dashboard):
    resampling caps dependence at the block length, so this is approximate."""
    rng = np.random.default_rng(seed)
    v = gk_var.dropna().to_numpy()
    T = len(v)
    hs = []
    n_blocks = int(np.ceil(T / block))
    for _ in range(n_boot):
        starts = rng.integers(0, T, n_blocks)
        idx = np.concatenate([(s + np.arange(block)) % T for s in starts])[:T]
        vb = pd.Series(v[idx])
        hs.append(estimate_hurst(vb, smooth=smooth)["H"])
    return float(np.percentile(hs, 2.5)), float(np.percentile(hs, 97.5))


# ---------------------------------------------------------------------------
# exact fGn simulation (Davies-Harte) for the verification gate
# ---------------------------------------------------------------------------

def simulate_fgn(n: int, H: float, seed: int = 42) -> np.ndarray:
    """Fractional Gaussian noise via circulant embedding (exact)."""
    rng = np.random.default_rng(seed)
    k = np.arange(n)
    gamma = 0.5 * (np.abs(k + 1) ** (2 * H) - 2 * np.abs(k) ** (2 * H)
                   + np.abs(k - 1) ** (2 * H))
    c = np.concatenate([gamma, [0.0], gamma[1:][::-1]])
    eig = np.fft.fft(c).real
    eig = np.maximum(eig, 0.0)          # clip tiny negatives from rounding
    m = len(c)
    z = rng.normal(size=m) + 1j * rng.normal(size=m)
    f = np.fft.fft(z * np.sqrt(eig / (2 * m)))
    return np.sqrt(2.0) * f.real[:n]


def simulate_rough_logvol(n: int, H: float, nu: float = 0.3,
                          seed: int = 42) -> np.ndarray:
    """log sigma_t as scaled fractional Brownian motion increments cumsum."""
    fgn = simulate_fgn(n, H, seed)
    return nu * np.cumsum(fgn) / (n ** 0)  # fBm path, scale nu per step
