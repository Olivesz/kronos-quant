"""Regime-model horse race (KRONOS-X, answers Q1 & Q2).

Pre-registered protocol (DESIGN2.md §1.4):
  * features: (market return, log GK realized vol 10d) — identical for all
  * walk-forward: expanding window, min 750 obs, refit every 21d
  * SJM lambda chosen on the tuning segment (predictions before 2019-01-01)
  * headline metric: mean one-step predictive log-density of returns on the
    evaluation segment (2019-01-01 onward) — label-free and causally fair
  * plus: crash-detection latency, persistence stats, economic value
  * decision rule: production engine = predictive winner unless the economic
    test contradicts by > 0.15 net Sharpe
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import logsumexp

from kronos.regime import GaussianHMM
from kronos.dhmm import DurationHMM
from kronos.sjm import JumpModel

EVAL_START = "2019-01-01"

CRASH_EPISODES = {
    "Aug-2015 flash": "2015-08-17",
    "Feb-2018 volmageddon": "2018-02-01",
    "COVID crash": "2020-02-20",
    "2022 bear": "2022-01-03",
}


# ---------------------------------------------------------------------------
# features
# ---------------------------------------------------------------------------

def build_features_gk(mkt_rets: pd.Series, gk_var_mkt: pd.Series,
                      vol_window: int = 10) -> pd.DataFrame:
    rv = np.sqrt(gk_var_mkt.rolling(vol_window, min_periods=5).mean() * 252)
    feats = pd.DataFrame({
        "ret": mkt_rets,
        "logvol": np.log(rv.clip(lower=1e-4)),
    }).dropna()
    return feats


# ---------------------------------------------------------------------------
# walk-forward scorers (one per model family, shared protocol)
# ---------------------------------------------------------------------------

def _hmm_family_walkforward(make_model, X: np.ndarray, Kreg: int,
                            min_train: int, refit_every: int,
                            regime_probs_fn=None) -> dict:
    """Generic walk-forward for EM models with .fit(init_from=) warm starts.

    Returns causal predictive log-densities and causal regime probabilities.
    """
    T = X.shape[0]
    pred_ld = np.full(T, np.nan)       # log p(r_t | F_{t-1}), stored at t
    reg_probs = np.full((T, Kreg), np.nan)
    model = None
    t = min_train
    refits = 0
    while t < T:
        m = make_model(first=(model is None))
        model = m.fit(X[:t], init_from=model)
        refits += 1
        t_next = min(t + refit_every, T)
        logB = model._log_obs(X[:t_next])
        la = model._forward(logB)
        filt = np.exp(la - logsumexp(la, axis=1, keepdims=True))
        pred = filt[:-1] @ model.A_                  # P(s_t | F_{t-1})
        mu = model.means_[:, 0]
        sd = np.sqrt(model.covs_[:, 0, 0])
        r = X[1:t_next, 0]
        dens = (pred * np.exp(-0.5 * ((r[:, None] - mu) / sd) ** 2)
                / (sd * np.sqrt(2 * np.pi))).sum(axis=1)
        ld = np.log(np.maximum(dens, 1e-300))        # entry i = log p(r_{i+1}|F_i)
        lo = max(t - 1, 0)
        pred_ld[lo + 1:t_next] = ld[lo:t_next - 1]
        fp = regime_probs_fn(filt) if regime_probs_fn else filt
        reg_probs[t - 1:t_next] = fp[t - 1:t_next]
        t = t_next
    return {"pred_ld": pred_ld, "reg_probs": reg_probs, "refits": refits}


def hmm_walkforward(X, K=3, min_train=750, refit_every=21, seed=42):
    def make(first):
        return GaussianHMM(K, 200 if first else 25, 1e-6, seed)
    return _hmm_family_walkforward(make, X, K, min_train, refit_every)


def dhmm_walkforward(X, K=3, r=3, min_train=750, refit_every=21, seed=42):
    holder = {}
    def make(first):
        m = DurationHMM(K, r, 200 if first else 25, 1e-6, seed)
        holder["m"] = m
        return m
    return _hmm_family_walkforward(make, X, K, min_train, refit_every,
                                   regime_probs_fn=lambda f: holder["m"].regime_probs(f))


def sjm_walkforward(X, K=3, lam=16.0, min_train=750, refit_every=21, seed=42):
    T = X.shape[0]
    pred_ld = np.full(T, np.nan)
    reg_probs = np.full((T, K), np.nan)
    t = min_train
    refits = 0
    while t < T:
        jm = JumpModel(K, lam=lam, seed=seed).fit(X[:t])
        refits += 1
        t_next = min(t + refit_every, T)
        states = jm.online_states(X[:t_next])        # causal terminal states
        mu = jm.means_[:, 0]
        sd = np.sqrt(jm.covs_[:, 0, 0])
        for s_idx in range(max(t - 1, 1), t_next):
            st = states[s_idx - 1]                   # state known at s-1
            pred = jm.A_[st]
            r = X[s_idx, 0]
            dens = (pred * np.exp(-0.5 * ((r - mu) / sd) ** 2)
                    / (sd * np.sqrt(2 * np.pi))).sum()
            pred_ld[s_idx] = np.log(max(dens, 1e-300))
            onehot = np.zeros(K); onehot[states[s_idx]] = 1.0
            reg_probs[s_idx] = onehot
        t = t_next
    return {"pred_ld": pred_ld, "reg_probs": reg_probs, "refits": refits}


# ---------------------------------------------------------------------------
# evaluation metrics
# ---------------------------------------------------------------------------

def causal_regime_series(reg_probs: np.ndarray, idx: pd.DatetimeIndex,
                         cfg) -> pd.Series:
    """Identical hysteresis stabilizer for every model (it's part of the
    platform, the engine is the swappable piece)."""
    T, K = reg_probs.shape
    regime = np.full(T, -1)
    current, streak_state, streak, dwell = -1, -1, 0, 0
    filled = np.where(np.isnan(reg_probs), -1.0, reg_probs)
    argmax = filled.argmax(axis=1)
    maxp = filled.max(axis=1)
    for i in range(T):
        if np.isnan(reg_probs[i]).any():
            continue
        cand = argmax[i]
        if current == -1:
            current = cand
        dwell += 1
        if cand != current and maxp[i] >= cfg.hmm_hysteresis_prob:
            if cand == streak_state:
                streak += 1
            else:
                streak_state, streak = cand, 1
            confirmed = streak >= cfg.hmm_hysteresis_days
            urgent = maxp[i] >= cfg.hmm_urgent_prob
            if confirmed and (dwell >= cfg.hmm_min_dwell or urgent):
                current = cand
                streak_state, streak = -1, 0
                dwell = 0
        else:
            streak_state, streak = -1, 0
        regime[i] = current
    return pd.Series(regime, index=idx, name="regime")


def crash_latency(regime: pd.Series, episode_start: str, max_days: int = 60) -> int:
    """Business days from episode start until stress (regime>=1) flagged for
    2 consecutive days. Returns max_days if never flagged."""
    seg = regime.loc[episode_start:]
    if len(seg) < 3:
        return max_days
    stress = (seg >= 1).to_numpy()
    for i in range(len(stress) - 1):
        if i >= max_days:
            break
        if stress[i] and stress[i + 1]:
            return i
    return max_days


def persistence_stats(regime: pd.Series) -> dict:
    r = regime[regime >= 0].to_numpy()
    if len(r) == 0:
        return {"switches_per_year": 0.0, "median_dwell": 0.0}
    switches = (np.diff(r) != 0)
    n_sw = int(switches.sum())
    years = len(r) / 252
    seg_lengths = np.diff(np.flatnonzero(np.r_[True, switches, True]))
    return {"switches_per_year": n_sw / years,
            "median_dwell": float(np.median(seg_lengths))}


def oos_mean_logscore(pred_ld: np.ndarray, idx: pd.DatetimeIndex,
                      start: str = EVAL_START) -> float:
    s = pd.Series(pred_ld, index=idx)
    seg = s.loc[start:].dropna()
    return float(seg.mean())


# ---------------------------------------------------------------------------
# the race
# ---------------------------------------------------------------------------

def select_sjm_lambda(X: np.ndarray, idx: pd.DatetimeIndex, cfg,
                      grid=(2.0, 4.0, 8.0, 16.0, 32.0, 64.0)) -> dict:
    """Walk-forward predictive log-score on the TUNING segment only."""
    scores = {}
    for lam in grid:
        wf = sjm_walkforward(X, K=cfg.n_states, lam=lam,
                             min_train=cfg.hmm_min_train,
                             refit_every=cfg.hmm_refit_every, seed=cfg.seed)
        s = pd.Series(wf["pred_ld"], index=idx)
        tune = s.loc[:EVAL_START].dropna()           # strictly pre-eval
        scores[lam] = float(tune.mean())
    best = max(scores, key=scores.get)
    return {"grid_scores": scores, "lam": best}


def run_horserace(feats: pd.DataFrame, cfg) -> dict:
    """All models, all metrics. Returns the race table (economic value is
    appended by the caller, which owns the backtester)."""
    X = feats.to_numpy()
    idx = feats.index
    out = {"eval_start": EVAL_START, "models": {}}

    lam_sel = select_sjm_lambda(X, idx, cfg)
    out["sjm_lambda"] = lam_sel

    runs = {
        "HMM-3": lambda: hmm_walkforward(X, 3, cfg.hmm_min_train,
                                         cfg.hmm_refit_every, cfg.seed),
        "SJM-3": lambda: sjm_walkforward(X, 3, lam_sel["lam"], cfg.hmm_min_train,
                                         cfg.hmm_refit_every, cfg.seed),
        "DurHMM-3x3": lambda: dhmm_walkforward(X, 3, 3, cfg.hmm_min_train,
                                               cfg.hmm_refit_every, cfg.seed),
    }
    for name, fn in runs.items():
        wf = fn()
        regime = causal_regime_series(wf["reg_probs"], idx, cfg)
        rec = {
            "logscore_oos": oos_mean_logscore(wf["pred_ld"], idx),
            "refits": wf["refits"],
            **persistence_stats(regime),
            "latency": {ep: crash_latency(regime, d)
                        for ep, d in CRASH_EPISODES.items()},
        }
        out["models"][name] = rec
        out["models"][name]["_regime"] = regime      # caller uses, then strips
        out["models"][name]["_reg_probs"] = wf["reg_probs"]

    # Q1: how many regimes? (log-score vs K, both families)
    ksweep = {"HMM": {}, "SJM": {}}
    for K in (2, 3, 4, 5):
        wf = hmm_walkforward(X, K, cfg.hmm_min_train, cfg.hmm_refit_every, cfg.seed)
        ksweep["HMM"][K] = oos_mean_logscore(wf["pred_ld"], idx)
        wf = sjm_walkforward(X, K, lam_sel["lam"], cfg.hmm_min_train,
                             cfg.hmm_refit_every, cfg.seed)
        ksweep["SJM"][K] = oos_mean_logscore(wf["pred_ld"], idx)
    out["ksweep"] = ksweep
    return out
