"""Gate X20: the EWS test convicts a fold bifurcation, exonerates a shock."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from kronos.critical import (ews_indicators, walkforward_incremental_auc,
                             bootstrap_auc_gain, kappa_from_phi, _ar1_phi,
                             simulate_fold_world, simulate_shock_world,
                             jumps_to_labels)

# --- kappa estimator: OU with known mean reversion ------------------------------
rng = np.random.default_rng(3)
for theta in (0.05, 0.5):
    phi_true = np.exp(-theta)
    x = np.zeros(20000)
    for t in range(1, 20000):
        x[t] = phi_true * x[t - 1] + rng.normal()
    phi_hat = _ar1_phi(x)
    print(f"OU theta={theta}: kappa_true={theta:.3f} kappa_hat={kappa_from_phi(phi_hat):.3f}")
    assert abs(kappa_from_phi(phi_hat) - theta) < 0.05

def run_world(world_fn, seed, label):
    w = world_fn(8000, seed=seed)
    x = pd.Series(w["x"], index=pd.RangeIndex(len(w["x"])))
    dx = x.diff().fillna(0)
    feats = ews_indicators(x, dx, L=60)
    labels = pd.Series(jumps_to_labels(w["jumps"], H=20), index=x.index)
    res = walkforward_incremental_auc(feats, labels, refit_every=500,
                                      min_train=1500)
    boot = bootstrap_auc_gain(res["pred_vol"], res["pred_all"], res["labels"],
                              n_boot=300, seed=seed)
    print(f"{label}: AUC vol={res['auc_vol']:.3f} all={res['auc_all']:.3f} "
          f"gain={boot['gain']:+.3f} CI[{boot['ci_lo']:+.3f},{boot['ci_hi']:+.3f}] "
          f"(n_pos={res['n_pos']})")
    return boot

print("\n-- fold-bifurcation world (CSD present: test must CONVICT) --")
fold = run_world(simulate_fold_world, 1, "fold")
print("\n-- shock world (no CSD: test must EXONERATE) --")
shock = run_world(simulate_shock_world, 2, "shock")

assert fold["ci_lo"] > 0, "must detect CSD incremental signal in the fold world"
assert shock["ci_lo"] <= 0, "must NOT find incremental signal in the shock world"
assert fold["gain"] > shock["gain"] + 0.02, "fold must beat shock clearly"

print("\nGATE X20 PASSED")
