"""KRONOS-CONSTANTS: which market laws are constant vs drifting? (DESIGN11)

For each prior-study quantity, estimate it in non-overlapping era windows,
then classify CONSTANT / DRIFTING / REGIME-VARYING via:
  * a variance-ratio test (cross-era dispersion vs within-era sampling noise),
  * a bootstrapped linear time-trend.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kronos.rough import estimate_hurst
from kronos.hawkes import fit_hawkes, raw_and_deformed_events, recovery_curve, debias


ERA_EDGES = ["2010-01-01", "2013-04-01", "2016-07-01", "2019-10-01",
             "2023-01-01", "2026-07-01"]   # 5 non-overlapping ~3.25y windows


# ---------------------------------------------------------------------------
# per-window, per-asset quantities
# ---------------------------------------------------------------------------

def _leverage(r: np.ndarray, gkv: np.ndarray) -> float:
    out = []
    for tau in range(1, 11):
        x, y = r[:-tau], gkv[tau:]
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() > 30:
            out.append(np.corrcoef(x[ok], y[ok])[0, 1])
    return float(np.mean(out)) if out else np.nan


def _pooled_simple(cl, gkw, day_idx):
    """Median-across-asset of {kurt, kurt_def, leverage, H} on a (possibly
    bootstrap-resampled) set of day positions."""
    K, KD, LV, HH = [], [], [], []
    for c in cl.columns:
        s = cl[c]
        r_full = np.log(s / s.shift(1)).to_numpy()
        g_full = gkw[c].to_numpy()
        gsm = pd.Series(g_full).rolling(5).mean().to_numpy()   # aligned, pre-resample
        r = r_full[day_idx]; g = g_full[day_idx]; gs = gsm[day_idx]
        ok = np.isfinite(r) & np.isfinite(g)
        r, g, gs = r[ok], g[ok], gs[ok]
        if len(r) < 100:
            continue
        K.append(pd.Series(r).kurtosis() + 3.0)
        z = r / np.sqrt(gs)
        z = z[np.isfinite(z)]
        KD.append(pd.Series(z).kurtosis() + 3.0)
        LV.append(_leverage(r, g))
        try:
            HH.append(estimate_hurst(pd.Series(g[g > 0]))["H"])
        except Exception:
            pass
    return {"kurt": np.nanmedian(K), "kurt_def": np.nanmedian(KD),
            "leverage": np.nanmedian(LV), "H": np.nanmedian(HH)}


def window_quantities(close: pd.DataFrame, gk: pd.DataFrame, lo: str, hi: str,
                      curve: dict, n_boot: int = 40) -> dict:
    """Per-window pooled estimates + TIME-block-bootstrap sampling SDs."""
    cl = close.loc[lo:hi]
    gkw = gk.loc[lo:hi]
    T = len(cl)
    base = _pooled_simple(cl, gkw, np.arange(T))
    # time-block bootstrap for the simple quantities' sampling SDs
    rng = np.random.default_rng(1)
    block = 63
    accum = {k: [] for k in base}
    for _ in range(n_boot):
        starts = rng.integers(0, T, int(np.ceil(T / block)))
        idx = np.concatenate([(s + np.arange(block)) % T for s in starts])[:T]
        b = _pooled_simple(cl, gkw, idx)
        for k in accum:
            accum[k].append(b[k])
    out = {k: (float(base[k]), float(np.nanstd(accum[k]))) for k in base}

    # Hawkes branching ratios: per-asset, conservative cross-asset-std SD
    nr, nd = [], []
    for c in cl.columns:
        s = cl[c].dropna()
        if len(s) < 300:
            continue
        ev = raw_and_deformed_events(s, gkw[c], q=0.95)
        if len(ev["raw"]) > 25:
            nr.append(debias(fit_hawkes(ev["raw"], ev["T"])["n"], curve))
        if len(ev["deformed"]) > 25:
            nd.append(debias(fit_hawkes(ev["deformed"], ev["T"])["n"], curve))
    out["n_raw"] = (float(np.nanmedian(nr)), float(np.nanstd(nr) / np.sqrt(3)))
    out["n_def"] = (float(np.nanmedian(nd)), float(np.nanstd(nd) / np.sqrt(3)))

    # cross-sectional clock commonality + block-bootstrap SD
    lv = 0.5 * np.log(gkw.where(gkw > 0)).rolling(10).mean().dropna(how="all")
    def eig1(frame):
        corr = frame.corr().to_numpy()
        keep = np.isfinite(corr).all(axis=1)
        corr = corr[keep][:, keep]
        return float(np.linalg.eigvalsh(corr)[-1] / len(corr)) if len(corr) else np.nan
    boots = []
    Tl = len(lv)
    for _ in range(n_boot):
        starts = rng.integers(0, Tl, int(np.ceil(Tl / block)))
        idx = np.concatenate([(s + np.arange(block)) % Tl for s in starts])[:Tl]
        boots.append(eig1(lv.iloc[idx]))
    out["commonality"] = (eig1(lv), float(np.nanstd(boots)))
    return out


# ---------------------------------------------------------------------------
# stability test
# ---------------------------------------------------------------------------

def variance_ratio_test(window_means: np.ndarray, window_sds: np.ndarray,
                        n_null: int = 5000, seed: int = 0) -> dict:
    """VR = cross-window dispersion / mean within-window sampling variance.
    VR~1 => constant; VR>>1 => genuine drift. Bootstrap p under the
    constant-true-value null."""
    m = window_means
    s = window_sds
    ok = np.isfinite(m) & np.isfinite(s) & (s > 0)
    m, s = m[ok], s[ok]
    if len(m) < 3:
        return {"VR": np.nan, "p": np.nan}
    vr = np.var(m, ddof=1) / np.mean(s ** 2)
    rng = np.random.default_rng(seed)
    null = np.empty(n_null)
    mu = m.mean()
    for i in range(n_null):
        sim = mu + rng.normal(0, 1, len(m)) * s
        null[i] = np.var(sim, ddof=1) / np.mean(s ** 2)
    return {"VR": float(vr), "p": float((null >= vr).mean())}


def trend_test(t_centers: np.ndarray, means: np.ndarray, sds: np.ndarray,
               n_boot: int = 5000, seed: int = 0) -> dict:
    """Bootstrapped OLS slope of estimate vs era-center-year."""
    ok = np.isfinite(means) & np.isfinite(sds)
    t, m, s = t_centers[ok], means[ok], sds[ok]
    if len(t) < 3:
        return {"slope": np.nan, "ci": [np.nan, np.nan]}
    A = np.column_stack([np.ones(len(t)), t - t.mean()])
    slope0 = np.linalg.lstsq(A, m, rcond=None)[0][1]
    rng = np.random.default_rng(seed)
    slopes = np.empty(n_boot)
    for i in range(n_boot):
        mb = m + rng.normal(0, 1, len(m)) * s
        slopes[i] = np.linalg.lstsq(A, mb, rcond=None)[0][1]
    return {"slope": float(slope0),
            "ci": [float(np.percentile(slopes, 2.5)),
                   float(np.percentile(slopes, 97.5))]}


def classify(vr: dict, trend: dict, span_years: float) -> str:
    drift_total = trend["slope"] * span_years if np.isfinite(trend["slope"]) else 0
    trend_sig = (np.isfinite(trend["ci"][0]) and
                 (trend["ci"][0] > 0 or trend["ci"][1] < 0))
    vr_sig = np.isfinite(vr["p"]) and vr["p"] < 0.10
    if trend_sig:
        return "DRIFTING"
    if vr_sig:
        return "REGIME-VARYING"
    return "CONSTANT"
