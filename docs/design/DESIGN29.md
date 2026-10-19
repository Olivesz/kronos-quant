# DESIGN29 — KRONOS-VOLALPHA: does the shipped overlay earn alpha on a century of survivorship-free factors?

*Pre-registered 2026-10-19. Written before any file used here was downloaded,
before KRONOS read any pre-2013 factor return, and before any code for it.
DESIGN28 stays registered and sealed and is not run here.*

## Question

Does KRONOS's shipped volatility-targeting overlay earn alpha net of the
Fama-French five factors, momentum and betting-against-beta? The test assets
are survivorship-free market and factor portfolios from 1926 on.

The shipped overlay has five parts:
- the HAR forecast-vol lever (`vol_target` 0.13, `max_exposure` 1.5);
- the CVaR brake (`cvar_target` 0.018 daily);
- the drawdown brake (−8% to −20%, floor 0.25);
- 5-day smoothing;
- the ±15% tilt on the sign of 21-day momentum.

The overlay is a timing rule applied at the portfolio level. The right test
assets are therefore long, survivorship-free portfolio returns, not single
names. Ken French builds them from CRSP and publishes them from 1926. They
replace the 48 hindsight-picked names entirely.

**Prior.** The odds that the overlay EARNS ALPHA under the rule below are
about 20%. Moreira & Muir find a market alpha with a full-sample constant.
Cederburg et al. find no real-time Sharpe gain on the market. Liu, Tang &
Zhou report deep drawdowns once the look-ahead is removed. The overlay is
capped and braked, which lowers both its alpha and its risk.

## Data

All sources are public and need no login.

