"""KRONOS-CLOCK: is systemic tail risk just correlated volatility clocks?

Pre-registered in DESIGN5.md. Machinery:
  * empirical tail-dependence and exceedance-correlation statistics,
  * finite-sample Gaussian-copula null bands via a rho-binned simulation
    lookup (every pair judged against a null with its own correlation and
    sample length),
  * the multifractality-after-deformation control,
  * common-clock (market-clock) deformation decomposition.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# tail statistics
# ---------------------------------------------------------------------------

def tail_dependence(x: np.ndarray, y: np.ndarray, q: float,
                    lower: bool = True) -> float:
    """Empirical lambda(q) = P(y in tail | x in tail), symmetric estimate."""
    qx = np.quantile(x, q if lower else 1 - q)
    qy = np.quantile(y, q if lower else 1 - q)
    if lower:
        joint = np.mean((x <= qx) & (y <= qy))
    else:
        joint = np.mean((x >= qx) & (y >= qy))
    return float(joint / q)            # = P(both)/P(one) under exchangeability


def exceedance_asymmetry(x: np.ndarray, y: np.ndarray, q: float = 0.10) -> float:
    """corr in joint lower tail minus corr in joint upper tail."""
    qxl, qxu = np.quantile(x, q), np.quantile(x, 1 - q)
    qyl, qyu = np.quantile(y, q), np.quantile(y, 1 - q)
    lo = (x <= qxl) & (y <= qyl)
    hi = (x >= qxu) & (y >= qyu)
    out = 0.0
    if lo.sum() > 10 and hi.sum() > 10:
        out = float(np.corrcoef(x[lo], y[lo])[0, 1]
                    - np.corrcoef(x[hi], y[hi])[0, 1])
    return out


# ---------------------------------------------------------------------------
# Gaussian-copula null bands (rho-binned finite-sample lookup)
# ---------------------------------------------------------------------------

class GaussianNull:
    def __init__(self, T: int, qs=(0.05, 0.025), n_sims: int = 400,
                 rho_grid=None, seed: int = 42):
        self.T = T
        self.qs = qs
        rho_grid = np.arange(0.0, 0.96, 0.05) if rho_grid is None else rho_grid
        self.rho_grid = rho_grid
        rng = np.random.default_rng(seed)
        # bands[q][i] = (mean, p95) of tail dependence under Gaussian copula
        self.bands = {q: np.zeros((len(rho_grid), 2)) for q in qs}
        self.asym = np.zeros((len(rho_grid), 2))
        for i, rho in enumerate(rho_grid):
            stats_q = {q: [] for q in qs}
            stats_a = []
            for s in range(n_sims):
                z1 = rng.normal(size=T)
                z2 = rho * z1 + np.sqrt(1 - rho ** 2) * rng.normal(size=T)
                for q in qs:
                    stats_q[q].append(tail_dependence(z1, z2, q))
                stats_a.append(exceedance_asymmetry(z1, z2))
            for q in qs:
                a = np.array(stats_q[q])
                self.bands[q][i] = [a.mean(), np.percentile(a, 95)]
            aa = np.array(stats_a)
            self.asym[i] = [aa.mean(), np.percentile(aa, 95)]

    def lookup(self, rho: float, q: float) -> tuple[float, float]:
        i = int(np.clip(np.round(rho / 0.05), 0, len(self.rho_grid) - 1))
        return tuple(self.bands[q][i])

    def lookup_asym(self, rho: float) -> tuple[float, float]:
        i = int(np.clip(np.round(rho / 0.05), 0, len(self.rho_grid) - 1))
        return tuple(self.asym[i])


def pair_tail_study(rets: pd.DataFrame, null: GaussianNull,
                    qs=(0.05, 0.025), max_pairs: int | None = None,
                    seed: int = 42) -> dict:
    """All-pairs tail stats vs their Gaussian nulls."""
    cols = list(rets.columns)
    pairs = [(a, b) for i, a in enumerate(cols) for b in cols[i + 1:]]
    if max_pairs and len(pairs) > max_pairs:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(pairs), max_pairs, replace=False)
        pairs = [pairs[i] for i in idx]
    out = {q: {"excess": [], "above95": 0} for q in qs}
    asym_excess, asym_above = [], 0
    n = 0
    X = rets.to_numpy()
    colmap = {c: i for i, c in enumerate(cols)}
    from scipy.stats import spearmanr
    for a, b in pairs:
        x, y = X[:, colmap[a]], X[:, colmap[b]]
        ok = np.isfinite(x) & np.isfinite(y)
        x, y = x[ok], y[ok]
        if len(x) < 500:
            continue
        # calibrate the Gaussian null with RANK correlation: Pearson is
        # inflated by the very jump days under test (conditioning on it
        # blinds the test); for a bivariate Gaussian the conversion
        # rho = 2 sin(pi * rho_S / 6) is exact, and Spearman has bounded
        # influence against tail contamination.
        rho_s = float(spearmanr(x, y).statistic)
        rho = float(2 * np.sin(np.pi * rho_s / 6))
        if not np.isfinite(rho):
            continue
        n += 1
        for q in qs:
            td = tail_dependence(x, y, q)
            mean_null, p95 = null.lookup(abs(rho), q)
            out[q]["excess"].append(td - mean_null)
            out[q]["above95"] += int(td > p95)
        asy = exceedance_asymmetry(x, y)
        am, a95 = null.lookup_asym(abs(rho))
        asym_excess.append(asy - am)
        asym_above += int(asy > a95)
    res = {"n_pairs": n}
    for q in qs:
        e = np.array(out[q]["excess"])
        res[f"q{int(q*1000)}"] = {
            "median_excess": float(np.median(e)),
            "frac_above95": float(out[q]["above95"] / max(n, 1)),
        }
    res["asym_median_excess"] = float(np.median(asym_excess))
    res["asym_frac_above95"] = float(asym_above / max(n, 1))
    return res


# ---------------------------------------------------------------------------
# simulation worlds for the gate
# ---------------------------------------------------------------------------

def simulate_clock_world(T: int, n_assets: int = 6, rho_eps: float = 0.45,
                         rho_clock: float = 0.8, s2: float = 0.12,
                         joint_jumps: float = 0.0, seed: int = 0) -> dict:
    """Correlated lognormal clocks + Gaussian-copula innovations.
    joint_jumps > 0 adds a common crash shock (the contagion component)."""
    rng = np.random.default_rng(seed)
    rho_v = 0.98
    eta = np.sqrt(s2 * (1 - rho_v ** 2))
    # one common clock factor + idiosyncratic clocks
    common = np.zeros(T)
    for t in range(1, T):
        common[t] = rho_v * common[t - 1] + eta * rng.normal()
    lv = np.zeros((T, n_assets))
    for j in range(n_assets):
        idio = np.zeros(T)
        for t in range(1, T):
            idio[t] = rho_v * idio[t - 1] + eta * rng.normal()
        lv[:, j] = np.sqrt(rho_clock) * common + np.sqrt(1 - rho_clock) * idio
    sigma = 0.01 * np.exp(lv)
    # Gaussian-copula innovations with equicorrelation rho_eps
    L = np.linalg.cholesky(np.full((n_assets, n_assets), rho_eps)
                           + np.eye(n_assets) * (1 - rho_eps))
    eps = rng.normal(size=(T, n_assets)) @ L.T
    r = sigma * eps
    if joint_jumps > 0:
        jdays = rng.random(T) < 0.01
        jsize = rng.normal(0, joint_jumps * 0.01, T)   # COMMON shock
        r = r + (jdays * jsize)[:, None] * rng.uniform(0.7, 1.3, (T, n_assets))
    idx = pd.bdate_range("2012-01-02", periods=T)
    close = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx,
                         columns=[f"A{j}" for j in range(n_assets)])
    gkvar = pd.DataFrame(sigma ** 2 * rng.gamma(3.7, 1 / 3.7, (T, n_assets)),
                         index=idx, columns=close.columns)
    return {"close": close, "gkvar": gkvar}


# ---------------------------------------------------------------------------
# C3: common-clock decomposition
# ---------------------------------------------------------------------------

def clock_commonality(gkvar: pd.DataFrame, smooth: int = 10) -> dict:
    """Top-eigenvalue share of the smoothed log-vol correlation matrix.
    (Daily log-vol CHANGES are dominated by iid proxy noise; the common
    clock lives in the slow levels, so smooth first.)"""
    lv = 0.5 * np.log(gkvar.where(gkvar > 0))
    lv = lv.rolling(smooth).mean().dropna(how="all")
    corr = lv.corr().to_numpy()
    ev = np.linalg.eigvalsh(corr)[::-1]
    return {"eig1_share": float(ev[0] / len(corr)),
            "eig2_share": float(ev[1] / len(corr))}


def market_clock_deformation(close: pd.DataFrame, gkvar: pd.DataFrame,
                             market: str) -> dict:
    """Kurtosis after deforming every asset by the MARKET clock only."""
    from kronos.laws import tail_report
    r = np.log(close / close.shift(1))
    own = r / np.sqrt(gkvar)
    mkt = r.div(np.sqrt(gkvar[market]), axis=0)
    out = {}
    for c in close.columns:
        out[c] = {
            "kurt_raw": tail_report(r[c])["kurt"],
            "kurt_mktclock": tail_report(mkt[c])["kurt"],
            "kurt_ownclock": tail_report(own[c])["kurt"],
        }
    return out
