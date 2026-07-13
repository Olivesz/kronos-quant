"""Overfitting forensics (KRONOS-X, Q6).

The tools that decide whether our results are real:
  * Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) — P(true SR > 0)
    after adjusting for non-normality, track length, and the number of
    strategy configurations tried.
  * PBO via CSCV (Bailey, Borwein, Lopez de Prado, Zhu 2017) — probability
    that the in-sample winner underperforms the median out-of-sample.
  * Stationary bootstrap (Politis & Romano 1994) — Sharpe confidence
    intervals that respect serial dependence.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import norm

EULER_GAMMA = 0.5772156649


# ---------------------------------------------------------------------------
# Deflated Sharpe Ratio
# ---------------------------------------------------------------------------

def expected_max_sharpe(n_trials: int, sr_std_across_trials: float) -> float:
    """E[max SR] of n_trials zero-skill strategies (daily units)."""
    if n_trials <= 1:
        return 0.0
    z1 = norm.ppf(1 - 1.0 / n_trials)
    z2 = norm.ppf(1 - 1.0 / (n_trials * np.e))
    return sr_std_across_trials * ((1 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)


def deflated_sharpe(rets: pd.Series, n_trials: int,
                    sr_std_across_trials: float | None = None,
                    trial_srs: np.ndarray | None = None) -> dict:
    """DSR = P(true SR > 0 | observed SR, trials). All in daily units."""
    r = rets.dropna().to_numpy()
    T = len(r)
    sr = r.mean() / r.std()
    skew = float(pd.Series(r).skew())
    kurt = float(pd.Series(r).kurtosis()) + 3.0   # raw kurtosis
    if trial_srs is not None and len(trial_srs) > 1:
        sr_std = float(np.std(trial_srs))
    else:
        sr_std = sr_std_across_trials if sr_std_across_trials is not None else 0.0
    sr0 = expected_max_sharpe(n_trials, sr_std)
    denom = np.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr ** 2, 1e-12))
    z = (sr - sr0) * np.sqrt(T - 1) / denom
    return {"sr_daily": float(sr), "sr_annual": float(sr * np.sqrt(252)),
            "sr0_daily": float(sr0), "sr0_annual": float(sr0 * np.sqrt(252)),
            "dsr": float(norm.cdf(z)), "z": float(z),
            "skew": skew, "kurt": kurt, "n_trials": int(n_trials), "T": T}


# ---------------------------------------------------------------------------
# PBO via combinatorially symmetric cross-validation
# ---------------------------------------------------------------------------

def cscv_pbo(returns_matrix: np.ndarray, n_blocks: int = 16,
             max_combos: int = 12870, seed: int = 42) -> dict:
    """returns_matrix: (T, V) daily returns of V strategy variants.

    Splits T into n_blocks; for every half/half combination, ranks variants
    in-sample, then asks where the IS winner lands out-of-sample.
    PBO = fraction of splits where the IS winner is below the OOS median.
    """
    T, V = returns_matrix.shape
    blocks = np.array_split(np.arange(T), n_blocks)
    # per-block sufficient statistics per variant
    bsum = np.array([returns_matrix[b].sum(axis=0) for b in blocks])     # (B,V)
    bsq = np.array([(returns_matrix[b] ** 2).sum(axis=0) for b in blocks])
    bn = np.array([len(b) for b in blocks], dtype=float)

    combos = list(combinations(range(n_blocks), n_blocks // 2))
    if len(combos) > max_combos:
        rng = np.random.default_rng(seed)
        combos = [combos[i] for i in
                  rng.choice(len(combos), max_combos, replace=False)]
    M = np.zeros((len(combos), n_blocks))
    for i, c in enumerate(combos):
        M[i, list(c)] = 1.0

    def sharpe_from_stats(mask):
        n = mask @ bn                       # (C,)
        s = mask @ bsum                     # (C, V)
        ss = mask @ bsq
        mean = s / n[:, None]
        var = ss / n[:, None] - mean ** 2
        var = np.maximum(var, 1e-18)
        return mean / np.sqrt(var)

    sr_is = sharpe_from_stats(M)
    sr_oos = sharpe_from_stats(1.0 - M)
    best_is = sr_is.argmax(axis=1)                          # (C,)
    oos_of_best = sr_oos[np.arange(len(combos)), best_is]
    # relative OOS rank of the IS winner
    ranks = (sr_oos < oos_of_best[:, None]).mean(axis=1)
    ranks = np.clip(ranks, 1e-6, 1 - 1e-6)
    logits = np.log(ranks / (1 - ranks))
    return {"pbo": float((ranks <= 0.5).mean()),
            "logits": logits.tolist(),
            "n_combos": len(combos), "n_variants": V,
            "median_oos_rank": float(np.median(ranks))}


# ---------------------------------------------------------------------------
# stationary bootstrap
# ---------------------------------------------------------------------------

def stationary_bootstrap_indices(T: int, mean_block: float,
                                 rng: np.random.Generator) -> np.ndarray:
    p = 1.0 / mean_block
    idx = np.empty(T, dtype=np.int64)
    t = 0
    while t < T:
        start = rng.integers(0, T)
        L = rng.geometric(p)
        L = min(L, T - t)
        idx[t:t + L] = (start + np.arange(L)) % T
        t += L
    return idx


def bootstrap_sharpe_ci(rets: pd.Series, n_boot: int = 2000,
                        mean_block: float = 63.0, seed: int = 42) -> dict:
    r = rets.dropna().to_numpy()
    T = len(r)
    rng = np.random.default_rng(seed)
    srs = np.empty(n_boot)
    for i in range(n_boot):
        rb = r[stationary_bootstrap_indices(T, mean_block, rng)]
        srs[i] = rb.mean() / rb.std() * np.sqrt(252)
    return {"sr_point": float(r.mean() / r.std() * np.sqrt(252)),
            "ci_lo": float(np.percentile(srs, 2.5)),
            "ci_hi": float(np.percentile(srs, 97.5)),
            "p_sr_below_0": float((srs <= 0).mean())}


def bootstrap_equity_fan(rets: pd.Series, n_boot: int = 400,
                         mean_block: float = 63.0, seed: int = 42,
                         pcts=(5, 25, 50, 75, 95)) -> dict:
    """Percentile envelope of resampled cumulative-return paths."""
    r = rets.dropna().to_numpy()
    T = len(r)
    rng = np.random.default_rng(seed)
    navs = np.empty((n_boot, T))
    for i in range(n_boot):
        rb = r[stationary_bootstrap_indices(T, mean_block, rng)]
        navs[i] = np.cumprod(1 + rb)
    out = {f"p{p}": np.percentile(navs, p, axis=0).tolist() for p in pcts}
    out["dates"] = [str(d.date()) for d in rets.dropna().index]
    return out


# ---------------------------------------------------------------------------
# variant family for CSCV (pure algebra on stored sleeve returns)
# ---------------------------------------------------------------------------

def build_variant_family(sleeves: pd.DataFrame, vol_targets=(0.08, 0.10, 0.13, 0.16),
                         n_blend_grid: int = 4) -> tuple[np.ndarray, list[str]]:
    """Variants = simplex grid of sleeve blends x vol-target scalings.

    Each variant is causal by construction: sleeve returns were generated
    walk-forward, blending/vol-scaling cannot peek ahead."""
    cols = list(sleeves.columns)
    K = len(cols)
    R = sleeves.to_numpy()
    # simplex grid with resolution n_blend_grid
    grids = []
    def rec(prefix, left, depth):
        if depth == K - 1:
            grids.append(prefix + [left])
            return
        for v in range(left + 1):
            rec(prefix + [v], left - v, depth + 1)
    rec([], n_blend_grid, 0)
    blends = np.array(grids, dtype=float) / n_blend_grid    # (n_simplex, K)

    variants, names = [], []
    ann = np.sqrt(252)
    for b in blends:
        base = R @ b
        s = pd.Series(base, index=sleeves.index)
        ewvol = s.ewm(halflife=21).std().shift(1) * ann
        for vt in vol_targets:
            scale = (vt / ewvol).clip(upper=1.0).fillna(1.0).to_numpy()
            variants.append(base * scale)
            names.append(f"b{np.round(b,2).tolist()}-vt{vt}")
    return np.column_stack(variants), names
