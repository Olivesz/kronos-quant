"""Gate X6: MP edge finds the planted number of factors; denoising helps."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from kronos.rmt import corr_from_cov, denoise_corr, min_var_weights

rng = np.random.default_rng(31)

# planted k-factor model: N=48, T=252 (the real-world shape), k=3 factors
N, T, k_true = 48, 252, 3
betas = rng.normal(0, 1, (N, k_true)) * np.array([1.2, 0.6, 0.4])
F = rng.normal(0, 0.01, (T, k_true))
eps = rng.normal(0, 0.012, (T, N))
R = F @ betas.T + eps
true_cov = (betas * np.array([1.2, 0.6, 0.4]) ** 0) @ np.diag([0.01**2]*k_true) @ betas.T  # not used directly

S = np.cov(R.T)
corr = corr_from_cov(S)
dn, info = denoise_corr(corr, T)
print(f"planted factors: {k_true}, detected: {info['n_factors']} (edge {info['edge']:.2f})")
assert abs(info["n_factors"] - k_true) <= 1, "MP edge missed the factor count badly"

# denoised correlation must stay valid
eig = np.linalg.eigvalsh(dn)
assert eig.min() > -1e-10 and np.allclose(np.diag(dn), 1)

# min-var with denoised cov should beat sample cov out of sample
F2 = rng.normal(0, 0.01, (5000, k_true))
eps2 = rng.normal(0, 0.012, (5000, N))
R_oos = F2 @ betas.T + eps2
vol = np.sqrt(np.diag(S))
cov_dn = dn * np.outer(vol, vol)
w_samp = min_var_weights(S)
w_dn = min_var_weights(cov_dn)
vol_samp = (R_oos @ w_samp).std() * np.sqrt(252)
vol_dn = (R_oos @ w_dn).std() * np.sqrt(252)
print(f"OOS min-var vol: sample {vol_samp:.2%} vs denoised {vol_dn:.2%}")
assert vol_dn < vol_samp, "denoising should reduce OOS min-var vol"

# pure-noise sanity: detected factors should be ~0
Rn = rng.normal(0, 0.01, (T, N))
_, info_n = denoise_corr(corr_from_cov(np.cov(Rn.T)), T)
print(f"pure noise detected factors: {info_n['n_factors']}")
assert info_n["n_factors"] <= 1

print("\nGATE X6 PASSED")
