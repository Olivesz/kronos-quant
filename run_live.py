"""KRONOS-LIVE runner (DESIGN23): daily forward-ledger emit + congruence check.

  .venv/bin/python run_live.py --emit    # fetch today's bar, append ledger row
  .venv/bin/python run_live.py --check   # L1/L2/L3 congruence on the ledger

The emit is strictly as-of: it fetches ONLY the recent bar window, appends to
live/bars.csv, and computes from genesis+bars (kronos/live.py). Any fetch or
compute failure writes a loud GAP row — there is no cached fallback here.
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

from config import CFG
from kronos.data import clean_panel
from kronos.live import (
    LIVE_DIR,
    SHIPPED,
    append_row,
    emit,
    emit_shipped,
    l1_reproduce,
    l2_vol_tracking,
    l3_bands,
    read_ledger,
    reconstruct_panel,
    shipped_l1,
)
from kronos.trade import TradeConfig, TradingSystem

FIELDS = ("open", "high", "low", "close")


def fetch_recent_bar():
    """Strict fetch of the latest daily bar for the universe (no fallback).
    Returns (bar_df indexed by ticker, recent adjusted-close window)."""
    import yfinance as yf
    raw = yf.download(CFG.universe, period="10d", auto_adjust=True,
                      progress=False, threads=True)
    if raw is None or len(raw) == 0 or not isinstance(raw.columns, pd.MultiIndex):
        raise RuntimeError("yahoo returned empty/malformed recent window")
    fields = {}
    for f in FIELDS:
        name = f.capitalize()
        df = raw[name] if name in raw.columns.get_level_values(0) \
            else raw.xs(name, axis=1, level=1)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        fields[f] = df
    close = fields["close"].dropna(how="all")
    if close.shape[0] == 0 or close.iloc[-1].notna().mean() < 0.8:
        raise RuntimeError("last bar missing for >20% of universe")
    last = close.index[-1]
    bar = pd.DataFrame({f: fields[f].loc[last] for f in FIELDS})
    bar.index.name = "ticker"
    return bar.dropna(), close, str(last.date())


def recommend_from_panel(ohlc: dict) -> dict:
    px = clean_panel(ohlc["close"].copy(), CFG.min_coverage, CFG.max_ffill_days)
    cols = [c for c in px.columns if c in ohlc["close"].columns]
    idx = px.index
    aligned = {k: v.reindex(index=idx, columns=cols) for k, v in ohlc.items()}
    sysd = TradingSystem(TradeConfig(forecast_vol=True))
    return sysd.recommend(px[cols], aligned, notional=100_000.0)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode == "--emit":
        bar, recent_adj, bar_date = None, None, None
        try:
            bar, recent_adj, bar_date = fetch_recent_bar()
        except Exception:
            pass  # emit() will re-raise through its own fetch call below
        ledger = read_ledger()
        if bar_date and any(r.get("date") == bar_date and r.get("status") == "LIVE"
                            for r in ledger):
            print(f"[live] {bar_date} already recorded — nothing to do")
            return 0

        def fetch():
            if bar is None:
                b, a, _ = fetch_recent_bar()   # surface the original error
                return b, a
            return bar, recent_adj

        row = emit(fetch, recommend_from_panel, day=bar_date)
        if row["status"] == "LIVE":                    # today's bar is archived
            srow = emit_shipped(row["date"], CFG)
            print(f"[live] shipped stream {srow['date']}: {srow['status']}"
                  + (f" — {srow.get('reason', '')}" if srow["status"] == "GAP" else
                     f" | exposure {srow['exposure']:.2f}"))
        else:
            append_row({"date": row["date"], "status": "GAP",
                        "reason": f"main stream {row['status']}"}, name=SHIPPED)
        print(f"[live] {row['date']}: {row['status']}"
              + (f" — {row.get('reason', '')}" if row["status"] == "GAP" else
                 f" | regime {row.get('regime')} | fc vol "
                 f"{row.get('forecast_vol_ann', 0):.1%} | exposure "
                 f"{row.get('exposure', 0):.0%}"))
        return 0 if row["status"] in ("LIVE", "REANCHOR") else 1

    if mode == "--performance":
        from kronos.live import shipped_returns, write_performance
        doc = write_performance(CFG)
        srows = read_ledger(name=SHIPPED)
        sr = shipped_returns(srows, reconstruct_panel()["close"])
        sdoc = {"system": "the shipped book (1/N backbone, levered overlay, pairs "
                          "sleeve) — the README headline's system",
                "status": "display only (DESIGN23): no pass/fail before 3 years",
                "first": str(sr.index[0].date()) if len(sr) else None,
                "as_of": str(sr.index[-1].date()) if len(sr) else None,
                "n_days": int(len(sr)),
                "cum_return": float((1 + sr).prod() - 1) if len(sr) else 0.0,
                "daily": {"dates": [d.strftime("%Y-%m-%d") for d in sr.index],
                          "returns": [round(float(v), 10) for v in sr]}}
        with open(os.path.join(LIVE_DIR, "shipped_performance.json"), "w") as fh:
            json.dump(sdoc, fh, indent=1)
        sm = doc["summary"]
        if not doc["first_live"]:
            print("[live] no LIVE rows yet — performance.json empty")
            return 0
        print(f"[live] realized {doc['first_live']}..{doc['as_of']} "
              f"({sm['kronos']['n_days']} days): KRONOS-TRADE "
              f"{sm['kronos']['cum_return']:+.2%} | SPY {sm['spy']['cum_return']:+.2%}"
              f" | EW {sm['equal_weight']['cum_return']:+.2%} (display only)")
        return 0

    # --check
    ledger = read_ledger()
    live_rows = [r for r in ledger if r.get("status") == "LIVE"]
    print(f"[live] ledger: {len(ledger)} rows ({len(live_rows)} LIVE, "
          f"{sum(1 for r in ledger if r.get('status') == 'GAP')} GAP)")
    if not live_rows:
        print("[live] no LIVE rows yet")
        return 0
    l1 = l1_reproduce(live_rows[-1], recommend_from_panel)
    l2 = l2_vol_tracking(ledger)
    l3 = l3_bands(ledger)
    srows = [r for r in read_ledger(name=SHIPPED) if r.get("status") == "LIVE"]
    if srows:
        sl1 = shipped_l1(srows[-1], CFG)
        print(f"[live] shipped L1             : {sl1['kind']}")
    print(f"[live] L1 weight reproduction : {l1['kind']}"
          + ("" if l1["ok"] else f" (max diff {l1.get('max_weight_diff')})"))
    print(f"[live] L2 vol tracking        : {l2['verdict']} "
          f"(n={l2['n']}" + (f", stat {l2['stat']} vs crit {l2['crit95']})"
                            if "stat" in l2 else ")"))
    print(f"[live] L3 exposure/gaps       : {l3['verdict']} "
          f"({l3['n']} rows, {l3['n_gaps']} gaps)")
    print(json.dumps({"l1": l1, "l2": l2, "l3": l3}, default=float))
    breach = (not l1["ok"]) or l2.get("verdict") == "BREACH" \
        or l3.get("verdict") == "BREACH"
    return 2 if breach else 0


if __name__ == "__main__":
    sys.exit(main())
