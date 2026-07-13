"""'Regimes or fat tails?' — the K-hallucination study (KRONOS-X², Study 1).

Pre-registered in DESIGN3.md. Two parts:

  * Monte Carlo (H1/H2): on worlds with KNOWN K=3 — one Gaussian-emission,
    one t-emission (nu=5) — does held-out predictive-density model selection
    over K=2..5 recover K=3? Hypothesis: the Gaussian family hallucinates
    K>3 on the fat-tailed world; the t family does not; both behave on the
    Gaussian world.

  * Real data (H3): walk-forward K-curves for both families on (SPY return,
    GK log-vol) features, with Amisano-Giacomini tests on the daily
    log-score differentials and a Model Confidence Set over the full regime-
    model universe {Gaussian K2..5, t K2..5, SJM-3, DurHMM-3x3}.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import logsumexp

from kronos.regime import GaussianHMM
from kronos.thmm import StudentTHMM
from kronos.dhmm import DurationHMM

EVAL_START = "2019-01-01"

# the same synthetic geometry used by every regime gate (realistic scales)
MEANS = np.array([[0.0008, np.log(0.10)],
                  [0.0000, np.log(0.20)],
                  [-0.0015, np.log(0.35)]])
SCALES = np.array([[0.006, 0.08], [0.012, 0.10], [0.022, 0.12]])
A_TRUE = np.array([[0.97, 0.02, 0.01],
                   [0.03, 0.94, 0.03],
                   [0.02, 0.04, 0.94]])


def gen_world(T: int, nu: float | None, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    s = np.zeros(T, dtype=int)
    for t in range(1, T):
        s[t] = rng.choice(3, p=A_TRUE[s[t - 1]])
    z = rng.normal(size=(T, 2))
    if nu is not None:
        g = rng.chisquare(nu, size=T) / nu
        z = z / np.sqrt(g)[:, None] * np.sqrt((nu - 2) / nu)
    return MEANS[s] + SCALES[s] * z


def heldout_logscore(model, X: np.ndarray, t0: int) -> float:
    logB = model._log_obs(X)
    la = model._forward(logB)
    filt = np.exp(la - logsumexp(la, axis=1, keepdims=True))
    pred = filt[:-1] @ model.A_
    ld = model.return_marginal_logdens(pred, X[1:, 0])
    return float(ld[t0 - 1:].mean())


def mc_khallucination(n_seeds: int = 8, T: int = 3000, train: int = 2000,
                      Ks=(2, 3, 4, 5), nu_fat: float = 5.0) -> dict:
    """H1/H2: chosen-K distributions per (world, family)."""
    out = {}
    for wname, nu in (("gaussian_world", None), ("fat_world", nu_fat)):
        chosen = {"gauss": [], "t": []}
        curves = {"gauss": np.zeros((n_seeds, len(Ks))),
                  "t": np.zeros((n_seeds, len(Ks)))}
        for si in range(n_seeds):
            X = gen_world(T, nu, seed=1000 + si)
            for fam, cls in (("gauss", GaussianHMM), ("t", StudentTHMM)):
                scores = []
                for K in Ks:
                    m = cls(K, max_iter=120, seed=42).fit(X[:train],
                                                          n_restarts=2)
                    scores.append(heldout_logscore(m, X, train))
                curves[fam][si] = scores
                chosen[fam].append(Ks[int(np.argmax(scores))])
        out[wname] = {
            "chosen_K": {f: {str(k): int((np.array(c) == k).sum())
                             for k in Ks} for f, c in chosen.items()},
            "mean_curves": {f: np.round(curves[f].mean(axis=0), 4).tolist()
                            for f in curves},
            "frac_overfit": {f: float((np.array(c) > 3).mean())
                             for f, c in chosen.items()},
        }
    out["Ks"] = list(Ks)
    out["n_seeds"] = n_seeds
    return out


# ---------------------------------------------------------------------------
# real data: generic walk-forward that works for any HMM-family model
# ---------------------------------------------------------------------------

def generic_walkforward(make_model, X: np.ndarray, min_train: int,
                        refit_every: int) -> np.ndarray:
    """Daily causal predictive log-densities; pred_ld[t] = log p(r_t|F_{t-1})."""
    T = X.shape[0]
    pred_ld = np.full(T, np.nan)
    model = None
    t = min_train
    while t < T:
        m = make_model(first=(model is None))
        model = m.fit(X[:t], init_from=model)
        t_next = min(t + refit_every, T)
        logB = model._log_obs(X[:t_next])
        la = model._forward(logB)
        filt = np.exp(la - logsumexp(la, axis=1, keepdims=True))
        pred = filt[:-1] @ model.A_
        ld = model.return_marginal_logdens(pred, X[1:t_next, 0])
        lo = max(t - 1, 0)
        pred_ld[lo + 1:t_next] = ld[lo:t_next - 1]
        t = t_next
    return pred_ld


def realdata_study(feats: pd.DataFrame, cfg, sjm_lam: float) -> dict:
    """H3 + AG matrix + MCS over the regime-model universe."""
    from kronos.horserace import sjm_walkforward
    from kronos.infer import amisano_giacomini, model_confidence_set

    X = feats.to_numpy()
    idx = feats.index
    series = {}

    for K in (2, 3, 4, 5):
        def mk_g(first, K=K):
            return GaussianHMM(K, 200 if first else 25, 1e-6, cfg.seed)
        series[f"G{K}"] = generic_walkforward(mk_g, X, cfg.hmm_min_train,
                                              cfg.hmm_refit_every)
        def mk_t(first, K=K):
            return StudentTHMM(K, 200 if first else 25, 1e-6, cfg.seed)
        series[f"T{K}"] = generic_walkforward(mk_t, X, cfg.hmm_min_train,
                                              cfg.hmm_refit_every)

    def mk_d(first):
        return DurationHMM(3, 3, 200 if first else 25, 1e-6, cfg.seed)
    series["Dur3x3"] = generic_walkforward(mk_d, X, cfg.hmm_min_train,
                                           cfg.hmm_refit_every)
    series["SJM3"] = sjm_walkforward(X, 3, sjm_lam, cfg.hmm_min_train,
                                     cfg.hmm_refit_every, cfg.seed)["pred_ld"]

    df = pd.DataFrame(series, index=idx).loc[EVAL_START:].dropna()
    means = df.mean().to_dict()

    # final-fit nu estimates for the market (interesting in their own right)
    tm = StudentTHMM(3, seed=cfg.seed).fit(X)
    nus = np.round(tm.nus_, 1).tolist()

    ag = {}
    for a, b in (("T3", "G3"), ("T3", "G5"), ("G5", "G3"),
                 ("T3", "SJM3"), ("T5", "T3"), ("T3", "Dur3x3")):
        ag[f"{a}_vs_{b}"] = amisano_giacomini(df[a].to_numpy(),
                                              df[b].to_numpy())

    mcs = model_confidence_set(-df.to_numpy(), list(df.columns),
                               alpha=0.10, n_boot=1000)
    return {"logscores_eval": {k: round(float(v), 4) for k, v in means.items()},
            "ag": ag, "mcs": mcs, "market_nus_K3": nus,
            "n_eval_days": len(df)}
