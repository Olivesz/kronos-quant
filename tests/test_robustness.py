"""Gate X36: DESIGN25 referee-program estimators (whitened MI + t3 flag).

(a) IDENTITY: the factored E9 block reproduces battery()["stats"]["dir_bits"]
    EXACTLY (in-process equivalence, arch-safe) on simulated worlds — the
    R2/R6 machinery measures the same statistic the battery scores;
(b) ANALYTIC CALIBRATION: on a Gaussian AR(1) world (phi = -0.3) the
    sign_t-alone MI matches the closed form 1 - H2(1/2 + arcsin(phi)/pi)
    within tolerance, the raw joint bits are significant, and the
    AR(1)-whitened bits are NOT — the whitener removes exactly the linear
    one-lag channel;
(c) ORTHOGONALITY: on a world whose sign information rides the vol-tercile
    channel (drift set by the slow vol state, not by yesterday's return),
    whitening PRESERVES significant bits — nonlinear sign structure is not
    destroyed;
(d) fund_t3_scale flag: default 0.0 is BYTE-IDENTICAL to the published
    simulator (X30a/X34a pinned hash reproduced), the flag is live,
    deterministic, finite, and produces measurably heavier tails than the
    Gaussian-fundamental world at matched variance scale;
(e) the threshold rescorer at the published thresholds reproduces the
    battery's own event verdicts on a simulated world.

Fully synthetic, deterministic, no data dependencies.
"""
import hashlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from kronos.decathlon import CONFIGS, battery, simulate_abm
from kronos.robustness import (THRESHOLDS, ar1_whiten, e9_bits,
                               e9_decomposition, rescore_events)

t0 = time.time()

# --- (a) E9-block identity with the battery ---------------------------------------
for name, seed in (("FCVM", 100), ("FV", 101)):
    r = simulate_abm(T=4000, seed=seed, **CONFIGS[name])
    b = battery(r, seed=3)
    db = e9_bits(r, seed=3)
    assert b["stats"]["dir_bits"] == db["bits"], \
        f"E9 block drifted from battery() on {name} (seed {seed})"
print("X36a: factored E9 block == battery dir_bits exactly (2 worlds)")

# --- (b) analytic AR(1) calibration ----------------------------------------------
PHI = -0.3
p_agree = 0.5 + np.arcsin(PHI) / np.pi
closed_mi = 1 - (-p_agree * np.log2(p_agree)
                 - (1 - p_agree) * np.log2(1 - p_agree))
raw_sig, whit_sig, sign_errs = 0, 0, []
for seed in (1, 2, 3):
    rng = np.random.default_rng(seed)
    eps = rng.normal(0, 0.01, 6000)
    x = np.empty(6000)
    x[0] = eps[0]
    for t in range(1, 6000):
        x[t] = PHI * x[t - 1] + eps[t]
    s = pd.Series(x, index=pd.bdate_range("2002-01-01", periods=6000))
    raw = e9_bits(s, seed=seed)
    phi_hat, w = ar1_whiten(s)
    assert abs(phi_hat - PHI) < 0.05, f"AR(1) fit off: {phi_hat:.3f}"
    wb = e9_bits(w, seed=seed)
    dec = e9_decomposition(s, seed=seed)
    sign_errs.append(abs(dec["sign"]["bits"] - closed_mi))
    raw_sig += int(raw["significant"])
    whit_sig += int(wb["significant"])
assert raw_sig == 3, "AR(1) linear sign info not detected in the raw bits"
assert whit_sig == 0, "whitening failed to remove the linear channel"
assert max(sign_errs) < 0.01, \
    f"sign-alone MI off closed form {closed_mi:.4f} by {max(sign_errs):.4f}"
print(f"X36b: AR(1) phi={PHI}: raw significant 3/3, whitened 0/3; "
      f"sign-alone MI within {max(sign_errs):.4f} of closed form {closed_mi:.4f}")

