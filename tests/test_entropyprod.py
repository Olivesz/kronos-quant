"""Gate X18: EP estimator — zero on reversible worlds, positive on GJR."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from kronos.entropyprod import ep_with_null, ngram_ep, symbolize
from kronos.surge import simulate_gjr_world, simulate_reversible_world

rng = np.random.default_rng(101)
T = 6000

# --- size: stationary Gaussian AR(1) is exactly time-reversible -----------------
phi = 0.95
x = np.zeros(T)
for t in range(1, T):
    x[t] = phi * x[t - 1] + rng.normal() * np.sqrt(1 - phi ** 2)
r_ar = ep_with_null(np.diff(x), n=3, n_null=100)
print(f"Gaussian AR(1) increments: EP={r_ar['ep_bits']:.5f} "
      f"null95={r_ar['null_p95']:.5f} sig={r_ar['significant']}")
assert not r_ar["significant"], "Gaussian AR(1) must be reversible"

# --- size: reversible SV world's returns -----------------------------------------
r0, v0 = simulate_reversible_world(T, seed=2)
rr = ep_with_null(r0.to_numpy(), n=3, n_null=100)
print(f"reversible SV returns   : EP={rr['ep_bits']:.5f} "
      f"null95={rr['null_p95']:.5f} sig={rr['significant']}")
assert not rr["significant"], "reversible SV returns must show no arrow"

# --- power + calibration: cyclic Markov chain with KNOWN entropy production -------
# P violates detailed balance (0 -> 1 -> 2 -> 0 bias); closed-form EP exists.
P = np.array([[0.10, 0.80, 0.10],
              [0.10, 0.10, 0.80],
              [0.80, 0.10, 0.10]])
pi = np.full(3, 1 / 3)                       # uniform by symmetry
ep_true_nats = sum(pi[i] * P[i, j] * np.log(P[i, j] / P[j, i])
                   for i in range(3) for j in range(3))
ep_true_bits = ep_true_nats / np.log(2)
s = np.zeros(T, dtype=int)
for t in range(1, T):
    s[t] = rng.choice(3, p=P[s[t - 1]])
# n-gram KL grows ~ (n-1)*EP_step, so /n recovers ~ (n-1)/n of truth
from kronos.entropyprod import ngram_ep
ep_est = ngram_ep(s, n=3) * 3 / 2            # slope correction for Markov
# null via coin-flip block reversal (the corrected surrogate)
rng2 = np.random.default_rng(7)
nulls = []
for i in range(100):
    out = s.copy()
    for a in range(0, T, 126):
        if rng2.random() < 0.5:
            out[a:a + 126] = out[a:a + 126][::-1]
    nulls.append(ngram_ep(out, n=3) * 3 / 2)
print(f"cyclic Markov chain     : EP_est={ep_est:.3f} bits (true {ep_true_bits:.3f}) "
      f"null95={np.percentile(nulls, 95):.4f}")
assert ep_est > np.percentile(nulls, 95) * 3, "EP must detect broken detailed balance"
assert 0.5 * ep_true_bits < ep_est < 1.3 * ep_true_bits, "EP calibration off"

# --- power: GJR world — TRUE vol path is irreversible (fast up, slow decay) -------
rg, vg = simulate_gjr_world(T, seed=1)
dlv_true = np.diff(0.5 * np.log(vg.attrs["true_var"]))
rgep = ep_with_null(dlv_true, n=3, n_null=100)
print(f"GJR d(log vol), true    : EP={rgep['ep_bits']:.5f} "
      f"null95={rgep['null_p95']:.5f} sig={rgep['significant']}")
assert rgep["significant"], "GJR true vol path must show an arrow"

# informational: the noisy daily proxy hides the arrow (known power limit —
# real-data vol-path EP must use aggregated/weekly innovations)
dlv_proxy = (0.5 * np.log(vg)).rolling(5).mean().diff().dropna().to_numpy()
rgp = ep_with_null(dlv_proxy, n=3, n_null=50)
print(f"GJR d(log vol), proxy   : EP={rgp['ep_bits']:.5f} sig={rgp['significant']} "
      f"(noise hides the arrow — use weekly innovations on real data)")

print("\nGATE X18 PASSED")
