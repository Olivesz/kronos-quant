"""Gate X11: t-HMM recovers nu and beats Gaussian on t worlds, ties on
Gaussian worlds — the prerequisites for the hallucination study."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy.special import logsumexp

from kronos.regime import GaussianHMM
from kronos.thmm import StudentTHMM

rng = np.random.default_rng(71)

MEANS = np.array([[0.0008, np.log(0.10)],
                  [0.0000, np.log(0.20)],
                  [-0.0015, np.log(0.35)]])
SCALES = np.array([[0.006, 0.08], [0.012, 0.10], [0.022, 0.12]])
A_TRUE = np.array([[0.97, 0.02, 0.01],
                   [0.03, 0.94, 0.03],
                   [0.02, 0.04, 0.94]])


def gen_world(T, nu=None, seed=0):
    """nu=None -> Gaussian emissions; else multivariate-t with that nu."""
    r = np.random.default_rng(seed)
    s = np.zeros(T, dtype=int)
    for t in range(1, T):
        s[t] = r.choice(3, p=A_TRUE[s[t - 1]])
    z = r.normal(size=(T, 2))
    if nu is not None:
        g = r.chisquare(nu, size=T) / nu
        z = z / np.sqrt(g)[:, None]
        z *= np.sqrt((nu - 2) / nu)   # unit-variance scaling for comparability
    X = MEANS[s] + SCALES[s] * z
    return X, s


def oos_logscore(model, X, t0):
    logB = model._log_obs(X)
    la = model._forward(logB)
    filt = np.exp(la - logsumexp(la, axis=1, keepdims=True))
    pred = filt[:-1] @ model.A_
    ld = model.return_marginal_logdens(pred, X[1:, 0])
    return float(ld[t0 - 1:].mean())


TRAIN, TOTAL = 2000, 3000

# --- t world: recover nu, beat Gaussian ---------------------------------------
Xt, st = gen_world(TOTAL, nu=5.0, seed=1)
t0 = time.time()
tm = StudentTHMM(3, seed=42).fit(Xt[:TRAIN])
fit_s = time.time() - t0
gm = GaussianHMM(3, seed=42).fit(Xt[:TRAIN])
print(f"t-HMM fit {fit_s:.1f}s | est nus: {np.round(tm.nus_, 1)} (true 5.0)")
print(f"A diag est {np.round(np.diag(tm.A_), 3)} (true {np.diag(A_TRUE)})")
# note: scaled-t emissions => effective nu equals the mixing chi2's nu
assert np.all(np.abs(tm.nus_ - 5.0) < 2.0), "nu recovery failed"
assert np.all(np.abs(np.diag(tm.A_) - np.diag(A_TRUE)) < 0.05)

s_t = oos_logscore(tm, Xt, TRAIN)
s_g = oos_logscore(gm, Xt, TRAIN)
print(f"t world  : t-HMM {s_t:.4f} vs Gaussian {s_g:.4f} (edge {s_t-s_g:+.4f})")
assert s_t > s_g + 0.002, "t-HMM must beat Gaussian on a t world"

# state recovery should also be respectable
fp = tm.filtered_probs(Xt)
acc = (fp.argmax(axis=1) == st).mean()
print(f"t world filtered accuracy: {acc:.1%}")
assert acc > 0.75

# --- Gaussian world: no penalty for the extra machinery ------------------------
Xg, sg = gen_world(TOTAL, nu=None, seed=2)
tm_g = StudentTHMM(3, seed=42).fit(Xg[:TRAIN])
gm_g = GaussianHMM(3, seed=42).fit(Xg[:TRAIN])
s_t2 = oos_logscore(tm_g, Xg, TRAIN)
s_g2 = oos_logscore(gm_g, Xg, TRAIN)
print(f"gauss world: t-HMM {s_t2:.4f} vs Gaussian {s_g2:.4f} "
      f"(gap {abs(s_t2-s_g2):.4f}, est nus {np.round(tm_g.nus_,0)})")
assert abs(s_t2 - s_g2) < 0.005, "should tie on Gaussian data"
assert np.all(tm_g.nus_ > 15), "nu should blow up toward Gaussian"

print("\nGATE X11 PASSED")
