# DESIGN28 — KRONOS-PREMIA: a survivorship-free, out-of-era test of what KRONOS can honestly claim

*Pre-registered 2026-10-13, before any code for it and before any 1995–2009
data has been loaded by KRONOS. Program chosen by a five-architect,
three-judge design panel (allocator, statistician, engineer lenses); the four
programs not registered are listed in Appendix A and charged nothing unless
later registered.*

### Decision record

Registered 2026-10-13. The owner asked for a materially better system after
DESIGN27 ("not even close to where we want to be"); the oversight session,
which decides in the owner's place, accepted this program and its framing on
the same day:

- **This program produces a number a skeptical reviewer will believe, not a
  bigger number.** Expected headline: excess-over-cash Sharpe of about 0.6–0.75
  pooled over 1995–2026 and about 0.5–0.8 on 2013–2026.
- **Today's headline is a different object**: it was measured on a
  hindsight-picked universe.
- **Odds:** the registered WIN has a prior of about 15%; the modal outcome is
  FAILURE.
- **The README headline does not change until this program's verdict lands,
  and then changes whatever the verdict is**, with WIN or FAILURE stated (see
  Shipping and headline rule). The shipped book stays the control until then.

### Context

**What is shipped.** C1 (DESIGN27, shipped by owner decision): 1/N over 48 names, the HAR lever up to 1.5×, CVaR/DD brakes, a ±15% tilt on 21-day SPY momentum, and the pairs sleeve. On 2013-01-14..2026-06-04 it shows Sharpe 1.12 at rf=0 and 0.97 excess over cash, CAGR +13.6% and MaxDD −18.7% (after the two fixes below). DSR is 0.83 at N=188 and PBO is 0.45. DESIGN27 FAILED its registered bar: equal-weight raw scored 0.98 excess.

**Defects found while writing this file, each verified in code:**

1. **Universe.** 36 of the 48 tickers in the pinned panel are large caps chosen in 2026; the panel is 36 stocks plus 12 ETFs, with META excluded on coverage.
2. **Cash accrual — FIXED 2026-10-13 before registration (gate X38c).** `dtb3_daily` accrued `DTB3/100/360` per *trading* day, about 70% of the annual bill rate, so every excess Sharpe was overstated (measured: by 0.03–0.05). It now accrues the money-market yield over calendar days at the previous day's rate — algebraically the `d28` cash convention below.
3. **Engine** (`kronos/backtest.py`):
   - (a) Idle capital earns 0: `net = gross·e − costs − financing`.
   - (b) Leverage pays a flat 3.5%/yr, which sat below DTB3 in 2023–25.
   - (c) Daily exposure changes cost nothing, and rebalance costs are not scaled by exposure.
   - (d) `new /= new.sum()` would push gated-out capital back into risky assets.
   - (e) Every backbone zero-padded 762 warmup days and the overlay was fitted on them. FIXED 2026-10-13 before registration (gate X42): the overlay now sees only the book's own returns.

   (a)–(d) are not caught by any gate; gate X43a/h is added for them.

**What the repo licenses** (FINDINGS):
- **Magnitude.** About 0.40 bits/day (BITS). HAR beats EWMA, QLIKE 0.417 vs 0.511 (Q3a). Licensed for book-level forecast vol by X28/EDGE2.
- **Monthly direction.** mom21 is licensed on SPY at h=21 (HARVEST gap 0.0208; MOMTILT +0.02).
- **Daily sign channel.** Closed (0.0007 bits/day).
- **Crashes.** Shocks, not critical transitions (CRITICAL).
- **Leverage effect.** −0.04 in equity, transferring across four markets. About 0 in FX and gold. +0.03 in TLT (TRANSFER, SURGE, FX).
- **Not licensed.** Trend outside SPY, at h=63 or h=252, and per-sleeve HAR weights. All three rest on the literature plus gate X43.

**Programs considered (meta-selection disclosure).** Five candidate programs were drafted. Each was reviewed from three angles: allocator, statistician and engineer. This design combines:
- the highest-scored core: a rule-picked multi-asset ETF book with an untouched pre-2010 holdout;
- one grafted test: the frozen overlay out of era, on SPY;
- the reviews' required fixes.

The four programs not registered are listed in Appendix A. None runs under DESIGN28. Any later run of any of them is a new registration charged to the same ledger. DESIGN28's verdict heads the README.

### Conventions (fixed now)

**Cash, convention `d28`.**
- Convert each DTB3 discount print to a bond-equivalent yield: BEY = 365·d/(360 − 91·d).
- Daily cash return: rf_t = BEY_{t−1}·Δcal_t/365.
  - BEY_{t−1} comes from the latest print dated on or before the previous trading day, which respects the H.15 one-day publication lag.
  - Δcal_t is the number of calendar days since the previous trading day.
- This is what `kronos.metrics.dtb3_daily` already computes since the 2026-10-13 fix: d/(1 − 91d/360) accrued per calendar day over 360 equals BEY·Δcal/365 exactly. No legacy flag is kept; the buggy accrual is not reproduced.

**Accounting, `accounting="d28"`.**
- Idle capital (1−e)⁺ earns rf_t.
- The levered portion (e−1)⁺ pays rf_t + 0.015·Δcal_t/365.
- Rebalance costs are scaled by applied exposure.
- Daily exposure changes cost |Δe|·3bp.
- `accounting="d28"` is opt-in until this program's verdict; the shipped control keeps the current engine on every README surface until then, and is restated under `d28` inside the program (Stage 2) after gate X43a passes.

