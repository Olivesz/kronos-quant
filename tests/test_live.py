"""Gate X35: the KRONOS-LIVE forward-ledger machinery (DESIGN23).

(a) L2 size/power: on matched synthetic worlds the vol-tracking check must
    not fire (~5% size); on a 1.5x vol-defect world at 90d it must fire with
    the pre-registered power (>= 0.6 in this reduced-rep gate; calibrated
    0.73 at full reps).
(b) L1 exactness: a clean emit reproduces exactly; a single perturbed weight
    is caught as WEIGHT_DRIFT; a perturbed archived bar is caught as
    DIGEST_MISMATCH.
(c) GAP path: a failing fetch writes a loud GAP row and appends no bar —
    never a stale row dressed as live.
(d) REANCHOR path: a simulated split (adjusted overlap at 0.5x) produces an
    explicit REANCHOR event, and L1 remains exact afterwards.
(e) L3: an out-of-band exposure row is a BREACH.
(f) BACKFILL: a hole in the archived bars is repaired as a logged event; the
    repaired panel equals the truth, an earlier row still reproduces exactly
    from the input it recorded, and a new row reproduces on the repaired panel.
Fully synthetic, tmpdir-isolated, no network.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from kronos.live import (
    _digest,
    append_bar,
    append_row,
    backfill,
    emit,
    l1_reproduce,
    l2_null_band,
    l3_bands,
    read_ledger,
    reconstruct_panel,
    write_genesis,
)

rng = np.random.default_rng(4)
TICKERS = ["AA", "BB", "CC"]


def toy_panel(T=260, seed=0):
    r = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-02", periods=T)
    close = pd.DataFrame(
        100 * np.exp(np.cumsum(r.normal(0, 0.01, (T, 3)), axis=0)),
        index=idx, columns=TICKERS)
    o = close.shift(1).bfill()
    return {"open": o, "high": close * 1.01, "low": o * 0.99, "close": close}


def toy_recommend(ohlc):
    """Deterministic toy system: inverse-last-close weights, fixed vol/expo."""
    c = ohlc["close"].dropna(how="all")
    last = c.iloc[-1]
    w = (1.0 / last) / (1.0 / last).sum()
    return {"as_of": str(c.index[-1].date()), "regime": "Bull",
            "forecast_portfolio_vol_ann": 0.10, "exposure": 0.9,
            "target_weights": {k: float(v) for k, v in w.items()}}


def make_live_dir(panel):
    d = tempfile.mkdtemp(prefix="kronos_live_gate_")
    write_genesis(panel, live_dir=d)
    return d


def bar_from(panel, i):
    return pd.DataFrame({f: panel[f].iloc[i] for f in ("open", "high", "low", "close")})


# --- (b)+(c)+(d)+(e): ledger mechanics on a toy world ---------------------------
full = toy_panel(T=270, seed=1)
genesis = {f: v.iloc[:260] for f, v in full.items()}
d = make_live_dir(genesis)

for i in range(260, 265):                                   # five clean emits
    day = str(full["close"].index[i].date())
    row = emit(lambda i=i: (bar_from(full, i), full["close"].iloc[i - 6:i + 1]),
               toy_recommend, day=day, live_dir=d)
    assert row["status"] == "LIVE", f"clean emit produced {row['status']}"

ledger = read_ledger(d)
assert len([r for r in ledger if r["status"] == "LIVE"]) == 5

l1 = l1_reproduce(ledger[-1], toy_recommend, live_dir=d)
assert l1["ok"] and l1["kind"] == "EXACT", f"clean L1 failed: {l1}"
print("X35b: clean emit reproduces EXACTLY (5 rows, max diff 0)")

# single perturbed weight -> WEIGHT_DRIFT
bad = dict(ledger[-1]); bad["weights"] = dict(bad["weights"])
bad["weights"][TICKERS[0]] += 1e-6
l1p = l1_reproduce(bad, toy_recommend, live_dir=d)
assert (not l1p["ok"]) and l1p["kind"] == "WEIGHT_DRIFT", l1p
# perturbed archived bar -> DIGEST_MISMATCH
bars_path = os.path.join(d, "bars.csv")
b = pd.read_csv(bars_path)
b.loc[b.index[-1], "close"] *= 1.001
b.to_csv(bars_path, index=False)
l1d = l1_reproduce(ledger[-1], toy_recommend, live_dir=d)
assert l1d["kind"] == "DIGEST_MISMATCH", l1d
b.loc[b.index[-1], "close"] /= 1.001
b.to_csv(bars_path, index=False)
print("X35b: perturbed weight -> WEIGHT_DRIFT; perturbed bar -> DIGEST_MISMATCH")

# GAP path: failing fetch -> loud GAP, no bar appended, no stale row
n_bars_before = len(pd.read_csv(bars_path))
def boom():
    raise RuntimeError("yahoo down")
row = emit(boom, toy_recommend, day="2026-01-09", live_dir=d)
assert row["status"] == "GAP" and "yahoo down" in row["reason"]
assert len(pd.read_csv(bars_path)) == n_bars_before, "GAP appended a bar"
assert read_ledger(d)[-1]["status"] == "GAP"
print("X35c: fetch failure -> loud GAP row, zero bars appended")

# REANCHOR: adjusted overlap at 0.5x for one ticker (a 2:1 split re-adjustment)
i = 265
day = str(full["close"].index[i].date())
adj = full["close"].iloc[i - 6:i + 1].copy()
adj[TICKERS[0]] *= 0.5
row = emit(lambda: (bar_from(full, i), adj), toy_recommend, day=day, live_dir=d)
ledger = read_ledger(d)
kinds = [r["status"] for r in ledger[-2:]]
assert "REANCHOR" in kinds and row["status"] in ("LIVE", "REANCHOR"), kinds
ev = [r for r in ledger if r["status"] == "REANCHOR"][-1]
assert abs(ev["factors"][TICKERS[0]] - 0.5) < 0.01, ev
recon = reconstruct_panel(d)
assert abs(recon["close"].iloc[0][TICKERS[0]]
           / (genesis["close"].iloc[0][TICKERS[0]] * 0.5) - 1) < 1e-9
live_last = [r for r in ledger if r["status"] == "LIVE"][-1]
l1r = l1_reproduce(live_last, toy_recommend, live_dir=d)
assert l1r["ok"], f"L1 not exact after REANCHOR: {l1r}"
print(f"X35d: split detected (factor {ev['factors'][TICKERS[0]]:.3f}), "
      "REANCHOR logged, L1 still EXACT")

# L3 band breach
append_row({"date": "2026-01-12", "status": "LIVE", "exposure": 1.2,
            "weights": {}, "forecast_vol_ann": 0.1, "input_digest": "x",
            "as_of": "2026-01-12", "regime": "Bull", "code_version": "t"}, d)
l3 = l3_bands(read_ledger(d))
assert l3["verdict"] == "BREACH" and "2026-01-12" in l3["band_violations"]
print("X35e: out-of-band exposure -> BREACH")
shutil.rmtree(d)

# --- (f) BACKFILL: a hole in the archived bars, repaired as a logged event ------
# genesis ends at day 199 on an OLDER adjustment basis for one ticker (x0.98,
# as if a dividend had since been back-adjusted); bars resume at day 230, so
# days 200..229 are a hole the reconstruction reads as one return.
full = toy_panel(T=260, seed=3)
old_basis = {f: v.iloc[:200].copy() for f, v in full.items()}
for f in old_basis:
    old_basis[f][TICKERS[0]] *= 0.98
d = make_live_dir(old_basis)
for i in range(230, 240):
    append_bar(str(full["close"].index[i].date()), bar_from(full, i), live_dir=d)
day_a = str(full["close"].index[240].date())
row_a = emit(lambda: (bar_from(full, 240), full["close"].iloc[234:241]),
             toy_recommend, day=day_a, live_dir=d)
assert row_a["status"] == "LIVE"
gapped = reconstruct_panel(d)["close"]
assert (gapped.index[1:] - gapped.index[:-1]).max() > pd.Timedelta(days=20), "hole not planted"

record = str(full["close"].index[241].date())
missing = {f: v.iloc[199:230] for f, v in full.items()}       # anchor day 199 + hole
ev = backfill(missing, record_date=record, applies_before=str(full["close"].index[200].date()),
              reason="toy hole", live_dir=d)
assert ev["status"] == "BACKFILL" and ev["n_days"] == 30, ev
assert set(ev["factors"]) == {TICKERS[0]} and abs(ev["factors"][TICKERS[0]] - 1 / 0.98) < 1e-12, ev
fixed = reconstruct_panel(d)["close"]
truth = full["close"].iloc[:241]
assert list(fixed.index) == list(truth.index), "backfilled panel still has a hole"
err = float((fixed - truth).abs().max().max() / truth.abs().max().max())
assert err < 1e-12, f"repaired panel != truth (rel err {err:.1e})"

# the earlier row still reproduces from the gapped input it actually used ...
l1a = l1_reproduce(row_a, toy_recommend, live_dir=d)
assert l1a["ok"] and l1a["kind"] == "EXACT", f"old row no longer reproduces: {l1a}"
# ... and that requires the as-of rebuild: the full panel would not reproduce it
assert _digest(reconstruct_panel(d)["close"].loc[:day_a]) != row_a["input_digest"]
# a new row is computed on the repaired panel and reproduces too
row_b = emit(lambda: (bar_from(full, 241), full["close"].iloc[235:242]),
             toy_recommend, day=record, live_dir=d)
assert row_b["status"] == "LIVE"
l1b = l1_reproduce(row_b, toy_recommend, live_dir=d)
assert l1b["ok"] and l1b["kind"] == "EXACT", f"post-backfill row: {l1b}"
print("X35f: BACKFILL repairs the hole (panel == truth, basis re-anchored "
      f"x{ev['factors'][TICKERS[0]]:.4f}); the earlier row still reproduces EXACTLY "
      "from its recorded input; the full panel would not; a new row reproduces")
shutil.rmtree(d)

# --- (a) L2 size and power on synthetic tracks ----------------------------------
def l2_stat_track(window, vol_scale, seed):
    """Mean daily QLIKE of a track where realized vol = vol_scale x forecast."""
    r = np.random.default_rng(seed)
    ann = np.sqrt(252)
    rho, eta, mu = 0.98, np.sqrt(0.25 * (1 - 0.98 ** 2)), np.log(0.115 / ann)
    h = np.zeros(window)
    for t in range(1, window):
        h[t] = rho * h[t - 1] + eta * r.normal()
    sig_fc = np.exp(mu + h)
    rets = sig_fc * vol_scale * r.normal(size=window)
    x = (rets ** 2 + 1e-12) / sig_fc ** 2
    return float(np.mean(x - np.log(x) - 1.0))

crit = l2_null_band(90, n_sims=600)
size = np.mean([l2_stat_track(90, 1.0, 10_000 + s) > crit for s in range(200)])
power = np.mean([l2_stat_track(90, 1.5, 20_000 + s) > crit for s in range(200)])
print(f"X35a: L2 @90d — size {size:.2f} (must be <= 0.10), "
      f"power vs 1.5x defect {power:.2f} (must be >= 0.60; registered 0.68)")
assert size <= 0.10, "L2 over-rejects on matched worlds"
assert power >= 0.60, "L2 lacks the pre-registered power at 90d"

print("\nGATE X35 PASSED")
