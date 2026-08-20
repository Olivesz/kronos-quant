"""Generate every figure for the preprint from research/*.json.

Reads ONLY the research JSONs (research/decathlon.json, decathlon2.json,
decathlon3.json, decathlon4.json, fx.json, crypto.json, battery_audit.json,
score_se.json) — no hand-entered numbers.  Outputs LaTeX-sized PDF figures
(single-column, ~3.4 in wide, monochrome-friendly) into docs/paper/figures/.

Figures
-------
F1  battery_scorecard.pdf   ten-event scorecard heat-strip: SPY vs the ablation ladder
F2  e9_bits_configs.pdf     E9 direction bits across every rationality config
F3  deca3_inversion.pdf     the DECA3 inversion: forecastable flow falls, leaked bits rise
F4  deca4_wildfacts.pdf     DECA4 amplitude-fact medians vs quote-skew lambda
F5  leverage_triangle.pdf   the leverage effect across equities / FX / crypto
F6  gate_schematic.pdf      the size/power validation gate pattern
F7  leverage_perasset.pdf   per-instrument leverage across the three venue classes
F8  audit_matrix.pdf        multi-index battery audit: events x indices
F9  tuning_grid.pdf         Experiment I tuning grid: score by (kA, capA, sA)
F10 score_se.pdf            battery scores with seed-bootstrap SEs, all configs

Build note: matplotlib is a PAPER-BUILD-ONLY dependency.  It is deliberately
NOT in requirements.txt / project dependencies; install it into the venv ad
hoc (`pip install matplotlib`) when rebuilding the figures.
"""

import json
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent          # docs/paper/
ROOT = HERE.parent.parent                        # repo root
RESEARCH = ROOT / "research"
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)


def load(name):
    with open(RESEARCH / f"{name}.json") as fh:
        return json.load(fh)


D1 = load("decathlon")
D2 = load("decathlon2")
D3 = load("decathlon3")
D4 = load("decathlon4")
FX = load("fx")
CR = load("crypto")
BA = load("battery_audit")
SE = load("score_se")

# Cross-file consistency (the FCVM control is shared byte-for-byte).
assert D3["dir_bits_vs_K"]["K0_FCVM"]["per_seed"] == \
    D4["dir_bits_vs_lambda"]["FCVM"]["per_seed"], "FCVM control differs across DECA3/DECA4"
assert abs(D3["dir_bits_vs_K"]["K1_DECA2"]["median"]
           - D2["configs"]["FCVM+A"]["median_stats"]["dir_bits"]) < 1e-6, \
    "DECA3 K=1 does not reproduce DECA2's single layer"

mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6.5,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "pdf.fonttype": 42,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})

EVENTS = ["E1_efficiency", "E2_fat_tails", "E3_clustering", "E4_long_memory",
          "E5_leverage", "E6_one_clock", "E7_clock_jumps", "E8_arrow",
          "E9_no_sign_info", "E10_tail_asym"]
EVENT_SHORT = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10"]


