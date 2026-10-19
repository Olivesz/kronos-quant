#!/usr/bin/env python3
"""Write numbers.tex: every number the DESIGN29 working paper cites, as a
LaTeX macro derived from the committed research artifacts. The paper's text
types no measured number by hand, so a re-run cannot leave it stale.

Sources: research/volalpha_replication.json (Stage 1), research/volalpha.json
(Stage 2), research/forensics.json and research/trials.json (trial ledger).

Run:  python make_numbers.py            (writes numbers.tex)
      python make_numbers.py --check    (exit 1 if numbers.tex is stale)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
R = ROOT / "research"


def load(name):
    with open(R / f"{name}.json") as fh:
        return json.load(fh)


rep, va, fo = load("volalpha_replication"), load("volalpha"), load("forensics")
NAMES = {"Mkt-RF": "Mkt", "SMB": "SMB", "HML": "HML", "RMW": "RMW", "CMA": "CMA", "UMD": "Mom", "BAB": "BAB"}
LABEL = {"Mkt-RF": "Mkt", "SMB": "SMB", "HML": "HML", "RMW": "RMW", "CMA": "CMA", "UMD": "UMD", "BAB": "BAB"}
macros = {}


def num(x, d=2, sign=False):
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    if s.startswith("-"):
        return r"\ensuremath{-" + s[1:] + "}"
    if s.startswith("+"):
        return r"\ensuremath{+" + s[1:] + "}"
    return s


def pct(x, d=2, sign=False):
    return num(100 * x, d, sign)


def put(name, value):
    assert name.isalpha(), name
    assert name not in macros, name
    macros[name] = value


# ---- Stage 1 ----------------------------------------------------------------
PUB_MM = {"Mkt-RF": (4.86, 1.56, 0.61), "UMD": (12.51, 1.71, 0.47), "SMB": (-0.58, 0.91, 0.62),
          "HML": (1.97, 1.02, 0.57), "RMW": (2.44, 0.83, 0.62), "CMA": (0.38, 0.67, 0.68)}
rows = []
for k in ("Mkt-RF", "UMD", "SMB", "HML", "RMW", "CMA"):
    r, (a, se, b) = rep["mm_table1"][k], PUB_MM[k]
    n = NAMES[k]
    put(f"mm{n}A", pct(r["alpha"]))
    put(f"mm{n}SE", pct(r["se"]))
    put(f"mm{n}B", num(r["beta"]))
    put(f"mm{n}N", f"{r['n']:,}")
    tol = 0.75 * se if k in ("Mkt-RF", "UMD") else se
    rows.append(f"{LABEL[k]} & {num(a)} & ({se:.2f}) & {num(b)} & {pct(r['alpha'])} & ({pct(r['se'])}) & "
                f"{num(r['beta'])} & {r['n']:,} & {tol:.2f} \\\\")
put("tabMM", "\n".join(rows))
t1, t5 = rep["cowy_table1"], rep["cowy_table5"]
for k in ("Mkt-RF", "UMD"):
    n = NAMES[k]
    put(f"cowy{n}SRo", num(t1[k]["sr_original"]))
    put(f"cowy{n}SRm", num(t1[k]["sr_managed"]))
    put(f"cowy{n}D", num(t1[k]["sr_diff"], sign=True))
    put(f"cowy{n}Comb", num(t5[k]["sr_combination"]))
    put(f"cowy{n}Orig", num(t5[k]["sr_original"]))
    put(f"cowy{n}TD", num(t5[k]["sr_diff"], sign=True))
    put(f"cowy{n}P", num(t5[k]["p_jk"]))
put("cowyMktSpan", "--".join(t5["Mkt-RF"]["span"]))
L = rep["ltz_realtime_c"]
put("ltzDDrt", pct(L["max_dd_realtime_c"], 1))
put("ltzDDfs", pct(L["max_dd_fullsample_c"], 1))
put("ltzDDmkt", pct(L["max_dd_market"], 1))
put("ltzA", pct(L["alpha_realtime_c"]["alpha"]))
put("ltzSE", pct(L["alpha_realtime_c"]["se"]))
put("ltzT", num(L["alpha_realtime_c"]["alpha"] / L["alpha_realtime_c"]["se"], 1))
put("ltzLev", num(L["max_leverage_realtime_c"], 1))
put("ltzSpan", "--".join(L["span"]))

# ---- Stage 2 ----------------------------------------------------------------
u, fm, lw, rw = va["univariate"], va["full_model"], va["ledoit_wolf"], va["romano_wolf"]
m = "Mkt-RF"
put("mktUniA", pct(u[m]["alpha"]))
put("mktUniT", num(u[m]["t"]))
put("mktUniB", num(u[m]["betas"]["Mkt-RF"]))
put("mktUniSpan", "--".join(u[m]["span"]))
put("mktUniN", f"{u[m]['n']:,}")
put("mktFullA", pct(fm[m]["alpha"]))
put("mktFullT", num(fm[m]["t"]))
put("mktFullRsq", num(fm[m]["r2"]))
put("mktFullSpan", "--".join(fm[m]["span"]))
for c, v in fm[m]["betas"].items():
    put("mktFullB" + NAMES[c], num(v))
put("mktSRm", num(lw[m]["sr_a"]))
put("mktSRr", num(lw[m]["sr_b"]))
put("mktSRd", num(lw[m]["diff_annual"], sign=True))
put("mktLWp", f"{lw[m]['p_one_sided']:.3f}")
put("mktRWp", num(rw["p_adj"][m]))
put("rwSpan", "--".join(rw["span"]))
put("rwN", str(rw["n"]))
put("spaP", f"{va['spa']['p']:.4f}")
eras = []
for span, v in va["eras"].items():
    lab = f"{span[:4]}--{span.split('..')[1][:4]}"          # "1927-07..1945-12" -> 1927--1945
    eras.append(f"{lab} & {pct(v['alpha'])} & ({num(v['t'])}) & {v['n']} \\\\")
put("tabEras", "\n".join(eras))
put("erasPos", str(va["decision"]["eras_positive"]))
sw = va["sup_wald"]
put("swStat", num(sw["sup_wald"]))
put("swAt", sw["break_at"])
put("swP", f"{sw['p']:.3f}")
crit = va["decision"]["criteria"]
put("verdict", va["decision"]["verdict"])
put("critOne", "holds" if crit["1_full_model_t_ge_3"] else "fails")
put("critTwo", "holds" if crit["2_lw_p_lt_0.05"] else "fails")
put("critThree", "holds" if crit["3_romano_wolf"] else "fails")
put("critFour", "holds" if crit["4_eras_3_of_4"] else "fails")
co = va["costs"]
put("turnover", num(co["annual_turnover"]))
put("breakevenUni", num(co["breakeven_bp_univariate"], 0))
put("breakevenFull", num(co["breakeven_bp_full_model"], 0))
put("meanExposure", num(co["mean_exposure"]))
put("shareCap", pct(co["share_at_cap"], 1))
put("emHalfTickBp", num(0.125 / 6000 * 1e4, 2))
g = va["grid_sharpe"]
put("gridSRmin", num(min(g.values()), 3))
put("gridSRmax", num(max(g.values()), 3))
put("gridSRprim", num(g["tilt0.15_cap1.5_brakeson"], 3))
put("gridPBO", num(va["pbo_grid"]["pbo"]))
put("gridCombos", f"{va['pbo_grid']['n_combos']:,}")
d = va["dsr_program_sr0"]
put("dsrProg", num(d["dsr"]))
put("dsrSRzero", num(d["sr0_annual"], 3))
put("nTrials", str(va["n_trials"]))
put("repoPBO", num(fo["pbo"]["pbo"]))
put("repoDSR", num(fo["dsr"]["dsr"]))
put("repoVariants", str(fo["pbo"]["n_variants"]))
dt = va["robust_dtb3"]
put("dtbUniA", pct(dt["univariate"]["alpha"]))
put("dtbUniT", num(dt["univariate"]["t"]))
put("dtbFullA", pct(dt["full_model"]["alpha"]))
put("dtbFullT", num(dt["full_model"]["t"]))
put("dtbSpread", pct(dt["mean_spread_ann"]))
c = va["contaminated"]
put("conA", pct(c["univariate"]["alpha"]))
put("conT", num(c["univariate"]["t"], 1))
put("conSRm", num(c["sr_managed"]))
put("conSRr", num(c["sr_raw"]))
put("conSpan", "--".join(c["span"]))
put("vixHold", num(va["vix"]["corr_holdout"]))
put("vixCon", num(va["vix"]["corr_contaminated"]))
fam = []
for k in ("SMB", "HML", "RMW", "CMA", "UMD", "BAB"):
    n = NAMES[k]
    put(f"fam{n}A", pct(fm[k]["alpha"]))
    put(f"fam{n}T", num(fm[k]["t"]))
    p = lw[k]["p_one_sided"]
    pl = "$<$0.001" if p < 0.001 else f"{p:.3f}"
    q = rw["p_adj"][k]
    ql = "$<$0.001" if q < 0.001 else f"{q:.3f}"
    sc = va["family_scale"][k]["median_scale"]
    fam.append(f"{LABEL[k]} & {pct(u[k]['alpha'])} & ({num(u[k]['t'])}) & {pct(fm[k]['alpha'])} & "
               f"({num(fm[k]['t'])}) & {ql} & {num(lw[k]['sr_b'])} & "
               f"{num(lw[k]['sr_a'])} & {pl} & {sc:.1f} \\\\")
put("tabFamily", "\n".join(fam))
sc = [v["median_scale"] for v in va["family_scale"].values()]
put("scaleMin", num(min(sc), 1))
put("scaleMax", num(max(sc), 1))

body = ["% Generated by make_numbers.py from research/*.json. Do not edit by hand."]
body += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in macros.items()]
text = "\n".join(body) + "\n"
target = HERE / "numbers.tex"
if "--check" in sys.argv:
    if not target.exists() or target.read_text() != text:
        print("numbers.tex is stale: run make_numbers.py")
        sys.exit(1)
    print(f"numbers.tex current ({len(macros)} macros)")
else:
    target.write_text(text)
    print(f"wrote numbers.tex ({len(macros)} macros)")
