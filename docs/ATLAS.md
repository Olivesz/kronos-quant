# THE ATLAS OF IGNORANCE — What Quant Finance Does Not Know

*A map of the open problems, organized by territory. For each: what is known,
what nobody knows, why it resists, and how KRONOS specifically could attack
it. Fun score is subjective and proud of it.*

---

## Territory I — The Origin of Price Movement (microstructure & reflexivity)

**I.1 Why are markets near-critical?**
Known: Hawkes-process fits consistently estimate the endogeneity/branching
ratio near 1 (most activity is triggered by other activity, not news).
Unknown: WHY the market self-organizes to the critical point and stays
there. No accepted mechanism. Self-organized criticality stories exist but
none is testable.
KRONOS attack: estimate the branching ratio from daily extreme-event
clustering (Hawkes on threshold exceedances); check stability across eras.
Daily data is coarse — power is the issue. Fun: 7/10.

**I.2 The square-root impact law.**
Known: meta-order impact ~ sigma * sqrt(Q/V), eerily universal (equities,
futures, FX, crypto, century of data). The closest thing finance has to a
physical law. Unknown: WHY. The latent-liquidity derivation is promising
but unconfirmed; no consensus first-principles account.
KRONOS attack: we have no order-level data — out of reach empirically, but
an ABM (see VIII) could test whether simple liquidity dynamics reproduce
it. Fun: 8/10, blocked on data except via simulation.

**I.3 The excess volatility puzzle (Shiller, 1981 — still open).**
Prices move ~5-13x more than subsequent dividend changes justify. The
amplification mechanism (sentiment? feedback? discount-rate variation?)
remains unidentified after 44 years.
KRONOS attack: indirect only. Fun: 5/10 for us.

---

## Territory II — The Volatility Mysteries (our home turf)

**II.1 WHY is volatility rough?** We measured H≈0.10 with CI [0.08, 0.13].
The leading story: order-splitting + near-critical Hawkes dynamics implies
H→0 in the limit. The exact bridge from microstructure to H≈0.1 at daily
scale: open.
**II.2 Why does the cascade terminate?** (OUR OWN finding, SURGE S1: vol
innovations are not conditionally Gaussian given vol-of-vol — one clock
deep, then irreducible jumps.) No model in the literature predicts exactly
this one-level structure. rBergomi gives recursion-free roughness but no
jumps; jump-diffusion vol gives jumps but no roughness link.
**II.3 What causes the Zumbach effect / leverage effect?** Options-hedging
feedback? Stop-loss cascades? Behavioral panic asymmetry? The effect is
clear intraday, faint in daily bars (we measured exactly that). Attribution
unknown.
**II.4 The vol risk premium:** implied > realized, persistently, ~3-5 vol
points. Compensation for jump risk or behavioral insurance demand? Its
time-variation is forecastable — why doesn't it arbitrage away?
KRONOS attack on II.2: specify the minimal vol model (rough diffusion +
jumps) and fit it against our SURGE statistics — does it reproduce cascade
termination? Fun: 8/10. On II.4: needs options data we don't have.

---

## Territory III — The Cross-Section Crisis (asset pricing)

**III.1 How many real dimensions of expected return exist?**
400+ published anomalies; replication studies kill half; factor-zoo
dimension estimates range 3 to 20. The "periodic table of risk premia"
does not exist.
**III.2 Why does momentum still work 30 years after publication?**
Both behavioral and risk-based stories are unsatisfying. Its crashes
(2009) are regime-linked — our regime machinery is relevant.
**III.3 The low-vol anomaly:** the market's most basic prediction
(more risk, more return) FAILS in the cross-section. Leverage-constraint
explanations are partial.
**III.4 A conservation law of alpha?** McLean-Pontiff: anomaly returns
decay ~50% after publication. Is decay rate predictable from anomaly
characteristics (capacity, turnover, arb cost)? A quantitative law of
alpha decay would be foundational for the industry.
KRONOS attack: III.4 needs a panel of anomalies (Chen-Zimmermann open data
exists but ingestion is heavy). Fun: 7/10, data-blocked short-term.

