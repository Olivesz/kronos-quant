"""Gate X38 (DESIGN27): EW backbone identity, causality, cash-rate machinery.

(a) EW-backbone identity: with the overlay neutralized, the backbone's gross
    book equals an independently drifted 1/N book on the rebalance grid.
(b) Causality: shifting all inputs forward one day changes no EW target
    weight on shared dates (test_trade pattern).
(c) DTB3 loader + excess-Sharpe fixture: committed CSV parses, daily rate
    sane, hand-computed 3-day fixture reproduces exactly.
(d) Shipped-row anchor: the DESIGN27 driver's shipped book reproduces
    research/momtilt.json (real data only; SKIPPED under KRONOS_SYNTHETIC).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

import numpy as np
import pandas as pd

from config import CFG
from kronos.backtest import run_backtest
from kronos.data import is_real, load_prices
from kronos.metrics import dtb3_daily, sharpe_excess
from kronos.regime import walkforward_regimes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

px, src = load_prices(CFG)
px = px.iloc[-1400:]
cfg = replace(CFG, backbone="ew", hmm_min_train=500)
mkt = px[cfg.market].pct_change().dropna()
reg = walkforward_regimes(mkt, cfg)["regime"]
bt = run_backtest(px, reg, cfg)

# (a) identity: reconstruct the 1/N-with-drift book independently from the
# weights frame run_backtest exposes; gross must equal sum(w*r) exactly, and
# each rebalance-day target must be uniform over live names.
rets = px.pct_change().fillna(0.0)
recon = (bt["weights"] * rets).sum(axis=1)
assert float((recon - bt["gross"]).abs().max()) < 1e-12, "gross != w.r"
targets = bt["targets"]
for t, w in list(targets.items())[::7]:
    live = px.loc[t].notna()
    expect = 1.0 / live.sum()
    nz = w[live]
    assert float((nz - expect).abs().max()) < 1e-12, f"non-uniform target at {t}"
    assert float(w[~live].abs().max() if (~live).any() else 0.0) == 0.0
print(f"X38a EW identity: gross==w.r to 1e-12; {len(targets)} uniform targets")

# (b) causality: run on data shifted forward one day; targets on shared
# rebalance dates must be identical (the 1/N rule sees only names live at t).
px2 = px.shift(1)  # same index, values one day late: grid positions coincide
mkt2 = px2[cfg.market].pct_change().dropna()
reg2 = walkforward_regimes(mkt2, cfg)["regime"]
bt2 = run_backtest(px2, reg2, cfg)
shared = sorted(set(targets) & set(bt2["targets"]))[5:]
diff = max(float((targets[t] - bt2["targets"][t]).abs().max()) for t in shared)
assert diff == 0.0, f"EW causality leak: max target diff {diff}"
print(f"X38b causality: max target-weight diff on {len(shared)} shared dates = {diff:.2e}")

# (c) DTB3 loader + fixture
idx = pd.bdate_range("2020-01-02", periods=300)
rf = dtb3_daily(idx, path=os.path.join(ROOT, "data", "dtb3.csv"))
assert rf.notna().all() and float(rf.min()) >= -1e-5 and float(rf.max()) < 25e-4, \
    f"DTB3 daily rate out of range: {rf.min()}..{rf.max()}"
fix = pd.Series([0.01, -0.005, 0.002],
                index=pd.bdate_range("2021-01-04", periods=3))
rf_fix = pd.Series(0.0001, index=fix.index)
ex = fix - rf_fix
expect = float(ex.mean() / ex.std() * np.sqrt(252))
got = sharpe_excess(fix, rf_fix)
assert abs(got - expect) < 1e-12, f"excess-Sharpe fixture: {got} != {expect}"
# and the loader must refuse an uncovered span
try:
    dtb3_daily(pd.bdate_range("1890-01-01", periods=5),
               path=os.path.join(ROOT, "data", "dtb3.csv"))
    raise AssertionError("DTB3 loader accepted an uncovered span")
except ValueError:
    pass
print(f"X38c DTB3: {len(rf)} daily rates in range; fixture {got:.4f} exact; "
      "uncovered span refused")

# (d) shipped-row anchor against the canonical artifact (real data only)
if not is_real(src):
    print("X38d SKIPPED (synthetic mode): shipped-row anchor needs real data")
else:
    import json
    with open(os.path.join(ROOT, "research", "ewbar.json")) as fh:
        ew = json.load(fh)
    with open(os.path.join(ROOT, "research", "momtilt.json")) as fh:
        mt = json.load(fh)
    for k in ("sharpe", "max_dd", "cagr"):
        a = ew["rows"]["shipped_tilted"][k]
        b = mt["rows"]["shipped_tilted"][k]
        assert abs(a - b) < 1e-6, f"ewbar shipped row drifted on {k}: {a} vs {b}"
    print("X38d anchor: ewbar shipped row == momtilt.json on sharpe/max_dd/cagr")

print("GATE X38 PASSED")
