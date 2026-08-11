"""Gate X30: DECATHLON-2 anticipatory agent (DESIGN18).

(a) with anticipators=False, simulate_abm is BYTE-IDENTICAL to the
    pre-DESIGN18 simulator (pinned sha256 of the raw float64 output) —
    this protects gate X19's SPY-10/GBM-3 calibration;
(b) the flow forecast is CAUSAL: tampering with future returns must not
    change the trade prefix (truncation trick);
(c) mechanism sanity on a deterministic toy world with a perfectly
    predictable mechanical flow: the anticipator profits AND damps the
    flow's price impact.

Fully synthetic, deterministic, no data dependencies.
"""
import hashlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from kronos.decathlon import CONFIGS, DEFAULTS, _ant_target, anticipator_flows, simulate_abm

t0 = time.time()

# --- (a) flag OFF => byte-identical to the pre-change simulator -----------------
# sha256 of simulate_abm(...).to_numpy().tobytes(), captured at the commit
# BEFORE the anticipatory agent existed. Any drift here breaks X19's
# calibration and fails the gate.
PINNED = [
    ("FCVM",  7, 2000, "0882dd90e4264600d6fdb2767058577d0102171ef3a43bf91d62d5961ef2a2a4"),
    ("FV",    3, 2000, "a4b4823db5a11f95def5b2ffe82113707d1b099d7864cf4d6ceb2f1ba4a791fd"),
    ("FCVMH", 11, 1500, "6e47c2e4bf21f8dc988faf9aa682a696a168fd6e0a0eac4ffdb4e65e2d106571"),
    ("G",     5, 1000, "6e251afb01c1038a480b093caa1bae898c9e9f46440db4cf7c478b3411166161"),
    ("F",     2, 1200, "0ed356db2977c8acf43dd5160894f95a0317435664b572dc76a8cb85686914c2"),
]
for name, seed, T, want in PINNED:
    r = simulate_abm(T=T, seed=seed, **CONFIGS[name])
    got = hashlib.sha256(r.to_numpy().tobytes()).hexdigest()
    assert got == want, f"flag-off output drifted for {name} (seed {seed})"
print(f"X30a: {len(PINNED)} pinned configs byte-identical with anticipators off")

# the flag must be LIVE (on => different world) and deterministic
r_off = simulate_abm(T=2000, seed=7, **CONFIGS["FCVM"])
r_on1 = simulate_abm(T=2000, seed=7, anticipators=True, **CONFIGS["FCVM"])
r_on2 = simulate_abm(T=2000, seed=7, anticipators=True, **CONFIGS["FCVM"])
assert not np.allclose(r_off, r_on1), "anticipators flag has no effect"
assert np.array_equal(r_on1.to_numpy(), r_on2.to_numpy()), "not deterministic"
assert np.isfinite(r_on1).all()
ann = r_on1.std() * np.sqrt(252)
assert 0.02 < ann < 1.0, "anticipator world vol insane"
print(f"X30a: flag live and deterministic (FCVM+A ann vol {ann:.1%})")

# --- (b) causality: the future must not reach the present trade ------------------
rng = np.random.default_rng(0)
r_base = rng.normal(0.0, 0.01, 1500)
r_base[700:720] -= 0.03                     # a vol episode the agent reacts to
f_base = anticipator_flows(r_base)
assert np.array_equal(f_base, anticipator_flows(r_base)), "helper not deterministic"

CUT = 1000
for tamper_seed in (1, 2, 3):
    rt = np.random.default_rng(tamper_seed)
    r_tam = r_base.copy()
    r_tam[CUT:] = rt.permutation(r_tam[CUT:]) * rt.uniform(-3.0, 3.0)
    f_tam = anticipator_flows(r_tam)
    # flow[t] may use r[:t] only => flows 0..CUT (inclusive) must be identical
    assert np.array_equal(f_base[:CUT + 1], f_tam[:CUT + 1]), \
        "future returns changed the anticipator's past trades — look-ahead"
    assert not np.array_equal(f_base[CUT + 1:], f_tam[CUT + 1:]), \
        "forecast ignores the data entirely"
# truncation form: the prefix of the series gives the prefix of the trades
assert np.array_equal(anticipator_flows(r_base[:CUT]), f_base[:CUT])
print("X30b: causal — future tampering leaves the trade prefix unchanged (3 tampers + truncation)")

# --- (c) toy world: perfectly predictable mechanical flow ------------------------
# One vol-targeting cohort starts de-levered after a vol shock
# (sigma_hat = 3 * sigma*), no noise anywhere: the re-leveraging path is
# deterministic and exactly what the anticipator's model forecasts.
p = dict(DEFAULTS)
TOY_T = 150


def run_toy(with_ant: bool):
    sig2 = np.array([(3.0 * p["sig_target"]) ** 2])
    L_prev = np.array([1.0])
    I_prev = 0.0
    rets, f_mech, inv = [], [], []
    for _ in range(TOY_T):
        L = np.minimum(p["Lmax"],
                       p["sig_target"] / np.maximum(np.sqrt(sig2), 1e-5))
        fm = p["kV"] * float((L - L_prev).sum())
        L_prev = L
        D = fm
        if with_ant:
            I_star = _ant_target(sig2, p)
            D += I_star - I_prev
            I_prev = I_star
        r = p["lam"] * D
        rets.append(r)
        f_mech.append(fm)
        inv.append(I_prev)
        # ambient activity pins the estimator's fixed point at the target —
        # the deterministic analogue of the full sim's noise floor (without
        # it toy vol collapses to 0 and the targeters pin at Lmax forever)
        sig2 = (1 - p["a_s"]) * sig2 + p["a_s"] * (r ** 2 + p["sig_target"] ** 2)
    return np.array(rets), np.array(f_mech), np.array(inv)


r_no, fm_no, _ = run_toy(with_ant=False)
r_yes, fm_yes, inv = run_toy(with_ant=True)

# the anticipator profits: inventory held into the next return, and it
# unwinds by the end (sells into the re-leveraging bid it forecast)
pnl = float(np.sum(inv[:-1] * r_yes[1:]))
assert pnl > 0, f"anticipator loses money on a perfectly predictable flow ({pnl:.2e})"
assert abs(inv[-1]) < 0.1 * np.abs(inv).max(), "inventory failed to unwind"

# and it DAMPS the flow's price impact: the price move per unit of arriving
# mechanical flow falls (without anticipators r = lam * f_mech exactly)
beta_no = float(np.sum(fm_no * r_no) / np.sum(fm_no ** 2))
beta_yes = float(np.sum(fm_yes * r_yes) / np.sum(fm_yes ** 2))
assert abs(beta_no - p["lam"]) < 1e-9
assert beta_yes < 0.9 * beta_no, \
    f"anticipator does not damp the mechanical flow's impact ({beta_yes:.3f} vs {beta_no:.3f})"
print(f"X30c: toy world — anticipator PnL {pnl:.2e} > 0, inventory unwound, "
      f"impact beta {beta_no:.2f} -> {beta_yes:.2f}")

print(f"\nGATE X30 PASSED ({time.time() - t0:.0f}s)")
