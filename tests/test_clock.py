"""Gate X15: the clock machinery can exonerate AND convict."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from kronos.clock import (GaussianNull, pair_tail_study, simulate_clock_world,
                          clock_commonality)
from kronos.laws import standardized_returns, mrw_lambda2

T = 4000
t0 = time.time()
null = GaussianNull(T, n_sims=300)
print(f"null table built in {time.time()-t0:.0f}s")

def deformed(world, lag=0):
    z = standardized_returns(world["close"], world["gkvar"], smooth=5, lag=lag)
    return z.dropna()

def raw(world):
    import pandas as pd
    return np.log(world["close"] / world["close"].shift(1)).dropna()

# --- world 1: correlated clocks, NO contagion — must exonerate ---------------
# (both deformations: same-day removes everything the range sees; lagged
#  removes only the predictable clock — with persistent clocks both should
#  exonerate when there are no joint jumps)
w1 = simulate_clock_world(T, s2=0.20, joint_jumps=0.0, seed=1)
res_raw = pair_tail_study(raw(w1), null)
res_z0 = pair_tail_study(deformed(w1, lag=0), null)
res_z1 = pair_tail_study(deformed(w1, lag=1), null)
print(f"clock world: raw frac>95 {res_raw['q50']['frac_above95']:.0%} -> "
      f"same-day {res_z0['q50']['frac_above95']:.0%} | "
      f"lagged {res_z1['q50']['frac_above95']:.0%}")
assert res_raw["q50"]["frac_above95"] > 0.3, \
    "correlated clocks must CREATE apparent tail dependence in raw returns"
assert res_z0["q50"]["frac_above95"] < 0.25, "same-day must exonerate"
assert res_z1["q50"]["frac_above95"] < 0.35, "lagged must (mostly) exonerate"

# --- world 2: + COMMON JUMPS — the LAGGED deformation must convict -------------
# (the same-day range absorbs the jump — discovered in gate development —
#  so conviction is the lagged deformation's job)
w2 = simulate_clock_world(T, s2=0.20, joint_jumps=5.0, seed=2)
res2_z0 = pair_tail_study(deformed(w2, lag=0), null)
res2_z1 = pair_tail_study(deformed(w2, lag=1), null)
print(f"jump world : same-day frac>95 {res2_z0['q50']['frac_above95']:.0%} "
      f"(absorbs jumps) | lagged {res2_z1['q50']['frac_above95']:.0%} "
      f"(excess {res2_z1['q50']['median_excess']:+.2f})")
assert res2_z1["q50"]["frac_above95"] > 0.5, \
    "lagged deformation must NOT destroy evidence of genuine joint jumps"

# --- C1 control: lambda2 collapses after deformation on an SV world -----------
z1 = deformed(w1)
lam_raw = np.median([mrw_lambda2(w1["close"][c])["lambda2"]
                     for c in w1["close"].columns])
import pandas as pd
lam_z = []
for c in z1.columns:
    fake_close = pd.Series(100 * np.exp(np.cumsum(z1[c].to_numpy() * 0.01)),
                           index=z1.index)
    lam_z.append(mrw_lambda2(fake_close)["lambda2"])
lam_z = np.median(lam_z)
print(f"lambda2: raw {lam_raw:.3f} -> deformed {lam_z:.3f}")
assert lam_z < lam_raw * 0.65, "deformation must remove clock-driven intermittency"

# --- commonality measure sanity ------------------------------------------------
cc = clock_commonality(w1["gkvar"])
print(f"clock eig1 share (rho_clock=0.8 world): {cc['eig1_share']:.0%}")
assert cc["eig1_share"] > 0.4, "common clock factor should dominate"

print("\nGATE X15 PASSED")
