"""Gate X40: the README headline is a regression target, not a remembered number.

Recomputes the shipped book from the committed price snapshot, independently
of run_research.py, and asserts it reproduces research/momtilt.json — the one
artifact every README results-table cell is pinned to by check_surfaces.py.
A code change that moves the shipped Sharpe, drawdown, CAGR or excess-cash
Sharpe by more than the tolerance fails CI until the artifact is regenerated
(and the README with it). Also asserts the artifact was produced from the
pinned snapshot this checkout carries (input digest).

Real data only; under KRONOS_SYNTHETIC it prints SKIPPED, and the real-data
CI job fails on any SKIPPED line.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CFG
from kronos import metrics as M
from kronos.backtest import run_backtest
from kronos.data import is_real, load_prices
from kronos.metrics import dtb3_daily, sharpe_excess
from kronos.pairs import run_pairs_sleeve
from kronos.regime import walkforward_regimes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOL = 1e-3

px, src = load_prices(CFG)
if not is_real(src):
    print("GATE X40 SKIPPED (synthetic data): the headline is a real-data claim")
    sys.exit(0)

with open(os.path.join(ROOT, "research", "momtilt.json")) as fh:
    art = json.load(fh)

with open(os.path.join(ROOT, "data", "pinned_manifest.json")) as fh:
    digest = json.load(fh)["sha256"]["close.csv.gz"][:16]
assert src == "pinned" and digest == art["input_digest"], \
    f"artifact built from different prices: {art['input_digest']} vs snapshot {digest} ({src})"
assert art["backbone"] == CFG.backbone, \
    f"artifact backbone {art['backbone']!r} != shipped default {CFG.backbone!r}"

mkt = px[CFG.market].pct_change().dropna()
rg = walkforward_regimes(mkt, CFG)
pairs = run_pairs_sleeve(px, [], CFG)["returns"] * CFG.pairs_gross_sleeve
bt = run_backtest(px, rg["regime"], CFG)
cut = bt["warmup_end"]
net = (bt["net"] + pairs).loc[cut:]
ew = (bt["gross"] - bt["costs"]).loc[cut:]
rf = dtb3_daily(net.index)

checks = {
    "shipped_tilted": net,
    "equal_weight_raw": ew,
    "spy": mkt.loc[cut:],
}
worst = 0.0
for label, series in checks.items():
    got = M.summary(series, label)
    got["sharpe_excess"] = sharpe_excess(series, rf)
    want = art["rows"][label]
    for k in ("sharpe", "sharpe_excess", "max_dd", "cagr", "vol"):
        d = abs(got[k] - want[k])
        worst = max(worst, d)
        assert d < TOL, (f"{label}.{k} regressed: recomputed {got[k]:.5f} vs "
                         f"momtilt.json {want[k]:.5f} (|d|={d:.2e} >= {TOL})")
    print(f"X40 {label:16s} Sharpe {got['sharpe']:.4f} (excess {got['sharpe_excess']:.4f}) "
          f"MaxDD {got['max_dd']:.2%} CAGR {got['cagr']:.2%} == artifact")
assert str(net.index[0].date()) == art["span"][0] and str(net.index[-1].date()) == art["span"][1]
print(f"X40 span {art['span'][0]}..{art['span'][1]} and input digest {digest} match; "
      f"worst |d| = {worst:.1e} < {TOL}")
print("GATE X40 PASSED")
