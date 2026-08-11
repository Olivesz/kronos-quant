"""Gate X29: the Student-t regime engine wired into the production
walk-forward driver (DESIGN16 V2).

(a) Gaussian-emission world: the t-engine's walk-forward filtered-state
    accuracy must not regress vs the Gaussian engine (within 3pp), and its
    fitted nus must blow up toward the Gaussian clamp.
(b) Student-t(5)-emission world: the t-engine must be at least as accurate
    (minus 1pp) and strictly better on held-out predictive log-score.
(c) Causality: filtered probabilities and regime labels at time t must be
    invariant to truncating the future (test_trade's truncation trick).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

import numpy as np
import pandas as pd
from scipy.special import logsumexp

from config import CFG
from kronos.regime import GaussianHMM, build_features, walkforward_regimes
from kronos.thmm import StudentTHMM

T_TOTAL = 2400
TRAIN = 1500          # held-out log-score split
MU = np.array([0.0008, 0.0000, -0.0015])
SIG = np.array([0.006, 0.012, 0.022])
A_TRUE = np.array([[0.97, 0.02, 0.01],
                   [0.03, 0.94, 0.03],
                   [0.02, 0.04, 0.94]])

# lean walk-forward cfg for the synthetic worlds (identical for both engines)
WCFG = replace(CFG, hmm_min_train=600, hmm_refit_every=63)


def gen_returns(T, nu=None, seed=0):
    """Daily return Series from a 3-state chain; nu=None -> Gaussian
    innovations, else unit-variance-scaled Student-t(nu)."""
    r = np.random.default_rng(seed)
    s = np.zeros(T, dtype=int)
    for t in range(1, T):
        s[t] = r.choice(3, p=A_TRUE[s[t - 1]])
    z = r.normal(size=T)
    if nu is not None:
        g = r.chisquare(nu, size=T) / nu
        z = z / np.sqrt(g) * np.sqrt((nu - 2) / nu)
    idx = pd.bdate_range("2005-01-03", periods=T)
    return pd.Series(MU[s] + SIG[s] * z, index=idx), pd.Series(s, index=idx)


def wf_accuracy(rets, states, engine):
    rg = walkforward_regimes(rets, replace(WCFG, regime_engine=engine))
    filt = rg["filtered"].dropna()
    truth = states.reindex(filt.index)
    acc = float((filt.to_numpy().argmax(axis=1) == truth.to_numpy()).mean())
    return acc, rg


def oos_logscore(model, X, t0):
    logB = model._log_obs(X)
    la = model._forward(logB)
    filt = np.exp(la - logsumexp(la, axis=1, keepdims=True))
    pred = filt[:-1] @ model.A_
    ld = model.return_marginal_logdens(pred, X[1:, 0])
    return float(ld[t0 - 1:].mean())


t_start = time.time()

# --- (a) Gaussian world: no regression --------------------------------------
rets_g, st_g = gen_returns(T_TOTAL, nu=None, seed=29)
acc_gg, _ = wf_accuracy(rets_g, st_g, "gaussian")
acc_tg, rg_tg = wf_accuracy(rets_g, st_g, "thmm")
nus = rg_tg["model"].nus_
print(f"gauss world: gaussian acc {acc_gg:.1%} | t-engine acc {acc_tg:.1%} "
      f"(gap {100*(acc_tg-acc_gg):+.1f}pp) | est nus {np.round(nus, 0)}")
assert acc_tg >= acc_gg - 0.03, "t-engine regressed >3pp on a Gaussian world"
assert np.all(nus > 10), "nu should blow up toward Gaussian on Gaussian data"

# --- (b) t(5) world: at least as accurate, better log-score ------------------
rets_t, st_t = gen_returns(T_TOTAL, nu=5.0, seed=31)
acc_gt, _ = wf_accuracy(rets_t, st_t, "gaussian")
acc_tt, rg_tt = wf_accuracy(rets_t, st_t, "thmm")
print(f"t(5) world : gaussian acc {acc_gt:.1%} | t-engine acc {acc_tt:.1%} "
      f"(gap {100*(acc_tt-acc_gt):+.1f}pp)")
assert acc_tt >= acc_gt - 0.01, "t-engine must be >= Gaussian - 1pp on a t world"

X_t = build_features(rets_t, WCFG.hmm_vol_window).to_numpy()
tm = StudentTHMM(3, seed=42).fit(X_t[:TRAIN])
gm = GaussianHMM(3, seed=42).fit(X_t[:TRAIN])
s_t = oos_logscore(tm, X_t, TRAIN)
s_g = oos_logscore(gm, X_t, TRAIN)
print(f"t(5) world : held-out log-score t {s_t:.4f} vs gaussian {s_g:.4f} "
      f"(edge {s_t - s_g:+.4f})")
assert s_t > s_g, "t-engine must strictly beat Gaussian log-score on a t world"

# --- (c) causality: truncation invariance ------------------------------------
cut = rets_t.index[-300]
rg_trunc = walkforward_regimes(rets_t.loc[:cut], replace(WCFG, regime_engine="thmm"))
f_full = rg_tt["filtered"]
f_trunc = rg_trunc["filtered"].dropna()
common = f_trunc.index
maxdiff = float((f_full.loc[common] - f_trunc).abs().max().max())
reg_match = (rg_tt["regime"].loc[common] == rg_trunc["regime"].loc[common]).all()
print(f"causality  : max filtered-prob diff on shared dates = {maxdiff:.2e} | "
      f"regime labels identical = {bool(reg_match)}")
assert maxdiff < 1e-9, "look-ahead — filtered probs changed when future removed"
assert reg_match, "look-ahead — regime labels changed when future removed"

print(f"\nGATE X29 PASSED in {time.time() - t_start:.0f}s")