**Sharpe ratio.**
- ExSR = √252·mean(n−rf)/sd(n−rf), with rf from `d28`.
- Raw rf=0 Sharpe is reported alongside.

**DESIGN27 is never re-scored.** Its rows are restated under `d28` (Stage 3) as non-adjudicating rows only.

**Deflation.**
- DSR is computed on *excess* returns at N=211. SR dispersion comes from two sources:
  - (i) the legacy ledger restated in the excess convention, wherever its series exist;
  - (ii) the 16 DESIGN28 books evaluated on the pooled window.
- The headline is the lower of the two DSRs.
- The legacy rf0 DSR is reported for continuity.
- PBO 0.45 is restated beside every Sharpe as the *sibling-family* number. It is not this book's PBO.

### Hypotheses

**H-AUDIT (measurement; read first).** The 2013–2026 gap between EW-48 and survivorship-free equity is mostly selection.
- Comparison: EW-48 raw against EWcf on 2013-01-14..2026-06-04. EWcf is EW-48 with its 36 single names replaced by RSP at their aggregate weight (36/48).
- Prior: ExSR(EW-48) − ExSR(EWcf) = +0.15 to +0.40, central +0.25.
- Reported whichever way it falls.

**H1 (flagship).** B is an equal-risk blend of P and E (spec below). B beats naive diversification and the index:
- pooled 1995–2026, by at least a margin δ certified on synthetic data;
- without losing to 60/40 after publication (2013–2026);
- beating both 60/40 and SPY in the untouched 1995–2009 era;
- robust to removing any single sleeve of P;
- with a vol-matched drawdown no deeper than 60/40's.

**H2 (components; reported, each with its own kill, none gates H1):**
- **H2a, diversifier.** P beats 60/40 in era A and does not lose to it in era B.
- **H2b, trend gate.** P > A1 in at least 3 of 4 panels: era A, era B, WEBS-17 and SPDR-9.
- **H2c, risk balancing.** P > A2 in at least 3 of 4 panels.
- **H2d, overlay out of era.** In both era A and era B, E beats SPY on ExSR with a vol-matched MaxDD no deeper than 0.85× SPY's.

**Predicted signs (reported, not gating):**
- The trend increment P−A1 comes mostly from 2000–02, 2008 and 2022, and is about zero or negative in calm years.
- Trend does *not* protect in Feb–Mar 2020 (CRITICAL). There, only the cap and the safe-haven sleeves act.
- E's gain over SPY comes from equity vol-timing, as the leverage effect predicts.

### Strategy spec (every parameter fixed)

**Universe U9.** One sleeve per class in a nine-class taxonomy.
- Five classes are Faber (2007)'s: US equity, developed ex-US equity, US 10-year Treasuries, US REITs and commodities.
- Four are added and disclosed as a designer choice: EM equity, long Treasuries, IG credit and gold.
- Instrument rule: the oldest US-listed, unlevered, index-tracking ETF in each class.
- Resulting sleeves: SPY, EFA, EEM, IYR, IEF, TLT, LQD, GLD, DBC.
- DBC and EEM are kept on purpose, although both are known to have been weak after 2013.
- Fragility is gated by R4. The published five-class list is reported as R-F5.

**Pre-listing proxies.** Each is used only before its ETF's first return, then switched hard to the ETF. All are gated by X44; a failing proxy is dropped, never substituted.

| Sleeve | Proxy before listing |
|---|---|
| IEF | IEF*: a daily 10-year constant-maturity par bond priced from FRED DGS10 |
| TLT | TLT*: a 30-year par bond priced from DGS30. DGS30 is chosen over DGS20 on duration match. Per FRED's notes, which must be verified, DGS30 values from 2002-02-18 to 2006-02-09 are Treasury extrapolations; disclosed. |
| EEM | VEIEX |
| IYR | VGSIX |
| EFA | VTMGX |
| LQD, GLD, DBC | No proxy (no index fund existed) |

**Par-bond pricing (Swinkels 2019 method).**
- Return = PV_t/100 − 1.
- PV_t is the value at t of a bond bought at par at t−1: semiannual coupon y_{t−1}, maturity M years from t−1, discounted at y_t, so accrued interest is included.
- Subtract 0.15%·Δcal/365 for expenses.

**Eligibility.** A sleeve is live at t if and only if it has at least 252 valid daily returns, counting its spliced series.

**Sleeve P.** At each sub-book rebalance date t, decided at the close of t and held from t+1:

1. σ̂_i = max(HAR_i, 0.5·σ252_i), where:
   - HAR_i = `risk.har_vol_forecast` on the sleeve's own close-to-close total returns (refit 21, min_train 252, EWMA hl 21 fallback, real history only);
   - σ252_i = the trailing 252-day sample std, annualized.
2. Trend votes v_{i,h} = 1[Π(1+r_i) − Π(1+rf) > 0 over (t−h, t]], for h ∈ {21, 63, 252}. The gate g_i = (v₂₁ + v₆₃ + v₂₅₂)/3 takes values in {0, ⅓, ⅔, 1}.
3. Weights x_i = g_i·(1/σ̂_i) / Σ_live(1/σ̂_j). Cash = 1 − Σx_i is an explicit sleeve earning rf. Weights are never renormalized.
4. **Tranching** (Jegadeesh–Titman 1993):
   - The book is the equal-weight average of 21 sub-books.
   - Sub-book k rebalances on day indices ≡ k (mod 21), counted from 1993-02-01.
   - The no-trade band is 0.0025 of *sub-book* NAV, applied per sub-book.
   - Sub-book weights drift between rebalances, and the cash leg accrues rf.
