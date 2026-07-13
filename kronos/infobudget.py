"""KRONOS-BITS: the information budget of the market (DESIGN7.md).

Estimators:
  * KSG (Kraskov-Stogbauer-Grassberger, type 1) k-NN mutual information
    for continuous variables, applied to rank-transformed data (MI is
    invariant under monotone maps; ranking tames heavy tails).
  * Discrete plug-in MI with Miller-Madow bias correction, minus a
    shuffle null, for the direction channel.
Ceiling translations:
  * Gaussian channel:  SR_daily = sqrt(exp(2 I_nats) - 1)
  * Binary channel:    I_bits = 1 - H2(p)  =>  p  =>  SR_ann = (2p-1) sqrt(252)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.spatial import cKDTree
from scipy.special import digamma

LN2 = np.log(2.0)


# ---------------------------------------------------------------------------
# continuous MI: KSG type 1 on rank-transformed data
# ---------------------------------------------------------------------------

def _rank_gauss(x: np.ndarray) -> np.ndarray:
    """Map to standard-normal scores by rank (copula transform)."""
    from scipy.stats import norm
    r = pd.Series(x).rank(method="average").to_numpy()
    return norm.ppf((r - 0.375) / (len(x) + 0.25))


def ksg_mi(X: np.ndarray, Y: np.ndarray, k: int = 4,
           rank: bool = True, seed: int = 0) -> float:
    """I(X;Y) in NATS. X: (N,dx), Y: (N,dy)."""
    X = np.atleast_2d(X.T).T if X.ndim == 1 else X
    Y = np.atleast_2d(Y.T).T if Y.ndim == 1 else Y
    ok = np.isfinite(X).all(axis=1) & np.isfinite(Y).all(axis=1)
    X, Y = X[ok], Y[ok]
    N = len(X)
    if rank:
        X = np.column_stack([_rank_gauss(X[:, j]) for j in range(X.shape[1])])
        Y = np.column_stack([_rank_gauss(Y[:, j]) for j in range(Y.shape[1])])
    # tiny jitter breaks rank ties without touching the dependence
    rng = np.random.default_rng(seed)
    X = X + rng.normal(0, 1e-9, X.shape)
    Y = Y + rng.normal(0, 1e-9, Y.shape)
    Z = np.hstack([X, Y])
    tz = cKDTree(Z)
    # distance to k-th neighbour in max norm
    dists, _ = tz.query(Z, k=k + 1, p=np.inf)
    eps = dists[:, -1]
    tx, ty = cKDTree(X), cKDTree(Y)
    nx = np.array([len(tx.query_ball_point(X[i], eps[i] - 1e-12, p=np.inf)) - 1
                   for i in range(N)])
    ny = np.array([len(ty.query_ball_point(Y[i], eps[i] - 1e-12, p=np.inf)) - 1
                   for i in range(N)])
    mi = (digamma(k) + digamma(N)
          - np.mean(digamma(nx + 1) + digamma(ny + 1)))
    return float(max(mi, 0.0))


def ksg_mi_net(X: np.ndarray, Y: np.ndarray, k: int = 4,
               n_shuffle: int = 5, seed: int = 0) -> dict:
    """KSG MI minus the mean shuffled-Y MI (residual estimator bias)."""
    raw = ksg_mi(X, Y, k=k, seed=seed)
    rng = np.random.default_rng(seed + 1)
    Y2 = np.atleast_2d(Y.T).T if Y.ndim == 1 else Y
    nulls = []
    for i in range(n_shuffle):
        Yp = Y2[rng.permutation(len(Y2))]
        nulls.append(ksg_mi(X, Yp, k=k, seed=seed + 2 + i))
    null = float(np.mean(nulls))
    return {"mi_nats": max(raw - null, 0.0), "raw": raw, "null": null,
            "null_sd": float(np.std(nulls))}


# ---------------------------------------------------------------------------
# discrete MI: direction channel
# ---------------------------------------------------------------------------

def discrete_mi(x: np.ndarray, y: np.ndarray) -> float:
    """Plug-in MI (nats) with Miller-Madow bias correction."""
    xs, ys = pd.factorize(x)[0], pd.factorize(y)[0]
    ok = (xs >= 0) & (ys >= 0)
    xs, ys = xs[ok], ys[ok]
    N = len(xs)
    joint = pd.crosstab(xs, ys).to_numpy().astype(float)
    pj = joint / N
    px = pj.sum(axis=1, keepdims=True)
    py = pj.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = pj * np.log(pj / (px * py))
    mi = float(np.nansum(terms))
    # Miller-Madow: + (cells_joint - cells_x - cells_y + 1) / (2N)
    kx, ky = (px > 0).sum(), (py > 0).sum()
    kj = (pj > 0).sum()
    mi_mm = mi - (kj - kx - ky + 1) / (2 * N)
    return float(mi_mm)


def direction_bits(features: pd.DataFrame, future_sign: pd.Series,
                   n_shuffle: int = 200, seed: int = 0) -> dict:
    """I(sign ; features) in BITS/day, with a permutation null band."""
    df = pd.concat([features, future_sign.rename("_y")], axis=1).dropna()
    y = df["_y"].to_numpy()
    # composite discrete feature: cartesian product of the columns
    code = np.zeros(len(df), dtype=np.int64)
    mult = 1
    for c in features.columns:
        vals = pd.factorize(df[c])[0]
        code = code + vals * mult
        mult *= vals.max() + 1
    mi = discrete_mi(code, y) / LN2
    rng = np.random.default_rng(seed)
    nulls = np.array([discrete_mi(code, y[rng.permutation(len(y))]) / LN2
                      for _ in range(n_shuffle)])
    return {"bits": mi, "null_mean": float(nulls.mean()),
            "null_p95": float(np.percentile(nulls, 95)),
            "bits_net": float(max(mi - nulls.mean(), 0.0)),
            "significant": bool(mi > np.percentile(nulls, 95)),
            "n": len(df)}


# ---------------------------------------------------------------------------
# ceilings
# ---------------------------------------------------------------------------

def gaussian_sharpe_ceiling(mi_nats: float) -> float:
    """Annualized Sharpe ceiling of a Gaussian channel with I nats/day."""
    sr_d = np.sqrt(max(np.exp(2 * mi_nats) - 1, 0.0))
    return float(sr_d * np.sqrt(252))


def binary_sharpe_ceiling(bits: float) -> float:
    """Annualized Sharpe of a unit-vol sign bet with I = 1 - H2(p) bits."""
    bits = float(np.clip(bits, 0.0, 0.999))
    if bits <= 1e-12:
        return 0.0
    def f(p):
        h = -p * np.log2(p) - (1 - p) * np.log2(1 - p)
        return (1 - h) - bits
    p = brentq(f, 0.5 + 1e-9, 1 - 1e-9)
    return float((2 * p - 1) * np.sqrt(252))


def bits_consumed_by(sr_ann: float) -> float:
    """Bits/day a strategy's realized Sharpe implies it extracted."""
    sr_d = sr_ann / np.sqrt(252)
    return float(0.5 * np.log(1 + sr_d ** 2) / LN2)


# ---------------------------------------------------------------------------
# feature builders (all strictly causal)
# ---------------------------------------------------------------------------

def causal_features(r: pd.Series, gkvar: pd.Series, regime: pd.Series | None = None):
    """Discrete features known at close of t for predicting t+1."""
    lv = 0.5 * np.log(gkvar.rolling(5).mean())
    vol_terc = pd.Series(pd.qcut(lv.rank(pct=True), 3, labels=False),
                         index=lv.index)
    mom = np.sign(r.rolling(21).sum())
    feats = pd.DataFrame({
        "sign_t": np.sign(r),
        "mom21": mom,
        "vol_terc": vol_terc,
    })
    if regime is not None:
        feats["regime"] = regime.reindex(feats.index).ffill()
    return feats
