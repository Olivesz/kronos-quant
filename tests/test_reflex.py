"""Gate X21: Hawkes MLE recovers known branching ratio; Poisson -> 0;
vol-clustering attributed correctly by the raw/deformed decomposition."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from kronos.hawkes import (fit_hawkes, simulate_hawkes, recovery_curve, debias,
                           raw_and_deformed_events)

# --- 1. recovery of known branching ratio (monotone, ordered) -------------------
print("true n   mean n_hat (T=5000)")
T = 5000.0
ests = {}
for nt in (0.3, 0.6, 0.9):
    beta = 0.2; mu = 0.05 * (1 - nt)
    e = [fit_hawkes(simulate_hawkes(mu, nt, beta, T, seed=s), T, seed=s)["n"]
         for s in range(10)]
    ests[nt] = np.nanmean(e)
    print(f"  {nt:.1f}      {ests[nt]:.3f}")
# monotone recovery and ordered (bias allowed, but must track truth)
assert ests[0.3] < ests[0.6] < ests[0.9], "n_hat must be monotone in true n"
assert abs(ests[0.6] - 0.6) < 0.20, "n_hat must track truth within finite-sample bias"
assert ests[0.9] > 0.7, "near-critical must be detected as high"

# --- 2. Poisson (n=0): no spurious endogeneity ----------------------------------
rng = np.random.default_rng(1)
pois = np.sort(rng.uniform(0, T, 250))
n_pois = fit_hawkes(pois, T, seed=0)["n"]
print(f"Poisson process: n_hat = {n_pois:.3f} (must be ~0)")
assert n_pois < 0.25, "Poisson must not look endogenous"

# --- 3. kernel timescale recovery ------------------------------------------------
ev = simulate_hawkes(0.02, 0.6, 0.1, 8000.0, seed=2)
fit = fit_hawkes(ev, 8000.0, seed=2)
print(f"timescale: true 1/beta=10.0, est={fit['timescale']:.1f}")
assert 4 < fit["timescale"] < 25

# --- 4. THE DECOMPOSITION: clustered-but-not-self-exciting (SV world) -----------
# A pure stochastic-vol world has NO self-excitation; raw |r| events cluster
# (look endogenous), deformed |r/vol| events are ~Poisson (n~0).
from kronos.surge import simulate_reversible_world
r0, v0 = simulate_reversible_world(8000, seed=3)
close = pd.Series(100 * np.exp(np.cumsum(r0.to_numpy())), index=r0.index)
ev = raw_and_deformed_events(close, v0, q=0.95)
n_raw = fit_hawkes(ev["raw"], ev["T"], seed=0)["n"]
n_def = fit_hawkes(ev["deformed"], ev["T"], seed=0)["n"]
print(f"SV world: n_raw={n_raw:.3f} (clustering) vs n_deformed={n_def:.3f} (must drop)")
assert n_raw > 0.2, "raw vol-clustering events should look self-exciting"
assert n_def < n_raw - 0.1, "deformation must remove clustering-driven endogeneity"

# --- 5. debias inverts the recovery curve ---------------------------------------
curve = recovery_curve(n_rep=6, seed=5)
print("recovery curve:", {k: round(v, 2) for k, v in curve.items()})
assert abs(debias(curve[0.6], curve) - 0.6) < 0.08, "debias must invert the curve"

print("\nGATE X21 PASSED")
