"""DESIGN29 Stage 2: KRONOS's shipped overlay on survivorship-free factors.

The overlay is kronos.risk.exposure_series, unchanged, with the tilt the
shipped backtest builds (1 + mom_tilt * sign of the trailing 21-observation
log return). Exposure decided at close t applies to t+1; the first `warmup`
observations of the input are the overlay's training span and are not
evaluated, mirroring the shipped backtest.

Inference (all monthly):
  newey_west_alpha   spanning / full-model regressions, Bartlett-kernel HAC;
  lw_sharpe_diff     Ledoit & Wolf (2008) studentized circular-block bootstrap;
  romano_wolf        studentized stepdown over K alphas (one-sided);
  hansen_spa         Hansen (2005) studentized SPA, stationary bootstrap;
  sup_wald_break     Andrews (1993) sup-Wald for an intercept break, p-value
                     from simulated Brownian bridges (no table lookup).
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from kronos.forensics import stationary_bootstrap_indices
from kronos.risk import exposure_series
from kronos.volmanaged import ols

WARMUP = 252
NORM_WINDOW = 2520


def align_to_calendar(daily: pd.Series, calendar: pd.DatetimeIndex) -> pd.Series:
    """Compound observations on dates outside `calendar` (AQR's non-US
    holidays) into the next calendar date; dates after the last calendar date
    are dropped."""
    s = daily.dropna()
    pos = calendar.searchsorted(s.index)                 # next calendar date at or after
    keep = pos < len(calendar)
    s, pos = s[keep], pos[keep]
    out = (1.0 + s).groupby(calendar[pos]).prod() - 1.0
    out.index.name = None
    return out


def tilt_series(log_input: pd.Series, mom_tilt: float) -> pd.Series | None:
    """The shipped tilt: 1 + mom_tilt * sign(21-observation log return)."""
    if mom_tilt <= 0:
        return None
    return 1.0 + mom_tilt * np.sign(log_input.rolling(21).sum()).fillna(0.0)


def overlay_exposure(est: pd.Series, cfg, tilt_log: pd.Series | None = None) -> pd.Series:
    """Exposure decided at each close from the estimator input `est` (the
    book the overlay reads), lagged one observation: the value at t is what
    applies to t's return. Before the first decision it is NaN. The tilt reads
    `tilt_log` (default log(1 + est)), as the shipped backtest reads the
    market's log price change."""
    tl = np.log1p(est) if tilt_log is None else tilt_log
    tilt = tilt_series(tl, getattr(cfg, "mom_tilt", 0.0))
    e = exposure_series(est, cfg, tilt=tilt)["exposure"]
    return e.shift(1)


def brakes_off(cfg):
    """The grid's 'brakes off' members: CVaR and drawdown multipliers pinned
    at 1 (finite stand-ins for ∞ / −∞, which would make the drawdown ramp 0/0)."""
    return replace(cfg, cvar_target=1e9, dd_start=-1e9, dd_floor_at=-2e9)


def normalized(f: pd.Series, target: float = 0.13) -> tuple[pd.Series, pd.Series]:
    """Family rule: f̃_t = f_t * target / σ̂_{t-1}, σ̂ the trailing realized vol
    over NORM_WINDOW observations (expanding from WARMUP), annualized by √252.
    Returns (f̃, scale) where scale_t = target / σ̂_{t-1}."""
    sig = f.rolling(NORM_WINDOW, min_periods=WARMUP).std(ddof=1) * np.sqrt(252)
    scale = (target / sig).shift(1)
    return (f * scale).dropna(), scale.dropna()


def managed_daily(f: pd.Series, rf: pd.Series, cfg, est: pd.Series | None = None) -> dict:
    """The overlay on one excess-return series f. `est` is what the
    estimators read (default: f itself). Returns the daily exposure applied,
    the evaluated span (after WARMUP observations of est), and the managed
    excess return e_{t-1} * f_t on that span."""
    est = f if est is None else est.reindex(f.index)
    e = overlay_exposure(est, cfg)
    span = f.index[WARMUP:]
    e = e.reindex(span)
    if e.isna().any():
        raise ValueError("exposure undefined inside the evaluated span")
    return {"exposure": e, "managed": e * f.reindex(span), "raw": f.reindex(span),
            "rf": rf.reindex(span)}