# --- (c) orthogonal channel survives whitening ------------------------------------
def ortho_world(seed: int, T: int = 6000, a: float = 0.35,
                phv: float = 0.98, sv: float = 0.5) -> pd.Series:
    """Sign info rides the slow vol state (tercile drift), not lag-1 r."""
    rng = np.random.default_rng(seed)
    lv = np.zeros(T)
    innov = rng.normal(0, sv * np.sqrt(1 - phv ** 2), T)
    for t in range(1, T):
        lv[t] = phv * lv[t - 1] + innov[t]
    sig = 0.01 * np.exp(lv - lv.var() / 2)
    z = rng.normal(0, 1, T)
    q1, q2 = np.quantile(lv, [1 / 3, 2 / 3])
    d = np.where(lv > q2, 1.0, np.where(lv < q1, -1.0, 0.0))
    r = np.empty(T)
    for t in range(T):
        r[t] = sig[t] * ((a * d[t - 1] if t > 0 else 0.0) + z[t])
    return pd.Series(r, index=pd.bdate_range("2002-01-01", periods=T))


for seed in (0, 1, 2):
    s = ortho_world(seed)
    raw = e9_bits(s, seed=seed)
    _, w = ar1_whiten(s)
    wb = e9_bits(w, seed=seed)
    assert raw["significant"], f"orthogonal world carries no raw bits (seed {seed})"
    assert wb["significant"], \
        f"whitening destroyed nonlinear sign structure (seed {seed})"
    assert wb["bits"] > 0.5 * raw["bits"], \
        f"whitening ate the nonlinear channel (seed {seed}): " \
        f"{raw['bits']:.4f} -> {wb['bits']:.4f}"
print("X36c: vol-tercile sign channel survives whitening on 3/3 seeds")

# --- (d) fund_t3_scale flag -------------------------------------------------------
# default 0.0 byte-identical to the published simulator (the X30a/X34a pin)
r_off = simulate_abm(T=2000, seed=7, fund_t3_scale=0.0, **CONFIGS["FCVM"])
got = hashlib.sha256(r_off.to_numpy().tobytes()).hexdigest()
assert got == "0882dd90e4264600d6fdb2767058577d0102171ef3a43bf91d62d5961ef2a2a4", \
    "fund_t3_scale=0.0 drifted from the pinned published simulator"
SC = 3 * 0.006 / np.sqrt(3)          # loud gate scale (variance-matched x3)
r_a = simulate_abm(T=2000, seed=7, fund_t3_scale=SC, **CONFIGS["FCVM"])
r_b = simulate_abm(T=2000, seed=7, fund_t3_scale=SC, **CONFIGS["FCVM"])
assert not np.allclose(r_off, r_a), "t3 flag has no effect"
assert np.array_equal(r_a.to_numpy(), r_b.to_numpy()), "t3 flag not deterministic"
assert np.isfinite(r_a).all()
kg, kt = [], []
for seed in (0, 1, 2):
    kg.append(float(simulate_abm(T=6000, seed=seed, **CONFIGS["F"]).kurtosis()) + 3)
    kt.append(float(simulate_abm(T=6000, seed=seed, fund_t3_scale=SC,
                                 **CONFIGS["F"]).kurtosis()) + 3)
assert np.median(kt) > np.median(kg) + 0.3, \
    f"t3 fundamentals not measurably heavier-tailed ({np.median(kg):.2f} vs {np.median(kt):.2f})"
print(f"X36d: flag-off pin holds; t3 live/deterministic; F-world kurt "
      f"{np.median(kg):.2f} -> {np.median(kt):.2f} (median of 3 seeds)")

# --- (e) rescorer identity at the published thresholds ----------------------------
r = simulate_abm(T=6000, seed=100, **CONFIGS["FCVM"])
b = battery(r, seed=0)
st = {k: float(v) for k, v in b["stats"].items()
      if isinstance(v, (int, float, np.floating, np.bool_))}
ev = rescore_events(st, THRESHOLDS, e9_pass=b["events"]["E9_no_sign_info"])
assert ev == {k: bool(v) for k, v in b["events"].items()}, \
    f"rescorer disagrees with battery at the published thresholds: " \
    f"{[(k, ev[k], bool(b['events'][k])) for k in ev if ev[k] != bool(b['events'][k])]}"
print("X36e: threshold rescorer == battery events at the published thresholds")

print(f"\nGATE X36 PASSED ({time.time() - t0:.0f}s)")
