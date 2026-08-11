"""KRONOS-X research runner: executes each experiment, caches results.

Usage:
  .venv/bin/python run_research.py horserace   # one experiment
  .venv/bin/python run_research.py all
  .venv/bin/python run_research.py all --force # ignore caches
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

from config import CFG
from kronos import metrics as M
from kronos.data import load_ohlc, load_prices
from kronos.volest import gk_variance

ROOT = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(ROOT, "research")
os.makedirs(RES, exist_ok=True)


def cache_path(name: str) -> str:
    return os.path.join(RES, f"{name}.json")


def save(name: str, obj: dict) -> None:
    with open(cache_path(name), "w") as f:
        json.dump(obj, f, indent=1, default=float)


def load_cached(name: str) -> dict | None:
    p = cache_path(name)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def get_data():
    px, src = load_prices(CFG)
    ohlc, _ = load_ohlc(CFG)
    # align OHLC to the cleaned close panel
    cols = [c for c in px.columns if c in ohlc["close"].columns]
    idx = px.index.intersection(ohlc["close"].index)
    ohlc = {k: v.loc[idx, cols] for k, v in ohlc.items()}
    px = px.loc[idx, cols]
    gk = gk_variance(ohlc["open"], ohlc["high"], ohlc["low"], ohlc["close"])
    return px, ohlc, gk, src


# ---------------------------------------------------------------------------
# Experiment 1: regime horse race (Q1, Q2)
# ---------------------------------------------------------------------------

def exp_horserace(force: bool = False) -> dict:
    if not force and (c := load_cached("horserace")):
        print("[horserace] cached")
        return c
    from kronos.backtest import run_backtest
    from kronos.horserace import build_features_gk, run_horserace

    px, ohlc, gk, src = get_data()
    mkt = px[CFG.market].pct_change().dropna()
    feats = build_features_gk(mkt, gk[CFG.market])
    print(f"[horserace] features: {len(feats)} days, eval from 2019-01-01")

    t0 = time.time()
    race = run_horserace(feats, CFG)
    print(f"[horserace] statistical race done in {time.time()-t0:.0f}s")

    # economic value: plug each engine's regime series into the platform
    for name, rec in race["models"].items():
        regime = rec.pop("_regime")
        rec.pop("_reg_probs", None)
        t1 = time.time()
        bt = run_backtest(px, regime, CFG)
        net = bt["net"].loc[bt["warmup_end"]:]
        eval_net = net.loc[race["eval_start"]:]
        rec["econ_sharpe_full"] = M.sharpe(net)
        rec["econ_sharpe_eval"] = M.sharpe(eval_net)
        rec["econ_maxdd_full"] = M.max_drawdown(net)[0]
        print(f"[horserace] {name}: logscore {rec['logscore_oos']:.4f} | "
              f"Sharpe(eval) {rec['econ_sharpe_eval']:.2f} | "
              f"sw/yr {rec['switches_per_year']:.1f} | "
              f"COVID latency {rec['latency']['COVID crash']}d "
              f"({time.time()-t1:.0f}s)")

    # pre-registered decision rule
    by_score = max(race["models"], key=lambda m: race["models"][m]["logscore_oos"])
    by_econ = max(race["models"], key=lambda m: race["models"][m]["econ_sharpe_eval"])
    winner = by_score
    margin = (race["models"][by_econ]["econ_sharpe_eval"]
              - race["models"][by_score]["econ_sharpe_eval"])
    if by_econ != by_score and margin > 0.15:
        winner = by_econ
    race["decision"] = {"by_logscore": by_score, "by_econ": by_econ,
                        "winner": winner, "econ_margin": margin}
    print(f"[horserace] winner: {winner} (logscore: {by_score}, econ: {by_econ}, "
          f"margin {margin:+.2f})")
    save("horserace", race)
    return race


# ---------------------------------------------------------------------------
# Experiment 2: volatility lab (Q3a)
# ---------------------------------------------------------------------------

def exp_vollab(force: bool = False) -> dict:
    if not force and (c := load_cached("vollab")):
        print("[vollab] cached")
        return c
    from kronos.vollab import diebold_mariano, qlike, walkforward_vol_forecasts

    px, ohlc, gk, src = get_data()
    r = px[CFG.market].pct_change().dropna()
    gkv = gk[CFG.market].dropna()
    t0 = time.time()
    fc = walkforward_vol_forecasts(r, gkv, min_train=750, refit_every=21)
    oos = fc.dropna()
    losses = {m: qlike(oos["rv"].to_numpy(), oos[m].to_numpy())
              for m in ("ewma", "har", "garch")}
    table = {m: float(np.mean(L)) for m, L in losses.items()}
    dm = {}
    for a, b in (("har", "ewma"), ("garch", "ewma"), ("har", "garch")):
        dm[f"{a}_vs_{b}"] = diebold_mariano(losses[a], losses[b])
    winner = min(table, key=table.get)
    print(f"[vollab] QLIKE: { {k: round(v,4) for k,v in table.items()} } "
          f"winner={winner} ({time.time()-t0:.0f}s, "
          f"garch_fails={fc.attrs.get('garch_fails',0)})")
    for k, v in dm.items():
        print(f"[vollab] DM {k}: stat={v['stat']:+.2f} p={v['p']:.4f}")
    # downsampled forecast-vs-realized series for the dashboard
    sub = oos.iloc[::5]
    out = {"qlike": table, "dm": dm, "winner": winner,
           "n_oos_days": len(oos),
           "series": {"dates": [str(d.date()) for d in sub.index],
                      "rv_ann": np.sqrt(sub["rv"] * 252).round(4).tolist(),
                      **{m: np.sqrt(sub[m] * 252).round(4).tolist()
                         for m in ("ewma", "har", "garch")}}}
    save("vollab", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 3: rough volatility (Q3b)
# ---------------------------------------------------------------------------

def exp_rough(force: bool = False) -> dict:
    if not force and (c := load_cached("rough")):
        print("[rough] cached")
        return c
    from kronos.rough import block_bootstrap_ci, estimate_hurst, subwindow_hursts

    px, ohlc, gk, src = get_data()
    gkv = gk[CFG.market].dropna()
    t0 = time.time()
    res = {}
    for label, smooth in (("daily", 1), ("smoothed_5d", 5)):
        est = estimate_hurst(gkv, smooth=smooth)
        lo, hi = block_bootstrap_ci(gkv, n_boot=200, smooth=smooth)
        ci = {"ci_lo": lo, "ci_hi": hi}
        res[label] = {"H": est["H"], "ci": ci,
                      "zeta": est["zeta"].tolist(), "qs": est["qs"],
                      "deltas": est["deltas"],
                      "log_m": est["log_m"].tolist(),
                      "monofractal_resid": est["monofractal_resid"]}
    res["subwindow_H"] = subwindow_hursts(gkv, window_years=4)
    # cross-sectional: median H across all names (daily proxy)
    hs = []
    for c_ in px.columns:
        v = gk[c_].dropna()
        if len(v) > 1500:
            hs.append(estimate_hurst(v)["H"])
    res["cross_sectional"] = {"median_H": float(np.median(hs)),
                              "q25": float(np.percentile(hs, 25)),
                              "q75": float(np.percentile(hs, 75)),
                              "n_names": len(hs)}
    print(f"[rough] SPY H={res['daily']['H']:.3f} "
          f"CI[{res['daily']['ci']['ci_lo']:.3f},{res['daily']['ci']['ci_hi']:.3f}] | "
          f"5d-smoothed H={res['smoothed_5d']['H']:.3f} | "
          f"cross-sec median H={res['cross_sectional']['median_H']:.3f} "
          f"({time.time()-t0:.0f}s)")
    save("rough", res)
    return res


# ---------------------------------------------------------------------------
# Experiment 4: RMT covariance bake-off (Q5a)
# ---------------------------------------------------------------------------

def exp_rmt(force: bool = False) -> dict:
    if not force and (c := load_cached("rmt")):
        print("[rmt] cached")
        return c
    from kronos.rmt import corr_from_cov, minvar_bakeoff, mp_pdf, n_signal_factors

    px, ohlc, gk, src = get_data()
    rets = px.pct_change().fillna(0.0).iloc[1:]
    t0 = time.time()
    bake = minvar_bakeoff(rets)
    # final-window eigenvalue spectrum for the dashboard
    sub = rets.iloc[-252:]
    corr = corr_from_cov(np.cov(sub.T.to_numpy()))
    ev = np.linalg.eigvalsh(corr)[::-1]
    k, edge = n_signal_factors(ev, corr.shape[0] / 252)
    grid = np.linspace(1e-3, 3.0, 200)
    bake["spectrum"] = {"eigvals": ev.tolist(), "edge": edge, "n_signal": k,
                        "mp_grid": grid.tolist(),
                        "mp_pdf": mp_pdf(grid, corr.shape[0] / 252,
                                         1.0 - ev[:k].sum() / len(ev)).tolist()}
    print("[rmt] min-var realized vol: " +
          " | ".join(f"{m}={v['realized_vol']:.2%}" for m, v in bake["methods"].items()) +
          f" | signal factors={k} ({time.time()-t0:.0f}s)")
    save("rmt", bake)
    return bake


# ---------------------------------------------------------------------------
# Experiment 5: stat-arb sleeve on real data
# ---------------------------------------------------------------------------

def exp_statarb(force: bool = False) -> dict:
    if not force and (c := load_cached("statarb")):
        print("[statarb] cached")
        return c
    from kronos.statarb import run_statarb_sleeve

    px, ohlc, gk, src = get_data()
    t0 = time.time()
    res = run_statarb_sleeve(px, CFG)
    r = res["returns"]
    active = r[r != 0]
    def stats(seg):
        if len(seg) < 50 or seg.std() == 0:
            return {"ann_ret": 0.0, "sharpe": 0.0}
        return {"ann_ret": float(seg.mean() * 252),
                "sharpe": float(seg.mean() / seg.std() * np.sqrt(252))}
    out = {"full": stats(active),
           "pre2019": stats(active.loc[:"2018-12-31"]),
           "post2019": stats(active.loc["2019-01-01":]),
           "n_open_mean": res["n_open_mean"],
           "m_factors_median": res["m_factors_median"],
           "trade_days": res["trade_days"],
           "nav": {"dates": [str(d.date()) for d in r.index[::5]],
                   "values": (1 + r).cumprod().iloc[::5].round(4).tolist()},
           "median_abs_s": res["median_abs_s"]}
    # persist daily returns for the synthesis step
    r.to_csv(os.path.join(RES, "statarb_returns.csv"))
    print(f"[statarb] full: {out['full']['ann_ret']:+.1%}/yr SR {out['full']['sharpe']:.2f} | "
          f"pre2019 SR {out['pre2019']['sharpe']:.2f} | post2019 SR {out['post2019']['sharpe']:.2f} | "
          f"avg open {out['n_open_mean']:.1f} | m_med {out['m_factors_median']:.0f} "
          f"({time.time()-t0:.0f}s)")
    save("statarb", out)
    return out


# ---------------------------------------------------------------------------
# shared: v1-style sleeves + regimes (needed by ensemble/forensics/synthesis)
# ---------------------------------------------------------------------------

_SLEEVE_CACHE = os.path.join(RES, "sleeve_returns.csv")

def get_sleeves_and_regime(force: bool = False):
    from kronos.regime import walkforward_regimes
    px, ohlc, gk, src = get_data()
    mkt = px[CFG.market].pct_change().dropna()
    rg = walkforward_regimes(mkt, CFG)
    regime = rg["regime"]
    if not force and os.path.exists(_SLEEVE_CACHE):
        sleeves = pd.read_csv(_SLEEVE_CACHE, index_col=0, parse_dates=True)
    else:
        from kronos.backtest import sleeve_backtests
        sl = sleeve_backtests(px, regime, CFG)
        sleeves = pd.DataFrame(sl)
        sa_path = os.path.join(RES, "statarb_returns.csv")
        if os.path.exists(sa_path):
            sa = pd.read_csv(sa_path, index_col=0, parse_dates=True).iloc[:, 0]
            sleeves["statarb"] = sa.reindex(sleeves.index).fillna(0.0)
        sleeves.to_csv(_SLEEVE_CACHE)
    return px, regime, sleeves, rg


# ---------------------------------------------------------------------------
# Experiment 6: min-CVaR bake-off (Q5b)
# ---------------------------------------------------------------------------

def exp_cvar(force: bool = False) -> dict:
    if not force and (c := load_cached("cvar")):
        print("[cvar] cached")
        return c
    from kronos.cvar_opt import cvar_bakeoff

    px, regime, sleeves, rg = get_sleeves_and_regime()
    rets = px.pct_change().fillna(0.0).iloc[1:]
    t0 = time.time()
    out = cvar_bakeoff(rets, regime, CFG)
    print("[cvar] " + " | ".join(
        f"{e}: SR {v['sharpe']:.2f} CVaR {v['cvar95']:.2%} DD {v['max_dd']:.0%}"
        for e, v in out.items()) + f" ({time.time()-t0:.0f}s)")
    save("cvar", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 7: online ensemble vs regime gates (Q4)
# ---------------------------------------------------------------------------

def exp_ensemble(force: bool = False) -> dict:
    if not force and (c := load_cached("ensemble")):
        print("[ensemble] cached")
        return c
    from config import REGIME_STRATEGY_WEIGHTS
    from kronos.ensemble import gates_blend, run_meta

    px, regime, sleeves, rg = get_sleeves_and_regime()
    core = sleeves[["momentum", "mean_reversion", "low_vol"]].loc["2014-01-01":]
    t0 = time.time()

    methods = {}
    sr = lambda r: float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    eq = core.mean(axis=1)
    methods["equal_blend"] = {"sharpe": sr(eq)}
    gates = gates_blend(core, regime, REGIME_STRATEGY_WEIGHTS)
    methods["regime_gates"] = {"sharpe": sr(gates)}
    res_h = run_meta(core, "hedge")
    methods["hedge"] = {"sharpe": sr(res_h["returns"]), "eta": res_h["eta"]}
    res_fs = run_meta(core, "fixed_share")
    methods["fixed_share"] = {"sharpe": sr(res_fs["returns"])}
    res_rh = run_meta(core, "regime_hedge", regime=regime)
    methods["regime_hedge"] = {"sharpe": sr(res_rh["returns"])}

    best_static = max(sr(core[c]) for c in core.columns)
    out = {"methods": methods, "best_static_sharpe": best_static,
           "verdict": max(methods, key=lambda m: methods[m]["sharpe"]),
           "weights_river": {
               "dates": [str(d.date()) for d in res_fs["weights"].index[::5]],
               **{c: res_fs["weights"][c].iloc[::5].round(3).tolist()
                  for c in core.columns}},
           "regret": {"dates": [str(d.date()) for d in res_fs["regret"].index[::5]],
                      "fixed_share": res_fs["regret"].iloc[::5].round(2).tolist(),
                      "hedge": res_h["regret"].iloc[::5].round(2).tolist()}}
    print("[ensemble] " + " | ".join(f"{m}: SR {v['sharpe']:.2f}"
                                      for m, v in methods.items()) +
          f" | best static {best_static:.2f} -> verdict: {out['verdict']} "
          f"({time.time()-t0:.0f}s)")
    save("ensemble", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 8: overfitting forensics on the final strategy (Q6)
# ---------------------------------------------------------------------------

def exp_forensics(force: bool = False) -> dict:
    if not force and (c := load_cached("forensics")):
        print("[forensics] cached")
        return c
    from kronos.backtest import run_backtest
    from kronos.forensics import (
        bootstrap_equity_fan,
        bootstrap_sharpe_ci,
        build_variant_family,
        cscv_pbo,
        deflated_sharpe,
    )

    px, regime, sleeves, rg = get_sleeves_and_regime()
    t0 = time.time()

    # variant family: every blend/vol-target configuration we could have shipped
    fam, names = build_variant_family(sleeves.loc["2014-01-01":])
    pbo = cscv_pbo(fam, n_blocks=16)

    # the actual shipped strategy: v1 core + statarb overlay
    bt = run_backtest(px, regime, CFG)
    sa_path = os.path.join(RES, "statarb_returns.csv")
    sa = pd.read_csv(sa_path, index_col=0, parse_dates=True).iloc[:, 0] \
        if os.path.exists(sa_path) else pd.Series(0.0, index=px.index)
    net = (bt["net"] + 0.10 * sa.reindex(bt["net"].index).fillna(0.0)
           ).loc[bt["warmup_end"]:]

    # honest trial ledger
    trials = {
        "variant_family": fam.shape[1],
        "v1_manual_sweeps": 10,        # pairs(4) voltarget(2) hysteresis(2) kappa(2)
        "regime_models": 3, "k_sweep": 8, "sjm_lambda_grid": 6,
        "cvar_engines": 4, "ensemble_methods": 5, "vol_forecasters": 3,
        "design15_edge_variants": 2,   # fix-only + fix+lev1.5 (DESIGN15)
    }
    n_trials = int(sum(trials.values()))
    with open(os.path.join(RES, "trials.json"), "w") as f:
        json.dump(trials, f, indent=1)

    trial_srs = fam.mean(axis=0) / fam.std(axis=0)
    dsr = deflated_sharpe(net, n_trials=n_trials, trial_srs=trial_srs)
    ci = bootstrap_sharpe_ci(net)
    fan = bootstrap_equity_fan(net, n_boot=300)
    # decimate fan for payload
    step = max(1, len(fan["dates"]) // 400)
    fan_small = {k: (v[::step] if isinstance(v, list) else v)
                 for k, v in fan.items()}

    out = {"pbo": {k: v for k, v in pbo.items() if k != "logits"},
           "pbo_logits_hist": np.histogram(pbo["logits"], bins=30)[0].tolist(),
           "pbo_logits_edges": np.histogram(pbo["logits"], bins=30)[1].round(3).tolist(),
           "dsr": dsr, "bootstrap": ci, "fan": fan_small,
           "trials": trials, "n_trials": n_trials}
    print(f"[forensics] PBO={pbo['pbo']:.2f} | DSR={dsr['dsr']:.3f} "
          f"(SR {dsr['sr_annual']:.2f} vs SR0 {dsr['sr0_annual']:.2f}, "
          f"N={n_trials}) | bootstrap CI [{ci['ci_lo']:.2f},{ci['ci_hi']:.2f}] "
          f"({time.time()-t0:.0f}s)")
    save("forensics", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 9: final synthesis — KRONOS-X vs v1 vs SPY
# ---------------------------------------------------------------------------

def exp_synthesis(force: bool = False) -> dict:
    if not force and (c := load_cached("synthesis")):
        print("[synthesis] cached")
        return c
    from kronos.backtest import run_backtest
    from kronos.pairs import run_pairs_sleeve

    px, regime, sleeves, rg = get_sleeves_and_regime()
    mkt = px[CFG.market].pct_change().dropna()
    t0 = time.time()

    bt = run_backtest(px, regime, CFG)
    start = bt["warmup_end"]
    sa = pd.read_csv(os.path.join(RES, "statarb_returns.csv"),
                     index_col=0, parse_dates=True).iloc[:, 0]
    pares = run_pairs_sleeve(px, [], CFG)

    v1 = (bt["net"] + CFG.pairs_gross_sleeve * pares["returns"]).loc[start:]
    x = (bt["net"] + 0.10 * sa.reindex(bt["net"].index).fillna(0.0)).loc[start:]
    core = bt["net"].loc[start:]                  # no overlay at all
    spy = mkt.reindex(x.index).fillna(0.0)

    def stats(r, name):
        return {"name": name, **{k: v for k, v in M.summary(r, name).items()
                                 if k != "name"}}
    out = {"strategies": {
        "KRONOS-X": stats(x, "KRONOS-X"),
        "KRONOS v1": stats(v1, "KRONOS v1"),
        "Core (no overlay)": stats(core, "Core (no overlay)"),
        "SPY": stats(spy, "SPY"),
    }, "nav": {
        "dates": [str(d.date()) for d in x.index[::5]],
        "x": (1 + x).cumprod().iloc[::5].round(4).tolist(),
        "v1": (1 + v1).cumprod().iloc[::5].round(4).tolist(),
        "core": (1 + core).cumprod().iloc[::5].round(4).tolist(),
        "spy": (1 + spy).cumprod().iloc[::5].round(4).tolist(),
    }}
    print(f"[synthesis] X: SR {out['strategies']['KRONOS-X']['sharpe']:.2f} "
          f"DD {out['strategies']['KRONOS-X']['max_dd']:.0%} | "
          f"v1: SR {out['strategies']['KRONOS v1']['sharpe']:.2f} | "
          f"SPY: SR {out['strategies']['SPY']['sharpe']:.2f} "
          f"({time.time()-t0:.0f}s)")
    save("synthesis", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 10 (X²): regimes or fat tails?
# ---------------------------------------------------------------------------

def exp_tails(force: bool = False) -> dict:
    if not force and (c := load_cached("tails")):
        print("[tails] cached")
        return c
    from kronos.horserace import build_features_gk
    from kronos.tails import mc_khallucination, realdata_study

    t0 = time.time()
    mc = mc_khallucination(n_seeds=8)
    for w, rec in mc.items():
        if not isinstance(rec, dict):
            continue
        print(f"[tails] MC {w}: chosen-K gauss {rec['chosen_K']['gauss']} | "
              f"t {rec['chosen_K']['t']} | overfit frac "
              f"g={rec['frac_overfit']['gauss']:.0%} t={rec['frac_overfit']['t']:.0%}")
    print(f"[tails] Monte Carlo done in {time.time()-t0:.0f}s")

    px, ohlc, gk, src = get_data()
    mkt = px[CFG.market].pct_change().dropna()
    feats = build_features_gk(mkt, gk[CFG.market])
    hr = load_cached("horserace")
    sjm_lam = hr["sjm_lambda"]["lam"] if hr else 2.0

    t1 = time.time()
    real = realdata_study(feats, CFG, sjm_lam)
    print(f"[tails] real-data scores: {real['logscores_eval']}")
    print(f"[tails] market nus (K=3): {real['market_nus_K3']}")
    for k, v in real["ag"].items():
        print(f"[tails] AG {k}: stat={v['stat']:+.2f} p={v['p']:.4f}")
    print(f"[tails] MCS(10%): {real['mcs']['mcs']} (best: {real['mcs']['best']}) "
          f"({time.time()-t1:.0f}s)")

    out = {"mc": mc, "real": real}
    save("tails", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 11 (X²): does roughness forecast? (vol lab v2)
# ---------------------------------------------------------------------------

def exp_rfsv(force: bool = False) -> dict:
    if not force and (c := load_cached("rfsv")):
        print("[rfsv] cached")
        return c
    from kronos.infer import amisano_giacomini, model_confidence_set
    from kronos.rfsv import RFSV, walkforward_rfsv
    from kronos.vollab import qlike, walkforward_vol_forecasts

    px, ohlc, gk, src = get_data()
    r = px[CFG.market].pct_change().dropna()
    gkv = gk[CFG.market].dropna()
    t0 = time.time()

    fc = walkforward_vol_forecasts(r, gkv, min_train=750, refit_every=21)
    fc["rfsv"] = walkforward_rfsv(gkv, min_train=750, refit_every=21)
    oos = fc.dropna()
    models = ["ewma", "har", "garch", "rfsv"]
    losses = {m: qlike(oos["rv"].to_numpy(), oos[m].to_numpy()) for m in models}
    table = {m: float(np.mean(L)) for m, L in losses.items()}
    winner = min(table, key=table.get)

    ag = {}
    for a, b in (("rfsv", "har"), ("rfsv", "ewma"), ("rfsv", "garch")):
        # negative losses as scores: positive AG stat favors a
        ag[f"{a}_vs_{b}"] = amisano_giacomini(-losses[a], -losses[b])

    Lmat = np.column_stack([losses[m] for m in models])
    mcs = model_confidence_set(Lmat, models, alpha=0.10, n_boot=1000)

    # final-window kernel diagnostics
    m_final = RFSV().fit(gkv.to_numpy())
    out = {"qlike": table, "winner": winner, "ag": ag, "mcs": mcs,
           "kernel": {"H": m_final.H_, "halflife": m_final.halflife_,
                      "calib_b": m_final.b_},
           "n_oos_days": len(oos)}
    print(f"[rfsv] QLIKE: { {k: round(v, 4) for k, v in table.items()} } "
          f"winner={winner}")
    for k, v in ag.items():
        print(f"[rfsv] AG {k}: stat={v['stat']:+.2f} p={v['p']:.4f}")
    print(f"[rfsv] vol MCS(10%): {mcs['mcs']} | kernel H={m_final.H_:.2f} "
          f"hl={m_final.halflife_} b={m_final.b_:.2f} ({time.time()-t0:.0f}s)")
    save("rfsv", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 12 (LAWS): invariance screens L1-L3
# ---------------------------------------------------------------------------

def exp_laws(force: bool = False) -> dict:
    if not force and (c := load_cached("laws")):
        print("[laws] cached")
        return c
    from kronos.laws import (
        kurtosis_law,
        mrw_lambda2,
        standardized_returns,
        tail_report,
        universality_collapse,
    )
    from kronos.regime import GaussianHMM
    from kronos.tails import generic_walkforward
    from kronos.thmm import StudentTHMM

    px, ohlc, gk, src = get_data()
    close = ohlc["close"]
    t0 = time.time()

    # ---- L1: deformation kills the tails -----------------------------------
    smooth_grid = [1, 3, 5, 10]
    l1 = {"smooth_curve": {}, "per_asset": {}}
    raw_kurts, z_kurts, raw_nus, z_nus = [], [], [], []
    z_best = None
    for sm in smooth_grid:
        z = standardized_returns(close, gk, smooth=sm)
        kurts = [tail_report(z[c])["kurt"] for c in z.columns]
        l1["smooth_curve"][sm] = float(np.median(kurts))
    best_sm = min(l1["smooth_curve"], key=l1["smooth_curve"].get)
    z_best = standardized_returns(close, gk, smooth=best_sm)
    for c in close.columns:
        r = np.log(close[c] / close[c].shift(1)).dropna()
        rr, zr = tail_report(r), tail_report(z_best[c])
        l1["per_asset"][c] = {"kurt_raw": rr["kurt"], "kurt_z": zr["kurt"],
                              "nu_raw": rr["nu"], "nu_z": zr["nu"]}
        raw_kurts.append(rr["kurt"]); z_kurts.append(zr["kurt"])
        raw_nus.append(rr["nu"]); z_nus.append(zr["nu"])
    l1["best_smooth"] = best_sm
    l1["median_kurt_raw"] = float(np.median(raw_kurts))
    l1["median_kurt_z"] = float(np.median(z_kurts))
    l1["median_nu_raw"] = float(np.median(raw_nus))
    l1["median_nu_z"] = float(np.median(z_nus))
    l1["collapse"] = universality_collapse(z_best)
    print(f"[laws] L1: median kurt {l1['median_kurt_raw']:.1f} -> "
          f"{l1['median_kurt_z']:.2f} (smooth={best_sm}) | nu {l1['median_nu_raw']:.1f} "
          f"-> {l1['median_nu_z']:.0f} | KS cross/within ratio "
          f"{l1['collapse']['ratio']:.2f}")

    # ---- P1b: do the hallucinated regimes die with the tails? --------------
    z_spy = z_best[CFG.market].dropna()
    rv_z = z_spy.rolling(10).std()
    feats_z = pd.DataFrame({"ret": z_spy,
                            "logvol": np.log(rv_z.clip(lower=1e-3))}).dropna()
    Xz = feats_z.to_numpy()
    kcurve_z = {}
    for K in (2, 3, 4, 5):
        def mk(first, K=K):
            return GaussianHMM(K, 200 if first else 25, 1e-6, CFG.seed)
        ld = generic_walkforward(mk, Xz, CFG.hmm_min_train, CFG.hmm_refit_every)
        s = pd.Series(ld, index=feats_z.index).loc["2019-01-01":].dropna()
        kcurve_z[K] = float(s.mean())
    tm_z = StudentTHMM(3, seed=CFG.seed).fit(Xz)
    l1["kcurve_z"] = kcurve_z
    l1["nus_z_hmm"] = np.round(tm_z.nus_, 1).tolist()
    rise_raw = 3.1888 - 3.1689            # G5-G3 on raw features (cached fact)
    rise_z = kcurve_z[5] - kcurve_z[3]
    l1["k_rise_raw"] = rise_raw
    l1["k_rise_z"] = float(rise_z)
    print(f"[laws] P1b: Gaussian K-rise(3->5) raw {rise_raw:+.4f} vs deformed "
          f"{rise_z:+.4f} | t-HMM nus on z: {l1['nus_z_hmm']}")

    # ---- L2: parameter-free kurtosis law ------------------------------------
    l2 = {"per_asset": {}}
    preds, reals = [], []
    for c in close.columns:
        res = kurtosis_law(close[c], gk[c])
        l2["per_asset"][c] = res
        preds.append(res["kurt_pred"]); reals.append(res["kurt_real"])
    preds, reals = np.array(preds), np.array(reals)
    finite = np.isfinite(preds) & np.isfinite(reals)
    corr = float(np.corrcoef(np.log(preds[finite]), np.log(reals[finite]))[0, 1])
    slope, *_ = np.linalg.lstsq(
        np.column_stack([np.ones(finite.sum()), np.log(preds[finite])]),
        np.log(reals[finite]), rcond=None)
    l2["log_corr"] = corr
    l2["log_slope"] = float(slope[1])
    l2["median_excess"] = float(np.median(reals[finite] - preds[finite]))
    print(f"[laws] L2: log-corr(pred,real kurt) = {corr:.2f}, slope {slope[1]:.2f}, "
          f"median jump excess {l2['median_excess']:+.1f}")

    # ---- L3: multifractal universality --------------------------------------
    lams = {}
    for c in close.columns:
        try:
            lams[c] = mrw_lambda2(close[c])["lambda2"]
        except Exception:
            continue
    lv = np.array(list(lams.values()))
    l3 = {"per_asset": lams, "median": float(np.median(lv)),
          "iqr": [float(np.percentile(lv, 25)), float(np.percentile(lv, 75))],
          "rel_spread": float((np.percentile(lv, 75) - np.percentile(lv, 25))
                              / max(np.median(lv), 1e-9))}
    print(f"[laws] L3: lambda2 median {l3['median']:.3f} "
          f"IQR [{l3['iqr'][0]:.3f},{l3['iqr'][1]:.3f}] rel spread {l3['rel_spread']:.2f}")

    out = {"l1": l1, "l2": l2, "l3": l3}
    print(f"[laws] all screens in {time.time()-t0:.0f}s")
    save("laws", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 13 (CLOCK): is systemic tail risk just correlated clocks?
# ---------------------------------------------------------------------------

EQUITIES = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "BAC",
            "GS", "UNH", "JNJ", "PFE", "XOM", "CVX", "CAT", "HON", "BA",
            "WMT", "PG", "KO", "PEP", "MCD", "HD", "DIS", "NFLX", "CRM",
            "ADBE", "INTC", "CSCO", "ORCL", "T", "VZ", "NEE", "DUK", "LIN",
            "FDX", "UPS"]


def exp_clock(force: bool = False) -> dict:
    if not force and (c := load_cached("clock")):
        print("[clock] cached")
        return c
    from kronos.clock import (
        GaussianNull,
        clock_commonality,
        market_clock_deformation,
        pair_tail_study,
    )
    from kronos.laws import mrw_lambda2, standardized_returns

    px, ohlc, gk, src = get_data()
    close = ohlc["close"]
    t0 = time.time()

    r_raw = np.log(close / close.shift(1))
    z_same = standardized_returns(close, gk, smooth=1, lag=0)
    z_lag = standardized_returns(close, gk, smooth=5, lag=1)

    T = len(r_raw.dropna(how="all"))
    null = GaussianNull(T, n_sims=400)

    out = {"versions": {}}
    eq_cols = [c for c in EQUITIES if c in close.columns]
    for name, df in (("raw", r_raw), ("same_day", z_same), ("lagged", z_lag)):
        full = pair_tail_study(df.dropna(how="all"), null)
        eq = pair_tail_study(df[eq_cols].dropna(how="all"), null)
        out["versions"][name] = {"all": full, "equities": eq}
        print(f"[clock] {name:9s}: all-pairs frac>95 q5 "
              f"{full['q50']['frac_above95']:.0%} (excess {full['q50']['median_excess']:+.3f}) | "
              f"equities {eq['q50']['frac_above95']:.0%} | "
              f"asym>95 {full['asym_frac_above95']:.0%}")

    # C1: multifractality after deformation
    lam_raw, lam_z = [], []
    zb = z_same
    for c in close.columns:
        try:
            lam_raw.append(mrw_lambda2(close[c])["lambda2"])
            zc = zb[c].dropna()
            fake = pd.Series(100 * np.exp(np.cumsum(zc.to_numpy() * 0.01)),
                             index=zc.index)
            lam_z.append(mrw_lambda2(fake)["lambda2"])
        except Exception:
            continue
    out["c1"] = {"lambda2_raw_median": float(np.median(lam_raw)),
                 "lambda2_z_median": float(np.median(lam_z)),
                 "ratio": float(np.median(lam_z) / max(np.median(lam_raw), 1e-9))}
    print(f"[clock] C1: lambda2 raw {out['c1']['lambda2_raw_median']:.3f} -> "
          f"deformed {out['c1']['lambda2_z_median']:.3f} "
          f"(ratio {out['c1']['ratio']:.2f})")

    # C3: how common is the clock?
    out["c3"] = clock_commonality(gk)
    mc = market_clock_deformation(close, gk, CFG.market)
    eq_kurt_drop, noneq_kurt_drop = [], []
    for c, rec in mc.items():
        if c == CFG.market:
            continue
        drop_mkt = rec["kurt_raw"] - rec["kurt_mktclock"]
        drop_own = rec["kurt_raw"] - rec["kurt_ownclock"]
        share = drop_mkt / drop_own if drop_own > 0.5 else np.nan
        (eq_kurt_drop if c in eq_cols else noneq_kurt_drop).append(share)
    out["c3"]["mkt_clock_share_equities"] = float(np.nanmedian(eq_kurt_drop))
    out["c3"]["mkt_clock_share_other"] = float(np.nanmedian(noneq_kurt_drop))
    print(f"[clock] C3: vol-clock eig1 share {out['c3']['eig1_share']:.0%} | "
          f"market clock explains {out['c3']['mkt_clock_share_equities']:.0%} of equity "
          f"kurtosis removal vs {out['c3']['mkt_clock_share_other']:.0%} for non-equity "
          f"({time.time()-t0:.0f}s)")
    save("clock", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 14 (SURGE): the structure of common volatility surprises
# ---------------------------------------------------------------------------

def exp_surge(force: bool = False) -> dict:
    if not force and (c := load_cached("surge")):
        print("[surge] cached")
        return c
    from kronos.surge import cascade_report, leverage_kernel, surge_intensity_lift, zumbach_with_ci

    px, ohlc, gk, src = get_data()
    close = ohlc["close"]
    rets = np.log(close / close.shift(1))
    t0 = time.time()

    # ---- S1: does the clock have a clock? -----------------------------------
    s1_assets = {}
    for c in close.columns:
        s1_assets[c] = cascade_report(gk[c].dropna())
    med = lambda k: float(np.median([v[k] for v in s1_assets.values()]))
    s1 = {"spy": cascade_report(gk[CFG.market].dropna()),
          "median_kurt_u": med("kurt_u"), "median_ac1": med("ac1_absu"),
          "median_kurt_z2": med("kurt_z2")}
    print(f"[surge] S1: clock innovations kurt {s1['median_kurt_u']:.1f} "
          f"(SPY {s1['spy']['kurt_u']:.1f}) | AC1(|u|) {s1['median_ac1']:+.2f} | "
          f"after meta-deformation {s1['median_kurt_z2']:.2f}")

    # ---- S2: the arrow of time -----------------------------------------------
    vcent = {c: gk[c].rolling(5, center=True).mean() for c in close.columns}
    s2_assets = {}
    n_pos = 0
    for c in close.columns:
        z = zumbach_with_ci(rets[c], vcent[c], n_boot=200)
        s2_assets[c] = z
        n_pos += int(z["ci_lo"] > 0)
    zvals = [v["z"] for v in s2_assets.values()]
    s2 = {"median_z": float(np.median(zvals)),
          "frac_significant_pos": n_pos / len(s2_assets),
          "per_asset": {c: {k: round(v2, 3) for k, v2 in v.items()}
                        for c, v in s2_assets.items()},
          "kernels": {c: leverage_kernel(rets[c], vcent[c], 40)
                      for c in (CFG.market, "GLD", "TLT", "AAPL")},
          }
    s2["lev10"] = {c: float(np.mean(k[:10])) for c, k in s2["kernels"].items()}
    print(f"[surge] S2: median Zumbach Z {s2['median_z']:+.2f}, "
          f"{s2['frac_significant_pos']:.0%} of assets CI>0 | "
          f"leverage L(1..10): SPY {s2['lev10'][CFG.market]:+.3f}, "
          f"GLD {s2['lev10']['GLD']:+.3f}, TLT {s2['lev10']['TLT']:+.3f}")

    # ---- S3: surge-intensity forecastability ---------------------------------
    s3 = surge_intensity_lift(rets.iloc[1:], gk[CFG.market], n_boot=300)
    print(f"[surge] S3: joint-tail lift T3/T1 = {s3['lift']:.2f} "
          f"CI[{s3['ci_lo']:.2f},{s3['ci_hi']:.2f}] "
          f"(freq {s3['freq_t1']:.3f} -> {s3['freq_t3']:.3f}, "
          f"base {s3['base_rate']:.3f}) ({time.time()-t0:.0f}s)")

    out = {"s1": s1, "s2": {k: v for k, v in s2.items() if k != "per_asset"},
           "s2_per_asset": s2["per_asset"], "s3": s3}
    save("surge", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 15 (BITS): the information budget of the market
# ---------------------------------------------------------------------------

def exp_bits(force: bool = False) -> dict:
    if not force and (c := load_cached("bits")):
        print("[bits] cached")
        return c
    from kronos.infobudget import (
        LN2,
        binary_sharpe_ceiling,
        bits_consumed_by,
        causal_features,
        direction_bits,
        gaussian_sharpe_ceiling,
        ksg_mi_net,
    )

    px, ohlc, gk, src = get_data()
    close = ohlc["close"]
    _, regime, _, _ = get_sleeves_and_regime()
    t0 = time.time()

    def asset_direction(c, horizon=1, era=None):
        r = np.log(close[c] / close[c].shift(1)).dropna()
        if era == "pre":
            r = r.loc[:"2017-12-31"]
        elif era == "post":
            r = r.loc["2018-01-01":]
        feats = causal_features(r, gk[c].reindex(r.index),
                                regime if c == CFG.market else None)
        fwd = np.sign(r.rolling(horizon).sum().shift(-horizon))
        return direction_bits(feats, fwd.rename("y"), n_shuffle=200)

    # ---- direction channel ---------------------------------------------------
    dir_res = {}
    for h in (1, 5, 21):
        dir_res[h] = asset_direction(CFG.market, h)
    # cross-asset at h=1
    per_asset = {}
    n_sig = 0
    for c in close.columns:
        d = asset_direction(c, 1)
        per_asset[c] = {"bits_net": round(d["bits_net"], 5),
                        "sig": d["significant"]}
        n_sig += int(d["significant"])
    med_dir = float(np.median([v["bits_net"] for v in per_asset.values()]))
    print(f"[bits] direction (SPY): h=1 {dir_res[1]['bits_net']:.5f} bits "
          f"(sig={dir_res[1]['significant']}), h=5 {dir_res[5]['bits_net']:.5f}, "
          f"h=21 {dir_res[21]['bits_net']:.5f}")
    print(f"[bits] direction cross-asset: median {med_dir:.5f} bits, "
          f"{n_sig}/{len(per_asset)} significant at 5%")

    # ---- magnitude channel -----------------------------------------------------
    def asset_magnitude(c, era=None):
        v = gk[c].dropna()
        if era == "pre":
            v = v.loc[:"2017-12-31"]
        elif era == "post":
            v = v.loc["2018-01-01":]
        lv = 0.5 * np.log(v.rolling(5).mean())
        dlv = lv.diff()
        target = np.log(v.shift(-1))
        df = pd.concat([lv, dlv, target], axis=1).dropna().to_numpy()
        return ksg_mi_net(df[:, :2], df[:, 2], n_shuffle=5)

    mag_spy = asset_magnitude(CFG.market)
    mag_assets = {}
    for c in list(close.columns)[::4]:          # representative subsample
        mag_assets[c] = asset_magnitude(c)["mi_nats"]
    med_mag = float(np.median(list(mag_assets.values())))
    print(f"[bits] magnitude (SPY): {mag_spy['mi_nats']:.3f} nats = "
          f"{mag_spy['mi_nats']/LN2:.3f} bits/day | cross-asset median "
          f"{med_mag/LN2:.3f} bits")

    # ---- total return bits + era stability --------------------------------------
    r_spy = np.log(close[CFG.market] / close[CFG.market].shift(1)).dropna()
    lv_spy = 0.5 * np.log(gk[CFG.market].rolling(5).mean())
    dft = pd.concat([r_spy, lv_spy, r_spy.shift(-1)], axis=1,
                    sort=False).dropna().to_numpy()
    total = ksg_mi_net(dft[:, :2], dft[:, 2], n_shuffle=5)
    eras = {"pre": asset_magnitude(CFG.market, "pre")["mi_nats"] / LN2,
            "post": asset_magnitude(CFG.market, "post")["mi_nats"] / LN2}
    dir_eras = {e: asset_direction(CFG.market, 1, e)["bits_net"]
                for e in ("pre", "post")}
    print(f"[bits] total return bits (SPY): {total['mi_nats']/LN2:.4f} | "
          f"magnitude era pre {eras['pre']:.3f} vs post {eras['post']:.3f} | "
          f"direction era pre {dir_eras['pre']:.5f} vs post {dir_eras['post']:.5f}")

    # ---- ceilings + utilization -------------------------------------------------
    ceil_dir = binary_sharpe_ceiling(dir_res[1]["bits_net"])
    ceil_total = gaussian_sharpe_ceiling(total["mi_nats"])
    ceil_mag = gaussian_sharpe_ceiling(mag_spy["mi_nats"])
    syn = load_cached("synthesis")
    sr_real = syn["strategies"]["Core (no overlay)"]["sharpe"] if syn else 0.95
    used = bits_consumed_by(sr_real)
    print(f"[bits] ceilings: direction-only {ceil_dir:.2f} SR | return-channel "
          f"{ceil_total:.2f} SR | vol-channel {ceil_mag:.2f} SR-equivalent")
    print(f"[bits] KRONOS uses {used:.4f} bits/day "
          f"(realized SR {sr_real:.2f}) ({time.time()-t0:.0f}s)")

    out = {"direction": {str(h): {k: v for k, v in dir_res[h].items()}
                         for h in dir_res},
           "direction_cross": {"median_bits": med_dir, "n_sig": n_sig,
                               "n_assets": len(per_asset),
                               "per_asset": per_asset},
           "magnitude": {"spy_bits": mag_spy["mi_nats"] / LN2,
                         "spy_nats": mag_spy["mi_nats"],
                         "cross_median_bits": med_mag / LN2},
           "total_bits": total["mi_nats"] / LN2,
           "eras": {"magnitude": eras, "direction": dir_eras},
           "ceilings": {"direction_sr": ceil_dir, "total_sr": ceil_total,
                        "vol_channel_sr": ceil_mag},
           "utilization": {"kronos_bits": used, "kronos_sr": sr_real}}
    save("bits", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 16 (ARROW): entropy production — where does time's arrow live?
# ---------------------------------------------------------------------------

def exp_arrow(force: bool = False) -> dict:
    if not force and (c := load_cached("arrow")):
        print("[arrow] cached")
        return c
    from kronos.entropyprod import ep_with_null
    from kronos.laws import standardized_returns
    from kronos.surge import clock_innovations

    px, ohlc, gk, src = get_data()
    close = ohlc["close"]
    t0 = time.time()

    rets = np.log(close / close.shift(1))
    z = standardized_returns(close, gk, smooth=1)

    out = {"per_asset": {}}
    counts = {"returns": 0, "clock": 0, "deformed": 0}
    eps = {"returns": [], "clock": [], "deformed": []}
    for c in close.columns:
        rec = {}
        r_ep = ep_with_null(rets[c].dropna().to_numpy(), n=3, n_null=150)
        u = clock_innovations(gk[c].dropna())        # weekly: kills proxy noise
        u_ep = ep_with_null(u, n=3, n_null=150, block=26)
        z_ep = ep_with_null(z[c].dropna().to_numpy(), n=3, n_null=150)
        for name, e in (("returns", r_ep), ("clock", u_ep), ("deformed", z_ep)):
            rec[name] = {"ep": round(e["ep_bits"], 5),
                         "net": round(e["ep_net"], 5), "sig": e["significant"]}
            counts[name] += int(e["significant"])
            eps[name].append(e["ep_net"])
        out["per_asset"][c] = rec
    n = len(out["per_asset"])
    out["summary"] = {k: {"n_sig": counts[k], "n": n,
                          "median_net_bits": float(np.median(eps[k]))}
                      for k in counts}
    out["spy"] = out["per_asset"][CFG.market]
    print(f"[arrow] returns : {counts['returns']}/{n} significant, "
          f"median net {out['summary']['returns']['median_net_bits']:.5f} bits")
    print(f"[arrow] clock   : {counts['clock']}/{n} significant, "
          f"median net {out['summary']['clock']['median_net_bits']:.5f} bits")
    print(f"[arrow] deformed: {counts['deformed']}/{n} significant, "
          f"median net {out['summary']['deformed']['median_net_bits']:.5f} bits")
    print(f"[arrow] SPY: returns {out['spy']['returns']['ep']:.5f} "
          f"(sig={out['spy']['returns']['sig']}) | clock {out['spy']['clock']['ep']:.5f} "
          f"(sig={out['spy']['clock']['sig']}) ({time.time()-t0:.0f}s)")
    save("arrow", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 17 (DECATHLON): the minimal market vs the ten-event battery
# ---------------------------------------------------------------------------

def exp_decathlon(force: bool = False) -> dict:
    if not force and (c := load_cached("decathlon")):
        print("[decathlon] cached")
        return c
    from kronos.decathlon import battery, run_decathlon

    px, ohlc, gk, src = get_data()
    t0 = time.time()
    spy = battery(px[CFG.market].pct_change().dropna())
    table = run_decathlon(n_seeds=8, T=6000)
    out = {"spy": {"score": spy["score"], "events": spy["events"],
                   "stats": {k: round(float(v), 4) for k, v in spy["stats"].items()
                             if isinstance(v, (int, float, np.floating))}},
           "configs": table}
    for name, rec in table.items():
        passes = [k for k, v in rec["events"].items() if v]
        print(f"[decathlon] {name:6s}: {rec['score']}/10  ({', '.join(p.split('_')[0] for p in passes)})")
    print(f"[decathlon] SPY reference: {spy['score']}/10 ({time.time()-t0:.0f}s)")
    save("decathlon", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 18 (CRITICAL): are crashes critical transitions or shocks?
# ---------------------------------------------------------------------------

_ASSET_CLASS = {}
for _c in EQUITIES:
    _ASSET_CLASS[_c] = "equity"
for _c in ("SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "XLU"):
    _ASSET_CLASS[_c] = "equity_index"
for _c in ("TLT", "LQD", "HYG"):
    _ASSET_CLASS[_c] = "bond"
_ASSET_CLASS["GLD"] = "gold"


def exp_critical(force: bool = False) -> dict:
    if not force and (c := load_cached("critical")):
        print("[critical] cached")
        return c
    from kronos.critical import (
        bootstrap_auc_gain,
        crash_labels,
        ews_indicators,
        stratified_lift,
        walkforward_incremental_auc,
    )

    px, ohlc, gk, src = get_data()
    close = ohlc["close"]
    t0 = time.time()

    # EWS features are H-independent; cache per asset to sweep horizons cheaply
    _fcache = {}
    def get_feats(c):
        if c not in _fcache:
            cl = close[c].dropna()
            r = np.log(cl / cl.shift(1))
            state = (0.5 * np.log(gk[c].clip(lower=1e-12))).rolling(5).mean()
            _fcache[c] = (cl, ews_indicators(state.reindex(r.index), r, L=60))
        return _fcache[c]

    def asset_gain(c, lower=True, H=20):
        cl, feats = get_feats(c)
        lab = crash_labels(cl, H=H, q=0.05, lower=lower)
        res = walkforward_incremental_auc(feats, lab, refit_every=252,
                                          min_train=756, embargo=H)
        if not np.isfinite(res["auc_vol"]) or res["n_pos"] < 30:
            return None
        return {"auc_vol": res["auc_vol"], "auc_all": res["auc_all"],
                "gain": res["auc_all"] - res["auc_vol"], "res": res,
                "feats": feats, "lab": lab}

    # per-asset down-crash gains
    per_asset = {}
    for c in close.columns:
        g = asset_gain(c, lower=True)
        if g is None:
            continue
        per_asset[c] = {"auc_vol": round(g["auc_vol"], 3),
                        "auc_all": round(g["auc_all"], 3),
                        "gain": round(g["gain"], 4),
                        "cls": _ASSET_CLASS.get(c, "equity")}
    gains = np.array([v["gain"] for v in per_asset.values()])
    print(f"[critical] {len(per_asset)} assets | median down-crash AUC gain "
          f"{np.median(gains):+.4f} | frac>0 {np.mean(gains > 0):.0%}")

    # cluster bootstrap over EQUITY assets for the mean gain
    eq = [v["gain"] for c, v in per_asset.items() if v["cls"] == "equity"]
    rng = np.random.default_rng(0)
    boot = [np.mean(rng.choice(eq, len(eq), replace=True)) for _ in range(2000)]
    eq_ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
    print(f"[critical] equity mean gain {np.mean(eq):+.4f} "
          f"CI[{eq_ci[0]:+.4f},{eq_ci[1]:+.4f}] (cluster bootstrap, n={len(eq)})")

    # SPY headline with block-bootstrap CI
    g_spy = asset_gain(CFG.market, lower=True)
    spy_boot = bootstrap_auc_gain(g_spy["res"]["pred_vol"], g_spy["res"]["pred_all"],
                                  g_spy["res"]["labels"], n_boot=500)
    strat = stratified_lift(g_spy["feats"], g_spy["lab"], signal="phi")
    print(f"[critical] SPY: gain {spy_boot['gain']:+.4f} "
          f"CI[{spy_boot['ci_lo']:+.4f},{spy_boot['ci_hi']:+.4f}] | "
          f"mid-vol phi lift {strat['lift']:.2f}")

    # asset-class universality
    classes = {}
    for cls in ("equity", "equity_index", "bond", "gold"):
        cg = [v["gain"] for v in per_asset.values() if v["cls"] == cls]
        if cg:
            classes[cls] = {"median_gain": float(np.median(cg)),
                            "frac_pos": float(np.mean(np.array(cg) > 0)),
                            "n": len(cg)}
    for cls, rec in classes.items():
        print(f"[critical]   {cls:13s}: median gain {rec['median_gain']:+.4f} "
              f"(frac>0 {rec['frac_pos']:.0%}, n={rec['n']})")

    # down vs up asymmetry (pooled equity median)
    up_gains = []
    for c in [k for k, v in per_asset.items() if v["cls"] == "equity"]:
        gu = asset_gain(c, lower=False)
        if gu:
            up_gains.append(gu["gain"])
    print(f"[critical] asymmetry: equity median gain DOWN "
          f"{np.median(eq):+.4f} vs UP {np.median(up_gains):+.4f} "
          f"({time.time()-t0:.0f}s)")

    # horizon sweep: a real slowing-down signal should STRENGTHEN with H
    from scipy.stats import binomtest
    hsweep = {}
    for H in (10, 20, 60):
        hg = [asset_gain(c, lower=True, H=H) for c in
              [k for k, v in per_asset.items() if v["cls"] == "equity"]]
        hg = [g["gain"] for g in hg if g]
        hsweep[H] = {"median": float(np.median(hg)),
                     "frac_pos": float(np.mean(np.array(hg) > 0))}
    print("[critical] horizon sweep (equity median gain): " +
          " ".join(f"H={H}:{r['median']:+.4f}" for H, r in hsweep.items()))

    # sign test: is the per-asset gain distribution centered above 0?
    n_pos = int((gains > 0).sum())
    sign_p = float(binomtest(n_pos, len(gains), 0.5, alternative="greater").pvalue)

    # precursor effect size (true-null vs low-power): real equities vs the
    # known fold world. If real shifts ~0 while the fold shows large phi
    # shift, the null is real, not underpowered.
    from kronos.critical import CSD_FEATURES, jumps_to_labels, precursor_shift, simulate_fold_world
    eq_names = [k for k, v in per_asset.items() if v["cls"] == "equity"]
    shifts = {s: [] for s in CSD_FEATURES}
    for c in eq_names:
        cl, feats = get_feats(c)
        lab = crash_labels(cl, H=20, q=0.05, lower=True)
        ps = precursor_shift(feats, lab, W=20)
        for s in CSD_FEATURES:
            shifts[s].append(ps[s])
    real_shift = {s: float(np.median(v)) for s, v in shifts.items()}
    fw = simulate_fold_world(8000, seed=1)
    fx = pd.Series(fw["x"]); fdx = fx.diff().fillna(0)
    ffeats = ews_indicators(fx, fdx, L=60)
    flab = pd.Series(jumps_to_labels(fw["jumps"], H=20), index=fx.index)
    fold_shift = precursor_shift(ffeats, flab, W=20)
    # gate-summary for the dashboard credibility anchor (method convicts a
    # known fold, exonerates a known shock)
    from kronos.critical import simulate_shock_world
    f_res = walkforward_incremental_auc(ffeats, flab, refit_every=500, min_train=1500)
    sw = simulate_shock_world(8000, seed=2)
    sx = pd.Series(sw["x"]); sdx = sx.diff().fillna(0)
    s_res = walkforward_incremental_auc(
        ews_indicators(sx, sdx, L=60),
        pd.Series(jumps_to_labels(sw["jumps"], H=20), index=sx.index),
        refit_every=500, min_train=1500)
    gate_summary = {"fold_gain": round(f_res["auc_all"] - f_res["auc_vol"], 3),
                    "shock_gain": round(s_res["auc_all"] - s_res["auc_vol"], 3)}
    print("[critical] precursor shift (std units, real equity median | fold):")
    for s in CSD_FEATURES:
        print(f"[critical]   {s:10s} real {real_shift[s]:+.3f} | fold {fold_shift[s]:+.3f}")

    # honest verdict: median-null + sign-test-null => shock-dominated
    if sign_p < 0.05 and eq_ci[0] > 0.002:
        verdict = "critical_transition"
    elif eq_ci[0] > 0 and sign_p < 0.20:
        verdict = "weak_transition"
    else:
        verdict = "shock_dominated"
    out = {"verdict": verdict, "per_asset": per_asset,
           "equity_mean_gain": float(np.mean(eq)), "equity_ci": eq_ci,
           "median_gain": float(np.median(gains)),
           "frac_pos": float(np.mean(gains > 0)), "sign_test_p": sign_p,
           "spy": {"gain": spy_boot["gain"], "ci": [spy_boot["ci_lo"], spy_boot["ci_hi"]],
                   "auc_vol": g_spy["auc_vol"], "auc_all": g_spy["auc_all"],
                   "phi_lift_midvol": strat["lift"]},
           "classes": classes, "hsweep": hsweep, "gate": gate_summary,
           "precursor": {"real": real_shift, "fold": fold_shift},
           "asymmetry": {"down": float(np.median(eq)), "up": float(np.median(up_gains))}}
    print(f"[critical] VERDICT: {verdict} (sign-test p={sign_p:.2f})")
    save("critical", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 19 (REFLEX): how endogenous is the market?
# ---------------------------------------------------------------------------

def exp_reflex(force: bool = False) -> dict:
    if not force and (c := load_cached("reflex")):
        print("[reflex] cached")
        return c
    from kronos.hawkes import (
        debias,
        exceedance_times,
        fit_hawkes,
        raw_and_deformed_events,
        recovery_curve,
    )

    px, ohlc, gk, src = get_data()
    close = ohlc["close"]
    t0 = time.time()

    curve = recovery_curve(n_rep=10, seed=0)
    print(f"[reflex] recovery curve: {{{', '.join(f'{k}:{v:.2f}' for k,v in curve.items())}}}")

    # F1/F2: raw vs deformed branching ratio per asset
    per_asset = {}
    for c in close.columns:
        ev = raw_and_deformed_events(close[c], gk[c], q=0.95)
        nr = fit_hawkes(ev["raw"], ev["T"], seed=0)["n"]
        nd = fit_hawkes(ev["deformed"], ev["T"], seed=0)["n"]
        per_asset[c] = {"n_raw": debias(nr, curve), "n_def": debias(nd, curve),
                        "cls": _ASSET_CLASS.get(c, "equity")}
    nr_all = np.array([v["n_raw"] for v in per_asset.values()])
    nd_all = np.array([v["n_def"] for v in per_asset.values()])
    med_raw, med_def = float(np.nanmedian(nr_all)), float(np.nanmedian(nd_all))
    # cluster bootstrap over assets for the median CIs
    rng = np.random.default_rng(0)
    br = [np.nanmedian(rng.choice(nr_all, len(nr_all))) for _ in range(2000)]
    bd = [np.nanmedian(rng.choice(nd_all, len(nd_all))) for _ in range(2000)]
    ci_raw = (float(np.percentile(br, 2.5)), float(np.percentile(br, 97.5)))
    ci_def = (float(np.percentile(bd, 2.5)), float(np.percentile(bd, 97.5)))
    # pure-stochastic-vol null (no self-excitation) for n_deformed reference
    from kronos.surge import simulate_reversible_world
    sv_nd = []
    for s in range(8):
        rsv, vsv = simulate_reversible_world(4000, seed=200 + s)
        csv = pd.Series(100 * np.exp(np.cumsum(rsv.to_numpy())), index=rsv.index)
        ev = raw_and_deformed_events(csv, vsv, q=0.95)
        sv_nd.append(debias(fit_hawkes(ev["deformed"], ev["T"], seed=0)["n"], curve))
    sv_null = float(np.nanmean(sv_nd))
    print(f"[reflex] F1/F2: median n_raw={med_raw:.3f} CI[{ci_raw[0]:.2f},{ci_raw[1]:.2f}] | "
          f"n_deformed={med_def:.3f} CI[{ci_def[0]:.2f},{ci_def[1]:.2f}] "
          f"| clustering share {1 - med_def/max(med_raw,1e-9):.0%}")
    print(f"[reflex] pure-SV-clustering null n_deformed={sv_null:.3f} "
          f"(real {med_def:.3f} is {'above' if med_def > sv_null else 'at'} the null)")

    # F3: did endogeneity grow? pre/post 2012
    def period_med(lo, hi):
        rr, dd = [], []
        for c in close.columns:
            sub = close[c].loc[lo:hi]
            gsub = gk[c].loc[lo:hi]
            if len(sub.dropna()) < 600:
                continue
            ev = raw_and_deformed_events(sub, gsub, q=0.95)
            rr.append(debias(fit_hawkes(ev["raw"], ev["T"], seed=0)["n"], curve))
            dd.append(debias(fit_hawkes(ev["deformed"], ev["T"], seed=0)["n"], curve))
        return float(np.nanmedian(rr)), float(np.nanmedian(dd))
    pre = period_med("2010-01-01", "2017-12-31")
    post = period_med("2018-01-01", "2026-12-31")
    print(f"[reflex] F3 trend: n_raw {pre[0]:.3f}->{post[0]:.3f} | "
          f"n_def {pre[1]:.3f}->{post[1]:.3f}")

    # F4: systemic (market-wide surprise) vs idiosyncratic
    r = np.log(close / close.shift(1))
    sig = np.sqrt(gk.rolling(5).mean().shift(1))
    z = (r / sig).abs()
    systemic = z.median(axis=1).dropna()          # cross-sectional surprise
    sys_ev = exceedance_times(systemic, 0.95)
    n_sys = debias(fit_hawkes(sys_ev, float(len(systemic)), seed=0)["n"], curve)
    print(f"[reflex] F4: systemic n={n_sys:.3f} vs median single-asset "
          f"n_def={med_def:.3f} (systemic {'MORE' if n_sys>med_def else 'less'} reflexive)")

    # F5: bridge to CRITICAL — does n_raw correlate with the CSD precursor?
    f5 = None
    crit = load_cached("critical")
    if crit and "per_asset" in crit:
        from kronos.critical import crash_labels, ews_indicators, precursor_shift
        xs, ys = [], []
        for c in [k for k in per_asset if per_asset[k]["cls"] == "equity"]:
            cl = close[c].dropna()
            rr = np.log(cl / cl.shift(1))
            state = (0.5 * np.log(gk[c].clip(lower=1e-12))).rolling(5).mean()
            feats = ews_indicators(state.reindex(rr.index), rr, L=60)
            lab = crash_labels(cl, H=20, q=0.05)
            ps = precursor_shift(feats, lab, W=20)
            xs.append(per_asset[c]["n_raw"]); ys.append(ps["phi"])
        rho = float(np.corrcoef(xs, ys)[0, 1])
        f5 = {"corr_nraw_phishift": rho, "n": len(xs)}
        print(f"[reflex] F5: corr(n_raw, CSD phi-shift) = {rho:+.2f} (n={len(xs)})")

    classes = {}
    for cls in ("equity", "equity_index", "bond", "gold"):
        cc = [(v["n_raw"], v["n_def"]) for v in per_asset.values() if v["cls"] == cls]
        if cc:
            classes[cls] = {"n_raw": float(np.nanmedian([x[0] for x in cc])),
                            "n_def": float(np.nanmedian([x[1] for x in cc]))}

    out = {"recovery_curve": {str(k): v for k, v in curve.items()},
           "median_n_raw": med_raw, "median_n_def": med_def,
           "ci_raw": ci_raw, "ci_def": ci_def, "sv_null_n_def": sv_null,
           "clustering_share": float(1 - med_def / max(med_raw, 1e-9)),
           "per_asset": {k: {"n_raw": round(v["n_raw"], 3),
                             "n_def": round(v["n_def"], 3), "cls": v["cls"]}
                         for k, v in per_asset.items()},
           "trend": {"pre": {"n_raw": pre[0], "n_def": pre[1]},
                     "post": {"n_raw": post[0], "n_def": post[1]}},
           "systemic": {"n": n_sys, "median_single": med_def},
           "classes": classes, "f5": f5,
           "spy": {"n_raw": per_asset[CFG.market]["n_raw"],
                   "n_def": per_asset[CFG.market]["n_def"]}}
    print(f"[reflex] done ({time.time()-t0:.0f}s)")
    save("reflex", out)
    return out


# ---------------------------------------------------------------------------
# Experiment 20 (CONSTANTS): which market laws are constant vs drifting?
# ---------------------------------------------------------------------------

def exp_constants(force: bool = False) -> dict:
    if not force and (c := load_cached("constants")):
        print("[constants] cached")
        return c
    from kronos.constants import (
        ERA_EDGES,
        classify,
        trend_test,
        variance_ratio_test,
        window_quantities,
    )
    from kronos.hawkes import recovery_curve

    px, ohlc, gk, src = get_data()
    close = ohlc["close"]
    t0 = time.time()
    curve = recovery_curve(n_rep=8, T=900.0, seed=0)   # T matched to window length

    eras = list(zip(ERA_EDGES[:-1], ERA_EDGES[1:]))
    centers = np.array([2010.0 + 3.25 * (i + 0.5) for i in range(len(eras))])
    per_window = [window_quantities(close, gk, lo, hi, curve) for lo, hi in eras]

    QUANTS = ["H", "kurt", "kurt_def", "leverage", "commonality", "n_raw", "n_def"]
    NAMES = {"H": "roughness H", "kurt": "fat tails (kurtosis)",
             "kurt_def": "one-clock kurtosis", "leverage": "leverage effect",
             "commonality": "clock commonality", "n_raw": "branching ratio (raw)",
             "n_def": "branching ratio (deformed)"}
    results = {}
    for q in QUANTS:
        means, sds, vals = [], [], []
        for w in per_window:
            est, sd = w[q]                       # (estimate, sampling SD)
            means.append(est); sds.append(sd); vals.append(round(est, 3))
        means, sds = np.array(means), np.array(sds)
        vr = variance_ratio_test(means, sds)
        tr = trend_test(centers, means, sds)
        cls = classify(vr, tr, centers[-1] - centers[0])
        results[q] = {"name": NAMES[q], "era_values": vals,
                      "VR": round(vr["VR"], 2) if np.isfinite(vr["VR"]) else None,
                      "p": round(vr["p"], 3) if np.isfinite(vr["p"]) else None,
                      "slope": round(tr["slope"], 4), "trend_ci": [round(x, 4) for x in tr["ci"]],
                      "class": cls}
        print(f"[constants] {NAMES[q]:26s} {cls:14s} VR={results[q]['VR']} "
              f"trend={tr['slope']:+.4f}/yr eras={vals}")

    out = {"eras": [f"{lo[:4]}-{hi[:4]}" for lo, hi in eras],
           "centers": centers.tolist(), "quantities": results}
    n_const = sum(1 for r in results.values() if r["class"] == "CONSTANT")
    print(f"[constants] {n_const}/{len(QUANTS)} laws CONSTANT ({time.time()-t0:.0f}s)")
    save("constants", out)
    return out


def exp_transfer(force: bool = False) -> dict:
    if not force and (c := load_cached("transfer")):
        print("[transfer] cached")
        return c
    from kronos.hawkes import recovery_curve
    from kronos.transfer import UNIVERSES, battery, frozen_system, load_universe, transfer_tests

    px, ohlc, gk, src = get_data()
    t0 = time.time()
    curve = recovery_curve(n_rep=8, T=float(len(px)), seed=0)

    bats = {"US": battery(ohlc["close"], gk, curve)}
    frozen = {"US": frozen_system(px, CFG.market, CFG)}
    sources = {"US": src}
    for name in UNIVERSES:
        u = load_universe(name, CFG.start, CFG.end, seed=CFG.seed)
        sources[name] = u["source"]
        print(f"[transfer] {name}: {u['close'].shape[1]} tickers x "
              f"{len(u['close'])} days ({u['source']})")
        bats[name] = battery(u["close"], u["gk"], curve)
        frozen[name] = frozen_system(u["close"], UNIVERSES[name]["market"], CFG)
        f = frozen[name]["net"]
        print(f"[transfer] {name}: frozen system Sharpe {f['sharpe']:.2f} "
              f"MaxDD {f['max_dd']:.1%} | index Sharpe "
              f"{frozen[name]['index']['sharpe']:.2f} "
              f"MaxDD {frozen[name]['index']['max_dd']:.1%}")

    rep = transfer_tests(bats, ref="US")
    n_tr = sum(1 for q in rep if rep[q]["class"] == "TRANSFERS")
    for q in rep:
        print(f"[transfer] {q:12s} {rep[q]['class']:17s} VR={rep[q]['VR']} "
              f"p={rep[q]['p']} values={rep[q]['values']}")

    tr1 = n_tr >= 5
    tr2a = all(frozen[n]["net"]["sharpe"] > 0 for n in UNIVERSES)
    tr2b = all(frozen[n]["net"]["max_dd"] >= frozen[n]["index"]["max_dd"]
               for n in UNIVERSES)  # max_dd is negative: >= means shallower
    print(f"[transfer] TR1 (>=5/7 laws transfer): {tr1} ({n_tr}/{len(rep)})")
    print(f"[transfer] TR2a (frozen Sharpe>0 everywhere): {tr2a} | "
          f"TR2b (frozen MaxDD shallower than index everywhere): {tr2b}")

    out = {"sources": sources, "laws": rep,
           "n_transfer": n_tr, "n_laws": len(rep),
           "frozen": frozen,
           "hypotheses": {"TR1": bool(tr1), "TR2a": bool(tr2a),
                          "TR2b": bool(tr2b)}}
    print(f"[transfer] done in {time.time()-t0:.0f}s")
    save("transfer", out)
    return out


def exp_crypto(force: bool = False) -> dict:
    if not force and (c := load_cached("crypto")):
        print("[crypto] cached")
        return c
    from kronos.crypto import (CRYPTO_UNIVERSE, leverage_contrast, load_crypto,
                               per_asset_leverage)
    from kronos.hawkes import recovery_curve
    from kronos.transfer import battery, transfer_tests

    # Equity cohort: reuse the EXACT batteries TRANSFER already reported, so the
    # two studies share one equity baseline. (Run `run_research.py transfer` first.)
    tj = load_cached("transfer")
    if tj is None:
        exp_transfer(force=False)
        tj = load_cached("transfer")
    eq_markets = list(tj["sources"].keys())          # US + 3 equity regions
    laws = tj["laws"]
    batteries = {m: {q: (laws[q]["values"][m], laws[q]["sds"][m])
                     for q in laws if m in laws[q]["values"]}
                 for m in eq_markets}

    t0 = time.time()
    cu = load_crypto()
    print(f"[crypto] {cu['close'].shape[1]} coins x {len(cu['close'])} days "
          f"({cu['source']}, {cu['close'].index[0].date()} -> "
          f"{cu['close'].index[-1].date()})")
    curve = recovery_curve(n_rep=8, T=float(len(cu["close"])), seed=0)
    batteries["crypto"] = battery(cu["close"], cu["gk"], curve)

    rep = transfer_tests(batteries, ref="US")
    lev = leverage_contrast(batteries, eq_markets)
    per_coin = per_asset_leverage(cu["close"], cu["gk"])

    def eqmed(q):
        return float(np.median([laws[q]["values"][m] for m in eq_markets]))

    C = batteries["crypto"]
    c1 = C["kurt_def"][0] < 5.0
    c2 = lev["verdict"] in ("INVERTED", "WEAKER")
    # C3 requires crypto to be SIGNIFICANTLY more reflexive, not just nominally:
    # a nominal-only edge means near-critical branching simply transfers.
    c3 = (rep["n_raw"]["class"] == "UNIVERSE-SPECIFIC"
          and C["n_raw"][0] > eqmed("n_raw"))
    c4 = C["kurt"][0] > eqmed("kurt")
    n_inv = sum(1 for v in per_coin.values() if v > 0)

    for q in rep:
        cv = rep[q]["values"].get("crypto")
        print(f"[crypto] {q:12s} crypto={cv} vs equity-median={round(eqmed(q),3)} "
              f"| {rep[q]['class']}  z={rep[q]['z_vs_ref'].get('crypto')}")
    print(f"[crypto] LEVERAGE: crypto {lev['crypto_leverage']:+.3f} vs equity "
          f"{lev['equity_mean']:+.3f} (z={lev['z_vs_equities']}) -> {lev['verdict']}; "
          f"{n_inv}/{len(per_coin)} coins individually inverted")
    print(f"[crypto] C1 one-clock survives: {c1} (kurt_def={C['kurt_def'][0]:.2f}) | "
          f"C2 leverage differs: {c2} ({lev['verdict']}) | "
          f"C3 more reflexive: {c3} (n_raw {C['n_raw'][0]:.2f} vs {eqmed('n_raw'):.2f}) | "
          f"C4 fatter tails: {c4} (kurt {C['kurt'][0]:.1f} vs {eqmed('kurt'):.1f})")

    out = {"source": cu["source"], "coins": list(cu["close"].columns),
           "span": [str(cu["close"].index[0].date()),
                    str(cu["close"].index[-1].date())],
           "equity_markets": eq_markets, "laws": rep,
           "leverage_contrast": lev, "per_coin_leverage": per_coin,
           "branching_still_collapses": bool(C["n_def"][0] < C["n_raw"][0]),
           "hypotheses": {"C1": bool(c1), "C2": bool(c2),
                          "C3": bool(c3), "C4": bool(c4)}}
    print(f"[crypto] done in {time.time()-t0:.0f}s")
    save("crypto", out)
    return out


def exp_edge(force: bool = False) -> dict:
    """DESIGN15 before/after, reproducible: reconstructs the LEGACY (inverted-
    throttle) overlay inline for the baseline row, then measures fix-only and
    fix+leverage, with split-half robustness and regime/stress exposure."""
    if not force and (c := load_cached("edge")):
        print("[edge] cached")
        return c
    from dataclasses import replace

    import kronos.backtest as B
    from config import REGIME_NAMES
    from kronos.pairs import run_pairs_sleeve
    from kronos.regime import walkforward_regimes
    from kronos.risk import historical_cvar

    px, _, _, src = get_data()
    mkt = px[CFG.market].pct_change().dropna()
    t0 = time.time()
    rg = walkforward_regimes(mkt, CFG)
    pairs = run_pairs_sleeve(px, [], CFG)["returns"] * CFG.pairs_gross_sleeve

    def legacy_exposure(port_rets, cfg):
        """The pre-DESIGN15 overlay, verbatim: inverted m_dd, min() combiner,
        hard cap at 1. Kept ONLY to reproduce the baseline row."""
        r = port_rets.fillna(0.0)
        ann = np.sqrt(252)
        ewma_vol = r.ewm(halflife=21).std() * ann
        m_vol = (cfg.vol_target / ewma_vol.replace(0, np.nan)).clip(upper=1.0).fillna(1.0)
        cvar = r.rolling(252).apply(
            lambda x: historical_cvar(x.to_numpy(), cfg.cvar_alpha), raw=False)
        m_cvar = (cfg.cvar_target / cvar.replace(0, np.nan)).clip(upper=1.0).fillna(1.0)
        nav = (1 + r).cumprod()
        dd = nav / nav.cummax() - 1.0
        span = cfg.dd_floor_at - cfg.dd_start
        m_dd = (1.0 + (dd - cfg.dd_start) * (1 - cfg.dd_min_exposure) / span) \
            .clip(cfg.dd_min_exposure, 1.0)
        raw = pd.concat([m_vol, m_cvar, m_dd], axis=1).min(axis=1)
        exposure = raw.ewm(span=cfg.risk_smooth_days).mean().clip(0.0, 1.0)
        return pd.DataFrame({"m_vol": m_vol, "m_cvar": m_cvar, "m_dd": m_dd,
                             "exposure": exposure})

    def run(cfg, patch_legacy=False):
        orig = B.exposure_series
        if patch_legacy:
            B.exposure_series = legacy_exposure
        try:
            bt = B.run_backtest(px, rg["regime"], cfg)
        finally:
            B.exposure_series = orig
        start = bt["warmup_end"]
        net = (bt["net"] + pairs).loc[start:]
        halves = {}
        for lo, hi in (("2013-01-01", "2019-12-31"), ("2020-01-01", "2026-12-31")):
            seg = net.loc[lo:hi]
            halves[f"{lo[:4]}-{hi[:4]}"] = {
                "sharpe": M.sharpe(seg),
                "cagr": float((1 + seg).prod() ** (252 / len(seg)) - 1),
                "max_dd": float(((1 + seg).cumprod()
                                 .pipe(lambda n: n / n.cummax() - 1)).min())}
        fin_ann = float(bt["financing"].loc[start:].sum() / (len(net) / 252)) \
            if "financing" in bt else 0.0
        return bt, {"full": M.summary(net, ""), "halves": halves,
                    "fin_ann": fin_ann}

    _, base = run(replace(CFG, max_exposure=1.0), patch_legacy=True)
    _, fix = run(replace(CFG, max_exposure=1.0))
    bt_lev, lev = run(CFG)

    # regime / stress behavior of the levered default
    ex = bt_lev["exposure_applied"].loc[bt_lev["warmup_end"]:]
    reg = rg["regime"].reindex(ex.index).ffill().fillna(1).astype(int)
    regime_expo = {REGIME_NAMES[rid]: {"mean": float(ex[reg == rid].mean()),
                                       "levered_frac": float((ex[reg == rid] > 1).mean())}
                   for rid in REGIME_NAMES}
    stress = {}
    for lo, hi, label in (("2020-02-15", "2020-04-30", "COVID crash"),
                          ("2022-01-01", "2022-10-31", "2022 bear")):
        w = ex.loc[lo:hi]
        stress[label] = {"mean": float(w.mean()), "min": float(w.min())}

    variants = {"baseline (bug, cap 1)": base, "fix-only (cap 1)": fix,
                "fix + lever 1.5": lev}
    for name, v in variants.items():
        f = v["full"]
        print(f"[edge] {name:22s} CAGR {f['cagr']:+.1%} SR {f['sharpe']:.2f} "
              f"DD {f['max_dd']:.1%} fin {v['fin_ann']:.2%}/yr")
    out = {"variants": variants, "regime_exposure": regime_expo,
           "stress": stress, "financing_rate_ann": CFG.financing_rate_ann,
           "max_exposure": CFG.max_exposure}
    print(f"[edge] done in {time.time()-t0:.0f}s")
    save("edge", out)
    return out


EXPERIMENTS = {
    "horserace": exp_horserace,
    "tails": exp_tails,
    "rfsv": exp_rfsv,
    "laws": exp_laws,
    "clock": exp_clock,
    "surge": exp_surge,
    "bits": exp_bits,
    "arrow": exp_arrow,
    "decathlon": exp_decathlon,
    "critical": exp_critical,
    "reflex": exp_reflex,
    "constants": exp_constants,
    "transfer": exp_transfer,
    "crypto": exp_crypto,
    "edge": exp_edge,
    "vollab": exp_vollab,
    "rough": exp_rough,
    "rmt": exp_rmt,
    "statarb": exp_statarb,
    "cvar": exp_cvar,
    "ensemble": exp_ensemble,
    "forensics": exp_forensics,
    "synthesis": exp_synthesis,
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    force = "--force" in sys.argv
    which = args[0] if args else "all"
    t0 = time.time()
    if which == "all":
        for name, fn in EXPERIMENTS.items():
            fn(force=force)
    else:
        EXPERIMENTS[which](force=force)
    print(f"\nresearch run complete in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