def monthly_excess(daily_excess: pd.Series, rf: pd.Series, full_months: bool = True) -> pd.Series:
    """R_m = Π(1 + x_t + rf_t) − Π(1 + rf_t) over each calendar month: the
    excess return of a position rebalanced daily and financed / collateralized
    at the bill rate. With full_months, the first month is dropped unless the
    series starts on that month's first observation of rf."""
    x = daily_excess.dropna()
    r = rf.reindex(x.index)
    per = x.index.to_period("M")
    gross = (1.0 + x + r).groupby(per).prod()
    cash = (1.0 + r).groupby(per).prod()
    out = gross - cash
    if full_months and len(x):
        first = per[0]
        rf_first_day = rf.index[rf.index.to_period("M") == first][0]
        if x.index[0] != rf_first_day:
            out = out.iloc[1:]
    return out


# ---------------------------------------------------------------------------
# inference
# ---------------------------------------------------------------------------

def newey_west_alpha(y: pd.Series, X: pd.DataFrame, lags: int = 12) -> dict:
    """α (×12), NW SE (×12), t, betas, N, span."""
    df = pd.concat([y.rename("_y"), X], axis=1).dropna()
    Z = np.column_stack([np.ones(len(df)), df[X.columns].to_numpy()])
    r = ols(df["_y"].to_numpy(), Z, "nw", lags)
    return {"alpha": 12 * r["coef"][0], "se": 12 * r["se"][0], "t": r["coef"][0] / r["se"][0],
            "betas": dict(zip(X.columns, r["coef"][1:].tolist())), "r2": r["r2"], "n": r["n"],
            "span": [str(df.index[0]), str(df.index[-1])]}


def _sr_diff_and_se(a: np.ndarray, b: np.ndarray, lags: int) -> tuple[float, float]:
    """SR(a) − SR(b) (monthly units) and its delta-method HAC SE (Bartlett)."""
    T = len(a)
    m1, m2 = a.mean(), b.mean()
    g1, g2 = (a ** 2).mean(), (b ** 2).mean()
    d = m1 / np.sqrt(g1 - m1 ** 2) - m2 / np.sqrt(g2 - m2 ** 2)
    grad = np.array([g1 / (g1 - m1 ** 2) ** 1.5, -g2 / (g2 - m2 ** 2) ** 1.5,
                     -0.5 * m1 / (g1 - m1 ** 2) ** 1.5, 0.5 * m2 / (g2 - m2 ** 2) ** 1.5])
    Y = np.column_stack([a - m1, b - m2, a ** 2 - g1, b ** 2 - g2])
    S = Y.T @ Y / T
    for L in range(1, lags + 1):
        G = Y[L:].T @ Y[:-L] / T
        S += (1 - L / (lags + 1)) * (G + G.T)
    return float(d), float(np.sqrt(max(grad @ S @ grad, 1e-300) / T))


def lw_sharpe_diff(a: pd.Series, b: pd.Series, block: int = 12, n_boot: int = 5000,
                   seed: int = 42) -> dict:
    """Ledoit & Wolf (2008): one-sided p for H0 SR(a) <= SR(b). The original
    statistic is studentized by a Bartlett HAC SE (lags = block); each
    circular-block resample is studentized by the block-sum SE LW prescribe."""
    df = pd.concat([a, b], axis=1).dropna()
    x, y = df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy()
    T = len(x)
    d0, se0 = _sr_diff_and_se(x, y, block)
    rng = np.random.default_rng(seed)
    L = T // block                            # whole blocks for the resample's SE
    stats_ = np.empty(n_boot)
    for i in range(n_boot):
        idx = _cbb_index(T, block, rng)
        xs, ys = x[idx], y[idx]
        m1, m2, g1, g2 = xs.mean(), ys.mean(), (xs ** 2).mean(), (ys ** 2).mean()
        d = m1 / np.sqrt(g1 - m1 ** 2) - m2 / np.sqrt(g2 - m2 ** 2)
        grad = np.array([g1 / (g1 - m1 ** 2) ** 1.5, -g2 / (g2 - m2 ** 2) ** 1.5,
                         -0.5 * m1 / (g1 - m1 ** 2) ** 1.5, 0.5 * m2 / (g2 - m2 ** 2) ** 1.5])
        Yb = np.column_stack([xs - m1, ys - m2, xs ** 2 - g1, ys ** 2 - g2])[:L * block]
        sums = Yb.reshape(L, block, 4).sum(axis=1) / np.sqrt(block)
        Psi = sums.T @ sums / L
        se = np.sqrt(max(grad @ Psi @ grad, 1e-300) / T)
        stats_[i] = (d - d0) / se
    t0 = d0 / se0
    p = (np.sum(stats_ >= t0) + 1) / (n_boot + 1)
    return {"sr_a": float(np.sqrt(12) * x.mean() / x.std(ddof=1)),
            "sr_b": float(np.sqrt(12) * y.mean() / y.std(ddof=1)),
            "diff_annual": float(np.sqrt(12) * d0), "t": float(t0), "p_one_sided": float(p),
            "n": T, "span": [str(df.index[0]), str(df.index[-1])]}


