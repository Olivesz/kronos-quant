"""Gate X16: surge machinery — Zumbach size & power, S3 lift size & power."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kronos.surge import (
    cascade_report,
    simulate_gjr_world,
    simulate_reversible_world,
    simulate_volofvol_world,
    surge_intensity_lift,
    zumbach_with_ci,
)

T = 6000

# NOTE: the vol proxy must be smoothed with a CENTERED window here — trailing
# smoothing breaks time symmetry mechanically (forward correlations see
# closer lags than backward ones) and manufactures a spurious arrow of time.
# Discovered by this gate's size check.
def centered(v):
    return v.rolling(5, center=True).mean()

# --- S2 power: GJR world has built-in leverage => Z > 0 ------------------------
r, v = simulate_gjr_world(T, seed=1)
zg = zumbach_with_ci(r, centered(v), n_boot=200)
print(f"GJR world       : Z={zg['z']:+.2f} CI[{zg['ci_lo']:.2f},{zg['ci_hi']:.2f}]")
assert zg["z"] > 0 and zg["ci_lo"] > 0, "Zumbach must detect GJR leverage"

# --- S2 size: reversible world => Z ~ 0 ----------------------------------------
r0, v0 = simulate_reversible_world(T, seed=2)
z0 = zumbach_with_ci(r0, centered(v0), n_boot=200)
print(f"reversible world: Z={z0['z']:+.2f} CI[{z0['ci_lo']:.2f},{z0['ci_hi']:.2f}]")
assert z0["ci_lo"] < 0 < z0["ci_hi"], "Zumbach must NOT reject on reversible world"

# --- S1 cascade machinery: clean Gaussian clock => kurt(u) ~ 3 ------------------
c0 = cascade_report(v0)
print(f"reversible clock: kurt(u)={c0['kurt_u']:.2f} ac1(|u|)={c0['ac1_absu']:+.2f} "
      f"-> kurt(z2)={c0['kurt_z2']:.2f}")
assert c0["kurt_u"] < 4.0, "Gaussian clock innovations should not be fat"

# --- S3: lift must appear iff vol-of-vol clusters ------------------------------
rets_s, proxy_s = simulate_volofvol_world(10000, switching=True, seed=3)
lift_s = surge_intensity_lift(rets_s, proxy_s, n_boot=150)
rets_c, proxy_c = simulate_volofvol_world(10000, switching=False, seed=4)
lift_c = surge_intensity_lift(rets_c, proxy_c, n_boot=150)
print(f"switching vol-of-vol: lift={lift_s['lift']:.2f} "
      f"CI[{lift_s['ci_lo']:.2f},{lift_s['ci_hi']:.2f}]")
print(f"constant  vol-of-vol: lift={lift_c['lift']:.2f} "
      f"CI[{lift_c['ci_lo']:.2f},{lift_c['ci_hi']:.2f}]")
assert lift_s["lift"] > 1.3 and lift_s["ci_lo"] > 1.0, "must detect clustered surges"
assert lift_c["ci_lo"] < 1.1, "must not invent predictability when none exists"

print("\nGATE X16 PASSED")
