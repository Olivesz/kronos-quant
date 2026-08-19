#!/usr/bin/env python3
"""Verify every derivable number in docs/paper/paper.tex against its source.

Sources of truth:
  * research/*.json           -- all measured values (the only numeric source)
  * kronos/decathlon.py       -- the battery's pass thresholds (code constants)

The paper's `% src:` comments name the source of each nearby claim; this
script (a) audits that every research JSON named in a src comment exists,
(b) re-derives every derivable number and asserts the tex cites it correctly
(match within half a unit in the last cited decimal place), and (c) checks
table rows -- scores, failed-event sets, and statistics -- cell by cell.

Numbers that are NOT derivable from the research JSONs (they trace to the
FINDINGS/DESIGN narrative) are listed in SKIPS at the bottom, with reasons,
so the residual is explicit.

Run:  make check   (or  ../../.venv/bin/python check_numbers.py)
Exit: 0 iff every check passes.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # docs/paper/
ROOT = HERE.parent.parent                          # repo root
RESEARCH = ROOT / "research"

TEX = (HERE / "paper.tex").read_text()
CODE = (ROOT / "kronos" / "decathlon.py").read_text()


def load(name):
    with open(RESEARCH / f"{name}.json") as fh:
        return json.load(fh)


D1 = load("decathlon")
D2 = load("decathlon2")
D3 = load("decathlon3")
D4 = load("decathlon4")
FX = load("fx")
CR = load("crypto")
REFLEX = load("reflex")
ROUGH = load("rough")
FORENSICS = load("forensics")

failures = []
n_checks = 0


def check(label, ok, detail=""):
    global n_checks
    n_checks += 1
    if not ok:
        failures.append(f"{label}: {detail}")
        print(f"  FAIL  {label}  {detail}")


def tol_of(cited_str):
    """Half a unit in the last cited decimal place (plus float slack)."""
    if "." in cited_str:
        d = len(cited_str.split(".")[1])
    else:
        d = 0
    return 0.5 * 10 ** (-d) + 1e-9


def cite(label, pattern, *actuals):
    """Regex with N capture groups of cited numbers; each must match the
    corresponding actual within half a unit of its cited precision."""
    m = re.search(pattern, TEX)
    if not m:
        check(label, False, f"pattern not found in tex: {pattern!r}")
        return
    groups = m.groups()
    if len(groups) != len(actuals):
        check(label, False, f"{len(groups)} captures != {len(actuals)} actuals")
        return
    for g, a in zip(groups, actuals):
        check(f"{label} [{g}]", abs(float(g) - a) <= tol_of(g),
              f"cited {g} vs actual {a:.6g}")


def row_cells(line_regex):
    """Find a single table-row line and split it into & cells."""
    m = re.search(line_regex, TEX)
    if not m:
        return None
    return [c.strip() for c in m.group(0).rstrip("\\").split("&")]


def cell_events(cell):
    return set(int(x) for x in re.findall(r"E(\d+)", cell))


def failed_set(events_dict):
    return set(int(re.match(r"E(\d+)_", k).group(1))
               for k, v in events_dict.items() if not v)


def check_row(label, line_regex, score, failed, bits, score_cell=1,
              events_cell=2, bits_cell=3):
    cells = row_cells(line_regex)
    if cells is None:
        check(label, False, f"row not found: {line_regex!r}")
        return
    m = re.search(r"(\d+)/10", cells[score_cell])
    check(f"{label} score", m and int(m.group(1)) == score,
          f"cited {cells[score_cell]!r} vs actual {score}/10")
    if failed is not None:
        check(f"{label} failed events", cell_events(cells[events_cell]) == failed,
              f"cited {sorted(cell_events(cells[events_cell]))} vs actual {sorted(failed)}")
    if bits is not None:
        g = re.search(r"[\d.]+", cells[bits_cell]).group(0)
        check(f"{label} E9 bits", abs(float(g) - bits) <= tol_of(g),
              f"cited {g} vs actual {bits:.6g}")


def check_stat_row(label, line_regex, actuals):
    """Numeric-only table row: every number in the row, in order."""
    m = re.search(line_regex, TEX)
    if not m:
        check(label, False, f"row not found: {line_regex!r}")
        return
    cited = re.findall(r"[-+]?\d+\.?\d*", m.group(0).rstrip("\\"))
    if len(cited) != len(actuals):
        check(label, False, f"{len(cited)} numbers in row, expected {len(actuals)}: {cited}")
        return
    for g, a in zip(cited, actuals):
        check(f"{label} [{g}]", abs(float(g) - a) <= tol_of(g),
              f"cited {g} vs actual {a:.6g}")


# ------------------------------------------------------------------ 0. src audit
print("== src-comment audit")
named = set(re.findall(r"([a-z0-9_]+)\.json", TEX))
for n in sorted(named):
    check(f"src json exists: {n}.json", (RESEARCH / f"{n}.json").exists())

# ------------------------------------------------------------- 1. battery code
print("== battery thresholds vs kronos/decathlon.py")
code_ws = re.sub(r"\s+", " ", CODE)
for label, pat in [
    ("E1 bounds", r'-0\.15 <= S\["ac1_r"\] <= 0\.05'),
    ("E2 bounds", r'4\.5 <= S\["kurt"\] <= 40\.0'),
    ("E3 bounds", r'S\["ac1_absr"\] >= 0\.12 and S\["ac_slow"\] >= 0\.05'),
    ("E4 bound", r'wc\["ac8_level"\] >= 0\.12'),
    ("E5 bound", r'S\["leverage"\] <= -0\.03'),
    ("E6 bound", r'S\["kurt_z"\] <= 5\.0'),
    ("E7 bound", r'S\["clock_skew_u"\] >= -0\.35'),
    ("E8 ratio", r'S\["ep_z"\] <= 0\.75 \* S\["ep_r"\]'),
    ("E10 sigma", r'rr < -2\.5 \* sd'),
    ("E10 bound", r'S\["tail_asym"\] >= 1\.25'),
]:
    check(f"code has {label}", re.search(pat, code_ws) is not None, pat)

for label, snippet in [
    ("appendix E1", "$[-0.15,\\ 0.05]$"),
    ("appendix E2", "$[4.5,\\ 40]$"),
    ("appendix E3", "$\\ge 0.12$ and $\\ge 0.05$"),
    ("appendix E4", "(weekly clock level) & $\\ge 0.12$"),
    ("appendix E5", "$\\le -0.03$"),
    ("appendix E6", "kurtosis$(z)$ & $\\le 5$"),
    ("appendix E7", "$\\ge -0.35$"),
    ("appendix E8", "\\le 0.75\\,\\mathrm{EP}(r)$"),
    ("appendix E10", "$\\ge 1.25$"),
]:
    check(f"appendix states {label}", snippet in TEX, repr(snippet))

# ------------------------------------------------------------ 2. calibration
print("== calibration (decathlon.json)")
spy, G = D1["spy"]["stats"], D1["configs"]["G"]["median_stats"]
FCVM = D1["configs"]["FCVM"]["median_stats"]
check("SPY score 10", D1["spy"]["score"] == 10)
check("GBM score 3", D1["configs"]["G"]["score"] == 3)
check("GBM passes exactly E1,E6,E9",
      failed_set(D1["configs"]["G"]["events"]) == {2, 3, 4, 5, 7, 8, 10})
for cfg, score in [("F", 3), ("FC", 1), ("FV", 5), ("FCVM", 5), ("FCVMH", 4)]:
    check(f"{cfg} score {score}", D1["configs"][cfg]["score"] == score)
check("FCVM failed events = {3,4,7,8,9}",
      failed_set(D1["configs"]["FCVM"]["events"]) == {3, 4, 7, 8, 9})

check_stat_row("tab:fcvm SPY", r"SPY \(real\) *&.*?\\\\",
               [spy["ac1_r"], spy["kurt"], spy["ac1_absr"], spy["leverage"], spy["dir_bits"]])
check_stat_row("tab:fcvm GBM", r"GBM \(G\) *&.*?\\\\",
               [G["ac1_r"], G["kurt"], G["ac1_absr"], G["leverage"], G["dir_bits"]])
check_stat_row("tab:fcvm FCVM", r"\\cfg{FCVM} \(best flow-only\).*?\\\\",
               [FCVM["ac1_r"], FCVM["kurt"], FCVM["ac1_absr"], FCVM["leverage"], FCVM["dir_bits"]])

cite("§2 FCVM vs SPY bits",
     r"E9: ([\d.]+) significant direction bits against\s*SPY's ([\d.]+)",
     FCVM["dir_bits"], spy["dir_bits"])
cite("§2 sign-leak definition",
     r"leaks ([\d.]+\d) bits where real\s*SPY shows ([\d.]+\d)",
     FCVM["dir_bits"], spy["dir_bits"])

# --------------------------------------------------------- 3. experiment I
print("== experiment I (decathlon2.json)")
t = D2["tuning"]
check("first shot params", (t["first_shot"]["kA"], t["first_shot"]["capA"],
                            t["first_shot"]["sA"]) == (0.5, 0.02, 0.002))
check("first shot score 4", t["first_shot"]["score"] == 4)
check("grid best 5", t["grid_best_score"] == 5)
check("frozen params", (D2["frozen_params"]["kA"], D2["frozen_params"]["capA"],
                        D2["frozen_params"]["sA"]) == (0.25, 0.01, 0.001))
cite("§3 first-shot cite",
     r"\(k_A, \\mathrm{cap}_A, s_A\) = \(([\d.]+), ([\d.]+), ([\d.]+)\)",
     0.5, 0.02, 0.002)
cite("§3 frozen cite", r"selected \$\(([\d.]+), ([\d.]+), ([\d.]+)\)\$",
     0.25, 0.01, 0.001)

c2 = D2["configs"]
check_row("tab:deca2 FCVM", r"\\cfg{FCVM} \(control\).*?\\\\",
          c2["FCVM"]["score"], failed_set(c2["FCVM"]["events"]),
          c2["FCVM"]["median_stats"]["dir_bits"])
check_row("tab:deca2 FCVM+A", r"\\cfg{FCVM\+A} \(hypothesis\).*?\\\\",
          c2["FCVM+A"]["score"], failed_set(c2["FCVM+A"]["events"]),
          c2["FCVM+A"]["median_stats"]["dir_bits"])
check_row("tab:deca2 FV+A", r"\\cfg{FV\+A} .*?\\\\",
          c2["FV+A"]["score"], failed_set(c2["FV+A"]["events"]),
          c2["FV+A"]["median_stats"]["dir_bits"])
check_row("tab:deca2 F+A", r"\\cfg{F\+A} \(no targeters\).*?\\\\",
          c2["F+A"]["score"], None, None)
check("F+A failure set == F's (the '= F exactly' claim)",
      failed_set(c2["F+A"]["events"]) == failed_set(D1["configs"]["F"]["events"]))
cite("§3 one-layer medians",
     r"medians \$([\d.]+) \\to ([\d.]+)\$; the paired per-seed",
     c2["FCVM"]["median_stats"]["dir_bits"], c2["FCVM+A"]["median_stats"]["dir_bits"])

# --------------------------------------------------------- 4. experiment II
print("== experiment II (decathlon3.json)")
b = D3["forecastable_flow_fraction_vs_K"]
betas = (b["K0"]["toy_beta"], b["K1"]["toy_beta"], b["K5"]["toy_beta"])
for lab, pat in [
    ("§3 toy damping", r"from ([\d.]+) to ([\d.]+) per unit"),
]:
    cite(lab, pat, betas[0], betas[1])
cite("§4 contraction cite",
     r"\\beta_K = ([\d.]+) \\to ([\d.]+) \\to ([\d.]+)\$ at \$K = 0", *betas)
check("toy betas match theory", all(
    abs(b[f"K{k}"]["toy_beta"] - b[f"K{k}"]["theory"]) < 5e-5 for k in (0, 1, 5)))

bits = D3["dir_bits_vs_K"]
med = {k: bits[k]["median"] for k in bits}
cite("§4 result medians",
     r"falls \$1\.000 \\to 0\.750 \\to 0\.237\$ while the\s*market-space sign leak rises \$([\d.]+) \\to ([\d.]+) \\to ([\d.]+)\$ bits",
     med["K0_FCVM"], med["K1_DECA2"], med["K5_FIXEDPOINT"])
k0s, k1s, k5s = (bits["K0_FCVM"]["per_seed"], bits["K1_DECA2"]["per_seed"],
                 bits["K5_FIXEDPOINT"]["per_seed"])
check("K5>K0 on 7 of 8 paired seeds",
      sum(a > b_ for a, b_ in zip(k5s, k0s)) == 7)
check("K1 vs K0 paired split 4-4",
      sum(a > b_ for a, b_ in zip(k1s, k0s)) == 4)
check("intro cites 7 of 8", "7 of 8\npaired seeds" in TEX or "7 of 8 paired seeds" in TEX.replace("\n", " "))

c3 = D3["configs"]
check_row("tab:deca3 K0", r"\$K{=}0\$ \(\\cfg{FCVM}, control\).*?\\\\",
          c3["K0_FCVM"]["score"], failed_set(c3["K0_FCVM"]["events"]),
          med["K0_FCVM"])
check_row("tab:deca3 K1", r"\$K{=}1\$ \(Exp\..*?\\\\",
          c3["K1_DECA2"]["score"], failed_set(c3["K1_DECA2"]["events"]),
          med["K1_DECA2"])
check_row("tab:deca3 K5 frozen", r"\$K{=}5\$ \(frozen carry-over\).*?\\\\",
          c3["K5_FIXEDPOINT"]["score"], failed_set(c3["K5_FIXEDPOINT"]["events"]),
          med["K5_FIXEDPOINT"])
check_row("tab:deca3 K5 tuned", r"\$K{=}5\$ \(tuned, contingent pass\).*?\\\\",
          D3["tuned_eval"]["score"], failed_set(D3["tuned_eval"]["events"]),
          D3["tuned_eval"]["median_stats"]["dir_bits"])

m1, m5 = c3["K1_DECA2"]["median_stats"], c3["K5_FIXEDPOINT"]["median_stats"]
cite("§4 regression ac1", r"AC\$_1\$: \$(-[\d.]+) \\to (-[\d.]+)\$, breaking E1",
     m1["ac1_r"], m5["ac1_r"])
cite("§4 regression leverage", r"E5 dies, \$(-[\d.]+) \\to (-[\d.]+)\$",
     m1["leverage"], m5["leverage"])
cite("§4 regression kurt", r"kurtosis \$([\d.]+) \\to ([\d.]+)\$\) and crash",
     m1["kurt"], m5["kurt"])
cite("§4 regression tail", r"ratio \$([\d.]+) \\to ([\d.]+)\$\)",
     m1["tail_asym"], m5["tail_asym"])

grid3 = {(g["kA"], g["capA"]): g["score"] for g in D3["tuning"]["grid"]}
check("DECA3 grid winner kA=0.05 among tied best",
      grid3[(0.05, 0.005)] == 5 and max(grid3.values()) == 5)
cite("§4 tuned kA", r"\$k_A = ([\d.]+)\$, an effective stack strength", 0.05)
cite("§4 effective strength", r"1 - 0\.95\^5 = ([\d.]+)\$", 1 - 0.95 ** 5)

# -------------------------------------------------------- 5. experiment III
print("== experiment III (decathlon4.json)")
toy = D4["toy_leak_corr_vs_lambda"]
cite("§5 toy corr", r"collapses from \$\+([\d.]+)\$ to\s*\$-([\d.]+)\$",
     toy["lam0.0"], -toy["lam1.0"])
c4 = D4["configs"]
bits4 = {k: D4["dir_bits_vs_lambda"][k]["median"] for k in D4["dir_bits_vs_lambda"]}
check_row("tab:deca4 FCVM", r"\\cfg{FCVM} \(control\) +& 5/10.*?\\\\",
          c4["FCVM"]["score"], failed_set(c4["FCVM"]["events"]), bits4["FCVM"])
check_row("tab:deca4 Q1.0", r"\\cfg{FCVM\+Q}\(\$\\lambda_Q{=}1\.0\$\).*?\\\\",
          c4["FCVM+Q1.0"]["score"], None, bits4["FCVM+Q1.0"], bits_cell=3)
check("Q1.0 fails all but E6",
      failed_set(c4["FCVM+Q1.0"]["events"]) == {1, 2, 3, 4, 5, 7, 8, 9, 10})
check_row("tab:deca4 Q0.5", r"\\cfg{FCVM\+Q}\(\$\\lambda_Q{=}0\.5\$\).*?\\\\",
          c4["FCVM+Q0.5"]["score"], failed_set(c4["FCVM+Q0.5"]["events"]),
          bits4["FCVM+Q0.5"])
cp = D4["contingent_pass"]
check_row("tab:deca4 tuned", r"\\cfg{FCVM\+Q}\(\$\\lambda_Q{=}0\.05\$\).*?\\\\",
          cp["tuned_eval"]["score"], failed_set(cp["tuned_eval"]["events"]),
          cp["tuned_eval"]["median_stats"]["dir_bits"])
check("tuned winner lambda 0.05", cp["winner_lambda"] == 0.05)
check("grid flat 5 up to 0.30 and 4 at 0.40",
      all(cp["grid"][f"lam{l}"] == 5 for l in ("0.05", "0.1", "0.15", "0.2", "0.3"))
      and cp["grid"]["lam0.4"] == 4)

q1s, fs = (D4["dir_bits_vs_lambda"]["FCVM+Q1.0"]["per_seed"],
           D4["dir_bits_vs_lambda"]["FCVM"]["per_seed"])
check("Q1.0 > control on 7 of 8 seeds", sum(a > b_ for a, b_ in zip(q1s, fs)) == 7)
cite("§5 bits half vs control", r"flat at half skew \(([\d.]+) versus ([\d.]+)\)",
     bits4["FCVM+Q0.5"], bits4["FCVM"])
cite("§5 bits full", r"grow} at full skew \(([\d.]+),", bits4["FCVM+Q1.0"])

mF, mQ1 = c4["FCVM"]["median_stats"], c4["FCVM+Q1.0"]["median_stats"]
cite("wildfacts kurt (all occurrences share values)", r"kurtosis\s*\$([\d.]+) \\to ([\d.]+)\$", mF["kurt"], mQ1["kurt"])
cite("wildfacts leverage", r"\$(-0\.125) \\to (-0\.008)\$",
     mF["leverage"], mQ1["leverage"])
cite("§5 tail ratio", r"ratio \$(40) \\to (1\.1)\$", mF["tail_asym"], mQ1["tail_asym"])
cite("§5 clustering", r"AC\$_1\(\|r\|\)\$\s*\$([\d.]+) \\to ([\d.]+)\$",
     mF["ac1_absr"], mQ1["ac1_absr"])
cite("§5 efficiency break", r"AC\$_1\$: \$\+([\d.]+) \\to (-[\d.]+)\$",
     mF["ac1_r"], mQ1["ac1_r"])

# ------------------------------------------------------------- 6. triangle
print("== the triangle (fx.json / crypto.json)")
lc, cc = FX["leverage_contrast"], CR["leverage_contrast"]
check_stat_row("tab:triangle leverage row",
               r"leverage effect & \$-0\.0405.*?\\\\",
               [lc["equity_mean"], lc["equity_spread"], lc["fx_leverage"],
                lc["fx_sd"], cc["crypto_leverage"], cc["crypto_sd"]])
check_stat_row("tab:triangle z vs zero (derived)",
               r"\$z\$ vs\.\\ zero &.*?\\\\",
               [lc["equity_mean"] / lc["equity_spread"], lc["z_fx_vs_zero"],
                cc["crypto_leverage"] / cc["crypto_sd"]])
check_stat_row("tab:triangle z vs FX", r"\$z\$ vs\.\\ FX &.*?\\\\",
               [lc["z_fx_vs_equities"], lc["z_crypto_vs_fx"]])
n_pos_pairs = sum(v > 0 for v in FX["per_pair_leverage"].values())
n_pos_coins = sum(v > 0 for v in CR["per_coin_leverage"].values())
check("n_pairs_positive field consistent", FX["n_pairs_positive"] == n_pos_pairs == 7)
check("8 of 10 coins positive", n_pos_coins == 8)
check("0 of 4 equity markets positive",
      sum(v > 0 for v in lc["equity_values"].values()) == 0)
check_stat_row("tab:triangle instruments row",
               r"instruments positive &.*?\\\\",
               [0, 4, n_pos_pairs, len(FX["per_pair_leverage"]),
                n_pos_coins, len(CR["per_coin_leverage"])])

eqv = lc["equity_values"]
cite("§7 equity range", r"all four universes \(\$(-0\.030)\$ to\s*\$(-0\.047)\$\)",
     max(eqv.values()), min(eqv.values()))
cite("§7 fx zero", r"statistically zero \(\$\+([\d.]+)\$, \$z\$ vs\.\\ zero \$= ([\d.]+)\$",
     lc["fx_leverage"], lc["z_fx_vs_zero"])
check("§7 '7 of 13 pairs positive'", "7 of 13 pairs positive" in TEX)
cite("§7 crypto", r"sits at \$\+([\d.]+)\$, with 8 of 10 coins", cc["crypto_leverage"])
cite("§7 BTC/ETH", r"BTC \(\$(-[\d.]+)\$\) and ETH \(\$(-[\d.]+)\$\)",
     CR["per_coin_leverage"]["BTC-USD"], CR["per_coin_leverage"]["ETH-USD"])
cite("§7 yen pairs",
     r"AUDJPY\s*\$(-[\d.]+)\$,\s*GBPJPY\s*\$(-[\d.]+)\$,\s*EURJPY\s*\$(-[\d.]+)\$",
     FX["per_pair_leverage"]["AUDJPY=X"], FX["per_pair_leverage"]["GBPJPY=X"],
     FX["per_pair_leverage"]["EURJPY=X"])
cite("§7 USDMXN", r"USDMXN\s*\(\$\+([\d.]+)\$", FX["per_pair_leverage"]["MXN=X"])
cite("§7 z equity edge", r"\$z = ([\d.]+)\$ against FX, \$z = ([\d.]+)\$ against crypto",
     lc["z_fx_vs_equities"], cc["z_vs_equities"])
cite("§7 z fx-crypto", r"FX--crypto edge is \$z = ([\d.]+)\$", lc["z_crypto_vs_fx"])
cite("abstract equities", r"equities \(\$(-0\.04)\$\)", lc["equity_mean"])
cite("abstract crypto", r"crypto \(\$\+(0\.03)\$\)", cc["crypto_leverage"])

# ------------------------------------------------------- 7. methods/related
print("== methods and related work")
cite("§8 PBO", r"its PBO of ([\d.]+) is restated", FORENSICS["pbo"]["pbo"])
cite("§9 branching raw", r"branching ratio \$([\d.]+)\$ across 48 US assets",
     REFLEX["median_n_raw"])
check("48 assets", len(REFLEX["per_asset"]) == 48)
cite("§9 branching deformed", r"collapses to \$([\d.]+)\$", REFLEX["median_n_def"])
cite("§9 rough H", r"H \\approx ([\d.]+)\$ on 16", ROUGH["daily"]["H"])
check("§9 FC score cited",
      re.search(r"destroy efficiency, scoring 1/10", TEX) is not None
      and D1["configs"]["FC"]["score"] == 1)

# ----------------------------------------------------------- 8. appendix
print("== appendix stat table (decathlon.json)")
rows = [
    (r"\$\\mathrm{AC}_1\(r\)\$ +& E1.*?\\\\", "ac1_r", 1),
    (r"kurtosis\$\(r\)\$ +& E2.*?\\\\", "kurt", 2),
    (r"\$\\mathrm{AC}_1\(\|r\|\)\$ +& E3.*?\\\\", "ac1_absr", 3),
    (r"mean \$\\mathrm{AC}_{5\.\.20}\(\|r\|\)\$ & E3.*?\\\\", "ac_slow", (5, 20, 3)),
    (r"\$\\mathrm{AC}_8\(w\)\$ +& E4.*?\\\\", "clock_ac8_level", (8, 4)),
    (r"leverage +& E5.*?\\\\", "leverage", 5),
    (r"kurtosis\$\(z\)\$ +& E6.*?\\\\", "kurt_z", 6),
    (r"skew\$\(u\)\$ +& E7.*?\\\\", "clock_skew_u", 7),
    (r"\$\\mathrm{EP}\(r\)\$ bits +& E8.*?\\\\", "ep_r", 8),
    (r"\$\\mathrm{EP}\(z\)\$ bits +& E8.*?\\\\", "ep_z", 8),
    (r"direction bits +& E9.*?\\\\", "dir_bits", 9),
    (r"tail asymmetry +& E10.*?\\\\", "tail_asym", 10),
]
for pat, key, _ in rows:
    m = re.search(pat, TEX)
    if not m:
        check(f"appendix row {key}", False, f"row not found: {pat!r}")
        continue
    cells = [c.strip() for c in m.group(0).rstrip("\\").split("&")]
    for cell, actual, who in zip(cells[-3:], (spy[key], G[key], FCVM[key]),
                                 ("SPY", "GBM", "FCVM")):
        g = re.search(r"[-+]?\d+\.?\d*", cell).group(0)
        check(f"appendix {key} {who}", abs(float(g) - actual) <= tol_of(g),
              f"cited {g} vs actual {actual:.6g}")

check("appendix EP ratio claim (SPY 33% below)",
      abs((1 - spy["ep_z"] / spy["ep_r"]) - 0.33) < 0.005
      and re.search(r"33\\% below", TEX) is not None)
check("appendix 6x direction bits",
      6 <= FCVM["dir_bits"] / spy["dir_bits"] < 7
      and re.search(r"\$6\\times\$ SPY's direction bits", TEX) is not None)
check("appendix GBM skew floor cited",
      re.search(r"\(\$-0\.651\$\)", TEX) is not None
      and abs(G["clock_skew_u"] - (-0.651)) <= 0.0005)
check("appendix SPY skew cited",
      re.search(r"\(SPY \$-0\.221\$\)", TEX) is not None
      and abs(spy["clock_skew_u"] - (-0.221)) <= 0.0005)

# --------------------------------------------------------- 9. protocol facts
print("== protocol facts")
check("T=6000 in budgets", D3["budget"]["T"] == 6000 and D4["budget"]["T"] == 6000
      and "$T = 6000$" in TEX)
check("eval seeds 100-107", D3["budget"]["seeds"] == "100-107"
      and "100--107" in TEX)
check("tuning seeds 900-903", D2["tuning"]["seeds"] == "900-903"
      and "900--903" in TEX)

# cross-file byte-identity claims made in the paper
check("FCVM control shared across DECA3/DECA4 (byte-identity claim)",
      D3["dir_bits_vs_K"]["K0_FCVM"]["per_seed"]
      == D4["dir_bits_vs_lambda"]["FCVM"]["per_seed"])
check("DECA3 K=1 reproduces DECA2's layer (byte-identity claim)",
      abs(D3["dir_bits_vs_K"]["K1_DECA2"]["median"]
          - D2["configs"]["FCVM+A"]["median_stats"]["dir_bits"]) < 1e-6)

# ------------------------------------------------------------------ SKIPS
SKIPS = [
    ("§3 tuning-grid mechanism numbers (AC1 -0.09→-0.35, kurt 8.8→4.6, "
     "bits 0.039 at kA=1)", "decathlon2.json stores only grid scores; "
     "narrative source docs/FINDINGS.md DECATHLON-2 (logged in REVIEW-NOTES)"),
    ("§7 spurious-leverage bound |0.04| (gate X26)",
     "gate constant lives in tests/, narrative in FINDINGS KRONOS-CRYPTO/FX"),
    ("appendix GJR-GARCH clock AC8 ≈ 0.06",
     "calibration-phase measurement recorded in DESIGN8/code comments only"),
    ("§9 toy corr exact values in src comment (0.6575 → -0.0583)",
     "checked above at cited 2-dp precision; exact values asserted here:"),
]
check("src-comment exact toy corr", abs(toy["lam0.0"] - 0.6575) < 5e-5
      and abs(toy["lam1.0"] - (-0.0583)) < 5e-5)

print()
for s, why in SKIPS:
    print(f"  SKIP  {s}\n        ({why})")
print()
if failures:
    print(f"FAILED: {len(failures)} of {n_checks} checks")
    sys.exit(1)
print(f"PASS: all {n_checks} checks against research/*.json and kronos/decathlon.py")
