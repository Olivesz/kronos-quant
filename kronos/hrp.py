"""Hierarchical Risk Parity (Lopez de Prado, 2016).

No matrix inversion: correlation distance -> single-linkage tree ->
quasi-diagonalization -> recursive bisection with inverse-variance splits.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import squareform


def _corr_from_cov(cov: np.ndarray) -> np.ndarray:
    d = np.sqrt(np.diag(cov))
    corr = cov / np.outer(d, d)
    return np.clip(corr, -1.0, 1.0)


def quasi_diag_order(cov: pd.DataFrame) -> list[int]:
    corr = _corr_from_cov(cov.to_numpy())
    dist = np.sqrt(0.5 * (1 - corr))
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    Z = linkage(condensed, method="single")
    return list(leaves_list(Z))


def _cluster_var(cov: np.ndarray, idx: list[int]) -> float:
    sub = cov[np.ix_(idx, idx)]
    ivp = 1.0 / np.diag(sub)
    ivp /= ivp.sum()
    return float(ivp @ sub @ ivp)


def hrp_weights(cov: pd.DataFrame) -> pd.Series:
    order = quasi_diag_order(cov)
    C = cov.to_numpy()
    w = pd.Series(1.0, index=order, dtype=float)
    clusters = [order]
    while clusters:
        nxt = []
        for cl in clusters:
            if len(cl) <= 1:
                continue
            mid = len(cl) // 2
            left, right = cl[:mid], cl[mid:]
            vl, vr = _cluster_var(C, left), _cluster_var(C, right)
            alpha = 1 - vl / (vl + vr)
            w[left] *= alpha
            w[right] *= 1 - alpha
            nxt += [left, right]
        clusters = nxt
    out = pd.Series(0.0, index=cov.index)
    for pos, weight in w.items():
        out.iloc[pos] = weight
    return out / out.sum()
