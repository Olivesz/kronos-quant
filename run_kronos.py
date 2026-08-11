"""KRONOS pipeline: data -> regimes -> alpha -> portfolio -> risk -> dashboard.

Run:  .venv/bin/python run_kronos.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

from config import CFG, REGIME_NAMES
from kronos import metrics as M
from kronos.backtest import run_backtest, sleeve_backtests
from kronos.dashboard import render_dashboard
from kronos.data import load_prices
from kronos.pairs import run_pairs_sleeve
from kronos.regime import walkforward_regimes
from kronos.risk import portfolio_greeks

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def decimate(dates: pd.DatetimeIndex, values: np.ndarray, max_pts: int = 1500):
    """Min/max-preserving downsample: keeps spikes that stride sampling loses."""
    n = len(values)
    if n <= max_pts:
        keep = np.arange(n)
    else:
        buckets = np.array_split(np.arange(n), max_pts // 2)
        keep = set()
        for b in buckets:
            if len(b) == 0:
                continue
            seg = values[b]
            if np.isfinite(seg).any():
                keep.add(int(b[np.nanargmin(seg)]))
                keep.add(int(b[np.nanargmax(seg)]))
            keep.add(int(b[-1]))
        keep = np.array(sorted(keep))
    return ([str(dates[i].date()) for i in keep],
            [None if not np.isfinite(values[i]) else round(float(values[i]), 6)
             for i in keep])


def ser(dates, values, max_pts=1500):
    d, v = decimate(dates, np.asarray(values, dtype=float), max_pts)
    return {"dates": d, "values": v}


def round_list(x, nd=4):
    return [round(float(v), nd) if np.isfinite(v) else None for v in x]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    t_start = time.time()
    print("KRONOS pipeline starting")

    # 1. data ----------------------------------------------------------------
    px, source = load_prices(CFG)
    rets = px.pct_change().fillna(0.0)
    mkt = px[CFG.market].pct_change().dropna()
    print(f"[data] {source}: {px.shape[1]} tickers x {len(px)} days "
          f"({px.index[0].date()} -> {px.index[-1].date()})")

    # 2. regimes ---------------------------------------------------------------
    t0 = time.time()
    rg = walkforward_regimes(mkt, CFG)
    regime = rg["regime"]
    print(f"[regime] {rg['refits']} walk-forward refits in {time.time()-t0:.0f}s")

    # 3. core backtest ---------------------------------------------------------
    t0 = time.time()
    bt = run_backtest(px, regime, CFG)
    print(f"[backtest] core book in {time.time()-t0:.0f}s")

    # 4. pairs sleeve ------------------------------------------------------------
    t0 = time.time()
    pares = run_pairs_sleeve(px, [], CFG)
    pairs_ret = pares["returns"] * CFG.pairs_gross_sleeve
    print(f"[pairs] {len(pares['trades'])} trade events in {time.time()-t0:.0f}s")

    # 5. combine + attribution ---------------------------------------------------
    start = bt["warmup_end"]
    net = (bt["net"] + pairs_ret).loc[start:]
    gross = (bt["gross"] * bt["exposure_applied"] + pairs_ret).loc[start:]
    spy = mkt.reindex(net.index).fillna(0.0)
    ew = rets.loc[start:].mean(axis=1)

    t0 = time.time()
    sleeves = sleeve_backtests(px, regime, CFG)
    sleeves["pairs"] = pairs_ret
    print(f"[attribution] sleeves in {time.time()-t0:.0f}s")

    # 6. metrics -----------------------------------------------------------------
    stats = {
        "KRONOS (net)": M.summary(net, "KRONOS (net)"),
        "KRONOS (gross)": M.summary(gross, "KRONOS (gross)"),
        "SPY": M.summary(spy, "SPY"),
        "Equal-Weight": M.summary(ew, "Equal-Weight"),
    }
    years = len(net) / 252
    ann_cost = bt["costs"].loc[start:].sum() / years
    ann_fin = bt["financing"].loc[start:].sum() / years
    ann_turn = bt["turnover"].loc[start:].sum() / years
    greeks = portfolio_greeks(net, mkt, ann_cost + ann_fin)

    print("\n=== KRONOS net of costs ===")
    s = stats["KRONOS (net)"]
    print(f"  CAGR {s['cagr']:+.1%} | Vol {s['vol']:.1%} | Sharpe {s['sharpe']:.2f} | "
          f"Sortino {s['sortino']:.2f} | MaxDD {s['max_dd']:.1%} | CVaR95 {s['cvar95']:.2%}")
    print(f"  SPY: CAGR {stats['SPY']['cagr']:+.1%} Sharpe {stats['SPY']['sharpe']:.2f} "
          f"MaxDD {stats['SPY']['max_dd']:.1%}")

    # 7. payload --------------------------------------------------------------
    payload = build_payload(px, source, regime, rg, bt, pares, pairs_ret,
                            sleeves, net, gross, spy, ew, stats, greeks,
                            ann_cost, ann_fin, ann_turn)

    # attach KRONOS-X research results if cached (run_research.py)
    if "--research" in sys.argv:
        res_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research")
        research = {}
        core = ("horserace", "vollab", "rough", "rmt", "statarb",
                "cvar", "ensemble", "forensics", "synthesis")
        for name in core + ("tails", "rfsv", "laws", "clock", "surge",
                            "bits", "arrow", "decathlon", "critical", "reflex",
                            "constants", "trade", "transfer", "crypto", "edge",
                            "fx", "harvest", "decathlon2"):
            p = os.path.join(res_dir, f"{name}.json")
            if os.path.exists(p):
                with open(p) as f:
                    research[name] = json.load(f)
        if all(n in research for n in core):
            payload["research"] = research
            print(f"[research] attached {len(research)} experiments to dashboard")
        else:
            print(f"[research] only {len(research)} experiments cached — "
                  "run run_research.py all first; skipping research tab")

    os.makedirs(OUT, exist_ok=True)
    html_path = os.path.join(OUT, "dashboard.html")
    render_dashboard(payload, html_path)
    size_mb = os.path.getsize(html_path) / 1e6
    print(f"\n[dashboard] {html_path} ({size_mb:.1f} MB)")
    print(f"KRONOS done in {time.time()-t_start:.0f}s — open with:\n  open {html_path}")
    return payload


def build_payload(px, source, regime, rg, bt, pares, pairs_ret, sleeves,
                  net, gross, spy, ew, stats, greeks, ann_cost, ann_fin, ann_turn):
    idx = net.index
    nav = lambda r: (1 + r).cumprod()

    # regime series aligned to traded window. The raw single-day filtered
    # probabilities are causal but visually noisy, so for the *chart* we apply
    # a short causal EWMA (still look-ahead-free) and renormalize to sum to 1.
    filt_raw = rg["filtered"].reindex(idx).ffill()
    filt = filt_raw.ewm(span=10, min_periods=1).mean()
    filt = filt.div(filt.sum(axis=1), axis=0)
    reg_t = regime.reindex(idx).ffill().fillna(1).astype(int)

    # regime band segments for chart underlay
    segs, cur, seg_start = [], None, None
    for d, v in reg_t.items():
        if v != cur:
            if cur is not None and cur >= 0:
                segs.append({"r": int(cur), "a": str(seg_start.date()), "b": str(d.date())})
            cur, seg_start = v, d
    if cur is not None and cur >= 0:
        segs.append({"r": int(cur), "a": str(seg_start.date()), "b": str(idx[-1].date())})

    # per-regime stats (KRONOS net + SPY in each regime)
    per_regime = []
    for rid, rname in REGIME_NAMES.items():
        mask = reg_t == rid
        if mask.sum() < 20:
            continue
        per_regime.append({
            "name": rname, "days": int(mask.sum()),
            "kronos_ann": float(net[mask].mean() * 252),
            "kronos_sharpe": M.sharpe(net[mask]),
            "spy_ann": float(spy[mask].mean() * 252),
            "spy_sharpe": M.sharpe(spy[mask]),
        })

    # strategy weights over time (categorical stacked area)
    sw_dates, sw_series = [], {"momentum": [], "mean_reversion": [], "low_vol": []}
    sw_regime = []
    for d, rec in bt["strategy_weights"].items():
        if d < idx[0]:
            continue
        sw_dates.append(str(d.date()))
        sw_regime.append(rec["regime"])
        for k in sw_series:
            sw_series[k].append(rec[k])

    # latest portfolio
    last_w = bt["weights"].iloc[-1]
    last_w = last_w[last_w > 0.001].sort_values(ascending=False)

    # weight history heatmap: monthly samples
    wh = bt["weights"].loc[idx[0]:]
    monthly_w = wh.resample("ME").last()
    top_cols = wh.mean().sort_values(ascending=False).head(25).index.tolist()
    weight_heat = {
        "dates": [str(d.date()) for d in monthly_w.index],
        "tickers": top_cols,
        "values": [round_list(monthly_w[c].fillna(0).to_numpy(), 4) for c in top_cols],
    }

    # monthly returns heatmap
    mtab = M.monthly_table(net)
    monthly = [{"y": int(r.year), "m": int(r.month), "v": round(float(r.ret), 4)}
               for r in mtab.itertuples()]

    # histogram
    h_counts, h_edges = np.histogram(net.to_numpy(), bins=80)
    var95, cvar95 = M.var_cvar(net)

    # pairs: pick the z-history with the most points for the example chart.
    # Break the line across inactive re-selection gaps by inserting nulls.
    z_ex = {"pair": "", "dates": [], "z": []}
    if pares["z_history"]:
        key = max(pares["z_history"], key=lambda k: len(pares["z_history"][k]))
        hist = pares["z_history"][key][-900:]
        zd, zv, prev = [], [], None
        for d, z in hist:
            if prev is not None and (d - prev).days > 25:
                zd.append(str(prev.date())); zv.append(None)  # gap break
            zd.append(str(d.date())); zv.append(round(float(z), 3))
            prev = d
        z_ex = {"pair": f"{key[0]} / {key[1]}", "dates": zd, "z": zv}

    expo = bt["exposure"].loc[idx[0]:]
    roll_sharpe = (net.rolling(126).mean() / net.rolling(126).std() * np.sqrt(252))
    roll_vol = net.rolling(63).std() * np.sqrt(252)
    rb = greeks["rolling_beta"].reindex(idx)

    sleeve_navs = {k: ser(idx, nav(v.loc[idx[0]:].reindex(idx).fillna(0)).to_numpy())
                   for k, v in sleeves.items()}

    payload = {
        "meta": {
            "source": source.upper(),
            "generated": time.strftime("%Y-%m-%d %H:%M"),
            "range": [str(idx[0].date()), str(idx[-1].date())],
            "n_assets": int(px.shape[1]),
            "trading_days": int(len(idx)),
            "current_regime": REGIME_NAMES.get(int(reg_t.iloc[-1]), "?"),
            "rebalance_days": CFG.rebalance_every,
            "vol_target": CFG.vol_target,
            "ann_cost": float(ann_cost),
            "ann_financing": float(ann_fin),
            "ann_turnover": float(ann_turn),
        },
        "stats": stats,
        "greeks": {k: (float(v) if not isinstance(v, pd.Series) else None)
                   for k, v in greeks.items() if k != "rolling_beta"},
        "series": {
            "nav_net": ser(idx, nav(net).to_numpy()),
            "nav_gross": ser(idx, nav(gross).to_numpy()),
            "nav_spy": ser(idx, nav(spy).to_numpy()),
            "nav_ew": ser(idx, nav(ew).to_numpy()),
            "drawdown": ser(idx, M.drawdown_series(net).to_numpy()),
            "dd_spy": ser(idx, M.drawdown_series(spy).to_numpy()),
            "exposure": ser(idx, expo["exposure"].to_numpy()),
            "m_vol": ser(idx, expo["m_vol"].to_numpy()),
            "m_cvar": ser(idx, expo["m_cvar"].to_numpy()),
            "m_dd": ser(idx, expo["m_dd"].to_numpy()),
            "roll_sharpe": ser(idx, roll_sharpe.to_numpy()),
            "roll_vol": ser(idx, roll_vol.to_numpy()),
            "roll_beta": ser(idx, rb.to_numpy()),
            "prob_bull": ser(idx, filt["Bull"].to_numpy()),
            "prob_vol": ser(idx, filt["Volatile"].to_numpy()),
            "prob_bear": ser(idx, filt["Bear"].to_numpy()),
        },
        "sleeves": sleeve_navs,
        "regime": {
            "segments": segs,
            "transition": np.round(rg["model"].A_, 4).tolist(),
            "per_regime": per_regime,
            "names": ["Bull", "Volatile", "Bear"],
        },
        "strategy_weights": {"dates": sw_dates, "series": sw_series, "regime": sw_regime},
        "portfolio": {
            "tickers": last_w.index.tolist(),
            "weights": round_list(last_w.to_numpy(), 4),
            "heat": weight_heat,
        },
        "risk": {
            "hist_counts": [int(c) for c in h_counts],
            "hist_edges": round_list(h_edges, 5),
            "var95": float(var95), "cvar95": float(cvar95),
            "vol_target": CFG.vol_target,
        },
        "monthly": monthly,
        "pairs": {
            "table": [{"y": a, "x": b, "pos": p, "beta": bta, "dead": dd}
                      for a, b, p, bta, dd in pares["final_pairs"]],
            "trades": pares["trades"][-40:],
            "n_trades": len(pares["trades"]),
            "z_example": z_ex,
            "entry": CFG.pairs_entry_z, "exit": CFG.pairs_exit_z,
            "stop": CFG.pairs_stop_z,
            "total_return": float((1 + pairs_ret).prod() - 1),
        },
    }
    return payload


if __name__ == "__main__":
    main()
