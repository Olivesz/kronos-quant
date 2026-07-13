"""Kalman-filter pairs trading sleeve.

Formation: pick highly-correlated pairs whose OLS spread passes a
stationarity t-test (Engle-Granger flavored, computed manually).
Trading: time-varying hedge ratio via a 2-state Kalman filter
(state = [alpha, beta]); trade the innovation z-score with entry/exit
bands, a structural-break stop, and a max holding period.
"""
from __future__ import annotations

import itertools
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Formation
# ---------------------------------------------------------------------------

def _adf_tstat(resid: np.ndarray) -> float:
    """t-stat of rho in: d_resid_t = rho * resid_{t-1} + e_t (no constant/lags).

    More negative => stronger mean reversion. Critical value ~ -2.8/-3.3.
    """
    y = np.diff(resid)
    x = resid[:-1]
    denom = float(x @ x)
    if denom <= 0:
        return 0.0
    rho = float(x @ y) / denom
    e = y - rho * x
    dof = max(len(y) - 1, 1)
    se = np.sqrt((e @ e) / dof / denom)
    return rho / se if se > 0 else 0.0


def select_pairs(px: pd.DataFrame, t: pd.Timestamp, cfg) -> list[tuple[str, str, float]]:
    """Returns [(y_ticker, x_ticker, resid_var)] selected on data through t."""
    window = px.loc[:t].iloc[-cfg.pairs_formation:]
    if len(window) < cfg.pairs_formation:
        return []
    logp = np.log(window)
    rets = logp.diff().dropna()
    corr = rets.corr()
    cands = []
    cols = list(px.columns)
    for a, b in itertools.combinations(cols, 2):
        c = corr.loc[a, b]
        if c >= cfg.pairs_corr_min:
            cands.append((c, a, b))
    cands.sort(reverse=True)

    picked, used = [], set()
    for c, a, b in cands[:120]:  # cap the stationarity tests for speed
        if a in used or b in used:
            continue
        ya, xb = logp[a].to_numpy(), logp[b].to_numpy()
        X = np.column_stack([np.ones_like(xb), xb])
        coef, *_ = np.linalg.lstsq(X, ya, rcond=None)
        resid = ya - X @ coef
        tstat = _adf_tstat(resid)
        if tstat < cfg.pairs_adf_tstat:
            picked.append((a, b, float(np.var(resid))))
            used.update((a, b))
        if len(picked) >= cfg.pairs_n:
            break
    return picked


# ---------------------------------------------------------------------------
# Kalman hedge-ratio filter
# ---------------------------------------------------------------------------

class KalmanPair:
    """State theta=[alpha, beta]; obs y_t = [1, x_t] @ theta + eps."""

    def __init__(self, y: str, x: str, resid_var: float, delta: float):
        self.yname, self.xname = y, x
        self.theta = np.zeros(2)
        self.P = np.eye(2)
        self.Q = (delta / (1 - delta)) * np.eye(2)
        self.R = max(resid_var, 1e-8)
        self.initialized = False
        # trailing innovation variance for a properly-scaled trading z-score.
        # (The Kalman's own S is anchored to the spread *level* variance and is
        #  far too large to normalize one-step innovations, so we track the
        #  innovation's own EWMA variance — the standard Chan approach.)
        self.ewma_var = max(resid_var, 1e-8)
        self.ewma_lam = 0.96
        self.n_seen = 0
        # trading state
        self.position = 0      # +1 long spread, -1 short spread
        self.days_held = 0
        self.dead = False      # killed by structural-break stop

    def update(self, ly: float, lx: float) -> tuple[float, float]:
        """One predict/update step on log prices. Returns (z, beta)."""
        H = np.array([1.0, lx])
        if not self.initialized:
            self.theta = np.array([ly - lx, 1.0])
            self.initialized = True
        # predict
        P = self.P + self.Q
        # innovation
        yhat = H @ self.theta
        e = ly - yhat
        S = H @ P @ H + self.R
        # trading z-score: innovation vs its own trailing volatility
        self.n_seen += 1
        if self.n_seen > 1:
            self.ewma_var = self.ewma_lam * self.ewma_var + (1 - self.ewma_lam) * e * e
        z = e / np.sqrt(max(self.ewma_var, 1e-12))
        # Kalman update
        Kg = P @ H / S
        self.theta = self.theta + Kg * e
        self.P = P - np.outer(Kg, H @ P)
        return float(z), float(self.theta[1])