def _cbb_index(T: int, block: int, rng) -> np.ndarray:
    nb = int(np.ceil(T / block))
    starts = rng.integers(0, T, nb)
    return ((starts[:, None] + np.arange(block)[None, :]) % T).ravel()[:T]


def romano_wolf(Y: pd.DataFrame, X: dict[str, pd.DataFrame], lags: int = 12, block: int = 12,
                n_boot: int = 5000, seed: int = 42, level: float = 0.05) -> dict:
    """Studentized stepdown (Romano & Wolf 2005) for H_k: α_k <= 0, k = columns
    of Y, each regressed on its own design X[k], on the rows where every
    series exists. Rows are resampled jointly by circular blocks."""
    names = list(Y.columns)
    allX = pd.concat([Y] + [X[k].add_prefix(f"{k}|") for k in names], axis=1).dropna()
    T = len(allX)
    designs = {k: np.column_stack([np.ones(T), allX[[f"{k}|{c}" for c in X[k].columns]].to_numpy()])
               for k in names}
    ys = {k: allX[k].to_numpy() for k in names}
    fit = {k: ols(ys[k], designs[k], "nw", lags) for k in names}
    a0 = np.array([fit[k]["coef"][0] for k in names])
    t0 = np.array([fit[k]["coef"][0] / fit[k]["se"][0] for k in names])
    rng = np.random.default_rng(seed)
    tb = np.empty((n_boot, len(names)))
    for i in range(n_boot):
        idx = _cbb_index(T, block, rng)
        for j, k in enumerate(names):
            r = ols(ys[k][idx], designs[k][idx], "nw", lags)
            tb[i, j] = (r["coef"][0] - a0[j]) / r["se"][0]
    active = np.ones(len(names), bool)
    rejected = np.zeros(len(names), bool)
    while active.any():
        crit = np.quantile(tb[:, active].max(axis=1), 1 - level)
        new = active & (t0 > crit)
        if not new.any():
            break
        rejected |= new
        active &= ~new
    # stepdown-adjusted p-values (monotone)
    order = np.argsort(-t0)
    padj = np.empty(len(names))
    run = 0.0
    for r_, j in enumerate(order):
        rest = order[r_:]
        p = (np.sum(tb[:, rest].max(axis=1) >= t0[j]) + 1) / (n_boot + 1)
        run = max(run, p)
        padj[j] = run
    return {"names": names, "t": t0.tolist(), "alpha": (12 * a0).tolist(),
            "rejected": dict(zip(names, rejected.tolist())), "p_adj": dict(zip(names, padj.tolist())),
            "n": T, "span": [str(allX.index[0]), str(allX.index[-1])]}


