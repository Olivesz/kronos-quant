"""Gate X47 (DESIGN29 Stage 2): the machinery that tests the shipped overlay
on survivorship-free factors.

a. The overlay is the shipped one: on a synthetic panel, overlay_exposure on
   the backtest's own live book (tilt reading the market's log price change)
   equals run_backtest's applied exposure on every live day after the first,
   exactly. It is causal: perturbing returns from day s on leaves every
   exposure applied through day s unchanged.
b. Bookkeeping: monthly_excess equals Π(1 + e f + rf) − Π(1 + rf) by hand, and
   drops a partial first month; the family's vol scale at t uses data
   through t−1 only; calendar alignment compounds off-calendar days forward.
c. Inference has its size and power on synthetic data: the Ledoit-Wolf
   Sharpe-difference test, the Romano-Wolf stepdown (family-wise error under
   a global null; it finds one planted alpha), Hansen's SPA, and the sup-Wald
   break test (no break vs a planted intercept break).
d. After the reveal: the artifact was produced by the sealed code (its
   code_digest equals the one DESIGN29's seal amendment records), from the
   committed manifest, and its verdict follows from its own numbers under the
   registered rule. Before the reveal it reports that the holdout is sealed.
Synthetic except d; no network.
"""
import json
import os
import re
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from config import CFG
from kronos import volalpha as VA
from kronos.backtest import run_backtest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- a. the shipped overlay, exactly -------------------------------------
rng = np.random.default_rng(47)
T = 1500
idx = pd.bdate_range("2010-01-04", periods=T)
vol = np.exp(np.cumsum(rng.normal(0, 0.05, T)) * 0.3) * 0.012
mkt = np.cumsum(rng.normal(0.0003, 1, T) * vol)
cols = {"MKT": mkt}
for i in range(1, 4):
    cols[f"S{i}"] = mkt * rng.uniform(0.7, 1.3) + np.cumsum(rng.normal(0, 0.008, T))
px = pd.DataFrame({k: 50 * np.exp(v) for k, v in cols.items()}, index=idx)
cfg = replace(CFG, universe=list(px.columns), market="MKT", backbone="ew", min_coverage=0.5)
bt = run_backtest(px, pd.Series(0, index=idx), cfg)
w = list(idx).index(bt["warmup_end"])
live = bt["gross"].iloc[w + 1:]
ours = VA.overlay_exposure(live, cfg, tilt_log=np.log(px["MKT"] / px["MKT"].shift(1)))
theirs = bt["exposure_applied"].reindex(live.index)
diff = float((ours.iloc[1:] - theirs.iloc[1:]).abs().max())
assert diff == 0.0, f"overlay_exposure differs from the shipped backtest by {diff}"
assert theirs.iloc[1:].max() > 1.0 and theirs.iloc[1:].min() < 0.9, "synthetic book never exercised the lever"
s = len(live) // 2
pert = live.copy()
pert.iloc[s:] = rng.normal(0, 0.05, len(live) - s)
e2 = VA.overlay_exposure(pert, cfg)
e1 = VA.overlay_exposure(live, cfg)
assert e1.iloc[:s + 1].equals(e2.iloc[:s + 1]), "exposure applied at s read data from s on"
assert e1.iloc[s + 1] != e2.iloc[s + 1]
print(f"X47a overlay_exposure == run_backtest exposure_applied on {len(live) - 1} live days "
      "(exact); causal through day s")

# ---- b. bookkeeping -------------------------------------------------------
di = pd.bdate_range("2001-01-15", "2001-03-30")
f = pd.Series(rng.normal(0, 0.01, len(di)), index=di)
rf = pd.Series(0.0001, index=pd.bdate_range("2001-01-01", "2001-03-30"))
e = pd.Series(rng.uniform(0.5, 1.5, len(di)), index=di)
m = VA.monthly_excess(e * f, rf)
assert list(m.index.astype(str)) == ["2001-02", "2001-03"], "partial first month not dropped"
feb = di[di.month == 2]
hand = np.prod(1 + e[feb] * f[feb] + 0.0001) - np.prod(1 + rf.reindex(feb))
assert abs(m.loc["2001-02"] - hand) < 1e-15
long = pd.Series(rng.normal(0, 0.01, 3000), index=pd.bdate_range("1990-01-01", periods=3000))
ft, sc = VA.normalized(long)
long2 = long.copy()
long2.iloc[1500:] *= 3.0
_, sc2 = VA.normalized(long2)
cut = long.index[1500]
assert sc.loc[:cut].equals(sc2.loc[:cut]) and sc.loc[long.index[1501]] != sc2.loc[long.index[1501]]
assert sc.index[0] == long.index[VA.WARMUP], "vol scale starts before its minimum window"
cal = pd.DatetimeIndex(["2000-07-03", "2000-07-05", "2000-07-06"])
x = pd.Series([0.01, 0.02, -0.01, 0.03], index=pd.DatetimeIndex(["2000-07-03", "2000-07-04",
                                                                  "2000-07-05", "2000-07-06"]))
al = VA.align_to_calendar(x, cal)
assert list(al.index) == list(cal) and abs(al.iloc[1] - (1.02 * 0.99 - 1)) < 1e-15
print("X47b monthly compounding by hand; partial month dropped; vol scale causal; "
      "off-calendar days compound forward")

# ---- c. size and power ------------------------------------------------------
pm = pd.period_range("1950-01", periods=600, freq="M")


