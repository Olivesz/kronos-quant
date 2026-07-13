# KRONOS-SURGE — The Structure of Common Volatility Surprises

*Pre-registered before running. CLOCK's verdict: joint crashes are common,
unpredictable clock surges. This program interrogates the surge itself.*

## S1 — Does the clock have a clock? (the cascade question)
Level 0: returns are fat (kurt ~12.6) until deformed by the vol clock (L1).
Level 1: are the clock's own innovations fat and clustered? Measure weekly
log-vol innovations u (non-overlapping 5d means of log GK vol, differenced —
weekly because daily innovations are proxy-noise-dominated, a lesson from
L2/C3). Test: kurtosis of u; autocorrelation of |u| (vol-of-vol clustering).
Level 2: standardize u by an EWMA meta-clock of |u|; does kurtosis fall to
~3? If yes: the one-clock law is RECURSIVE — a two-level cascade suffices.
If level-2 residuals stay fat: turtles all the way down (true multilevel
cascade a la Mandelbrot/Bacry-Muzy).
- Verdicts: kurt(u) > 4 and AC(|u|) significant = "the clock has a clock";
  kurt after meta-deformation < 3.5 = "two levels suffice".

## S2 — Time-reversal asymmetry (the Zumbach effect)
Financial time has an arrow: past squared returns predict future vol MORE
than past vol predicts future squared returns. Statistic:
  Z = sum_{tau=1..20} [ corr(r²_t, v_{t+tau}) - corr(v_t, r²_{t+tau}) ]
with v = 5d-smoothed GK variance; stationary-bootstrap CI per asset.
Also the leverage kernel L(tau) = corr(r_t, v_{t+tau}), tau = 1..60:
sign, decay, and cross-asset universality.
- **P-S2a:** Z > 0 with CI excluding 0 for the majority of assets
  (the arrow of time is universal, not an index artifact).
- **P-S2b:** Z survives vol-deformation of the returns (the asymmetry lives
  in the return->clock coupling, not in the marginals).
- **P-S2c:** equities show L(tau) < 0 (leverage); does GLD show the
  opposite sign (inverse leverage of safe havens)? Asset-class structure.
- Gates: GJR-GARCH world (built-in leverage) => estimator finds Z > 0;
  time-reversible SV world (vol path independent of returns) => Z ≈ 0
  (size). Both before real data.

## S3 — Is surge risk forecastable in INTENSITY? (auditing our own verdict)
CLOCK said joint crashes are unpredictable from yesterday. But that tested
the conditional MEAN. If vol-of-vol clusters (S1), the conditional
INTENSITY is predictable: P(joint-tail day in next 21d) should rise with
the meta-clock level.
Define: joint-tail day = >=25% of assets below their own trailing 5%
quantile. Meta-clock = EWMA(|u|) of the market clock, known at t-1.
Measure: frequency of joint-tail days in (t, t+21] by meta-clock tercile;
lift = tercile3 / tercile1, stationary-bootstrap CI.
- **P-S3:** lift > 1.5 with CI excluding 1 => surge risk IS forecastable in
  intensity, and the CLOCK verdict gets amended to: "unpredictable in
  direction, predictable in intensity."
- Gate: world with regime-switching vol-of-vol => lift detected; world with
  constant vol-of-vol => lift ≈ 1 (size check).

## Outputs
research/surge.json; dashboard panel + verdict cards; README updates;
gates in tests/test_surge.py wired into run_all.
