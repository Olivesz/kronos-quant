"""Gate X4: GARCH MLE recovers known params; DM test has power and size."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from kronos.vollab import GJRGARCH, HAR, diebold_mariano, ewma_forecast, qlike

rng = np.random.default_rng(21)

# --- simulate GJR-GARCH-t with known parameters -------------------------------
T = 6000
alpha, gamma_, beta, nu = 0.04, 0.10, 0.86, 7.0
uncond = (0.16 ** 2) / 252
omega = uncond * (1 - alpha - beta - gamma_ / 2)
r = np.empty(T)
s2 = uncond
for t in range(T):
    z = rng.standard_t(nu) * np.sqrt((nu - 2) / nu)
    r[t] = np.sqrt(s2) * z
    s2 = omega + (alpha + gamma_ * (r[t] < 0)) * r[t] ** 2 + beta * s2

t0 = time.time()
g = GJRGARCH().fit(r)
print(f"fit in {time.time()-t0:.1f}s, converged={g.converged_}")
a, gm, b, nu_hat = g.params_
print(f"alpha {a:.3f} (true {alpha}) | gamma {gm:.3f} (true {gamma_}) | "
      f"beta {b:.3f} (true {beta}) | nu {nu_hat:.1f} (true {nu})")
assert g.converged_
assert abs(a - alpha) < 0.03 and abs(gm - gamma_) < 0.05 and abs(b - beta) < 0.04
assert abs(nu_hat - nu) < 3.0

# --- DM test: power (GARCH-truth vs EWMA) and size (EWMA vs itself + noise) ---
true_s2 = np.empty(T)
s2 = uncond
for t in range(T):
    true_s2[t] = s2
    s2 = omega + (alpha + gamma_ * (r[t] < 0)) * r[t] ** 2 + beta * s2
# GK-quality realized proxy: unbiased, ~7x more efficient than r^2
# (gamma(k)/k multiplicative noise with k=3.7 matches that efficiency)
rv_proxy = true_s2 * rng.gamma(3.7, 1 / 3.7, T)

f_true = true_s2                       # oracle forecaster
f_ewma = ewma_forecast(r ** 2)
f_bad = ewma_forecast(r ** 2, lam=0.995)   # clearly misspecified rival
L_true = qlike(rv_proxy[100:], f_true[100:])
L_ewma = qlike(rv_proxy[100:], f_ewma[100:])
L_bad = qlike(rv_proxy[100:], f_bad[100:])
dm = diebold_mariano(L_true, L_bad)
print(f"DM oracle-vs-bad : stat={dm['stat']:.1f} p={dm['p']:.1e} (must favor oracle)")
dm_e = diebold_mariano(L_ewma, L_bad)
print(f"DM EWMA-vs-bad   : stat={dm_e['stat']:.1f} p={dm_e['p']:.1e}")
assert dm["stat"] < -3 and dm["p"] < 0.01, "DM has no power"
assert dm_e["stat"] < -2, "DM should also favor well-tuned EWMA over bad"

# size: same forecaster, permuted tiny noise -> should NOT reject
f_ewma2 = f_ewma * np.exp(rng.normal(0, 1e-4, T))
dm0 = diebold_mariano(qlike(rv_proxy[100:], f_ewma[100:]),
                      qlike(rv_proxy[100:], f_ewma2[100:]))
print(f"DM null check: stat={dm0['stat']:.2f} p={dm0['p']:.2f} (must not reject)")
assert dm0["p"] > 0.05, "DM over-rejects under the null"

# --- HAR sanity: forecasts positively correlated with future RV ---------------
har = HAR().fit(rv_proxy[:4000])
fc = np.array([har.forecast_next(rv_proxy[:s]) for s in range(4000, T)])
corr = np.corrcoef(np.log(fc), np.log(true_s2[4000:]))[0, 1]
print(f"HAR log-forecast corr with true log-variance: {corr:.2f}")
assert corr > 0.6, "HAR forecasts uninformative"

print("\nGATE X4 PASSED")
