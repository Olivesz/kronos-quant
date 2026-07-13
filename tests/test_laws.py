"""Gate X14: the law-screen machinery on worlds where the answer is known."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from kronos.laws import (simulate_sv_world, kurtosis_law, logvol_signal_variance,
                         standardized_returns, tail_report, mrw_lambda2)

# --- L2 machinery: recovers the parameter-free law on a pure SV world ---------
errs = []
for seed in range(5):
    w = simulate_sv_world(6000, s2=0.12, seed=seed)
    res = kurtosis_law(w["close"], w["gkvar"])
    errs.append(res["kurt_pred"] / w["true_kurt_sv"] - 1)
print(f"SV world: pred/true kurt ratio err = {np.mean(errs):+.1%} ± {np.std(errs):.1%}")
assert abs(np.mean(errs)) < 0.20, "kurtosis-law machinery biased on SV world"

# realized kurtosis should also roughly match prediction on the SV world
w = simulate_sv_world(6000, s2=0.12, seed=11)
res = kurtosis_law(w["close"], w["gkvar"])
print(f"SV world: pred {res['kurt_pred']:.2f} vs realized {res['kurt_real']:.2f} "
      f"(theory {w['true_kurt_sv']:.2f})")
assert abs(res["kurt_pred"] - res["kurt_real"]) < 1.5

# with jumps, realized must EXCEED predicted (the deviation is the jump part)
wj = simulate_sv_world(6000, s2=0.12, jumps=6.0, seed=3)
rj = kurtosis_law(wj["close"], wj["gkvar"])
print(f"SV+jumps: pred {rj['kurt_pred']:.2f} vs realized {rj['kurt_real']:.2f} (must exceed)")
assert rj["kurt_real"] > rj["kurt_pred"] + 1.0

# --- L1 machinery: standardization gaussianizes a fat SV world -----------------
# subtlety the gate must encode: raw single-day GK carries multiplicative
# measurement noise whose reciprocal sqrt is itself fat-tailed — naive
# standardization INJECTS tails; smoothing the vol estimate first fixes it.
close_df = w["close"].to_frame("X")
gk_df = w["gkvar"].to_frame("X")
raw_rep = tail_report(np.log(w["close"] / w["close"].shift(1)).dropna())
z1_rep = tail_report(standardized_returns(close_df, gk_df, smooth=1)["X"])
z5_rep = tail_report(standardized_returns(close_df, gk_df, smooth=5)["X"])
print(f"L1 on SV world: raw kurt {raw_rep['kurt']:.1f} | z(smooth=1) {z1_rep['kurt']:.1f} "
      f"(noise-injected) | z(smooth=5) {z5_rep['kurt']:.1f}")
assert z1_rep["kurt"] > z5_rep["kurt"], "smoothing must remove proxy-noise tails"
assert z5_rep["kurt"] < raw_rep["kurt"] - 0.5, "smoothed deformation must gaussianize"
assert abs(z5_rep["kurt"] - 3) < 0.7, "SV world should be ~Gaussian after deformation"

# --- L3 machinery: Brownian world must give lambda2 ~ 0 ------------------------
rng = np.random.default_rng(5)
bm = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 6000))),
               index=pd.bdate_range("2012-01-02", periods=6000))
lam_bm = mrw_lambda2(bm)
# and the SV world (persistent vol) must give lambda2 > Brownian
lam_sv = mrw_lambda2(w["close"])
print(f"L3: lambda2 Brownian {lam_bm['lambda2']:.4f} vs SV {lam_sv['lambda2']:.4f}")
assert abs(lam_bm["lambda2"]) < 0.02, "Brownian world should have ~zero intermittency"
assert lam_sv["lambda2"] > lam_bm["lambda2"], "SV world should be more intermittent"

print("\nGATE X14 PASSED")