| File | Source | Use |
|---|---|---|
| `F-F_Research_Data_Factors_daily_CSV.zip`, `F-F_Research_Data_Factors_CSV.zip` | Ken French library | Mkt−RF, SMB, HML, RF; daily from 1926-07 |
| `F-F_Research_Data_5_Factors_2x3_daily_CSV.zip`, `F-F_Research_Data_5_Factors_2x3_CSV.zip` | Ken French library | RMW, CMA; from 1963-07 |
| `F-F_Momentum_Factor_daily_CSV.zip`, `F-F_Momentum_Factor_CSV.zip` | Ken French library | UMD (French's "Mom") |
| `Betting-Against-Beta-Equity-Factors-Daily.xlsx` | AQR data library | BAB, USA column |
| `VIX_History.csv` | Cboe | descriptive only: VIX against the HAR forecast, 1990 on. Not used in any test |
| DTB3 (`data/dtb3.csv`, already committed, from 1954) | FRED | robustness only: financing at the 3-month bill |

**Archive and verification.**
- Every file is fetched once, after this registration is committed.
- Files are stored in `data/vendor/`, which is git-ignored. The owner decides
  separately whether third-party files may be redistributed.
- `data/vendor/MANIFEST.json` is committed. It records each file's URL,
  retrieval timestamp (UTC), byte size and SHA-256.
- Loaders verify the hash before parsing and fail closed on any mismatch.
- **French revises history.** The manifest, not the URL, therefore defines the
  data. Anyone reproducing either obtains the same bytes or sees the mismatch.

**Parsing.** CSVs are parsed with `float_precision="round_trip"`.

**Sources ruled out.**
- ALFRED: it adds nothing for T-bill rates, which are never revised, so it is
  not fetched.
- No Yahoo data, no single names, no hindsight universe.

**Financing.** French's RF is a T-bill rate, and the factors are already
excess returns over it. Holding exposure e in Mkt−RF is therefore the same
as holding e in the market and 1 − e in bills, or borrowing e − 1 at the bill
rate. Leverage is thus financed at the T-bill rate exactly.

**Monthly returns of a daily-rebalanced position.** A position with daily
exposure e_t, collateralized or financed at RF, has monthly excess return

R = Π(1 + e_t f_t + rf_t) − Π(1 + rf_t), compounded over the month's trading days.

The unmanaged factor uses e_t ≡ 1. Stage 2 uses this for both sides of every
comparison, so there is no mixing of French's monthly files with
daily-compounded returns.

**Saturday sessions (Stage 2 only).** The NYSE traded Saturdays until 1952.
The overlay's windows (1, 5, 22 and 252 observations) and its √252 scaling
assume weekday sessions. Before Stage 2, each Saturday return is therefore
compounded into the next observation. A Monday then spans Friday's close to
Monday's close, as it does today. Stage 1 uses French's daily files
unchanged, as the replicated papers did.

## Windows and the seal

| Window | Span | Role |
|---|---|---|
| Holdout | 1926-07 .. 2012-12 | Sealed. KRONOS's overlay was designed on 2013–2026 and has never run on these years. |
| Full-model holdout | 1963-07 .. 2012-12 | The span where all seven regressors exist |
| Contaminated | 2013-01 .. latest | Reported descriptively; never used in a decision |

**Seal.** The order is fixed:
1. The replication gate (Stage 1) runs first, on published strategies only.
2. A seal amendment is then committed. It records the SHA-256 of `config.py`,
   `run_research.py` and `kronos/*.py` (the `code_digest` convention), of the
   Stage-2 test file, and of `MANIFEST.json`.
3. Only then does the overlay touch any pre-2013 return.
4. The reveal runs that exact code once.

## Stage 1 — replication gate (published strategies, not KRONOS's)

Stage 1 runs on the archived French vintage and matches each paper's sample.
The tolerances below are fixed now. They allow for French's revisions since
the papers were written.

**Common construction.** The managed factor is

f^σ_t = (c / RV²_{t−1}) f_t,

where:
- RV²_{t−1} is the demeaned sum of squared daily factor returns in month t−1;
- f_t is French's monthly return;
- the full-sample c sets std(f^σ) = std(f).

**R-MM: Moreira & Muir, NBER WP 22208, Table 1 Panel A.** Spanning
regression f^σ = α + βf + ε, monthly, with α ×12 and heteroscedasticity-robust
(White) SEs. Samples:
- Mkt, SMB and HML: 1926-08 .. 2015-12.
- Mom: from 1927-01, French's momentum start.
- RMW and CMA: from 1963-07.

| Factor | Published α (SE) | β | Tolerance |
|---|---|---|---|
| Mkt | 4.86 (1.56) | 0.61 | \|Δα\| ≤ 0.75·SE and \|Δβ\| ≤ 0.06 |
| Mom | 12.51 (1.71) | 0.47 | \|Δα\| ≤ 0.75·SE and \|Δβ\| ≤ 0.06 |
| SMB | −0.58 (0.91) | 0.62 | \|Δα\| ≤ 1·SE |
| HML | 1.97 (1.02) | 0.57 | \|Δα\| ≤ 1·SE |
| RMW | 2.44 (0.83) | 0.62 | \|Δα\| ≤ 1·SE |
| CMA | 0.38 (0.67) | 0.68 | \|Δα\| ≤ 1·SE |

**R-COWY: Cederburg, O'Doherty, Wang & Yan (2020, JFE 138:95–117), authors'
copy.** Samples end 2016-12 and start as in R-MM. All Sharpe ratios are
annualized.

*Table 1 (in sample):*
- Mkt managed SR 0.51 against original 0.42, a difference of +0.09.
- Mom difference +0.50.
- Tolerance: each figure within ±0.05, except the Mom difference, within ±0.08.

*Table 5 (real time):*
- Training starts with K = 120 months and the window then expands.
- At the start of each out-of-sample month, c_t matches the variances of f^σ
  and f over the training window.
- (x^σ_t, x_t) = Σ̂_t⁻¹ μ̂_t / γ, with γ = 5.
- The position is y_t = x^σ_t c_t / RV²_{t−1} + x_t, clipped to |y_t| ≤ 5.
- The original-only strategy is x_t = μ̂_t / (γ σ̂²_t), clipped the same way.

Published Mkt figures: combination SR 0.42 against original 0.46, a
difference of −0.04.

Tolerances:
- each SR within ±0.06;
- the difference within ±0.06 and ≤ 0.

**R-LTZ: Liu, Tang & Zhou (2019, JPM 46(1):38–51).** The full text is not
accessible here (SSRN returns 403; the journal is paywalled). Their point is
the look-ahead in the full-sample c. It is reproduced directly:
- Construction: the Mkt strategy with real-time c_t (expanding window from
  K = 120 months).
- Reported beside the full-sample version: alpha, Sharpe and maximum
  drawdown.

Only the abstract's claim is registered, and it is descriptive, not gating:
maximum drawdowns of about 68–93% once the constant is real-time. A real-time
Mkt maximum drawdown outside 60–95% is flagged as a discrepancy.

**Gate rule.** PASS iff all three hold:
- Mkt and Mom pass R-MM;
- at least 3 of the other 4 R-MM factors pass;
- all three R-COWY Mkt checks pass.

**If the gate fails, the program stops.** The report names the failed check,
and nothing in Stage 2 runs.

## Stage 2 — the test (the reveal)

**Primary: the overlay on Mkt, exactly as shipped.**
- The overlay is `kronos.risk.exposure_series` with the shipped `CFG`
  (`lever_mode` "har").
- Its estimators read the market's total daily return, Mkt−RF + RF. This is
  what the shipped book's estimators read: a total-return book, not an excess
  return.
- The tilt is sign(Σ₂₁ log(1 + Mkt−RF + RF)).
- Exposure decided at close t applies to t+1. The managed excess return is
  e_{t−1} · (Mkt−RF)_t.
- The first 252 observations are overlay warmup, mirroring the shipped
  backtest. The evaluation therefore starts 1927-07 or later.

One property of the shipped rule is known in advance and registered here: the
drawdown brake reads the market's own high-water mark. After 1929 it
therefore holds near its 0.25 floor until that mark is regained.

**Family: SMB, HML, RMW, CMA, UMD and BAB.** The shipped thresholds are
denominated in the shipped book's volatility. Applied raw, a 13% target would
pin the lever at its cap for these lower-vol factors.

The overlay therefore runs on each factor expressed in shipped units:
- f̃_t = f_t · 0.13 / σ̂_{t−1}.
- σ̂ is the factor's trailing realized volatility over 2,520 observations,
  expanding from a 252-observation minimum, annualized by √252. It is causal.
- The tilt reads sign(Σ₂₁ log(1 + f̃)).
- The managed return is e_{t−1} · f̃_t. Its gross exposure to f is
  e · 0.13 / σ̂.

This slow normalization is part of the registered rule and is disclosed as
such. No alternative is tried.

**Regressions.** All are monthly, with Newey-West SEs at 12 lags and α ×12.
1. Univariate spanning, f^overlay = α + βf + ε, from each factor's first
   evaluation month to 2012-12.
2. Full model: each managed factor regressed on Mkt, SMB, HML, RMW, CMA, UMD
   and BAB, 1963-07 .. 2012-12. The managed factor's own unmanaged version is
   one of the seven.

**Inference.**
- **Sharpe difference.** Ledoit & Wolf (2008) HAC-studentized circular block
  bootstrap of SR(managed) − SR(unmanaged): block of 12 months, 5,000
  resamples, seed 42, one-sided. For Mkt it runs over the full holdout after
  warmup; for each family factor, over its own span.
- **Romano-Wolf** studentized stepdown across the seven full-model alphas, at
  5% family-wise.
- **Hansen (2005) SPA.** H0: no managed factor has a positive full-model
  alpha. It uses the seven hedged series f^overlay − β̂′X, with a stationary
  bootstrap (mean block 12 months, 5,000 resamples, seed 42).
- **DSR** on the primary at cumulative N (below), using excess returns.
- **PBO** by CSCV over the 8-member Mkt grid below: S = 16 blocks over the Mkt
  holdout, monthly Sharpe. The repo's PBO of 0.45 is restated beside every
  Sharpe, per house rule.
- **Stability.**
  - Univariate Mkt alphas in four eras: 1927-07 .. 1945, 1946 .. 1962,
    1963 .. 1987 and 1988 .. 2012. They are univariate because the full model
    does not exist before 1963.
  - An Andrews (1993) sup-Wald break test, 15% trimming, on the primary's
    univariate alpha.

**Robustness (reported, never decisive).**
- Primary financed at DTB3 instead of RF from 1954 on. The spread
  (DTB3 − RF) is charged on (e − 1)⁺.
- The contaminated window, 2013 .. latest.

**Decision rule.** The overlay **EARNS ALPHA** iff all four hold for the
primary:
1. Full-model α > 0 with Newey-West t ≥ 3.0 (the Harvey-Liu-Zhu hurdle).
2. Ledoit-Wolf one-sided p < 0.05 for the Sharpe gain.
3. The full-model alpha survives Romano-Wolf at 5%.
4. Univariate α > 0 in at least 3 of the 4 eras.

Otherwise the verdict is **NO ALPHA SURVIVES**, stated as such. Family results
are reported with their Romano-Wolf-adjusted p-values however they land.

## Stage 3 — costs

**Breakeven.** The breakeven cost is the one-way cost per unit of exposure
turnover: annual α ÷ annual Σ|Δe|, in bp. It is reported for the primary.

It is compared with two figures:
- **The E-mini S&P 500 half-tick.** The contract's minimum price fluctuation
  is cited from CME when fetched. It is expressed in bp of the index level on
  the measurement date.
- **SPY's effective spread from IEX HIST trade messages**, 2·|p − m|/m against
  IEX's own top of book, labeled "one venue".

**IEX blocker.** The IEX measurement is blocked until the owner accepts the
IEX Historical Data Terms of Use. Downloading means agreeing to them, and
that is the owner's decision. Raw pcaps stay outside the repo; only their
hashes and aggregates are committed.

**What TAQ would change.** TAQ is not on UT's WRDS list. It would replace the
one-venue spread with a consolidated, all-venue effective spread against the
NBBO. It would also allow an impact calibration for the overlay's trade sizes
instead of a breakeven figure. Without it, Stage 3 claims only a comparison
of the breakeven against the two figures above.

## Stage 4 — external checks (owner actions)

- **S&P 500 Daily Risk Control index levels** (e.g. the 10% variant), if the
  owner can export them by hand. The check is the correlation of daily
  returns, and the tracking error, against the overlay on Mkt over the
  index's history.
- **An Alpaca paper account the owner creates.** Its key goes in an
  environment variable he sets. The account trades the overlay on SPY daily,
  so every order and fill carries a third-party timestamp.

## Trial accounting

The replications are of published strategies, so they charge nothing.

Stage 2 charges 14 entries (`design29_volalpha`). The cumulative count goes
from N = 188 to 202, and the primary's DSR is computed at N = 202.
- The 8-member Mkt grid: tilt ∈ {0, 0.15} × `max_exposure` ∈ {1.0, 1.5} ×
  brakes {on, off}. "Off" sets `cvar_target` = ∞ and `dd_start` = −∞. The
  primary is the (0.15, 1.5, on) member, fixed now.
- The six family factors.

DESIGN28's 23 books are charged only if it runs.

## Reporting

- `research/volalpha_replication.json`: Stage 1.
- `research/volalpha.json`: Stages 2–3.

Each artifact carries `input_digest`, the SHA-256 of `MANIFEST.json`, and
`code_digest`.

FINDINGS gains KRONOS-VOLALPHA, and the verdict is stated as which claim
survives. A working paper (Stage 5) is written only after the verdict. It is
written for review by a McCombs finance professor and for posting on SSRN.

## Not claimed, whatever the result

- Nothing about single-name books: stock-level CRSP is not available. It
  would allow the overlay on a point-in-time version of the shipped 1/N book
  itself, rather than on factor proxies.
- Nothing about all-venue trading costs: there is no TAQ.
- Nothing about Liu, Tang & Zhou beyond their abstract.
