"""Gate X43: the shipped-book stream measures the shipped book, exactly.

The live ledger's second stream records, before each session, the shipped
book's decision for the next day (kronos.live.shipped_decision): overlay
exposure, equity holdings, pair-sleeve legs, the next day's trading cost and
financing. This gate replays those decisions on a synthetic panel with planted
cointegrated pairs: deciding at each close from the prefix of data available
then, and applying the decision to the next day's returns, must reproduce the
full backtest's net return (core book + pairs sleeve) on every replayed day to
1e-12 — including a monthly rebalance and days with open pair positions. It
also checks that the 1/N backbone ignores the regime series (the stream passes
a constant one) and that a same-day-aligned replay does not match.
Synthetic, no network; identical in both CI jobs.
"""
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from config import CFG
from kronos.backtest import run_backtest
from kronos.live import shipped_decision, shipped_returns
from kronos.pairs import run_pairs_sleeve

rng = np.random.default_rng(7)
T = 1100
idx = pd.bdate_range("2018-01-02", periods=T)
f = np.cumsum(rng.normal(0.0003, 0.010, T))
cols = {"MKT": f}
for i in range(1, 6):
    cols[f"S{i}"] = f * rng.uniform(0.6, 1.4) + np.cumsum(rng.normal(0, 0.012, T))
for a, b in (("P1", "P2"), ("P3", "P4")):                  # cointegrated pairs
    base = np.cumsum(rng.normal(0.0002, 0.012, T))
    ou = np.zeros(T)
    for t in range(1, T):
        ou[t] = 0.85 * ou[t - 1] + rng.normal(0, 0.003)
    cols[a], cols[b] = base, base + ou
px = pd.DataFrame({k: 50 * np.exp(v) for k, v in cols.items()}, index=idx)
cfg = replace(CFG, universe=list(px.columns), market="MKT", backbone="ew",
              min_coverage=0.5)

zeros = pd.Series(0, index=idx)
bt = run_backtest(px, zeros, cfg)
sleeve = run_pairs_sleeve(px, [], cfg)
target = bt["net"] + cfg.pairs_gross_sleeve * sleeve["returns"]

# the backbone ignores regimes: any regime series gives the same book
alt = pd.Series(rng.integers(0, 3, T), index=idx)
assert float((run_backtest(px, alt, cfg)["net"] - bt["net"]).abs().max()) == 0.0, \
    "1/N backbone read the regime series"

# replay 40 consecutive days ending a few days after the sleeve's last open
# position, so the window holds open legs and a monthly rebalance
active = np.flatnonzero(sleeve["returns"].to_numpy() != 0)
assert len(active), "planted pairs never traded"
end = min(int(active[-1]) + 5, T - 2)
worst, rebal_seen, legs_seen, rows = 0.0, False, False, []
for t in range(end - 39, end + 1):
    dec = shipped_decision({"close": px.iloc[:t + 1]}, cfg)
    row = {"status": "LIVE", **dec}
    rows.append(row)
    got = shipped_returns([row], px)
    d = got.index[0]
    assert d == idx[t + 1], f"decision at {idx[t].date()} applied to {d.date()}"
    diff = abs(float(got.iloc[0]) - float(target.loc[d]))
    worst = max(worst, diff)
    assert diff < 1e-12, f"replay {d.date()}: {got.iloc[0]:.12f} vs backtest {target.loc[d]:.12f}"
    rebal_seen |= dec["next_cost"] > 0
    legs_seen |= bool(dec["pair_legs"])
assert rebal_seen, "replay window contains no rebalance"
assert legs_seen, "replay window contains no open pair position"
print(f"X43a replayed decisions == backtest net on 40 days (worst |d| {worst:.1e}); "
      "window includes a rebalance and open pair legs; regimes ignored by the backbone")

# falsification: the same decisions applied to the SAME day must not match
same = []
for row in rows:
    d0 = pd.Timestamp(row["as_of"])
    r0 = px.pct_change().loc[d0].fillna(0.0)
    eq = sum(w * r0[k] for k, w in row["equity_weights"].items())
    pl = sum(w * r0[k] for k, w in row["pair_legs"].items())
    v = row["exposure"] * eq + row["pairs_gross"] * pl - row["next_cost"] - row["financing_daily"]
    same.append(abs(v - float(target.loc[d0])))
assert max(same) > 1e-4, "a same-day alignment reproduced the backtest"
print(f"X43b falsified: same-day alignment misses the backtest by up to {max(same):.4f}")
print("GATE X43 PASSED")
