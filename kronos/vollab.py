"""Volatility forecasting laboratory (KRONOS-X, Q3a).

Three forecasters of next-day variance, walk-forward, judged by QLIKE with
Diebold-Mariano tests:
  * EWMA (RiskMetrics lambda=0.94) — the v1 incumbent
  * HAR-RV (Corsi) on log GK realized variance
  * GJR-GARCH(1,1)-t fit by our own MLE (variance targeting + transforms)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import norm


# ---------------------------------------------------------------------------
# forecasters
# ---------------------------------------------------------------------------

def ewma_forecast(r2: np.ndarray, lam: float = 0.94) -> np.ndarray:
    """sigma2_hat[t] = forecast of var at t made at t-1 (uses r2 < t)."""
    T = len(r2)
    s2 = np.empty(T)
    s2[0] = r2[:20].mean() if T >= 20 else r2.mean()
    for t in range(1, T):
        s2[t] = lam * s2[t - 1] + (1 - lam) * r2[t - 1]
    return s2


class HAR:
    """log-HAR: log RV_{t} ~ 1 + log RV_d(t-1) + log RV_w(t-1) + log RV_m(t-1)."""

    def fit(self, rv: np.ndarray) -> "HAR":
        lrv = np.log(np.maximum(rv, 1e-12))
        d = lrv
        w = pd.Series(lrv).rolling(5).mean().to_numpy()
        m = pd.Series(lrv).rolling(22).mean().to_numpy()
        y = lrv[22:]
        Xm = np.column_stack([np.ones(len(y)), d[21:-1], w[21:-1], m[21:-1]])
        ok = np.isfinite(Xm).all(axis=1) & np.isfinite(y)
        coef, *_ = np.linalg.lstsq(Xm[ok], y[ok], rcond=None)
        resid = y[ok] - Xm[ok] @ coef
        self.coef_ = coef
        self.s2_resid_ = float(resid.var())
        return self

    def forecast_next(self, rv: np.ndarray) -> float:
        """Variance forecast for t+1 given rv through t (lognormal-corrected)."""
        lrv = np.log(np.maximum(rv, 1e-12))
        x = np.array([1.0, lrv[-1], lrv[-5:].mean(), lrv[-22:].mean()])
        return float(np.exp(x @ self.coef_ + 0.5 * self.s2_resid_))


class GJRGARCH:
    """GJR-GARCH(1,1) with standardized Student-t innovations, own MLE.

    sigma2_t = omega + alpha*r2_{t-1} + gamma_*r2_{t-1}*1[r<0] + beta*sigma2_{t-1}
    omega from variance targeting; params optimized with bounds + penalty,
    multistart L-BFGS-B.
    """

    def __init__(self):
        self.params_ = None  # (alpha, gamma_, beta, nu)
        self.converged_ = False

    @staticmethod
    def _filter(r: np.ndarray, alpha: float, gamma_: float, beta: float,
                uncond: float) -> np.ndarray:
        # hot path of the MLE: plain-float recursion is ~5x faster than
        # numpy scalar indexing here
        T = len(r)
        omega = uncond * max(1 - alpha - beta - gamma_ / 2, 1e-4)
        r2 = (r * r).tolist()
        neg = (r < 0).tolist()
        out = [uncond] * T
        prev = uncond
        a, g, b = float(alpha), float(gamma_), float(beta)
        for t in range(1, T):
            prev = omega + (a + g * neg[t - 1]) * r2[t - 1] + b * prev
            out[t] = prev
        return np.maximum(np.array(out), 1e-12)

    def _nll(self, theta: np.ndarray, r: np.ndarray, uncond: float) -> float:
        a, g, b, nu = theta
        if a + b + g / 2 >= 0.999:
            return 1e9 * (a + b + g / 2)
        s2 = self._filter(r, a, g, b, uncond)
        z2 = r * r / s2
        ll = (gammaln((nu + 1) / 2) - gammaln(nu / 2)
              - 0.5 * np.log(np.pi * (nu - 2))
              - 0.5 * np.log(s2)
              - (nu + 1) / 2 * np.log1p(z2 / (nu - 2)))
        return -float(ll.sum())

    def fit(self, r: np.ndarray) -> "GJRGARCH":
        uncond = float(r.var())
        bounds = [(1e-4, 0.30), (0.0, 0.30), (0.50, 0.995), (4.1, 30.0)]
        starts = [np.array([0.05, 0.08, 0.88, 8.0]),
                  np.array([0.02, 0.12, 0.90, 6.0]),
                  np.array([0.10, 0.02, 0.82, 12.0])]
        best = None
        for x0 in starts:
            try:
                res = minimize(self._nll, x0, args=(r, uncond),
                               method="L-BFGS-B", bounds=bounds,
                               options={"maxiter": 300})
                if best is None or res.fun < best.fun:
                    best = res
            except Exception:
                continue
        if best is None or not np.isfinite(best.fun):
            self.converged_ = False
            return self
        self.params_ = tuple(best.x)
        self.uncond_ = uncond
        self.converged_ = True
        return self

    def state(self, r: np.ndarray) -> float:
        """Conditional variance at the last observation (one full filter pass)."""
        a, g, b, _ = self.params_
        return float(self._filter(r, a, g, b, self.uncond_)[-1])

    def step(self, s2_prev: float, r_prev: float) -> float:
        """Incremental 1-step variance update (no re-filtering)."""
        a, g, b, _ = self.params_
        omega = self.uncond_ * max(1 - a - b - g / 2, 1e-4)
        return omega + (a + g * (r_prev < 0)) * r_prev * r_prev + b * s2_prev


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------

def qlike(rv: np.ndarray, f: np.ndarray) -> np.ndarray:
    """QLIKE loss per day (robust to noisy RV proxy; Patton 2011)."""
    ratio = np.maximum(rv, 1e-12) / np.maximum(f, 1e-12)
    return ratio - np.log(ratio) - 1.0


def diebold_mariano(lossA: np.ndarray, lossB: np.ndarray, h: int = 5) -> dict:
    """DM test of equal predictive accuracy; negative stat favors A."""
    d = lossA - lossB
    d = d[np.isfinite(d)]
    T = len(d)
    dbar = d.mean()
    # Newey-West long-run variance
    gamma0 = ((d - dbar) ** 2).mean()
    lrv = gamma0
    for k in range(1, h + 1):
        cov = ((d[k:] - dbar) * (d[:-k] - dbar)).mean()
        lrv += 2 * (1 - k / (h + 1)) * cov
    stat = dbar / np.sqrt(max(lrv, 1e-300) / T)
    p = 2 * (1 - norm.cdf(abs(stat)))
    return {"stat": float(stat), "p": float(p), "mean_diff": float(dbar)}


def walkforward_vol_forecasts(r: pd.Series, gkvar: pd.Series,
                              min_train: int = 750, refit_every: int = 21,
                              garch_refit_every: int = 63) -> pd.DataFrame:
    """Daily 1-step-ahead variance forecasts from all three models, causal.

    GARCH is refit on a slower cadence (its MLE is the expensive piece, and
    GARCH parameters drift slowly); its variance state still updates daily.
    """
    df = pd.concat([r, gkvar], axis=1, keys=["r", "rv"]).dropna()
    rr = df["r"].to_numpy()
    rv = df["rv"].to_numpy()
    T = len(df)

    f_ewma = ewma_forecast(rr * rr)   # fully causal already
    f_har = np.full(T, np.nan)
    f_garch = np.full(T, np.nan)
    garch_fails = 0

    t = min_train
    har, garch = None, None
    last_garch_fit = -10 ** 9
    while t < T:
        har = HAR().fit(rv[:t])
        if t - last_garch_fit >= garch_refit_every:
            g = GJRGARCH().fit(rr[:t])
            if g.converged_:
                garch = g
            else:
                garch_fails += 1                # keep previous fit (logged)
            last_garch_fit = t
        t_next = min(t + refit_every, T)
        s2 = garch.state(rr[:t]) if garch is not None else None
        for s in range(t, t_next):
            f_har[s] = har.forecast_next(rv[:s])
            if s2 is not None:
                s2 = garch.step(s2, rr[s - 1])   # forecast for day s
                f_garch[s] = s2
        t = t_next

    out = pd.DataFrame({"rv": rv, "ewma": f_ewma, "har": f_har,
                        "garch": f_garch}, index=df.index)
    out.attrs["garch_fails"] = garch_fails
    return out
