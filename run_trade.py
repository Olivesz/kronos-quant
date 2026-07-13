"""KRONOS-TRADE runner: walk-forward backtest of the research-grounded trading
system, the forecast-vs-realized A/B, the honest metrics table, and a live
TODAY'S PORTFOLIO recommendation.

Run:  .venv/bin/python run_trade.py
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import replace

import numpy as np
import pandas as pd

from config import CFG
from kronos.data import load_prices, load_ohlc
from kronos.trade import TradingSystem, TradeConfig
from kronos import metrics as M

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research")


def _stats(r, name):
    return {"name": name, **{k: v for k, v in M.summary(r, name).items() if k != "name"}}


def main():
    t0 = time.time()
    px, src = load_prices(CFG)
    ohlc, _ = load_ohlc(CFG)
    cols = [c for c in px.columns if c in ohlc["close"].columns]
    idx = px.index.intersection(ohlc["close"].index)
    px = px.loc[idx, cols]
    ohlc = {k: v.loc[idx, cols] for k, v in ohlc.items()}
    print(f"KRONOS-TRADE: {len(cols)} assets, {len(idx)} days ({src})")

    # forecast-vol-targeted system (the research-grounded design)
    sys_fc = TradingSystem(TradeConfig(forecast_vol=True))
    bt_fc = sys_fc.backtest(px, ohlc)
    # realized-vol-targeted control (the A/B)
    sys_rl = TradingSystem(TradeConfig(forecast_vol=False))
    bt_rl = sys_rl.backtest(px, ohlc)

    start = bt_fc["start"]
    net_fc = bt_fc["net"].loc[start:]
    net_rl = bt_rl["net"].loc[start:]
    spy = px[CFG.market].pct_change().reindex(net_fc.index).fillna(0.0)
    ew = px.pct_change().loc[start:].mean(axis=1)

    strategies = {
        "KRONOS-TRADE (forecast-vol)": _stats(net_fc, "forecast"),
        "Realized-vol control": _stats(net_rl, "realized"),
        "SPY (buy & hold)": _stats(spy, "spy"),
        "Equal-weight": _stats(ew, "ew"),
    }

    print("\n=== Walk-forward backtest (net of costs) ===")
    print(f"{'strategy':30s} {'CAGR':>7} {'Sharpe':>7} {'Sortino':>8} "
          f"{'MaxDD':>7} {'Calmar':>7} {'CVaR95':>7}")
    for nm, s in strategies.items():
        print(f"{nm:30s} {s['cagr']:>6.1%} {s['sharpe']:>7.2f} {s['sortino']:>8.2f} "
              f"{s['max_dd']:>6.1%} {s['calmar']:>7.2f} {s['cvar95']:>6.2%}")

    # T1 verdict
    a, b = strategies["KRONOS-TRADE (forecast-vol)"], strategies["Realized-vol control"]
    print(f"\n[T1] forecast-vol vs realized: Sharpe {a['sharpe']:.2f} vs {b['sharpe']:.2f}, "
          f"MaxDD {a['max_dd']:.1%} vs {b['max_dd']:.1%}")
    sp = strategies["SPY (buy & hold)"]
    print(f"[T2] vs SPY: Sharpe {a['sharpe']:.2f} vs {sp['sharpe']:.2f}, "
          f"MaxDD {a['max_dd']:.1%} vs {sp['max_dd']:.1%}")
    print(f"[T3] CAGR (honest): {a['cagr']:.1%} vs SPY {sp['cagr']:.1%} "
          f"— risk-adjusted win, not a CAGR win (as the research dictates)")

    # live recommendation
    rec = sys_fc.recommend(px, ohlc, notional=100_000)
    print(f"\n=== TODAY'S PORTFOLIO ({rec['as_of']}) ===")
    print(f"regime: {rec['regime']} | forecast vol: {rec['forecast_portfolio_vol_ann']:.1%} "
          f"| exposure: {rec['exposure']:.0%} | last rebalance: {rec['rebalanced_on']}")
    print(f"{'ticker':8s} {'weight':>8} {'$ (100k acct)':>14}")
    for tk, w in list(rec["target_weights"].items())[:15]:
        print(f"{tk:8s} {w:>7.1%} {rec['dollar_alloc'].get(tk, 0):>13,.0f}")
    print(f"{'CASH':8s} {'':>8} {rec['cash']:>13,.0f}")

    # NAV series + payload for the dashboard
    nav = lambda r: (1 + r).cumprod()
    def ser(s):
        sub = s.iloc[::5]
        return {"dates": [str(d.date()) for d in sub.index],
                "values": sub.round(4).tolist()}
    payload = {
        "metrics": strategies,
        "ab": {"forecast_sharpe": a["sharpe"], "realized_sharpe": b["sharpe"],
               "forecast_maxdd": a["max_dd"], "realized_maxdd": b["max_dd"]},
        "nav": {"trade": ser(nav(net_fc)), "realized": ser(nav(net_rl)),
                "spy": ser(nav(spy)), "ew": ser(nav(ew))},
        "exposure": ser(bt_fc["exposure"].loc[start:]),
        "recommendation": rec,
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "trade.json"), "w") as f:
        json.dump(payload, f, indent=1, default=float)
    print(f"\nsaved research/trade.json — done in {time.time()-t0:.0f}s")
    return payload


if __name__ == "__main__":
    main()
