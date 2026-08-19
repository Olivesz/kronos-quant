# Review state (post-strengthening, 19 pp — submission-grade draft v2)

Six passes completed on top of draft v1 (one commit per pass, messages
"paper pass N: ..."): the strengthening queue, a hostile-referee pass, a
statistics-referee pass with a programmatic number checker, arXiv/TeX Live
compatibility, a prose/terminology pass, and a final clean-build
verification. Current state:

- **Build**: `make` (TinyTeX or any standard TeX Live; caption.sty used when
  present, kernel fallback otherwise; `\pdfoutput=1`; no shell-escape).
  19 pages, zero errors, zero undefined references, zero overfull boxes.
- **Numbers**: `make check` runs `check_numbers.py` — 233 assertions
  verifying every table row (scores, failed-event sets, statistics) and
  every derivable prose number against research/*.json and the battery
  code's thresholds. PASSES. Four declared narrative-only skips are printed
  by the script.
- **Submission tarball**: `make arxiv` stages tex+figures, smoke-builds the
  staged copy (two pdflatex passes, fails on undefined refs), and packs a
  pristine `dist/arxiv.tar.gz`.
- **Terminology**: primary term is "the sign leak", defined once in §2 as a
  significant excess of E9's direction-bits statistic over its shuffle null.
- **Abstract**: 1566 chars (arXiv limit ~1920). Title unchanged.
- Byline remains a submission-time decision (in-repo stays authorless).

## Resolved from the v1 queue

1. §7 triangle: the two narrative-sourced z-values are now DERIVED from
   stored JSON fields (equity_mean/equity_spread = −5.1;
   crypto_leverage/crypto_sd = 1.97) and asserted by check_numbers.py.
2. §9 related work: added Brock–Hommes 1998, Challet–Zhang 1997,
   Giardina–Bouchaud 2003, Samuelson 1965, Fama 1970, Grossman–Stiglitz 1980
   (plus Black 1976 and Bekaert–Wu 2000 in §7 as the classical equity-side
   explanations the cross-venue design discriminates against).
3. §2 appendix: exact per-event thresholds as implemented (cited to
   kronos/decathlon.py) + full SPY/GBM/FCVM statistic table from
   decathlon.json. Fixed en route: E9's estimator was misattributed as KSG
   (it is discrete plug-in MI with Miller–Madow correction; KSG is the
   program's continuous channel), and Table 1's E8 wording now matches the
   implemented ratio criterion.

## Known limitations (referee pass — fixable only with new experiments)

1. **DECA2 tuning-grid stats are narrative-sourced.** `decathlon2.json`'s
   tuning block stores only scores; the §3 mechanism numbers (AC1 −0.09→−0.35,
   kurt 8.8→4.6, bits up to 0.039 at kA=1) trace to the FINDINGS DECATHLON-2
   narrative. Re-deriving them needs a re-run of the grid with per-setting
   stat export into the JSON (cheap, but it is a new run).
2. **The one-layer E9 step is inside seed noise.** K0→K1 median bits
   0.0184→0.0200, but the paired per-seed comparison splits 4–4 (the paper
   says "unchanged, not reduced" at one layer; only the K=5 and full-skew
   rises are resolved, 7/8 paired seeds). Resolving the one-layer sign would
   need more evaluation seeds under a new registration.
3. **The joint-10/10 calibration anchor is one index (SPY).** Thresholds are
   multi-asset ranges, but scoring more real assets through the battery — and
   re-registering the calibration gate — is a new experiment. The paper
   scopes the battery as comparative (§2).
4. **No formal SE on a battery score.** Comparisons are paired (shared seeds)
   and conclusions rest on kill criteria, not one-event margins (stated in
   §2); a seed bootstrap for score bands would be a new study.
5. **FX–crypto edge (z = 1.44) uncertifiable at current history length** —
   honest in §7; needs longer crypto history, not a different test.

## What a future session might still improve

- The caption.sty branch of the preamble is untested locally (TinyTeX lacks
  the package, so local builds exercise the fallback); options used are
  bog-standard (`font=small,labelfont=bf,labelsep=period`), but a one-time
  build on full TeX Live before submission would close the loop.
- METHODS.md §8 says "37 gates"; grep over tests/+kronos/ finds X1–X35. The
  paper states "X1–X35" (verifiable); reconcile METHODS.
- decathlon2.json could be enriched with per-setting tuning-grid stats
  (limitation 1 above), converting the last narrative-sourced §3 numbers to
  JSON-backed and shrinking check_numbers.py's skip list.
- Optional: an ISO byline/abstract block at submission time (owner's call).