5. **Book vol cap.**
   - σ̂_book,t = √(252·hᵀ D R D h), where:
     - h is the aggregate drifted risky vector;
     - D = diag(daily σ̂_i);
     - R is the correlation implied by `covariance.shrunk_cov` on the trailing 252 days of live sleeves (halflife 63, window 252).
   - m_t = min(1, 0.10/σ̂_book,t).
   - Exposure e_t = EWMA_span5(m_t), clipped to [0, 1] and applied from t+1.
   - Held weights = e·h. There is no leverage, so no financing. Because the cap never exceeds 1, it cannot re-lever surviving legs.
   - The fraction of days the cap binds is reported. **No magnitude-channel Sharpe is claimed for the cap.**

**Sleeve E.**
- Run `run_backtest` on the universe ["SPY"] with `backbone="ew"`, giving 100% SPY.
- Overlay frozen exactly as in `config.py`:

| Overlay setting | Value |
|---|---|
| `lever_mode` | "har" |
| `vol_target` | 0.13 |
| `max_exposure` | 1.5 |
| CVaR | α 0.95, target 0.018/day |
| DD brake | from −8% down to −20%, floor 0.25 |
| `risk_smooth_days` | 5 |
| `mom_tilt` | 0.15 on the sign of SPY's 21-day log return |
| Pairs sleeve | off |

- `accounting="d28"` with `warmup_mode="backbone"`: for the single-asset backbone the signal lookback warmup is skipped, so the overlay consumes real SPY returns from 1993-02-01 (no zero padding, per the X42 fix), and evaluation starts 1995-01-03.
- The DD brake reads the *gross backbone* high-water mark from 1993-02-01 and never resets. That is the licensed behavior, frozen and disclosed. E_nodd decomposes its effect.

**Flagship B.**
- α_t = (1/σ̂_P) / (1/σ̂_P + 1/σ̂_E). Each σ̂ is `har_vol_forecast` on the sleeve's own daily net-return history, with the 0.5·σ252 floor.
- α is reset every 21 trading days, counted from 1995-01-03, and drifts in between.
- Return: B = α·P + (1−α)·E, minus 3bp × 2|Δα| on reset days.
- Gross notional is at most 1.5.

