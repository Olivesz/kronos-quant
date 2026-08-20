"""KRONOS-DECATHLON referee program estimators (DESIGN25).

Attribution and robustness machinery for the CLOSED DESIGN8 line:

  * the battery's E9 block, factored VERBATIM so the direction-bits statistic
    can be recomputed on arbitrary series (raw and AR(1)-whitened) — gate
    X36a asserts exact identity with battery()["stats"]["dir_bits"];
  * AR(1) whitening (the linear-reversal channel remover, gate-calibrated on
    an analytic AR(1) world — X36b/c);
  * the per-feature / conditional MI decomposition of E9 (R2);
  * realized anticipator strength from a closed-loop return series (R1);
  * the threshold rescorer — every battery event as a pure function of the
    per-seed statistics and a threshold dict (R6).

Nothing here touches kronos/decathlon.py's battery or simulator paths.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from kronos.decathlon import DEFAULTS, _ant_target_fp, _flow_forecast
from kronos.infobudget import LN2, direction_bits, discrete_mi

# ---------------------------------------------------------------------------
# the battery's E9 block, verbatim (identity asserted by gate X36a)
# ---------------------------------------------------------------------------

def e9_features(returns: pd.Series):
    """Feature frame + forward-sign target, exactly as battery() builds them.

    Mirrors kronos/decathlon.py battery() lines E9 (rv from the close-only
    clock, lv = 0.5*log(rv), sign/mom21/vol-tercile features, next-day sign
    target). Any drift between the two is a gate X36a failure.
    """
    r = returns.dropna()
    rv = (r ** 2).rolling(5).mean().clip(lower=1e-12)
    lv = 0.5 * np.log(rv)
    feats = pd.DataFrame({
        "sign_t": np.sign(r),
        "mom21": np.sign(r.rolling(21).sum()),
        "vol_terc": pd.qcut(lv.rank(pct=True), 3, labels=False),
    })
    fwd = np.sign(r.shift(-1)).rename("y")
    return feats, fwd


def e9_bits(returns: pd.Series, seed: int = 0, n_shuffle: int = 120) -> dict:
    """The battery's E9 statistic on an arbitrary series (bits, significant)."""
    feats, fwd = e9_features(returns)
    return direction_bits(feats, fwd, n_shuffle=n_shuffle, seed=seed)


# ---------------------------------------------------------------------------
# AR(1) whitening — removes exactly the linear one-lag channel
# ---------------------------------------------------------------------------

def ar1_whiten(returns: pd.Series) -> tuple[float, pd.Series]:
    """OLS AR(1) residuals: e_t = (r_t - rbar) - phi*(r_{t-1} - rbar).

    phi is the OLS slope, so the residuals have exactly zero sample
    covariance with the lagged regressor — the linear reversal/momentum
    channel is removed in-sample; nonlinear sign structure is untouched
    (gate X36c)."""
    x = returns.dropna().to_numpy(dtype=float)
    xc = x - x.mean()
    phi = float(np.sum(xc[1:] * xc[:-1]) / np.sum(xc[:-1] ** 2))
    e = xc[1:] - phi * xc[:-1]
    return phi, pd.Series(e, index=returns.dropna().index[1:], name="whitened")


def sign_ac1(returns: pd.Series) -> float:
    """Lag-1 autocorrelation of the sign sequence."""
    s = np.sign(returns.dropna().to_numpy(dtype=float))
    s = s - s.mean()
    return float(np.mean(s[1:] * s[:-1]) / np.mean(s * s))


# ---------------------------------------------------------------------------
# E9 mutual-information decomposition (R2)
# ---------------------------------------------------------------------------

def _mi_with_null(code: np.ndarray, y: np.ndarray, n_shuffle: int,
                  seed: int) -> dict:
    mi = discrete_mi(code, y) / LN2
    rng = np.random.default_rng(seed)
    nulls = np.array([discrete_mi(code, y[rng.permutation(len(y))]) / LN2
                      for _ in range(n_shuffle)])
    return {"bits": float(mi), "null_p95": float(np.percentile(nulls, 95)),
            "significant": bool(mi > np.percentile(nulls, 95))}


