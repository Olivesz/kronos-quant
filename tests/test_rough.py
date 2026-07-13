"""Gate X5: Hurst estimator recovers known H on exact fGn paths."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from kronos.rough import simulate_fgn, simulate_rough_logvol, scaling_moments

# fGn simulator sanity: variance 1, lag-1 autocorr matches the closed form
# rho(1) = 0.5*(2^(2H) - 2)
for H in (0.1, 0.45, 0.7):
    x = simulate_fgn(100_000, H, seed=3)
    ac1 = np.corrcoef(x[:-1], x[1:])[0, 1]
    rho_theory = 0.5 * (2 ** (2 * H) - 2)
    print(f"fGn H={H}: var={x.var():.3f}, lag-1 ac={ac1:+.3f} (theory {rho_theory:+.3f})")
    assert abs(x.var() - 1) < 0.05
    assert abs(ac1 - rho_theory) < 0.02

# H recovery from fBm log-vol paths of realistic length (T=4000)
deltas = np.unique(np.round(np.exp(np.linspace(0, np.log(50), 16))).astype(int))
print("\ntrue_H  est_H (3 seeds)")
for H_true in (0.05, 0.10, 0.30, 0.45):
    ests = []
    for seed in (1, 2, 3):
        lv = simulate_rough_logvol(4000, H_true, nu=0.3, seed=seed)
        ests.append(scaling_moments(lv, deltas)["H"])
    err = abs(np.mean(ests) - H_true)
    print(f"{H_true:5.2f}  {np.mean(ests):5.3f} ± {np.std(ests):.3f}  (|bias| {err:.3f})")
    assert err < 0.05, f"H recovery failed for H={H_true}"

# measurement-noise direction check: additive noise on log-vol biases H DOWN at
# short lags — we must know the sign of this artifact before reading real data
lv = simulate_rough_logvol(4000, 0.30, nu=0.3, seed=1)
rng = np.random.default_rng(9)
lv_noisy = lv + rng.normal(0, 0.25, len(lv))
H_clean = scaling_moments(lv, deltas)["H"]
H_noisy = scaling_moments(lv_noisy, deltas)["H"]
print(f"\nnoise artifact: H_clean={H_clean:.3f} -> H_noisy={H_noisy:.3f} (must drop)")
assert H_noisy < H_clean, "noise should bias H downward"

# monofractality residual small on true fBm
res = scaling_moments(lv, deltas)["monofractal_resid"]
print(f"monofractal residual: {res:.4f}")
assert res < 0.05

print("\nGATE X5 PASSED")