def hansen_spa(D: pd.DataFrame, mean_block: float = 12, n_boot: int = 5000, seed: int = 42) -> dict:
    """Hansen (2005) consistent studentized SPA. H0: max_k E[d_k] <= 0, d_k
    the performance differentials (columns of D), on the common rows."""
    d = D.dropna().to_numpy()
    n, K = d.shape
    dbar = d.mean(axis=0)
    rng = np.random.default_rng(seed)
    boot = np.empty((n_boot, K))
    for i in range(n_boot):
        boot[i] = d[stationary_bootstrap_indices(n, mean_block, rng)].mean(axis=0)
    omega = np.sqrt(n * ((boot - dbar) ** 2).mean(axis=0))
    tstat = max(float(np.max(np.sqrt(n) * dbar / omega)), 0.0)
    thresh = -np.sqrt(2 * np.log(np.log(n)))
    mu_c = np.where(np.sqrt(n) * dbar / omega <= thresh, dbar, 0.0)
    tb = np.maximum((np.sqrt(n) * (boot - dbar + mu_c) / omega).max(axis=1), 0.0)
    return {"stat": tstat, "p": float((np.sum(tb >= tstat) + 1) / (n_boot + 1)), "n": n,
            "names": list(D.columns), "t_each": (np.sqrt(n) * dbar / omega).tolist()}


def sup_wald_break(y: pd.Series, x: pd.Series, trim: float = 0.15, lags: int = 12,
                   n_sim: int = 20000, grid: int = 1000, seed: int = 42) -> dict:
    """Andrews (1993) sup-Wald for a break in the intercept of y = α + βx + ε
    (β held common), NW covariance; p-value from n_sim simulated Brownian
    bridges, sup over π in [trim, 1-trim] of B(π)² / (π(1-π))."""
    df = pd.concat([y, x], axis=1).dropna()
    T = len(df)
    yv, xv = df.iloc[:, 0].to_numpy(), df.iloc[:, 1].to_numpy()
    lo, hi = int(np.floor(trim * T)), int(np.ceil((1 - trim) * T))
    best, at = -np.inf, None
    for k in range(lo, hi):
        D = (np.arange(T) >= k).astype(float)
        Z = np.column_stack([np.ones(T), D, xv])
        r = ols(yv, Z, "nw", lags)
        w = (r["coef"][1] / r["se"][1]) ** 2
        if w > best:
            best, at = w, k
    rng = np.random.default_rng(seed)
    pis = np.arange(1, grid + 1) / grid
    sel = (pis >= trim) & (pis <= 1 - trim)
    sims = np.empty(n_sim)
    for i in range(0, n_sim, 1000):
        W = np.cumsum(rng.standard_normal((1000, grid)), axis=1) / np.sqrt(grid)
        B = W - pis[None, :] * W[:, -1:]
        sims[i:i + 1000] = (B[:, sel] ** 2 / (pis[sel] * (1 - pis[sel]))).max(axis=1)
    return {"sup_wald": float(best), "break_at": str(df.index[at]), "p": float(np.mean(sims >= best)),
            "n": T}


# ---------------------------------------------------------------------------
# the registered program
# ---------------------------------------------------------------------------

FAMILY = ["SMB", "HML", "RMW", "CMA", "UMD", "BAB"]
REGRESSORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "UMD", "BAB"]
HOLDOUT_END = pd.Period("2012-12", "M")
CONTAMINATED_START = pd.Period("2013-01", "M")
FULL_START = pd.Period("1963-07", "M")
ERAS = [("1927-07", "1945-12"), ("1946-01", "1962-12"), ("1963-01", "1987-12"), ("1988-01", "2012-12")]


def daily_inputs() -> pd.DataFrame:
    """French's daily factors + AQR's US BAB on French's calendar, Saturday
    sessions compounded into the next observation (DESIGN29 Stage 2)."""
    from kronos import factors as F
    d = F.french("daily")
    d = d.join(align_to_calendar(F.bab_daily(), d.index).rename("BAB"))
    return F.merge_saturdays(d)


def grid_configs(cfg) -> dict:
    """The registered 8-member Mkt grid; the primary is (0.15, 1.5, on)."""
    out = {}
    for tilt in (0.0, 0.15):
        for cap in (1.0, 1.5):
            for brakes in ("on", "off"):
                c = replace(cfg, mom_tilt=tilt, max_exposure=cap)
                out[f"tilt{tilt}_cap{cap}_brakes{brakes}"] = c if brakes == "on" else brakes_off(c)
    return out


PRIMARY = "tilt0.15_cap1.5_brakeson"


