"""Online ensemble meta-allocation over strategy sleeves (KRONOS-X, Q4).

Exponentiated-gradient / Hedge family with provable regret bounds:

    w_{k,t+1}  proportional to  w_{k,t} * exp(eta * r_{k,t} / scale_{k,t})

Variants:
  * hedge        — plain multiplicative weights
  * fixed_share  — mixes a uniform restart in each step (tracks regime shifts)
  * regime_hedge — separate expert-weight vector per detected regime
                   (the hybrid: regimes + learning)

All causal: the weight applied to day t's returns was computed from data
through t-1. Rewards are vol-normalized so no sleeve dominates by leverage.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def run_meta(sleeves: pd.DataFrame, method: str = "hedge",
             eta: float | None = None, share: float = 0.005,
             regime: pd.Series | None = None, vol_halflife: int = 63) -> dict:
    """sleeves: (T, K) daily sleeve returns. Returns blended returns,
    weight history, and the regret curve vs best-in-hindsight."""
    R = sleeves.to_numpy()
    T, K = R.shape
    if eta is None:
        eta = np.sqrt(8 * np.log(K) / max(T, 2))

    # causal vol scale per sleeve (EWMA std, shifted one day)
    scale = (sleeves.ewm(halflife=vol_halflife).std()
             .shift(1).fillna(sleeves.std().mean()).to_numpy())
    scale = np.maximum(scale, 1e-5)

    n_reg = 3
    if method == "regime_hedge":
        assert regime is not None
        reg = regime.reindex(sleeves.index).ffill().fillna(0).astype(int).to_numpy()
        reg = np.clip(reg, 0, n_reg - 1)
        logw_bank = np.zeros((n_reg, K))
    logw = np.zeros(K)

    W = np.zeros((T, K))
    blended = np.zeros(T)
    for t in range(T):
        if method == "regime_hedge":
            logw = logw_bank[reg[t - 1] if t > 0 else 0]
        w = np.exp(logw - logw.max())
        w /= w.sum()
        W[t] = w
        blended[t] = w @ R[t]
        # update with day-t rewards (available at close of t, used t+1)
        g = eta * R[t] / scale[t]
        g = np.clip(g, -10, 10)
        if method == "regime_hedge":
            bank = logw_bank[reg[t]]
            bank += g
            wb = np.exp(bank - bank.max()); wb /= wb.sum()
            wb = (1 - share) * wb + share / K
            logw_bank[reg[t]] = np.log(wb)
        else:
            logw = logw + g
            w_new = np.exp(logw - logw.max()); w_new /= w_new.sum()
            if method == "fixed_share":
                w_new = (1 - share) * w_new + share / K
            logw = np.log(w_new)

    blended_s = pd.Series(blended, index=sleeves.index)
    # regret vs best sleeve in hindsight, in vol-normalized reward units
    norm_R = R / scale
    cum_expert = norm_R.cumsum(axis=0)
    learner = (W * norm_R).sum(axis=1).cumsum()
    regret = cum_expert.max(axis=1) - learner
    return {"returns": blended_s,
            "weights": pd.DataFrame(W, index=sleeves.index, columns=sleeves.columns),
            "regret": pd.Series(regret, index=sleeves.index),
            "eta": float(eta)}


def gates_blend(sleeves: pd.DataFrame, regime: pd.Series,
                gate_map: dict) -> pd.Series:
    """The v1 alternative: hand-designed regime -> sleeve-weight gates,
    applied causally (regime known at t-1 weights day t)."""
    from config import REGIME_NAMES
    reg = regime.reindex(sleeves.index).ffill().fillna(1).astype(int)
    cols = list(sleeves.columns)
    Wm = np.zeros((len(sleeves), len(cols)))
    for rid, rname in REGIME_NAMES.items():
        gates = gate_map.get(rname, {})
        w = np.array([gates.get(c, 0.0) for c in cols])
        if w.sum() > 0:
            w = w / w.sum()
        else:
            w = np.full(len(cols), 1 / len(cols))
        Wm[(reg == rid).to_numpy()] = w
    Wm = np.roll(Wm, 1, axis=0)  # causal: regime at t-1 sets weights for t
    Wm[0] = 1 / len(cols)
    return pd.Series((Wm * sleeves.to_numpy()).sum(axis=1), index=sleeves.index)
