"""Gate X31: the harvest-gap estimator must CONVICT when a feature outside
the harvested set genuinely carries sign information (recovering the
enumerated true gap), EXONERATE when the harvested state is sufficient, and
read ~0 on pure noise. Truth is exact — the worlds are discrete."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from kronos.harvest import harvest_gap, simulate_world

T = 4000

# --- unharvested world: must CONVICT and recover the true gap -------------------
feats, y, true_gap = simulate_world(T, unharvested=True, seed=1)
g = harvest_gap(feats, ["regime"], y, n_boot=150, seed=1)
print(f"unharvested world: gap {g['gap_bits']:.4f} bits (true {true_gap:.4f}) "
      f"CI [{g['ci'][0]:.4f}, {g['ci'][1]:.4f}] sig={g['significant']}")
assert g["significant"], "failed to convict a genuinely unharvested feature"
assert abs(g["gap_bits"] - true_gap) < 0.4 * true_gap, \
    "estimated gap far from enumerated truth"

# --- harvested world: must EXONERATE -------------------------------------------
feats, y, true_gap = simulate_world(T, unharvested=False, seed=2)
g = harvest_gap(feats, ["regime"], y, n_boot=150, seed=2)
print(f"harvested world:   gap {g['gap_bits']:.4f} bits (true {true_gap:.4f}) "
      f"CI [{g['ci'][0]:.4f}, {g['ci'][1]:.4f}] sig={g['significant']}")
assert not g["significant"], "convicted a sufficient harvested state (false positive)"

# --- pure noise: net gap ~ 0 ----------------------------------------------------
rng = np.random.default_rng(3)
idx = pd.bdate_range("2012-01-02", periods=T)
feats = pd.DataFrame({"regime": rng.integers(0, 3, T),
                      "extra": rng.integers(0, 2, T),
                      "junk": rng.integers(0, 2, T)}, index=idx)
y = pd.Series(rng.integers(0, 2, T), index=idx)
g = harvest_gap(feats, ["regime"], y, n_boot=150, seed=3)
print(f"pure noise:        gap {g['gap_bits']:.4f} bits "
      f"CI [{g['ci'][0]:.4f}, {g['ci'][1]:.4f}] sig={g['significant']}")
assert not g["significant"], "significant gap on pure noise"
assert abs(g["gap_bits"]) < 0.01, "net gap not debiased on noise"

print("\nGATE X31 PASSED")
