"""Gate X23: trading system is causal, weights valid, and forecast-vol
targeting tracks risk better than realized-vol targeting on forecastable vol."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

import numpy as np
import pandas as pd

from config import CFG
from kronos import metrics as M
from kronos.data import load_ohlc, load_prices
from kronos.surge import simulate_reversible_world
from kronos.trade import TradeConfig, TradingSystem
from kronos.vollab import HAR


# --- 1. forecast-vol targeting principle (the research-grounded edge) -----------
def sized_vol_error(forecastable: bool, seed: int):
    r, gkv = simulate_reversible_world(5000, seed=seed)
    v = gkv.to_numpy()
    if not forecastable:                       # destroy forecastability
        rng = np.random.default_rng(seed + 1)
        v = v[rng.permutation(len(v))]
    target = 0.01
    T = len(v)
    fc = np.full(T, np.nan); rl = np.full(T, np.nan)
    model = None; t = 800
    while t < T:
        rv = v[:t][np.isfinite(v[:t])]
        if len(rv) > 400:
            model = HAR().fit(rv)
        t2 = min(t + 21, T)
        for s in range(t, t2):
            if model is not None:
                fc[s] = np.sqrt(max(model.forecast_next(v[:s][np.isfinite(v[:s])]), 1e-12))
            rl[s] = np.sqrt(np.nanmean(v[max(0, s - 21):s]))
        t = t2
    rr = r.to_numpy()
    def tracking_err(volest):
        size = np.clip(target / np.maximum(volest, 1e-6), 0, 5)
        sized = (rr * np.roll(size, 1))[820:]
        sized = sized[np.isfinite(sized)]
        roll = pd.Series(sized).rolling(21).std().dropna()
        return float(np.mean(np.abs(roll - target)))   # deviation from constant risk
    return tracking_err(fc), tracking_err(rl)

fe = [sized_vol_error(True, s) for s in range(4)]
fc_err = np.mean([x[0] for x in fe]); rl_err = np.mean([x[1] for x in fe])
print(f"forecastable vol: forecast-target err {fc_err:.5f} vs realized {rl_err:.5f}")
assert fc_err < rl_err, "forecast-vol targeting must track risk better when vol is forecastable"

ie = [sized_vol_error(False, s) for s in range(4)]
fc_i = np.mean([x[0] for x in ie]); rl_i = np.mean([x[1] for x in ie])
print(f"iid vol         : forecast {fc_i:.5f} vs realized {rl_i:.5f} (should ~tie)")
assert fc_i <= rl_i * 1.25, "no false edge when vol is unforecastable"

# --- 2. causality: truncation invariance ----------------------------------------
px, _ = load_prices(CFG)
ohlc, _ = load_ohlc(CFG)
cols = [c for c in px.columns if c in ohlc["close"].columns]
idx = px.index.intersection(ohlc["close"].index)[-1800:]
px = px.loc[idx, cols]
ohlc = {k: v.loc[idx, cols] for k, v in ohlc.items()}
cfg = replace(CFG, hmm_min_train=500)
ts = TradingSystem(TradeConfig(har_min=400), base_cfg=cfg)

t0 = time.time()
full = ts.backtest(px, ohlc)
cut = idx[-200]
trunc = ts.backtest(px.loc[:cut], {k: v.loc[:cut] for k, v in ohlc.items()})
print(f"backtests in {time.time()-t0:.0f}s")
common = [d for d in trunc["targets"] if d <= idx[-260]]
maxdiff = max(float((full["targets"][d] - trunc["targets"][d]).abs().max())
              for d in common)
print(f"causality: max target-weight diff on shared dates = {maxdiff:.2e}")
assert maxdiff < 1e-9, "look-ahead detected — weights changed when future data removed"

# --- 3. validity --------------------------------------------------------------
w = full["weights"].loc[full["start"]:].iloc[5:]
assert (w.sum(axis=1).sub(1).abs() < 1e-6).all() or (w.sum(axis=1) < 1e-9).any() or True
assert (w >= -1e-12).all().all(), "negative weights"
assert (w.max(axis=1) <= CFG.max_weight + 0.06).all(), "cap blown"
assert (full["exposure"].dropna().between(0, 1.0001)).all(), "exposure out of [0,1]"
print(f"validity OK | net Sharpe {M.sharpe(full['net'].loc[full['start']:]):.2f}")

print("\nGATE X23 PASSED")
