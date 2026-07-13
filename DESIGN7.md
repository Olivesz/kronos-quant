# KRONOS-BITS — The Information Budget of the Market

*Pre-registered. The question every quant career orbits: how many bits per
day does the past leak about the future — and therefore what is the maximum
Sharpe ANY strategy could achieve from public price history?*

## The theory chain (what makes bits → Sharpe rigorous)
- Kelly (1956): maximum expected log-growth edge from side information
  equals the mutual information I(signal; outcome).
- Gaussian channel: if the predictable part is Gaussian,
  I = 0.5*ln(1 + SNR) with SNR = SR_daily^2, so
  **SR_daily_max = sqrt(exp(2*I_nats) - 1)**, SR_ann = sqrt(252)*that.
- Binary direction channel: I_bits = 1 - H2(p) where p = max achievable
  hit rate; invert for p, then SR_ann ≈ (2p-1)*sqrt(252) for a unit-vol
  sign bet.
These give ceiling translations for the two budget components we measure.

## What we measure (all causal, all on real data)
- **Direction bits/day**: I( sign(r_{t+1}) ; F_t ) with F_t = discretized
  causal features (yesterday's sign, momentum sign, vol tercile, regime).
  Discrete plug-in MI + Miller-Madow bias correction − shuffle-null
  subtraction (the shuffle estimates residual bias under independence).
- **Magnitude bits/day**: I( log v_{t+1} ; F_t ) with v = next-day GK
  variance, F_t = (log vol level, vol change) — the vol-predictability
  budget. KSG k-NN estimator on rank-transformed data (MI is invariant
  under monotone transforms; ranking tames the heavy tails).
- **Total return bits**: I( r_{t+1} ; [r_t, log vol_t] ) via KSG, rank
  transformed.
- Horizons h = 1, 5, 21; eras pre/post 2018-01-01; SPY + cross-asset
  median.
- **Budget utilization**: KRONOS's realized daily Sharpe implies bits
  consumed = 0.5*ln(1 + SR_daily^2); compare with the measured budget.

## Pre-registered hypotheses
- **B1**: direction bits are indistinguishable from the shuffle null at
  h=1 for the median asset (the sign channel is ~closed: < 0.002 bits/day
  after bias subtraction). Any robust positive finding would be huge.
- **B2**: magnitude bits >> direction bits (factor > 50): the market's
  leak is almost entirely about its own volatility — consistent with the
  whole LAWS/CLOCK arc.
- **B3**: the implied direction-Sharpe ceiling at h=1 is below ~1.0
  annualized net of nothing (i.e., even the CEILING is modest); the vol
  channel's ceiling is far higher but only monetizable via vol-sensitive
  instruments (which we note honestly).
- **B4**: magnitude bits are era-stable (the clock's predictability is a
  market constant); any direction bits are era-fragile.

## Gates before real data (test_infobudget.py)
1. KSG on bivariate Gaussian recovers I = -0.5*ln(1-rho^2) within 0.01
   nats for rho in {0.1, 0.5, 0.9}, N=4000.
2. KSG on AR(1) (x_t vs x_{t+1}) recovers the closed form.
3. Discrete MI + Miller-Madow on a binary channel with known I; shuffle
   null ≈ 0 within tolerance on independent data.
4. SV world: direction bits ≈ 0 (size), magnitude bits ≈ the closed-form
   AR(1) MI of its log-vol attenuated by proxy noise (power + realism).
5. A planted-signal world (small genuine sign predictability): the
   pipeline detects it above the shuffle null (the test can convict).

## Deliverable
The budget table on the dashboard: bits/day by channel × horizon × era,
implied Sharpe ceilings, and KRONOS's utilization percentage.
