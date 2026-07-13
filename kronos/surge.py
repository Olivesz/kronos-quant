"""KRONOS-SURGE: the structure of common volatility surprises (DESIGN6.md).

S1  cascade: do the clock's innovations have their own clock?
S2  time-reversal asymmetry (Zumbach effect) + leverage kernels
S3  surge-intensity forecastability (auditing CLOCK's verdict)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kronos.forensics import stationary_bootstrap_indices

# ---------------------------------------------------------------------------
# S1: the cascade
# ---------------------------------------------------------------------------

def weekly_logvol(gkvar: pd.Series, week: int = 5) -> np.ndarray:
    """Non-overlapping weekly means of log vol (kills iid proxy noise)."""
    lv = 0.5 * np.log(gkvar.dropna().to_numpy())
    n = len(lv) // week
    return lv[:n * week].reshape(n, week).mean(axis=1)


def clock_innovations(gkvar: pd.Series, week: int = 5) -> np.ndarray:
    """u_w = weekly log-vol differences — the clock's own shocks."""
    wl = weekly_logvol(gkvar, week)
    return np.diff(wl)


def cascade_report(gkvar: pd.Series, halflife: int = 8) -> dict:
    """Level-1 stats of clock innovations + level-2 meta-deformation."""
    u = clock_innovations(gkvar)
    u = u - u.mean()
    kurt_u = float(pd.Series(u).kurtosis()) + 3.0
    # vol-of-vol clustering: autocorrelation of |u|
    a = np.abs(u) - np.abs(u).mean()
    ac1 = float(np.mean(a[1:] * a[:-1]) / np.mean(a * a))
    ac5 = float(np.mean(a[5:] * a[:-5]) / np.mean(a * a))
    # meta-clock: EWMA of |u| (lagged: strictly past info)
    s = pd.Series(np.abs(u))
    meta = s.ewm(halflife=halflife).mean().shift(1).to_numpy()
    ok = np.isfinite(meta) & (meta > 1e-8)
    z2 = u[ok] / meta[ok]
    kurt_z2 = float(pd.Series(z2).kurtosis()) + 3.0
    return {"kurt_u": kurt_u, "ac1_absu": ac1, "ac5_absu": ac5,
            "kurt_z2": kurt_z2, "n_weeks": len(u)}


# ---------------------------------------------------------------------------
# S2: Zumbach effect + leverage kernel
# ---------------------------------------------------------------------------

def _xcorr(x: np.ndarray, y: np.ndarray, tau: int) -> float:
    """corr(x_t, y_{t+tau}), tau >= 0."""
    if tau == 0:
        a, b = x, y
    else:
        a, b = x[:-tau], y[tau:]
    sa, sb = a.std(), b.std()
    if sa < 1e-14 or sb < 1e-14:
        return 0.0
    return float(np.mean((a - a.mean()) * (b - b.mean())) / (sa * sb))


def zumbach_stat(r: np.ndarray, v: np.ndarray, taus=range(1, 21)) -> float:
    """Z = sum_tau corr(r2_t, v_{t+tau}) - corr(v_t, r2_{t+tau}).
    Positive = time's arrow points the Zumbach way."""
    r2 = r * r
    return float(sum(_xcorr(r2, v, t) - _xcorr(v, r2, t) for t in taus))


def zumbach_with_ci(r: pd.Series, v: pd.Series, n_boot: int = 300,
                    mean_block: float = 63.0, seed: int = 42) -> dict:
    df = pd.concat([r, v], axis=1, keys=["r", "v"]).dropna()
    rr, vv = df["r"].to_numpy(), df["v"].to_numpy()
    z = zumbach_stat(rr, vv)
    rng = np.random.default_rng(seed)
    T = len(rr)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        idx = stationary_bootstrap_indices(T, mean_block, rng)
        # joint resampling preserves the r-v coupling within blocks
        boots[i] = zumbach_stat(rr[idx], vv[idx])
    return {"z": z, "ci_lo": float(np.percentile(boots, 2.5)),
            "ci_hi": float(np.percentile(boots, 97.5)),
            "p_pos": float((boots > 0).mean())}


def leverage_kernel(r: pd.Series, v: pd.Series, tau_max: int = 60) -> list:
    df = pd.concat([r, v], axis=1, keys=["r", "v"]).dropna()
    rr, vv = df["r"].to_numpy(), df["v"].to_numpy()
    return [round(_xcorr(rr, vv, t), 4) for t in range(1, tau_max + 1)]


# ---------------------------------------------------------------------------
# S3: surge-intensity forecastability
# ---------------------------------------------------------------------------

def joint_tail_days(rets: pd.DataFrame, q: float = 0.05,
                    frac: float = 0.25, window: int = 504) -> pd.Series:
    """Day is a joint-tail day if >= frac of assets sit below their own
    trailing q-quantile (quantiles from strictly past data)."""
    qts = rets.rolling(window).quantile(q).shift(1)
    hits = (rets < qts).mean(axis=1)
    return (hits >= frac).astype(float)


