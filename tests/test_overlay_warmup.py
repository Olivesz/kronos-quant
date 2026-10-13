"""Gate X42: the risk overlay sees only the book's own returns.

run_backtest pads every pre-warmup day with a zero return (the book does not
exist yet). Those zeros are not data: an overlay trained on them (the HAR
lever's regression, the CVaR and drawdown brakes) reads a fictitious
zero-volatility history and opens the lever at its cap. This gate pins that
run_backtest's applied exposure equals the overlay computed on the
post-warmup returns alone, and shows in-gate that the zero-padded input gives
a different, cap-biased exposure path — so the property is not vacuous.
Synthetic panel, no network; identical in both CI jobs.
"""
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from config import CFG
from kronos.backtest import run_backtest
from kronos.risk import exposure_series

rng = np.random.default_rng(42)
T, n = 1400, 6
idx = pd.bdate_range("2015-01-02", periods=T)
vol = 0.012 * np.exp(0.5 * np.sin(np.arange(T) / 90.0))[:, None]
rets = rng.standard_t(5, size=(T, n)) * vol / np.sqrt(5 / 3) + 0.0003
px = pd.DataFrame(100 * np.cumprod(1 + rets, axis=0), index=idx,
                  columns=["MKT"] + [f"S{i}" for i in range(1, n)])
cfg = replace(CFG, universe=list(px.columns), market="MKT", backbone="ew",
              mom_tilt=0.15, pairs_gross_sleeve=0.0)
regime = pd.Series(0, index=idx)

bt = run_backtest(px, regime, cfg)
w = list(idx).index(bt["warmup_end"])
gross = bt["gross"]
assert float(gross.iloc[:w + 1].abs().max()) == 0.0, "precondition: zero-padded warmup"

logr = np.log(px["MKT"] / px["MKT"].shift(1))
tilt = 1.0 + cfg.mom_tilt * np.sign(logr.rolling(21).sum()).fillna(0.0)
clean = exposure_series(gross.iloc[w + 1:], cfg, tilt=tilt)["exposure"]
applied = bt["exposure_applied"].iloc[w + 2:]
want = clean.shift(1).iloc[1:]
d = float((applied - want.reindex(applied.index)).abs().max())
assert d < 1e-12, f"applied exposure is not the overlay on post-warmup returns (|d|={d:.2e})"
print(f"X42a applied exposure == overlay on the book's own returns ({len(applied)} days, |d|={d:.1e})")

padded = exposure_series(gross, cfg, tilt=tilt)["exposure"].iloc[w + 1:]
early = slice(0, 120)
gap = float((padded.iloc[early] - clean.iloc[early]).abs().mean())
cap_padded = float((padded.iloc[early] >= cfg.max_exposure - 1e-9).mean())
cap_clean = float((clean.iloc[early] >= cfg.max_exposure - 1e-9).mean())
assert gap > 0.01, f"zero-padded overlay indistinguishable from the clean one (gap {gap:.4f})"
print(f"X42b zero-padded input differs over the first 120 days (mean |d| {gap:.3f}; "
      f"at cap {cap_padded:.0%} padded vs {cap_clean:.0%} clean)")
print("GATE X42 PASSED")
