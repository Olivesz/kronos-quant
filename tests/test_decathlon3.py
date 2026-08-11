"""Gate X32: DECATHLON-3 fixed-point anticipation (DESIGN20).

(a) with the feature off, simulate_abm is BYTE-IDENTICAL to the
    pre-DESIGN20 simulator: X30a's flag-off pins still hold at
    fixed_point_iters=0, and the DECA2 anticipator path (pinned pre-change
    hashes) is reproduced at fixed_point_iters in {0, 1} — protecting
    X19's SPY-10/GBM-3 calibration AND DECA2's published rows;
(b) the ITERATED path is CAUSAL: tampering with future returns must not
    change the K=5 trade prefix (truncation trick, X30b extended);
(c) mechanism sanity on the deterministic X30c toy world: the forecastable
    fraction of TOTAL flow — the projection of realized total flow onto the
    (perfectly forecastable) mechanical flow — is non-increasing over
    K = 0 -> 1 -> 5, and at K=5 it is below K=1: the operator contracts.

Fully synthetic, deterministic, no data dependencies.
"""
import hashlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from kronos.decathlon import (CONFIGS, CONFIGS2, DEFAULTS, _ant_target_fp,
                              anticipator_flows, simulate_abm)

t0 = time.time()

# --- (a) feature off => byte-identical to the pre-DESIGN20 simulator ------------
# X30a's flag-off pins, re-asserted with fixed_point_iters passed explicitly.
PINNED_OFF = [
    ("FCVM", 7, 2000, "0882dd90e4264600d6fdb2767058577d0102171ef3a43bf91d62d5961ef2a2a4"),
    ("G",    5, 1000, "6e251afb01c1038a480b093caa1bae898c9e9f46440db4cf7c478b3411166161"),
]
for name, seed, T, want in PINNED_OFF:
    r = simulate_abm(T=T, seed=seed, fixed_point_iters=0, **CONFIGS[name])
    got = hashlib.sha256(r.to_numpy().tobytes()).hexdigest()
    assert got == want, f"flag-off output drifted for {name} (seed {seed})"

# DECA2's anticipator path (sha256 of simulate_abm(...).to_numpy().tobytes(),
# captured at the commit BEFORE fixed_point_iters existed) must be reproduced
# at K=0 (legacy default) AND K=1 (the stack's single layer) — DECA2's
# published FCVM+A/FV+A/F+A rows depend on it.
PINNED_A = [
    ("FCVM+A", 7, 2000, "c21cf3ea0bc43c4df6f0465db26dcb6360ce0f6d4164b87e85e6b734e9c08db9"),
    ("FV+A",   3, 2000, "87f5ff45cc40b0869db6fb598244cb9807cb56a5057aaa7f8aa4eb6d3e85ac0a"),
    ("F+A",    2, 1200, "0bc35dd4e50e626f1352be5d122ba5e86fe920a58ee614ed2a2ccc4c6c83c4f5"),
]
for name, seed, T, want in PINNED_A:
    for iters in (0, 1):
        r = simulate_abm(T=T, seed=seed, fixed_point_iters=iters,
                         **CONFIGS2[name])
        got = hashlib.sha256(r.to_numpy().tobytes()).hexdigest()
        assert got == want, \
            f"DECA2 anticipator path drifted for {name} at K={iters}"
print(f"X32a: {len(PINNED_OFF)} flag-off + {len(PINNED_A)} anticipator configs "
      "byte-identical at K in {0,1}")

# K must be LIVE (K=5 is a different world) and deterministic
r_k1 = simulate_abm(T=2000, seed=7, fixed_point_iters=1, **CONFIGS2["FCVM+A"])
r_k5a = simulate_abm(T=2000, seed=7, fixed_point_iters=5, **CONFIGS2["FCVM+A"])
r_k5b = simulate_abm(T=2000, seed=7, fixed_point_iters=5, **CONFIGS2["FCVM+A"])
assert not np.allclose(r_k1, r_k5a), "fixed_point_iters has no effect"
assert np.array_equal(r_k5a.to_numpy(), r_k5b.to_numpy()), "not deterministic"
assert np.isfinite(r_k5a).all()
ann = r_k5a.std() * np.sqrt(252)
assert 0.02 < ann < 1.0, "K=5 world vol insane"
print(f"X32a: K live and deterministic (K=5 ann vol {ann:.1%})")

