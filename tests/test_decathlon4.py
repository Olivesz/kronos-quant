"""Gate X34: DECATHLON-4 quote-skewing maker (DESIGN22).

(a) with quote_skew=0, simulate_abm is BYTE-IDENTICAL to the pre-DESIGN22
    simulator: X30a's flag-off pins AND X32a's anticipator-path pins must
    both be reproduced (the latter also certifies the _flow_forecast
    refactor changed no floats) — protecting X19's SPY-10/GBM-3 calibration
    and DECA2/3's published rows;
(b) the quote path is CAUSAL: tampering with future returns must not change
    the maker_quote_path prefix (truncation trick, X30b protocol);
(c) mechanism sanity on the X30c toy world (DESIGN22-amended: de-levered
    initial L, sn=0.0005 seeded ambient noise flow): at quote_skew=1.0 the
    correlation between the forecastable mechanical flow and the NEXT-period
    return collapses toward zero while the flow series itself is essentially
    unchanged — the leak is absorbed into the price LEVEL, not suppressed by
    killing the flow; at quote_skew=0 the toy matches the no-maker baseline
    bit-identically.

Fully synthetic, deterministic, no data dependencies.
"""
import hashlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from kronos.decathlon import (CONFIGS, CONFIGS2, DEFAULTS, _flow_forecast,
                              maker_quote_path, simulate_abm)

t0 = time.time()

# --- (a) quote_skew=0 => byte-identical to the pre-DESIGN22 simulator ------------
# X30a's flag-off pins, re-asserted with quote_skew passed explicitly.
PINNED_OFF = [
    ("FCVM",  7, 2000, "0882dd90e4264600d6fdb2767058577d0102171ef3a43bf91d62d5961ef2a2a4"),
    ("FV",    3, 2000, "a4b4823db5a11f95def5b2ffe82113707d1b099d7864cf4d6ceb2f1ba4a791fd"),
    ("FCVMH", 11, 1500, "6e47c2e4bf21f8dc988faf9aa682a696a168fd6e0a0eac4ffdb4e65e2d106571"),
    ("G",     5, 1000, "6e251afb01c1038a480b093caa1bae898c9e9f46440db4cf7c478b3411166161"),
    ("F",     2, 1200, "0ed356db2977c8acf43dd5160894f95a0317435664b572dc76a8cb85686914c2"),
]
for name, seed, T, want in PINNED_OFF:
    r = simulate_abm(T=T, seed=seed, quote_skew=0.0, **CONFIGS[name])
    got = hashlib.sha256(r.to_numpy().tobytes()).hexdigest()
    assert got == want, f"flag-off output drifted for {name} (seed {seed})"

# X32a's anticipator-path pins: the DECA2 worlds must also be untouched at
# quote_skew=0 (this exercises the shared _flow_forecast refactor).
PINNED_A = [
    ("FCVM+A", 7, 2000, "c21cf3ea0bc43c4df6f0465db26dcb6360ce0f6d4164b87e85e6b734e9c08db9"),
    ("FV+A",   3, 2000, "87f5ff45cc40b0869db6fb598244cb9807cb56a5057aaa7f8aa4eb6d3e85ac0a"),
    ("F+A",    2, 1200, "0bc35dd4e50e626f1352be5d122ba5e86fe920a58ee614ed2a2ccc4c6c83c4f5"),
]
for name, seed, T, want in PINNED_A:
    r = simulate_abm(T=T, seed=seed, quote_skew=0.0, **CONFIGS2[name])
    got = hashlib.sha256(r.to_numpy().tobytes()).hexdigest()
    assert got == want, f"DECA2 anticipator path drifted for {name}"
print(f"X34a: {len(PINNED_OFF)} flag-off + {len(PINNED_A)} anticipator configs "
      "byte-identical at quote_skew=0")

# the skew must be LIVE (a different world), deterministic, finite, sane
r_off = simulate_abm(T=2000, seed=7, **CONFIGS["FCVM"])
r_q1a = simulate_abm(T=2000, seed=7, quote_skew=1.0, **CONFIGS["FCVM"])
r_q1b = simulate_abm(T=2000, seed=7, quote_skew=1.0, **CONFIGS["FCVM"])
r_qh = simulate_abm(T=2000, seed=7, quote_skew=0.5, **CONFIGS["FCVM"])
assert not np.allclose(r_off, r_q1a), "quote_skew has no effect"
assert not np.allclose(r_q1a, r_qh), "skew strength has no effect"
assert np.array_equal(r_q1a.to_numpy(), r_q1b.to_numpy()), "not deterministic"
assert np.isfinite(r_q1a).all()
ann = r_q1a.std() * np.sqrt(252)
assert 0.02 < ann < 1.0, "quote-skewed world vol insane"
print(f"X34a: skew live and deterministic (FCVM+Q1.0 ann vol {ann:.1%})")

