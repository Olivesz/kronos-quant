# The KRONOS Methods — *How Do You Know You're Not Fooling Yourself?*

> A guided tour of the statistical machinery behind KRONOS, written for a
> curious technical reader. No finance PhD required — but by the end you'll know
> why most quant backtests are noise, and the specific tricks this project uses
> to avoid becoming one of them.

Financial data is the most seductive minefield in applied statistics. It is
abundant, it looks like it has patterns, and money is on the line — so people
find patterns whether or not they exist. The graveyard of quantitative finance
is full of strategies that looked brilliant in a backtest and died on contact
with reality. Almost every one died of the same three diseases: **look-ahead**
(peeking at the future), **overfitting** (mistaking noise for signal), and
**confounding** (measuring one thing while believing you measured another).

KRONOS is built around a single obsession: *don't get fooled.* This document
explains the toolkit that obsession produced. Each section is a technique, its
intuition, the math when the math matters, and the actual place in the project
where it earned its keep.

---

## 0. The one rule: gate before you claim

Every estimator in KRONOS — every model, every statistical test — has to pass a
**gate** before it is allowed anywhere near real market data. A gate is a test
on *synthetic* data where **we already know the answer**, and it must prove two
opposite things:

- **Size** (a.k.a. the false-positive rate): on a world where the effect is
  *absent*, the test does **not** fire. If your crash predictor "predicts"
  crashes on pure noise, it predicts nothing.
- **Power**: on a world where the effect is *present by construction*, the test
  **detects** it. A test that never fires has perfect size and zero worth.