# --- (b) causality: the future must not reach the K=5 trades --------------------
rng = np.random.default_rng(0)
r_base = rng.normal(0.0, 0.01, 1500)
r_base[700:720] -= 0.03                     # a vol episode the stack reacts to
f_base = anticipator_flows(r_base, fixed_point_iters=5)
assert np.array_equal(f_base, anticipator_flows(r_base, fixed_point_iters=5)), \
    "helper not deterministic"

CUT = 1000
for tamper_seed in (1, 2, 3):
    rt = np.random.default_rng(tamper_seed)
    r_tam = r_base.copy()
    r_tam[CUT:] = rt.permutation(r_tam[CUT:]) * rt.uniform(-3.0, 3.0)
    f_tam = anticipator_flows(r_tam, fixed_point_iters=5)
    # flow[t] may use r[:t] only => flows 0..CUT (inclusive) must be identical
    assert np.array_equal(f_base[:CUT + 1], f_tam[:CUT + 1]), \
        "future returns changed the stack's past trades — look-ahead"
    assert not np.array_equal(f_base[CUT + 1:], f_tam[CUT + 1:]), \
        "iterated forecast ignores the data entirely"
# truncation form: the prefix of the series gives the prefix of the trades
assert np.array_equal(anticipator_flows(r_base[:CUT], fixed_point_iters=5),
                      f_base[:CUT])
print("X32b: causal at K=5 — future tampering leaves the trade prefix "
      "unchanged (3 tampers + truncation)")

# --- (c) toy world: the operator contracts the forecastable flow ----------------
# The X30c deterministic world: one vol-targeting cohort starts de-levered
# after a vol shock (sigma_hat = 3 * sigma*), no noise anywhere — every flow
# is a deterministic function of the public state, i.e. perfectly
# forecastable. The forecastable fraction of TOTAL flow is measured as the
# projection of realized total flow onto the mechanical flow,
#   beta_K = <f_mech, D_K> / <f_mech, f_mech>
# (beta_0 = 1 exactly; uncapped theory beta_K = (1-kA)^K). DESIGN20 requires
# beta non-increasing over K = 0 -> 1 -> 5 and beta_5 < beta_1.
p = dict(DEFAULTS)
TOY_T = 150


def run_toy(iters: int):
    """Total flow D_t and mechanical flow fm_t; iters=0 = no anticipators."""
    sig2 = np.array([(3.0 * p["sig_target"]) ** 2])
    L_prev = np.array([1.0])
    I_prev = 0.0
    flows, f_mech = [], []
    for _ in range(TOY_T):
        L = np.minimum(p["Lmax"],
                       p["sig_target"] / np.maximum(np.sqrt(sig2), 1e-5))
        fm = p["kV"] * float((L - L_prev).sum())
        L_prev = L
        D = fm
        if iters > 0:
            I_star = _ant_target_fp(sig2, p, iters)
            D += I_star - I_prev
            I_prev = I_star
        r = p["lam"] * D
        flows.append(D)
        f_mech.append(fm)
        # ambient activity pins the estimator's fixed point at the target
        # (the deterministic analogue of the full sim's noise floor)
        sig2 = (1 - p["a_s"]) * sig2 + p["a_s"] * (r ** 2 + p["sig_target"] ** 2)
    return np.array(flows), np.array(f_mech), I_prev


betas = {}
for K in (0, 1, 5):
    D, fm, I_end = run_toy(K)
    betas[K] = float(np.sum(fm * D) / np.sum(fm ** 2))
    assert abs(I_end) < 0.1 * p["capA"], f"K={K} stack failed to unwind"
assert abs(betas[0] - 1.0) < 1e-12, "K=0 total flow must equal mechanical flow"
assert betas[1] <= betas[0] and betas[5] <= betas[1], \
    f"forecastable-flow fraction not non-increasing in K: {betas}"
assert betas[5] < betas[1], \
    f"the operator does not contract beyond one layer: {betas}"
theory = {K: (1 - p["kA"]) ** K for K in (0, 1, 5)}
assert abs(betas[5] - theory[5]) < 0.05, \
    f"K=5 contraction far from the (1-kA)^K theory: {betas[5]} vs {theory[5]}"
print("X32c: toy forecastable-flow fraction " +
      " -> ".join(f"K={K}: {betas[K]:.3f}" for K in (0, 1, 5)) +
      f"  (theory (1-kA)^K: {theory[1]:.3f}/{theory[5]:.3f})")

print(f"\nGATE X32 PASSED ({time.time() - t0:.0f}s)")
