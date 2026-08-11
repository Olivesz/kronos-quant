"""Gate X27: the risk overlay must have the right DIRECTION and reach.

Pins the exact properties whose absence hid the DESIGN15 sign bug:
(a) the drawdown throttle holds m_dd = 1 at the high-water mark and decreases
    monotonically with drawdown depth to the floor at dd_floor_at;
(b) vol targeting levers a calm low-vol world toward the target, capped at
    max_exposure, and de-levers a hot world below 1;
(c) the backtester charges financing when — and only when — exposure > 1.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

import numpy as np
import pandas as pd

from config import CFG
from kronos.risk import exposure_series

rng = np.random.default_rng(3)
idx = pd.bdate_range("2015-01-01", periods=1500)
cfg = replace(CFG, risk_smooth_days=1)          # no smoothing: read raw multipliers


# --- (a) throttle direction: engineered drawdown path ---------------------------
# flat, then a controlled slide to -25%, then recovery
r = np.zeros(1500)
r[300:340] = -0.00722                            # ~ -25% cumulative slide
r[340:420] = 0.004                               # recovery leg
path = pd.Series(r, index=idx)
ex = exposure_series(path, cfg)
nav = (1 + path).cumprod()
dd = nav / nav.cummax() - 1.0

at_hwm = ex["m_dd"][dd >= -1e-12]
print(f"m_dd at high-water: min {at_hwm.min():.3f} (must be 1)")
assert (at_hwm > 0.999).all(), "throttle brakes at the high-water mark (the DESIGN15 bug)"

deep = ex["m_dd"][dd < cfg.dd_floor_at]
print(f"m_dd beyond floor dd: max {deep.max():.3f} (must be {cfg.dd_min_exposure})")
assert np.allclose(deep, cfg.dd_min_exposure, atol=1e-9), "no floor at dd_floor_at"

# monotone: deeper drawdown never gets MORE exposure
sl = slice(300, 340)
dd_slide, m_slide = dd.iloc[sl].to_numpy(), ex["m_dd"].iloc[sl].to_numpy()
order = np.argsort(dd_slide)                     # shallow -> deep? argsort ascending = deepest first
assert (np.diff(m_slide[order]) >= -1e-12).all(), "m_dd not monotone in drawdown depth"
mid = ex["m_dd"][(dd < -0.10) & (dd > -0.18)]
assert (mid < 1.0).all() and (mid > cfg.dd_min_exposure).all(), "no linear mid-zone"

# --- (b) vol targeting levers up when calm, down when hot -----------------------
# drift keeps the calm book near its high-water mark so the lever is isolated
calm = pd.Series(rng.normal(0.08 / 252, 0.05 / np.sqrt(252), 1500), index=idx)
hot = pd.Series(rng.normal(0.20 / 252, 0.30 / np.sqrt(252), 1500), index=idx)
exc = exposure_series(calm, cfg)
exh = exposure_series(hot, cfg)
ex_calm = exc["exposure"].iloc[-500:]
print(f"calm 5%-vol world: mean exposure {ex_calm.mean():.2f} "
      f"(target/vol={cfg.vol_target/0.05:.1f}, cap {cfg.max_exposure})")
print(f"hot 30%-vol world: mean m_vol {exh['m_vol'].iloc[-500:].mean():.2f} "
      f"(target/vol={cfg.vol_target/0.30:.2f})")
assert ex_calm.mean() > 1.2, "vol targeting fails to lever a calm world"
assert (ex_calm <= cfg.max_exposure + 1e-9).all(), "max_exposure cap violated"
assert 0.25 < exh["m_vol"].iloc[-500:].mean() < 0.65, "lever fails to de-lever a hot world"
assert (exh["exposure"] <= exh["m_vol"] * 1.0001 + 1e-9).all(), \
    "brakes must only ever reduce the lever"

# --- (c) financing charged iff levered ------------------------------------------
from kronos.backtest import run_backtest  # noqa: E402
from kronos.data import generate_synthetic  # noqa: E402

px = generate_synthetic(CFG.universe, "2014-01-01", "2020-12-31", seed=11)
regime = pd.Series(0, index=px.index)
cfg_lev = replace(CFG, hmm_min_train=500, max_exposure=1.5, financing_rate_ann=0.035)
cfg_nolev = replace(cfg_lev, max_exposure=1.0)
bt_lev = run_backtest(px, regime, cfg_lev)
bt_nolev = run_backtest(px, regime, cfg_nolev)

lev_days = (bt_lev["exposure_applied"] > 1.0)
fin_implied = (bt_lev["gross"] * bt_lev["exposure_applied"]
               - bt_lev["costs"] - bt_lev["net"])
print(f"levered days: {lev_days.mean():.0%}; financing on levered days "
      f"~{fin_implied[lev_days].mean()*1e4:.2f} bp/day; on unlevered days "
      f"{fin_implied[~lev_days].abs().max()*1e4:.4f} bp max")
assert lev_days.any(), "leverage never engaged on a calm synthetic world"
assert (fin_implied[lev_days] > 0).all(), "no financing charged while levered"
assert (fin_implied[~lev_days].abs() < 1e-12).all(), "financing charged while unlevered"
exp_fin = ((bt_lev["exposure_applied"][lev_days] - 1) * 0.035 / 252)
assert np.allclose(fin_implied[lev_days], exp_fin, atol=1e-12), "financing rate wrong"
assert (bt_nolev["exposure_applied"] <= 1.0 + 1e-9).all(), "cap=1 config leaks leverage"

print("\nGATE X27 PASSED")
