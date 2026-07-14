"""Gate X26: the leverage-effect estimator must recover the SIGN of the
leverage effect on synthetic worlds where it is known — negative (equity-like:
down-moves raise next-day vol), positive (inverted: up-moves raise vol), and
~zero (symmetric). This licenses reading a crypto leverage sign (KRONOS-CRYPTO,
C2) as a real property of the data rather than an estimator artifact."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from kronos.constants import _leverage

T, SEEDS = 6000, (0, 1, 2)


def leverage_world(kind: str, T: int = T, seed: int = 0):
    """GJR-style stochastic-vol world with a KNOWN leverage sign.

    Next-day log-vol gets an asymmetric bump from the sign of today's shock:
    equity -> bump after DOWN moves; inverse -> bump after UP moves; symmetric
    -> no bump. Returns (r, gkvar) with a Gamma GK-proxy noise like real data.
    """
    rng = np.random.default_rng(seed)
    mu, rho, eta, gamma = np.log(0.01), 0.94, 0.15, 0.6
    h, prev = mu, 0.0
    r = np.zeros(T)
    gk = np.zeros(T)
    for t in range(T):
        if kind == "equity":
            lev = gamma * max(0.0, -prev)
        elif kind == "inverse":
            lev = gamma * max(0.0, prev)
        else:
            lev = 0.0
        h = mu + rho * (h - mu) + lev + eta * rng.normal()
        sig = np.exp(h)
        innov = rng.normal()
        r[t] = sig * innov
        gk[t] = sig ** 2 * rng.gamma(3.7, 1 / 3.7)
        prev = innov
    return r, gk


def measure(kind):
    vals = [_leverage(*leverage_world(kind, seed=s)) for s in SEEDS]
    return np.array(vals)


eq, inv, sym = measure("equity"), measure("inverse"), measure("symmetric")
print(f"equity    leverage: mean {eq.mean():+.3f}  per-seed {np.round(eq, 3)}")
print(f"inverse   leverage: mean {inv.mean():+.3f}  per-seed {np.round(inv, 3)}")
print(f"symmetric leverage: mean {sym.mean():+.3f}  per-seed {np.round(sym, 3)}")

# --- SIZE: symmetric world must read ~0 (no spurious leverage) ------------------
assert abs(sym.mean()) < 0.04, "spurious leverage on a symmetric world"

# --- POWER + SIGN: equity negative, inverse positive, every seed consistent -----
assert eq.mean() < -0.05, "failed to detect the equity (negative) leverage effect"
assert inv.mean() > 0.05, "failed to detect the inverted (positive) leverage effect"
assert (eq < 0).all(), "equity leverage sign not recovered on every seed"
assert (inv > 0).all(), "inverse leverage sign not recovered on every seed"

# --- SEPARATION: correct ordering and a wide, unambiguous gap -------------------
assert eq.mean() < sym.mean() < inv.mean(), "leverage ordering wrong"
assert inv.mean() - eq.mean() > 0.15, "equity/inverse worlds not separable"
print(f"separation (inverse - equity) = {inv.mean() - eq.mean():+.3f}")

print("\nGATE X26 PASSED")
