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
    """Numeric-only table row: every number in the row, in order.
    En/em dashes (`--`, `---`) are separators, not minus signs."""
    m = re.search(line_regex, TEX)
    if not m:
        check(label, False, f"row not found: {line_regex!r}")
        return
    cited = re.findall(r"[-+]?\d+\.?\d*", m.group(0).rstrip("\\").replace("--", " "))
    if len(cited) != len(actuals):
        check(label, False, f"{len(cited)} numbers in row, expected {len(actuals)}: {cited}")
        return
    for g, a in zip(cited, actuals):
        check(f"{label} [{g}]", abs(float(g) - a) <= tol_of(g),
              f"cited {g} vs actual {a:.6g}")


# ------------------------------------------------------------------ 0. src audit
print("== src-comment audit")
named = {n.replace("\\", "")                       # tex-escaped \_ in body text
         for n in re.findall(r"([a-z0-9_\\]+)\.json", TEX)}
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

# --- the tuning-grid mechanism numbers (DESIGN24 A0: exported per-setting) --
g = D2["tuning_grid_stats"]
cells = {(c["kA"], c["capA"], c["sA"]): c for c in g["per_setting"]}
check("grid: 18 settings on tuning seeds", len(cells) == 18
      and g["seeds"] == "900-903")
check("grid tie structure reproduces the DESIGN18 amendment",
      {k for k, c in cells.items() if c["score"] == 5}
      == ({(0.25, a, s) for a in (0.01, 0.02, 0.05) for s in (0.001, 0.002)}
          | {(0.5, 0.01, 0.001)}))
check("grid first shot scored 4/10", cells[(0.5, 0.02, 0.002)]["score"] == 4)
cite("§3 grid AC1 endpoints",
     r"AC\$_1\$ falls from \$(-0\.09)\$ at the frozen setting toward "
     r"\$(-0\.35)\$\s*at \$k_A = 1\$",
     cells[(0.25, 0.01, 0.001)]["ac1_r"], cells[(1.0, 0.05, 0.001)]["ac1_r"])
cite("§3 grid kurt erosion",
     r"kurtosis\s*\$([\d.]+) \\to ([\d.]+)\$ from the control to the grid's "
     r"most capitalized",
     D2["configs"]["FCVM"]["median_stats"]["kurt"],
     cells[(0.5, 0.05, 0.001)]["kurt"])
cite("§3 grid max bits",
     r"up to ([\d.]+) bits at full\s*strength \$k_A = 1\$",
     max(c["dir_bits"] for c in g["per_setting"]))
check("grid max bits occurs at kA=1",
      max(g["per_setting"], key=lambda c: c["dir_bits"])["kA"] == 1.0)

