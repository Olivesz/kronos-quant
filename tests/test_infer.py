"""Gate X12: AG test size & power; MCS keeps truth, kills the bad."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from kronos.infer import amisano_giacomini, model_confidence_set

rng = np.random.default_rng(81)
T = 1500

# --- AG size: equal-skill scores with autocorrelated noise --------------------
rejections = 0
n_rep = 200
for _ in range(n_rep):
    base = rng.normal(0, 1, T)
    # AR(1) common noise + idiosyncratic: equal skill by construction
    e = np.zeros(T); phi = 0.3
    for t in range(1, T):
        e[t] = phi * e[t - 1] + rng.normal()
    a = base + 0.5 * e + rng.normal(0, 0.5, T)
    b = base + 0.5 * e + rng.normal(0, 0.5, T)
    if amisano_giacomini(a, b)["p"] < 0.05:
        rejections += 1
size = rejections / n_rep
print(f"AG empirical size at 5%: {size:.1%}")
assert size < 0.10, "AG over-rejects under the null"

# --- AG power: genuinely better density forecaster -----------------------------
# realistic structure: scores share most variation (same data), small skill gap
base = rng.normal(0, 1, T)
a = base + rng.normal(0, 0.5, T) + 0.08
b = base + rng.normal(0, 0.5, T)
ag = amisano_giacomini(a, b)
print(f"AG power case: stat={ag['stat']:.1f} p={ag['p']:.1e}")
assert ag["stat"] > 0 and ag["p"] < 0.05

# --- MCS coverage --------------------------------------------------------------
names = [f"M{i}" for i in range(6)]
keep_good, kill_bad = 0, 0
n_rep2 = 40
for rep in range(n_rep2):
    r2 = np.random.default_rng(rep)
    L = r2.normal(1.0, 1.0, (T, 6))
    L[:, 3:] += 0.12          # models 3-5 clearly worse (higher loss)
    res = model_confidence_set(L, names, alpha=0.10, n_boot=200, seed=rep)
    if all(f"M{i}" in res["mcs"] for i in range(3)):
        keep_good += 1
    if all(f"M{i}" not in res["mcs"] for i in range(3, 6)):
        kill_bad += 1
print(f"MCS keeps all 3 good: {keep_good/n_rep2:.0%} | kills all 3 bad: {kill_bad/n_rep2:.0%}")
assert keep_good / n_rep2 >= 0.80, "MCS coverage too low"
assert kill_bad / n_rep2 >= 0.80, "MCS power too low"

# all-equal case: MCS should keep (almost) everything
L_eq = rng.normal(1.0, 1.0, (T, 6))
res_eq = model_confidence_set(L_eq, names, alpha=0.10, n_boot=300)
print(f"all-equal case: MCS size {len(res_eq['mcs'])}/6")
assert len(res_eq["mcs"]) >= 4

print("\nGATE X12 PASSED")
