"""Gate 7: backtester accounting integrity on real data (short window)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

from config import CFG
from kronos.backtest import run_backtest
from kronos.data import load_prices
from kronos.metrics import summary
from kronos.regime import walkforward_regimes
from kronos.risk import portfolio_greeks

px, src = load_prices(CFG)
px = px.iloc[-1800:]  # ~7 years for a fast gate
cfg = replace(CFG, hmm_min_train=500)

mkt = px[cfg.market].pct_change().dropna()
reg = walkforward_regimes(mkt, cfg)["regime"]

t0 = time.time()
bt = run_backtest(px, reg, cfg)
print("backtest %ds" % (time.time() - t0))

w = bt["weights"]
after = w.loc[bt["warmup_end"]:].iloc[2:]
sums = after.sum(axis=1)
assert not after.isna().any().any(), "NaN weights"
assert ((sums - 1).abs() < 1e-6).all(), f"weights don't sum to 1: {sums.describe()}"
assert (after >= -1e-12).all().all(), "negative weight in long-only book"
assert (after.max(axis=1) <= CFG.max_weight + 0.06).all(), "cap blown past drift allowance"

assert (bt["costs"] >= 0).all() and bt["cost_total"] > 0, "costs missing"
net_nav = (1 + bt["net"]).prod()
gross_nav = (1 + bt["gross"] * bt["exposure_applied"]).prod()
print("NAV gross(risk-scaled) %.3f vs net %.3f" % (gross_nav, net_nav))
assert net_nav < gross_nav, "costs must reduce NAV"

ann_cost = bt["costs"].sum() / (len(px) / 252)
print("cost drag: %.2f%%/yr, turnover: %.1fx/yr" %
      (100 * ann_cost, bt["turnover"].sum() / (len(px) / 252)))
assert ann_cost < 0.05, "implausible cost drag"

s = summary(bt["net"].loc[bt["warmup_end"]:], "net")
print({k: round(v, 3) for k, v in s.items() if isinstance(v, float)})
assert -0.5 < s["cagr"] < 1.0 and s["vol"] < 0.5, "implausible performance"

g = portfolio_greeks(bt["net"], mkt, ann_cost)
print("greeks: delta=%.2f gamma=%.2f vega=%.4f" % (g["delta"], g["gamma"], g["vega"]))
assert 0.0 < g["delta"] < 1.5, "delta implausible for long-only equity book"

print("\nGATE 7 PASSED")
