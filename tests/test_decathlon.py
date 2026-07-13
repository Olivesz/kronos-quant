"""Gate X19: battery dynamic range — SPY scores ~10, GBM scores ~3."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from kronos.decathlon import battery, simulate_abm
from config import CFG
from kronos.data import load_prices

# --- real SPY (close-only) must pass nearly everything --------------------------
px, src = load_prices(CFG)
r_spy = px[CFG.market].pct_change().dropna()
t0 = time.time()
b_spy = battery(r_spy)
print(f"SPY battery ({time.time()-t0:.0f}s): score {b_spy['score']}/10")
for k, v in b_spy["events"].items():
    mark = "PASS" if v else "FAIL"
    print(f"  {k:20s} {mark}")
assert b_spy["score"] >= 9, "the battery must recognize the real market"

# --- pure GBM must fail the stylized events --------------------------------------
rng = np.random.default_rng(5)
gbm = pd.Series(rng.normal(0.0003, 0.01, 6000),
                index=pd.bdate_range("2002-01-01", periods=6000))
b_gbm = battery(gbm)
print(f"\nGBM battery: score {b_gbm['score']}/10 "
      f"(passes: {[k for k, v in b_gbm['events'].items() if v]})")
assert b_gbm["score"] <= 4, "GBM must fail the stylized events"
assert b_gbm["events"]["E1_efficiency"] and b_gbm["events"]["E9_no_sign_info"]

# --- ABM sanity: runs, finite, reasonable vol, deterministic ----------------------
r1 = simulate_abm(T=3000, seed=1)
r2 = simulate_abm(T=3000, seed=1)
assert np.allclose(r1, r2), "ABM must be deterministic given seed"
ann = r1.std() * np.sqrt(252)
print(f"\nABM (FCV defaults): ann vol {ann:.1%}, kurt {float(r1.kurtosis())+3:.1f}")
assert np.isfinite(r1).all() and 0.02 < ann < 1.0, "ABM vol insane"

print("\nGATE X19 PASSED")
