# Review state (post-wave-2, 19 pp — final-draft candidate)

Eleven passes total. Wave 1 (passes 1–6, commits "paper pass N"): the
strengthening queue, hostile referee, statistics referee + programmatic
number checker, arXiv/TeX Live compatibility, prose/terminology, clean-build
verification. Wave 2 (passes 7–11, commits "paper wave2 pass N"): structural
conventions, the reader's first 90 seconds, rendered figure inspection,
notation/consistency audit, and a full adversarial re-read.

## Current state

- **Build**: `make` — 19 pages, zero errors, zero undefined references, zero
  overfull boxes (the one 1.2 pt box introduced by the pass-11 table rename
  was removed with a local `\tabcolsep`). `make arxiv` re-run after wave 2:
  staged copy smoke-builds standalone, `dist/arxiv.tar.gz` packed.
- **Numbers**: `make check` — 233 assertions against research/*.json and the
  battery code's thresholds. PASSES. Four declared narrative-only skips.
  (Pass 11 renamed Table 5's tuned row to `FCVM+Q(λ_Q=0.05)`; the checker's
  row regex was updated in the same commit.)
- **Structure** (pass 7): narrative sections contiguous (results → structural
  claim → empirical counterpart → related work), Methods + a "Code and data
  availability" subsection as back matter; keywords block after the abstract.
  Considered and rejected: folding Methods into §2; moving more battery
  detail to the appendix (already split).
- **First 90 seconds** (pass 8): intro opens question-first (no literature in
  paragraph 1); Figure 1 lands atop page 2 and is cited from the opening
  paragraph; page 1 carries question, method novelty, and the
  joint-production result.
- **Figures** (pass 9): all six rendered at in-paper scale and inspected;
  fixed — F2 tick-label collision, F4 marker clipping + panel letters (a)–(d),
  F5 cohort-bar span, F6 text-hyphen minus. F1/F3 passed as-is.
- **Notation** (pass 10): every symbol now defined at first use (s_A, s,
  λ, D_t, f_mech = D^vol); eq:market labeled; every float and eq:stack
  cross-referenced; appendix σ_t tied to Table 1's σ_5d; terminology table
  judged unwarranted at this length.
- Byline remains a submission-time decision (in-repo stays authorless).

## Remaining items (severity-labeled)

Fixable only with new experiments or repo-side work — none blocks the draft:

1. **MEDIUM — DECA2 tuning-grid stats are narrative-sourced.** The §3
   mechanism numbers (AC1 −0.09→−0.35, kurt 8.8→4.6, 0.039 bits at kA=1)
   trace to the FINDINGS DECATHLON-2 narrative, not JSON fields; they are the
   checker's declared skips. Converting them needs a re-run of the grid with
   per-setting stat export.
2. **MEDIUM — the joint-10/10 calibration anchor is one index (SPY).**
   Scoped honestly in §2 (battery is comparative), but a referee may press
   for a second real asset scored 10/10; that is a new experiment and a
   re-registration.
3. **LOW — the one-layer E9 step is inside seed noise** (4–4 paired split).
   Disclosed wherever cited; resolving the sign needs more evaluation seeds
   under a new registration.
4. **LOW — no formal SE on a battery score.** Disclosed in §2; conclusions
   rest on paired kill criteria, not margins.
5. **LOW — FX–crypto edge (z = 1.44) uncertifiable at current history
   length.** Disclosed in §7 as an ordering of point estimates.
6. **LOW — caption.sty branch of the preamble untested locally** (TinyTeX
   exercises the kernel fallback); one build on full TeX Live before
   submission closes it.
7. **LOW — repo-side**: METHODS.md §8 says "37 gates"; the paper states the
   verifiable X1–X35. Reconcile METHODS (outside the paper).

## Readiness verdict

**Final-draft (owner-review-ready); no wave 3 warranted.** Every remaining
item above is either a new experiment (1–5) or a submission-time chore (6,
byline) — none is reachable by further prose passes, and further editing
risks churn without evidence. A wave 3 makes sense only if the owner elects
to run the new experiments (items 1–3) before submission.
