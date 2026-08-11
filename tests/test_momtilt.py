"""Gate X33: the momentum exposure tilt (DESIGN21) must add Sharpe on a world
where 21d momentum genuinely predicts sign, TIE on a driftless world with
identical vol dynamics (the mechanism-disappears test), stay inside the
exposure cap under extreme tilts (verified, not assumed — orchestrator
condition), and be exactly causal."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

import numpy as np
import pandas as pd

from config import CFG
from kronos.risk import exposure_series

T = 5000
idx = pd.bdate_range("2010-01-04", periods=T)


def world(trending: bool, seed: int):
    """Persistent-vol market whose drift regime flips slowly (trending=True:
    21d momentum predicts the sign of future drift) or is zero (driftless)."""
    rng = np.random.default_rng(seed)
    rho, eta = 0.98, np.sqrt(0.20 * (1 - 0.98 ** 2))
    h = np.zeros(T)
    for t in range(1, T):
        h[t] = rho * h[t - 1] + eta * rng.normal()
    sig = 0.10 / np.sqrt(252) * np.exp(h)
    drift = np.zeros(T)
    if trending:
        state = 1
        for t in range(T):
            if rng.random() < 0.01:            # ~100-day drift regimes
                state = -state
            drift[t] = state * 0.35 / 252      # +/-35%/yr drift
    r = pd.Series(drift + sig * rng.normal(size=T), index=idx)
    return r


def run(r: pd.Series, mt: float):
    cfg = replace(CFG, mom_tilt=mt, market="MKT")   # market series = the book
    tilt = None
    if mt > 0:
        tilt = 1.0 + mt * np.sign(np.log1p(r).rolling(21).sum()).fillna(0.0)
    ex = exposure_series(r, cfg, tilt=tilt)["exposure"]
    net = (r * ex.shift(1).fillna(1.0)).iloc[300:]
    sr = float(net.mean() / net.std() * np.sqrt(252))
    return sr, ex


# --- trending world: tilt must add Sharpe (3 seeds) -----------------------------
gains = []
for s in (0, 1, 2):
    r = world(True, seed=10 + s)
    sr_t, _ = run(r, 0.15)
    sr_0, _ = run(r, 0.0)
    gains.append(sr_t - sr_0)
print(f"trending world: Sharpe gain from tilt {np.round(gains, 3)} "
      f"(mean {np.mean(gains):+.3f})")
assert np.mean(gains) > 0.05, "tilt adds nothing where momentum predicts sign"
assert min(gains) > 0, "tilt not consistently positive on trending worlds"

# --- driftless world: must tie (no false edge from vol interaction) -------------
diffs = []
for s in (0, 1, 2):
    r = world(False, seed=20 + s)
    sr_t, _ = run(r, 0.15)
    sr_0, _ = run(r, 0.0)
    diffs.append(sr_t - sr_0)
print(f"driftless world: Sharpe diff {np.round(diffs, 3)} (mean {np.mean(diffs):+.3f})")
assert abs(np.mean(diffs)) < 0.05, "tilt invents an edge where the mechanism cannot help"

# --- cap safety under EXTREME tilt (orchestrator condition: verify, not assume) --
r = world(True, seed=42)
cfg = replace(CFG, mom_tilt=0.5, market="MKT")
tilt_extreme = pd.Series(1.5, index=idx)               # permanently max-tilted
ex = exposure_series(r, cfg, tilt=tilt_extreme)["exposure"]
print(f"extreme-tilt max exposure: {ex.max():.4f} (cap {cfg.max_exposure})")
assert (ex <= cfg.max_exposure + 1e-9).all(), "tilt breaches the exposure cap"

# --- causality: truncating the future leaves the tilt path identical ------------
r = world(True, seed=7)
t_full = 1.0 + 0.15 * np.sign(np.log1p(r).rolling(21).sum()).fillna(0.0)
t_trunc = 1.0 + 0.15 * np.sign(np.log1p(r.iloc[:-300]).rolling(21).sum()).fillna(0.0)
diff = (t_full.iloc[:-300] - t_trunc).abs().max()
print(f"causality: max tilt diff after truncating 300 future days = {diff:.2e}")
assert diff < 1e-15, "tilt leaks the future"

print("\nGATE X33 PASSED")
