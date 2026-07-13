"""Random Matrix Theory covariance denoising (KRONOS-X, Q5a).

Marchenko-Pastur: for an NxN correlation matrix estimated from T iid
observations of pure noise, eigenvalues concentrate in
[(1-sqrt(q))^2, (1+sqrt(q))^2] * sigma2, q = N/T. Eigenvalues above the
upper edge carry signal; the bulk is sampling noise. Denoise by replacing
bulk eigenvalues with their average (trace-preserving), keeping signal
eigenvectors intact.

sigma2 is estimated iteratively: after removing the variance explained by
the signal eigenvalues, the residual noise variance shrinks, which moves
the edge, which can reveal more signal — iterate to a fixed point.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def corr_from_cov(cov: np.ndarray) -> np.ndarray:
    d = np.sqrt(np.diag(cov))
    return np.clip(cov / np.outer(d, d), -1, 1)


def mp_edge(q: float, sigma2: float = 1.0) -> float:
    return sigma2 * (1 + np.sqrt(q)) ** 2


def mp_pdf(x: np.ndarray, q: float, sigma2: float) -> np.ndarray:
    lo = sigma2 * (1 - np.sqrt(q)) ** 2
    hi = sigma2 * (1 + np.sqrt(q)) ** 2
    out = np.zeros_like(x)
    inside = (x > lo) & (x < hi)
    xi = x[inside]
    out[inside] = np.sqrt((hi - xi) * (xi - lo)) / (2 * np.pi * q * sigma2 * xi)
    return out


def n_signal_factors(eigvals: np.ndarray, q: float) -> tuple[int, float]:
    """Signal count via de Prado's MP fit: choose sigma2 so the MP density
    matches the empirical eigenvalue distribution (signal eigenvalues are
    sparse outliers with negligible density mass), then count above the edge.
    Avoids the runaway cascade of naive iterative variance-removal."""
    from scipy.optimize import minimize_scalar
    from scipy.stats import gaussian_kde

    ev = np.sort(eigvals)[::-1]
    kde = gaussian_kde(ev, bw_method=0.25)
    grid = np.linspace(1e-4, max(3.0, ev[min(2, len(ev) - 1)]), 400)
    emp = kde(grid)

    def sse(sigma2):
        return float(((mp_pdf(grid, q, sigma2) - emp) ** 2).sum())

    res = minimize_scalar(sse, bounds=(0.2, 1.3), method="bounded")
    sigma2 = float(res.x)
    edge = mp_edge(q, sigma2)
    k = int((ev > edge).sum())
    return k, float(edge)


def denoise_corr(corr: np.ndarray, T: int) -> tuple[np.ndarray, dict]:
    """Eigenvalue clipping: bulk -> average (trace preserving)."""
    N = corr.shape[0]
    q = N / T
    eigval, eigvec = np.linalg.eigh(corr)      # ascending
    eigval = eigval[::-1]; eigvec = eigvec[:, ::-1]
    k, edge = n_signal_factors(eigval, q)
    out_val = eigval.copy()
    if k < N:
        out_val[k:] = eigval[k:].mean()        # flatten the bulk
    C = eigvec @ np.diag(out_val) @ eigvec.T
    # renormalize to a proper correlation matrix
    d = np.sqrt(np.diag(C))
    C = np.clip(C / np.outer(d, d), -1, 1)
    np.fill_diagonal(C, 1.0)
    return C, {"n_factors": int(k), "edge": float(edge), "q": float(q),
               "eigvals": eigval.tolist()}


def denoise_cov(cov: pd.DataFrame, T: int) -> tuple[pd.DataFrame, dict]:
    C = cov.to_numpy()
    vol = np.sqrt(np.diag(C))
    corr = corr_from_cov(C)
    dn, info = denoise_corr(corr, T)
    out = dn * np.outer(vol, vol)
    return pd.DataFrame(out, index=cov.index, columns=cov.columns), info


def detone_corr(corr: np.ndarray, n_remove: int = 1) -> np.ndarray:
    """Remove the top market mode(s) — useful for clustering structure."""
    eigval, eigvec = np.linalg.eigh(corr)
    eigval = eigval[::-1]; eigvec = eigvec[:, ::-1]
    C = corr - (eigvec[:, :n_remove] * eigval[:n_remove]) @ eigvec[:, :n_remove].T
    d = np.sqrt(np.maximum(np.diag(C), 1e-12))
    C = np.clip(C / np.outer(d, d), -1, 1)
    np.fill_diagonal(C, 1.0)
    return C


# ---------------------------------------------------------------------------
# min-variance bake-off (the covariance quality experiment)
# ---------------------------------------------------------------------------

def min_var_weights(cov: np.ndarray) -> np.ndarray:
    """Unconstrained min-variance (the purest covariance test; can short)."""
    ones = np.ones(len(cov))
    w = np.linalg.solve(cov + np.eye(len(cov)) * 1e-8, ones)
    return w / w.sum()


def minvar_bakeoff(rets: pd.DataFrame, window: int = 252,
                   rebalance: int = 21, halflife: int = 63) -> dict:
    """Walk-forward min-var realized vol under four covariance estimators."""
    from kronos.covariance import ewma_cov, shrunk_cov

    dates = rets.index
    T = len(dates)
    methods = ["sample", "lw", "rmt", "lw_rmt"]
    port_rets = {m: np.zeros(T) for m in methods}
    n_factors_hist = []
    turnover = dict.fromkeys(methods, 0.0)
    prev_w = dict.fromkeys(methods)

    for i in range(window, T, rebalance):
        sub = rets.iloc[i - window:i]
        S_samp = ewma_cov(sub, halflife)
        S_lw = shrunk_cov(sub, halflife, window).to_numpy()
        S_rmt, info = denoise_cov(pd.DataFrame(S_samp, index=rets.columns,
                                               columns=rets.columns), window)
        S_lwrmt, _ = denoise_cov(pd.DataFrame(S_lw, index=rets.columns,
                                              columns=rets.columns), window)
        n_factors_hist.append(info["n_factors"])
        covs = {"sample": S_samp, "lw": S_lw,
                "rmt": S_rmt.to_numpy(), "lw_rmt": S_lwrmt.to_numpy()}
        j_end = min(i + rebalance, T)
        R = rets.iloc[i:j_end].to_numpy()
        for m in methods:
            w = min_var_weights(covs[m])
            port_rets[m][i:j_end] = R @ w
            if prev_w[m] is not None:
                turnover[m] += float(np.abs(w - prev_w[m]).sum())
            prev_w[m] = w

    start = window
    years = (T - start) / 252
    out = {"n_factors_median": float(np.median(n_factors_hist)),
           "n_factors_hist": n_factors_hist, "methods": {}}
    for m in methods:
        r = pd.Series(port_rets[m][start:])
        out["methods"][m] = {
            "realized_vol": float(r.std() * np.sqrt(252)),
            "turnover_per_year": turnover[m] / years,
        }
    return out