def pair(rng, gap):
    z = rng.standard_normal((600, 2)) @ np.linalg.cholesky([[1, 0.6], [0.6, 1]]).T
    a = pd.Series(0.04 * z[:, 0] + 0.04 * (0.15 + gap) / np.sqrt(12), index=pm)
    b = pd.Series(0.04 * z[:, 1] + 0.04 * 0.15 / np.sqrt(12), index=pm)
    return a, b


rng = np.random.default_rng(3)
lw0 = np.mean([VA.lw_sharpe_diff(*pair(rng, 0.0), n_boot=299, seed=i)["p_one_sided"] < 0.05
               for i in range(120)])
lw1 = np.mean([VA.lw_sharpe_diff(*pair(rng, 0.45), n_boot=299, seed=i)["p_one_sided"] < 0.05
               for i in range(60)])
assert lw0 <= 0.10 and lw1 >= 0.80, f"Ledoit-Wolf size {lw0:.3f} power {lw1:.3f}"


def rw_world(rng, planted):
    F = pd.DataFrame(rng.standard_normal((600, 2)) * 0.04, index=pm, columns=["f1", "f2"])
    Y = pd.DataFrame({f"y{j}": 0.5 * F["f1"] + 0.3 * F["f2"] + 0.03 * rng.standard_normal(600)
                      for j in range(4)}, index=pm)
    if planted:
        Y["y0"] += 0.006
    return Y, dict.fromkeys(Y.columns, F)


rng = np.random.default_rng(4)
fwer = np.mean([any(VA.romano_wolf(*rw_world(rng, False), n_boot=199, seed=i)["rejected"].values())
                for i in range(40)])
hits = [VA.romano_wolf(*rw_world(rng, True), n_boot=199, seed=i)["rejected"] for i in range(20)]
rw_power = np.mean([h["y0"] for h in hits])
rw_false = np.mean([any(h[k] for k in ("y1", "y2", "y3")) for h in hits])
assert fwer <= 0.125 and rw_power >= 0.80 and rw_false <= 0.15, \
    f"Romano-Wolf FWER {fwer:.3f}, power {rw_power:.3f}, false {rw_false:.3f}"

rng = np.random.default_rng(6)
spa0 = np.mean([VA.hansen_spa(pd.DataFrame(rng.standard_normal((600, 5)) * 0.02, index=pm),
                              n_boot=299, seed=i)["p"] < 0.05 for i in range(100)])
spa1 = np.mean([VA.hansen_spa(pd.DataFrame(rng.standard_normal((600, 5)) * 0.02 + [0.0035, 0, 0, 0, 0],
                                           index=pm), n_boot=299, seed=i)["p"] < 0.05 for i in range(40)])
assert spa0 <= 0.10 and spa1 >= 0.80, f"SPA size {spa0:.3f} power {spa1:.3f}"

rng = np.random.default_rng(9)
xb = pd.Series(rng.standard_normal(400) * 0.04, index=pm[:400])
sw0 = np.mean([VA.sup_wald_break(0.5 * xb + 0.03 * pd.Series(rng.standard_normal(400), index=xb.index),
                                 xb, n_sim=2000, lags=4)["p"] < 0.05 for _ in range(30)])
brk = pd.Series(np.r_[np.zeros(200), np.full(200, 0.015)], index=xb.index)
sw1 = np.mean([VA.sup_wald_break(0.5 * xb + brk + 0.03 * pd.Series(rng.standard_normal(400), index=xb.index),
                                 xb, n_sim=2000, lags=4)["p"] < 0.05 for _ in range(15)])
assert sw0 <= 0.15 and sw1 >= 0.80, f"sup-Wald size {sw0:.3f} power {sw1:.3f}"
print(f"X47c Ledoit-Wolf size {lw0:.3f} power {lw1:.3f}; Romano-Wolf FWER {fwer:.3f} "
      f"power {rw_power:.3f}; SPA size {spa0:.3f} power {spa1:.3f}; sup-Wald size {sw0:.3f} power {sw1:.3f}")

# ---- d. the reveal ------------------------------------------------------------
art_path = os.path.join(ROOT, "research", "volalpha.json")
design = open(os.path.join(ROOT, "docs", "design", "DESIGN29.md")).read()
seal = re.search(r"Stage-2 code digest \(`code_digest`\): `([0-9a-f]{16})`", design)
if not os.path.exists(art_path):
    print("X47d holdout sealed: research/volalpha.json not yet produced"
          + (f"; seal recorded (code {seal.group(1)})" if seal else "; seal amendment not yet committed"))
else:
    from kronos.factors import manifest_digest
    art = json.load(open(art_path))
    assert seal, "a reveal artifact exists but DESIGN29 records no seal"
    assert art["code_digest"] == seal.group(1), \
        f"the reveal ran code {art['code_digest']}, not the sealed {seal.group(1)}"
    assert art["input_digest"] == manifest_digest(), "the reveal read a different input set"
    fm, lw, rw = art["full_model"]["Mkt-RF"], art["ledoit_wolf"]["Mkt-RF"], art["romano_wolf"]
    eras = sum(v["alpha"] > 0 for v in art["eras"].values())
    crit = [fm["alpha"] > 0 and fm["t"] >= 3.0, lw["p_one_sided"] < 0.05, rw["rejected"]["Mkt-RF"], eras >= 3]
    verdict = "EARNS ALPHA" if all(crit) else "NO ALPHA SURVIVES"
    assert art["decision"]["verdict"] == verdict, "recorded verdict does not follow the registered rule"
    assert art["n_trials"] == 202
    print(f"X47d reveal ran the sealed code from the committed manifest; verdict {verdict} "
          f"follows from its numbers (criteria {crit})")
print("GATE X47 PASSED")
