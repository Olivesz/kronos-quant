"""Gate X1: Garman-Klass beats close-to-close on synthetic GBM with known vol."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from kronos.volest import gk_variance, c2c_variance, simulate_gbm_ohlc

biases = {}
for n_id in (78, 780):
    sim = simulate_gbm_ohlc(n_days=4000, sigma_ann=0.20, seed=5, n_intraday=n_id)
    true_var = sim["true_var"]
    gk = gk_variance(sim["open"], sim["high"], sim["low"], sim["close"])["X"].dropna()
    c2 = c2c_variance(sim["close"])["X"].dropna()
    biases[n_id] = gk.mean() / true_var - 1
    if n_id == 780:
        bias_c2 = c2.mean() / true_var - 1
        eff = c2.var() / gk.var()

print(f"GK bias @78 intraday steps : {biases[78]:+.1%}  (range discretization)")
print(f"GK bias @780 steps         : {biases[780]:+.1%}  (-> continuous limit)")
print(f"C2C bias                   : {bias_c2:+.1%}")
print(f"variance ratio C2C/GK (efficiency gain): {eff:.1f}x")

# bias must shrink toward zero as discretization vanishes (proves the
# estimator is right and the residual is simulation artifact)
assert abs(biases[780]) < abs(biases[78]) * 0.6, "bias not discretization-driven"
assert abs(biases[780]) < 0.07, "GK estimator biased in continuous limit"
assert abs(bias_c2) < 0.15, "C2C sanity"
assert eff > 3.0, "GK should be much tighter than close-to-close"

# real-data smoke: GK vol on SPY should track c2c vol closely in level.
# The synthetic OHLC generator does not reproduce realistic intraday range,
# so this level check is only meaningful on real data; skip it in the hermetic
# CI mode (the estimator-bias checks above already ran on synthetic truth).
if os.environ.get("KRONOS_SYNTHETIC", "").lower() in ("1", "true", "yes"):
    print("\nGATE X1 PASSED (real-data smoke skipped: KRONOS_SYNTHETIC)")
    sys.exit(0)

from config import CFG
from kronos.data import load_ohlc
ohlc, src = load_ohlc(CFG)
print("\nOHLC source:", src)
gk_real = gk_variance(ohlc["open"], ohlc["high"], ohlc["low"], ohlc["close"])
spy = gk_real["SPY"].dropna()
spy_ann = np.sqrt(spy.rolling(21).mean() * 252).dropna()
c2_spy = c2c_variance(ohlc["close"])["SPY"].dropna()
c2_ann = np.sqrt(c2_spy.rolling(21).mean() * 252).dropna()
join = spy_ann.to_frame("gk").join(c2_ann.rename("c2c")).dropna()
corr = join.corr().iloc[0, 1]
ratio = (join["gk"] / join["c2c"]).median()
print(f"SPY 21d vol: corr(GK,C2C)={corr:.3f}, median level ratio={ratio:.2f}")
print(f"SPY median ann vol (GK): {spy_ann.median():.1%}")
assert corr > 0.85 and 0.7 < ratio < 1.3, "GK real-data sanity failed"

print("\nGATE X1 PASSED")
