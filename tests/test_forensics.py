"""Gate X10: forensics validated on known-overfit and known-real worlds."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from kronos.forensics import bootstrap_sharpe_ci, cscv_pbo, deflated_sharpe

rng = np.random.default_rng(61)
T, V = 3000, 200
idx = pd.bdate_range("2014-01-01", periods=T)

# --- world A: pure noise variants (any 'winner' is overfit) ------------------
noise = rng.normal(0, 0.008, (T, V))
resA = cscv_pbo(noise, n_blocks=16, max_combos=3000)
print(f"pure-noise PBO: {resA['pbo']:.2f} (theory ~0.5)")
assert 0.35 < resA["pbo"] < 0.65, "PBO should be ~50% on noise"

# --- world B: one genuinely superior variant ---------------------------------
skilled = noise.copy()
skilled[:, 7] += 0.0008          # ~1.6 ann Sharpe of real skill
resB = cscv_pbo(skilled, n_blocks=16, max_combos=3000)
print(f"planted-skill PBO: {resB['pbo']:.2f} (should be low)")
assert resB["pbo"] < 0.15, "PBO should detect genuine skill"

# --- DSR: best-of-N noise must NOT survive deflation --------------------------
sr_trials = noise.mean(axis=0) / noise.std(axis=0)
best = noise[:, sr_trials.argmax()]
d_noise = deflated_sharpe(pd.Series(best, index=idx), n_trials=V,
                          trial_srs=sr_trials)
print(f"best-of-{V} noise: SR_ann {d_noise['sr_annual']:.2f}, "
      f"SR0_ann {d_noise['sr0_annual']:.2f}, DSR {d_noise['dsr']:.2f}")
assert d_noise["dsr"] < 0.80, "DSR must not certify best-of-noise"

# genuine skill with same trial count must survive
d_skill = deflated_sharpe(pd.Series(skilled[:, 7], index=idx), n_trials=V,
                          trial_srs=skilled.mean(axis=0) / skilled.std(axis=0))
print(f"genuine skill   : SR_ann {d_skill['sr_annual']:.2f}, DSR {d_skill['dsr']:.2f}")
assert d_skill["dsr"] > 0.90, "DSR should favor genuine skill"
assert d_skill["dsr"] > d_noise["dsr"] + 0.3, "DSR must separate skill from luck"

# --- bootstrap CI: covers truth, excludes 0 for skill --------------------------
ci = bootstrap_sharpe_ci(pd.Series(skilled[:, 7], index=idx), n_boot=500)
print(f"bootstrap CI for skilled: [{ci['ci_lo']:.2f}, {ci['ci_hi']:.2f}] "
      f"point {ci['sr_point']:.2f}")
assert ci["ci_lo"] < ci["sr_point"] < ci["ci_hi"]
assert ci["ci_lo"] > 0, "CI should exclude zero for genuine skill"

ci0 = bootstrap_sharpe_ci(pd.Series(noise[:, 0], index=idx), n_boot=500)
assert ci0["ci_lo"] < 0 < ci0["ci_hi"], "CI should include zero for noise"

print("\nGATE X10 PASSED")
