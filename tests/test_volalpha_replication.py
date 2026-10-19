"""Gate X46 (DESIGN29 Stage 1): the replication machinery, and the replication.

a. Moreira-Muir identities: std(f^σ) = std(f); RV² is demeaned within the month;
   α scales with the factor and its t-statistic does not.
b. Size and power of the spanning test on synthetic monthly worlds built from
   daily returns with persistent log-volatility: where the risk-return trade-off
   is proportional (μ_t = γσ_t², so buy-and-hold is efficient) the White t
   rejects near its nominal 5%; where μ is constant it finds the alpha.
c. Cederburg et al.'s real-time combination is causal (perturbing data from
   month s on leaves every position through s unchanged), respects its cap,
   and matches a hand computation; the Jobson-Korkie test has its size.
d. The vendor loaders fail closed: a flipped byte is refused, a missing file
   raises VendorUnavailable, French's CSV and AQR's xlsx parse to the values
   written, and Saturday sessions compound into the next observation.
e. The replication itself, against the tolerances registered in DESIGN29
   (fixed before any Stage-1 number existed). With the archived vendor files
   present it is recomputed and must equal the committed artifact; without them
   (CI: third-party files are not committed) the registered tolerances are
   re-applied to the committed artifact, whose input digest must equal the
   committed manifest's. The mode that ran is printed.
"""
import hashlib
import io
import json
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from kronos import factors as F
from kronos import volmanaged as V

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def world(rng, T, proportional, phi=0.9, eta=0.2, gamma=3.0, mu=0.006):
    """Monthly factor and RV² from 21 daily returns a month, log-vol AR(1)."""
    idx = pd.period_range("1900-01", periods=T, freq="M")
    lv = np.empty(T)
    lv[0] = np.log(0.045)
    for t in range(1, T):
        lv[t] = np.log(0.045) * (1 - phi) + phi * lv[t - 1] + eta * rng.standard_normal()
    s = np.exp(lv)
    m = gamma * s ** 2 if proportional else np.full(T, mu)
    daily = m[:, None] / 21 + s[:, None] / np.sqrt(21) * rng.standard_normal((T, 21))
    f = pd.Series(daily.sum(1), index=idx)
    rv = pd.Series(((daily - daily.mean(1, keepdims=True)) ** 2).sum(1), index=idx)
    return f, rv, daily


# ---- a. identities -------------------------------------------------------
rng = np.random.default_rng(29)
f, rv, daily = world(rng, 600, False)
man, c = V.mm_managed(f, rv)
assert abs(man.std(ddof=1) - f.reindex(man.index).std(ddof=1)) < 1e-12, "c does not match std"
assert man.index[0] == f.index[1], "first managed month must follow the first RV month"
days = pd.date_range("2000-01-03", periods=63, freq="B")
x = pd.Series(rng.normal(0, 0.01, 63), index=days)
shifted = x + x.index.to_period("M").map({p: k * 0.003 for k, p in
                                          enumerate(x.index.to_period("M").unique())}).to_numpy()
assert np.allclose(F.monthly_rv(x), F.monthly_rv(shifted), atol=1e-15), "RV² is not demeaned"
r1 = V.spanning(man, f)
man3, _ = V.mm_managed(3 * f, rv)
r3 = V.spanning(man3, 3 * f)
assert abs(r3["alpha"] - 3 * r1["alpha"]) < 1e-12 and abs(r3["alpha"] / r3["se"] - r1["alpha"] / r1["se"]) < 1e-9
print("X46a std(f^σ) = std(f); RV² demeaned; α scales with f, its t does not")

# ---- b. size and power ---------------------------------------------------
rej = {}
for prop in (True, False):
    rng = np.random.default_rng(1)
    t = []
    for _ in range(200):
        f, rv, _ = world(rng, 1000, prop)
        r = V.spanning(V.mm_managed(f, rv)[0], f)
        t.append(r["alpha"] / r["se"])
    rej[prop] = float(np.mean(np.abs(np.array(t)) > 1.96))
assert rej[True] <= 0.10, f"size {rej[True]:.3f} under the proportional null"
assert rej[False] >= 0.80, f"power {rej[False]:.3f} with constant μ"
print(f"X46b spanning t: size {rej[True]:.3f} (proportional trade-off), "
      f"power {rej[False]:.3f} (constant μ), 200 worlds × 1000 months")

