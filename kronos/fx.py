"""KRONOS-FX: the third vertex of the microstructure triangle. (DESIGN17)

Atlas IX.1c. TRANSFER showed the laws hold in every equity market; CRYPTO
showed the leverage effect inverts (+0.03) where the equity microstructure is
absent. FX is the third point: institutional dealer flow but no financial
leverage of the underlying AND no retail-FOMO dynamic — so the pre-registered
prediction is leverage ~ 0, making the effect a monotone function of
microstructure (equity negative, FX zero, crypto positive). Reuses the
CONSTANTS/TRANSFER 7-law battery; adds the three-class leverage contrast.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from kronos.constants import _leverage
from kronos.data import CACHE_DIR, fetch_yahoo_ohlc, generate_synthetic
from kronos.volest import gk_variance

# 13 liquid crosses (12 majors + USDMXN as the declared EM stress case), each
# in its NATIVE Yahoo quote direction (see DESIGN17 — under the zero-leverage
# null the quote direction is irrelevant, which is itself part of the claim).
FX_UNIVERSE = [
    "EURUSD=X", "JPY=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X", "CAD=X",
    "CHF=X", "EURJPY=X", "EURGBP=X", "GBPJPY=X", "EURCHF=X", "AUDJPY=X",
    "MXN=X",
]
FX_START = "2010-01-01"

# Tail-preserving clip (DESIGN17): the largest GENUINE one-day FX move since
# 2010 is the SNB floor removal (2015-01-15, EURCHF/USDCHF ~ -15..-19%), which
# must survive cleaning; Yahoo FX bad ticks are inversion/decimal glitches at
# 100%+ scale. 25% keeps every real event with margin and kills the glitches.
_CLIP = 0.25
_MIN_COVERAGE = 0.90
_MAX_FFILL = 3

# Garman-Klass validity guard (DESIGN17, pre-registered before lock-in):
# Yahoo FX daily bars sometimes carry FAKE ranges (high==low, or the range
# pinned exactly to |close-open|). GK is only licensed on pairs where >95% of
# days have a real range; the study aborts below 8 surviving pairs rather
# than silently degrading to a different estimator.
_MIN_REAL_RANGE = 0.95
_MIN_PAIRS = 8


def real_range_audit(ohlc: dict) -> dict[str, float]:
    """Fraction of days with a REAL intraday range, per pair, on the raw bars:
    high > low strictly AND (high - low) > |close - open| * 1.0001."""
    o, h, l, c = (ohlc[f] for f in ("open", "high", "low", "close"))
    out = {}
    for p in c.columns:
        ok = o[p].notna() & h[p].notna() & l[p].notna() & c[p].notna()
        if ok.sum() == 0:
            out[p] = 0.0
            continue
        oo, hh, ll, cc = o[p][ok], h[p][ok], l[p][ok], c[p][ok]
        real = (hh > ll) & ((hh - ll) > (cc - oo).abs() * 1.0001)
        out[p] = float(real.mean())
    return out


def _clean_fx(px: pd.DataFrame) -> pd.DataFrame:
    cov = px.notna().mean()
    px = px.loc[:, cov >= _MIN_COVERAGE]
    px = px.ffill(limit=_MAX_FFILL)
    px = px.dropna(axis=0, how="any")
    rets = px.pct_change()
    bad = rets.abs() > _CLIP           # data errors only — real FX tails survive
    if bad.to_numpy().any():
        rets = rets.where(~bad, 0.0).fillna(0.0)
        px = (1 + rets).cumprod().mul(px.iloc[0], axis=1)
    return px


def load_fx(start: str = FX_START, end: str = "2026-06-05",
            seed: int = 42) -> dict:
    """Cached FX OHLC + Garman-Klass variance panels, behind the range guard.

    Returns {"close", "gk", "source", "range_audit", "dropped"}. Falls back to
    a seeded synthetic market when Yahoo is unreachable so the study still
    runs offline (the JSON records which source was used). Raises RuntimeError
    if fewer than 8 pairs carry a real intraday range on >95% of days.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    paths = {f: os.path.join(CACHE_DIR, f"fx_{f}_{start}_{end}.csv")
             for f in ("open", "high", "low", "close")}

    if all(os.path.exists(p) for p in paths.values()):
        ohlc = {f: pd.read_csv(p, index_col=0, parse_dates=True)
                for f, p in paths.items()}
        source = "yahoo"
    else:
        ohlc = fetch_yahoo_ohlc(FX_UNIVERSE, start, end)
        if ohlc is not None:
            for f, p in paths.items():
                ohlc[f].to_csv(p)
            source = "yahoo"
        else:
            c = generate_synthetic(FX_UNIVERSE, start, end, seed + 13)
            # rescale to FX-like daily vol (~0.6%) around 1.0
            r = np.log(c / c.shift(1)) * 0.45
            c = np.exp(r.fillna(0.0).cumsum())
            rng = np.random.default_rng(seed + 1)
            o = c.shift(1) * np.exp(rng.normal(0, 0.001, c.shape))
            span = np.abs(rng.normal(0, 0.004, c.shape)) + 0.001
            ohlc = {"open": o, "close": c,
                    "high": np.maximum(o, c) * (1 + span / 2),
                    "low": np.minimum(o, c) * (1 - span / 2)}
            source = "synthetic"

    # ---- runtime GK-validity guard (pre-registered in DESIGN17) ----------
    audit = real_range_audit(ohlc)
    keep = [p for p, f in audit.items() if f > _MIN_REAL_RANGE]
    dropped = {p: round(f, 4) for p, f in audit.items() if p not in keep}
    if len(keep) < _MIN_PAIRS:
        raise RuntimeError(
            f"FX data quality failure: only {len(keep)} pairs have a real "
            f"intraday range on >{_MIN_REAL_RANGE:.0%} of days "
            f"(need >= {_MIN_PAIRS}). Garman-Klass is not licensed on this "
            f"data; refusing to degrade to close-to-close. Audit: "
            + ", ".join(f"{p}={f:.2%}" for p, f in sorted(audit.items())))
    ohlc = {f: df[keep] for f, df in ohlc.items()}

    close = _clean_fx(ohlc["close"])
    cols, idx = close.columns, close.index
    o, h, l = (ohlc[f].reindex(index=idx, columns=cols).ffill(limit=_MAX_FFILL)
               for f in ("open", "high", "low"))
    gk = gk_variance(o, h, l, close)
    return {"close": close, "gk": gk, "source": source,
            "range_audit": {p: round(f, 4) for p, f in audit.items()},
            "dropped": dropped}


