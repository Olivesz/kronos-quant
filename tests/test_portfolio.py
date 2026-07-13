"""Gates 4 & 5: HRP sanity + Black-Litterman behavioral checks."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from config import CFG
from kronos.black_litterman import construct_portfolio
from kronos.covariance import shrunk_cov
from kronos.hrp import hrp_weights

rng = np.random.default_rng(3)

# --- HRP toy case -------------------------------------------------------------
# 2 correlated risky assets + 1 quiet diversifier: HRP must overweight the quiet one
cov = pd.DataFrame(
    [[0.04, 0.032, 0.001],
     [0.032, 0.04, 0.001],
     [0.001, 0.001, 0.005]],
    index=["RISKY1", "RISKY2", "QUIET"], columns=["RISKY1", "RISKY2", "QUIET"])
w = hrp_weights(cov)
print("HRP toy weights:\n", w.round(3).to_string())
assert abs(w.sum() - 1) < 1e-9 and (w >= 0).all()
assert w["QUIET"] > w["RISKY1"] and w["QUIET"] > w["RISKY2"]
assert abs(w["RISKY1"] - w["RISKY2"]) < 0.05  # symmetric risks ~ symmetric weights

# --- shrunk covariance is PSD and sane ----------------------------------------
X = pd.DataFrame(rng.normal(0, 0.01, (300, 12)),
                 columns=[f"A{i}" for i in range(12)])
S = shrunk_cov(X, halflife=63, window=252)
eig = np.linalg.eigvalsh(S.to_numpy())
print("shrunk cov min eig: %.2e" % eig.min())
assert eig.min() > -1e-12, "covariance not PSD"

# --- BL behavioral checks -------------------------------------------------------
N = 12
A = rng.normal(0, 0.01, (400, N))
rets = pd.DataFrame(A, columns=[f"A{i}" for i in range(N)])
cov2 = shrunk_cov(rets, 63, 252)

# zero views -> posterior == prior, tilt == HRP
z0 = pd.Series(0.0, index=cov2.index)
res0 = construct_portfolio(cov2, z0, CFG)
assert np.allclose(res0["mu"], res0["pi"], atol=1e-12), "zero views should leave prior"
assert np.allclose(res0["weights"], res0["hrp"], atol=1e-9), "zero views should keep HRP"

# strong positive view on A3 -> its weight rises vs HRP
z1 = z0.copy(); z1["A3"] = 3.0
res1 = construct_portfolio(cov2, z1, CFG)
print("A3 weight: HRP %.3f -> BL %.3f" % (res1["hrp"]["A3"], res1["weights"]["A3"]))
assert res1["weights"]["A3"] > res1["hrp"]["A3"], "positive view didn't raise weight"
assert res1["weights"].max() <= CFG.max_weight + 1e-9, "cap violated"
assert abs(res1["weights"].sum() - 1) < 1e-9 and (res1["weights"] >= -1e-12).all()

print("\nGATES 4 & 5 PASSED")
