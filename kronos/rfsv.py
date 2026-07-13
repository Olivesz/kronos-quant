"""RFSV rough-volatility forecaster (KRONOS-X², Study 2).

Gatheral-Jaisson-Rosenbaum: if log-vol is (approximately) fBm with Hurst H,
its conditional expectation given the past is a kernel-weighted history,

    E[log v_{t+D} | F_t]  ~  sum_s  w_s * log v_{t-s},
    w_s ∝ 1 / ((s + D + 0.5) * (s + 0.5)^(H + 1/2)),

truncated at `lookback` days and normalized (exact fBm prediction up to
truncation; the +0.5 offsets are the standard midpoint discretization).
H is re-estimated walk-forward (causal), and a per-window OLS calibration
log v_{t+1} = a + b * yhat absorbs truncation bias; the exp-transform adds
the usual +0.5 * resid-var lognormal correction.

Does roughness *forecast*, or only describe? This module answers it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kronos.rough import estimate_hurst


def rfsv_kernel(H: float, horizon: int, lookback: int) -> np.ndarray:
    """Weights over lags s = 0..lookback-1 (s=0 is the most recent day)."""
    s = np.arange(lookback, dtype=float)
    w = 1.0 / ((s + horizon + 0.5) * (s + 0.5) ** (H + 0.5))
    return w / w.sum()


class RFSV:
    def __init__(self, horizon: int = 1, lookback: int = 500,
                 smooth_grid=(1, 2, 5, 10)):
        self.horizon = horizon
        self.lookback = lookback
        self.smooth_grid = smooth_grid
        self.H_ = None
        self.halflife_ = 1
        self.a_ = 0.0
        self.b_ = 1.0
        self.s2_ = 0.0
        self.w_ = None

    @staticmethod
    def _ewma(x: np.ndarray, halflife: float) -> np.ndarray:
        if halflife <= 1:
            return x
        lam = np.exp(-np.log(2) / halflife)
        out = np.empty_like(x)
        out[0] = x[0]
        for i in range(1, len(x)):
            out[i] = lam * out[i - 1] + (1 - lam) * x[i]
        return out

    def fit(self, gkvar: np.ndarray) -> RFSV:
        """Estimate H, pick the noise-filter halflife, OLS-calibrate.

        The exact fBm kernel is optimal for CLEAN observations, but a daily
        range proxy carries measurement noise and the kernel concentrates
        ~half its mass on lag 0 — importing that noise. Pre-filtering the
        log-variance with a short EWMA (halflife selected on the training
        window only) is the errors-in-variables correction; everything
        remains strictly causal."""
        v = np.maximum(np.asarray(gkvar, dtype=float), 1e-12)
        # kernel H from the 5d-smoothed proxy: measurement noise biases the
        # raw estimate down (Gate X5), smoothing biases up — for the KERNEL
        # this is a tuning input absorbed by the OLS calibration, while H
        # *measurement* rigor lives in the dedicated rough-vol experiment
        self.H_ = float(np.clip(estimate_hurst(pd.Series(v), smooth=5)["H"],
                                0.02, 0.49))
        self.w_ = rfsv_kernel(self.H_, self.horizon, self.lookback)
        lv = np.log(v)
        L = self.lookback
        ts = np.arange(L, len(lv) - self.horizon)
        targets = lv[ts + self.horizon - 1]
        best = None
        for hl in self.smooth_grid:
            sm = self._ewma(lv, hl)
            conv = np.convolve(sm, self.w_)
            preds = conv[ts - 1]
            A = np.column_stack([np.ones_like(preds), preds])
            coef, *_ = np.linalg.lstsq(A, targets, rcond=None)
            s2 = float((targets - A @ coef).var())
            if best is None or s2 < best[0]:
                best = (s2, hl, float(coef[0]), float(coef[1]))
        self.s2_, self.halflife_, self.a_, self.b_ = best
        return self

    def forecast_next(self, gkvar: np.ndarray) -> float:
        """Variance forecast for the next day given history through today."""
        lv = np.log(np.maximum(gkvar, 1e-12))
        sm = self._ewma(lv, self.halflife_)[-self.lookback:][::-1]
        if len(sm) < self.lookback:
            w = self.w_[:len(sm)]
            w = w / w.sum()
        else:
            w = self.w_
        yhat = float(w @ sm)
        return float(np.exp(self.a_ + self.b_ * yhat + 0.5 * self.s2_))


def walkforward_rfsv(gkvar: pd.Series, min_train: int = 750,
                     refit_every: int = 21) -> pd.Series:
    """Causal daily 1-step variance forecasts."""
    v = gkvar.dropna()
    arr = v.to_numpy()
    T = len(arr)
    out = np.full(T, np.nan)
    model = None
    t = min_train
    while t < T:
        model = RFSV().fit(arr[:t])
        t_next = min(t + refit_every, T)
        for s in range(t, t_next):
            out[s] = model.forecast_next(arr[:s])
        t = t_next
    return pd.Series(out, index=v.index, name="rfsv")


# ---------------------------------------------------------------------------
# simulation for the gate: RFSV world with known H
# ---------------------------------------------------------------------------

def simulate_rfsv_world(T: int, H: float = 0.10, nu: float = 0.30,
                        mean_logvar: float = -9.2, noise_shape: float = 3.7,
                        seed: int = 42) -> pd.Series:
    """True log-variance = fBm(H)*nu + mean; observed GK proxy adds
    multiplicative gamma noise matching GK's efficiency."""
    from kronos.rough import simulate_fgn
    rng = np.random.default_rng(seed)
    fgn = simulate_fgn(T, H, seed)
    logv = mean_logvar + nu * np.cumsum(fgn) / np.sqrt(T ** 0)  # fBm path
    # soft mean reversion so the level doesn't wander off to absurdity
    logv = logv - np.linspace(0, logv[-1] - logv[0], T) * 0.0
    v_true = np.exp(logv - logv.mean() + mean_logvar)
    proxy = v_true * rng.gamma(noise_shape, 1 / noise_shape, T)
    idx = pd.bdate_range("2012-01-02", periods=T)
    s = pd.Series(proxy, index=idx)
    s.attrs["true_var"] = v_true
    return s
