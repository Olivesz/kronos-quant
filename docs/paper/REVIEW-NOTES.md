# Review queue (draft v1, 16 pp — strengthening pass before submission)

Priority order (drafting agent's self-assessment, confirmed at integration):
1. **§7 triangle bridge** — most attackable inference; two table entries source
   to FINDINGS narrative, not JSON fields (promote those numbers into fx.json
   or soften the table).
2. **§9 related work** — add Brock–Hommes (JEDC 1998), Giardina–Bouchaud
   (2003), Challet–Zhang minority games, and the E9-adjacent efficiency
   literature; show the REFLEX/rough-vol gates rather than asserting.
3. **§2 battery thresholds** — appendix with exact calibrated pass criteria
   per event (E4's 0.12 bar lives only in DESIGN18 prose) + expanded SPY/GBM
   stat table.
Also: OUTLINE-vs-JSON rounding notes are in the tex `% src:` comments; byline
is a submission-time decision (in-repo stays authorless).

## Known limitations (referee pass — fixable only with new experiments)

1. **DECA2 tuning-grid stats are narrative-sourced.** `decathlon2.json`'s
   tuning block stores only scores; the §3 mechanism numbers (AC1 −0.09→−0.35,
   kurt 8.8→4.6, bits up to 0.039 at kA=1) trace to the FINDINGS DECATHLON-2
   narrative. Re-deriving them needs a re-run of the grid with per-setting
   stat export into the JSON (cheap, but it is a new run).
2. **The one-layer E9 step is inside seed noise.** K0→K1 median bits
   0.0184→0.0200, but the paired per-seed comparison splits 4–4 (the paper now
   says "unchanged, not reduced" at one layer; only the K=5 and full-skew
   rises are resolved, 7/8 paired seeds). Resolving the one-layer sign would
   need more evaluation seeds under a new registration.
3. **The joint-10/10 calibration anchor is one index (SPY).** Thresholds are
   multi-asset ranges, but scoring more real assets through the battery — and
   re-registering the calibration gate — is a new experiment. The paper now
   scopes the battery as comparative.
4. **No formal SE on a battery score.** Comparisons are paired (shared seeds)
   and conclusions rest on kill criteria, not one-event margins (now stated in
   §2); a seed bootstrap for score bands would be a new study.
5. **FX–crypto edge (z = 1.44) uncertifiable at current history length** —
   already honest in §7; needs longer crypto history, not a different test.
6. **Repo-doc discrepancy:** METHODS.md §8 says "37 gates"; grep over
   tests/+kronos/ finds X1–X35. Paper now states "X1–X35" (verifiable).
   Reconcile METHODS at some point.