def surge_intensity_lift(rets: pd.DataFrame, gkvar_mkt: pd.Series,
                         horizon: int = 21, n_boot: int = 300,
                         seed: int = 42) -> dict:
    """Frequency of joint-tail days in (t, t+horizon] by meta-clock tercile
    at t (strictly causal), with a stationary-bootstrap CI on the lift."""
    jt = joint_tail_days(rets)
    # daily meta-clock: EWMA std of daily changes of 5d-smoothed log vol
    lv = 0.5 * np.log(gkvar_mkt.where(gkvar_mkt > 0)).rolling(5).mean()
    u = lv.diff()
    meta = u.abs().ewm(halflife=40).mean()
    df = pd.concat([jt.rename("jt"), meta.rename("meta")], axis=1).dropna()
    # future joint-tail frequency over (t, t+h]
    fwd = df["jt"].rolling(horizon).mean().shift(-horizon)
    # expanding causal terciles of the meta-clock
    m = df["meta"]
    r1 = m.expanding(min_periods=504).quantile(1 / 3).shift(1)
    r2 = m.expanding(min_periods=504).quantile(2 / 3).shift(1)
    tercile = pd.Series(np.where(m <= r1, 0, np.where(m <= r2, 1, 2)),
                        index=df.index)
    ok = fwd.notna() & r1.notna()
    fwd_v = fwd[ok].to_numpy()
    ter_v = tercile[ok].to_numpy()

    def lift_of(f, t):
        f1 = f[t == 0].mean()
        f3 = f[t == 2].mean()
        return f3 / max(f1, 1e-9), f1, f3

    lift, f1, f3 = lift_of(fwd_v, ter_v)
    rng = np.random.default_rng(seed)
    T = len(fwd_v)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        idx = stationary_bootstrap_indices(T, 63.0, rng)
        boots[i], _, _ = lift_of(fwd_v[idx], ter_v[idx])
    return {"lift": float(lift), "freq_t1": float(f1), "freq_t3": float(f3),
            "ci_lo": float(np.percentile(boots, 2.5)),
            "ci_hi": float(np.percentile(boots, 97.5)),
            "base_rate": float(np.nanmean(fwd_v)), "n_days": T}


# ---------------------------------------------------------------------------
# simulation worlds for the gates
# ---------------------------------------------------------------------------

def simulate_gjr_world(T: int, seed: int = 0) -> tuple[pd.Series, pd.Series]:
    """GJR-GARCH returns (built-in leverage => Zumbach asymmetry exists)."""
    rng = np.random.default_rng(seed)
    alpha, gamma_, beta = 0.03, 0.12, 0.86
    uncond = 1e-4
    omega = uncond * (1 - alpha - beta - gamma_ / 2)
    r = np.empty(T); v = np.empty(T)
    s2 = uncond
    for t in range(T):
        v[t] = s2
        r[t] = np.sqrt(s2) * rng.normal()
        s2 = omega + (alpha + gamma_ * (r[t] < 0)) * r[t] ** 2 + beta * s2
    idx = pd.bdate_range("2012-01-02", periods=T)
    proxy = pd.Series(v * rng.gamma(3.7, 1 / 3.7, T), index=idx)
    proxy.attrs["true_var"] = v
    return pd.Series(r, index=idx), proxy


def simulate_reversible_world(T: int, seed: int = 0) -> tuple[pd.Series, pd.Series]:
    """Vol path independent of returns => time-reversible, Z should be ~0."""
    rng = np.random.default_rng(seed)
    rho, s2 = 0.98, 0.15
    eta = np.sqrt(s2 * (1 - rho ** 2))
    lv = np.zeros(T)
    for t in range(1, T):
        lv[t] = rho * lv[t - 1] + eta * rng.normal()
    sigma = 0.01 * np.exp(lv)
    r = sigma * rng.normal(size=T)
    idx = pd.bdate_range("2012-01-02", periods=T)
    proxy = pd.Series(sigma ** 2 * rng.gamma(3.7, 1 / 3.7, T), index=idx)
    return pd.Series(r, index=idx), proxy


def simulate_volofvol_world(T: int, n_assets: int = 8, switching: bool = True,
                            seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    """Common clock whose INNOVATION SIZE switches regimes (or stays const).
    Used by the S3 gate: lift must appear iff vol-of-vol clusters."""
    rng = np.random.default_rng(seed)
    rho = 0.99
    base_eta = np.sqrt(0.15 * (1 - rho ** 2))
    eta_t = np.full(T, base_eta)
    if switching:
        state = 0
        for t in range(T):
            if rng.random() < 0.003:
                state = 1 - state
            eta_t[t] = base_eta * (4.0 if state else 0.4)
    lv = np.zeros(T)
    for t in range(1, T):
        lv[t] = rho * lv[t - 1] + eta_t[t] * rng.normal()
    sigma = 0.01 * np.exp(lv)
    eps = rng.normal(size=(T, n_assets)) * 0.6 \
        + rng.normal(size=(T, 1)) * np.sqrt(1 - 0.36)
    r = sigma[:, None] * eps
    idx = pd.bdate_range("2010-01-02", periods=T)
    rets = pd.DataFrame(r, index=idx, columns=[f"A{j}" for j in range(n_assets)])
    proxy = pd.Series(sigma ** 2 * rng.gamma(3.7, 1 / 3.7, T), index=idx)
    return rets, proxy
