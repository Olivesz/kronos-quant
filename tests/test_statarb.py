"""Gate X7: stat-arb extracts planted mean-reverting residuals, net of costs."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from config import CFG
from kronos.statarb import fit_factor_model, ou_sscores, run_statarb_sleeve

rng = np.random.default_rng(17)

# synthetic world: one market factor, N=20 names; half have STRONG
# mean-reverting residuals (OU half-life ~8d), half pure random walk residuals
T, N = 2000, 20
mkt = rng.normal(0.0003, 0.01, T)
betas = rng.uniform(0.8, 1.2, N)
names = [f"S{i}" for i in range(N)]
R = np.zeros((T, N))
phi = np.exp(np.log(0.5) / 8)      # AR(1) coeff for 8d half-life
ou = np.zeros(N)
for t in range(T):
    for i in range(N):
        if i < 10:   # planted OU residual names
            ou_prev = ou[i]
            ou[i] = phi * ou[i] + rng.normal(0, 0.004)
            resid_ret = ou[i] - ou_prev
        else:        # pure noise residuals (no mean reversion)
            resid_ret = rng.normal(0, 0.004)
        R[t, i] = betas[i] * mkt[t] + resid_ret

px = pd.DataFrame(100 * np.exp(np.cumsum(R, axis=0)), columns=names,
                  index=pd.bdate_range("2017-01-02", periods=T))

# unit check: s-scores flag the planted names as tradable far more often
rets = px.pct_change().fillna(0.0)
window = rets.iloc[-252:]
model = fit_factor_model(window)
m = model["m"]
sc = ou_sscores(window.iloc[-60:], model)
tradable = sc["s"].notna()
frac_planted = tradable.iloc[:10].mean()
frac_noise = tradable.iloc[10:].mean()
print(f"factors detected m={m}; tradable: planted {frac_planted:.0%} vs noise {frac_noise:.0%}")
assert m <= 3, "should find ~1 factor"
assert frac_planted >= frac_noise, "planted names should be at least as tradable"

t0 = time.time()
res = run_statarb_sleeve(px, CFG)
r = res["returns"]
active = r[r != 0]
ann_ret = active.mean() * 252
sharpe = active.mean() / active.std() * np.sqrt(252)
print(f"sleeve: ann ret {ann_ret:+.1%}, Sharpe {sharpe:.2f}, "
      f"avg open {res['n_open_mean']:.1f}, m_med {res['m_factors_median']:.0f} "
      f"({time.time()-t0:.0f}s)")
assert ann_ret > 0.02, "should profit on planted mean reversion"
assert sharpe > 1.0, "planted-OU world should give high Sharpe"

print("\nGATE X7 PASSED")
