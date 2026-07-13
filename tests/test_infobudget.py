"""Gate X17: MI estimators against closed-form truth; size and power."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from kronos.infobudget import (
    binary_sharpe_ceiling,
    bits_consumed_by,
    direction_bits,
    discrete_mi,
    gaussian_sharpe_ceiling,
    ksg_mi,
    ksg_mi_net,
)

rng = np.random.default_rng(91)
N = 4000

# --- 1. KSG vs closed-form Gaussian MI -----------------------------------------
print("rho    true(nats)  KSG(nats)")
for rho in (0.1, 0.5, 0.9):
    x = rng.normal(size=N)
    y = rho * x + np.sqrt(1 - rho ** 2) * rng.normal(size=N)
    true = -0.5 * np.log(1 - rho ** 2)
    est = ksg_mi(x, y)
    print(f"{rho:.1f}    {true:.4f}      {est:.4f}")
    assert abs(est - true) < 0.015 + 0.05 * true, f"KSG off at rho={rho}"

# --- 2. AR(1) one-step MI --------------------------------------------------------
phi = 0.95
x = np.zeros(N + 1)
for t in range(1, N + 1):
    x[t] = phi * x[t - 1] + rng.normal() * np.sqrt(1 - phi ** 2)
true = -0.5 * np.log(1 - phi ** 2)
est = ksg_mi(x[:-1], x[1:])
print(f"AR(1) phi=0.95: true {true:.3f} vs KSG {est:.3f}")
assert abs(est - true) < 0.10 * true + 0.02

# --- 3. shuffle-net on independent data ≈ 0 --------------------------------------
res0 = ksg_mi_net(rng.normal(size=N), rng.normal(size=N))
print(f"independent: net {res0['mi_nats']:.4f} (raw {res0['raw']:.4f})")
assert res0["mi_nats"] < 0.01

# --- 4. discrete binary channel with known I -------------------------------------
p = 0.55                                   # hit rate
xs = rng.integers(0, 2, N)
flip = rng.random(N) > p
ys = np.where(flip, 1 - xs, xs)
true_bits = 1 - (-p * np.log2(p) - (1 - p) * np.log2(1 - p))
est_bits = discrete_mi(xs, ys) / np.log(2)
print(f"binary channel p=0.55: true {true_bits:.4f} bits vs est {est_bits:.4f}")
assert abs(est_bits - true_bits) < 0.003

# --- 5. direction_bits: size on noise, power on planted signal --------------------
idx = pd.bdate_range("2010-01-01", periods=N)
r = pd.Series(rng.normal(0, 0.01, N), index=idx)
feats = pd.DataFrame({"sign_t": np.sign(r), "noise": rng.integers(0, 3, N)},
                     index=idx)
future = pd.Series(np.sign(rng.normal(size=N)), index=idx)
d0 = direction_bits(feats, future, n_shuffle=100)
print(f"null world: bits {d0['bits']:.5f} vs null95 {d0['null_p95']:.5f} "
      f"sig={d0['significant']}")
assert not d0["significant"], "must not find direction bits in noise"

# planted: tomorrow's sign follows today's with p=0.56
s = np.sign(rng.normal(size=N))
nxt = np.where(rng.random(N) < 0.56, s, -s)
featsP = pd.DataFrame({"sign_t": s}, index=idx)
futureP = pd.Series(nxt, index=idx)
dP = direction_bits(featsP, futureP, n_shuffle=100)
print(f"planted p=0.56: bits {dP['bits']:.5f} (true {1-(-0.56*np.log2(0.56)-0.44*np.log2(0.44)):.5f}) "
      f"sig={dP['significant']}")
assert dP["significant"], "must detect planted sign predictability"

# --- 6. ceiling sanity -------------------------------------------------------------
sr1 = binary_sharpe_ceiling(dP["bits_net"])
print(f"planted world implied Sharpe ceiling: {sr1:.2f} "
      f"(true edge => {(2*0.56-1)*np.sqrt(252):.2f})")
assert abs(sr1 - (2 * 0.56 - 1) * np.sqrt(252)) < 0.7
assert abs(bits_consumed_by(gaussian_sharpe_ceiling(0.05)) - 0.05/np.log(2)) < 0.01

print("\nGATE X17 PASSED")
