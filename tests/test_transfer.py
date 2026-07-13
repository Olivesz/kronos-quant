"""Gate X24: the transfer test must EXONERATE identical mechanisms (same
generative world, different seeds => laws classified TRANSFERS) and CONVICT
different mechanisms (clock world vs iid-Gaussian world => the laws that
genuinely differ classified UNIVERSE-SPECIFIC)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from kronos.clock import simulate_clock_world
from kronos.transfer import battery, transfer_tests

T, N_ASSETS, N_BOOT = 2200, 8, 20


def iid_world(T: int, n_assets: int, seed: int) -> dict:
    """Constant-vol Gaussian market: no fat tails, no clock, no leverage."""
    rng = np.random.default_rng(seed)
    r = 0.01 * rng.normal(size=(T, n_assets))
    idx = pd.bdate_range("2012-01-02", periods=T)
    cols = [f"A{j}" for j in range(n_assets)]
    close = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx, columns=cols)
    gkvar = pd.DataFrame(1e-4 * rng.gamma(3.7, 1 / 3.7, (T, n_assets)),
                         index=idx, columns=cols)
    return {"close": close, "gkvar": gkvar}


# --- same mechanism, three seeds: must EXONERATE --------------------------------
worlds = {f"U{i}": simulate_clock_world(T, n_assets=N_ASSETS, seed=10 + i)
          for i in range(3)}
bats = {n: battery(w["close"], w["gkvar"], curve=None, n_boot=N_BOOT)
        for n, w in worlds.items()}
rep = transfer_tests(bats, ref="U0")
n_transfer = sum(1 for q in rep if rep[q]["class"] == "TRANSFERS")
zs = [abs(z) for q in rep for z in rep[q]["z_vs_ref"].values()]
for q in rep:
    print(f"same-mechanism {q:12s} {rep[q]['class']:17s} "
          f"VR={rep[q]['VR']} values={rep[q]['values']}")
print(f"same-mechanism: {n_transfer}/{len(rep)} TRANSFERS, median |z|={np.median(zs):.2f}")
assert n_transfer >= len(rep) - 1, "transfer test convicts identical mechanisms"
assert np.median(zs) < 2.5, "z-scores miscalibrated under the same-mechanism null"

# --- different mechanisms: must CONVICT where the laws differ --------------------
w_iid = iid_world(T, N_ASSETS, seed=99)
bats2 = {"U0": bats["U0"],
         "IID": battery(w_iid["close"], w_iid["gkvar"], curve=None, n_boot=N_BOOT)}
rep2 = transfer_tests(bats2, ref="U0")
for q in rep2:
    print(f"diff-mechanism {q:12s} {rep2[q]['class']:17s} "
          f"z={rep2[q]['z_vs_ref']} values={rep2[q]['values']}")
for q in ("kurt", "commonality"):
    assert rep2[q]["class"] == "UNIVERSE-SPECIFIC", \
        f"transfer test misses the {q} difference between mechanisms"
    assert abs(list(rep2[q]["z_vs_ref"].values())[0]) > 2.5, \
        f"{q} z-score too small for a genuinely different mechanism"

print("\nGATE X24 PASSED")
