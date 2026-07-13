"""Gate X13: RFSV forecaster beats HAR on its home turf (true RFSV world),
stays competitive on a GARCH world (graceful misspecification)."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from kronos.rfsv import RFSV, walkforward_rfsv, simulate_rfsv_world, rfsv_kernel
from kronos.vollab import HAR, qlike, ewma_forecast

# kernel sanity: weights positive, decreasing, sum to 1; rough H = slow decay
w1 = rfsv_kernel(0.10, 1, 500)
w2 = rfsv_kernel(0.45, 1, 500)
assert abs(w1.sum() - 1) < 1e-12 and (np.diff(w1) < 0).all()
print(f"kernel mass in first 5 lags: H=0.10 -> {w1[:5].sum():.2f}, "
      f"H=0.45 -> {w2[:5].sum():.2f} (rougher = longer memory in levels)")

# --- RFSV world: the true model must win --------------------------------------
proxy = simulate_rfsv_world(4500, H=0.10, seed=7)
true_v = proxy.attrs["true_var"]
arr = proxy.to_numpy()

t0 = time.time()
fc_rfsv = walkforward_rfsv(proxy, min_train=1500, refit_every=63)
print(f"walk-forward RFSV in {time.time()-t0:.0f}s")

# HAR walk-forward on the same proxy
T = len(arr)
fc_har = np.full(T, np.nan)
t = 1500
while t < T:
    har = HAR().fit(arr[:t])
    t_next = min(t + 63, T)
    for s in range(t, t_next):
        fc_har[s] = har.forecast_next(arr[:s])
    t = t_next

mask = ~np.isnan(fc_rfsv.to_numpy()) & ~np.isnan(fc_har)
# judge against the TRUE variance (available in simulation) — no proxy noise
L_rfsv = qlike(true_v[mask], fc_rfsv.to_numpy()[mask])
L_har = qlike(true_v[mask], fc_har[mask])
print(f"RFSV world QLIKE vs truth: RFSV {L_rfsv.mean():.4f} | HAR {L_har.mean():.4f}")
assert L_rfsv.mean() < L_har.mean(), "true model must beat HAR on RFSV world"

# kernel-H sanity: in range, with calibration shrinkage active.
# (Exact H recovery under measurement noise is impossible by construction —
#  Gate X5 characterizes both bias directions; the forecast test above is
#  the hypothesis that matters here.)
m = RFSV().fit(arr[:3000])
print(f"kernel H: {m.H_:.3f} (true 0.10) | smooth hl={m.halflife_} | calib b={m.b_:.2f}")
assert 0.02 <= m.H_ <= 0.49 and 0.2 < m.b_ <= 1.5

# --- GARCH world: misspecified but must stay competitive ----------------------
rng = np.random.default_rng(3)
alpha, beta = 0.06, 0.90
uncond = (0.16 ** 2) / 252
omega = uncond * (1 - alpha - beta)
r = np.empty(5000); s2 = uncond; tv = np.empty(5000)
for i in range(5000):
    tv[i] = s2
    r[i] = np.sqrt(s2) * rng.normal()
    s2 = omega + alpha * r[i] ** 2 + beta * s2
proxy_g = pd.Series(tv * rng.gamma(3.7, 1/3.7, 5000),
                    index=pd.bdate_range("2010-01-01", periods=5000))
fc_r2 = walkforward_rfsv(proxy_g, min_train=1500, refit_every=63)
arr_g = proxy_g.to_numpy()
fc_h2 = np.full(5000, np.nan)
t = 1500
while t < 5000:
    har = HAR().fit(arr_g[:t])
    t_next = min(t + 63, 5000)
    for s in range(t, t_next):
        fc_h2[s] = har.forecast_next(arr_g[:s])
    t = t_next
mask = ~np.isnan(fc_r2.to_numpy()) & ~np.isnan(fc_h2)
Lr = qlike(tv[mask], fc_r2.to_numpy()[mask]).mean()
Lh = qlike(tv[mask], fc_h2[mask]).mean()
print(f"GARCH world QLIKE vs truth: RFSV {Lr:.4f} | HAR {Lh:.4f} (ratio {Lr/Lh:.2f})")
assert Lr / Lh < 1.15, "RFSV should degrade gracefully off-model"

print("\nGATE X13 PASSED")
