"""Black-Litterman blending of the HRP risk backbone with alpha-signal views.

Prior: implied equilibrium returns reverse-optimized from the HRP weights.
Views: one absolute view per asset, Q_i = pi_i + lambda * z_i * sigma_i,
with view uncertainty Omega tightened by signal conviction (Idzorek-flavored).
Posterior tilts the HRP weights multiplicatively — stability of HRP,
information of BL, no fragile optimizer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def bl_posterior(cov: pd.DataFrame, w_prior: pd.Series, signal_z: pd.Series, cfg) -> dict:
    Sigma = cov.to_numpy()
    w0 = w_prior.reindex(cov.index).fillna(0.0).to_numpy()
    z = signal_z.reindex(cov.index).fillna(0.0).to_numpy()
    sigma = np.sqrt(np.diag(Sigma))

    pi = cfg.bl_delta * Sigma @ w0                      # equilibrium prior
    Q = pi + cfg.bl_view_lambda * z * sigma             # signal views
    tau = cfg.bl_tau
    conviction = np.maximum(np.abs(z), 0.1)
    omega_diag = tau * np.diag(Sigma) / conviction      # confident => tight
    # posterior: mu = pi + tau*Sigma (tau*Sigma + Omega)^-1 (Q - pi)  [P = I]
    M = tau * Sigma + np.diag(omega_diag)
    adj = tau * Sigma @ np.linalg.solve(M, Q - pi)
    mu = pi + adj
    return {"pi": pd.Series(pi, index=cov.index),
            "mu": pd.Series(mu, index=cov.index),
            "Q": pd.Series(Q, index=cov.index)}


def tilt_weights(w_hrp: pd.Series, mu: pd.Series, pi: pd.Series, cfg) -> pd.Series:
    """Multiplicative tilt of the HRP backbone by the BL excess view."""
    edge = (mu - pi)
    sd = edge.std()
    if not np.isfinite(sd) or sd < 1e-14:
        tilted = w_hrp.copy()
    else:
        tilted = w_hrp * (1.0 + cfg.bl_tilt_kappa * (edge - edge.mean()) / sd)
    tilted = tilted.clip(lower=0.0)
    if tilted.sum() <= 0:
        tilted = w_hrp.copy()
    tilted /= tilted.sum()
    # iterative cap-and-redistribute for the max weight constraint
    for _ in range(20):
        over = tilted > cfg.max_weight
        if not over.any():
            break
        excess = (tilted[over] - cfg.max_weight).sum()
        tilted[over] = cfg.max_weight
        under = ~over
        room = (cfg.max_weight - tilted[under]).clip(lower=0)
        if room.sum() <= 1e-12:
            tilted /= tilted.sum()
            break
        tilted[under] += excess * room / room.sum()
    return tilted / tilted.sum()


def construct_portfolio(cov: pd.DataFrame, signal_z: pd.Series, cfg) -> dict:
    from kronos.hrp import hrp_weights
    w_hrp = hrp_weights(cov)
    post = bl_posterior(cov, w_hrp, signal_z, cfg)
    w = tilt_weights(w_hrp, post["mu"], post["pi"], cfg)
    return {"weights": w, "hrp": w_hrp, "mu": post["mu"], "pi": post["pi"]}