def run_pairs_sleeve(px: pd.DataFrame, rebalance_dates: list, cfg) -> dict:
    """Walk-forward pairs book. Re-select pairs every 252 trading days.

    Returns daily sleeve returns (gross of sleeve sizing), a trade log,
    and the last spread z-series for the dashboard.
    """
    logp = np.log(px)
    rets = px.pct_change().fillna(0.0)
    dates = px.index
    n = len(dates)

    sleeve_ret = np.zeros(n)
    trade_log = []
    z_history = {}          # (y,x) -> list[(date, z)]
    active: list[KalmanPair] = []
    last_selection = -10**9

    start_i = cfg.pairs_formation
    # positions held as weight vector over (y, x) legs per pair
    for i in range(start_i, n):
        t = dates[i]
        # annual re-selection (on information through t-1)
        if i - last_selection >= 252:
            sel = select_pairs(px, dates[i - 1], cfg)
            active = [KalmanPair(a, b, rv, cfg.pairs_delta) for a, b, rv in sel]
            # burn in the filter on the formation window (no trading)
            for kp in active:
                for j in range(i - cfg.pairs_formation, i):
                    kp.update(float(logp.iloc[j][kp.yname]), float(logp.iloc[j][kp.xname]))
            last_selection = i

        if not active:
            continue
        live = [kp for kp in active if not kp.dead]
        if not live:
            continue
        per_pair = 1.0 / max(len(live), 1)

        for kp in live:
            # PnL today from yesterday's position (T+1 discipline: position was
            # set on yesterday's z, earns today's returns)
            if kp.position != 0:
                pnl = kp.position * per_pair * 0.5 * (
                    rets.iloc[i][kp.yname] - kp.beta_clamped * rets.iloc[i][kp.xname])
                sleeve_ret[i] += pnl
                kp.days_held += 1

            z, beta = kp.update(float(logp.iloc[i][kp.yname]), float(logp.iloc[i][kp.xname]))
            kp.beta_clamped = float(np.clip(beta, 0.2, 3.0))
            key = (kp.yname, kp.xname)
            z_history.setdefault(key, []).append((t, z))

            # trading rules on today's z (position effective tomorrow)
            if kp.position == 0:
                if abs(z) > cfg.pairs_entry_z and abs(z) < cfg.pairs_stop_z:
                    kp.position = -int(np.sign(z))  # fade the spread
                    kp.days_held = 0
                    trade_log.append({"date": str(t.date()), "pair": f"{kp.yname}/{kp.xname}",
                                      "action": "enter", "z": round(z, 2)})
            else:
                stop = abs(z) > cfg.pairs_stop_z
                exit_band = abs(z) < cfg.pairs_exit_z
                timeout = kp.days_held >= cfg.pairs_max_hold
                if stop or exit_band or timeout:
                    trade_log.append({"date": str(t.date()), "pair": f"{kp.yname}/{kp.xname}",
                                      "action": "stop" if stop else "exit", "z": round(z, 2)})
                    kp.position = 0
                    if stop:
                        kp.dead = True  # structural break -> retire until re-selection

    sleeve = pd.Series(sleeve_ret, index=dates, name="pairs")
    return {"returns": sleeve, "trades": trade_log, "z_history": z_history,
            "final_pairs": [(kp.yname, kp.xname, kp.position,
                             round(getattr(kp, "beta_clamped", 1.0), 3), kp.dead)
                            for kp in active]}
