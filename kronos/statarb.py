"""Avellaneda-Lee eigenportfolio statistical arbitrage (KRONOS-X).

The canonical modern stat-arb (Avellaneda & Lee 2010): extract market/sector
factors as PCA eigenportfolios (count chosen by the Marchenko-Pastur edge,
courtesy of kronos.rmt), regress each stock on them, model the cumulative
residual as an Ornstein-Uhlenbeck process, and trade its s-score:

  open long  s < -s_open   (residual cheap vs factors)
  open short s > +s_open
  close when |s| inside s_close, or the OU fit degrades.

Only stocks whose residual mean-reverts fast (half-life <= hl_max days)
are tradable. Dollar-neutral by construction: each unit of stock is hedged
with its beta-weighted eigenportfolio basket.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kronos.rmt import n_signal_factors, corr_from_cov


# trading parameters (pre-registered; counted in the trials ledger)
S_OPEN = 1.25
S_CLOSE = 0.50
HL_MAX = 30          # max residual half-life in trading days
PCA_WINDOW = 252
OU_WINDOW = 60
REFIT_EVERY = 5      # weekly
COST_BPS = 3.5       # linear cost per unit turnover (commission+spread)


def eigenportfolios(rets_window: pd.DataFrame, max_m: int = 15) -> tuple[np.ndarray, int]:
    """Returns (Q, m): Q is (N, m) name-weights of each eigenportfolio."""
    sd = rets_window.std().to_numpy()
    sd = np.where(sd < 1e-8, 1e-8, sd)
    Z = (rets_window - rets_window.mean()) / sd
    corr = np.clip(np.cov(Z.T.to_numpy()), -1, 1)
    T = len(rets_window)
    eigval, eigvec = np.linalg.eigh(corr)
    eigval = eigval[::-1]; eigvec = eigvec[:, ::-1]
    m, _ = n_signal_factors(eigval, corr.shape[0] / T)
    m = int(np.clip(m, 1, max_m))
    Q = eigvec[:, :m] / sd[:, None]            # A-L: v_ji / sigma_i
    # sign convention: largest-|loading| component positive
    for j in range(m):
        i_star = np.abs(Q[:, j]).argmax()
        if Q[i_star, j] < 0:
            Q[:, j] = -Q[:, j]
    Q = Q / np.abs(Q).sum(axis=0, keepdims=True)   # normalize gross to 1
    return Q, m


def fit_factor_model(rets_window: pd.DataFrame) -> dict:
    """Weekly piece: eigenportfolios + frozen betas from the early window.

    Betas are estimated on the window EXCLUDING the trailing OU_WINDOW, so
    the evaluation residuals are genuinely out-of-sample. In-sample residuals
    (with intercept) sum to zero, making their cumsum a Brownian bridge that
    fakes mean reversion for every name — frozen betas restore a real
    unit-root null for the t-stat filter."""
    Q, m = eigenportfolios(rets_window)
    R = rets_window.to_numpy()
    F = R @ Q
    T = len(R)
    fit = slice(0, T - OU_WINDOW)
    X_fit = np.column_stack([np.ones(T - OU_WINDOW), F[fit]])
    coef, *_ = np.linalg.lstsq(X_fit, R[fit], rcond=None)   # (m+1, N)
    return {"Q": Q, "coef": coef, "m": m}


def ou_sscores(rets_tail: pd.DataFrame, model: dict) -> pd.DataFrame:
    """Daily piece: OU fit on cumulative OOS residuals of the trailing
    OU_WINDOW with the frozen weekly factor model."""
    Q, coef = model["Q"], model["coef"]
    R = rets_tail.to_numpy()[-OU_WINDOW:]
    F = R @ Q
    X_ev = np.column_stack([np.ones(len(R)), F])
    resid = R - X_ev @ coef                      # genuine OOS residuals
    Xcum = resid.cumsum(axis=0)                  # cumulative residual
    # AR(1) per name, vectorized: X_t = a + b X_{t-1} + z
    Y, L = Xcum[1:], Xcum[:-1]
    Lm, Ym = L.mean(axis=0), Y.mean(axis=0)
    cov = ((L - Lm) * (Y - Ym)).sum(axis=0)
    var = ((L - Lm) ** 2).sum(axis=0)
    b = np.where(var > 1e-16, cov / np.maximum(var, 1e-16), np.nan)
    a = Ym - b * Lm
    z = Y - (a + b * L)
    s2z = z.var(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        hl = -np.log(2) / np.log(np.abs(b))
        m_eq = a / (1 - b)
        sigma_eq = np.sqrt(s2z / (1 - b ** 2))
        s = (Xcum[-1] - m_eq) / sigma_eq
        # unit-root significance: t-stat of (b - 1); a random-walk residual
        # passes the half-life screen spuriously ~half the time without this
        se_b = np.sqrt(s2z * len(Y) / np.maximum((len(Y) - 2) * var, 1e-16))
        t_ur = (b - 1.0) / np.maximum(se_b, 1e-12)
    ok = ((b > 0.05) & (b < 1.0) & (hl <= HL_MAX) & (sigma_eq > 1e-10)
          & (t_ur < -2.0))
    s_entry = np.where(ok, s, np.nan)            # strict screen gates ENTRY
    s_raw = np.where((b > 0) & (b < 1.0) & (sigma_eq > 1e-10), s, np.nan)
    out = pd.DataFrame({"s": s_entry, "s_raw": s_raw, "b": b, "halflife": hl},
                       index=rets_tail.columns)
    out["beta"] = list(coef[1:].T)              # per-name factor betas
    return out


def run_statarb_sleeve(px: pd.DataFrame, cfg) -> dict:
    """Walk-forward stat-arb book. Returns daily sleeve returns (gross
    exposure normalized to ~1; the caller sizes the sleeve)."""
    rets = px.pct_change().fillna(0.0)
    dates = px.index
    T, N = rets.shape
    names = list(px.columns)

    sleeve = np.zeros(T)
    position = pd.Series(0.0, index=names)      # +1 long / -1 short per name
    net_w = np.zeros(N)                          # hedged name-level weights
    n_open_hist, m_hist, s_example = [], [], []
    trades = 0
    prev_net = np.zeros(N)

    start = PCA_WINDOW + 5
    model = None
    pos = np.zeros(N)
    for i in range(start, T):
        # PnL from yesterday's book (T+1 discipline)
        sleeve[i] = float(net_w @ rets.iloc[i].to_numpy())

        if (i - start) % REFIT_EVERY == 0:       # weekly: factors + betas
            model = fit_factor_model(rets.iloc[i - PCA_WINDOW:i])
            m_hist.append(model["m"])

        # daily: s-scores with frozen weekly model, data through today's close
        sc = ou_sscores(rets.iloc[i - OU_WINDOW + 1:i + 1], model)
        s_arr = sc["s"].to_numpy()        # filtered: entry signal
        s_raw = sc["s_raw"].to_numpy()    # unfiltered: exit signal
        b_arr = sc["b"].to_numpy()
        new_pos = pos.copy()
        for k in range(N):
            if pos[k] == 0:
                s = s_arr[k]
                if np.isnan(s):
                    continue
                if s < -S_OPEN:
                    new_pos[k] = 1.0
                elif s > S_OPEN:
                    new_pos[k] = -1.0
            else:
                sx = s_raw[k]
                # structural stop: residual no longer mean-reverting at all
                if np.isnan(sx) or b_arr[k] >= 1.0:
                    new_pos[k] = 0.0
                elif pos[k] > 0 and sx > -S_CLOSE:
                    new_pos[k] = 0.0
                elif pos[k] < 0 and sx < S_CLOSE:
                    new_pos[k] = 0.0
        pos = new_pos

        # hedged book: stock minus beta-weighted eigenportfolio baskets
        w = np.zeros(N)
        open_idx = np.flatnonzero(pos)
        Q = model["Q"]
        for k in open_idx:
            w[k] += pos[k]
            w -= pos[k] * (Q @ sc["beta"].iloc[k])
        gross = np.abs(w).sum()
        if gross > 1e-9:
            w = w / gross                        # sleeve gross = 1
        turn = np.abs(w - prev_net).sum()
        if turn > 1e-9:
            sleeve[i] -= turn * COST_BPS / 1e4
            trades += 1
        prev_net = w
        net_w = w
        n_open_hist.append(len(open_idx))
        if i % 21 == 0:
            s_example.append((str(dates[i].date()),
                              float(np.nanmedian(np.abs(s_arr)))))

    sleeve_s = pd.Series(sleeve, index=dates, name="statarb")
    return {"returns": sleeve_s,
            "n_open_mean": float(np.mean(n_open_hist)) if n_open_hist else 0.0,
            "m_factors_median": float(np.median(m_hist)) if m_hist else 0.0,
            "median_abs_s": s_example,
            "trade_days": trades,
            "rebalances": len(m_hist)}
