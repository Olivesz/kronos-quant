"""Gate X41: realized forward P&L of the live ledger, against hand arithmetic.

kronos.live.forward_returns turns the ledger's recorded weights into daily
net returns. This gate builds a 3-day ledger on a toy panel whose returns
are chosen by hand and checks every day against arithmetic written out
independently below:
  (a) T+1 timing: weights recorded at close t earn the return over (t, t+1];
  (b) entry cost, no cost while the target is unchanged, rebalance cost when
      it changes — on the DRIFTED holdings, not the stale target;
  (c) cash remainder (exposure < 1) earns zero;
  (d) benchmarks: SPY's own return, equal-weight = daily cross-sectional mean.
Falsified in-gate: a same-day-alignment variant (weights at t earn day t)
must disagree with the hand values.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from kronos.live import forward_returns

idx = pd.bdate_range("2026-01-05", periods=4)          # d0..d3
rA = [0.10, -0.05, 0.02]                                 # returns on d1, d2, d3
rB = [0.00, 0.04, -0.03]
rS = [0.01, 0.02, -0.01]
close = pd.DataFrame({"A": 100 * np.cumprod([1] + [1 + x for x in rA]),
                      "B": 50 * np.cumprod([1] + [1 + x for x in rB]),
                      "SPY": 400 * np.cumprod([1] + [1 + x for x in rS])}, index=idx)
BPS = 10.0                                               # linear cost only
costs = SimpleNamespace(commission_bps=BPS, spread_bps=0.0,
                        impact_coeff=0.0, impact_cap_bps=0.0)
ledger = [
    {"date": "2026-01-05", "status": "LIVE", "exposure": 0.9, "weights": {"A": 0.5, "B": 0.5}},
    {"date": "2026-01-06", "status": "LIVE", "exposure": 0.9, "weights": {"A": 0.5, "B": 0.5}},
    {"date": "2026-01-07", "status": "LIVE", "exposure": 1.0, "weights": {"A": 1.0}},
    {"date": "2026-01-07", "status": "REANCHOR", "factors": {}},   # ignored
]

# ---- hand arithmetic ----------------------------------------------------------
c = BPS / 1e4
# d1: enter 0.45/0.45 (cash 0.10) at close d0; entry cost 0.9*c charged on d1
pA, pB = 0.45, 0.45
g1 = pA * rA[0] + pB * rB[0]                    # 0.045
n1 = g1 - 0.9 * c
pA, pB = pA * (1 + rA[0]) / (1 + g1), pB * (1 + rB[0]) / (1 + g1)
# d2: target unchanged -> no trade, no cost; holdings have drifted
g2 = pA * rA[1] + pB * rB[1]
n2 = g2
pA, pB = pA * (1 + rA[1]) / (1 + g2), pB * (1 + rB[1]) / (1 + g2)
# d3: target -> {A: 1.0} at close d2, traded from the DRIFTED holdings
cost3 = (abs(1.0 - pA) + abs(0.0 - pB)) * c
g3 = 1.0 * rA[2]
n3 = g3 - cost3
hand = {"kronos": [n1, n2, n3], "spy": rS,
        "equal_weight": [np.mean([a, b, s]) for a, b, s in zip(rA, rB, rS)]}

got = forward_returns(ledger, close, costs)
assert list(got.index) == list(idx[1:]), f"dates {list(got.index)}"
for col, vals in hand.items():
    diff = float(np.max(np.abs(got[col].to_numpy() - np.array(vals))))
    assert diff < 1e-14, f"{col} differs from hand arithmetic by {diff:.2e}"
print(f"X41a-d forward P&L == hand arithmetic to 1e-14: kronos "
      f"{[round(x, 6) for x in hand['kronos']]}, drifted rebalance cost {cost3:.6f}")

# ---- falsification: same-day alignment must NOT match -------------------------
shifted = [dict(r, date=str((pd.Timestamp(r['date']) - pd.offsets.BDay(1)).date()))
           if r.get("status") == "LIVE" else r for r in ledger]
close_ext = pd.concat([close.iloc[:1].set_axis([idx[0] - pd.offsets.BDay(1)]), close])
close_ext.iloc[0] = close.iloc[0]
bad = forward_returns(shifted, close_ext, costs).reindex(got.index)
d = float(np.nanmax(np.abs(bad["kronos"].to_numpy() - np.array(hand["kronos"]))))
assert d > 1e-3, "a same-day-aligned ledger reproduced the T+1 hand values"
print(f"X41 falsified: same-day alignment misses the hand values by {d:.4f}")
print("GATE X41 PASSED")