---

## Territory IV — Dependence & Systemic Structure

**IV.1 What triggers the common clock surge?** (Our CLOCK finding: joint
crashes are correlated clock surges; the trigger is unidentified.)
Margin spirals? Vol-targeting feedback loops (everyone de-levers at once
BECAUSE everyone vol-targets)? The candidate mechanism is beautifully
self-referential: risk management CAUSES the risk. Testable prediction:
surge sizes should have grown as vol-targeting AUM grew (structural break
in vol-of-vol around 2010s).
**IV.2 Can crashes be anticipated?** Critical-slowing-down indicators
(rising AC1, rising variance before transitions) work in ecosystems and
climate; in markets the evidence is disputed. LPPLS bubble models remain
controversial. We HAVE dated regime transitions (HMM walk-forward) — we
can test whether early-warning statistics rise before bear transitions vs
matched control windows. Clean, falsifiable, our infra. Fun: 9/10.
**IV.3 Financial network topology from prices alone:** Granger/transfer-
entropy networks are notoriously unstable. Open whether ANY stable
structure beyond the one-factor clock exists. Fun: 6/10.

---

## Territory V — The Limits of Prediction (the deepest one)

**V.1 THE INFORMATION BUDGET OF THE MARKET.**
The grand question hiding under every quant job: how many bits per day
does the past leak about the future, and therefore what is the MAXIMUM
Sharpe any strategy could ever achieve?
Known fragments: direction is nearly unpredictable, vol is highly
predictable, Kelly theory links growth rates to mutual information
(Kelly 1956: the channel capacity IS the max log-growth edge), and for
Gaussian channels SR_per_step ≈ sqrt(2·I) nats. Nobody has assembled the
measurement: I(past ; future return) in bits/day, estimated model-free,
with honest bias control, separated into direction bits vs magnitude bits,
per horizon, per era.
Why it resists: mutual-information estimation on continuous, heavy-tailed,
serially dependent data is a minefield (estimator bias scales with
dimension; any leak inflates it). But we are the lab with the gate
methodology for exactly this kind of minefield — and the punchline table
("the market leaks 0.00x bits/day about direction and ~0.4 bits/day about
its own volatility; the no-cost Sharpe ceiling implied is Y; KRONOS
realizes Z% of its budget") would be unlike anything in the literature.
Closed-form gates exist: Gaussian AR(1) has exact I; we can verify
estimators to the third decimal. Fun: 10/10. THE pick.

**V.2 Entropy production: the true arrow of time.**
Zumbach is ONE projection of irreversibility. The general object is the
entropy production rate: KL(forward path distribution || time-reversed
path distribution) — the physics measure of how far the market is from
equilibrium. If daily returns have EP ≈ 0 but vol paths have EP > 0, the
arrow of time lives entirely in the clock — a sharper version of our
SURGE S2 finding, and a genuinely physics-grade quantity nobody computes
for markets. Estimable via path-space density-ratio methods or compression
asymmetry on coarse-grained sequences. Gates: reversible SV world (EP=0)
vs GJR world (EP>0), both already built. Fun: 9/10.

**V.3 The half-life of market structure.**
Is the data-generating process stable-with-regimes or genuinely evolving
(Adaptive Markets)? Measurable: walk-forward parameter drift of our fitted
laws (H, nu, clock commonality, leverage kernel) across eras with formal
break tests. "Which constants of the market are actually constant?" Fun:
8/10, cheap — we already have all the estimators.

---

## Territory VI — Decision Theory Under Reality

**VI.1 Multi-asset optimal trading under costs + predictability:** solved
only in toy cases. Computational frontier.
**VI.2 How much structure should a portfolio prior have?** (Bayes vs
shrinkage vs hierarchy — we touched this with HRP/LW.)
**VI.3 What SHOULD an investor maximize?** Kelly vs mean-variance vs
ambiguity aversion — unresolved after 70 years. Fun: 5/10 (philosophy-
heavy, hard to falsify).

---

## Territory VII — Derivatives Land (data-blocked for us)

VIX/SPX joint calibration; implied-vs-realized jump inconsistencies;
the volatility surface's shape grammar. All need options data. Fun: 7/10,
blocked.

---

## Territory VIII — The Minimal Market (generative models)

**VIII.1 THE STYLIZED-FACTS DECATHLON.**
What is the SMALLEST mechanism that reproduces ALL the facts we measured?
Our battery is now uniquely complete and validated: nu≈3-4 conditional
tails, one-clock Gaussianization, H≈0.10, cascade termination after one
level, faint-Zumbach, clock-driven joint tails (93→15→71 signature),
leverage class structure. No ABM paper tests against a battery this rich —
because nobody else HAS the battery.
The experiment: a minimal agent-based market (fundamentalists +
trend-followers + a leverage/vol-target constraint) with ~6 parameters.
Run the full KRONOS battery on its output as a fitness function. Ablation
table: which ingredient buys which stylized fact. If the vol-targeting
constraint is the ingredient that produces BOTH roughness and the surge
structure, that's a mechanism discovery (and connects to IV.1: risk
management causes the risk).
Fun: 10/10. Big, modular, entirely self-contained.

