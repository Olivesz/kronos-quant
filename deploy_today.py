"""KRONOS-TRADE — live deployment: fetch the freshest prices and print today's
recommended portfolio. Produces a recommendation only; executes nothing.

Run:  .venv/bin/python deploy_today.py [notional]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

from config import CFG
from kronos.data import clean_panel, fetch_yahoo, fetch_yahoo_ohlc, load_ohlc, load_prices
from kronos.trade import TradeConfig, TradingSystem

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def get_fresh_data():
    """Fetch live prices+OHLC through today; fall back to the cache on failure."""
    today = date.today().isoformat()
    print(f"fetching live data through {today} ...")
    px = fetch_yahoo(CFG.universe, CFG.start, today)
    ohlc = fetch_yahoo_ohlc(CFG.universe, CFG.start, today)
    if px is not None and ohlc is not None and len(px) > 1000:
        px = clean_panel(px, CFG.min_coverage, CFG.max_ffill_days)
        return px, ohlc, "LIVE"
    print("live fetch unavailable — using cached data")
    px, _ = load_prices(CFG)
    ohlc, _ = load_ohlc(CFG)
    return px, ohlc, "CACHED"


def main():
    notional = float(sys.argv[1]) if len(sys.argv) > 1 else 100_000.0
    px, ohlc, source = get_fresh_data()
    cols = [c for c in px.columns if c in ohlc["close"].columns]
    idx = px.index.intersection(ohlc["close"].index)
    px = px.loc[idx, cols]
    ohlc = {k: v.loc[idx, cols] for k, v in ohlc.items()}

    sysd = TradingSystem(TradeConfig(forecast_vol=True))
    rec = sysd.recommend(px, ohlc, notional=notional)

    bar = "=" * 60
    print(f"\n{bar}\n  KRONOS-TRADE  ·  TODAY'S RECOMMENDED PORTFOLIO\n{bar}")
    print(f"  data source        : {source} (prices through {rec['as_of']})")
    print(f"  account notional   : ${notional:,.0f}")
    print(f"  detected regime    : {rec['regime']}")
    print(f"  forecast vol (ann) : {rec['forecast_portfolio_vol_ann']:.1%}")
    print(f"  target exposure    : {rec['exposure']:.0%}  (rest in cash; no leverage)")
    print(f"  last rebalance     : {rec['rebalanced_on']}")
    print(f"{bar}")
    print(f"  {'TICKER':8s}{'TARGET Wт':>12}{'$ ALLOCATION':>16}")
    print(f"  {'-'*8:8s}{'-'*10:>12}{'-'*14:>16}")
    tot = 0.0
    for tk, w in rec["target_weights"].items():
        d = rec["dollar_alloc"].get(tk, 0.0)
        tot += d
        print(f"  {tk:8s}{w*rec['exposure']:>11.1%}{d:>16,.0f}")
    print(f"  {'CASH':8s}{rec['cash']/notional:>11.1%}{rec['cash']:>16,.0f}")
    print(f"  {'-'*8:8s}{'-'*10:>12}{'-'*14:>16}")
    print(f"  {'TOTAL':8s}{'100.0%':>12}{notional:>16,.0f}")
    print(bar)
    print("  Weights shown are post-exposure (what to actually hold). Raw")
    print("  target weights sum to 100% of the invested sleeve before the")
    print(f"  {rec['exposure']:.0%} risk-exposure scaling.")
    print(bar)
    print("  DISCLAIMER: research/educational output, NOT financial advice.")
    print("  Backtest-derived; survivorship-biased universe; daily data;")
    print("  past performance does not predict returns. You execute trades")
    print("  yourself — this tool recommends, it does not transact.")
    print(bar)

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"positions_{rec['as_of']}.json")
    with open(path, "w") as f:
        json.dump({"source": source, **rec}, f, indent=2, default=float)
    print(f"\n  saved -> {path}")
    return rec


if __name__ == "__main__":
    main()
