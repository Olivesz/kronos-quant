# KRONOS-X² — "Regimes or Fat Tails?" + "Does Roughness Forecast?"

*Pre-registered protocol, written before the experiments run. Two studies that
upgrade our two best findings from observations to mechanism tests.*

---

## Study 1: Do markets have >3 regimes, or do Gaussian HMMs hallucinate regimes from fat tails?

### Background (what our data showed)
Walk-forward predictive log-score of Gaussian-HMMs rises monotonically with K
(2→5: 3.110, 3.169, 3.171, 3.189) while the Statistical Jump Model peaks at
K=3. Hypothesis: the extra Gaussian states are fitting the *conditional
return distribution's tails*, not recurring economic states.

### The control: Student-t HMM
HMM with multivariate Student-t emissions — fat tails *inside* each state, so
extra states are no longer needed to fake kurtosis. Implementation: ECM.
E-step carries both state responsibilities (forward-backward) and latent
gamma scale weights u_tk = (nu_k + d)/(nu_k + delta_tk); M-step uses
gamma*u-weighted means, gamma*u-weighted scatter normalized by sum(gamma)
(Kent-Tyler-Vardi), and per-state nu_k solved from the standard digamma
equation by Brent's method on [2.1, 200].

### Pre-registered hypotheses
- **H1 (mechanism, synthetic):** On data simulated from a t-HMM with K=3,
  nu=5: Gaussian-HMM model selection (held-out predictive log-score) chooses
  K>3 in the majority of seeds; t-HMM selection concentrates on K=3.
- **H2 (placebo, synthetic):** On data from a Gaussian-HMM with K=3, both
  families choose K=3 (no false hallucination signal).
- **H3 (real data):** The t-HMM's walk-forward log-score curve in K is flat
  or peaks at K<=3, while the Gaussian curve rises; AND t-HMM-3 >= Gaussian-5
  in log-score. If instead t-HMM also improves through K=5, the market
  genuinely has more than 3 conditional states and my fat-tails story is
  wrong. Either outcome is a finding.

### Inference (the rigor upgrade)
- **Amisano-Giacomini (2007)** unconditional test on daily log-score
  differentials (HAC/Newey-West variance, lag 10) for the key pairwise
  comparisons: t3 vs g3, t3 vs g5, g5 vs g3, t3 vs SJM3.
- **Hansen-Lunde-Nason Model Confidence Set** (alpha = 0.10, Tmax statistic,
  stationary bootstrap B=1000, mean block 63d) over the model universe
  {Gaussian K=2..5, t K=2..5, SJM-3, DurHMM-3x3}. Deliverable: the MCS —
  the set of regime models statistically indistinguishable from the best.

### Protocol details (identical to the v2 horse race)
Features (GK log-vol + market return), expanding walk-forward, min 750 obs,
refit 21d, warm starts, eval = 2019-01-01 onward, one-step-ahead return
marginal density. Monte Carlo: 8 seeds per world, T=3000 (2000 train / 1000
test, single fit per K — matches the selection problem practitioners face).

### Verification gates before real data
- t-HMM on synthetic t data: recovers nu within +/-1.5 (nu=5), transition
  diag within 0.03, beats Gaussian HMM log-score on t world, ties on
  Gaussian world (within 0.005 nats/day).
- AG test: correct size on equal-skill forecasters (p uniform-ish, 5% level
  rejects ~5%), power on distinct ones.
- MCS: on synthetic losses with 3 equal-best + 3 inferior models, keeps the
  good 3 (coverage >= 85% across seeds), eliminates the bad 3.

---

## Study 2: Does roughness forecast? (RFSV predictor vs HAR)

### The forecaster
Gatheral-Jaisson-Rosenbaum RFSV prediction: log v_hat(t+Delta) =
conditional expectation of fBm given its past = kernel-weighted history with
weights w_s ∝ 1 / ((s+Delta) * s^(H+1/2)), truncated at 500 days,
normalized; H re-estimated walk-forward (causal); per-window OLS calibration
log v_{t+1} = a + b * y_hat (absorbs truncation bias and the lognormal
variance correction via +0.5*resid-var in the exp transform).

### Pre-registered hypotheses
- **H4 (mechanism, synthetic):** On simulated RFSV data (fBm log-vol,
  H=0.10, gamma measurement noise), RFSV-forecast beats HAR on QLIKE
  (it is the true model — if it can't win here, the implementation is wrong).
- **H5 (real data):** On SPY GK variance, RFSV is at least competitive with
  HAR (AG/DM |t| < 2 means "tie"). HAR is a brutal benchmark — published
  results suggest rough forecasters roughly match HAR at daily horizons, so
  a tie *with H estimated at 0.1* is itself confirmatory of the rough view;
  a HAR win is a counter-data-point worth reporting; an RFSV win would be
  noteworthy.
- Add RFSV to the vol-lab MCS: {EWMA, HAR, GARCH, RFSV}.

### Gate
On RFSV-simulated world with known H: forecaster beats HAR on QLIKE.
On GARCH world: RFSV within 10% of HAR QLIKE (graceful misspecification).

---

## Outputs
- `research/tails.json` — MC tables, real-data K-curves for both families,
  AG matrix, regime-model MCS.
- `research/rfsv.json` — vol-lab v2 with RFSV, AG tests, vol-model MCS.
- Two new verdict cards + two panels on the dashboard RESEARCH tab.
- README findings table updated. All gates added to tests/run_all.py.
