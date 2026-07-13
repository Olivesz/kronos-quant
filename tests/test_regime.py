"""Gate 2: HMM recovers known parameters; real-data regimes match history."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from config import CFG
from kronos.regime import GaussianHMM, walkforward_regimes

rng = np.random.default_rng(7)

# --- synthetic ground truth: 3 well-separated states ------------------------
T = 3000
A_true = np.array([[0.97, 0.02, 0.01],
                   [0.03, 0.94, 0.03],
                   [0.02, 0.04, 0.94]])
means_true = np.array([[0.0008, np.log(0.10)],
                       [0.0000, np.log(0.20)],
                       [-0.0015, np.log(0.35)]])
stds_true = np.array([[0.006, 0.08], [0.012, 0.10], [0.022, 0.12]])

s = np.zeros(T, dtype=int)
for t in range(1, T):
    s[t] = rng.choice(3, p=A_true[s[t - 1]])
X = means_true[s] + stds_true[s] * rng.normal(size=(T, 2))

hmm = GaussianHMM(3, seed=42).fit(X)
print("true A diag :", np.diag(A_true))
print("est  A diag :", np.round(np.diag(hmm.A_), 3))
print("true means[:,0]:", means_true[:, 0])
print("est  means[:,0]:", np.round(hmm.means_[:, 0], 5))

# state alignment after canonicalization: bull=0, volatile=1, bear=2
assert abs(hmm.means_[0, 0] - 0.0008) < 4e-4, "bull mean off"
assert abs(hmm.means_[2, 0] - (-0.0015)) < 1.2e-3, "bear mean off"  # se ~1e-3 w/ ~500 bear obs
assert np.all(np.diag(hmm.A_) > 0.85), "transition persistence not recovered"

# filtered accuracy
fp = hmm.filtered_probs(X)
acc = (fp.argmax(axis=1) == s).mean()
print("filtered state accuracy: %.1f%%" % (100 * acc))
assert acc > 0.80, "filtered accuracy too low"

# --- real data walk-forward --------------------------------------------------
from kronos.data import load_prices

px, src = load_prices(CFG)
mkt = px[CFG.market].pct_change().dropna()
t0 = time.time()
res = walkforward_regimes(mkt, CFG)
elapsed = time.time() - t0
print(f"\nwalk-forward: {res['refits']} refits in {elapsed:.1f}s ({src} data)")

reg = res["regime"]
names = {0: "Bull", 1: "Volatile", 2: "Bear"}
counts = reg[reg >= 0].map(names).value_counts()
print(counts.to_string())

if src == "yahoo":
    # March 2020 must be overwhelmingly Bear/Volatile
    covid = reg.loc["2020-03-01":"2020-04-15"]
    frac = (covid >= 1).mean()
    print("Mar-2020 Bear/Volatile fraction: %.0f%%" % (100 * frac))
    assert frac > 0.7, "COVID crash not detected"
    # 2017 (ultra-calm year) mostly Bull
    calm = reg.loc["2017-01-01":"2017-12-31"]
    frac_bull = (calm == 0).mean()
    print("2017 Bull fraction: %.0f%%" % (100 * frac_bull))
    assert frac_bull > 0.7, "2017 calm bull not detected"

print("\nGATE 2 PASSED")