# --- (b) causality: the future must not reach the quote ---------------------------
rng = np.random.default_rng(0)
r_base = rng.normal(0.0, 0.01, 1500)
r_base[700:720] -= 0.03                     # a vol episode the maker re-quotes on
q_base = maker_quote_path(r_base)
assert np.array_equal(q_base, maker_quote_path(r_base)), "helper not deterministic"

CUT = 1000
for tamper_seed in (1, 2, 3):
    rt = np.random.default_rng(tamper_seed)
    r_tam = r_base.copy()
    r_tam[CUT:] = rt.permutation(r_tam[CUT:]) * rt.uniform(-3.0, 3.0)
    q_tam = maker_quote_path(r_tam)
    # q[t] may use r[:t] only => quotes 0..CUT (inclusive) must be identical
    assert np.array_equal(q_base[:CUT + 1], q_tam[:CUT + 1]), \
        "future returns changed the maker's past quotes — look-ahead"
    assert not np.array_equal(q_base[CUT + 1:], q_tam[CUT + 1:]), \
        "quote path ignores the data entirely"
# truncation form: the prefix of the series gives the prefix of the quotes
assert np.array_equal(maker_quote_path(r_base[:CUT]), q_base[:CUT])
print("X34b: causal — future tampering leaves the quote prefix unchanged "
      "(3 tampers + truncation)")

# --- (c) toy world: the leak is absorbed into the LEVEL, the flow survives --------
# X30c's deterministic world with the DESIGN22 amendment: the leverage state
# starts already shocked (L_prev = L(sigma_hat_0), removing the t=0
# initialization impulse so the measured object is the forecastable
# RE-LEVERAGING DRIFT — the E9 leak), plus a small seeded ambient noise flow
# sn=0.0005 (the "unforecastable surprise" the return should keep; without it
# the skewed toy's returns are identically zero and the correlation is
# undefined). Same seed both runs => same noise draws.
p = dict(DEFAULTS)
TOY_T = 150
SN = 0.0005


def run_toy(skew: float, with_maker: bool = True):
    rng_t = np.random.default_rng(4)
    sig2 = np.array([(3.0 * p["sig_target"]) ** 2])
    L_prev = np.minimum(p["Lmax"],
                        p["sig_target"] / np.maximum(np.sqrt(sig2), 1e-5))
    q_prev = skew * p["lam"] * _flow_forecast(sig2, p) if with_maker else 0.0
    rets, f_mech = [], []
    for _ in range(TOY_T):
        L = np.minimum(p["Lmax"],
                       p["sig_target"] / np.maximum(np.sqrt(sig2), 1e-5))
        fm = p["kV"] * float((L - L_prev).sum())
        L_prev = L
        D = fm + SN * rng_t.normal()
        r = p["lam"] * D
        if with_maker and skew:
            q = skew * p["lam"] * _flow_forecast(sig2, p)
            r += q - q_prev
            q_prev = q
        rets.append(r)
        f_mech.append(fm)
        # ambient activity pins the estimator's fixed point at the target
        sig2 = (1 - p["a_s"]) * sig2 + p["a_s"] * (r ** 2 + p["sig_target"] ** 2)
    return np.array(rets), np.array(f_mech)


def corr_next(f: np.ndarray, r: np.ndarray) -> float:
    """corr(forecastable flow at t, return at t+1) — the leak estimator."""
    return float(np.corrcoef(f[:-1], r[1:])[0, 1])


# quote_skew=0 must be bit-identical to a world with no maker at all
r0, f0 = run_toy(0.0)
r0n, f0n = run_toy(0.0, with_maker=False)
assert np.array_equal(r0, r0n) and np.array_equal(f0, f0n), \
    "quote_skew=0 toy differs from the no-maker baseline"
c0 = corr_next(f0, r0)
r1, f1 = run_toy(1.0)
c1 = corr_next(f1, r1)
assert c0 > 0.3, f"unskewed toy leak not substantial (corr {c0:.3f}) — no leak to close"
assert abs(c1) < 0.1, \
    f"full skew does not collapse the leak (corr {c0:.3f} -> {c1:.3f})"
# ...and NOT by killing the flow: same targeters, essentially the same flow
max_df = float(np.abs(f1 - f0).max())
peak_f = float(np.abs(f0).max())
assert max_df < 0.10 * peak_f, \
    f"skew altered the mechanical flow itself (max df {max_df:.2e} vs peak {peak_f:.2e})"
assert abs(f1.sum() - f0.sum()) < 0.05 * abs(f0.sum()), \
    "total re-leveraging changed — the flow was suppressed, not re-priced"
# the LEVEL carries what left the return: the skewed price path still moves
assert np.abs(np.cumsum(r1)).max() > 0.5 * SN * TOY_T ** 0.5, "price level frozen"
print(f"X34c: toy leak corr(f_t, r_t+1) {c0:+.3f} (skew 0) -> {c1:+.3f} (skew 1); "
      f"flow unchanged (max|df|/peak {max_df / peak_f:.1%}, "
      f"sum f {f0.sum():.5f} vs {f1.sum():.5f})")

print(f"\nGATE X34 PASSED ({time.time() - t0:.0f}s)")
