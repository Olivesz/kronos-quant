# KRONOS-FX — Closing the Microstructure Triangle (Atlas IX.1c)

*Pre-registered. KRONOS-TRANSFER (DESIGN13) showed the mechanism laws hold in
every equity market; KRONOS-CRYPTO (DESIGN14) showed one of them — the
leverage effect — is not a market universal: it INVERTS (+0.031) where the
equity microstructure is absent. That leaves the triangle open. Equities have
BOTH financial/operating leverage and institutional de-risking (leverage
−0.04); crypto has NEITHER, plus a retail-FOMO dynamic (leverage +0.03). FX is
the third vertex: a decentralized 24/5 dealer market with institutional flow
but **no financial leverage of the underlying** (a currency is not a levered
claim on any balance sheet) and **no retail-FOMO dominance**. If the leverage
effect is a monotone function of these two microstructure ingredients, FX must
sit at ~zero — equity negative, FX zero, crypto positive — turning a binary
"inverts outside equities" into a three-point dial. That ordering is the
pre-registered prediction, stated with numeric criteria below, before any FX
leverage number has been computed.*

## The design

One new universe: **13 liquid FX crosses** (EURUSD, USDJPY, GBPUSD, AUDUSD,
NZDUSD, USDCAD, USDCHF, EURJPY, EURGBP, GBPJPY, EURCHF, AUDJPY, USDMXN —
Yahoo tickers `EURUSD=X`, `JPY=X`, `GBPUSD=X`, `AUDUSD=X`, `NZDUSD=X`,
`CAD=X`, `CHF=X`, `EURJPY=X`, `EURGBP=X`, `GBPJPY=X`, `EURCHF=X`, `AUDJPY=X`,
`MXN=X`), daily OHLC 2010–2026 — the **same span as the equity universes**,
unlike crypto's shorter 2017 start.

**Data quality was screened before this design was locked.** Yahoo FX daily
bars are known to sometimes carry fake ranges (high == low, or high/low
exactly pinned to open/close), which would silently invalidate Garman-Klass —
the vol proxy the whole battery rests on. Screen, applied per pair over
2010–2026: a day has a REAL range iff `high > low` strictly AND
`high − low > |close − open| · 1.0001`. Pre-declared rule: a pair is usable
only if >95% of its days have a real range; the study proceeds only if ≥8
pairs survive. **Measured result: all 13 pairs pass, with real-range fractions
99.88%–100.00%** (~4,275 days each). The universe is locked at 13; only range
quality was examined — no return, vol, or leverage quantity was computed.

The **same 7-law battery** (roughness H, raw kurtosis, one-clock deformed
kurtosis, leverage effect, clock commonality, Hawkes branching raw &
deformed) is estimated on FX and placed beside the four equity universes from
TRANSFER **and** the crypto universe from CRYPTO — six universes, one shared
equity baseline, pure reuse of the CONSTANTS variance-ratio machinery.

## Pre-registered hypotheses

Baselines cited from the already-published `research/transfer.json` and
`research/crypto.json` (equity-cohort leverage mean **−0.0405**, cross-market
spread **0.0079**; crypto leverage **+0.0312**, sampling SD **0.0158**; equity
raw kurtosis range **8.4–13.1**, median **10.1**).

- **F1 — the One-Clock law survives.** Deformed (vol-standardized) kurtosis
  lands below 5 (expected ~[3, 4.5], as in every market measured so far).
  *Kill:* deformed kurtosis ≥ 5 — the clock fails to gaussianize FX returns.
- **F2 — FX leverage is ZERO, and the triangle is monotone.** This is the
  differentiating prediction. All of the following, stated before looking
  (`lev_fx` ± `sd_fx` is the battery's pooled estimate with its
  block-bootstrap SD):
    1. **Indistinguishable from 0:** `|lev_fx| / sd_fx < 2`, AND the per-pair
       signs are not lopsided — between 3 and 10 of the 13 pairs positive
       (a two-sided binomial sign test at 5%: ≤2 or ≥11 rejects symmetry).
    2. **Above the equity cohort** (one-sided 5%):
       `(lev_fx − (−0.0405)) / sqrt(sd_fx² + 0.0079²) > +1.645`.
    3. **Below crypto** (one-sided 5%):
       `(+0.0312 − lev_fx) / sqrt(sd_fx² + 0.0158²) > +1.645`.
  One-sided tests are pre-registered deliberately: the *direction* of each gap
  is the hypothesis. Declared before looking: the crypto side is the weak
  test — crypto's own sampling SD (0.0158) means that even a true FX zero
  with an equity-like `sd_fx` of 0.008–0.012 yields z ≈ 1.6–1.8, so
  demanding 2.0 there would be a test the true hypothesis could barely pass;
  1.645 is the honest threshold, chosen now, not after.
  *Kill criteria (each a real finding, reported as such):*
    - `lev_fx < 0` with `|lev_fx|/sd_fx > 2` → the equity-style leverage
      effect does NOT require equity plumbing; the equity/FX side of the
      triangle collapses.
    - `lev_fx > 0` with `lev_fx/sd_fx > 2` → FX shares crypto's inversion;
      the retail-FOMO mechanism story is wrong.
    - criterion 2 fails → FX is indistinguishable from equities; leverage
      tracks something other than the proposed microstructure axis.
