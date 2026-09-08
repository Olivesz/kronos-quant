"""KRONOS-DECATHLON-R2 estimators (DESIGN26): the referee-panel follow-up.

Adds exactly one estimator to the DESIGN25 machinery and the drivers that
compose it with the archived worlds:

  * AR(p) whitening — one joint OLS of the demeaned return on its lags
    1..p (DESIGN26 W1 pin); ``arp_whiten(r, 1)`` reproduces
    ``ar1_whiten(r)`` to numerical identity (gate X37a). Everything else
    (the E9 block, permutation criterion, seed conventions) is imported
    unchanged from kronos.robustness so W1/W2/W3 measure the same
    statistic R2 measured.

Nothing here touches kronos/decathlon.py's battery or simulator paths.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# AR(p) whitening — removes the linear channel through lag p
# ---------------------------------------------------------------------------

def arp_whiten(returns: pd.Series, p: int) -> tuple[np.ndarray, pd.Series]:
    """OLS AR(p) residuals: e_t = xc_t - sum_{j=1..p} phi_j xc_{t-j}.

    One joint least-squares fit on the demeaned series (xc = r - rbar),
    residuals indexed from the (p+1)-th observation — the DESIGN26 W1
    amendment's pin. For p = 1 the normal equations reduce to
    ``ar1_whiten``'s ratio formula, asserted to 1e-10 by gate X37a."""
    x = returns.dropna().to_numpy(dtype=float)
    xc = x - x.mean()
    n = len(xc)
    X = np.column_stack([xc[p - j - 1:n - j - 1] for j in range(p)])
    y = xc[p:]
    phi, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ phi
    return phi, pd.Series(e, index=returns.dropna().index[p:],
                          name=f"ar{p}_whitened")


# ---------------------------------------------------------------------------
# planted worlds for gate X37 (ground truth by construction)
# ---------------------------------------------------------------------------

def linear_multilag_world(seed: int, T: int = 6000, phi: float = -0.45,
                          lags: tuple[int, ...] = (2, 3, 4)) -> pd.Series:
    """A purely LINEAR multi-lag world: x_t = (phi/len(lags)) * sum of the
    named lags + Gaussian noise. Carries sign information that a lag-1
    filter provably cannot remove and an AR(p >= max(lags)) filter can —
    the X37c size/power construction."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0, 0.01, T)
    x = np.zeros(T)
    w = phi / len(lags)
    for t in range(max(lags), T):
        x[t] = w * sum(x[t - L] for L in lags) + eps[t]
    return pd.Series(x, index=pd.bdate_range("2002-01-01", periods=T))
