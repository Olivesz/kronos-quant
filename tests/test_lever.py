"""Gate X28: the HAR forecast-vol lever (DESIGN16 V1) must track a
FORECASTABLE vol world better than the trailing-EWMA lever, and must NOT
invent an edge on an iid-vol world (the two must tie there)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

import numpy as np
import pandas as pd

from config import CFG
from kronos.risk import exposure_series

T = 4000
idx = pd.bdate_range("2012-01-02", periods=T)


def sv_world(persistent: bool, seed: int):
    """Returns (returns, true next-day ann vol). persistent=True: log-vol
    AR(1) rho=0.98 (forecastable). False: iid lognormal vol (unforecastable)."""
    rng = np.random.default_rng(seed)
    mu = np.log(0.10 / np.sqrt(252))
    if persistent:
        rho, eta = 0.98, np.sqrt(0.30 * (1 - 0.98 ** 2))
        h = np.zeros(T)
        for t in range(1, T):
            h[t] = rho * h[t - 1] + eta * rng.normal()
    else:
        h = np.sqrt(0.30) * rng.normal(size=T)
    sig = np.exp(mu + h)
    r = pd.Series(sig * rng.normal(size=T), index=idx)
    true_next = pd.Series(np.r_[sig[1:], np.nan] * np.sqrt(252), index=idx)
    return r, true_next


def tracking_error(mode: str, r: pd.Series, true_next: pd.Series) -> float:
    """RMSE of (exposure_t x true vol_{t+1}) around the vol target — how well
    the lever sizes AHEAD of tomorrow's true vol."""
    cfg = replace(CFG, lever_mode=mode, risk_smooth_days=1, max_exposure=3.0,
                  dd_start=-0.99, dd_floor_at=-1.0, cvar_target=1.0)  # brakes off
    ex = exposure_series(r, cfg)["exposure"]
    ach = (ex * true_next).iloc[300:-1]
    return float(np.sqrt(((ach - cfg.vol_target) ** 2).mean()))


# --- forecastable world: HAR lever must track better --------------------------
errs_h, errs_e = [], []
for s in (0, 1, 2):
    r, tv = sv_world(True, seed=10 + s)
    errs_h.append(tracking_error("har", r, tv))
    errs_e.append(tracking_error("ewma", r, tv))
eh, ee = np.mean(errs_h), np.mean(errs_e)
print(f"persistent-SV world: tracking RMSE har {eh:.4f} vs ewma {ee:.4f} "
      f"(gain {(1 - eh/ee)*100:+.1f}%)")
assert eh < ee * 0.97, "HAR lever fails to beat EWMA where vol IS forecastable"

# --- iid world: must tie (no false edge) --------------------------------------
errs_h, errs_e = [], []
for s in (0, 1, 2):
    r, tv = sv_world(False, seed=20 + s)
    errs_h.append(tracking_error("har", r, tv))
    errs_e.append(tracking_error("ewma", r, tv))
eh, ee = np.mean(errs_h), np.mean(errs_e)
print(f"iid-vol world: tracking RMSE har {eh:.4f} vs ewma {ee:.4f} "
      f"(ratio {eh/ee:.3f}, must be ~1)")
assert 0.9 < eh / ee < 1.1, "levers must tie when vol is unforecastable"

# --- causality: truncating the future must not change past forecasts -----------
from kronos.risk import har_vol_forecast  # noqa: E402

r, _ = sv_world(True, seed=42)
full = har_vol_forecast(r)
trunc = har_vol_forecast(r.iloc[:-250])
diff = (full.iloc[:-250] - trunc).abs().max()
print(f"causality: max forecast diff after truncating 250 future days = {diff:.2e}")
assert diff < 1e-12, "HAR lever leaks the future"

print("\nGATE X28 PASSED")
