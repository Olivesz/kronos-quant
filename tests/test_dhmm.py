"""Gate X3: duration-HMM beats HMM on semi-Markov data, ties on geometric."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.special import logsumexp

from kronos.dhmm import DurationHMM
from kronos.regime import GaussianHMM

rng = np.random.default_rng(13)

MEANS = np.array([[0.0008, np.log(0.10)],
                  [0.0000, np.log(0.20)],
                  [-0.0015, np.log(0.35)]])
STDS = np.array([[0.006, 0.08], [0.012, 0.10], [0.022, 0.12]])


def gen_semi_markov(T, r=3, mean_dur=(60, 25, 30)):
    """Negative-binomial durations (humped): sum of r geometrics."""
    s, t = [], 0
    k = 0
    while t < T:
        p_each = r / mean_dur[k]          # each stage mean = mean_dur/r
        dur = sum(rng.geometric(min(p_each, 0.95)) for _ in range(r))
        s += [k] * dur
        t += dur
        k = rng.choice([j for j in range(3) if j != k])
    s = np.array(s[:T])
    X = MEANS[s] + STDS[s] * rng.normal(size=(T, 2))
    return X, s


def gen_geometric(T, mean_dur=(60, 25, 30)):
    s, t, k = [], 0, 0
    while t < T:
        dur = rng.geometric(1 / mean_dur[k])
        s += [k] * dur
        t += dur
        k = rng.choice([j for j in range(3) if j != k])
    s = np.array(s[:T])
    X = MEANS[s] + STDS[s] * rng.normal(size=(T, 2))
    return X, s


def oos_logscore(model, X, t0):
    """Mean one-step-ahead predictive log-density of the return dim over
    t0..T-1, with params frozen (single incremental forward pass)."""
    logB = model._log_obs(X)
    la = model._forward(logB)
    filt = np.exp(la - logsumexp(la, axis=1, keepdims=True))
    pred = filt[:-1] @ model.A_                    # P(s_{t+1} | x_{1:t})
    mu = model.means_[:, 0]
    sd = np.sqrt(model.covs_[:, 0, 0])
    r_next = X[1:, 0]
    dens = (pred * np.exp(-0.5 * ((r_next[:, None] - mu) / sd) ** 2)
            / (sd * np.sqrt(2 * np.pi))).sum(axis=1)
    return float(np.log(np.maximum(dens[t0 - 1:], 1e-300)).mean())


TRAIN, TOTAL = 2500, 4000

# --- semi-Markov world: duration model should win ----------------------------
Xs, ss = gen_semi_markov(TOTAL)
hmm = GaussianHMM(3, seed=42).fit(Xs[:TRAIN])
dh = DurationHMM(3, r=3, seed=42).fit(Xs[:TRAIN])
s_hmm = oos_logscore(hmm, Xs, TRAIN)
s_dh = oos_logscore(dh, Xs, TRAIN)
print(f"semi-Markov data : HMM {s_hmm:.4f} | DurHMM {s_dh:.4f} | edge {s_dh-s_hmm:+.4f} nats/day")

# duration pmf should be humped (mode away from day 1)
pmf = dh.duration_pmf(0, 200)
mode = int(pmf.argmax()) + 1
print(f"implied bull-duration mode: day {mode} (geometric would be day 1)")

# --- geometric world: no false win -------------------------------------------
Xg, sg = gen_geometric(TOTAL)
hmm_g = GaussianHMM(3, seed=42).fit(Xg[:TRAIN])
dh_g = DurationHMM(3, r=3, seed=42).fit(Xg[:TRAIN])
g_hmm = oos_logscore(hmm_g, Xg, TRAIN)
g_dh = oos_logscore(dh_g, Xg, TRAIN)
print(f"geometric data   : HMM {g_hmm:.4f} | DurHMM {g_dh:.4f} | edge {g_dh-g_hmm:+.4f} nats/day")

assert s_dh > s_hmm - 1e-6, "DurHMM should not lose on semi-Markov data"
assert mode > 1, "duration law should be humped, not geometric"
assert abs(g_dh - g_hmm) < 0.01, "models should roughly tie on geometric data"

# regime aggregation sums to 1
fp = dh.filtered_probs(Xs[:500])
rp = dh.regime_probs(fp)
assert np.allclose(rp.sum(axis=1), 1, atol=1e-8)

print("\nGATE X3 PASSED")
