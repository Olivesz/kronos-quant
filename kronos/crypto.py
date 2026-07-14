"""KRONOS-CRYPTO: do the equity mechanism laws survive in crypto? (DESIGN14)

Atlas IX.1b. TRANSFER showed the laws reappear across equity markets that all
share one microstructure. Crypto breaks four assumptions at once — 24/7 (no
overnight gap), retail-momentum flow, no financial leverage, no close auction —
so it is the sharpest test of whether the laws are properties of MARKETS or of
the EQUITY microstructure. Reuses the CONSTANTS/TRANSFER 7-law battery; adds a
focused leverage-SIGN contrast (the one differentiating prediction, C2).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from kronos.constants import _leverage
from kronos.data import CACHE_DIR, fetch_yahoo_ohlc, generate_synthetic
from kronos.volest import gk_variance

# 10 liquid, long-listed majors with real Yahoo OHLC history from 2017.
CRYPTO_UNIVERSE = [
    "BTC-USD", "ETH-USD", "XRP-USD", "LTC-USD", "BCH-USD",
    "ADA-USD", "DOGE-USD", "LINK-USD", "XLM-USD", "ETC-USD",
]
CRYPTO_START = "2017-01-01"

# Crypto tails are REAL: >60% single-day moves happen and are the fat-tail
# signal C4 measures. So we do NOT reuse the equity clean_panel's 60% bad-tick
# clip; we only drop genuinely broken ticks (>500%) and forward-fill short gaps.
_CLIP = 5.0
_MIN_COVERAGE = 0.5
_MAX_FFILL = 3


def _clean_crypto(px: pd.DataFrame) -> pd.DataFrame:
    cov = px.notna().mean()
    px = px.loc[:, cov >= _MIN_COVERAGE]
    px = px.ffill(limit=_MAX_FFILL)
    px = px.dropna(axis=0, how="any")
    rets = px.pct_change()
    bad = rets.abs() > _CLIP           # data errors only, not real crypto moves
    if bad.to_numpy().any():
        rets = rets.where(~bad, 0.0).fillna(0.0)
        px = (1 + rets).cumprod().mul(px.iloc[0], axis=1)
    return px


def load_crypto(start: str = CRYPTO_START, end: str = "2026-06-05",
                seed: int = 42) -> dict:
    """Cached crypto OHLC + Garman-Klass variance panels.

    Returns {"close", "gk", "source"}. Falls back to a seeded synthetic market
    when Yahoo is unreachable so the study still runs offline (the JSON records
    which source was used).
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    paths = {f: os.path.join(CACHE_DIR, f"crypto_{f}_{start}_{end}.csv")
             for f in ("open", "high", "low", "close")}

    if all(os.path.exists(p) for p in paths.values()):
        ohlc = {f: pd.read_csv(p, index_col=0, parse_dates=True)
                for f, p in paths.items()}
        source = "yahoo"
    else:
        ohlc = fetch_yahoo_ohlc(CRYPTO_UNIVERSE, start, end)
        if ohlc is not None:
            for f, p in paths.items():
                ohlc[f].to_csv(p)
            source = "yahoo"
        else:
            c = generate_synthetic(CRYPTO_UNIVERSE, start, end, seed + 7)
            rng = np.random.default_rng(seed + 1)
            o = c.shift(1) * np.exp(rng.normal(0, 0.003, c.shape))
            span = np.abs(rng.normal(0, 0.02, c.shape)) + 0.004   # crypto is wilder
            ohlc = {"open": o, "close": c,
                    "high": np.maximum(o, c) * (1 + span / 2),
                    "low": np.minimum(o, c) * (1 - span / 2)}
            source = "synthetic"

    close = _clean_crypto(ohlc["close"])
    cols, idx = close.columns, close.index
    o, h, l = (ohlc[f].reindex(index=idx, columns=cols).ffill(limit=_MAX_FFILL)
               for f in ("open", "high", "low"))
    gk = gk_variance(o, h, l, close)
    return {"close": close, "gk": gk, "source": source}


def per_asset_leverage(close: pd.DataFrame, gk: pd.DataFrame) -> dict:
    """Leverage effect for each asset: mean corr(r_{t-tau}, gkvar_t), tau=1..10.
    Negative = equity-style (down -> higher future vol); positive = inverted."""
    out = {}
    for c in close.columns:
        r = np.log(close[c] / close[c].shift(1)).to_numpy()
        g = gk[c].to_numpy()
        out[c] = float(_leverage(r, g))
    return out


def leverage_contrast(batteries: dict[str, dict], equity_names: list[str],
                      crypto_name: str = "crypto") -> dict:
    """Is crypto's leverage effect inside the equity cohort, weaker, or inverted?

    Uses the battery's per-universe leverage (median-across-asset estimate with
    a block-bootstrap SD). Compares crypto to the spread of the equity cohort.
    """
    eq = np.array([batteries[n]["leverage"][0] for n in equity_names])
    eq_mean, eq_spread = float(eq.mean()), float(eq.std(ddof=1))
    cl, csd = batteries[crypto_name]["leverage"]
    # z of crypto vs the equity cohort: crypto sampling SD + cross-equity spread
    denom = float(np.sqrt(csd ** 2 + eq_spread ** 2 + 1e-12))
    z = (cl - eq_mean) / denom
    if cl > 0 and eq_mean < 0 and abs(z) > 2:
        verdict = "INVERTED"          # opposite sign, significant
    elif abs(z) > 2:
        verdict = "WEAKER" if cl > eq_mean else "STRONGER"
    else:
        verdict = "SAME-AS-EQUITIES"
    return {
        "crypto_leverage": round(cl, 4), "crypto_sd": round(csd, 4),
        "equity_mean": round(eq_mean, 4), "equity_spread": round(eq_spread, 4),
        "equity_values": {n: round(batteries[n]["leverage"][0], 4)
                          for n in equity_names},
        "z_vs_equities": round(z, 2), "verdict": verdict,
    }