def e9_decomposition(returns: pd.Series, seed: int = 0,
                     n_shuffle: int = 120) -> dict:
    """Per-feature MI, the joint, and the conditional MI given sign_t.

    The conditional term I(mom21, vol_terc ; y | sign_t) is computed by
    stratification over sign_t, with a STRATIFIED permutation null (y
    permuted within sign_t strata) — the null that preserves the one-lag
    sign channel and tests only what is left."""
    feats, fwd = e9_features(returns)
    df = pd.concat([feats, fwd], axis=1).dropna()
    y = df["y"].to_numpy()

    def col_code(cols: tuple[str, ...]) -> np.ndarray:
        code = np.zeros(len(df), dtype=np.int64)
        mult = 1
        for c in cols:
            vals = pd.factorize(df[c])[0]
            code = code + vals * mult
            mult *= vals.max() + 1
        return code

    out = {}
    for name, cols, off in (("sign", ("sign_t",), 0),
                            ("mom", ("mom21",), 1),
                            ("vol", ("vol_terc",), 2),
                            ("joint", ("sign_t", "mom21", "vol_terc"), 3)):
        out[name] = _mi_with_null(col_code(cols), y, n_shuffle,
                                  seed * 7 + off)

    # conditional MI by stratification over sign_t
    strata = pd.factorize(df["sign_t"])[0]
    code = col_code(("mom21", "vol_terc"))

    def cmi(yv: np.ndarray) -> float:
        tot = 0.0
        for lv in np.unique(strata):
            m = strata == lv
            if m.sum() < 10:
                continue
            tot += (m.sum() / len(yv)) * discrete_mi(code[m], yv[m])
        return tot / LN2

    raw = cmi(y)
    rng = np.random.default_rng(seed * 7 + 4)
    nulls = np.empty(n_shuffle)
    for i in range(n_shuffle):
        yp = y.copy()
        for lv in np.unique(strata):
            m = np.where(strata == lv)[0]
            yp[m] = y[m][rng.permutation(len(m))]
        nulls[i] = cmi(yp)
    out["cmi_given_sign"] = {
        "bits": float(raw), "null_p95": float(np.percentile(nulls, 95)),
        "significant": bool(raw > np.percentile(nulls, 95))}
    return out


# ---------------------------------------------------------------------------
# realized anticipator strength from a closed-loop tape (R1)
# ---------------------------------------------------------------------------

def realized_strength(returns: np.ndarray, params: dict | None = None,
                      K: int = 1) -> float:
    """beta = sum(I*_t F_hat_t) / sum(F_hat_t^2) along the realized tape.

    Reconstructs the public vol state exactly as simulate_abm evolves it
    (sig2 absorbs r_{t-1} before the time-t flows are formed; r_prev = 0 at
    t = 0), rebuilds the flow forecast and the K-stack's target inventory,
    and projects the inventory on the forecast. Away from the per-layer caps
    this equals 1-(1-kA)^K by the telescoping identity; capping shrinks it —
    which is exactly what R1 needs measured."""
    p = dict(DEFAULTS)
    if params:
        p.update(params)
    sig2 = np.full(1, p["sig_target"] ** 2)
    r_prev = 0.0
    F = np.empty(len(returns))
    I = np.empty(len(returns))
    for t in range(len(returns)):
        sig2 = (1 - p["a_s"]) * sig2 + p["a_s"] * r_prev ** 2
        F[t] = _flow_forecast(sig2, p)
        I[t] = _ant_target_fp(sig2, p, K)
        r_prev = float(returns[t])
    return float(np.sum(I * F) / np.sum(F * F))


# ---------------------------------------------------------------------------
# threshold rescorer (R6)
# ---------------------------------------------------------------------------

# The battery's 12 numeric thresholds (E9 is a permutation test — no numeric
# threshold; E8's significance flag is a test verdict, only its ratio is
# numeric). Values mirror kronos/decathlon.py battery() exactly.
THRESHOLDS = {
    "e1_lo": -0.15, "e1_hi": 0.05,
    "e2_lo": 4.5, "e2_hi": 40.0,
    "e3_ac1": 0.12, "e3_slow": 0.05,
    "e4": 0.12,
    "e5": -0.03,
    "e6": 5.0,
    "e7": -0.35,
    "e8_ratio": 0.75,
    "e10": 1.25,
}


def rescore_events(st: dict, th: dict, e9_pass: bool) -> dict:
    """Every battery event as a pure function of one seed's statistics.

    st: a battery stats dict (per-seed or single-series). th: a threshold
    dict shaped like THRESHOLDS. e9_pass: E9's verdict, held fixed (its
    pass/fail is a permutation test, not a threshold). E8's significance
    flag comes from st["ep_r_sig"]; only the 0.75 ratio is perturbable."""
    return {
        "E1_efficiency": bool(th["e1_lo"] <= st["ac1_r"] <= th["e1_hi"]),
        "E2_fat_tails": bool(th["e2_lo"] <= st["kurt"] <= th["e2_hi"]),
        "E3_clustering": bool(st["ac1_absr"] >= th["e3_ac1"]
                              and st["ac_slow"] >= th["e3_slow"]),
        "E4_long_memory": bool(st["clock_ac8_level"] >= th["e4"]),
        "E5_leverage": bool(st["leverage"] <= th["e5"]),
        "E6_one_clock": bool(st["kurt_z"] <= th["e6"]),
        "E7_clock_jumps": bool(st["clock_skew_u"] >= th["e7"]),
        "E8_arrow": bool(st["ep_r_sig"] > 0.5
                         and st["ep_z"] <= th["e8_ratio"] * st["ep_r"]),
        "E9_no_sign_info": bool(e9_pass),
        "E10_tail_asym": bool(st["tail_asym"] >= th["e10"]),
    }


def rescore_config(seed_stats: list[dict], th: dict, e9_pass: bool) -> dict:
    """Majority-vote rescoring of one config from its per-seed statistics."""
    votes: dict[str, int] = {}
    for st in seed_stats:
        ev = rescore_events(st, th, e9_pass)
        for k, v in ev.items():
            votes[k] = votes.get(k, 0) + int(v)
    n = len(seed_stats)
    events = {k: votes[k] > n / 2 for k in votes}
    return {"events": events, "score": int(sum(events.values()))}