# ---- c. real-time combination --------------------------------------------
rng = np.random.default_rng(5)
f, rv, _ = world(rng, 400, False)
base = V.realtime_combination(f, rv, K=120)
s = 250
f2, rv2 = f.copy(), rv.copy()
f2.iloc[s:] = rng.normal(0, 0.1, len(f) - s)
rv2.iloc[s:] = rv2.iloc[s:] * rng.uniform(0.2, 5.0, len(f) - s)
pert = V.realtime_combination(f2, rv2, K=120)
cut = f.index[s]
assert base["y_combination"].loc[:cut].equals(pert["y_combination"].loc[:cut]), "position used future data"
assert base["y_original"].loc[:cut].equals(pert["y_original"].loc[:cut]), "original used future data"
assert not np.isclose(base["y_combination"].loc[f.index[s + 1]], pert["y_combination"].loc[f.index[s + 1]])
assert base["y_combination"].abs().max() <= 5.0 + 1e-12
tight = V.realtime_combination(f, rv, K=120, cap=0.5)
assert np.isclose(tight["y_combination"].abs().max(), 0.5) and (tight["y_combination"].abs() == 0.5).any()
# hand computation for the first out-of-sample month (index K, 2×2 inverse by formula)
fs, inv = f.iloc[1:].to_numpy(), 1.0 / rv.iloc[:-1].to_numpy()
K = 120
a_tr, f_tr = fs[:K] * inv[:K], fs[:K]
ch = f_tr.std(ddof=1) / a_tr.std(ddof=1)
m1, m2 = (ch * a_tr).mean(), f_tr.mean()
v11, v22 = (ch * a_tr).var(ddof=1), f_tr.var(ddof=1)
v12 = np.cov(ch * a_tr, f_tr, ddof=1)[0, 1]
det = v11 * v22 - v12 ** 2
w1, w2 = (v22 * m1 - v12 * m2) / det / 5.0, (v11 * m2 - v12 * m1) / det / 5.0
y_hand = np.clip(w1 * ch * inv[K] + w2, -5, 5)
assert abs(base["y_combination"].iloc[0] - y_hand) < 1e-12, "combination weight differs from hand formula"
rng = np.random.default_rng(8)
p = []
for _ in range(400):
    z = rng.standard_normal((600, 2)) @ np.linalg.cholesky([[1, 0.5], [0.5, 1]]).T
    p.append(V.jobson_korkie(0.01 + 0.05 * z[:, 0], 0.01 + 0.05 * z[:, 1]))
jk = float(np.mean(np.array(p) < 0.05))
assert 0.02 <= jk <= 0.09, f"Jobson-Korkie size {jk:.3f}"
print(f"X46c real-time combination causal through month s, cap holds and binds at 0.5, "
      f"hand-formula match; Jobson-Korkie size {jk:.3f}")

# ---- d. loaders fail closed ----------------------------------------------
def zipped(name, text):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(name, text)
    return b.getvalue()


ff_csv = ("This file was created by using the 209901 CRSP database.\n\n"
          ",Mkt-RF,SMB,HML,RF\n19300102,    1.25,   -0.50,    0.33,    0.01\n"
          "19300103,   -0.07,    0.10,  -99.99,    0.01\n\nCopyright\n")
sheet = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
         '<row r="1"><c r="A1" t="s"><v>0</v></c></row>'
         '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2" t="s"><v>2</v></c><c r="C2" t="s"><v>3</v></c></row>'
         '<row r="3"><c r="A3" t="s"><v>4</v></c><c r="C3"><v>-0.00767530191583</v></c></row>'
         '<row r="4"><c r="A4" t="s"><v>5</v></c><c r="B4"><v>0.5</v></c><c r="C4"><v>1.25E-3</v></c></row>'
         '</sheetData></worksheet>')
ss = "".join(f"<si><t>{t}</t></si>" for t in ["title", "DATE", "AUS", "USA", "12/02/1930", "12/03/1930"])
xb = io.BytesIO()
with zipfile.ZipFile(xb, "w") as z:
    z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
               '<sheet name="BAB Factors" sheetId="1" r:id="rId1"/></sheets></workbook>')
    z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
               '2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
    z.writestr("xl/sharedStrings.xml", '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
               + ss + "</sst>")
    z.writestr("xl/worksheets/sheet1.xml", sheet)
blobs = {"F-F_Research_Data_Factors_daily_CSV.zip": zipped("F-F_Research_Data_Factors_daily.csv", ff_csv),
         F.BAB: xb.getvalue()}
