# KRONOS-CLOCK — Is Systemic Risk Just Correlated Clocks?

*Pre-registered before running. Follows DESIGN4's One-Clock result (L1): each
asset's vol path explains its own tails. The open question: does it explain
JOINT tails? Raw returns crash together more than any Gaussian copula allows
(Longin-Solnik asymmetry). Two hypotheses fight:*

- **Correlated-clocks view:** joint crashes are simultaneous clock
  accelerations; conditional on the clocks, dependence is plain Gaussian.
- **Contagion view:** there is a genuine common-crash component (joint
  jumps) that survives deformation.

## Screens

### C1 — Does multifractality survive deformation? (the L3 control)
lambda^2 of vol-deformed returns vs raw returns, all assets. Multifractal
cascades ARE vol-clustering structure, so the one-clock view predicts
lambda^2(z) ≈ 0; surviving lambda^2 would mean intermittency beyond the
daily clock. Also adjudicates the "spurious multifractality from fat tails"
debate on our data.
- Verdict metric: median lambda^2(z) / median lambda^2(raw).

### C2 — Joint tail dependence: raw vs deformed vs Gaussian null  (HEADLINE)
For all 1,128 pairs: empirical lower/upper tail-dependence
lambda_L(q) = P(y ≤ F_y^-1(q) | x ≤ F_x^-1(q)) at q = 5%, 2.5%, and lower-vs-
upper exceedance-correlation asymmetry. Benchmark: simulated bivariate
Gaussian null with the SAME correlation and length (rho-binned lookup table,
so every pair gets a finite-sample band, not an asymptotic formula).
- **P-C2a:** raw returns exceed the Gaussian null in the lower tail (known
  stylized fact; sanity check of the machinery's power).
- **P-C2b (the question):** deformed returns' lower-tail dependence falls
  to / stays above the null. Pre-registered metric: median excess lower-tail
  dependence over the null, raw vs deformed, plus the fraction of pairs
  above their null 95% band.
- **P-C2c:** lower-vs-upper asymmetry of deformed returns (Gaussian copula
  is symmetric; surviving asymmetry = directional contagion).

### C3 — How common is the clock?
- Correlation matrix of log-vol innovations (changes of log GK vol):
  top-eigenvalue share = "one market clock" strength.
- Deform every asset by the MARKET clock only (z_i = r_i / sigma_SPY):
  how much of each asset's kurtosis does the common clock alone remove?
  Share by asset class (equities vs bonds vs gold).

## Gates before real data (test_clock.py)
1. Gaussian-copula SV world (correlated clocks, no joint jumps): the
   machinery must show raw returns ABOVE the null (clock correlation creates
   apparent tail dependence) and deformed returns INSIDE the null band —
   i.e., the test can exonerate.
2. Joint-jump world (same + common crash shocks): deformed returns must
   REMAIN above the null — the test can convict; deformation must not
   destroy evidence of true contagion.
3. lambda^2 control on an SV world: lambda^2(z) << lambda^2(raw).

## Verdict thresholds (pre-registered)
- "Clocks explain systemic tails" if the fraction of pairs above their 95%
  null band drops from >50% (raw) to <15% (deformed) at q=5%.
- "Contagion survives" if >30% of pairs stay above the band after
  deformation, or deformed asymmetry remains significant.
- In between: partial — quantify the share of joint-tail risk attributable
  to clocks (the number itself is the contribution).
