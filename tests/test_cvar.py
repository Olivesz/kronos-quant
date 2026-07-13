"""Gate X8: min-CVaR LP correctness — beats equal-weight CVaR in-sample,
avoids the fat-tailed asset, respects constraints."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from kronos.cvar_opt import min_cvar_weights

rng = np.random.default_rng(41)

# 3 assets: two well-behaved, one with brutal left tail
S = 504
a = rng.normal(0.0004, 0.010, S)
b = rng.normal(0.0004, 0.010, S)
crash = rng.random(S) < 0.02
c = np.where(crash, -0.08 + rng.normal(0, 0.01, S), rng.normal(0.0015, 0.006, S))
scen = np.column_stack([a, b, c])

t0 = time.time()
res = min_cvar_weights(scen, beta=0.95, cap=0.8)
ms = (time.time() - t0) * 1000
w = res["weights"]
print(f"weights: {np.round(w, 3)} (solved in {ms:.0f}ms)")
assert res["status"] == "ok"
assert abs(w.sum() - 1) < 1e-8 and (w >= -1e-12).all() and (w <= 0.8 + 1e-9).all()

# in-sample CVaR must beat equal weight (it's the optimizer's own objective)
def cvar(port):
    q = np.quantile(port, 0.05)
    return -port[port <= q].mean()

cv_opt = cvar(scen @ w)
cv_ew = cvar(scen @ np.array([1/3, 1/3, 1/3]))
print(f"in-sample CVaR95: optimized {cv_opt:.4f} vs equal-weight {cv_ew:.4f}")
assert cv_opt < cv_ew, "optimizer must beat equal weight on its own objective"
assert w[2] < 0.34, "should underweight the crash asset"

# turnover penalty: with huge penalty, stays near w_prev
w_prev = np.array([0.5, 0.3, 0.2])
res2 = min_cvar_weights(scen, cap=0.8, w_prev=w_prev, turnover_penalty=10.0)
drift = np.abs(res2["weights"] - w_prev).sum()
print(f"turnover with punitive penalty: {drift:.4f}")
assert drift < 0.02, "punitive turnover penalty should freeze the book"

# cap binds
res3 = min_cvar_weights(scen, cap=0.40)
assert res3["weights"].max() <= 0.40 + 1e-9

print("\nGATE X8 PASSED")
