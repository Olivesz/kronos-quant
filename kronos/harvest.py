"""KRONOS-HARVEST: is the monthly direction channel fully harvested? (DESIGN19)

The harvest gap dI = I(F; s21) - I(S; s21): full causal feature set vs the
production market-state (the filtered regime label). Reuses the X17-gated
discrete-MI machinery (Miller-Madow + permutation nulls); the gap's CI comes
from a stationary block bootstrap; gate X31 proves convict/exonerate against
enumerated ground truth.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kronos.infobudget import LN2, discrete_mi


def _encode(df: pd.DataFrame) -> np.ndarray:
    """Cartesian-product code of the columns (same scheme as direction_bits)."""
    code = np.zeros(len(df), dtype=np.int64)
    mult = 1
    for c in df.columns:
        vals = pd.factorize(df[c])[0]
        code = code + vals * mult
        mult *= vals.max() + 1
    return code


def _net_mi_bits(code: np.ndarray, y: np.ndarray, n_shuffle: int,
                 rng: np.random.Generator) -> float:
    mi = discrete_mi(code, y) / LN2
    null = np.mean([discrete_mi(code, y[rng.permutation(len(y))]) / LN2
                    for _ in range(n_shuffle)])
    return float(mi - null)


def harvest_gap(features: pd.DataFrame, harvested_cols: list[str],
                future_sign: pd.Series, n_boot: int = 300, block: int = 63,
                n_shuffle: int = 60, seed: int = 0) -> dict:
    """dI = I(F; s) - I(S; s) with block-bootstrap CI and a gap shuffle null.

    Both MIs are permutation-null debiased per draw, so the composite-code
    cardinality difference between F and S cannot fake a gap.
    """
    df = pd.concat([features, future_sign.rename("_y")], axis=1).dropna()
    y = df["_y"].to_numpy()
    F = df[features.columns]
    S = df[harvested_cols]
    T = len(df)
    rng = np.random.default_rng(seed)

    code_F, code_S = _encode(F), _encode(S)
    gap0 = _net_mi_bits(code_F, y, n_shuffle, rng) \
        - _net_mi_bits(code_S, y, n_shuffle, rng)

    # stationary block bootstrap of the JOINT (features, target) series
    gaps = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, T, int(np.ceil(T / block)))
        idx = np.concatenate([(s + np.arange(block)) % T for s in starts])[:T]
        gaps[b] = _net_mi_bits(code_F[idx], y[idx], n_shuffle, rng) \
            - _net_mi_bits(code_S[idx], y[idx], n_shuffle, rng)

    # shuffle null for the gap itself: destroy all feature-target dependence
    null_gaps = np.empty(60)
    for b in range(60):
        yp = y[rng.permutation(T)]
        null_gaps[b] = _net_mi_bits(code_F, yp, n_shuffle, rng) \
            - _net_mi_bits(code_S, yp, n_shuffle, rng)

    ci = [float(np.percentile(gaps, 2.5)), float(np.percentile(gaps, 97.5))]
    null_p95 = float(np.percentile(null_gaps, 95))
    return {
        "gap_bits": float(gap0), "ci": ci, "null_p95": null_p95,
        "significant": bool(ci[0] > 0 and gap0 > null_p95),
        "mi_full_net": _net_mi_bits(code_F, y, n_shuffle, rng),
        "mi_harvested_net": _net_mi_bits(code_S, y, n_shuffle, rng),
        "n": T,
    }


def drop_one(features: pd.DataFrame, harvested_cols: list[str],
             future_sign: pd.Series, seed: int = 0) -> dict:
    """Attribution: gap when each non-harvested feature is removed from F."""
    out = {}
    extras = [c for c in features.columns if c not in harvested_cols]
    for c in extras:
        cols = [k for k in features.columns if k != c]
        g = harvest_gap(features[cols], harvested_cols, future_sign,
                        n_boot=80, seed=seed)
        out[c] = round(g["gap_bits"], 4)
    return out


# ---------------------------------------------------------------------------
# synthetic worlds with enumerable ground truth (gate X31)
# ---------------------------------------------------------------------------

def simulate_world(T: int, unharvested: bool, seed: int = 0,
                   p_edge: float = 0.12) -> tuple[pd.DataFrame, pd.Series, float]:
    """3-state Markov regime drives P(up); optionally an extra binary feature
    X also shifts P(up). Returns (features, sign, TRUE harvest gap in bits),
    the truth computed by exact enumeration over the discrete joint."""
    rng = np.random.default_rng(seed)
    P = np.full((3, 3), 0.02)
    np.fill_diagonal(P, 0.96)
    S = np.zeros(T, dtype=int)
    for t in range(1, T):
        S[t] = rng.choice(3, p=P[S[t - 1]])
    X = (rng.random(T) < 0.5).astype(int)
    base = np.array([0.5 - p_edge, 0.5, 0.5 + p_edge])
    p_up = base[S] + (p_edge * (2 * X - 1) if unharvested else 0.0)
    p_up = np.clip(p_up, 0.05, 0.95)
    y = (rng.random(T) < p_up).astype(int)

    # exact MI by enumeration (stationary S-distribution ~ uniform by symmetry)
    def H(p):
        p = np.clip(p, 1e-12, 1 - 1e-12)
        return -(p * np.log(p) + (1 - p) * np.log(1 - p))
    pS = np.array([(S == k).mean() for k in range(3)])
    if unharvested:
        p_joint = np.clip(base[:, None] + p_edge * np.array([-1, 1])[None, :],
                          0.05, 0.95)                      # (S, X)
        w = pS[:, None] * 0.5
        H_y_given_FX = float((w * H(p_joint)).sum())
        p_y_given_S = (p_joint * 0.5).sum(axis=1)
        H_y_given_S = float((pS * H(p_y_given_S)).sum())
    else:
        p_clip = np.clip(base, 0.05, 0.95)
        H_y_given_FX = float((pS * H(p_clip)).sum())
        H_y_given_S = H_y_given_FX
    true_gap = (H_y_given_S - H_y_given_FX) / LN2         # bits

    junk = (rng.random(T) < 0.5).astype(int)               # harvested-world junk
    feats = pd.DataFrame({"regime": S, "extra": X, "junk": junk})
    idx = pd.bdate_range("2012-01-02", periods=T)
    feats.index = idx
    return feats, pd.Series(y, index=idx), true_gap
