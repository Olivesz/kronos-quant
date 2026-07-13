"""KRONOS-TRANSFER: does market structure transfer across markets? (DESIGN13)

Territory IX.1 of the Atlas. Every law KRONOS measured — roughness H, fat
tails, one-clock Gaussianization, leverage effect, clock commonality, Hawkes
branching — was estimated on ONE universe (48 US tickers). Universality of
mechanism vs luck: re-estimate the same battery on Japan, Europe and Asia-EM
universes and apply the CONSTANTS variance-ratio machinery across SPACE
instead of TIME. Then run the frozen, US-tuned trading system on each foreign
universe with zero re-tuning.
"""
from __future__ import annotations

import os
from dataclasses import replace

import numpy as np
import pandas as pd

from kronos.data import CACHE_DIR, clean_panel, fetch_yahoo_ohlc, generate_synthetic
from kronos.volest import gk_variance
from kronos.constants import window_quantities, variance_ratio_test


# ---------------------------------------------------------------------------
# universes: long-listed liquid large caps, one timezone block each,
# plus a locally-listed broad-index ETF as the market proxy
# ---------------------------------------------------------------------------

UNIVERSES = {
    "japan": {
        "market": "1306.T",   # NEXT FUNDS TOPIX ETF
        "tickers": [
            "7203.T", "6758.T", "9984.T", "8306.T", "6861.T", "9432.T",
            "9433.T", "6501.T", "6752.T", "7267.T", "7974.T", "9983.T",
            "8035.T", "4063.T", "4502.T", "4568.T", "6954.T", "6301.T",
            "7751.T", "5108.T", "8031.T", "8058.T", "8766.T", "8801.T",
            "2914.T", "6902.T", "4519.T", "3382.T", "9020.T",
        ],
    },
    "europe": {
        "market": "EXW1.DE",  # iShares EURO STOXX 50 ETF
        "tickers": [
            "SAP.DE", "SIE.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "DTE.DE",
            "MUV2.DE", "BMW.DE", "MC.PA", "OR.PA", "TTE.PA", "SAN.PA",
            "AIR.PA", "BNP.PA", "SU.PA", "AI.PA", "CS.PA", "ASML.AS",
            "PHIA.AS", "INGA.AS", "HEIA.AS", "SHEL.L", "HSBA.L", "AZN.L",
            "ULVR.L", "BP.L", "GSK.L", "RIO.L", "DGE.L", "VOD.L", "BARC.L",
            "SAN.MC", "IBE.MC", "ITX.MC", "ENI.MI", "ISP.MI",
        ],
    },
    "asia_em": {
        "market": "2800.HK",  # Tracker Fund of Hong Kong
        "tickers": [
            "0700.HK", "0941.HK", "1398.HK", "0939.HK", "3988.HK", "2318.HK",
            "0386.HK", "0857.HK", "2628.HK", "0388.HK", "0016.HK", "0001.HK",
            "0027.HK", "0011.HK", "1299.HK", "0066.HK",
            "005930.KS", "000660.KS", "005380.KS", "051910.KS", "035420.KS",
            "2330.TW", "2317.TW", "2454.TW",
            "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        ],
    },
}

# mixed holiday calendars: coverage vs the union index is necessarily below
# the US universe's, and multi-day gaps around local holidays are normal
_MIN_COVERAGE = 0.90
_MAX_FFILL = 5


def load_universe(name: str, start: str, end: str, seed: int = 42) -> dict:
    """Cached OHLC + GK-variance panels for one foreign universe.

    Returns {"close", "gk", "source"}; falls back to a synthetic market
    (distinct seed per universe) when Yahoo is unreachable, so the study
    still runs offline — the JSON records which source was used.
    """
    spec = UNIVERSES[name]
    tickers = list(dict.fromkeys(spec["tickers"] + [spec["market"]]))
    os.makedirs(CACHE_DIR, exist_ok=True)
    paths = {f: os.path.join(CACHE_DIR, f"transfer_{name}_{f}_{start}_{end}.csv")
             for f in ("open", "high", "low", "close")}

    if all(os.path.exists(p) for p in paths.values()):
        ohlc = {f: pd.read_csv(p, index_col=0, parse_dates=True)
                for f, p in paths.items()}
        source = "yahoo"
    else:
        ohlc = fetch_yahoo_ohlc(tickers, start, end)
        if ohlc is not None:
            for f, p in paths.items():
                ohlc[f].to_csv(p)
            source = "yahoo"
        else:
            c = generate_synthetic(tickers, start, end,
                                   seed + abs(hash(name)) % 1000)
            rng = np.random.default_rng(seed + 1)
            o = c.shift(1) * np.exp(rng.normal(0, 0.003, c.shape))
            span = np.abs(rng.normal(0, 0.008, c.shape)) + 0.002
            ohlc = {"open": o, "close": c,
                    "high": np.maximum(o, c) * (1 + span / 2),
                    "low": np.minimum(o, c) * (1 - span / 2)}
            source = "synthetic"

    close = clean_panel(ohlc["close"], _MIN_COVERAGE, _MAX_FFILL)
    cols, idx = close.columns, close.index
    o, h, l = (ohlc[f].reindex(index=idx, columns=cols).ffill(limit=_MAX_FFILL)
               for f in ("open", "high", "low"))
    gk = gk_variance(o, h, l, close)
    return {"close": close, "gk": gk, "source": source}


# ---------------------------------------------------------------------------
# the battery: full-span law estimates with sampling SDs
# ---------------------------------------------------------------------------

def battery(close: pd.DataFrame, gk: pd.DataFrame, curve: dict | None = None,
            n_boot: int = 40) -> dict:
    """The CONSTANTS 7-law battery pooled over the full span of one universe.
    Returns {quantity: (estimate, sampling SD)}."""
    lo, hi = str(close.index[0].date()), str(close.index[-1].date())
    return window_quantities(close, gk, lo, hi, curve, n_boot=n_boot)


def transfer_tests(batteries: dict[str, dict], ref: str = "US") -> dict:
    """Per-law cross-universe stability test.

    The variance-ratio test asks whether the cross-UNIVERSE dispersion of a
    law's estimates exceeds their within-universe sampling noise (same
    machinery CONSTANTS applies across eras). Also reports each foreign
    universe's z-score vs the reference universe.
    """
    out = {}
    for q in batteries[ref]:
        names = [n for n in batteries
                 if q in batteries[n] and np.isfinite(batteries[n][q][0])]
        means = np.array([batteries[n][q][0] for n in names])
        sds = np.array([batteries[n][q][1] for n in names])
        vr = variance_ratio_test(means, sds)
        m0, s0 = batteries[ref][q]
        z = {n: float((batteries[n][q][0] - m0)
                      / np.sqrt(batteries[n][q][1] ** 2 + s0 ** 2 + 1e-12))
             for n in names if n != ref}
        if np.isfinite(vr["p"]):
            cls = "UNIVERSE-SPECIFIC" if vr["p"] < 0.10 else "TRANSFERS"
        else:  # <3 universes: VR undefined, fall back to the pairwise z-test
            zmax = max((abs(v) for v in z.values()), default=0.0)
            cls = "UNIVERSE-SPECIFIC" if zmax > 2.5 else "TRANSFERS"
        out[q] = {
            "values": {n: round(float(batteries[n][q][0]), 3) for n in names},
            "sds": {n: round(float(batteries[n][q][1]), 3) for n in names},
            "VR": round(vr["VR"], 2) if np.isfinite(vr["VR"]) else None,
            "p": round(vr["p"], 3) if np.isfinite(vr["p"]) else None,
            "z_vs_ref": {n: round(v, 2) for n, v in z.items()},
            "class": cls,
        }
    return out


# ---------------------------------------------------------------------------
# the frozen system: US-tuned config, zero re-tuning, foreign universe
# ---------------------------------------------------------------------------

def frozen_system(px: pd.DataFrame, market: str, cfg_base) -> dict:
    """Run the core book (regimes -> signals -> HRP+BL -> risk overlay) on a
    universe with every hyperparameter exactly as tuned on the US."""
    from kronos.regime import walkforward_regimes
    from kronos.backtest import run_backtest
    from kronos import metrics as M

    cfg = replace(cfg_base, universe=list(px.columns), market=market)
    mkt = px[market].pct_change().dropna()
    rg = walkforward_regimes(mkt, cfg)
    bt = run_backtest(px, rg["regime"], cfg)
    start = bt["warmup_end"]
    net = bt["net"].loc[start:]
    index = mkt.reindex(net.index).fillna(0.0)
    ew = px.pct_change().fillna(0.0).loc[start:].mean(axis=1)
    return {"net": M.summary(net, "frozen KRONOS"),
            "index": M.summary(index, "local index"),
            "ew": M.summary(ew, "equal-weight"),
            "traded_days": int(len(net))}
