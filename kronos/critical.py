"""KRONOS-CRITICAL: are crashes critical transitions or shocks? (DESIGN9.md)

Core machinery:
  * early-warning indicators (critical slowing down) on the volatility state,
  * crash-onset labels (price-based, causal, NOT vol-defined),
  * a confound-killing test: incremental out-of-sample AUC of {vol + CSD}
    over {vol only}, walk-forward, with stationary-bootstrap CIs,
  * fold-bifurcation and shock simulation worlds for the credibility gate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from kronos.forensics import stationary_bootstrap_indices

# ---------------------------------------------------------------------------
# early-warning indicators (critical slowing down), all causal
# ---------------------------------------------------------------------------

def _ar1_phi(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    if len(x) < 10:
        return np.nan
    a, b = x[:-1], x[1:]
    va = np.var(a)
    if va < 1e-18:
        return np.nan
    return float(np.cov(a, b)[0, 1] / va)


def _acf(x: np.ndarray, lag: int = 1) -> float:
    x = x - x.mean()
    v = np.mean(x * x)
    if v < 1e-18 or lag >= len(x):
        return np.nan
    return float(np.mean(x[lag:] * x[:-lag]) / v)


def _spectral_ratio(x: np.ndarray) -> float:
    """Low-freq / high-freq power — spectral reddening signature."""
    x = x - x.mean()
    if len(x) < 16:
        return np.nan
    f = np.abs(np.fft.rfft(x)) ** 2
    n = len(f)
    lo = f[1:n // 4].sum()
    hi = f[n // 4:].sum()
    return float(lo / hi) if hi > 0 else np.nan


def ews_indicators(state: pd.Series, rets: pd.Series, L: int = 60) -> pd.DataFrame:
    """Rolling CSD indicators known at each t (window of past L obs).

    state = the dynamical state variable (log GK volatility).
    """
    x = state.to_numpy()
    r = rets.reindex(state.index).to_numpy()
    T = len(x)
    cols = {"v_level": np.full(T, np.nan), "phi": np.full(T, np.nan),
            "ac1_x": np.full(T, np.nan), "volofvol": np.full(T, np.nan),
            "skew_dx": np.full(T, np.nan), "spectral": np.full(T, np.nan),
            "ac1_absr": np.full(T, np.nan)}
    for t in range(L, T):
        w = x[t - L:t]
        dw = np.diff(w)
        cols["v_level"][t] = w.mean()
        cols["phi"][t] = _ar1_phi(w)
        cols["ac1_x"][t] = _acf(w, 1)
        cols["volofvol"][t] = np.std(dw)
        cols["skew_dx"][t] = pd.Series(dw).skew()
        cols["spectral"][t] = _spectral_ratio(w)
        ra = np.abs(r[t - L:t])
        cols["ac1_absr"][t] = _acf(ra, 1)
    return pd.DataFrame(cols, index=state.index)


def kappa_from_phi(phi: float) -> float:
    """Restoring rate kappa = -ln(phi); kappa -> 0 is the CSD signature."""
    if not np.isfinite(phi) or phi <= 0:
        return np.nan
    return -np.log(min(phi, 0.9999))


# ---------------------------------------------------------------------------
# crash labels (price-based, causal threshold)
# ---------------------------------------------------------------------------

def crash_labels(close: pd.Series, H: int = 20, q: float = 0.05,
                 min_history: int = 504, lower: bool = True) -> pd.Series:
    """1 if the forward H-day log return is below (above) the causal
    q-quantile of all H-day forward returns seen so far."""
    lp = np.log(close)
    fwd = (lp.shift(-H) - lp)
    thr = (fwd.expanding(min_periods=min_history)
              .quantile(q if lower else 1 - q).shift(1))
    if lower:
        lab = (fwd < thr).astype(float)
    else:
        lab = (fwd > thr).astype(float)
    lab[fwd.isna() | thr.isna()] = np.nan
    return lab


# ---------------------------------------------------------------------------
# logistic regression (dependency-free, L2-penalized)
# ---------------------------------------------------------------------------

def _fit_logistic(X: np.ndarray, y: np.ndarray, lam: float = 1.0) -> np.ndarray:
    X = np.column_stack([np.ones(len(X)), X])
    n, p = X.shape

    def nll(b):
        z = X @ b
        ll = np.sum(y * z - np.logaddexp(0, z))
        pen = 0.5 * lam * np.sum(b[1:] ** 2)
        return -ll + pen

    def grad(b):
        z = X @ b
        mu = 1 / (1 + np.exp(-z))
        g = X.T @ (mu - y)
        g[1:] += lam * b[1:]
        return g

    res = minimize(nll, np.zeros(p), jac=grad, method="L-BFGS-B")
    return res.x


def _predict_logistic(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    z = beta[0] + X @ beta[1:]
    return 1 / (1 + np.exp(-z))


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney AUC."""
    ok = np.isfinite(scores) & np.isfinite(labels)
    s, y = scores[ok], labels[ok]
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    order = np.argsort(s)
    ranks = np.empty(len(s)); ranks[order] = np.arange(1, len(s) + 1)
    # average ties
    r = pd.Series(s).rank().to_numpy()
    return float((r[y == 1].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


# ---------------------------------------------------------------------------
# the confound-killing walk-forward AUC test
# ---------------------------------------------------------------------------

# The benchmark is the full volatility MAGNITUDE (level + dispersion) — the
# trivial confound. The CSD set is only the autocorrelation / restoring-force
# signatures of critical slowing down, which carry transition information
# ONLY under a genuine bifurcation (gate X20 proves the separation).
VOL_FEATURES = ["v_level", "volofvol"]
CSD_FEATURES = ["phi", "ac1_x", "spectral", "skew_dx"]


def walkforward_incremental_auc(feats: pd.DataFrame, labels: pd.Series,
                                refit_every: int = 252, min_train: int = 756,
                                lam: float = 1.0, embargo: int = 20) -> dict:
    """OOS predictions from {vol magnitude} and {vol + CSD}; returns pooled
    OOS scores, labels, and both AUCs. Strictly causal, with an `embargo`
    (= label horizon H) purging training rows whose forward labels would
    otherwise peek past the refit point (Lopez de Prado purged CV)."""
    df = pd.concat([feats, labels.rename("_y")], axis=1).dropna()
    y = df["_y"].to_numpy()
    Xvol = df[VOL_FEATURES].to_numpy()
    Xall = df[VOL_FEATURES + CSD_FEATURES].to_numpy()
    # standardize causally is overkill; standardize on each train fold
    T = len(df)
    pred_vol = np.full(T, np.nan)
    pred_all = np.full(T, np.nan)
    t = min_train
    while t < T:
        tr = slice(0, max(t - embargo, 10))
        te = slice(t, min(t + refit_every, T))
        nv = len(VOL_FEATURES)
        mu, sd = Xall[tr].mean(0), Xall[tr].std(0) + 1e-9
        muv, sdv = mu[:nv], sd[:nv]
        bv = _fit_logistic((Xvol[tr] - muv) / sdv, y[tr], lam)
        ba = _fit_logistic((Xall[tr] - mu) / sd, y[tr], lam)
        pred_vol[te] = _predict_logistic(bv, (Xvol[te] - muv) / sdv)
        pred_all[te] = _predict_logistic(ba, (Xall[te] - mu) / sd)
        t += refit_every
    idx = df.index
    return {"pred_vol": pd.Series(pred_vol, index=idx),
            "pred_all": pd.Series(pred_all, index=idx),
            "labels": pd.Series(y, index=idx),
            "auc_vol": auc(pred_vol, y), "auc_all": auc(pred_all, y),
            "n_pos": int(np.nansum(y)), "n": int(np.isfinite(pred_vol).sum())}


def bootstrap_auc_gain(pred_vol, pred_all, labels, n_boot=500,
                       mean_block=63.0, seed=0) -> dict:
    """Stationary-bootstrap CI for AUC(all) - AUC(vol)."""
    pv = pred_vol.to_numpy(); pa = pred_all.to_numpy(); y = labels.to_numpy()
    ok = np.isfinite(pv) & np.isfinite(pa) & np.isfinite(y)
    pv, pa, y = pv[ok], pa[ok], y[ok]
    T = len(y)
    gain = auc(pa, y) - auc(pv, y)
    rng = np.random.default_rng(seed)
    gains = np.empty(n_boot)
    for i in range(n_boot):
        idx = stationary_bootstrap_indices(T, mean_block, rng)
        if y[idx].sum() < 5 or y[idx].sum() > len(idx) - 5:
            gains[i] = np.nan; continue
        gains[i] = auc(pa[idx], y[idx]) - auc(pv[idx], y[idx])
    gains = gains[np.isfinite(gains)]
    return {"gain": float(gain),
            "ci_lo": float(np.percentile(gains, 2.5)),
            "ci_hi": float(np.percentile(gains, 97.5)),
            "p_gain_le_0": float((gains <= 0).mean())}


def stratified_lift(feats: pd.DataFrame, labels: pd.Series,
                    signal: str = "phi", n_strata: int = 3,
                    target_stratum: int = 1) -> dict:
    """Within a vol stratum, crash frequency in top vs bottom signal tercile.
    Kills the confound by holding the vol level ~fixed."""
    df = pd.concat([feats[["v_level", signal]], labels.rename("_y")],
                   axis=1).dropna()
    vt = pd.qcut(df["v_level"].rank(method="first"), n_strata, labels=False)
    sub = df[vt == target_stratum]
    st = pd.qcut(sub[signal].rank(method="first"), 3, labels=False)
    f_hi = sub["_y"][st == 2].mean()
    f_lo = sub["_y"][st == 0].mean()
    return {"freq_hi": float(f_hi), "freq_lo": float(f_lo),
            "lift": float(f_hi / max(f_lo, 1e-9)), "n": int(len(sub))}


def precursor_shift(feats: pd.DataFrame, labels: pd.Series, W: int = 20,
                    signals=CSD_FEATURES) -> dict:
    """Standardized shift of each indicator in the W days BEFORE a crash
    onset vs its overall level (in std units). This is the raw effect size:
    if there is no pre-crash CSD precursor at all, every shift is ~0 — the
    cleanest 'true null, not low power' statement. A genuine bifurcation
    shows a large positive phi/ac1 shift."""
    df = pd.concat([feats[list(signals)], labels.rename("_y")], axis=1).dropna()
    y = df["_y"].to_numpy()
    # 'approaching a crash' = a crash onset occurs within the next W days
    approaching = np.zeros(len(y), dtype=bool)
    onset = (np.diff(np.r_[0, y]) > 0)        # rising edge of the label
    idx = np.flatnonzero(onset)
    for i in idx:
        approaching[max(0, i - W):i] = True
    out = {}
    for s in signals:
        v = df[s].to_numpy()
        mu, sd = v.mean(), v.std() + 1e-12
        out[s] = float((v[approaching].mean() - mu) / sd) if approaching.any() else 0.0
    return out


# ---------------------------------------------------------------------------
# simulation worlds for the gate
# ---------------------------------------------------------------------------

def simulate_fold_world(T: int, seed: int = 0, dt: float = 0.05,
                        sigma: float = 0.12, period: int = 800) -> dict:
    """Double-well Langevin with a slowly cycling control parameter; the
    state jumps between wells at folds. CSD (phi -> 1) is PROVABLE as each
    fold is approached. Returns state x and crash labels (jump in next H)."""
    rng = np.random.default_rng(seed)
    # control parameter triangle-waves across the fold value (~+-0.4)
    tt = np.arange(T)
    c = 0.55 * np.sin(2 * np.pi * tt / period)
    x = np.zeros(T)
    x[0] = -1.0
    for t in range(1, T):
        force = x[t - 1] - x[t - 1] ** 3 + c[t]      # -dU/dx
        x[t] = x[t - 1] + force * dt + sigma * np.sqrt(dt) * rng.normal()
    # a transition = a basin switch: state moves decisively from one well
    # (|x|>0.5, one sign) to the other; mark the zero-crossing, dedup 30 steps
    jumps = np.zeros(T)
    last = -10 ** 9
    side = np.where(x > 0.5, 1, np.where(x < -0.5, -1, 0))
    cur = side[0] if side[0] != 0 else -1
    for t in range(1, T):
        if side[t] != 0 and side[t] != cur:
            if t - last > 30:
                jumps[t] = 1.0
                last = t
            cur = side[t]
    return {"x": x, "jumps": jumps, "c": c}


def simulate_shock_world(T: int, seed: int = 0, phi0: float = 0.85) -> dict:
    """AR(1) state with CONSTANT phi (no slowing down) but time-varying
    innovation variance; crashes are jumps whose probability depends only on
    the current variance level (vol predicts, phi does NOT add info)."""
    rng = np.random.default_rng(seed)
    # slow variance cycle
    logvar = 0.6 * np.sin(2 * np.pi * np.arange(T) / 700)
    innov_sd = 0.1 * np.exp(logvar)
    x = np.zeros(T)
    jumps = np.zeros(T)
    for t in range(1, T):
        x[t] = phi0 * x[t - 1] + innov_sd[t] * rng.normal()
        p_jump = 0.002 * np.exp(2 * logvar[t])       # depends on variance only
        if rng.random() < p_jump:
            x[t] -= 1.5
            jumps[t] = 1.0
    return {"x": x, "jumps": jumps, "innov_sd": innov_sd}


def jumps_to_labels(jumps: np.ndarray, H: int = 20) -> np.ndarray:
    """Label day t = 1 if a jump occurs in (t, t+H]."""
    T = len(jumps)
    lab = np.zeros(T)
    for t in range(T - 1):
        lab[t] = 1.0 if jumps[t + 1:t + 1 + H].sum() > 0 else 0.0
    lab[-H:] = np.nan
    return lab
