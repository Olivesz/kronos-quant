"""Gate X25: the K-hallucination machinery (kronos/tails.py) must CONVICT
fat tails and EXONERATE genuine regimes.

tails.py powers the KRONOS-X² "regimes or fat tails?" study. Its claim: a
Gaussian-emission HMM, scored by held-out predictive density over K, is
*rewarded* for adding spurious states (K>3) on a fat-tailed world because
extra regimes let it fake leptokurtosis; a Student-t HMM, which models
kurtosis *within* states, is not. On a genuinely Gaussian K=3 world neither
family is tempted.

This gate drives the real public API on worlds with KNOWN truth (true K=3
everywhere; the only difference is Gaussian vs Student-t(nu=5) emissions):

  * gen_world / mc_khallucination — the held-out model-selection Monte Carlo.
  * generic_walkforward           — the causal predictive-density driver.

SIZE  (null Gaussian world, K=3 truly correct): the two families are equally
      (un)tempted by K>3 — the hallucination detector does NOT fire.
POWER (fat-tailed world, K=3 still correct):    the Gaussian family's held-out
      density keeps *rising* from K=3 to K=5 (it over-selects), the t family's
      does not, and at the true K=3 the t family scores strictly higher.

Pure-synthetic and deterministic (all seeds fixed inside tails.py); no real
data, so it runs unchanged under CI's hermetic mode.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from kronos.tails import mc_khallucination, gen_world, generic_walkforward
from kronos.regime import GaussianHMM

np.random.seed(0)  # belt-and-suspenders; tails.py seeds everything internally

# ---------------------------------------------------------------------------
# 1. K-hallucination Monte Carlo on two KNOWN-truth worlds (true K=3 in both)
#    Downscaled from the pre-registered (n_seeds=8, T=3000) config to keep the
#    gate < 45s while preserving the effect; Ks=(3,5) isolates the K>3 contrast.
# ---------------------------------------------------------------------------
Ks = (3, 5)
t0 = time.time()
res = mc_khallucination(n_seeds=6, T=1500, train=1000, Ks=Ks, nu_fat=5.0)
mc_secs = time.time() - t0
i3, i5 = Ks.index(3), Ks.index(5)


def curve(world, fam):
    return res[world]["mean_curves"][fam]


def pressure(world, fam):
    """Held-out over-selection pressure: logscore(K=5) - logscore(K=3).
    Positive => the family's predictive density is *improved* by adding
    spurious states, i.e. it is drawn to hallucinate K>3."""
    c = curve(world, fam)
    return c[i5] - c[i3]


# differential hallucination detector: how much MORE the Gaussian family is
# pulled toward K>3 than the t family. ~0 means "no excess kurtosis to fake".
def detector(world):
    return pressure(world, "gauss") - pressure(world, "t")


for w in ("gaussian_world", "fat_world"):
    print(f"{w:15s} pressure(K5-K3): gauss {pressure(w,'gauss'):+.4f}  "
          f"t {pressure(w,'t'):+.4f}  | detector {detector(w):+.4f}  "
          f"| frac_overfit gauss={res[w]['frac_overfit']['gauss']:.2f} "
          f"t={res[w]['frac_overfit']['t']:.2f}")
print(f"K3 held-out logscore  fat: t {curve('fat_world','t')[i3]:.4f} vs "
      f"gauss {curve('fat_world','gauss')[i3]:.4f}  | "
      f"gauss-world: t {curve('gaussian_world','t')[i3]:.4f} vs "
      f"gauss {curve('gaussian_world','gauss')[i3]:.4f}")
print(f"[mc_khallucination ran in {mc_secs:.1f}s]")

# --- POWER: on the fat world the Gaussian family over-selects K>3 ----------------
assert pressure("fat_world", "gauss") > 0.006, \
    "Gaussian family should be rewarded for K>3 on a fat-tailed world"
# --- CURE: the t family is NOT (it models kurtosis within states) ----------------
assert pressure("fat_world", "t") < 0.004, \
    "t family should not need extra states on a fat-tailed world"
assert pressure("fat_world", "gauss") - pressure("fat_world", "t") > 0.008, \
    "Gaussian must be pulled to K>3 far more than the t family on fat tails"

# --- SIZE: on the genuinely Gaussian K=3 world the detector does NOT fire --------
assert abs(detector("gaussian_world")) < 0.005, \
    "families must behave the same when K=3 is genuinely correct (no false positive)"
assert detector("fat_world") - detector("gaussian_world") > 0.008, \
    "hallucination detector must separate the fat world from the Gaussian world"

# --- GROUND-TRUTH RECOVERY at the true K=3 --------------------------------------
assert curve("fat_world", "t")[i3] - curve("fat_world", "gauss")[i3] > 0.008, \
    "at true K=3 the t family must beat Gaussian on fat-tailed data"
assert abs(curve("gaussian_world", "t")[i3]
           - curve("gaussian_world", "gauss")[i3]) < 0.006, \
    "on Gaussian data the t family must tie Gaussian at K=3 (no free lunch)"

# --- argmax view (what mc_khallucination reports): the Gaussian family picks -----
#     K>3 more often on the fat world than when K=3 is genuinely correct ----------
assert (res["fat_world"]["frac_overfit"]["gauss"]
        > res["gaussian_world"]["frac_overfit"]["gauss"]), \
    "Gaussian family must over-select K>3 more often on the fat world"

# ---------------------------------------------------------------------------
# 2. generic_walkforward: the causal predictive-density driver must be strictly
#    out-of-sample (masked before min_train) and produce finite log-densities.
# ---------------------------------------------------------------------------
Xg = gen_world(1200, nu=None, seed=7)
min_train, refit_every = 600, 200


def mk_gauss(first):
    return GaussianHMM(3, 150 if first else 25, 1e-6, 42)


pred_ld = generic_walkforward(mk_gauss, Xg, min_train, refit_every)
filled = pred_ld[~np.isnan(pred_ld)]
first_filled = int(np.argmax(~np.isnan(pred_ld)))
print(f"generic_walkforward: first causal density at t={first_filled} "
      f"(min_train={min_train}), {filled.size} finite densities, "
      f"mean logscore {filled.mean():.4f}")
assert np.all(np.isnan(pred_ld[:min_train])), \
    "walk-forward leaked: densities exist before min_train"
assert first_filled == min_train, "first predictive density not at min_train"
assert filled.size == len(Xg) - min_train, "unexpected gaps in the causal path"
assert np.all(np.isfinite(filled)), "walk-forward produced non-finite densities"

print("\nGATE X25 PASSED")
