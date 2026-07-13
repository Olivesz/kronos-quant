"""KRONOS-ARROW: entropy production — the general arrow of time (ATLAS V.2).

The physics measure of irreversibility: entropy production rate
    EP = (1/n) * KL( P(x_1..x_n)  ||  P(x_n..x_1) )
over n-step path segments. EP = 0 iff the process is statistically
time-reversible. Stationary GAUSSIAN processes are always reversible
(symmetric autocovariance), so any EP > 0 in returns/vol is genuinely
non-Gaussian, nonlinear arrow-of-time structure — the general object of
which the Zumbach statistic (SURGE S2) is one weak projection.

Estimator: symbolize the series (quantile bins on increments), count
forward n-grams and their reversals, plug-in KL with pseudocounts, minus
a circular-shift null (which preserves marginals and approximate
stationarity but breaks the forward-backward coupling consistently).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LN2 = np.log(2.0)


def symbolize(x: np.ndarray, n_bins: int = 3) -> np.ndarray:
    """Quantile-bin a continuous series into symbols 0..n_bins-1."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    qs = np.quantile(x, np.linspace(0, 1, n_bins + 1)[1:-1])
    return np.digitize(x, qs)


def ngram_ep(symbols: np.ndarray, n: int = 3, alpha: float = 0.5) -> float:
    """KL(forward n-grams || reversed n-grams) per step, in BITS.

    alpha = Dirichlet pseudocount per cell (regularizes empty reversals).
    Note p_rev(g) = p_fwd(reverse(g)) estimated from the SAME sample, so
    the statistic is exactly zero for palindromic-symmetric counts.
    """
    s = np.asarray(symbols, dtype=np.int64)
    T = len(s) - n + 1
    if T < 50:
        return 0.0
    base = int(s.max()) + 1
    # encode n-grams and their reversals as integers
    codes_f = np.zeros(T, dtype=np.int64)
    codes_r = np.zeros(T, dtype=np.int64)
    for i in range(n):
        codes_f += s[i:i + T] * (base ** i)
        codes_r += s[i:i + T] * (base ** (n - 1 - i))
    n_cells = base ** n
    cf = np.bincount(codes_f, minlength=n_cells).astype(float)
    # reversed-path distribution = distribution of reversed codes
    cr = np.bincount(codes_r, minlength=n_cells).astype(float)
    pf = (cf + alpha) / (cf + alpha).sum()
    pr = (cr + alpha) / (cr + alpha).sum()
    kl = float(np.sum(pf * np.log(pf / pr))) / LN2
    return kl / n          # per step


def ep_with_null(x: np.ndarray, n: int = 3, n_bins: int = 3,
                 n_null: int = 200, block: int = 126, seed: int = 0) -> dict:
    """EP of the series vs a block-reversal null band.

    Null: time-reverse each block IN PLACE *with probability 1/2* (block
    order kept, boundaries randomly offset per surrogate). Under true
    reversibility this is exactly distribution-preserving (correct size);
    under irreversibility the pooled half-forward/half-backward n-gram
    population is symmetric, so the surrogate's arrow cancels (power).
    Deterministically reversing EVERY block — the first attempt — merely
    mirrors a strong arrow into an equally strong anti-arrow and has no
    power; IAAFT surrogates fail differently (they kill vol clustering and
    understate the null variance). Both failure modes are encoded in the
    gate."""
    rng = np.random.default_rng(seed)
    sym = symbolize(x, n_bins)
    ep = ngram_ep(sym, n)
    T = len(sym)
    nulls = np.empty(n_null)
    for i in range(n_null):
        off = int(rng.integers(0, block))
        out = sym.copy()
        edges = list(range(off, T, block))
        if off > 0:
            edges = [0] + edges
        edges.append(T)
        for a, b in zip(edges[:-1], edges[1:]):
            if rng.random() < 0.5:
                out[a:b] = out[a:b][::-1]
        nulls[i] = ngram_ep(out, n)
    return {"ep_bits": float(ep),
            "null_mean": float(nulls.mean()),
            "null_p95": float(np.percentile(nulls, 95)),
            "ep_net": float(max(ep - nulls.mean(), 0.0)),
            "significant": bool(ep > np.percentile(nulls, 95))}


def series_for_ep(close: pd.Series, gkvar: pd.Series) -> dict:
    """The three series whose reversibility we interrogate."""
    r = np.log(close / close.shift(1)).dropna()
    lv = (0.5 * np.log(gkvar.where(gkvar > 0))).rolling(5).mean()
    dlv = lv.diff().dropna()
    z = (r / np.sqrt(gkvar.reindex(r.index))).dropna()   # deformed returns
    return {"returns": r.to_numpy(), "dlogvol": dlv.to_numpy(),
            "deformed": z.to_numpy()}