real_vendor, real_manifest = F.VENDOR, F.MANIFEST
with tempfile.TemporaryDirectory() as tmp:
    F.VENDOR, F.MANIFEST = tmp, os.path.join(tmp, "MANIFEST.json")
    for n, b in blobs.items():
        open(os.path.join(tmp, n), "wb").write(b)
    json.dump({"files": {n: {"url": "test", "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
                         for n, b in blobs.items()}}, open(F.MANIFEST, "w"))
    t = F._french_first_table("F-F_Research_Data_Factors_daily_CSV.zip")
    assert list(t.columns) == ["Mkt-RF", "SMB", "HML", "RF"] and len(t) == 2
    assert t.iloc[0, 0] == 0.0125 and np.isnan(t.iloc[1, 2]), "French parse or missing-value mask wrong"
    bab = F.bab_daily()
    assert list(bab.index.strftime("%Y-%m-%d")) == ["1930-12-02", "1930-12-03"]
    assert bab.iloc[0] == -0.00767530191583 and bab.iloc[1] == 1.25e-3, "BAB read the wrong column"
    bad = bytearray(blobs[F.BAB])
    bad[len(bad) // 2] ^= 1
    open(os.path.join(tmp, F.BAB), "wb").write(bytes(bad))
    try:
        F.bab_daily()
        raise AssertionError("a flipped byte was parsed")
    except ValueError as e:
        assert "does not match the manifest" in str(e)
    os.remove(os.path.join(tmp, F.BAB))
    try:
        F.bab_daily()
        raise AssertionError("a missing file was not reported")
    except F.VendorUnavailable:
        pass
F.VENDOR, F.MANIFEST = real_vendor, real_manifest
cal = pd.to_datetime(["1950-01-05", "1950-01-06", "1950-01-07", "1950-01-09", "1950-01-10"])
dd = pd.DataFrame({"a": [0.01, -0.02, 0.03, 0.01, 0.005]}, index=cal)
mg = F.merge_saturdays(dd)
assert not (mg.index.dayofweek == 5).any() and len(mg) == 4
assert abs(mg.loc["1950-01-09", "a"] - (1.03 * 1.01 - 1)) < 1e-15
assert abs((1 + mg["a"]).prod() - (1 + dd["a"]).prod()) < 1e-15
print("X46d manifest hash refuses a flipped byte, missing file -> VendorUnavailable; "
      "French/AQR parse exact; Saturdays compound into Monday")

# ---- e. the replication against DESIGN29's registered tolerances ----------
art = json.load(open(os.path.join(ROOT, "research", "volalpha_replication.json")))
assert art["input_digest"] == F.manifest_digest(), "artifact was built from a different input set"
try:
    import run_research
    fresh = json.loads(json.dumps(run_research.volalpha_replication(), default=float))
    mode = "recomputed from the archived vendor files"
except F.VendorUnavailable:
    fresh, mode = None, "artifact check (vendor files not in this checkout; recomputation is local)"


def same(a, b, path=""):
    if isinstance(a, dict):
        assert set(a) == set(b), f"{path}: keys differ"
        for k in a:
            if k != "code_digest":
                same(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (u, v) in enumerate(zip(a, b)):
            same(u, v, f"{path}[{i}]")
    elif isinstance(a, float):
        assert abs(a - b) <= 1e-10 * max(1.0, abs(b)), f"{path}: {a!r} != {b!r}"
    else:
        assert a == b, f"{path}: {a!r} != {b!r}"


if fresh is not None:
    same(fresh, art)

# registered in DESIGN29 (Stage 1; amendment 1 for the sample end)
MM = {"Mkt-RF": (4.86, 1.56, 0.61, 0.75, 0.06), "UMD": (12.51, 1.71, 0.47, 0.75, 0.06),
      "SMB": (-0.58, 0.91, 0.62, 1.0, None), "HML": (1.97, 1.02, 0.57, 1.0, None),
      "RMW": (2.44, 0.83, 0.62, 1.0, None), "CMA": (0.38, 0.67, 0.68, 1.0, None)}
N = {"Mkt-RF": 1065, "UMD": 1060, "SMB": 1065, "HML": 1065, "RMW": 621, "CMA": 621}
ok, lines = {}, []
for k, (a, se, b, ka, kb) in MM.items():
    r = art["mm_table1"][k]
    assert r["n"] == N[k], f"{k}: N {r['n']} != published {N[k]}"
    da, db = abs(100 * r["alpha"] - a), abs(r["beta"] - b)
    ok[k] = da <= ka * se and (kb is None or db <= kb)
    lines.append(f"{k} Δα {da:.2f}/{ka * se:.2f}" + (f" Δβ {db:.2f}/{kb}" if kb else ""))
t1, t5 = art["cowy_table1"], art["cowy_table5"]
cowy = {
    "T1 Mkt SRs": abs(t1["Mkt-RF"]["sr_managed"] - 0.51) <= 0.05
    and abs(t1["Mkt-RF"]["sr_original"] - 0.42) <= 0.05 and abs(t1["Mkt-RF"]["sr_diff"] - 0.09) <= 0.05,
    "T1 Mom diff": abs(t1["UMD"]["sr_diff"] - 0.50) <= 0.08,
    "T5 Mkt": abs(t5["Mkt-RF"]["sr_combination"] - 0.42) <= 0.06
    and abs(t5["Mkt-RF"]["sr_original"] - 0.46) <= 0.06
    and abs(t5["Mkt-RF"]["sr_diff"] + 0.04) <= 0.06 and t5["Mkt-RF"]["sr_diff"] <= 0,
}
others = sum(ok[k] for k in ("SMB", "HML", "RMW", "CMA"))
passed = ok["Mkt-RF"] and ok["UMD"] and others >= 3 and all(cowy.values())
ltz = art["ltz_realtime_c"]["max_dd_realtime_c"]
flag = "" if -0.95 <= ltz <= -0.60 else "  [DISCREPANCY: outside the registered 60–95% band]"
print(f"X46e mode: {mode}")
print("X46e R-MM  " + "; ".join(lines))
print(f"X46e R-COWY {cowy}; R-LTZ real-time-c Mkt MaxDD {ltz:.1%} (descriptive){flag}")
assert passed, f"REPLICATION FAILED — DESIGN29 stops here: R-MM {ok}, R-COWY {cowy}"
print("X46e REPLICATION PASSED under the registered rule (Mkt, Mom, "
      f"{others}/4 others, all three Cederburg Mkt checks)")
print("GATE X46 PASSED")
