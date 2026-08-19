"""KRONOS-LIVE: the forward ledger (DESIGN23).

An append-only daily record of what the deployable system (KRONOS-TRADE)
recommended, judged by congruence tests calibrated before the first row
existed. The as-of guarantee is structural: the emit computes from a
committed GENESIS snapshot plus append-only daily BARS — never from a fresh
full-history fetch — so weight reproduction (L1) is exact by construction
and vendor revisions cannot masquerade as strategy drift. Corporate-action
divergences are detected against a small adjusted overlap window and become
explicit RE-ANCHOR events. Fetch failures write loud GAP rows; the silent
cached fallback is forbidden here (gate X35d).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import date

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_DIR = os.path.join(ROOT, "live")
GENESIS_DIR = os.path.join(LIVE_DIR, "genesis")
BARS_PATH = os.path.join(LIVE_DIR, "bars.csv")
LEDGER_PATH = os.path.join(LIVE_DIR, "ledger.jsonl")

FIELDS = ("open", "high", "low", "close")
ADJ_TOL = 0.005          # >0.5% divergence on the overlap = corporate action


# ---------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------

def _digest(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_numpy().tobytes()).hexdigest()[:16]


def write_genesis(ohlc: dict, live_dir: str = LIVE_DIR) -> str:
    """One-time anchor: the OHLC panel the ledger reconstructs from."""
    gdir = os.path.join(live_dir, "genesis")
    os.makedirs(gdir, exist_ok=True)
    for f in FIELDS:
        ohlc[f].to_csv(os.path.join(gdir, f"{f}.csv.gz"), compression="gzip")
    dig = _digest(ohlc["close"])
    with open(os.path.join(gdir, "META.json"), "w") as fh:
        json.dump({"close_digest": dig,
                   "span": [str(ohlc["close"].index[0].date()),
                            str(ohlc["close"].index[-1].date())],
                   "n_tickers": int(ohlc["close"].shape[1])}, fh, indent=1)
    return dig


def reconstruct_panel(live_dir: str = LIVE_DIR) -> dict:
    """genesis + bars (+ re-anchor factors) -> the as-of OHLC panel."""
    gdir = os.path.join(live_dir, "genesis")
    ohlc = {f: pd.read_csv(os.path.join(gdir, f"{f}.csv.gz"),
                           index_col=0, parse_dates=True) for f in FIELDS}
    bars_path = os.path.join(live_dir, "bars.csv")
    if os.path.exists(bars_path):
        bars = pd.read_csv(bars_path, parse_dates=["date"])
        for f in FIELDS:
            wide = bars.pivot(index="date", columns="ticker", values=f)
            wide = wide.reindex(columns=ohlc[f].columns)
            ohlc[f] = pd.concat([ohlc[f], wide]).sort_index()
            ohlc[f] = ohlc[f][~ohlc[f].index.duplicated(keep="last")]
    # apply logged re-anchor factors to history BEFORE each event date
    for ev in read_ledger(live_dir):
        if ev.get("status") == "REANCHOR":
            t0 = pd.Timestamp(ev["date"])
            for tk, fac in ev["factors"].items():
                if tk in ohlc["close"].columns:
                    for f in FIELDS:
                        ohlc[f].loc[ohlc[f].index < t0, tk] *= fac
    return ohlc


def append_bar(day: str, bar: pd.DataFrame, live_dir: str = LIVE_DIR) -> None:
    """bar: DataFrame indexed by ticker with columns open/high/low/close."""
    os.makedirs(live_dir, exist_ok=True)
    rec = bar.reset_index().rename(columns={"index": "ticker"})
    rec.insert(0, "date", day)
    path = os.path.join(live_dir, "bars.csv")
    rec.to_csv(path, mode="a", header=not os.path.exists(path), index=False)


def append_row(row: dict, live_dir: str = LIVE_DIR) -> None:
    os.makedirs(live_dir, exist_ok=True)
    with open(os.path.join(live_dir, "ledger.jsonl"), "a") as fh:
        fh.write(json.dumps(row, sort_keys=True, default=float) + "\n")


def read_ledger(live_dir: str = LIVE_DIR) -> list[dict]:
    path = os.path.join(live_dir, "ledger.jsonl")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def code_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, cwd=ROOT,
                              timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# the daily emit
# ---------------------------------------------------------------------------

def detect_adjustment(recent_adj: pd.DataFrame, recon_close: pd.DataFrame,
                      tol: float = ADJ_TOL) -> dict:
    """Compare a small freshly-fetched ADJUSTED window against the
    reconstructed tail. A stable per-ticker ratio far from 1 = corporate
    action (split/dividend re-adjustment). Returns {ticker: factor}."""
    overlap = recent_adj.index.intersection(recon_close.index)[-5:]
    factors = {}
    if len(overlap) < 3:
        return factors
    for tk in recon_close.columns:
        if tk not in recent_adj.columns:
            continue
        ratio = (recent_adj.loc[overlap, tk] / recon_close.loc[overlap, tk]).dropna()
        if len(ratio) >= 3 and abs(ratio.mean() - 1) > tol and ratio.std() < tol:
            factors[tk] = float(ratio.mean())
    return factors


def emit(fetch_bar_fn, recommend_fn, day: str | None = None,
         live_dir: str = LIVE_DIR) -> dict:
    """One live row. fetch_bar_fn() -> (bar_df, recent_adjusted_close) or
    raises; recommend_fn(ohlc_panel) -> the recommendation dict. Any fetch
    failure produces a GAP row — never a stale row dressed as live."""
    day = day or date.today().isoformat()
    try:
        bar, recent_adj = fetch_bar_fn()
    except Exception as exc:                              # loud GAP, no fallback
        row = {"date": day, "status": "GAP", "reason": f"fetch: {exc}",
               "code_version": code_version()}
        append_row(row, live_dir)
        return row

    recon = reconstruct_panel(live_dir)
    factors = detect_adjustment(recent_adj, recon["close"])
    if factors:
        append_row({"date": day, "status": "REANCHOR", "factors": factors,
                    "code_version": code_version()}, live_dir)
        recon = reconstruct_panel(live_dir)               # re-read with factors

    append_bar(day, bar, live_dir)
    recon2 = reconstruct_panel(live_dir)                  # panel incl. today
    try:
        rec = recommend_fn(recon2)
    except Exception as exc:
        row = {"date": day, "status": "GAP", "reason": f"compute: {exc}",
               "code_version": code_version()}
        append_row(row, live_dir)
        return row

    row = {
        "date": day, "status": "LIVE",
        "as_of": rec["as_of"], "regime": rec["regime"],
        "forecast_vol_ann": float(rec["forecast_portfolio_vol_ann"]),
        "exposure": float(rec["exposure"]),
        "weights": {k: round(float(v), 10)
                    for k, v in rec["target_weights"].items()},
        "input_digest": _digest(recon2["close"]),
        "code_version": code_version(),
    }
    append_row(row, live_dir)
    return row


# ---------------------------------------------------------------------------
# congruence checks (DESIGN23 L1-L3; calibrated constants, gate X35)
# ---------------------------------------------------------------------------

def l1_reproduce(row: dict, recommend_fn, live_dir: str = LIVE_DIR,
                 tol: float = 1e-9) -> dict:
    """Recompute the row from the reconstructed as-of panel; must match
    exactly. A digest mismatch means the reconstruction itself changed
    (should be impossible barring repo tampering) and is flagged distinctly."""
    recon = reconstruct_panel(live_dir)
    upto = {f: v.loc[:row["date"]] for f, v in recon.items()}
    if _digest(upto["close"]) != row["input_digest"]:
        return {"ok": False, "kind": "DIGEST_MISMATCH"}
    rec = recommend_fn(upto)
    got = {k: float(v) for k, v in rec["target_weights"].items()}
    want = {k: float(v) for k, v in row["weights"].items()}
    keys = set(got) | set(want)
    diff = max(abs(got.get(k, 0.0) - want.get(k, 0.0)) for k in keys) if keys else 0.0
    expo_diff = abs(float(rec["exposure"]) - row["exposure"])
    ok = diff <= tol and expo_diff <= tol
    return {"ok": ok, "kind": "EXACT" if ok else "WEIGHT_DRIFT",
            "max_weight_diff": diff, "exposure_diff": expo_diff}


def l2_null_band(window: int, n_sims: int = 300, seed: int = 11,
                 q: float = 0.95) -> float:
    """95% critical value for trailing mean daily QLIKE under the matched
    world (persistent SV, the DESIGN23 calibration world)."""
    rng = np.random.default_rng(seed)
    ann = np.sqrt(252)
    rho, eta, mu = 0.98, np.sqrt(0.25 * (1 - 0.98 ** 2)), np.log(0.115 / ann)
    stats = np.empty(n_sims)
    for s in range(n_sims):
        h = np.zeros(window)
        for t in range(1, window):
            h[t] = rho * h[t - 1] + eta * rng.normal()
        sig = np.exp(mu + h)
        r = sig * rng.normal(size=window)
        x = (r ** 2 + 1e-12) / sig ** 2
        stats[s] = np.mean(x - np.log(x) - 1.0)
    return float(np.quantile(stats, q))


def l2_vol_tracking(ledger: list[dict], live_dir: str = LIVE_DIR,
                    window: int = 90) -> dict:
    """Trailing mean daily QLIKE of realized portfolio r² vs the ledger's
    forecast variance, against the calibrated null band (power 0.73 @ 90d
    vs a 1.5x vol-engine failure, size ~5%; DESIGN23)."""
    rows = [r for r in ledger if r.get("status") == "LIVE"]
    if len(rows) < 2:
        return {"n": len(rows), "verdict": "INSUFFICIENT"}
    recon = reconstruct_panel(live_dir)
    close = recon["close"]
    rets = close.pct_change()
    qs = []
    for prev, cur in zip(rows[:-1], rows[1:]):
        d = pd.Timestamp(cur["date"])
        if d not in rets.index:
            continue
        w = pd.Series(prev["weights"], dtype=float)
        r_p = float((rets.loc[d].reindex(w.index).fillna(0.0) * w).sum()
                    * prev["exposure"])
        f_var = (prev["forecast_vol_ann"] / np.sqrt(252)) ** 2
        x = (r_p ** 2 + 1e-12) / max(f_var, 1e-12)
        qs.append(x - np.log(x) - 1.0)
    qs = qs[-window:]
    if len(qs) < 20:
        return {"n": len(qs), "verdict": "INSUFFICIENT"}
    stat = float(np.mean(qs))
    crit = l2_null_band(len(qs))
    return {"n": len(qs), "stat": round(stat, 4), "crit95": round(crit, 4),
            "verdict": "BREACH" if stat > crit else "OK"}


def l3_bands(ledger: list[dict], floor: float = 0.0, cap: float = 1.0) -> dict:
    """Exposure inside [floor, cap] on every LIVE row (TRADE: no leverage)."""
    rows = [r for r in ledger if r.get("status") == "LIVE"]
    bad = [r["date"] for r in rows
           if not (floor - 1e-9 <= r["exposure"] <= cap + 1e-9)]
    gaps = [r["date"] for r in ledger if r.get("status") == "GAP"]
    return {"n": len(rows), "band_violations": bad, "n_gaps": len(gaps),
            "verdict": "BREACH" if bad else "OK"}
