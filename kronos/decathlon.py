"""KRONOS-DECATHLON: the minimal market vs the ten-event battery (DESIGN8).

battery(returns)  -> ten pass/fail events + raw statistics, close-only,
                     identical code for real data and simulations.
simulate_abm(...) -> the minimal market with ablatable ingredient flows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kronos.entropyprod import ep_with_null
from kronos.infobudget import direction_bits
from kronos.rough import estimate_hurst

# ---------------------------------------------------------------------------
# the battery
# ---------------------------------------------------------------------------

def _acf(x: np.ndarray, lag: int) -> float:
    x = x - x.mean()
    if lag >= len(x):
        return 0.0
    return float(np.mean(x[lag:] * x[:-lag]) / np.mean(x * x))


def weekly_clock_stats(r: pd.Series) -> dict:
    """Clock statistics from NON-overlapping weekly means of log r^2,
    via AR(1) innovations (raw weekly differences carry an MA(1) artifact
    that makes even GBM's |diff| autocorrelate — gate X19 lesson)."""
    lr2 = np.log((r.to_numpy() ** 2).clip(min=1e-12))
    n = len(lr2) // 5
    wl = lr2[:n * 5].reshape(n, 5).mean(axis=1)
    # long memory of the clock level
    ac8 = _acf(wl, 8)
    # AR(1) innovations
    x, y = wl[:-1], wl[1:]
    phi = float(np.cov(x, y)[0, 1] / np.var(x))
    u = y - wl.mean() * (1 - phi) - phi * x
    return {"ac8_level": ac8,
            "skew_u": float(pd.Series(u).skew()),
            "ac1_absu": _acf(np.abs(u), 1),
            "phi": phi}


def battery(returns: pd.Series, seed: int = 0) -> dict:
    """Ten events. returns: daily simple/log returns with DatetimeIndex."""
    r = returns.dropna()
    rv = (r ** 2).rolling(5).mean().clip(lower=1e-12)       # close-only clock
    sigma = np.sqrt(rv)
    z = (r / sigma).dropna()
    rr = r.to_numpy()
    out = {"stats": {}, "events": {}}
    S, E = out["stats"], out["events"]

    # E1 efficiency: no trend persistence; the mild daily REVERSAL real
    # indices show (SPY ac1 ~ -0.10) is allowed — calibrated in gate X19
    S["ac1_r"] = _acf(rr, 1)
    E["E1_efficiency"] = -0.15 <= S["ac1_r"] <= 0.05

    # E2 fat tails
    S["kurt"] = float(r.kurtosis()) + 3.0
    E["E2_fat_tails"] = 4.5 <= S["kurt"] <= 40.0

    # E3 vol clustering
    a = np.abs(rr)
    S["ac1_absr"] = _acf(a, 1)
    S["ac_slow"] = float(np.mean([_acf(a, k) for k in range(5, 21)]))
    E["E3_clustering"] = S["ac1_absr"] >= 0.12 and S["ac_slow"] >= 0.05

    # E4 long-memory clock: weekly log-RV level autocorrelation at lag 8.
    # (Close-only Hurst is too noisy — rolling overlap gives GBM a fake
    # H≈0.13; the 8-week level AC separates cleanly: SPY 0.19, GBM 0.02,
    # and even GJR-GARCH fails at 0.06 — exponential memory can't fake it.)
    wc = weekly_clock_stats(r)
    S.update({f"clock_{k}": v for k, v in wc.items()})
    S["hurst"] = estimate_hurst(rv)["H"]      # informational only
    E["E4_long_memory"] = wc["ac8_level"] >= 0.12

    # E5 leverage
    rv_np = rv.to_numpy()
    levs = []
    for tau in range(1, 11):
        x, y = rr[:-tau], rv_np[tau:]
        ok = np.isfinite(x) & np.isfinite(y)
        levs.append(np.corrcoef(x[ok], y[ok])[0, 1])
    S["leverage"] = float(np.mean(levs))
    E["E5_leverage"] = S["leverage"] <= -0.03

    # E6 one-clock Gaussianization
    S["kurt_z"] = float(z.kurtosis()) + 3.0
    E["E6_one_clock"] = S["kurt_z"] <= 5.0

    # E7 clock jumps: weekly log-r^2 noise has a heavy LEFT tail (log chi2),
    # skew_u ~ -0.5..-0.8 on GBM; real vol's UP-jumps cancel much of it
    # (SPY -0.22). Pass = innovations skew above the noise floor.
    E["E7_clock_jumps"] = S["clock_skew_u"] >= -0.35

    # E8 arrow in the coupling: returns are irreversible AND deformation
    # substantially reduces it (close-only deformation cannot fully erase
    # the arrow the way GK deformation does — ratio criterion, gate X19)
    ep_r = ep_with_null(rr, n=3, n_null=120, seed=seed)
    ep_z = ep_with_null(z.to_numpy(), n=3, n_null=120, seed=seed + 1)
    S["ep_r"], S["ep_z"] = ep_r["ep_bits"], ep_z["ep_bits"]
    S["ep_r_sig"], S["ep_z_sig"] = ep_r["significant"], ep_z["significant"]
    E["E8_arrow"] = bool(ep_r["significant"]
                         and S["ep_z"] <= 0.75 * S["ep_r"])

    # E9 no sign information
    lv = 0.5 * np.log(rv)
    feats = pd.DataFrame({
        "sign_t": np.sign(r),
        "mom21": np.sign(r.rolling(21).sum()),
        "vol_terc": pd.qcut(lv.rank(pct=True), 3, labels=False),
    })
    fwd = np.sign(r.shift(-1))
    db = direction_bits(feats, fwd.rename("y"), n_shuffle=120, seed=seed)
    S["dir_bits"] = db["bits"]
    E["E9_no_sign_info"] = not db["significant"]

    # E10 gain/loss tail asymmetry: crashes outnumber melt-ups at 2.5 sigma.
    # (Vol-of-vol clustering is invisible in close-only weekly innovations —
    # the GK-based version lives in SURGE; this replaces it with another
    # measured fact a generative model must hit.)
    sd = rr.std()
    n_dn = int((rr < -2.5 * sd).sum())
    n_up = int((rr > 2.5 * sd).sum())
    S["tail_asym"] = float(n_dn / max(n_up, 1))
    E["E10_tail_asym"] = S["tail_asym"] >= 1.25

    out["score"] = int(sum(E.values()))
    return out


# ---------------------------------------------------------------------------
# the minimal market
# ---------------------------------------------------------------------------

# Frozen after one pre-registered tuning pass on the full config (E1/E2/E3 +
# sane vol only; documented in DESIGN8 amendment). Ablations zero out flows,
# never retune.
DEFAULTS = dict(
    lam=1.0,            # price impact
    kF=0.15,            # fundamentalist strength
    kC=0.003,           # chartist strength
    s_c=0.01,           # chartist signal scale (tanh saturation)
    kV=0.06,            # vol-targeter flow strength
    sig_target=0.010,   # vol-targeters' daily vol target
    Lmax=3.0,
    kM=0.30,            # market-maker (liquidity provider) flow
    sN=0.005,           # noise-trader flow
    sV=0.006,           # fundamental innovation vol
    a_m=1 / 10,         # chartist EWMA speed (single-scale)
    a_s=1 / 8,          # vol-estimate EWMA speed (single-scale)
    # --- anticipatory agent (DESIGN18) --- FROZEN after the one
    # pre-registered tuning pass (grid on seeds 900-903, disjoint from
    # evaluation seeds; first shot kA=0.5/capA=0.02/sA=0.002 scored 4/10;
    # the grid tied at 5/10 across all weak settings and the pre-declared
    # tie-break picked the weakest — itself part of the finding: the
    # battery scores best when the anticipator trades LEAST).
    kA=0.25,            # fraction of the integrated forecast flow front-run
    capA=0.01,          # inventory cap (limited capital)
    sA=0.001,           # execution/forecast noise
)


def _ant_target(sig2: np.ndarray, p: dict) -> float:
    """Anticipator's target inventory — a pure function of the CURRENT vol
    state (causality is gate X30b's contract).

    The vol-targeters' mandate is public: L = min(Lmax, sig*/sigma_hat) on a
    known EWMA of the tape. Under the anticipator's one belief — vol reverts
    to the targeters' own target — leverage ends at L_eq = min(Lmax, 1), so
    the INTEGRATED future mechanical flow the current state implies is
    kV * mean(L_eq - L). Hold kA of it, capped by capital."""
    L = np.minimum(p["Lmax"],
                   p["sig_target"] / np.maximum(np.sqrt(sig2), 1e-5))
    f_hat = p["kV"] * float((min(p["Lmax"], 1.0) - L).mean())
    return float(np.clip(p["kA"] * f_hat, -p["capA"], p["capA"]))


def anticipator_flows(r: np.ndarray, params: dict | None = None,
                      hetero: bool = False) -> np.ndarray:
    """Deterministic trade path of the anticipatory agent against an
    EXOGENOUS return series. flow[t] depends on r[:t] only — the time-t trade
    is decided before r[t] exists (same alignment as simulate_abm, where the
    vol state has absorbed returns through t-1 when flows are formed).
    Gate X30b tampers with the future and requires the prefix unchanged."""
    p = dict(DEFAULTS)
    if params:
        p.update(params)
    s_speeds = np.array([1 / 5, 1 / 20, 1 / 80]) if hetero else np.array([p["a_s"]])
    sig2 = np.full(len(s_speeds), p["sig_target"] ** 2)
    I_prev = 0.0
    out = np.empty(len(r))
    for t in range(len(r)):
        I_star = _ant_target(sig2, p)
        out[t] = I_star - I_prev
        I_prev = I_star
        sig2 = (1 - s_speeds) * sig2 + s_speeds * r[t] ** 2
    return out


def simulate_abm(T: int = 6000, seed: int = 0,
                 fundamentalists: bool = True, chartists: bool = True,
                 voltargeters: bool = True, marketmakers: bool = True,
                 hetero: bool = False, anticipators: bool = False,
                 params: dict | None = None) -> pd.Series:
    """Returns a pd.Series of daily returns from the minimal market."""
    p = dict(DEFAULTS)
    if params:
        p.update(params)
    rng = np.random.default_rng(seed)

    # heterogeneous timescales = PARALLEL COHORTS: separate vol-targeter
    # populations each running their own horizon's leverage spiral (the
    # cascade mechanism). Averaging the estimates into one flow — the first
    # implementation — merely damps the spiral and LOSES the tails.
    m_speeds = np.array([1 / 5, 1 / 20, 1 / 80]) if hetero else np.array([p["a_m"]])
    s_speeds = np.array([1 / 5, 1 / 20, 1 / 80]) if hetero else np.array([p["a_s"]])
    m = np.zeros(len(m_speeds))
    sig2 = np.full(len(s_speeds), p["sig_target"] ** 2)
    L_prev = np.ones(len(s_speeds))
    kV_each = p["kV"] / len(s_speeds)        # total flow budget conserved

    price, V = 0.0, 0.0
    out = np.empty(T)
    r_prev = 0.0
    I_ant = 0.0                              # anticipator inventory (DESIGN18)
    for t in range(T):
        V += p["sV"] * rng.normal()
        m = (1 - m_speeds) * m + m_speeds * r_prev
        sig2 = (1 - s_speeds) * sig2 + s_speeds * r_prev ** 2

        D = p["sN"] * rng.normal()
        if fundamentalists:
            D += p["kF"] * (V - price)
        if chartists:
            D += p["kC"] * np.tanh(float(m.mean()) / p["s_c"])
        if voltargeters:
            L = np.minimum(p["Lmax"],
                           p["sig_target"] / np.maximum(np.sqrt(sig2), 1e-5))
            D += float(kV_each * (L - L_prev).sum())   # each cohort's flow
            L_prev = L
        if marketmakers:
            D += -p["kM"] * r_prev           # liquidity provision (reversion)
        if anticipators:
            # trade toward the target inventory implied by the forecast of
            # the vol-targeters' remaining mechanical flow (current state
            # only — no look-ahead), plus execution noise. The extra RNG
            # draw happens ONLY behind this flag: with anticipators=False
            # the draw sequence, and hence the output, is byte-identical
            # to the pre-DESIGN18 simulator (gate X30a).
            I_star = _ant_target(sig2, p)
            D += (I_star - I_ant) + p["sA"] * rng.normal()
            I_ant = I_star
        r = p["lam"] * D
        r = float(np.clip(r, -0.25, 0.25))      # circuit breaker (data hygiene)
        price += r
        out[t] = r
        r_prev = r
    idx = pd.bdate_range("2002-01-01", periods=T)
    return pd.Series(out, index=idx, name="abm")


CONFIGS = {
    "G":     dict(fundamentalists=False, chartists=False, voltargeters=False,
                  marketmakers=False),
    "F":     dict(fundamentalists=True, chartists=False, voltargeters=False,
                  marketmakers=False),
    "FC":    dict(fundamentalists=True, chartists=True, voltargeters=False,
                  marketmakers=False),
    "FV":    dict(fundamentalists=True, chartists=False, voltargeters=True,
                  marketmakers=False),
    "FCV":   dict(fundamentalists=True, chartists=True, voltargeters=True,
                  marketmakers=False),
    "FCVM":  dict(fundamentalists=True, chartists=True, voltargeters=True,
                  marketmakers=True),
    "FCVMH": dict(fundamentalists=True, chartists=True, voltargeters=True,
                  marketmakers=True, hetero=True),
}

# DESIGN18 ablation: does EXPECTATION break the 5/10 ceiling?
CONFIGS2 = {
    "FCVM":   dict(fundamentalists=True, chartists=True, voltargeters=True,
                   marketmakers=True),
    "FCVM+A": dict(fundamentalists=True, chartists=True, voltargeters=True,
                   marketmakers=True, anticipators=True),
    "FV+A":   dict(fundamentalists=True, chartists=False, voltargeters=True,
                   marketmakers=False, anticipators=True),
    "F+A":    dict(fundamentalists=True, chartists=False, voltargeters=False,
                   marketmakers=False, anticipators=True),
}


def run_decathlon(n_seeds: int = 8, T: int = 6000,
                  configs: dict | None = None, seed0: int = 100) -> dict:
    """Ablation table: per config, the majority-vote event passes."""
    results = {}
    for name, cfg in (configs or CONFIGS).items():
        votes = None
        stats_acc = []
        for s in range(n_seeds):
            r = simulate_abm(T=T, seed=seed0 + s, **cfg)
            b = battery(r, seed=s)
            v = {k: int(bool(x)) for k, x in b["events"].items()}
            votes = v if votes is None else {k: votes[k] + v[k] for k in v}
            stats_acc.append(b["stats"])
        passed = {k: votes[k] > n_seeds / 2 for k in votes}
        med = {k: float(np.median([st[k] for st in stats_acc]))
               for k in stats_acc[0] if isinstance(stats_acc[0][k], (int, float))}
        results[name] = {"events": passed, "score": int(sum(passed.values())),
                         "median_stats": med}
    return results