def per_pair_leverage(close: pd.DataFrame, gk: pd.DataFrame) -> dict:
    """Leverage effect per pair, in its native quote direction: mean
    corr(r_{t-tau}, gkvar_t), tau=1..10. Negative = equity-style; positive =
    crypto-style; the F2 prediction is a symmetric scatter around zero."""
    out = {}
    for c in close.columns:
        r = np.log(close[c] / close[c].shift(1)).to_numpy()
        g = gk[c].to_numpy()
        out[c] = float(_leverage(r, g))
    return out


def fx_contrast(batteries: dict[str, dict], equity_names: list[str],
                fx_name: str = "fx", crypto_name: str = "crypto") -> dict:
    """The three-class leverage contrast: equity cohort vs FX vs crypto.

    Implements DESIGN17's F2 tests exactly as pre-registered: FX must be
    indistinguishable from 0 (|z| < 2), above the equity cohort (one-sided
    z > 1.645) and below crypto (one-sided z > 1.645).
    """
    eq = np.array([batteries[n]["leverage"][0] for n in equity_names])
    eq_mean, eq_spread = float(eq.mean()), float(eq.std(ddof=1))
    fl, fsd = batteries[fx_name]["leverage"]
    cl, csd = batteries[crypto_name]["leverage"]
    z_zero = fl / max(fsd, 1e-12)
    z_vs_eq = (fl - eq_mean) / float(np.sqrt(fsd ** 2 + eq_spread ** 2 + 1e-12))
    z_vs_crypto = (cl - fl) / float(np.sqrt(fsd ** 2 + csd ** 2 + 1e-12))
    monotone = bool(eq_mean < fl < cl)

    if abs(z_zero) < 2 and z_vs_eq > 1.645 and z_vs_crypto > 1.645:
        verdict = "ZERO-MIDPOINT"      # the pre-registered prediction
    elif z_zero <= -2:
        verdict = "EQUITY-STYLE"       # kill: negative and significant
    elif z_zero >= 2:
        verdict = "CRYPTO-STYLE"       # kill: positive and significant
    elif z_vs_eq <= 1.645:
        verdict = "SAME-AS-EQUITIES"   # kill: not separable from equities
    else:
        verdict = "SAME-AS-CRYPTO"     # ~0 but not separable from crypto
    return {
        "fx_leverage": round(fl, 4), "fx_sd": round(fsd, 4),
        "equity_mean": round(eq_mean, 4), "equity_spread": round(eq_spread, 4),
        "equity_values": {n: round(batteries[n]["leverage"][0], 4)
                          for n in equity_names},
        "crypto_leverage": round(cl, 4), "crypto_sd": round(csd, 4),
        "z_fx_vs_zero": round(z_zero, 2),
        "z_fx_vs_equities": round(z_vs_eq, 2),
        "z_crypto_vs_fx": round(z_vs_crypto, 2),
        "monotone_eq_fx_crypto": monotone,
        "verdict": verdict,
    }
