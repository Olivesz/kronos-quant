"""Gate X9: regret sublinear; fixed-share adapts to expert switch."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from kronos.ensemble import run_meta

rng = np.random.default_rng(51)
T, K = 3000, 4
idx = pd.bdate_range("2014-01-01", periods=T)

# world where the best expert SWITCHES at half-time
R = rng.normal(0, 0.006, (T, K))
R[:T//2, 0] += 0.0008      # expert 0 best in first half
R[T//2:, 2] += 0.0008      # expert 2 best in second half
sleeves = pd.DataFrame(R, index=idx, columns=list("ABCD"))

hedge = run_meta(sleeves, "hedge")
fs = run_meta(sleeves, "fixed_share", share=0.005)

# regret must be sublinear: second-half regret growth < first-half growth
for name, res in (("hedge", hedge), ("fixed_share", fs)):
    reg = res["regret"].to_numpy()
    g1 = reg[T//2] - reg[100]
    g2 = reg[-1] - reg[T//2]
    print(f"{name}: regret T/2={reg[T//2]:.1f}, T={reg[-1]:.1f} "
          f"(growth {g1:.1f} -> {g2:.1f})")

# fixed-share must adapt: expert 2 weight in late sample should dominate
w_late = fs["weights"].iloc[-250:].mean()
print("fixed-share late weights:", dict(w_late.round(2)))
assert w_late["C"] == w_late.max() and w_late["C"] > 0.35, "did not adapt to switch"

# fixed-share should beat plain hedge in a switching world
sr = lambda r: r.mean() / r.std() * np.sqrt(252)
print(f"Sharpe: fixed-share {sr(fs['returns']):.2f} vs hedge {sr(hedge['returns']):.2f} "
      f"vs best-static {sr(sleeves['A']):.2f}/{sr(sleeves['C']):.2f}")
assert sr(fs["returns"]) >= sr(hedge["returns"]) - 0.05

# stationary world: hedge should converge near the single best expert
R2 = rng.normal(0, 0.006, (T, K)); R2[:, 1] += 0.0006
sl2 = pd.DataFrame(R2, index=idx, columns=list("ABCD"))
h2 = run_meta(sl2, "hedge")
w_end = h2["weights"].iloc[-1]
print("stationary world final weights:", dict(w_end.round(2)))
assert w_end["B"] == w_end.max() and w_end["B"] > 0.5

print("\nGATE X9 PASSED")
