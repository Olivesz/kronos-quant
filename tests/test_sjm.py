"""Gate X2: SJM recovers planted regimes; lambda controls persistence."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from kronos.sjm import JumpModel

rng = np.random.default_rng(7)

# same synthetic 3-state ground truth as the HMM gate
T = 3000
A_true = np.array([[0.97, 0.02, 0.01],
                   [0.03, 0.94, 0.03],
                   [0.02, 0.04, 0.94]])
means_true = np.array([[0.0008, np.log(0.10)],
                       [0.0000, np.log(0.20)],
                       [-0.0015, np.log(0.35)]])
stds_true = np.array([[0.006, 0.08], [0.012, 0.10], [0.022, 0.12]])
s = np.zeros(T, dtype=int)
for t in range(1, T):
    s[t] = rng.choice(3, p=A_true[s[t - 1]])
X = means_true[s] + stds_true[s] * rng.normal(size=(T, 2))

# lambda sweep: switches must fall monotonically, accuracy peaks mid-range
print("lam   switches  accuracy")
accs = {}
for lam in (0.0, 4.0, 16.0, 64.0, 256.0):
    t0 = time.time()
    jm = JumpModel(3, lam=lam, seed=42).fit(X)
    fit_ms = (time.time() - t0) * 1000
    sw = int((np.diff(jm.states_) != 0).sum())
    acc = (jm.states_ == s).mean()
    accs[lam] = acc
    print(f"{lam:6.0f}  {sw:8d}  {acc:7.1%}   ({fit_ms:.0f}ms)")

sw0 = int((np.diff(JumpModel(3, 0.0, seed=42).fit(X).states_) != 0).sum())
sw256 = int((np.diff(JumpModel(3, 256.0, seed=42).fit(X).states_) != 0).sum())
assert sw256 < sw0 * 0.5, "lambda does not control persistence"
assert max(accs.values()) > 0.85, "SJM cannot recover planted regimes"

# canonicalization: state 0 must be the calm/up state, 2 the down state
jm = JumpModel(3, lam=4.0, seed=42).fit(X)   # the accuracy-optimal lambda
assert jm.means_[0, 0] > jm.means_[2, 0], "canonical order broken"
assert jm.covs_[0, 0, 0] < jm.covs_[2, 0, 0], "bull should be calmer than bear"

# causal online states: must agree with offline path most of the time
on = jm.online_states(X)
agree = (on == jm.states_).mean()
print(f"online-vs-offline agreement: {agree:.1%}")
assert agree > 0.85, "online filter diverges from smoother"

# predictive density is a proper density (integrates to ~1 over a grid)
grid = np.linspace(-0.12, 0.12, 4001)
pdf = np.exp([jm.predictive_logpdf_return(0, r) for r in grid])
integral = np.trapezoid(pdf, grid)
print(f"predictive density integral: {integral:.4f}")
assert abs(integral - 1) < 0.01

print("\nGATE X2 PASSED")