Statisticians call these Type I and Type II error control. We call it
**convict-and-exonerate**, because that framing forces you to build *both*
worlds. Here's the pattern, verbatim from the crash-prediction study
([KRONOS-CRITICAL](FINDINGS.md#kronos-critical--are-crashes-critical-transitions-or-shocks)):

- Build a **fold-bifurcation world** — a synthetic system that genuinely tips
  (a ball rolling in a double-well potential whose walls are collapsing). The
  early-warning test must **convict**: it scores an incremental AUC of **+0.63**.
- Build a **shock world** — a system that jumps for exogenous reasons, no
  tipping. The test must **exonerate**: it scores **+0.03**, confidence interval
  through zero.

Only after a test convicts the guilty and clears the innocent on synthetic data
do we point it at the real market. When the same test then reads **≈0** on real
crashes, we can *trust* that zero — because we proved the test isn't blind.
That is the difference between "we found nothing" and "there is nothing to
find." Every commit runs the full gate suite in CI — 39 gates at this
writing (count them: `ls tests/test_*.py`), and the number only grows: new
claims arrive with new gates.

> **Why this is rare.** Most backtests are a single number computed once on one
> history. They have no size, no power, no ground truth — there is nothing to
> check the number against. A gate is the unit test of empirical science.

---

## 1. The cardinal sin: look-ahead, and the three ways we kill it

Look-ahead is using information at time $t$ that you couldn't actually have had
at time $t$. It is astonishingly easy to do by accident, and it manufactures
gorgeous fake performance. KRONOS attacks it three ways.

**Filtered, not smoothed.** When you fit a hidden-state model (like our regime
detector) you can ask two different questions. *Filtering* asks: given data up
to today, what's the probability we're in each regime **now**? *Smoothing*
asks: given the **entire** dataset, what regime were we in on some past day? The
smoothed answer is better — it uses the future — which is exactly why you can
never trade on it. Textbook backtests quietly use smoothed states and look
psychic. KRONOS makes every decision on **filtered** probabilities, using only
$\{r_1, \dots, r_t\}$.

**Walk-forward refitting.** Parameters are re-estimated on a rolling window as
time advances, never fit once on the whole sample. The model that trades in 2019
has never seen 2020.

**T+1 execution.** A signal computed from today's close is executed at
*tomorrow's* prices, and pays a full transaction cost (commission + spread +
square-root market impact). You cannot trade at a price you used to make the
decision.

**And then we test that we did it right.** This is the part almost nobody does.
The trading system ships with a *causality gate*
([test_trade.py](../tests/test_trade.py)): shift every input forward by one day
and re-run history. If a single historical target weight changes, there was a
leak. The assertion is exact — zero tolerance:

```
causality: max target-weight diff on shared dates = 0.00e+00
```

If you can't write that test for your strategy, you don't know whether your
strategy looks into the future.

---

## 2. The volatility clock — the one trick that appears everywhere

If you take away one idea from KRONOS, take this one, because half the findings
are downstream of it.

Raw daily returns are **fat-tailed**: enormous moves happen far more often than
a bell curve allows (a "6-sigma" day should be a once-in-a-millennium event;
markets have several a decade). For 80 years this was treated as an intrinsic,
almost mystical property of markets. It mostly isn't.

The move is to **deform time by volatility**. Instead of looking at the return
$r_t$, look at the return *standardized by that day's own volatility*:

$$ z_t = \frac{r_t}{\sqrt{v_t}} $$

where $v_t$ is the day's variance. Do this and the fat tails largely **evaporate**.
Across 48 US assets, median kurtosis collapses from **12.6 to 2.6** — from wildly
fat-tailed to slightly *thinner* than Gaussian
([KRONOS-LAWS](FINDINGS.md#kronos-laws--invariance-hunting)). Equities, bonds,
gold, and credit, which look like utterly different distributions, become **one
shared distribution** after deformation. We call this the **One-Clock law**:
*returns are conditionally Gaussian given the volatility path.* The fat tails
were never in the returns — they were in the **clock**, the fact that volatility
itself lurches around. Big moves cluster on high-vol days; standardize them away
and the mystery dissolves.

Two technical points make this honest rather than circular:

**Measuring $v_t$ without the future.** We estimate each day's variance from its
**Open-High-Low-Close** range using the **Garman-Klass** estimator, which is
~6–8× more statistically efficient than squared close-to-close returns because
the high and low carry information the close throws away. Crucially it uses only
that day's bar — no peeking.

**The noise-injection trap.** If you standardize by a *noisy* estimate of
today's vol, you can accidentally *add* tails (dividing by an occasionally-tiny
denominator manufactures outliers). We caught this in a gate before it
contaminated a real result: standardizing by an unsmoothed proxy inflates
kurtosis. The fix — light causal smoothing of the vol proxy — is baked in and
gate-tested ([test_laws.py](../tests/test_laws.py)).

Once you have the clock, it becomes a *scalpel*. Nearly every later study works
by asking: **does this phenomenon survive deformation?**

- Systemic crashes? Raw, 93% of asset pairs crash together more than a Gaussian
  copula allows. Divide by the clock → 15%. **Contagion was mostly correlated
  volatility, not mysterious linkage** ([CLOCK](FINDINGS.md#kronos-clock--is-systemic-risk-just-correlated-clocks)).
- The market's famous "self-exciting" near-criticality? Raw branching ratio
  0.68; deformed, 0.25 — at the no-self-excitation null. **64% of it was
  volatility clustering, not reflexivity** ([REFLEX](FINDINGS.md#kronos-reflex--how-endogenous-is-the-market)).
- The arrow of time? Present in raw returns; **erased** by deformation — time's
  arrow lives in the return↔volatility coupling ([ARROW](FINDINGS.md#kronos-arrow--entropy-production)).

Same scalpel, five findings. That's what a good primitive buys you.

---

## 3. Honest uncertainty: bootstraps for data with a memory

Every estimate needs error bars, or it's a rumor. The standard way to get error
bars without assuming a distribution is the **bootstrap**: resample your data
with replacement thousands of times, recompute the statistic each time, and read
the spread. But the textbook bootstrap assumes your observations are
**independent** — and financial data emphatically is not. Volatility clusters;
today looks like yesterday. Resample days independently and you shatter that
structure, producing error bars that are far too *narrow* — false confidence,
the exact thing we're trying to avoid.

The fix is the **block / stationary bootstrap**: resample *contiguous blocks* of
time (KRONOS uses blocks of ~63 trading days — a quarter) so that the
autocorrelation inside each block is preserved. The *stationary* variant
(Politis–Romano) randomizes the block length with a geometric distribution so
the resampled series doesn't have artificial seams and is itself stationary.

You'll see this everywhere the project reports a confidence interval — the
strategy's Sharpe CI, the equity-curve fan chart, the era-stability tests. When
[KRONOS-SURGE](FINDINGS.md#kronos-surge--the-structure-of-the-surges) reports
that post-high-vol crash clustering has CI **[0.97, 6.74]** and therefore
*narrowly fails* significance, that interval came from a block bootstrap — and
the honest conclusion ("suggestive, not significant") came from respecting it
instead of rounding it away.

---

## 4. Comparing models without lying to yourself

Ask a model how well it fits the data it was trained on and it will flatter you.
The only honest question is **out-of-sample predictive accuracy**, and even that
has traps.

**Score densities, not point forecasts.** A good volatility model doesn't just
guess tomorrow's number; it puts a *probability distribution* on tomorrow. We
grade it with the **predictive log-density** (a proper scoring rule): the
log-probability it assigned, in advance, to what actually happened, in
nats/day. Proper scoring rules can't be gamed — you maximize your expected score
only by reporting your true beliefs. This is how the regime "horse race" is
judged, and it's why the answer to "how many regimes?" is honest.

**Is a difference real, or luck?** Two models differ by 0.02 nats/day — does
that mean anything? Three tests of increasing sophistication:

- **Diebold–Mariano** — a $t$-test on the *series of score differences*, with a
  HAC (heteroskedasticity-and-autocorrelation-consistent) variance so serial
  correlation doesn't fake significance. HAR-RV beats EWMA volatility forecasts
  at DM $= -7.1$ ($p < 0.001$): decisive.
- **Amisano–Giacomini** — like DM but for *conditional* predictive ability and
  density forecasts; asks whether one model would be preferred *going forward*,
  weightable toward the tails you care about.
- **Model Confidence Set** (Hansen–Lunde–Nason) — instead of crowning one
  winner, it returns the *set* of models that are statistically
  indistinguishable from the best at a chosen confidence level. This is the
  grown-up answer to model selection: often the data simply cannot separate the
  top few, and pretending otherwise is overfitting. When our MCS keeps both a
  two-state and a five-state model, that's the data telling us the extra states
  don't earn their keep.

Every one of these comparators is itself gated (e.g. the AG test is verified to
have **4.5% empirical size** at a nominal 5% — it fires on noise exactly as
often as it's allowed to, and no more).

---

## 5. Grading your own homework: overfitting forensics

Here is the deepest trap. Suppose you try 200 strategy variants and report the
best one's Sharpe ratio of 1.4. That number is **meaningless**, because the
*maximum* of 200 noisy Sharpes is large *even if every strategy is worthless*.
This is the multiple-comparisons problem wearing a suit, and it is how the
industry manufactures fake alpha at scale — usually without realizing it,
because the 199 discarded variants are never counted.

KRONOS runs the forensics on *itself*
([KRONOS-X Q6](FINDINGS.md#kronos-x--the-six-pre-registered-questions)):

**Deflated Sharpe Ratio** (Bailey–López de Prado). Take the raw Sharpe and
deflate it by (a) the number of trials you ran, (b) the variance of Sharpes
*across* those trials, and (c) the non-normality of returns (skew and fat tails
inflate naive Sharpe significance). The key quantity is the **expected maximum**
Sharpe under the null — roughly

$$ \mathbb{E}[\max \text{SR}] \approx \sigma_{\text{SR}}\Big(z_{1-1/N} \Big) $$

for $N$ trials — the bar a *real* edge has to clear. KRONOS's edge, deflated
across $N=181$ logged trials, gives **DSR $= 0.64$** — positive but *not*
certifiable. We say so, in the README, in bold.

**Probability of Backtest Overfitting** (PBO, via CSCV). Combinatorially split
the history into blocks, form every train/test partition, and ask: *when a
configuration is the in-sample best, how often is it below-median out-of-sample?*
That fraction **is** the probability your selection procedure is overfitting.
KRONOS measures **PBO $= 0.45$** — a coin-flip. The honest reading: our *core
engine* is sound, but choosing the single best sibling configuration is not
reliable. The trial ledger that feeds this is a real file
([research/trials.json](../research/trials.json)) — we count our shots.

Most projects hide the discarded variants. This one keeps a receipt.

---

## 6. The ceiling: how much is knowable at all?

Before you try to predict something, it's worth asking how predictable it *could*
possibly be. Information theory gives a clean answer.

The mutual information $I(\text{past}; \text{future})$ — measured in bits or nats
— is *the* upper bound on predictability: it's how many bits the past genuinely
leaks about the future. And by a beautiful result (Kelly, 1956), for a
log-growth-optimal bettor the **maximum achievable edge equals that mutual
information**. For a Gaussian channel it converts directly to a Sharpe ceiling:

$$ \text{SR}_{\text{daily}} = \sqrt{e^{2I} - 1} \;\approx\; \sqrt{2I}\ \text{ for small } I $$

So we *measured* it ([KRONOS-BITS](FINDINGS.md#kronos-bits--the-information-budget-of-the-market)).
Estimating mutual information on continuous, heavy-tailed, dependent data is a
minefield of its own, so we use the **KSG estimator** (Kraskov–Stögbauer–
Grassberger, a $k$-nearest-neighbor method, $k=4$) and — critically — subtract a
**shuffle null**: recompute MI on time-shuffled data (where the true answer is
zero) and subtract it, cancelling the estimator's finite-sample bias. Every
estimate is validated against **closed-form** MI on Gaussian AR(1) worlds where
the exact value is known.

The punchline table:

| Channel | leaks | meaning |
|---|---|---|
| **direction** (which way, tomorrow) | ~0.0007 bits/day | the daily sign channel is **closed** |
| **magnitude** (how big, tomorrow) | ~0.40 bits/day | vol is ~600× more predictable than direction |

The direction-only Sharpe *ceiling* — the best any daily sign-predictor of our
feature set could **ever** do — is **0.48**, which is below the market's own
buy-and-hold Sharpe. Read that again: a *perfect* daily direction-timer, given
this information, would still lose to holding the index. That single number
reorganized the entire trading system ([KRONOS-TRADE](FINDINGS.md#kronos-trade--the-deployable-system)):
stop timing direction, harvest the *magnitude* channel through volatility-aware
sizing. We didn't guess that; we measured the ceiling and obeyed it.

---

## 7. Measuring laws, not alphas — stability and transfer

The last third of the project stops hunting for profit and starts hunting for
**invariants** — quantities that are the same across time, across countries,
across asset classes. This is a shift from engineering to science, and it needs
its own statistic.

**Is a "constant" actually constant?** Estimate a quantity (say the roughness of
volatility, or the leverage effect) in several separate windows. They'll differ
— but is the difference *real drift*, or just sampling noise? The
**variance-ratio test** answers it:

$$ \text{VR} = \frac{\text{dispersion of the estimates across windows}}{\text{average sampling variance within a window}} $$

If $\text{VR} \approx 1$, the windows differ only as much as noise predicts —
**constant**. If $\text{VR} \gg 1$, there's genuine variation — **drifting**. A
bootstrap under the constant-true-value null turns VR into a $p$-value, and the
whole test is gated to have the right size (8% false-drift rate) and power (100%
detection of a planted trend). Applied across eras
([KRONOS-CONSTANTS](FINDINGS.md#kronos-constants--which-market-laws-are-actually-constant)),
it shows the market's *mechanism* constants (leverage, self-excitation, the
one-clock collapse) are genuinely fixed, while only crisis *intensity* moves —
a quantitative refutation of the "markets constantly evolve" story.

**The same machinery across space.** Run the identical variance-ratio test with
the "windows" being *different markets* instead of different eras, and you get a
transfer test. On Japan/Europe/Asia-EM ([TRANSFER](FINDINGS.md#kronos-transfer--does-market-structure-cross-borders))
the mechanism laws reappear; the exact values are local.

**The worked example, end to end: does the leverage effect survive crypto?**
This one shows the whole method in miniature
([KRONOS-CRYPTO](FINDINGS.md#kronos-crypto--do-the-laws-survive-outside-equities)).
The *leverage effect* is finance's most robust asymmetry: in equities, prices
falling **raises** future volatility (a negative correlation between today's
return and tomorrow's variance), from financial leverage and institutional
de-risking. It holds across every equity market, bonds, and gold. Does it hold
in crypto — a 24/7, retail-driven market with *no* financial leverage?

1. **Pre-register** (DESIGN14): before looking, we wrote the prediction — the
   effect should weaken or *invert* — and the kill criterion.
2. **Audit the reused machinery for domain assumptions.** The equity data
   cleaner clips >60% single-day moves as bad ticks. In crypto, 60% days are
   *real* — clipping them would silently delete the very fat tails we measure.
   We wrote a tail-preserving cleaner. (This is the kind of buried assumption
   that quietly invalidates cross-domain studies.)
3. **Gate the one new claim.** The whole finding rests on reading the *sign* of
   one correlation, so we built [gate X26](../tests/test_crypto.py): on
   synthetic worlds with a **known** leverage sign (equity-negative,
   inverted-positive, symmetric-zero), the estimator must recover each with wide
   separation. It does. So a "wrong" sign in real crypto is a property of the
   data, not the estimator.
4. **Measure.** Crypto's leverage effect is **+0.031** — *positive* — versus the
   equity cohort's **−0.041** ($z = 4.06$), with **8 of 10 coins individually
   flipping sign**.

The verdict: the mechanism laws are portable, but the leverage effect is **not a
market universal** — it's a property of the *equity* microstructure, and it
cleanly reverses where that plumbing is absent. A law that looked eternal,
broken on purpose by choosing the right stress test. That's the payoff of the
whole apparatus: findings you can *believe*, including the surprising ones,
because every load-bearing step was checked against a world where the answer was
already known.

---

## 8. Running a programme, not a backtest

Everything above is about one claim at a time. The final discipline is about
the *sequence* of claims — because the deadliest overfitting doesn't happen
inside an experiment, it happens *between* experiments, when you quietly run
ten and publish the two that worked.

KRONOS's research programme runs under four conditions, all required, for any
arm that touches the trading system:

1. **Pre-registered, with a kill criterion.** An arm that cannot say in
   advance what would kill it is not an experiment; it is a search for
   confirmation.
2. **A mechanism gate** — not a test that the outcome occurred, but a test
   that the edge *disappears where the mechanism cannot help* (the HAR lever
   must tie on iid-vol worlds; the momentum tilt must tie on driftless
   worlds). Outcome tests confirm luck as readily as skill; mechanism tests
   do not.
3. **Split-half survival in both eras**, with era-concentration disclosed
   rather than averaged away.
4. **A mechanism statable in one sentence.** A correlation you cannot explain
   is a future retraction.

And one number decides whether anything was *discovered*: the **deflated
Sharpe after the trial is charged to the ledger**. Raw Sharpe cannot count —
every additional look raises the bar a real edge must clear, so an arm that
lifts Sharpe while leaving DSR flat has found nothing but its own search. In
one representative night this programme ran eight arms: four survived (each
raising DSR while N grew — 0.60 → 0.75 across the arc), three were killed and
reported as loudly as the wins, one landed as a pre-registered partial. That
kill rate is not a failure statistic; it is the evidence that the bar exists.
A programme that reports success on everything is measuring its own
permissiveness, and the moment a parameter is being adjusted to get an arm
over its threshold, that arm is dead by definition.

## Postscript: the bug the gates missed

Everything above could read as "write enough tests and you're safe." Reality
check: for its first year of life, this project's flagship book ran with its
drawdown throttle **inverted** — a one-line sign error that applied maximum
braking at the equity high-water mark and *released* the brake into crashes.
Thirty gates, every one green, and none of them caught it, because **no gate
tested the overlay's direction**. Gates only cover the failure modes you
thought to imagine.

What found it was the other half of the discipline: **diagnosis before
optimization**. When the backtest looked mediocre, the temptation was to tune
signals at the result. Instead we asked *where does the return go?* — and the
accounting (a throttle binding on 93.6% of days, at its floor at the
high-water mark) pointed straight at the bug. The fix followed the full
protocol: pre-registered with expectations and kill criteria
([DESIGN15](design/DESIGN15.md)), shipped **with the missing gate** (X27, which
pins the throttle's monotonicity — m = 1 at the high-water mark, declining to
the floor), charged to the trial ledger, and reported with the old numbers
kept as the baseline row. The repair raised Sharpe from 0.94 to 1.02 before
any leverage — the "protection" had been pure drag.

Two lessons worth keeping. First, a green test suite is a claim about the
questions you asked, not the ones you didn't; when a result looks wrong,
*audit the accounting, not just the tests*. Second, the honest response to
finding a bug in your own published numbers is the same as for any other
finding: pre-register the fix, gate it, count the trials, and leave the old
numbers visible. ([Full write-up.](FINDINGS.md#kronos-edge--fixing-the-engines-structural-drag))

## The through-line

If there's a single principle under all of it: **make every claim falsifiable
and pre-committed, then try as hard as you can to break it.** Gate the
estimator on synthetic truth. Forbid the future. Deform away the confounds.
Bootstrap the error bars while respecting the memory in the data. Score models
out-of-sample and admit when the data can't separate them. Deflate your Sharpe
by the shots you took. Measure the ceiling before claiming the edge. And when a
law survives all of that across time, countries, and asset classes — *then* you
can call it a law.

That's not how you get the most impressive-looking backtest. It's how you get
one you can trust.

---

*Every claim above is reproduced by [`run_research.py`](../run_research.py) and
guarded by a gate in [`tests/`](../tests). For the full results, see
[FINDINGS.md](FINDINGS.md); for the research map, [README.md](README.md); for
the platform, the [top-level README](../README.md).*
