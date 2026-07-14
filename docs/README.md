# KRONOS — Research Map

This directory holds the pre-registered design notes behind every experiment.
Each was written **before** the code and the data run, so the negative results
carry the same weight as the positive ones. Read them in order for the full
arc, or jump to a finding.

- [**ATLAS.md**](ATLAS.md) — *The Atlas of Ignorance*: the open-problem map
  that scopes the whole research program (what quant finance does not know,
  and which questions KRONOS is actually equipped to attack).

## The build, in order

| # | Design note | Theme | One-line finding |
|---|-------------|-------|------------------|
| 1 | [DESIGN.md](design/DESIGN.md) | KRONOS v1 platform | The regime-aware core: HMM → signals → HRP/BL → risk overlay → dashboard. |
| 2 | [DESIGN2.md](design/DESIGN2.md) | KRONOS-X agenda | Six pre-registered research questions on top of the platform. |
| 3 | [DESIGN3.md](design/DESIGN3.md) | Student-t HMM | **Gaussian HMMs hallucinate regimes from fat tails** — it's ~3 regimes + heavy tails, not 5 regimes. |
| 4 | [DESIGN4.md](design/DESIGN4.md) | The One-Clock law | Returns are conditionally Gaussian given the realized-vol path (kurtosis 12.6 → 2.6 across 48 assets). |
| 5 | [DESIGN5.md](design/DESIGN5.md) | Systemic risk = correlated clocks | Joint crashes are correlated **volatility surges**, not residual contagion. |
| 6 | [DESIGN6.md](design/DESIGN6.md) | Surge structure | The cascade terminates after **one** level — volatility has irreducible jumps. |
| 7 | [DESIGN7.md](design/DESIGN7.md) | The information budget | The daily **direction** channel is closed (ceiling Sharpe 0.48 < beta); the **magnitude** channel leaks ~0.4 bits/day. |
| 8 | [DESIGN8.md](design/DESIGN8.md) | The minimal market | An agent-based market scored on the full battery: the vol-targeting spiral buys the wild facts; the missing organ is *expectation*. |
| 9 | [DESIGN9.md](design/DESIGN9.md) | Crashes: critical or shock? | After removing the volatility confound, **critical-slowing-down carries no incremental crash-prediction signal** — crashes are shocks. |
| 10 | [DESIGN10.md](design/DESIGN10.md) | Endogeneity / reflexivity | 64% of the market's famous near-criticality is **volatility clustering, not reflexivity** (branching ratio 0.68 → 0.25 after deformation). |
| 11 | [DESIGN11.md](design/DESIGN11.md) | Which laws are constant? | The market's *mechanism* constants are constant; what varies is **crisis intensity**, peaking in 2020 and reverting — no Adaptive-Markets secular drift. |
| 12 | [DESIGN12.md](design/DESIGN12.md) | The deployable system | `run_trade.py` — the trading system the research actually licenses (forecast-vol targeting; risk control, not direction timing). |
| 13 | [DESIGN13.md](design/DESIGN13.md) | Cross-market transfer | The mechanism laws (fat tails, leverage, near-critical branching) reappear abroad; the frozen US-tuned system holds its risk edge in Japan/Europe/Asia-EM. |
| 14 | [DESIGN14.md](design/DESIGN14.md) | Crypto: laws outside equities | The mechanism transfers to crypto (one-clock collapse, branching), but the **leverage effect inverts** — it's a property of the equity microstructure, not a market universal. |

## How the research maps to code

Every design note has a module and a synthetic-ground-truth **gate** that runs
before real data ever touches the estimator:

| Design | Module(s) | Gate |
|--------|-----------|------|
| One-Clock (4) | `kronos/laws.py` | `tests/test_laws.py` (X14) |
| Clock / contagion (5) | `kronos/clock.py` | `tests/test_clock.py` (X15) |
| Surge (6) | `kronos/surge.py` | `tests/test_surge.py` (X16) |
| Bits (7) | `kronos/infobudget.py` | `tests/test_infobudget.py` (X17) |
| Arrow of time (7) | `kronos/entropyprod.py` | `tests/test_entropyprod.py` (X18) |
| Decathlon (8) | `kronos/decathlon.py` | `tests/test_decathlon.py` (X19) |
| Critical (9) | `kronos/critical.py` | `tests/test_critical.py` (X20) |
| Reflex (10) | `kronos/hawkes.py` | `tests/test_reflex.py` (X21) |
| Constants (11) | `kronos/constants.py` | `tests/test_constants.py` (X22) |
| Trade (12) | `kronos/trade.py` | `tests/test_trade.py` (X23) |
| Transfer (13) | `kronos/transfer.py` | `tests/test_transfer.py` (X24) |
| Crypto (14) | `kronos/crypto.py` | `tests/test_crypto.py` (X26) |

See the top-level [README](../README.md) for the full results tables.