**Controls and robustness books (charged; none can ship):**
- **A1:** P with g ≡ 1 (inverse-vol, no trend).
- **A2:** P with x_i = g_i/N_live (1/N capital with the trend gate, Faber's analogue).
- **E_nodd:** E with m_dd ≡ 1.
- **B₋ᵢ (×9):** B built on P with sleeve i removed.
- **R-F5:** the P rule on Faber's five classes verbatim (SPY, EFA, IEF, IYR, DBC).
- **Transfer panels:** the P, A1 and A2 rules on:
  - **WEBS-17:** the complete March-1996 launch batch (EWA EWC EWD EWG EWH EWI EWJ EWK EWL EWM EWN EWO EWP EWQ EWS EWU EWW);
  - **SPDR-9:** the complete December-1998 batch (XLB XLE XLF XLI XLK XLP XLU XLV XLY; XLRE and XLC are excluded as later entrants).
- **EWcf** (the audit counterfactual).

**Benchmarks (not charged; same tranching, cadence and costs wherever they trade):**
- SPY buy-and-hold;
- 60/40 SPY/IEF* (spliced to IEF);
- 1/N over live U9 sleeves;
- RSP buy-and-hold (audit only);
- for the transfer panels, each panel's own 1/N.

**Costs.**
- Linear cost per unit traded = 1bp + max(2bp, s_{i,era}).
- Plus impact of 10·σ_d·√(|Δh|/1%) bp, capped at 25bp, with σ_d the 60-day std.
- s_{i,era} is a fixed half-spread schedule, declared conservatively and *not estimated from data*:

| Sleeve group | to 2006 | 2007–2012 | from 2013 |
|---|---|---|---|
| SPY | 1 | 1 | 1 |
| IEF TLT LQD EFA IYR GLD, SPDR-9 | 5 | 3 | 2 |
| EEM DBC | 10 | 5 | 3 |
| WEBS-17 | 15 | 8 | 5 |
| Proxies (fund NAV, par bond) | 2 | – | – |

- A 3× cost stress is reported for every book.

**Windows.**

| Window | Span | Role |
|---|---|---|
| Burn-in | 1993-02-01..1994-12-30 | State only, never reported |
| **Era A** | **1995-01-03..2009-12-31** | Sealed holdout, untouched by KRONOS |
| Bridge | 2010-01-04..2012-12-31 | Reported, not gated; KRONOS has seen it |
| **Era B** | **2013-01-02..2026-09-30** | Post-publication for MOP 2012, HOP 2013, Faber 2007, AFP 2012 |
| Pooled | 1995-01-03..2026-09-30 | |
| Audit | 2013-01-14..2026-06-04 | The ewbar span |
| Transfer | WEBS-17 from 1997-03-18; SPDR-9 from 1999-12-22; both to 2026-09-30 | Crisis-excluded variants drop 2000-03-01..2002-12-31 and 2007-10-01..2009-03-31 |

**Era-A sleeve count** (committed now; dates move to ETF listing + 252 days if a proxy fails X44):

| From | 1995-01 | 1995-05 | 1997-05 | 2000-08 | 2003-07 | 2005-11 | 2007-02 |
|---|---|---|---|---|---|---|---|
| Live sleeves | 3 (SPY, IEF*, TLT*) | 4 (+EEM*) | 5 (+IYR*) | 6 (+EFA*) | 7 (+LQD) | 8 (+GLD) | 9 (+DBC) |

The time-weighted mean is about 6.3 sleeves, or about 5.3 if every proxy fails. The full nine-sleeve panel covers only 2007-02..2009-12 of era A, which is reported descriptively.

**Metrics.**
- Primary: ExSR.
- Also: rf0 Sharpe, CAGR, vol, MaxDD, vol-matched MaxDD, CVaR95, turnover, mean invested fraction, fraction of days the cap binds.
- **Vol-matched MaxDD** of book x against benchmark y on a window:
  - k = sd(y−rf)/sd(x−rf);
  - n^vm_t = rf_t + k·(x_t − rf_t) − max(k−1, 0)·0.015·Δcal/365;
  - take the MaxDD of Π(1+n^vm).
- ΔSR inference: Ledoit–Wolf (2008), HAC-studentized circular block bootstrap, block 21 days, 5,000 resamples, seed 42; one-sided p and 90% CI.
- **Minimum detectable ΔSR at 80% power** (Lo 2002, ρ ≈ 0.6–0.7): about 0.55–0.6 per era and about 0.35–0.4 pooled. So a FAIL carries little information and a WIN is evidence, not proof.

### Data and availability

Checked 2026-10-13 on availability only. No returns or statistics were computed.

- **ETFs** (first trade on Yahoo; coverage 1.000 against the SPY calendar):

| Ticker | First trade |
|---|---|
| SPY | 1993-01-29 |
| IYR | 2000-06-19 |
| EFA | 2001-08-27 |
| IEF, TLT, LQD | 2002-07-30 |
| EEM | 2003-04-14 |
| RSP | 2003-05-01 |
| GLD | 2004-11-18 |
| DBC | 2006-02-06 |
| WEBS-17 | 1996-03-18, coverage 0.999 |
| SPDR-9 | 1998-12-22, coverage 0.999 |

  XLF carries a 1.231 split factor on 2016-09-19, its in-kind distribution of XLRE shares.
- **Proxies** (Yahoo):

| Fund | First date |
|---|---|
| VEIEX | 1994-05-04 |
| VGSIX | 1996-05-13 |
| VTMGX | 1999-08-17 |

  yfinance's `capital_gains` field is uninformative: it reads zero for these ETFs too. Distributions are therefore checked against issuer-published calendar-year total returns in X44(e).
- **FRED:**
  - DGS10 from 1962-01-02.
  - DGS30 has about 250 valid rows in every year 1992–2007.
  - DGS20 has values only from 1993-10 and is not used.
  - DTB3 is committed at `data/dtb3.csv` for 1954-01-04..2026-10-08.
- **Untouched-era check.** `live/genesis` spans 2010-01-04..2026-06-04. `data/cache` holds nothing before 2010. The only pre-2010 dates in the code are synthetic `bdate_range` indexes.
- **Verified unusable:**
  - ^SPGSCI (spot index, roll yield missing);
  - GC=F (roll gaps);
  - FRED LBMA gold (removed);
  - ICE BofA total-return series (truncated to 2023-10 onward);
  - DBV and GSP (delisted, absent from Yahoo);
  - the HF 1-minute set (unlicensed).
- **Snapshot.** One pull on the registration day, ending 2026-09-30, saved to `data/premia_genesis/*.csv.gz` with a SHA-256 of each file's bytes (fail-closed, the `data/pinned` pattern) and parsed with the correctly rounded float parser; no parsed-value digest is used, since those are platform-dependent (2026-10-13 CI incident). Nothing is re-pulled without a logged re-anchor.

### Gate X43 — synthetic and hermetic (`tests/test_premia.py`), before any real return is read

**Shared world** (all numbers pinned):
- 9 sleeves in four blocks.
- Annual vols {16, 18, 23, 22, 7, 14, 8, 16, 18}%.
- Correlations:
  - equity–equity 0.7;
  - rates–rates 0.85;
  - credit–rates 0.6;
  - credit–equity 0.3;
  - equity–rates −0.2 in regime 1 and +0.3 in regime 2;
  - real assets 0.1.
- Rough log-vol with H = 0.10 (`rough.simulate_rough_logvol`); the common clock carries a 0.5 share.
- Student-t innovations with ν = 5.
- Leverage effect −0.04 on equity, 0 on rates and gold, +0.03 on TLT.
- Staggered listings that match the real schedule.
- DTB3 replayed as cash; length 1995-01..2026-09.

**(a) Accounting.**
- A constant 5% discount rate on a synthetic business calendar with holidays: one year compounded matches the BEY target within 5bp.
- An all-cash book has excess ≡ 0 (to 1e-12).
- A book fully invested in an asset paying exactly rf has excess ≡ 0.
- E at e = 1.5 on that asset has excess ≡ −0.5·0.015·Δcal/365 per day.
- Idle capital is credited when e < 1.
- The exposure-change cost matches a hand fixture.
- The current net formula (`accounting` unset) reproduces the shipped engine in-process (to 1e-12). The momtilt reproduction runs as a run-time assert at 1e-6 in `exp_premia`, not as an arch-dependent byte pin.

**(b) Engine identity** (through the production path).
- With costs at 0, g ≡ 1, a non-binding cap and one tranche, P equals an independently coded inverse-vol drifted book (to 1e-12).
- With homogeneous vols, weights equal 1/N (to 1e-9).
- With every gate forced off, the book is 100% cash; nothing is renormalized.
- The 21-tranche average identity holds.
- With band = 0, the per-sub-book band matches an exact book; the lag the band adds is reported.

**(c) Causality and survivorship mechanics.**
- Every target, vote and exposure is exactly invariant to truncating future data.
- No weight goes to a sleeve before it has 252 returns.
- A planted delisting sends that sleeve's capital to cash.
- The splice switch is exact.
- **The seal mechanism:** an era-A run on data truncated at 2009-12-31 equals the full-span run's era-A slice exactly.

**(d) Trend-gate size and power (P vs A1, X33 mould).**
- (i) **Power world:** monthly drift predictability calibrated so I(mom21; 21-day sign) ≈ 0.02 bits. Required: ΔSR > 0 in at least 80% of 200 seeds.
- (ii) **Clean null:** drift ∝ variance (constant conditional Sharpe 0.3), with no predictability. Required: mean ΔSR ≤ +0.01, and ΔSR > 0 in both halves in at most 15% of seeds.
- (iii) **Leverage-only world** (constant drift, SV, equity leverage effect): ΔSR is reported and credited to the magnitude channel.
- (iv) **Long-bias world** (constant drift, homoskedastic): mean ΔSR < 0.

**(e) Cross-sectional weighting.**
- On the persistent-SV world, the dispersion of realized risk contributions under HAR-ratio weights is at most that under EWMA(hl 21)-ratio weights. On an iid-vol world the two tie within ±2%. Means over 100 seeds.
- The σ̂ floor fires on fewer than 0.5% of rebalances in normal worlds and on 100% of planted degenerate fits.

**(f) Par-bond pricer.**
- Matches closed form to 1e-10.
- With an unchanged yield, the return is the coupon accrual.
- Duration agrees with the analytic value.

**(g) Operating characteristics of the full rule R0–R5** (500 seeds per null, 300 per power world). The gate runs as a cached research artifact on a vectorized twin; the twin matches production to 1e-12 on a short panel.
- **Null worlds:**
  - N1 (smooth): drifts set so the population SR(B) equals max{SR(60/40), SR(SPY), SR(1/N)}. Calibrated by bisection on one drift scaler over a 1,000-year path.
  - N2 (episodic): regime-switching drift with about two deep equity bears per 30 years (mean length 18 months), plus one two-year stock–bond correlation flip. Same calibration.
  - N3 (decayed literature): trend predictability before 2010 and none after, with the era-B population margin set to 0.
- **δ** is the smallest value in {0, 0.05, …, 0.30} that gives a false-WIN rate of at most 10% in each of N1, N2 and N3.
  - If no value works, the rule is **untestable at this T** and the program stops (K0).
  - Expected δ: 0.05–0.20.
- **Power** is reported at true pooled ΔSR of +0.10, +0.20 and +0.30. Expected about 0.25, 0.45 and 0.65.
- CI runs a 5-seed × 10-year smoke version that must finish in under 30 seconds.

**(h) E/B mechanics and the new engine-defect gate.**
- Under `d28`, every HAR training row is real; no zero-padded rows. Asserted.
- The burn-in identity holds.
- The DD brake reads the gross-backbone high-water mark from the burn-in start.
- E_nodd has m_dd ≡ 1.
- B's blend identity holds.
- The legacy path is unchanged.

**(i) Cost schedule.** A fixture checks that the schedule is applied exactly by sleeve and era.

### Gate X44 — data quality on the committed snapshot (`tests/test_premia_data.py`), before any strategy statistic

The snapshot is committed, so this gate is hermetic. It computes no strategy statistic.

**(a) Integrity.** File-byte SHA-256 hashes are checked before parsing, fail-closed, as in X39.

**(b) Coverage.**
- Each ETF covers at least 0.995 of SPY-calendar days from first trade to 2026-09-30.
- Each FRED series has at least 0.95 valid rows per year.

**(c) Price integrity.**
- No price is non-positive.
- Every day with |r| > 25% (equity) or > 10% (bond or gold) must be explained by a Yahoo corporate-action record, or the gate fails.
- XLF's 1.231 factor on 2016-09-19 must be present and the adjusted series continuous.

**(d) Staleness.**
- Days with zero volume, or with H = L = C, are treated as missing.
- A WEBS sleeve is ineligible in any trailing 252-day window where more than 10% of days are such days.

**(e) Proxy fidelity on the overlap**, using weekly returns (Wednesday to Wednesday, immune to time-zone staleness):

| Proxy | Weekly correlation | Annual tracking error | Annual mean difference |
|---|---|---|---|
| Equity/REIT proxies | ≥ 0.95 | ≤ 5.0% | ≤ 1.5% |
| IEF* | ≥ 0.95 | ≤ 2.0% | ≤ 0.75% |
| TLT* | ≥ 0.95 | ≤ 3.5% | ≤ 0.75% |

- TLT* is tested on 2006-02-09..2026-09-30; its 2002-08..2006-02 overlap is reported only.
- Each mutual-fund proxy's calendar-year total returns must match the issuer's published figures within 0.50% for every year from its first full year to 2008. The reference values are transcribed, with source URL and retrieval date, into `data/premia_genesis/proxy_reference.csv` before X44 runs.
- Failure drops the proxy; the sleeve is then absent until its ETF listing plus 252 days.

**(f) Cross-check (reported, not gating).** IEF* and TLT* are compared against VFITX and VUSTX weekly returns over 1995–2002.

### Seal

- **At registration.** This file is committed alone, before any code for
  this program and before any data from 1995–2009 is fetched. Its SHA-256 and
  the registration commit's tree hash are recorded in the first amendment, which
  also commits the hash of `kronos/` and `run_research.py` at that point.
- **Before each reveal stage.** The code that produces the stage (`kronos/`,
  `run_research.py`, `tests/test_premia*.py`) is hashed and the hash committed
  in an amendment *before* the stage runs; the stage's artifact hash is
  committed with its results. A later stage asserts the earlier artifacts
  unchanged.
- **Trial count.** N is cumulative from 188 (all KRONOS work to date); this
  program's 23 books take it to 211, and any later owner selection adds one.

### Out-of-sample protocol — sealed staged reveal

Each stage is committed, with its artifact hash recorded in this file, before the next stage is read.

0. **Gates.** Run X43 and write the X43g numbers (δ, false-WIN rates, power) into a pre-run amendment.
1. **Data.** Run X44 on the committed snapshot. Record its outcome and the actual era-A sleeve schedule.
2. **Survivorship audit (`research/premia_audit.json`).** EW-48, EWcf, RSP and SPY under `d28`. C1 and EW raw are restated under `d28`; these are restatements of existing trials, not new variants.
3. **Era A (`research/premia_eraA.json`).** Every book is run on data truncated at 2009-12-31 (X43c makes this exact).
   - **K2 sanity check:** if ExSR(P) ≤ 0 or ExSR(B) ≤ 0, STOP. Audit before reading anything else. A fix requires a new failing gate and a ledger charge.
4. **Transfer panels (`research/premia_transfer.json`).**
5. **Era B (`research/premia_eraB.json`).** Assert that the full-span era-A slice equals the Stage-3 artifact to 1e-12.
6. **Pooled verdict and forensics (`research/premia.json`).** DSR at N=211, both SR0 sources; PBO 0.45 restated; program-family CSCV (16 blocks over the 15 pooled-window books in Ledger B, labeled low-information); the primary's out-of-sample rank; Hansen (2005) SPA of B against that family.
7. **Forward ledger.** P and E, plus B if shipped, are appended to `live/ledger.jsonl` through `run_live.py`, from a separate committed genesis of the ETF panel.
   - L1: exact reproduction.
   - L2: vol tracking. The QLIKE null band is recalibrated before the first row for a 5–7%-vol and a 12%-vol book.
   - L3: exposure bands [0, 1] for P and [0, 1.5] for E; cost drag within 2× the model.
   - Readouts: 12 months is descriptive, with tripwires on realized vol (±30% of forecast) and costs (±50% of model). 36 months is monitoring only (SE ≈ 0.58). The first inferential read is at 60 months: a one-sided test of H0: ExSR ≤ 0.

**Overclaim guard.** If pooled ExSR(B) > 1.0 or era-B ExSR(P) > 0.9, the verdict is withheld. A second engine is written from this spec without reading the first, and it must agree to 1e-6 on B's daily returns.

### Survivorship handling

1. **No single names** anywhere in the gated program. The 36 hindsight stocks appear only in the audit.
2. **Instruments come from a mechanical, performance-blind rule.** ETF and index-fund returns are index-level, with constituents chosen point-in-time by index providers; the residual bias is only that the wrapper survived.
3. **Both transfer panels are complete launch batches.** Every member of each batch still trades, so neither panel is survivorship-selected.
4. **Dead wrappers are excluded, not substituted.** Yahoo drops them (DBV, GSP), so carry and GSCI-ETN classes are left out. This is a disclosed wrapper filter.
5. **Treasury proxies come from FRED yields.** Rates do not delist.
6. **Index-fund proxies carry wrapper survivorship only.** No actively managed fund is used.
7. **C1's 1.00 is restated** "on a hindsight-selected universe", beside the audit's measured selection premium, wherever it appears. This holds whatever the verdict.

### Decision rule (fixed before any run)

Benchmarks are computed on the same days, under the same accounting.

B **WINS** if and only if all six conditions hold:

| | Condition |
|---|---|
| **R0** | ExSR(B) > 0 in era A and in era B. |
| **R1** | Pooled: ExSR(B) − max{ExSR(60/40), ExSR(SPY), ExSR(1/N-9)} ≥ δ, with δ from X43g. |
| **R2** | Era B (post-publication): ExSR(B) − ExSR(60/40) ≥ 0. |
| **R3** | Era A (holdout): ExSR(B) − ExSR(60/40) > 0 and ExSR(B) − ExSR(SPY) > 0. |
| **R4** | Fragility: for all nine B₋ᵢ, pooled ExSR(B₋ᵢ) − ExSR(60/40) > 0. |
| **R5** | Pooled vol-matched MaxDD(B → 60/40's vol) is no deeper than MaxDD(60/40). |

**CERTIFIED** additionally requires a Ledoit–Wolf one-sided p < 0.05 for the pooled ΔSR(B − 60/40) and a headline DSR ≥ 0.95. It is not expected to be reached.

**Component verdicts (reported, not gating):**
- **H2a** holds if and only if P beats 60/40 in era A and does not lose to it in era B.
- **H2b** (trend gate) is dead if ExSR(P) ≤ ExSR(A1) in 2 or more of the 4 panels.
- **H2c** (risk balancing) is dead if ExSR(P) ≤ ExSR(A2) in 2 or more of the 4 panels.
- **H2d** holds if and only if, in era A and in era B, ExSR(E) ≥ ExSR(SPY) and the vol-matched |MaxDD(E→SPY vol)| ≤ 0.85·|MaxDD(SPY)|. An era-A failure is recorded prominently: "the licensed overlay does not generalize out of its licensing era". E_nodd then attributes the failure to the lever or to the brake.
- **H-AUDIT** is reported as measured.

### Shipping and headline rule (fixed now; `check_surfaces.py` asserts the README states the DESIGN28 verdict)

- **WIN.** B becomes the default book. `accounting` and `warmup_mode` switch to `d28` globally in the same commit, and every surface is restated.
  - The README headline carries B's pooled and era-B ExSR, MaxDD, vol and CAGR, with DSR and PBO 0.45 beside them.
  - C1 is restated as "hindsight-selected universe" beside the selection premium.
- **FAILURE.** No new default. The README headline still changes:
  - it states "DESIGN28: FAILURE";
  - it shows the survivorship-free B, P and E numbers as research results;
  - it labels C1 with the audit's selection premium.

  C1 stays live only as the already-shipped interim system.
- **Overrides.** Any owner selection made after the verdict (for example, shipping B, P or E despite a FAILURE) is recorded as an owner selection and **charged one ledger entry**.

### Kill criteria

- **K0.** If X43 fails, the program stops before any real data is read and nothing is charged. This includes X43g finding no δ ≤ 0.30, which is reported as "untestable at this T". A failure of an ETF primary in X44 halts the program; a proxy failure only drops that proxy, by rule.
- **K2.** The era-A sanity stop in Stage 3.
- **K3.** If any of R0–R5 fails, the program is a **FAILURE** and is stated as one.
  - The line closes: no changes to lookbacks, sleeves, universe, cap, cadence, leverage, δ or windows; no grids; no retries.
  - Further Sharpe work requires a new licensed information source.
- **K4.** If the headline DSR is below 0.5, the result is labeled "not certifiable after deflation" next to every quote, whatever the verdict.
- **K5.** Component kills (H2b, H2c, H2d) are reported whichever way the program lands. A component that dies is never removed from the book and rerun.
- **K6.** In the forward ledger, a fired tripwire suspends the book pending review. Re-tuning is never allowed.

### Priors

These are stated now so the result can be read against them. They come from the literature and from the repo's reported numbers; the SPY and 60/40 figures for era A are general-knowledge priors and were not computed. Entries are ExSR.

| Book | Era A | Era B | Pooled | MaxDD (pooled) | Vol |
|---|---|---|---|---|---|
| **B** | 0.55–0.85 (0.70) | 0.50–0.85 (0.65) | 0.60–0.80 (0.70) | −12% to −22% | 6–8% |
| P | 0.65–1.00 (0.80) | 0.30–0.65 (0.45) | 0.55–0.75 (0.62) | −10% to −18% | 5–7% |
| A1 | 0.55–0.85 | 0.25–0.45 | 0.45–0.65 | −15% to −25% | 6–8% |
| E | 0.25–0.55 | 0.70–0.95 | 0.50–0.70 | −20% to −32% | 11–13% |
| SPY | 0.20–0.35 | about 0.80 | 0.45–0.60 | −55% | 18–19% |
| 60/40 | 0.35–0.55 | 0.65–0.85 | 0.55–0.70 | −28% to −32% | 10–11% |
| 1/N-9 | 0.40–0.65 | 0.25–0.40 | 0.40–0.55 | −35% to −45% | 10–13% |

- **Pass probabilities:** R1 ≈ 45%, R2 ≈ 35–45%, H2d ≈ 30–40%, WIN ≈ 15% (range 10–25%).
- **Most likely failure path:** R2. A diversified trend book does not beat 60/40 in a decade that rewarded US equity, and duration until 2021.
- **Selection premium (H-AUDIT):** +0.15 to +0.40.
- **Headline DSR:** about 0.1–0.4.

### Trial accounting

Twenty-three new entries go into `design28_premia` in the `exp_forensics` ledger dict, taking N from 188 to 211.

**Ledger A (all 23 charged):**
- B, P, A1, A2, E, E_nodd (6);
- B₋ᵢ (9);
- R-F5 (1);
- transfer P/A1/A2 × 2 (6);
- EWcf (1).

**Ledger B (the 15 pooled-window books used for CSCV):** B, P, A1, A2, E, E_nodd, and the nine B₋ᵢ.

Benchmarks and the `d28` restatements of existing DESIGN27 rows are not charged. DSR and PBO are recomputed and restated beside every quoted Sharpe.

### Budgets

**Compute.**
- About 30 books at roughly 8,000 days × at most 17 sleeves, all in vectorized numpy.
- X43g: about 1,500 null paths plus 900 power paths on the twin; hours at most, cached.
- The CI smoke runs in under 30 seconds.
- X43 and X44 move the gate count from 46 to 48. The README badge and the `check_surfaces` pins move in the same commit.

**Effort: about 12 working days.**

| Item | Days |
|---|---|
| This file and owner sign-off | 0.5 |
| Accounting and cash flags, X43a/h | 1.5 |
| Snapshot, par-bond builder, proxy reference file, X44 | 2 |
| `kronos/premia.py` engine and X43b–f, i | 2.5 |
| E/B through `backtest.py` (`d28`, warmup mode) | 1 |
| X43g calibration | 1.5 |
| Staged runs and forensics | 1 |
| FINDINGS (KRONOS-PREMIA), METHODS (cash convention), README/paper surfaces, forward-ledger extension with L2 recalibration | 2 |

### Reporting

- **Artifacts:** `research/premia_gate.json`, `premia_data.json`, `premia_audit.json`, `premia_eraA.json`, `premia_transfer.json`, `premia_eraB.json`, `premia.json`.
- **FINDINGS** gains KRONOS-PREMIA. It also records the engine defects (cash accrual, idle cash, the HAR zero-row warmup) together with their new gate.
- Verdicts are stated per the framing rule: which claim survives.

### Amendments

Allowed only before Stage 2, and only on synthetic evidence. The post-X43 amendment must record:
- δ;
- the X43g false-WIN and power numbers;
- the pinned world parameters;
- the measured floor-guard firing rate;
- the cap-binding rate on synthetic data;
- the snapshot digests;
- the realized era-A sleeve schedule after X44.

### Appendix A — programs considered and not registered

1. **Sector-ETF residual-momentum and vol-timing tilts.** Underpowered, and industry momentum has likely decayed. Its out-of-era overlay test is grafted here as E, on SPY.
2. **Macro-regime correlation organ.** The primary contrast is confounded by shrinkage, and the increment has no route into P&L.
3. **17-slot bucketed risk parity.** A mirrored dollar pair dominates its capital and its duration bucket is near cash. Its accounting fix and δ calibration are grafted here.
4. **1-minute tape.** The data cannot be published, and its robust arm is worth about +0.01. It can be reconsidered only with a licensed minute file.

### Literature

Every DOI below was fetched and matched (title, first author) against Crossref on 2026-10-13; entries without one are cited by venue only.

- DeMiguel, Garlappi & Uppal (2009). RFS 22(5):1915–1953. doi:10.1093/rfs/hhm075
- Faber (2007). JWM 9(4):69–79. doi:10.3905/jwm.2007.674809
- Moskowitz, Ooi & Pedersen (2012). JFE 104(2):228–250. doi:10.1016/j.jfineco.2011.11.003
- Hurst, Ooi & Pedersen (2013). "Demystifying Managed Futures". J. Investment Management 11(3):42–58. No DOI.
- Hurst, Ooi & Pedersen (2017). JPM 44(1):15–29. doi:10.3905/jpm.2017.44.1.015
- Lempérière et al. (2014). J. Investment Strategies 3(3):41–61. arXiv:1404.3274
- Babu, Levine, Ooi, Pedersen & Stamelos (2020). "Trends Everywhere". J. Investment Management 18(1)
- Levine & Pedersen (2016). FAJ 72(3):51–66. doi:10.2469/faj.v72.n3.3
- Clare, Seaton, Smith & Thomas (2016). J. Behavioral & Experimental Finance 9:63–80. doi:10.1016/j.jbef.2016.01.002
- Zakamulin (2014). J. Asset Management 15(4):261–278. No identifier verified.
- Hutchinson & O'Brien (2014). J. Alternative Investments 17(2):82–102. No identifier verified.
- Kim, Tse & Wald (2016). J. Financial Markets 30:103–124. doi:10.1016/j.finmar.2016.05.003
- Huang, Li, Wang & Zhou (2020). JFE 135(3):774–794. doi:10.1016/j.jfineco.2019.08.004
- Asness, Frazzini & Pedersen (2012). FAJ 68(1):47–59. doi:10.2469/faj.v68.n1.1
- Anderson, Bianchi & Goldberg (2012). FAJ 68(6):75–93. doi:10.2469/faj.v68.n6.7
- Maillard, Roncalli & Teïletche (2010). JPM 36(4):60–70. doi:10.3905/jpm.2010.36.4.060
- Kirby & Ostdiek (2012). JFQA 47(2):437–467. doi:10.1017/S0022109012000117
- Moreira & Muir (2017). JF 72(4):1611–1644. doi:10.1111/jofi.12513
- Cederburg, O'Doherty, Wang & Yan (2020). JFE 138(1):95–117. doi:10.1016/j.jfineco.2020.04.015
- Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & Van Hemert (2018). JPM 45(1):14–33. doi:10.3905/jpm.2018.45.1.014
- Bollerslev, Hood, Huss & Pedersen (2018). RFS 31(7):2729–2773. doi:10.1093/rfs/hhy041
- Corsi (2009). JFEc 7(2):174–196. doi:10.1093/jjfinec/nbp001
- Gatheral, Jaisson & Rosenbaum (2018). QF 18(6):933–949. doi:10.1080/14697688.2017.1393551
- Campbell, Pflueger & Viceira (2020). JPE 128(8):3148–3185. doi:10.1086/707766
- Erb & Harvey (2006). FAJ 62(2):69–97. doi:10.2469/faj.v62.n2.4084
- Bhardwaj, Gorton & Rouwenhorst (2015). NBER WP 21243.
- Welch & Goyal (2008). RFS 21(4):1455–1508. doi:10.1093/rfs/hhm014
- McLean & Pontiff (2016). JF 71(1):5–32. doi:10.1111/jofi.12365
- Jegadeesh & Titman (1993). JF 48(1):65–91. doi:10.1111/j.1540-6261.1993.tb04702.x
- Swinkels (2019). Data 4(3):91. doi:10.3390/data4030091
- Goetzmann, Ivković & Rouwenhorst (2001). JFQA 36(3):287–309. No identifier verified.
- Brown, Goetzmann, Ibbotson & Ross (1992). RFS 5(4):553–580. doi:10.1093/rfs/5.4.553
- Elton, Gruber & Blake (1996). RFS 9(4):1097–1120. doi:10.1093/rfs/9.4.1097
- Lo (2002). FAJ 58(4):36–52. doi:10.2469/faj.v58.n4.2453
- Ledoit & Wolf (2008). JEF 15(5):850–859. doi:10.1016/j.jempfin.2008.03.002
- Hansen (2005). JBES 23(4):365–380. doi:10.1198/073500105000000063
- Magdon-Ismail & Atiya (2004). "Maximum drawdown". Risk 17(10):99–102.
- Bailey & López de Prado (2014). JPM 40(5):94–107. doi:10.3905/jpm.2014.40.5.094
- Bailey, Borwein, López de Prado & Zhu (2017). J. Computational Finance 20(4):39–69. doi:10.21314/JCF.2016.322
- Politis & Romano (1994). JASA 89(428):1303–1313. doi:10.1080/01621459.1994.10476870