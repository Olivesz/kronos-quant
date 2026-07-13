"""Gate X22: stability test has correct size (calls constants constant) and
power (detects a known drift)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from kronos.constants import classify, trend_test, variance_ratio_test

rng = np.random.default_rng(7)
n_win = 5
t = np.arange(n_win, dtype=float)
sd = np.full(n_win, 0.05)               # known per-window sampling SD

# --- size: a CONSTANT quantity (windows differ only by sampling noise) ---------
false_pos = 0
n_rep = 400
for _ in range(n_rep):
    m = 0.5 + rng.normal(0, 1, n_win) * sd
    vr = variance_ratio_test(m, sd, n_null=800)
    tr = trend_test(t, m, sd, n_boot=800)
    if classify(vr, tr, 4.0) != "CONSTANT":
        false_pos += 1
size = false_pos / n_rep
print(f"CONSTANT world: false-positive rate {size:.0%} (must be low)")
assert size < 0.20, "stability test over-rejects constants"

# --- power: a DRIFTING quantity (linear trend >> sampling noise) ----------------
detected = 0
for _ in range(n_rep):
    m = 0.5 + 0.10 * t + rng.normal(0, 1, n_win) * sd      # strong drift
    vr = variance_ratio_test(m, sd, n_null=800)
    tr = trend_test(t, m, sd, n_boot=800)
    if classify(vr, tr, 4.0) == "DRIFTING":
        detected += 1
power = detected / n_rep
print(f"DRIFTING world: detection rate {power:.0%} (must be high)")
assert power > 0.80, "stability test misses real drift"

# --- VR calibration: pure noise gives VR ~ 1 ------------------------------------
vrs = []
for _ in range(300):
    m = rng.normal(0, 1, n_win) * sd
    vrs.append(variance_ratio_test(m, sd, n_null=400)["VR"])
print(f"pure-noise VR: median {np.median(vrs):.2f} (must be ~1)")
assert 0.5 < np.median(vrs) < 2.0, "VR not calibrated to ~1 under the null"

print("\nGATE X22 PASSED")