- **F3 — fat tails, but milder than equities.** FX majors are known
  thinner-tailed than single stocks (dealer intermediation, no earnings
  jumps). Pooled raw kurtosis expected in ~[4, 8]. *Pass:* below the equity
  cohort minimum **8.4**. *Kill:* at or above the equity median **10.1**.
  Between 8.4 and 10.1 → MARGINAL, reported as not confirmed.

## Cleaning: the clip, chosen and justified here

FX moves are small — but not always. The largest genuine one-day move in this
universe since 2010 is the SNB floor removal (2015-01-15): EURCHF and USDCHF
fell ~15–19% intraday. That day is exactly the kind of tail F3 measures and
MUST survive cleaning. Yahoo FX bad ticks, by contrast, are typically
inversion/decimal glitches at 100%+ scale. The pre-chosen clip is therefore
**|daily move| > 25% = data error** (zeroed): wide enough to preserve every
documented real FX event with margin, tight enough to kill genuine glitches.
(Crypto's 500% clip is inappropriate here — no major cross has ever moved
anything like that; equities' 60% clip would also pass, but 25% is chosen to
reflect what FX can actually do.) Coverage ≥90% vs the union calendar,
forward-fill limit 3 days.

## Quote-direction convention (declared before looking)

Yahoo mixes conventions: `EURUSD=X` is EUR/USD, but `JPY=X`, `CAD=X`,
`CHF=X`, `MXN=X` are USD/XXX. Inverting a pair flips the sign of its returns
and hence the sign of any leverage reading. Under the F2 null (zero leverage)
the convention is irrelevant — which is itself part of the prediction: FX has
no privileged "down" direction the way an equity does. Declared handling: each
pair is measured in its **native Yahoo quote direction**, fixed here. If F2
is killed by a significantly nonzero reading, per-pair signs will be
interpreted against the safe-haven axis (JPY/CHF strengthen risk-off, so
flight-to-safety flows could masquerade as leverage with sign set by the
quote direction) — that interpretation is declared now so it cannot be
invented after seeing the numbers.

## Gates: nothing new to license — plus a loud runtime guard

The battery machinery is gated by **X24** (transfer) and **X22** (stability);
reading a leverage *sign* is gated by **X26**, whose symmetric world also
bounds spurious leverage at |0.04| — which licenses reading a ~0 as a real ~0
(the F2 zero-reading is the same claim X26's symmetric arm already proves the
estimator can make). No new estimator gate is needed. The one new failure
mode is DATA quality, so the real-range screen above is also enforced at
runtime: `load_fx` re-measures the real-range fraction on every load, drops
any pair at ≤95%, and **raises** if fewer than 8 pairs survive — the study
fails loudly rather than measuring garbage through an invalid GK proxy. It
never silently degrades to close-to-close (that would change the estimator
and break comparability with the equity/crypto batteries).

## Scope / declared caveats

- **Laws only, not a trading system.** As with crypto, no frozen-system run:
  the KRONOS book is an equity long-only risk engine; FX carry/trend is a
  different animal and out of scope.
- **No official close.** FX trades continuously 24/5; Yahoo's daily bar
  boundary is a venue convention, not an auction. Fine for distributional
  laws; declared.
- **Shared legs correlate crosses mechanically** (EURUSD and EURGBP share
  EUR; triangular identities bind the crosses), so clock "commonality" is
  expected elevated for arithmetic reasons — reported, not hypothesised,
  exactly as in crypto.
- **One EM cross** (USDMXN) is included deliberately as the stress case;
  12 majors + 1 EM. Currencies do not delist, so survivorship is not the
  issue it was for crypto.
- **CHF pairs carry the SNB event.** Single-pair kurtosis for EURCHF/USDCHF
  may be enormous; the battery pools by median-across-pairs, so the pooled
  F3 reading is robust to it. Both facts declared.

## Deliverable

`run_research.py fx` → `research/fx.json`: the six-universe law table
(4 equity + crypto + FX, per-law TRANSFERS / UNIVERSE-SPECIFIC verdicts and
z-scores vs US), the three-class leverage contrast (equity cohort vs FX vs
crypto with the F2 z-tests), per-pair leverage, the real-range audit, and the
F1–F3 verdicts. Plus a FINDINGS entry — including, if any criterion is
killed, the honest write-up of what that means for the triangle.
