"""Gates 3 & 6: signal sanity + Kalman convergence on known cointegration."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from config import CFG
from kronos.pairs import KalmanPair, _adf_tstat, select_pairs
from kronos.signals import combined_signal, low_vol_signal, mean_reversion_signal, momentum_signal

rng = np.random.default_rng(11)

# --- signals on synthetic panel with known structure -------------------------
T, N = 400, 20
dates = pd.bdate_range("2022-01-03", periods=T)
trend = np.linspace(0, 0.8, T)[:, None] * np.linspace(-1, 1, N)[None, :]  # asset N-1 trends up
noise = rng.normal(0, 0.01, (T, N)).cumsum(axis=0)
px = pd.DataFrame(100 * np.exp(trend + noise), index=dates,
                  columns=[f"A{i}" for i in range(N)])

t = dates[-1]
mom = momentum_signal(px, t, CFG)
assert abs(mom.mean()) < 1e-9 and abs(mom.std() - 1) < 0.35, "momentum not z-scored"
assert mom["A19"] > 0.5 and mom["A0"] < -0.5, "momentum doesn't rank trends"

rev = mean_reversion_signal(px, t, CFG)
lv = low_vol_signal(px, t, CFG)
for s, nm in [(rev, "rev"), (lv, "lowvol")]:
    assert abs(s.mean()) < 1e-6, f"{nm} not centered"

combo = combined_signal(px, t, regime_id=0, cfg=CFG)
assert set(combo["components"]) == {"momentum", "mean_reversion", "low_vol"}
assert abs(combo["combined"].mean()) < 1e-6
print("signals gate OK  (mom z for best/worst trend: %.2f / %.2f)" % (mom["A19"], mom["A0"]))

# --- ADF helper: stationary vs random walk -----------------------------------
ar = np.zeros(500)
for i in range(1, 500):
    ar[i] = 0.7 * ar[i - 1] + rng.normal()
rw = rng.normal(size=500).cumsum()
t_ar, t_rw = _adf_tstat(ar), _adf_tstat(rw)
print("adf t-stats: AR(0.7)=%.1f  random-walk=%.1f" % (t_ar, t_rw))
assert t_ar < -4 and t_rw > -2.5, "ADF helper can't separate stationary from RW"

# --- Kalman convergence on true cointegration --------------------------------
Tk = 1000
lx = np.cumsum(rng.normal(0, 0.01, Tk)) + np.log(80)
spread = np.zeros(Tk)
for i in range(1, Tk):
    spread[i] = 0.9 * spread[i - 1] + rng.normal(0, 0.004)
true_beta = 1.5
ly = 0.5 + true_beta * lx + spread

kp = KalmanPair("Y", "X", resid_var=0.004**2, delta=CFG.pairs_delta)
zs, betas = [], []
for i in range(Tk):
    z, b = kp.update(ly[i], lx[i])
    zs.append(z); betas.append(b)
beta_final = np.mean(betas[-100:])
print("kalman beta -> %.3f (true %.1f)" % (beta_final, true_beta))
assert abs(beta_final - true_beta) < 0.15, "Kalman beta did not converge"
z_arr = np.array(zs[200:])
# innovations should mean-revert: lag-1 autocorr well below 1, mean ~ 0
ac = np.corrcoef(z_arr[:-1], z_arr[1:])[0, 1]
print("z lag-1 autocorr: %.2f, |mean|: %.2f" % (ac, abs(z_arr.mean())))
assert abs(z_arr.mean()) < 0.5 and ac < 0.97

# --- pair selection finds the planted pair -----------------------------------
panel = {}
for i in range(6):
    panel[f"N{i}"] = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.015, 600)))
base = np.cumsum(rng.normal(0.0003, 0.012, 600))
sp = np.zeros(600)
for i in range(1, 600):
    sp[i] = 0.85 * sp[i - 1] + rng.normal(0, 0.003)
panel["CO1"] = 100 * np.exp(base)
panel["CO2"] = 95 * np.exp(0.98 * base + sp)
ppx = pd.DataFrame(panel, index=pd.bdate_range("2021-01-04", periods=600))
sel = select_pairs(ppx, ppx.index[-1], CFG)
names = {frozenset((a, b)) for a, b, _ in sel}
print("selected pairs:", [(a, b) for a, b, _ in sel])
assert frozenset(("CO1", "CO2")) in names, "planted cointegrated pair not found"

print("\nGATES 3 & 6 PASSED")
