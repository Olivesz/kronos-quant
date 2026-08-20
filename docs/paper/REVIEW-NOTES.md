# Review state (post-research wave, 20 pp — submission-ready pending byline)

Two editorial waves (11 passes, commits "paper pass N" and "paper wave2
pass N") took the draft to final-draft state with seven remaining items,
five of them closable only by new experiments. The research wave (commits
"paper research 1–6", registrations in docs/design/DESIGN24.md, A0–A4)
then closed every item by measurement rather than prose. Outcomes that
went against the registered predictions are reported in the paper as
findings, per the registrations' honesty clauses.

## Current state

- **Build**: `make clean && make` — 20 pages, zero errors, zero undefined
  references, zero overfull boxes. `make arxiv` — staged copy smoke-builds
  standalone, `dist/arxiv.tar.gz` packed. caption.sty is now installed in
  the local TinyTeX, so local builds exercise the PRIMARY preamble branch
  (paper.log shows caption.sty loaded — the same branch arXiv uses); the
  kernel fallback was exercised by every pre-install build.
- **Numbers**: `make check` — 329 assertions against research/*.json, the
  battery code's thresholds, tests/ constants, and tests/run_all.py's gate
  list. PASSES with **zero narrative skips**: every number in the paper now
  traces to an executable source.
- **Gates**: full suite re-run after the research-wave code changes
  (per-seed event export, load_crypto universe parameter): 39/39 green.

## Former items — all closed

1. **DECA2 tuning-grid stats narrative-sourced** → CLOSED (A0). The frozen
   DESIGN18 grid was re-run with per-setting stat export
   (`decathlon2.json tuning_grid_stats`); every narrative number reproduced
   exactly (ac1 −0.090→−0.349, kurt 8.79→4.57, max bits 0.0390 at kA=1),
   including the registered pass's tie structure. §3 tethered; checker
   asserts.
2. **Joint-10/10 anchor is one index** → CLOSED (A1). Six-index audit,
   fixed list: the ≥9/10 prediction FAILED for non-US indices (DIA 10/10,
   QQQ/IWM 8/10, 1306.T/EXW1.DE/2800.HK 5–7/10, E7/E8/E9 recurring;
   calendar-padding ruled out by a recorded hygiene probe). Reported in the
   paper as a measured scope boundary: the battery's absolute anchor is a
   US-equity statement (§2 + appendix Table `tab:audit`); all in-paper
   conclusions are comparative and unaffected.
3. **One-layer E9 step inside seed noise** → CLOSED (A2). Registered
   32-seed extension: K1>K0 on 19/32, Wilcoxon p=0.57 — statistically
   flat, stated as such at every citation site; only the depth trend is
   licensed. F3's scatter shows all 32 seeds.
4. **No formal SE on battery scores** → CLOSED (A3). Seed-bootstrap SE per
   config (`score_se.json`), all ≤ 0.49 events; ± printed in the three
   experiment tables; §2's "no formal SE" caveat replaced by the method
   and the 0.5-event ceiling.
5. **FX–crypto edge z = 1.44 uncertifiable** → CLOSED as a proven bound
   (A4). Certification arithmetic: z ≥ 2 needs crypto SD 0.0158 → 0.0099;
   SDs are T-bound (~22 years of daily history needed, ~8.6 exist). The
   obtainable was obtained — registered widening to 17 majors moved the SD
   not at all (0.0161) and the z to 1.16. §7 now argues the bound in the
   body (underpowered, not under-analyzed) and states what would count as
   proof (a discriminating flow-migration prediction) and why current data
   cannot deliver it. This is the paper's one unavoidable limitation, and
   it is named with its impossibility argument rather than listed as a
   weakness.
6. **caption.sty branch untested locally** → CLOSED. `tlmgr install
   caption`; clean rebuild exercises the primary branch with identical
   output (19→20 pp change came from content, not the branch).
7. **METHODS.md "37 gates" vs paper** → CLOSED (commit 8a0e766): one
   executable truth (39), asserted by the checker against run_all.py.

## Remaining

- **Byline**: submission-time decision; in-repo stays authorless. Not a
  weakness.
- Known limitations now live **in the paper as measured statements**, not
  here: the battery's thresholds are US-calibrated (§2, appendix audit);
  the FX–crypto separation is history-bound (§7, with the arithmetic).
  This review knows of no referee-surfaceable item the paper does not
  already state with a number attached.

## Readiness verdict

**Submission-ready pending the owner's byline decision.** Zero open
weaknesses: every previously listed item is either closed by a registered
measurement or converted into an in-paper, checker-asserted bound. Further
passes are churn; the next state change is submission.

## What the checker cannot see (demonstrated, 2026-08-20)

`check_numbers.py` verifies number–source fidelity (329 assertions), not claim
composition. Tested by deliberate fraud: three passages were appended in which
every number was real and correctly `% src`-tethered but the joining claim was
false — (a) "front-running *reduces* the leak, 0.0184 → 0.0176" welding the
K0 baseline to the tuned-Q config as a fake causal effect (the honest pair is
0.0184 → 0.0200); (b) "widening *raises* z from 1.16 to 3.71" welding
z-vs-FX to z-vs-equities as one trend; (c) "the audit *confirms* venue
robustness: DIA 10/10, 2800.HK 5/10" — a gloss the numbers refute. The
checker passed all three at 329/329. **Composed-claim falsity is invisible to
mechanical tethering by construction.** The defenses that exist for this
class are the adversarial referee passes (which caught one real instance:
the K0→K1 "rise" overclaim) and the human read. Reader guidance: trust any
single number; verify any sentence that *joins* two numbers into a
comparison, trend, or causal claim against the named JSON fields.