cite("§3 one-layer medians",
     r"medians \$([\d.]+) \\to ([\d.]+)\$; the paired",
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
     r"falls \$1\.000 \\to 0\.750 \\to 0\.237\$ while the\s*raw E9 statistic rises \$([\d.]+) \\to ([\d.]+) \\to ([\d.]+)\$ bits",
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
cite("§4 regression leverage", r"E5 fails, \$(-[\d.]+) \\to (-[\d.]+)\$",
     m1["leverage"], m5["leverage"])
cite("§4 regression kurt", r"kurtosis \$([\d.]+) \\to ([\d.]+)\$\) and crash",
     m1["kurt"], m5["kurt"])
cite("§4 regression tail", r"ratio \$([\d.]+) \\to ([\d.]+)\$\)",
     m1["tail_asym"], m5["tail_asym"])

# --- the 32-seed K0-vs-K1 extension (DESIGN24 A2) -------------------------
ext = D3["k01_extension"]
check("A2 budget: 32 seeds, 100-131",
      ext["n_seeds"] == 32 and ext["seeds"] == "100-131")
for _k in ("K0_FCVM", "K1_DECA2"):
    check(f"A2 prefix byte-identity {_k}",
          ext["per_seed"][_k][:8] == bits[_k]["per_seed"])
cite("§3 extension flat",
     r"above control on (\d+) of (\d+) seeds, two-sided Wilcoxon\s*"
     r"\$p = ([\d.]+)\$",
     ext["n_pos"], ext["n_seeds"], ext["wilcoxon_p"])
cite("§4 extension medians",
     r"medians \$([\d.]+)\$ versus\s*\$([\d.]+)\$, Wilcoxon \$p = ([\d.]+)\$",
     ext["median"]["K0_FCVM"], ext["median"]["K1_DECA2"], ext["wilcoxon_p"])
check("A2 verdict consistent (flat, stated as such)",
      ext["separates_at_0.05"] is False
      and len(re.findall(r"flat at 32 seeds|statistically flat", TEX)) >= 3)

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
cite("§5 bits full", r"rises at full skew \(([\d.]+),", bits4["FCVM+Q1.0"])

mF, mQ1 = c4["FCVM"]["median_stats"], c4["FCVM+Q1.0"]["median_stats"]
cite("wildfacts kurt (all occurrences share values)", r"kurtosis\s*\$([\d.]+) \\to ([\d.]+)\$", mF["kurt"], mQ1["kurt"])
cite("wildfacts leverage", r"\$(-0\.125) \\to (-0\.008)\$",
     mF["leverage"], mQ1["leverage"])
cite("§5 tail ratio", r"ratio \$(40) \\to (1\.1)\$", mF["tail_asym"], mQ1["tail_asym"])
cite("§5 clustering", r"AC\$_1\(\|r\|\)\$\s*\$([\d.]+) \\to ([\d.]+)\$",
     mF["ac1_absr"], mQ1["ac1_absr"])
cite("§5 efficiency break", r"AC\$_1\$: \$\+([\d.]+) \\to (-[\d.]+)\$",
     mF["ac1_r"], mQ1["ac1_r"])

# ------------------------------------- 5d. referee program (DESIGN25, R1-R6)
print("== referee program (robustness.json)")
RB = load("robustness")


def _median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


check("R budget held as stated",
      RB["budget"]["battery_runs"]["total"] == 272
      and RB["budget"]["non_battery_sims"] == {"R2": 40, "R4_calibration": 24}
      and re.search(r"272 battery runs and 64 auxiliary\s*simulations", TEX)
      is not None)

# --- R1: matched strength --------------------------------------------------
sd = RB["strength_depth"]
sdt = sd["tests_depth5_vs_depth1"]
cite("R1 per-layer kA", r"k_A = 1-\(1-0\.25\)\^{1/5} \\approx ([\d.]+)\$",
     sd["kA_depth5"])
cite("R1 medians (robustness section)",
     r"depth five\s*leaks \\emph{less} than depth one: medians \$([\d.]+)\$ "
     r"versus \$([\d.]+)\$",
     sd["median_bits"]["depth5"], sd["median_bits"]["depth1"])
cite("R1 test",
     r"two-sided Wilcoxon \$p = ([\d.]+)\$, depth five\s*higher on (\d+) of "
     r"(\d+) seeds",
     sdt["wilcoxon_p"], sdt["n_pos"], sdt["n"])
cite("R1 realized strengths",
     r"\(\$([\d.]+)\$ at depth five, \$([\d.]+)\$ at depth one\)",
     sd["realized_strength"]["depth5"]["median"],
     sd["realized_strength"]["depth1"]["median"])
cite("R1 spearman",
     r"Spearman\s*correlation of anticipator strength with the raw statistic "
     r"is \$([\d.]+)\$",
     sd["strength_axis"]["tuning_grid_spearman_kA_bits"])
cite("R1 AC1-bits corr (referee setup)",
     r"raw\s*statistic is \$(-0\.89)\$ across the archived tuning grid",
     sd["strength_axis"]["tuning_grid_corr_ac1_bits"])
check("R1 separates, direction depth5 < depth1",
      sdt["separates_at_0.05"] is True and sdt["median_diff"] < 0)
cite("§4 matched-strength cite (deca3 body)",
     r"depth-five stack leaks \\emph{less} than the\s*depth-one layer "
     r"\(medians \$([\d.]+)\$ versus \$([\d.]+)\$, Wilcoxon\s*\$p = ([\d.]+)\$\)",
     sd["median_bits"]["depth5"], sd["median_bits"]["depth1"],
     sdt["wilcoxon_p"])
_arms1 = {a["arm"]: a for a in sd["strength_axis"]["eval_arms"]}
cite("§4 frozen-stack effective strength",
     r"the frozen stack ran at strength \$([\d.]+)\$",
     _arms1["K5_frozen"]["eff_strength"])
check("R1 depth1 arm reproduces the stored A2 K1 vector",
      sd["per_seed_bits"]["depth1"] == D3["k01_extension"]["per_seed"]["K1_DECA2"])

# --- R2: E9 attribution ----------------------------------------------------
e9 = RB["e9_attribution"]
_m = {cfg: {k: (_median(v) if isinstance(v, list)
              and not isinstance(v[0], bool) else v)
            for k, v in rec.items()}
      for cfg, rec in e9["per_config"].items()}
_wsig = {cfg: sum(e9["per_config"][cfg]["whitened_sig"]) for cfg in _m}
check("R2 whitened significance: 8/8 everywhere except Q0.5's 7/8",
      _wsig == {"FCVM": 8, "K1": 8, "K5_FROZEN": 8, "Q0.5": 7, "Q1.0": 8})
check("R2 39-of-40 configuration-seed pairs (intro claim)",
      sum(_wsig.values()) == 39
      and re.search(r"39 of 40 configuration--seed pairs", TEX) is not None)
for _label, _regex, _cfg, _pre in [
    ("tab:whiten FCVM", r"\\cfg{FCVM} \(control\) +& 0\..*?\\\\", "FCVM", []),
    ("tab:whiten K1", r"\$K{=}1\$ +& 0\..*?\\\\", "K1", [1]),
    ("tab:whiten K5", r"\$K{=}5\$ \(frozen\) +& 0\..*?\\\\", "K5_FROZEN", [5]),
    ("tab:whiten Q0.5", r"\\cfg{FCVM\+Q}\(\$\\lambda_Q{=}0\.5\$\) & 0\..*?\\\\",
     "Q0.5", [0.5]),
    ("tab:whiten Q1.0", r"\\cfg{FCVM\+Q}\(\$\\lambda_Q{=}1\.0\$\) & 0\..*?\\\\",
     "Q1.0", [1.0]),
]:
    check_stat_row(_label, _regex,
                   _pre + [_m[_cfg]["raw_bits"], _m[_cfg]["whitened_bits"],
                           _m[_cfg]["mi_sign"], _m[_cfg]["ac1_r"],
                           _wsig[_cfg], 8])
cite("R2 control nonlinear",
     r"\(\$([\d.]+)\$ whitened against \$([\d.]+)\$ raw, significant on "
     r"(\d+) of (\d+) seeds,\s*\$\\hat\\varphi = \+([\d.]+)\$\)",
     _m["FCVM"]["whitened_bits"], _m["FCVM"]["raw_bits"], 8, 8,
     _m["FCVM"]["phi_hat"])
cite("R2 conversion sequence",
     r"\$([\d.]+) \\to ([\d.]+)\$ \(\$K{=}1\$\) \$\\to ([\d.]+)\$ "
     r"\(\$K{=}5\$\) and \$([\d.]+)\$\s*\(\$\\lambda_Q{=}1\$\)",
     _m["FCVM"]["whitened_bits"], _m["K1"]["whitened_bits"],
     _m["K5_FROZEN"]["whitened_bits"], _m["Q1.0"]["whitened_bits"])
cite("R2 sign-alone rise",
     r"sign-alone component rises\s*\$([\d.]+) \\to ([\d.]+)\$ and \$([\d.]+)\$",
     _m["FCVM"]["mi_sign"], _m["K5_FROZEN"]["mi_sign"], _m["Q1.0"]["mi_sign"])
_tvc = e9["tests_vs_control"]
check("R2 whitened diffs reverse in all four arms (0/8 positive, p=0.0078)",
      all(_tvc[a]["whitened"]["n_pos"] == 0
          and abs(_tvc[a]["whitened"]["wilcoxon_p"] - 0.0078) < 5e-5
          and _tvc[a]["whitened"]["median_diff"] < 0
          for a in ("K1", "K5_FROZEN", "Q0.5", "Q1.0"))
      and re.search(r"positive on 0 of 8 seeds,\s*\$p = 0\.0078\$, in all "
                    r"four arms", TEX) is not None)
cite("R2 sign-component shares",
     r"share ([\d.]+) at \$K{=}5\$, ([\d.]+) at\s*\$\\lambda_Q{=}1\$",
     e9["verdicts"]["K5_FROZEN"]["sign_component_share_of_raw_rise"],
     e9["verdicts"]["Q1.0"]["sign_component_share_of_raw_rise"])
check("R2 conditional MI falls in every arm",
      all(_tvc[a]["cmi"]["n_pos"] == 0
          and abs(_tvc[a]["cmi"]["wilcoxon_p"] - 0.0078) < 5e-5
          for a in ("K1", "K5_FROZEN", "Q0.5", "Q1.0")))
cite("R2 whitened floor",
     r"reaching no lower than \$([\d.]+)\$\s*bits \(half skew\) and "
     r"\$([\d.]+)\$ at exact absorption",
     min(_m[c]["whitened_bits"] for c in _m), _m["Q1.0"]["whitened_bits"])
check("R2 floor is the half-skew configuration",
      min(_m, key=lambda c: _m[c]["whitened_bits"]) == "Q0.5")
check("R2 withdrawal stated per the registered rule",
      e9["verdicts"]["K5_FROZEN"]["rise_survives_whitening"] is False
      and e9["verdicts"]["Q1.0"]["rise_survives_whitening"] is False
      and re.search(r"re-creates sign\s*information in price space is "
                    r"\\emph{withdrawn}", TEX) is not None)
check("R2 raw medians reproduce the published values",
      abs(_m["FCVM"]["raw_bits"] - med["K0_FCVM"]) < 5e-5
      and abs(_m["K1"]["raw_bits"] - med["K1_DECA2"]) < 5e-5
      and abs(_m["K5_FROZEN"]["raw_bits"] - med["K5_FIXEDPOINT"]) < 5e-5
      and abs(_m["Q0.5"]["raw_bits"] - bits4["FCVM+Q0.5"]) < 5e-5
      and abs(_m["Q1.0"]["raw_bits"] - bits4["FCVM+Q1.0"]) < 5e-5)
# the abstract / intro / conclusion restatements of the conversion numbers
cite("abstract whitened conversion",
     r"whitened information\s*([\d.]+) to ([\d.]+) bits at exact\s*absorption",
     _m["FCVM"]["whitened_bits"], _m["Q1.0"]["whitened_bits"])
cite("intro whitened conversion",
     r"from ([\d.]+)\s*bits in the control to ([\d.]+)\s*under exact absorption",
     _m["FCVM"]["whitened_bits"], _m["Q1.0"]["whitened_bits"])
cite("conclusion whitened conversion",
     r"whitened information falls from \$([\d.]+)\$ bits in the control to\s*"
     r"\$([\d.]+)\$ under exact absorption",
     _m["FCVM"]["whitened_bits"], _m["Q1.0"]["whitened_bits"])
check("shared conversion pair cited consistently (>= 2 sites)",
      len(re.findall(r"\$0\.0197 \\to 0\.0036\$", TEX)) >= 2
      and abs(_m["FCVM"]["whitened_bits"] - 0.0197) < 5e-5
      and abs(_m["Q1.0"]["whitened_bits"] - 0.0036) < 5e-5)
cite("§3 K1 absorption share",
     r"absorbing part of\s*the genuine nonlinear leak \(whitened bits "
     r"\$([\d.]+) \\to ([\d.]+)\$\)",
     _m["FCVM"]["whitened_bits"], _m["K1"]["whitened_bits"])

# --- R3: 32-seed extensions ------------------------------------------------
ext32 = RB["ext32"]
cite("R3 K5 at 32 seeds",
     r"frozen \$K{=}5\$ stack at\s*\$([\d.]+)\$ against the control's "
     r"\$([\d.]+)\$, higher on (\d+) of (\d+) seeds",
     ext32["arms"]["K5_FROZEN"]["median"], ext32["control_median"],
     ext32["arms"]["K5_FROZEN"]["tests_vs_control"]["n_pos"], 32)
cite("R3 Q1.0 at 32 seeds",
     r"full skew at \$([\d.]+)\$, higher on (\d+) of (\d+)",
     ext32["arms"]["Q1.0"]["median"],
     ext32["arms"]["Q1.0"]["tests_vs_control"]["n_pos"], 32)
check("R3 both rises stand at p < 1e-4 (stated as such)",
      ext32["arms"]["K5_FROZEN"]["tests_vs_control"]["wilcoxon_p"] < 1e-4
      and ext32["arms"]["Q1.0"]["tests_vs_control"]["wilcoxon_p"] < 1e-4
      and len(re.findall(r"p < 10\^{-4}", TEX)) >= 2)
check("§4 28-of-32 cited in the deca3 body",
      re.search(r"7 of 8 paired seeds and on 28\s*of 32", TEX) is not None
      and ext32["arms"]["K5_FROZEN"]["tests_vs_control"]["n_pos"] == 28)
check("§5 26-of-32 cited in the deca4 body",
      re.search(r"7 of 8 seeds,\s*and on 26 of 32", TEX) is not None
      and ext32["arms"]["Q1.0"]["tests_vs_control"]["n_pos"] == 26)

# --- R4: t(3) fundamentals -------------------------------------------------
t3 = RB["t3_absorption"]
_lad = {c["mult"]: c for c in t3["calibration"]["ladder"]}
check("R4 variance-matching scale selected", t3["calibration"]["selected_mult"] == 1.0)
cite("R4 calibration",
     r"variance-matching scale won, median kurtosis \$([\d.]+)\$ against "
     r"the\s*control's \$([\d.]+)\$",
     _lad[1.0]["median_kurt"], t3["calibration"]["target_kurt"])
check("R4 ladder non-monotone (larger scales lower kurtosis)",
      _lad[3.0]["median_kurt"] < _lad[1.0]["median_kurt"]
      and re.search(r"larger \$t\$-scales\s*\\emph{lower} total kurtosis",
                    TEX) is not None)
check("R4 control 5/10 failing exactly FCVM's events",
      t3["configs"]["FCVM_T3"]["score"] == 5
      and failed_set(t3["configs"]["FCVM_T3"]["events"]) == {3, 4, 7, 8, 9}
      and re.search(r"\\cfg{FCVM-T3} scores 5/10, failing exactly "
                    r"\\cfg{FCVM}'s five events", TEX) is not None)
cite("R4 absorption outcome",
     r"\\cfg{FCVM-T3\+Q1\.0} scores 1/10 with kurtosis\s*\$([\d.]+)\$ and "
     r"the raw statistic at \$([\d.]+)\$ bits",
     t3["configs"]["FCVM_T3_Q1.0"]["median_stats"]["kurt"],
     t3["configs"]["FCVM_T3_Q1.0"]["median_stats"]["dir_bits"])
check("R4 T3+Q1.0 scores 1, tails do not survive",
      t3["configs"]["FCVM_T3_Q1.0"]["score"] == 1
      and t3["tails_survive_absorption"] is False
      and t3["leak_persists"] is True)
check("R4 kF cited == code constant",
      re.search(r"kF=0\.15", code_ws) is not None
      and "($k_F = 0.15$)" in TEX)
check("R4 scoping stated (flow-generated)",
      re.search(r"joint\s*production is structural to "
                r"\\emph{flow-generated} amplitude structure", TEX) is not None)

# --- R5: kM re-equilibration -----------------------------------------------
rq = RB["requilibration"]
_a, _q = rq["arms"]["A_K1"], rq["arms"]["Q1.0"]
check("R5 anticipator arm keeps kM=0.30, 5/10, FCVM's failure set",
      _a["winner_kM"] == 0.3 and _a["eval"]["score"] == 5
      and failed_set(_a["eval"]["events"]) == {3, 4, 7, 8, 9}
      and re.search(r"keeps\s*the frozen \$k_M = 0\.30\$ and scores 5/10",
                    TEX) is not None)
check("R5 Q arm picks kM=0.10, 2/10 passing exactly E1 and E6",
      _q["winner_kM"] == 0.1 and _q["eval"]["score"] == 2
      and failed_set(_q["eval"]["events"]) == {2, 3, 4, 5, 7, 8, 9, 10}
      and re.search(r"selects \$k_M = 0\.10\$ and\s*scores 2/10", TEX)
      is not None)
cite("R5 collapsed bits",
     r"median of \$([\d.]+)\$ bits\s*\(\$([\d.]+)\$--\$([\d.]+)\$ per seed",
     _q["eval"]["median_dir_bits"], min(_q["eval"]["dir_bits_per_seed"]),
     max(_q["eval"]["dir_bits_per_seed"]))
check("R5 ceiling survives", rq["ceiling_survives_requilibration"] is True
      and _a["exceeds_ceiling"] is False and _q["exceeds_ceiling"] is False)

# --- R6: threshold robustness ----------------------------------------------
tr = RB["threshold_robustness"]
check("R6 48 perturbations, baseline reproduced",
      len(tr["per_perturbation"]) == 48 and tr["baseline_reproduced"] is True
      and "48 perturbed scorings" in TEX)
check("R6 ceiling invariant holds in 48/48",
      tr["ceiling_invariant_holds"] is True
      and all(p["fcvm_is_max"] for p in tr["per_perturbation"])
      and tr["fcvm_failset_changes"] == [])
check("R6 GBM anchor stable", tr["score_bands"]["G"]["band_10pct"] == [3, 3]
      and tr["score_bands"]["G"]["band_20pct"] == [3, 3])
check("R6 SPY anchor: 10/10 at ±10%, 9 only at e8_ratio -20%",
      tr["spy_band"]["band_10pct"] == [10, 10]
      and tr["spy_band"]["band_20pct"] == [9, 10]
      and [(p["threshold"], p["delta"]) for p in tr["per_perturbation"]
           if p["spy"] != 10] == [("e8_ratio", -0.2)]
      and re.search(r"SPY\s*stays 10/10 at \$\\pm 10\\%\$ and drops to 9/10 "
                    r"only for the E8 ratio at\s*\$-20\\%\$", TEX) is not None)
check("R6 headline rows frozen at ±10%",
      all(tr["score_bands"][c]["band_10pct"] == [5, 5]
          for c in ("FCVM", "FCVM+A", "K5_TUNED", "Q_TUNED", "FV", "FCV")))
check("R6 knife edges are exactly the named configs",
      {e.split(":")[1] for e in tr["knife_edge_moves_at_10pct"]}
      == {"Q0.5", "FCVMH", "K5_FROZEN"})
check("appendix K5-frozen 20% band spans 2--4",
      tr["score_bands"]["K5_FROZEN"]["band_20pct"] == [2, 4]
      and re.search(r"frozen \$K{=}5\$ stack spans 2--4 events", TEX)
      is not None)
check("appendix headline rows stay 5 at ±20%",
      all(tr["score_bands"][c]["band_20pct"] == [5, 5]
          for c in ("FCVM", "FCVM+A", "K5_TUNED", "Q_TUNED", "FV", "FCV"))
      and re.search(r"every headline row stays at exactly 5", TEX) is not None)

# ---------------------------------------------- 5b. score SEs (DESIGN24 A3)
print("== battery-score SEs (score_se.json)")
SEJ = load("score_se")
check("SE method", SEJ["method"]["n_boot"] == 2000
      and SEJ["method"]["rng_seed"] == 0 and SEJ["method"]["seeds"] == "100-107")
_pub = {"G": D1["configs"]["G"]["score"], "F": D1["configs"]["F"]["score"],
        "FC": D1["configs"]["FC"]["score"], "FV": D1["configs"]["FV"]["score"],
        "FCV": D1["configs"]["FCV"]["score"],
        "FCVM": D1["configs"]["FCVM"]["score"],
        "FCVMH": D1["configs"]["FCVMH"]["score"],
        "FCVM+A": c2["FCVM+A"]["score"], "FV+A": c2["FV+A"]["score"],
        "F+A": c2["F+A"]["score"],
        "K5_FIXEDPOINT": c3["K5_FIXEDPOINT"]["score"],
        "K5_TUNED": D3["tuned_eval"]["score"],
        "FCVM+Q1.0": c4["FCVM+Q1.0"]["score"],
        "FCVM+Q0.5": c4["FCVM+Q0.5"]["score"],
        "Q_TUNED": cp["tuned_eval"]["score"]}
for _cfg, _sc in _pub.items():
    check(f"SE reproduction {_cfg}", SEJ["scores"][_cfg] == _sc,
          f"score_se {SEJ['scores'][_cfg]} vs published {_sc}")
check("§2 SE ceiling 0.5 claim", max(SEJ["se"].values()) <= 0.5
      and re.search(r"SE\s*is at most 0\.5 events", TEX) is not None)


def check_pm(label, line_regex, se_key, score_cell=1):
    cells = row_cells(line_regex)
    if cells is None:
        check(label, False, f"row not found: {line_regex!r}")
        return
    m = re.search(r"\\pm\$ ([\d.]+)", cells[score_cell])
    check(label, m is not None
          and abs(float(m.group(1)) - SEJ["se"][se_key]) <= tol_of(m.group(1))
          if m else False,
          f"cell {cells[score_cell]!r} vs SE {SEJ['se'][se_key]}")


check_pm("tab:deca2 FCVM ±", r"\\cfg{FCVM} \(control\).*?\\\\", "FCVM")
check_pm("tab:deca2 FCVM+A ±", r"\\cfg{FCVM\+A} \(hypothesis\).*?\\\\", "FCVM+A")
check_pm("tab:deca2 FV+A ±", r"\\cfg{FV\+A} .*?\\\\", "FV+A")
check_pm("tab:deca2 F+A ±", r"\\cfg{F\+A} \(no targeters\).*?\\\\", "F+A")
check_pm("tab:deca3 K0 ±", r"\$K{=}0\$ \(\\cfg{FCVM}, control\).*?\\\\", "FCVM")
check_pm("tab:deca3 K1 ±", r"\$K{=}1\$ \(Exp\..*?\\\\", "FCVM+A")
check_pm("tab:deca3 K5 ±", r"\$K{=}5\$ \(frozen carry-over\).*?\\\\",
         "K5_FIXEDPOINT")
check_pm("tab:deca3 K5 tuned ±", r"\$K{=}5\$ \(tuned, contingent pass\).*?\\\\",
         "K5_TUNED")
check_pm("tab:deca4 Q1.0 ±", r"\\cfg{FCVM\+Q}\(\$\\lambda_Q{=}1\.0\$\).*?\\\\",
         "FCVM+Q1.0")
check_pm("tab:deca4 Q0.5 ±", r"\\cfg{FCVM\+Q}\(\$\\lambda_Q{=}0\.5\$\).*?\\\\",
         "FCVM+Q0.5")
check_pm("tab:deca4 tuned ±", r"\\cfg{FCVM\+Q}\(\$\\lambda_Q{=}0\.05\$\).*?\\\\",
         "Q_TUNED")

# --------------------------------------------- 5c. data table (fx.json laws)
print("== descriptive-statistics table (fx.json laws)")
_L = FX["laws"]
_span = {"fx": (2010, 2026), "crypto": (2017, 2026)}
_counts = {"US": 49, "japan": 29, "europe": 36, "asia_em": 29,
           "fx": len(FX["per_pair_leverage"]), "crypto": len(CR["per_coin_leverage"])}
for _row, _uni in [("US equities", "US"), ("Japan equities", "japan"),
                   ("Europe equities", "europe"), ("Asia-EM equities", "asia_em"),
                   ("FX crosses", "fx"), ("Cryptocurrencies", "crypto")]:
    _lev = (_L["leverage"]["values"][_uni] if _uni != "crypto"
            else CR["leverage_contrast"]["crypto_leverage"])
    _kurt = _L["kurt"]["values"].get(_uni, None)
    _kdef = _L["kurt_def"]["values"].get(_uni, None)
    _y0, _y1 = _span.get(_uni, (2010, 2026))
    check_stat_row(f"tab:data {_row}", rf"{re.escape(_row)} +&.*?\\\\",
                   [_counts[_uni], _y0, _y1, _kurt, _kdef, _lev])
check("tab:data crypto leverage == laws value",
      abs(_L["leverage"]["values"]["crypto"]
          - CR["leverage_contrast"]["crypto_leverage"]) < 5e-4)
check("tab:data crypto span year == crypto.json span", CR["span"][0][:4] == "2017")
check("tab:data FX/equity span == fx.json span",
      FX["span"][0][:4] == "2010" and FX["span"][1][:4] == "2026")

# instrument counts against the versioned universe lists
_cfg_text = (ROOT / "config.py").read_text()
_um = re.search(r"UNIVERSE = \[(.*?)\]", _cfg_text, re.S)
check("tab:data US count == config.py UNIVERSE",
      _um is not None and len(re.findall(r'"[A-Z.\-]+"', _um.group(1))) == 49)
_tr_text = (ROOT / "kronos" / "transfer.py").read_text()
for _name, _n in [("japan", 29), ("europe", 36), ("asia_em", 29)]:
    _bm = re.search(rf'"{_name}":\s*\{{.*?"tickers":\s*\[(.*?)\]', _tr_text, re.S)
    check(f"tab:data {_name} count == transfer.py UNIVERSES",
          _bm is not None
          and len(re.findall(r'"[A-Z0-9.\-]+"', _bm.group(1))) == _n)
check("tab:data FX count == fx.json pairs", len(FX["pairs"]) == 13)
check("tab:data crypto count == crypto.json coins", len(CR["coins"]) == 10)

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
cite("abstract crypto", r"cryptocurrencies\s*\(\$\+(0\.03)\$\)", cc["crypto_leverage"])

# ------------------------------- 6b. widened crypto universe (DESIGN24 A4)
print("== widened crypto universe (crypto_wide.json)")
CW = load("crypto_wide")
ar = CW["arithmetic"]
cite("§7 power arithmetic SDs",
     r"fall from \$([\d.]+)\$ below \$([\d.]+)\$, a \$([\d.]+)\\times\$",
     ar["csd_now"], ar["csd_needed_for_z2"], ar["reduction_factor_needed"])
cite("§7 history bound",
     r"\\approx (\d+)\$ years of daily crypto data against\s*the ([\d.]+) "
     r"that exist",
     ar["history_years_needed_if_T_only"], ar["history_years_now"])
cite("§7 widening counts", r"from (\d+) to (\d+) majors",
     10, CW["n_coins"])
cite("§7 widened SD unchanged",
     r"essentially unchanged \(\$([\d.]+) \\to ([\d.]+)\$\)",
     ar["csd_now"], CW["sd_wide"])
cite("§7 widened estimate and z",
     r"pooled estimate moved\s*to \$\+([\d.]+)\$ \((\d+) of (\d+) coins "
     r"positive\) and the \$z\$\s*against FX to ([\d.]+)",
     CW["leverage_wide"], CW["n_pos"], CW["n_coins"], CW["z_vs_fx_wide"])
cite("§7 widened equity edge survives",
     r"survives the widening at \$z = ([\d.]+)\$", CW["z_vs_equities_wide"])
check("A4 not certified, and stated as such",
      CW["certified_ge2"] is False and CW["z_vs_fx_wide"] < 2
      and "cannot yet promote to a separation" in TEX)
check("A4 10-coin z consistent with fx.json",
      CW["z_vs_fx_10coin"] == lc["z_crypto_vs_fx"])
check("A4 T-protection: widened span == published crypto span",
      CW["span"][0] == CR["span"][0])
_need = ((CR["leverage_contrast"]["crypto_leverage"]
          - FX["leverage_contrast"]["fx_leverage"]) / 2) ** 2 \
    - FX["leverage_contrast"]["fx_sd"] ** 2
check("A4 arithmetic re-derived from stored vertices",
      abs(ar["csd_needed_for_z2"] - _need ** 0.5) < 5e-4)
check("A4 added coins pass the range gate",
      CW["range_audit"] and min(CW["range_audit"].values()) > 0.95
      and len(CW["coins"]) == 17)
cite("§7 institutional coins (epistemic passage)",
     r"BTC \(\$(-[\d.]+)\$\) and ETH \(\$(-[\d.]+)\$\), the two most",
     CR["per_coin_leverage"]["BTC-USD"], CR["per_coin_leverage"]["ETH-USD"])
check("§7 negative-sign sets: {BTC,ETH} registered, +XMR widened",
      {k for k, v in CR["per_coin_leverage"].items() if v < 0}
      == {"BTC-USD", "ETH-USD"}
      and {k for k, v in CW["per_coin_leverage"].items() if v < 0}
      == {"BTC-USD", "ETH-USD", "XMR-USD"}
      and "joined by XMR in the widened one" in TEX)

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

# ------------------------------------- 8b. calibration audit (DESIGN24 A1)
print("== multi-index calibration audit (battery_audit.json)")
BA = load("battery_audit")
gjr = BA["gjr_clock"]
cite("appendix GJR clock AC8",
     r"clock\s*\$\\mathrm{AC}_8\$ median \$([\d.]+)\$, maximum \$([\d.]+)\$",
     gjr["median"], gjr["max"])
check("GJR below the E4 bar on every seed",
      gjr["all_below_bar"] and gjr["e4_bar"] == 0.12
      and max(gjr["per_seed"]) < 0.12)
check("audit anchor unchanged", BA["anchor"] == {"SPY": 10, "GBM": 3})
check("audit prediction failed and the paper says so",
      BA["prediction_ge9_all"] is False
      and re.search(r"\$\\ge 9/10\$ --- \\emph{failed}", TEX) is not None)
_venue = {"QQQ": "US", "DIA": "US", "IWM": "US", "1306.T": "Japan",
          "EXW1.DE": "Europe", "2800.HK": "Hong Kong"}
for name, venue in _venue.items():
    rec = BA["indices"][name]
    check_row(f"tab:audit {name}",
              rf"{re.escape(name)} +& {venue}.*?\\\\",
              rec["score"], failed_set(rec["events"]), None,
              score_cell=2, events_cell=3)
check_row("tab:audit SPY", r"SPY \(anchor\) & US.*?\\\\",
          D1["spy"]["score"], failed_set(D1["spy"]["events"]), None,
          score_cell=2, events_cell=3)
_us = [BA["indices"][k]["score"] for k in ("QQQ", "DIA", "IWM")]
_foreign = [BA["indices"][k]["score"] for k in ("1306.T", "EXW1.DE", "2800.HK")]
check("§2 audit summary (DIA 10, QQQ/IWM 8, foreign 5-7)",
      BA["indices"]["DIA"]["score"] == 10
      and BA["indices"]["QQQ"]["score"] == BA["indices"]["IWM"]["score"] == 8
      and min(_foreign) == 5 and max(_foreign) == 7
      and re.search(r"DIA also scores 10/10, QQQ and IWM\s*8/10", TEX)
      and re.search(r"score only 5--7/10", TEX) is not None)
check("appendix recurring misses E7/E8/E9 in all foreign failure sets",
      all({7, 9} <= failed_set(BA["indices"][k]["events"])
          or {7, 8} <= failed_set(BA["indices"][k]["events"])
          for k in ("1306.T", "EXW1.DE", "2800.HK")))

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

# ------------------------------------------------------- former narrative SKIPS
# (converted to executable checks: the DECA2 grid stats via DESIGN24 A0
# above, the X26 bound and the toy-corr src comment here)
check("src-comment exact toy corr", abs(toy["lam0.0"] - 0.6575) < 5e-5
      and abs(toy["lam1.0"] - (-0.0583)) < 5e-5)
_x26 = (ROOT / "tests" / "test_crypto.py").read_text()
_m26 = re.search(r"abs\(sym\.mean\(\)\) < ([\d.]+)", _x26)
check("§7 spurious-leverage bound == gate X26's constant",
      _m26 is not None and float(_m26.group(1)) == 0.04
      and "$|0.04|$" in TEX)

# (no remaining narrative skips: the GJR clock reference is asserted against
# battery_audit.json gjr_clock in section 8b)
# --- anti-drift: gate counts stated in the paper must equal len(GATES) -------
_runner = (ROOT / "tests" / "run_all.py").read_text()
_n_true = len(re.findall(r'"(test_\w+\.py)"', _runner))
_stated = [int(x) for x in re.findall(r"runs all (\d+) verification gates", TEX)]
check("gate count stated in paper", len(_stated) >= 1,
      "paper must state the gate count explicitly")
for _s in _stated:
    check(f"paper gate count {_s} == len(GATES)", _s == _n_true,
          f"run_all.py defines {_n_true} gates")

print()
if failures:
    print(f"FAILED: {len(failures)} of {n_checks} checks")
    sys.exit(1)
print(f"PASS: all {n_checks} checks against research/*.json and kronos/decathlon.py")
