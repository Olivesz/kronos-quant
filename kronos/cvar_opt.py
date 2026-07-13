"""Minimum-CVaR portfolio via the Rockafellar-Uryasev LP (KRONOS-X, Q5b).

CVaR minimization over scenario returns is exactly linear:

    min_{w, a, u}   a + 1/((1-beta) S) * sum_s u_s  +  tc * sum_i t_i
    s.t.            u_s >= -r_s . w - a,   u >= 0
                    sum_i w_i = 1,         0 <= w_i <= cap
                    t_i >= w_i - w_prev_i, t_i >= -(w_i - w_prev_i)   (turnover)

Solved with scipy's HiGHS. Scenario variants: plain historical, EWMA-weighted
(recent days matter more), and regime-conditional (only days whose regime
matches the current one — the KRONOS twist).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog


def min_cvar_weights(scenarios: np.ndarray, beta: float = 0.95,
                     cap: float = 0.12, w_prev: np.ndarray | None = None,
                     turnover_penalty: float = 0.0,
                     scenario_weights: np.ndarray | None = None) -> dict:
    """scenarios: (S, N) daily returns. Returns dict(weights, cvar, status)."""
    S, N = scenarios.shape
    sw = np.full(S, 1.0 / S) if scenario_weights is None else \
        scenario_weights / scenario_weights.sum()

    use_to = turnover_penalty > 0 and w_prev is not None
    # variable layout: [w (N), a (1), u (S), t (N if turnover)]
    n_var = N + 1 + S + (N if use_to else 0)
    c = np.zeros(n_var)
    c[N] = 1.0                          # alpha
    c[N + 1:N + 1 + S] = sw / (1 - beta)
    if use_to:
        c[N + 1 + S:] = turnover_penalty

    # u_s >= -r_s.w - a  ->  -r_s.w - a - u_s <= 0
    A_ub = np.zeros((S + (2 * N if use_to else 0), n_var))
    b_ub = np.zeros(A_ub.shape[0])
    A_ub[:S, :N] = -scenarios
    A_ub[:S, N] = -1.0
    A_ub[np.arange(S), N + 1 + np.arange(S)] = -1.0
    if use_to:
        # w_i - t_i <= w_prev_i   and   -w_i - t_i <= -w_prev_i
        r0 = S
        for i in range(N):
            A_ub[r0 + i, i] = 1.0
            A_ub[r0 + i, N + 1 + S + i] = -1.0
            b_ub[r0 + i] = w_prev[i]
            A_ub[r0 + N + i, i] = -1.0
            A_ub[r0 + N + i, N + 1 + S + i] = -1.0
            b_ub[r0 + N + i] = -w_prev[i]

    A_eq = np.zeros((1, n_var)); A_eq[0, :N] = 1.0
    b_eq = np.array([1.0])
    bounds = [(0.0, cap)] * N + [(None, None)] + [(0.0, None)] * S
    if use_to:
        bounds += [(0.0, None)] * N

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        # graceful fallback: equal weight
        return {"weights": np.full(N, 1.0 / N), "cvar": np.nan,
                "status": res.message}
    w = res.x[:N]
    w = np.maximum(w, 0)
    w /= w.sum()
    port = scenarios @ w
    q = np.quantile(port, 1 - beta)
    cvar = float(-(port[port <= q] * 1.0).mean()) if (port <= q).any() else 0.0
    return {"weights": w, "cvar": cvar, "status": "ok"}


def cvar_bakeoff(rets: pd.DataFrame, regime: pd.Series, cfg,
                 window: int = 252, rebalance: int = 21) -> dict:
    """Walk-forward comparison: HRP vs min-CVaR (historical / EWMA /
    regime-conditional scenarios). Long-only, same cap, same cadence.
    Costs: same linear cost on turnover for every engine (flat 3.5bp)."""
    from kronos.covariance import shrunk_cov
    from kronos.hrp import hrp_weights

    dates = rets.index
    T = len(dates)
    engines = ["hrp", "cvar_hist", "cvar_ewma", "cvar_regime"]
    port = {e: np.zeros(T) for e in engines}
    prev = dict.fromkeys(engines)
    turn = dict.fromkeys(engines, 0.0)
    realized = {e: [] for e in engines}
    cost_bps = 3.5

    half = 63
    lam = np.exp(-np.log(2) / half)

    start = max(window, cfg.hmm_min_train)
    for i in range(start, T, rebalance):
        sub = rets.iloc[i - window:i]
        scen = sub.to_numpy()
        N = scen.shape[1]

        ws = {}
        cov = shrunk_cov(sub, cfg.cov_ewma_halflife, window)
        ws["hrp"] = hrp_weights(cov).to_numpy()

        ws["cvar_hist"] = min_cvar_weights(scen, cap=cfg.max_weight,
                                           w_prev=prev["cvar_hist"],
                                           turnover_penalty=0.001)["weights"]
        sw = lam ** np.arange(len(scen) - 1, -1, -1)
        ws["cvar_ewma"] = min_cvar_weights(scen, cap=cfg.max_weight,
                                           w_prev=prev["cvar_ewma"],
                                           turnover_penalty=0.001,
                                           scenario_weights=sw)["weights"]
        # regime-conditional: scenario pool = trailing 3y days in the SAME
        # regime as today (fallback to plain window if too few)
        reg_now = regime.reindex([dates[i - 1]]).iloc[0] if dates[i - 1] in regime.index else -1
        pool = rets.iloc[max(0, i - 756):i]
        reg_pool = regime.reindex(pool.index)
        match = pool[(reg_pool == reg_now).to_numpy()]
        scen_r = match.to_numpy() if len(match) >= 120 else scen
        ws["cvar_regime"] = min_cvar_weights(scen_r, cap=cfg.max_weight,
                                             w_prev=prev["cvar_regime"],
                                             turnover_penalty=0.001)["weights"]

        j_end = min(i + rebalance, T)
        R = rets.iloc[i:j_end].to_numpy()
        for e in engines:
            w = ws[e]
            port[e][i:j_end] = R @ w
            if prev[e] is not None:
                tn = float(np.abs(w - prev[e]).sum())
                turn[e] += tn
                port[e][i] -= tn * cost_bps / 1e4
            prev[e] = w

    years = (T - start) / 252
    out = {}
    for e in engines:
        r = pd.Series(port[e][start:], index=dates[start:])
        q = r.quantile(0.05)
        out[e] = {
            "ann_ret": float(r.mean() * 252),
            "vol": float(r.std() * np.sqrt(252)),
            "sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0,
            "cvar95": float(-r[r <= q].mean()),
            "max_dd": float(((1 + r).cumprod() / (1 + r).cumprod().cummax() - 1).min()),
            "turnover_per_year": turn[e] / years,
        }
    return out