# ---------------------------------------------------------------- F1
def f1_scorecard():
    ladder = ["G", "F", "FC", "FV", "FCV", "FCVM", "FCVMH"]
    rows = [("SPY (real)", D1["spy"]["events"], D1["spy"]["score"])]
    for c in ladder:
        rows.append((c, D1["configs"][c]["events"], D1["configs"][c]["score"]))

    n_r, n_c = len(rows), len(EVENTS)
    fig, ax = plt.subplots(figsize=(3.4, 0.24 * n_r + 0.55))
    for i, (label, ev, score) in enumerate(rows):
        y = n_r - 1 - i
        for j, e in enumerate(EVENTS):
            passed = ev[e]
            ax.add_patch(Rectangle((j, y), 0.92, 0.86,
                                   facecolor="0.15" if passed else "white",
                                   edgecolor="0.4", linewidth=0.5))
        ax.text(-0.25, y + 0.43, label, ha="right", va="center", fontsize=7)
        ax.text(n_c + 0.35, y + 0.43, f"{score}/10", ha="left", va="center",
                fontsize=7)
    for j, s in enumerate(EVENT_SHORT):
        ax.text(j + 0.46, n_r + 0.12, s, ha="center", va="bottom", fontsize=6.5)
    ax.set_xlim(-2.2, n_c + 1.3)
    ax.set_ylim(-0.15, n_r + 0.5)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(OUT / "battery_scorecard.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- F2
def f2_bits():
    labels = ["FCVM", "$+$A\n$K{=}1$", "$+$A\n$K{=}5$",
              "$+$Q\n$\\lambda_Q{=}0.5$", "$+$Q\n$\\lambda_Q{=}1$"]
    series = [D3["dir_bits_vs_K"]["K0_FCVM"],
              D3["dir_bits_vs_K"]["K1_DECA2"],
              D3["dir_bits_vs_K"]["K5_FIXEDPOINT"],
              D4["dir_bits_vs_lambda"]["FCVM+Q0.5"],
              D4["dir_bits_vs_lambda"]["FCVM+Q1.0"]]
    spy_bits = D1["spy"]["stats"]["dir_bits"]

    fig, ax = plt.subplots(figsize=(3.4, 2.0))
    for x, s in enumerate(series):
        seeds = s["per_seed"]
        xs = [x + (k - (len(seeds) - 1) / 2) * 0.035 for k in range(len(seeds))]
        ax.plot(xs, seeds, "o", ms=2.4, mfc="none", mec="0.55", mew=0.6,
                zorder=2)
        ax.hlines(s["median"], x - 0.22, x + 0.22, color="black", lw=1.4,
                  zorder=3)
    ax.axhline(spy_bits, color="0.3", lw=0.7, ls=":")
    ax.text(4.42, spy_bits + 0.0006, "SPY (real)", fontsize=6.5, color="0.3",
            ha="right", va="bottom")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("E9 direction bits")
    ax.set_ylim(0, 0.033)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUT / "e9_bits_configs.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- F3
def f3_inversion():
    ks = [0, 1, 5]
    beta = [D3["forecastable_flow_fraction_vs_K"][f"K{k}"]["toy_beta"]
            for k in ks]
    kA = D3["frozen_params"]["kA"]
    bit_keys = ["K0_FCVM", "K1_DECA2", "K5_FIXEDPOINT"]
    med = [D3["dir_bits_vs_K"][k]["median"] for k in bit_keys]
    # per-seed scatter: the DESIGN24 A2 32-seed extension at K=0/1, the 8
    # evaluation seeds at K=5 (medians stay the published 8-seed protocol
    # values; the caption states both seed counts)
    ext = D3["k01_extension"]["per_seed"]
    seeds = [ext.get(k, D3["dir_bits_vs_K"][k]["per_seed"]) for k in bit_keys]

    fig, ax = plt.subplots(figsize=(3.4, 2.55))
    axr = ax.twinx()

    # Left axis: forecastable-flow fraction, theory curve + toy measurements.
    kk = [i / 40 for i in range(0, 201)]
    ax.plot(kk, [(1 - kA) ** k for k in kk], "-", color="black", lw=1.1,
            zorder=2)
    ax.plot(ks, beta, "o", color="black", ms=4.5, zorder=3)
    ax.set_xlabel("anticipation depth $K$")
    ax.set_ylabel(r"forecastable-flow fraction $\beta_K$", color="black")
    ax.set_ylim(0, 1.05)
    ax.set_xlim(-0.3, 5.3)
    ax.set_xticks(ks)
    ax.text(1.45, 0.80, "model space: forecastable flow\n"
            r"$\beta_K=(1-k_A)^K\;\searrow$",
            fontsize=7, ha="left", va="bottom")
    ax.annotate(f"{beta[2]:.3f}", xy=(5, beta[2]), xytext=(4.72, beta[2]),
                fontsize=6.5, ha="right", va="center")

    # Right axis: E9 direction bits, per-seed + median.
    for x, s in zip(ks, seeds):
        sp = 0.045 if len(s) <= 8 else 0.016
        xs = [x + (k - (len(s) - 1) / 2) * sp for k in range(len(s))]
        axr.plot(xs, s, "o", ms=2.2, mfc="none", mec="0.55", mew=0.6, zorder=2)
    axr.plot(ks, med, "s--", color="0.25", ms=4.5, mfc="white", lw=1.1,
             zorder=3)
    axr.set_ylabel("E9 direction bits (eval seeds)", color="0.25")
    axr.set_ylim(0.010, 0.034)
    axr.text(3.52, 0.0220, "market space: leaked\n"
             r"sign bits (E9) $\nearrow$",
             fontsize=7, ha="left", va="top", color="0.25")
    axr.annotate(f"{med[0]:.4f}", xy=(0, med[0]), xytext=(0.30, 0.01745),
                 fontsize=6.5, color="0.25", ha="left")
    axr.annotate(f"{med[1]:.4f}", xy=(1, med[1]), xytext=(1.28, 0.0186),
                 fontsize=6.5, color="0.25", ha="left")
    axr.annotate(f"{med[2]:.4f}", xy=(5, med[2]), xytext=(4.70, 0.0253),
                 fontsize=6.5, color="0.25", ha="right")
    ax.spines["top"].set_visible(False)
    axr.spines["top"].set_visible(False)
    fig.savefig(OUT / "deca3_inversion.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- F4
def f4_wildfacts():
    lams = [0.0, 0.5, 1.0]
    cfgs = ["FCVM", "FCVM+Q0.5", "FCVM+Q1.0"]
    ms = [D4["configs"][c]["median_stats"] for c in cfgs]
    kurt = [m["kurt"] for m in ms]
    lev = [m["leverage"] for m in ms]
    ac1a = [m["ac1_absr"] for m in ms]
    bits = [D4["dir_bits_vs_lambda"][c]["median"] for c in cfgs]
    bit_seeds = [D4["dir_bits_vs_lambda"][c]["per_seed"] for c in cfgs]

    fig, axes = plt.subplots(2, 2, figsize=(3.4, 2.6), sharex=True)
    (a, b), (c, d) = axes
    for ax, letter in zip(axes.flat, "abcd"):
        ax.set_xticks(lams)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=6.5)
        ax.set_title(f"({letter})", loc="left", fontsize=7, pad=2)

    a.plot(lams, kurt, "o-", color="black", ms=3.5, lw=1.0)
    a.axhline(3.0, color="0.6", lw=0.6, ls=":")
    a.text(0.03, 3.35, "Gaussian", fontsize=6, color="0.45", ha="left")
    a.set_ylim(2.3, max(kurt) + 0.7)
    a.set_title("kurtosis", fontsize=7, pad=2)

    b.plot(lams, lev, "o-", color="black", ms=3.5, lw=1.0)
    b.axhline(0.0, color="0.6", lw=0.6, ls=":")
    b.set_ylim(min(lev) - 0.014, 0.012)
    b.set_title(r"leverage corr$(r_t,\mathrm{RV}_{t+1..10})$", fontsize=7,
                pad=2)

    c.plot(lams, ac1a, "o-", color="black", ms=3.5, lw=1.0)
    c.set_ylim(min(ac1a) - 0.04, max(ac1a) + 0.04)
    c.set_title(r"vol clustering AC$_1(|r|)$", fontsize=7, pad=2)
    c.set_xlabel(r"quote skew $\lambda_Q$", fontsize=7)

    for x, s in zip(lams, bit_seeds):
        xs = [x + (k - (len(s) - 1) / 2) * 0.022 for k in range(len(s))]
        d.plot(xs, s, "o", ms=1.8, mfc="none", mec="0.55", mew=0.5)
    d.plot(lams, bits, "s--", color="black", ms=3.5, lw=1.0, mfc="white")
    d.set_title("E9 direction bits", fontsize=7, pad=2)
    d.set_xlabel(r"quote skew $\lambda_Q$", fontsize=7)

    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "deca4_wildfacts.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- F5
def f5_triangle():
    lev = FX["laws"]["leverage"]["values"]
    sds = FX["laws"]["leverage"]["sds"]
    order = ["US", "japan", "europe", "asia_em", "fx", "crypto"]
    names = ["US", "Japan", "Europe", "Asia-EM", "FX", "crypto"]
    xs = [0, 1, 2, 3, 4.6, 6.2]

    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    ax.axhline(0, color="0.6", lw=0.7, ls=":", zorder=1)

    # per-instrument scatter for the FX and crypto vertices
    pair_vals = list(FX["per_pair_leverage"].values())
    coin_vals = list(CR["per_coin_leverage"].values())
    for base_x, vals in [(4.6, pair_vals), (6.2, coin_vals)]:
        px = [base_x + (i - (len(vals) - 1) / 2) * 0.055
              for i in range(len(vals))]
        ax.plot(px, vals, "o", ms=2.2, mfc="none", mec="0.6", mew=0.6,
                zorder=2)

    for x, k in zip(xs, order):
        ax.errorbar([x], [lev[k]], yerr=[sds[k]], fmt="o", color="black",
                    ms=4, capsize=2.5, lw=1.0, zorder=3)

    # Cohort-separation bars: equity cohort (centre of the four universes)
    # vs FX, and FX vs crypto — drawn below all data so neither bar reads as
    # a pairwise comparison with a single universe.
    z_eq_fx = FX["leverage_contrast"]["z_fx_vs_equities"]
    z_fx_cr = FX["leverage_contrast"]["z_crypto_vs_fx"]
    ax.annotate(f"$z={z_eq_fx}$", xy=(3.05, -0.081), fontsize=7, ha="center")
    ax.annotate("", xy=(4.6, -0.070), xytext=(1.5, -0.070),
                arrowprops=dict(arrowstyle="-", lw=0.6, color="0.3"))
    ax.annotate(f"$z={z_fx_cr}$", xy=(5.4, -0.081), fontsize=7, ha="center")
    ax.annotate("", xy=(6.2, -0.070), xytext=(4.6, -0.070),
                arrowprops=dict(arrowstyle="-", lw=0.6, color="0.3"))

    ax.set_xticks(xs)
    ax.set_xticklabels(names)
    ax.set_ylabel(r"leverage effect corr$(r_t,\mathrm{RV}_{t+1..10})$")
    ax.set_xlim(-0.6, 6.9)
    ax.set_ylim(-0.092, 0.085)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUT / "leverage_triangle.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- F6
def f6_gate():
    corr0 = D4["toy_leak_corr_vs_lambda"]["lam0.0"]
    corr1 = D4["toy_leak_corr_vs_lambda"]["lam1.0"]
    b = D3["forecastable_flow_fraction_vs_K"]
    betas = (b["K0"]["toy_beta"], b["K1"]["toy_beta"], b["K5"]["toy_beta"])

    fig, ax = plt.subplots(figsize=(3.4, 2.35))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)

    def box(x, y, w, h, text, fs=7, fc="white"):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.12,rounding_size=0.12",
                                    facecolor=fc, edgecolor="black", lw=0.7))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", lw=0.8, color="black"))

    box(3.1, 8.5, 3.8, 1.1, "estimator / mechanism")
    arrow(4.2, 8.4, 2.6, 7.3)
    arrow(5.8, 8.4, 7.4, 7.3)
    box(0.3, 5.9, 4.4, 1.4,
        "synthetic world,\neffect PRESENT by construction", 6.5, "0.92")
    box(5.3, 5.9, 4.4, 1.4,
        "synthetic world,\neffect ABSENT by construction", 6.5, "0.92")
    arrow(2.5, 5.8, 2.5, 4.7)
    arrow(7.5, 5.8, 7.5, 4.7)
    box(0.9, 3.5, 3.2, 1.2, "must detect\n(power)", 6.5)
    box(5.9, 3.5, 3.2, 1.2, "must stay silent\n(size)", 6.5)
    arrow(3.6, 3.4, 4.6, 2.4)
    arrow(6.4, 3.4, 5.4, 2.4)
    box(2.6, 1.0, 4.8, 1.4,
        "licensed: read the evaluation\ndata once, verdict binds", 6.5)

    ax.text(5, 0.15,
            "e.g. X32c: $\\beta_K$ contracts "
            f"${betas[0]:.2f} \\to {betas[1]:.2f} \\to {betas[2]:.2f}$;   "
            "X34c: leak corr "
            f"${corr0:.2f} \\to {corr1:.2f}$, flow unchanged",
            ha="center", va="bottom", fontsize=6, color="0.25")
    fig.savefig(OUT / "gate_schematic.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- F7
def f7_perasset():
    """Per-instrument leverage effect, grouped by venue class."""
    eq = FX["leverage_contrast"]["equity_values"]
    eq_names = {"US": "US", "japan": "Japan", "europe": "Europe",
                "asia_em": "Asia-EM"}
    fx_items = sorted(FX["per_pair_leverage"].items(), key=lambda kv: kv[1])
    cr_items = sorted(CR["per_coin_leverage"].items(), key=lambda kv: kv[1])
    eq_items = sorted(eq.items(), key=lambda kv: kv[1])

    labels, vals, colors = [], [], []
    for k, v in eq_items:
        labels.append(eq_names[k]); vals.append(v); colors.append("0.20")
    for k, v in fx_items:
        name = k.replace("=X", "")
        if len(name) == 3:          # Yahoo quotes majors as USD-based "JPY=X"
            name = "USD" + name
        labels.append(name); vals.append(v); colors.append("0.50")
    for k, v in cr_items:
        labels.append(k.replace("-USD", "")); vals.append(v); colors.append("0.78")

    n_eq, n_fx = len(eq_items), len(fx_items)
    xs, x, gap = [], 0.0, 1.6
    for i in range(len(labels)):
        if i in (n_eq, n_eq + n_fx):
            x += gap
        xs.append(x)
        x += 1.0

    fig, ax = plt.subplots(figsize=(5.9, 2.3))
    ax.axhline(0, color="0.35", lw=0.7, zorder=1)
    ax.bar(xs, vals, width=0.82, color=colors, edgecolor="black", lw=0.4,
           zorder=2)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=5.8)
    ax.set_ylabel(r"leverage effect corr$(r_t,\mathrm{RV}_{t+1..10})$",
                  fontsize=7)
    for cx, name in [(sum(xs[:n_eq]) / n_eq, "equity universes"),
                     (sum(xs[n_eq:n_eq + n_fx]) / n_fx, "FX crosses"),
                     (sum(xs[n_eq + n_fx:]) / len(cr_items), "cryptocurrencies")]:
        ax.text(cx, 0.088, name, ha="center", va="top", fontsize=7)
    ax.set_ylim(-0.075, 0.095)
    ax.set_xlim(xs[0] - 0.9, xs[-1] + 0.9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUT / "leverage_perasset.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- F8
def f8_audit_matrix():
    """Multi-index battery audit: events x indices pass/fail matrix."""
    order = ["QQQ", "DIA", "IWM", "1306.T", "EXW1.DE", "2800.HK"]
    rows = [("SPY (anchor)", D1["spy"]["events"], D1["spy"]["score"])]
    for name in order:
        rec = BA["indices"][name]
        rows.append((name, rec["events"], rec["score"]))

    n_r, n_c = len(rows), len(EVENTS)
    fig, ax = plt.subplots(figsize=(3.4, 0.24 * n_r + 0.55))
    for i, (label, ev, score) in enumerate(rows):
        y = n_r - 1 - i
        for j, e in enumerate(EVENTS):
            passed = ev[e]
            ax.add_patch(Rectangle((j, y), 0.92, 0.86,
                                   facecolor="0.15" if passed else "white",
                                   edgecolor="0.4", linewidth=0.5))
        ax.text(-0.25, y + 0.43, label, ha="right", va="center", fontsize=7)
        ax.text(n_c + 0.35, y + 0.43, f"{score}/10", ha="left", va="center",
                fontsize=7)
    for j, s in enumerate(EVENT_SHORT):
        ax.text(j + 0.46, n_r + 0.12, s, ha="center", va="bottom", fontsize=6.5)
    ax.set_xlim(-3.2, n_c + 1.3)
    ax.set_ylim(-0.15, n_r + 0.5)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(OUT / "audit_matrix.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- F9
def f9_tuning_grid():
    """Experiment I tuning grid: battery score by (kA, capA, sA)."""
    cells = {(c["kA"], c["capA"], c["sA"]): c
             for c in D2["tuning_grid_stats"]["per_setting"]}
    kas = [0.25, 0.5, 1.0]
    cols = [(a, s) for a in (0.01, 0.02, 0.05) for s in (0.001, 0.002)]
    frozen = (D2["frozen_params"]["kA"], D2["frozen_params"]["capA"],
              D2["frozen_params"]["sA"])
    first = (D2["tuning"]["first_shot"]["kA"], D2["tuning"]["first_shot"]["capA"],
             D2["tuning"]["first_shot"]["sA"])

    fig, ax = plt.subplots(figsize=(3.4, 1.75))
    for i, ka in enumerate(kas):
        for j, (capa, sa) in enumerate(cols):
            c = cells[(ka, capa, sa)]
            sc = c["score"]
            shade = str(0.95 - 0.13 * sc)
            ax.add_patch(Rectangle((j, len(kas) - 1 - i), 1, 1,
                                   facecolor=shade, edgecolor="0.3", lw=0.5))
            ax.text(j + 0.5, len(kas) - 1 - i + 0.5, str(sc), ha="center",
                    va="center", fontsize=8,
                    color="white" if sc >= 5 else "black")
            key = (ka, capa, sa)
            if key == frozen:
                ax.add_patch(Rectangle((j + 0.06, len(kas) - 1 - i + 0.06),
                                       0.88, 0.88, fill=False, edgecolor="black",
                                       lw=1.4))
            if key == first:
                ax.text(j + 0.88, len(kas) - 1 - i + 0.14, "*", ha="center",
                        va="center", fontsize=9,
                        color="white" if sc >= 5 else "black")
    ax.set_xticks([j + 0.5 for j in range(len(cols))])
    ax.set_xticklabels([f"{a:g}/{s:g}" for a, s in cols], fontsize=6)
    ax.set_yticks([len(kas) - 1 - i + 0.5 for i in range(len(kas))])
    ax.set_yticklabels([f"$k_A={k:g}$" for k in kas], fontsize=7)
    ax.set_xlabel(r"$\mathrm{cap}_A$ / $s_A$", fontsize=7)
    ax.set_xlim(0, len(cols))
    ax.set_ylim(0, len(kas))
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.savefig(OUT / "tuning_grid.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- F10
def f10_score_se():
    """Battery scores with seed-bootstrap SEs for every published config."""
    order = ["G", "F", "FC", "FV", "FCV", "FCVM", "FCVMH", "FCVM+A", "FV+A",
             "F+A", "K5_FIXEDPOINT", "K5_TUNED", "FCVM+Q1.0", "FCVM+Q0.5",
             "Q_TUNED"]
    pretty = {"K5_FIXEDPOINT": "K=5 (frozen)", "K5_TUNED": "K=5 (tuned)",
              "FCVM+Q1.0": r"FCVM+Q ($\lambda_Q{=}1$)",
              "FCVM+Q0.5": r"FCVM+Q ($\lambda_Q{=}0.5$)",
              "Q_TUNED": r"FCVM+Q ($\lambda_Q{=}0.05$)"}
    labels = [pretty.get(k, k) for k in order]
    scores = [SE["scores"][k] for k in order]
    ses = [SE["se"][k] for k in order]

    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    ys = list(range(len(order)))[::-1]
    ax.axvline(5, color="0.6", lw=0.7, ls=":", zorder=1)
    ax.errorbar(scores, ys, xerr=ses, fmt="o", color="black", ms=3.2,
                capsize=2, lw=0.9, zorder=2)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_xlabel("battery score (events passed, of 10)", fontsize=7)
    ax.set_xlim(0, 10.4)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUT / "score_se.pdf")
    plt.close(fig)


if __name__ == "__main__":
    f1_scorecard()
    f2_bits()
    f3_inversion()
    f4_wildfacts()
    f5_triangle()
    f6_gate()
    f7_perasset()
    f8_audit_matrix()
    f9_tuning_grid()
    f10_score_se()
    print("wrote 10 figures to", OUT)
