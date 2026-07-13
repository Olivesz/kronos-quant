"""Covariance estimation: EWMA sample covariance with Ledoit-Wolf-style
shrinkage toward a constant-correlation target. Closed form, no optimizer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ewma_cov(rets: pd.DataFrame, halflife: int) -> np.ndarray:
    lam = np.exp(-np.log(2) / halflife)
    X = rets.to_numpy()
    T, N = X.shape
    w = lam ** np.arange(T - 1, -1, -1)
    w /= w.sum()
    mu = w @ X
    Xc = X - mu
    return (Xc * w[:, None]).T @ Xc


def constant_corr_target(S: np.ndarray) -> np.ndarray:
    d = np.sqrt(np.diag(S))
    corr = S / np.outer(d, d)
    n = len(S)
    rbar = (corr.sum() - n) / (n * (n - 1))
    F = rbar * np.outer(d, d)
    np.fill_diagonal(F, d ** 2)
    return F


def shrunk_cov(rets: pd.DataFrame, halflife: int, window: int) -> pd.DataFrame:
    """EWMA cov shrunk toward constant correlation (Ledoit-Wolf intensity)."""
    sub = rets.iloc[-window:]
    S = ewma_cov(sub, halflife)
    F = constant_corr_target(S)

    # shrinkage intensity via the standard pi/gamma estimate on the sample
    X = sub.to_numpy()
    T, N = X.shape
    Xc = X - X.mean(axis=0)
    S_plain = Xc.T @ Xc / T
    # pi-hat: variance of covariance entries
    y = Xc[:, :, None] * Xc[:, None, :]          # (T, N, N)
    pi_mat = ((y - S_plain) ** 2).mean(axis=0)
    pi_hat = pi_mat.sum()
    gamma_hat = ((constant_corr_target(S_plain) - S_plain) ** 2).sum()
    kappa = pi_hat / gamma_hat if gamma_hat > 1e-18 else 0.0
    delta = float(np.clip(kappa / T, 0.0, 1.0))

    Sigma = delta * F + (1 - delta) * S
    # symmetrize + variance floor for numerical safety
    Sigma = (Sigma + Sigma.T) / 2
    eps = 1e-10
    Sigma[np.diag_indices(N)] = np.maximum(np.diag(Sigma), eps)
    return pd.DataFrame(Sigma, index=rets.columns, columns=rets.columns)