---

## Territory IX — Learning & Transfer

**IX.1 Does market structure transfer?** Train any structure (factors,
regime geometry, leverage kernels) on the US; test on Japan/Europe/EM.
Universality of MECHANISM vs luck. Data: more Yahoo tickers — feasible.
**IX.2 Is there nonlinear predictability beyond the linear factor world?**
Deep nets on returns mostly rediscover vol and momentum. MI measurement
(V.1) actually answers the ceiling question directly. Fun: folded into V.1.

---

## Territory X — The Weird Deep Ones

**X.1 A thermodynamics of markets:** fluctuation theorems, entropy
production (see V.2), an efficiency-temperature analogy. Mostly metaphor
so far; V.2 is the falsifiable piece.
**X.2 Ex-ante bubble definition:** does a quantitative, falsifiable bubble
criterion exist? LPPLS says maybe; backtests are contested. Fun: 7/10.
**X.3 Why 252 trading days of memory?** Where does the market's memory
length come from — institutional rhythms? Nobody asks the question
precisely. Fun: 6/10.

---

# THE SHORTLIST (chosen for maximum fun, zero regard for difficulty)

1. **THE INFORMATION BUDGET (V.1)** — measure the market's leak rate in
   bits/day; derive the Sharpe ceiling; compute what fraction of the
   budget KRONOS already spends. Gates: closed-form MI for Gaussian AR
   worlds; KSG and binned estimators with bias control; shuffled-data
   nulls. Headline artifact: the budget table.

2. **ENTROPY PRODUCTION (V.2)** — the full arrow-of-time measurement that
   SURGE S2 was a shadow of. Gates already half-built (reversible vs GJR
   worlds). Headline: EP(returns) ≈ 0 vs EP(clock) > 0?

3. **THE DECATHLON (VIII.1)** — minimal ABM scored on our complete
   battery; the ablation table of mechanisms→facts; the vol-targeting
   reflexivity hypothesis (IV.1) as the star ablation.

4. **EARLY WARNINGS (IV.2)** — critical slowing down before our dated bear
   transitions vs matched controls. Cheap, sharp, falsifiable.

5. **THE CONSTANTS OF THE MARKET (V.3)** — which of our measured laws are
   stable across eras? The "fundamental constants" stability report.

Execution order if approved: 1 → 2 (shared estimator machinery: both are
density-ratio/information functionals), then 4 and 5 (cheap), then 3 (the
big build, fed by everything before it).