def run_stage2(cfg, n_boot: int = 5000) -> dict:
    """Everything DESIGN29 Stage 2 registers, on the holdout (to 2012-12),
    plus the descriptive contaminated window. Pure: no cache, no writes."""
    from kronos.forensics import cscv_pbo, deflated_sharpe
    from kronos.metrics import dtb3_daily
    from kronos.risk import har_vol_forecast

    d = daily_inputs()
    rf = d["RF"]
    regs = pd.DataFrame({k: monthly_excess(d[k].dropna(), rf) for k in REGRESSORS})
    out = {"conventions": {
        "monthly": "R = prod(1 + e_{t-1} f_t + rf_t) - prod(1 + rf_t) over full calendar months",
        "saturdays": "compounded into the next observation; BAB aligned to French's calendar",
        "warmup": f"{WARMUP} observations of the overlay input; family adds {WARMUP} for the vol scale",
        "alpha": "x12, Newey-West 12 lags", "holdout_end": str(HOLDOUT_END)}}

    # --- the Mkt grid (primary = shipped) ---------------------------------
    f, est = d["Mkt-RF"], d["Mkt-RF"] + rf
    grid_m, grid_d, prim = {}, {}, None
    for name, c in grid_configs(cfg).items():
        md = managed_daily(f, rf, c, est=est)
        grid_m[name] = monthly_excess(md["managed"], rf)
        grid_d[name] = md
        if name == PRIMARY:
            prim = md
    raw_m = monthly_excess(prim["raw"], rf)
    pm = grid_m[PRIMARY]
    H = slice(None, HOLDOUT_END)

    series = {"Mkt-RF": (pm, raw_m)}
    family_scale = {}
    for k in FAMILY:
        fk = d[k].dropna()
        ft, scale = normalized(fk)
        md = managed_daily(ft, rf, cfg)
        series[k] = (monthly_excess(md["managed"], rf),
                     monthly_excess(fk.reindex(md["managed"].index), rf))
        family_scale[k] = {"median_scale": float(scale.loc[:"2012-12-31"].median()),
                           "eval_start": str(md["managed"].index[0].date())}

    uni, full, lw = {}, {}, {}
    for k, (man, raw) in series.items():
        uni[k] = newey_west_alpha(man.loc[H], raw.loc[H].to_frame(k))
        full[k] = newey_west_alpha(man.loc[FULL_START:HOLDOUT_END], regs.loc[FULL_START:HOLDOUT_END])
        lw[k] = lw_sharpe_diff(man.loc[H], raw.loc[H], n_boot=n_boot)
    out["univariate"], out["full_model"], out["ledoit_wolf"] = uni, full, lw
    out["family_scale"] = family_scale

    Y = pd.DataFrame({k: series[k][0] for k in series}).loc[FULL_START:HOLDOUT_END]
    X = dict.fromkeys(series, regs.loc[FULL_START:HOLDOUT_END])
    out["romano_wolf"] = romano_wolf(Y, X, n_boot=n_boot)
    hedged = pd.DataFrame({k: Y[k] - sum(b * regs[c].loc[FULL_START:HOLDOUT_END]
                                         for c, b in full[k]["betas"].items()) for k in series})
    out["spa"] = hansen_spa(hedged, n_boot=n_boot)

    # --- DSR and PBO --------------------------------------------------------
    prim_daily = prim["managed"].loc[:"2012-12-31"]
    trial_srs = [float(g["managed"].loc[:"2012-12-31"].mean() / g["managed"].loc[:"2012-12-31"].std())
                 for g in grid_d.values()]
    out["dsr_program_sr0"] = deflated_sharpe(prim_daily, 202, trial_srs=np.array(trial_srs))
    G = pd.DataFrame(grid_m).loc[H].dropna()
    pbo = cscv_pbo(G.to_numpy(), n_blocks=16)
    out["pbo_grid"] = {"pbo": pbo["pbo"], "n_combos": pbo["n_combos"], "n_variants": pbo["n_variants"],
                       "median_oos_rank": pbo["median_oos_rank"], "span": [str(G.index[0]), str(G.index[-1])],
                       "members": list(G.columns)}
    out["grid_sharpe"] = {k: float(np.sqrt(12) * v.loc[H].mean() / v.loc[H].std(ddof=1)) for k, v in grid_m.items()}

    # --- stability ----------------------------------------------------------
    out["eras"] = {f"{a}..{b}": newey_west_alpha(pm.loc[a:b], raw_m.loc[a:b].to_frame("Mkt-RF"))
                   for a, b in ERAS}
    out["sup_wald"] = sup_wald_break(pm.loc[H], raw_m.loc[H])

    # --- decision (registered rule) ----------------------------------------
    fm, rw = full["Mkt-RF"], out["romano_wolf"]
    eras_pos = sum(v["alpha"] > 0 for v in out["eras"].values())
    crit = {"1_full_model_t_ge_3": bool(fm["alpha"] > 0 and fm["t"] >= 3.0),
            "2_lw_p_lt_0.05": bool(lw["Mkt-RF"]["p_one_sided"] < 0.05),
            "3_romano_wolf": bool(rw["rejected"]["Mkt-RF"]),
            "4_eras_3_of_4": bool(eras_pos >= 3)}
    out["decision"] = {"criteria": crit, "eras_positive": int(eras_pos),
                       "verdict": "EARNS ALPHA" if all(crit.values()) else "NO ALPHA SURVIVES"}

    # --- costs ---------------------------------------------------------------
    e = prim["exposure"].loc[:"2012-12-31"]
    years = (e.index[-1] - e.index[0]).days / 365.25
    turn = float(e.diff().abs().sum() / years)
    out["costs"] = {"annual_turnover": turn,
                    "breakeven_bp_univariate": float(uni["Mkt-RF"]["alpha"] / turn * 1e4),
                    "breakeven_bp_full_model": float(fm["alpha"] / turn * 1e4),
                    "mean_exposure": float(e.mean()),
                    "share_at_cap": float((e >= cfg.max_exposure - 1e-9).mean())}

    # --- robustness and description (never decisive) ------------------------
    sp = prim["managed"].loc["1954-02-01":"2012-12-31"].index
    spread = dtb3_daily(sp) - rf.reindex(sp)
    fin = (prim["exposure"].reindex(sp) - 1.0).clip(lower=0.0) * spread
    pm_dtb3 = monthly_excess(prim["managed"].reindex(sp) - fin, rf)
    out["robust_dtb3"] = {
        "univariate": newey_west_alpha(pm_dtb3, raw_m.loc[pm_dtb3.index[0]:HOLDOUT_END].to_frame("Mkt-RF")),
        "full_model": newey_west_alpha(pm_dtb3.loc[FULL_START:], regs.loc[FULL_START:HOLDOUT_END]),
        "mean_spread_ann": float(spread.mean() * 252)}
    C = slice(CONTAMINATED_START, None)
    out["contaminated"] = {"univariate": newey_west_alpha(pm.loc[C], raw_m.loc[C].to_frame("Mkt-RF")),
                           "sr_managed": float(np.sqrt(12) * pm.loc[C].mean() / pm.loc[C].std(ddof=1)),
                           "sr_raw": float(np.sqrt(12) * raw_m.loc[C].mean() / raw_m.loc[C].std(ddof=1)),
                           "span": [str(pm.loc[C].index[0]), str(pm.loc[C].index[-1])]}
    v = vix_close() / 100.0
    h = har_vol_forecast(est)
    j = pd.concat([h, v], axis=1, keys=["har", "vix"]).dropna()
    out["vix"] = {"corr_holdout": float(j.loc[:"2012-12-31"].corr().iloc[0, 1]),
                  "corr_contaminated": float(j.loc["2013-01-01":].corr().iloc[0, 1]),
                  "span": [str(j.index[0].date()), str(j.index[-1].date())],
                  "note": "descriptive: HAR forecast on the market vs VIX/100, same day"}
    return out


def vix_close() -> pd.Series:
    """Cboe's VIX daily close (1990 on), hash-verified like every vendor file."""
    import io

    from kronos.data import FLOAT_PARSE
    from kronos.factors import _verified_bytes
    df = pd.read_csv(io.BytesIO(_verified_bytes("VIX_History.csv")), float_precision=FLOAT_PARSE)
    s = pd.Series(df["CLOSE"].to_numpy(), index=pd.to_datetime(df["DATE"], format="%m/%d/%Y"),
                  name="VIX")
    if s.index.has_duplicates or not s.index.is_monotonic_increasing:
        raise ValueError("VIX_History.csv: dates not strictly increasing")
    return s
