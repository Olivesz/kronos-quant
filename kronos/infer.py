"""Formal inference for forecast comparison (KRONOS-X²).

* Amisano-Giacomini (2007) test for comparing density forecasts: a t-test on
  the mean log-score differential with HAC (Newey-West) long-run variance.
  (With unit weights this is the unconditional AG test; mechanically a
  Diebold-Mariano test applied to log scores.)

* Hansen-Lunde-Nason (2011) Model Confidence Set: the subset of models that
  contains the true best model with probability >= 1-alpha, found by
  iterated elimination with the Tmax statistic under a stationary-bootstrap
  null. Works on any loss matrix (we use negative log-scores or QLIKE).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

from kronos.forensics import stationary_bootstrap_indices


def amisano_giacomini(logscore_a: np.ndarray, logscore_b: np.ndarray,
                      h: int = 10) -> dict:
    """Positive stat favors A. d_t = ls_a - ls_b (higher score = better)."""
    d = logscore_a - logscore_b
    d = d[np.isfinite(d)]
    T = len(d)
    dbar = d.mean()
    gamma0 = ((d - dbar) ** 2).mean()
    lrv = gamma0
    for k in range(1, h + 1):
        cov = ((d[k:] - dbar) * (d[:-k] - dbar)).mean()
        lrv += 2 * (1 - k / (h + 1)) * cov
    stat = dbar / np.sqrt(max(lrv, 1e-300) / T)
    return {"stat": float(stat), "p": float(2 * (1 - norm.cdf(abs(stat)))),
            "mean_diff": float(dbar), "T": T}


def model_confidence_set(losses: np.ndarray, names: list[str],
                         alpha: float = 0.10, n_boot: int = 1000,
                         mean_block: float = 63.0, seed: int = 42) -> dict:
    """losses: (T, M), lower is better. Returns the MCS and per-model
    elimination p-values (the level at which each model would survive)."""
    rng = np.random.default_rng(seed)
    T, M = losses.shape
    # precompute bootstrap index sets once (shared across elimination rounds)
    boots = [stationary_bootstrap_indices(T, mean_block, rng)
             for _ in range(n_boot)]

    active = list(range(M))
    pvals = {}
    seq_p = 0.0
    while len(active) > 1:
        L = losses[:, active]                     # (T, m)
        Lbar = L.mean(axis=0)
        dbar_i = Lbar - Lbar.mean()               # vs average of active set

        # bootstrap distribution of recentered t-statistics
        boot_means = np.empty((n_boot, len(active)))
        for b, idx in enumerate(boots):
            boot_means[b] = L[idx].mean(axis=0)
        boot_dev = (boot_means - boot_means.mean(axis=1, keepdims=True)
                    ) - dbar_i[None, :]
        var_i = (boot_dev ** 2).mean(axis=0)
        var_i = np.maximum(var_i, 1e-30)
        t_i = dbar_i / np.sqrt(var_i)
        Tmax = t_i.max()
        Tmax_boot = (boot_dev / np.sqrt(var_i)[None, :]).max(axis=1)
        p = float((Tmax_boot >= Tmax).mean())
        seq_p = max(seq_p, p)

        worst = active[int(np.argmax(t_i))]
        pvals[names[worst]] = seq_p
        if p >= alpha:
            break                                  # all remaining survive
        active.remove(worst)
    for i in active:
        pvals.setdefault(names[i], 1.0)
    mcs = [names[i] for i in active]
    return {"mcs": mcs, "pvals": pvals, "alpha": alpha,
            "best": names[int(np.argmin(losses.mean(axis=0)))]}
