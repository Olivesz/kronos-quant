# Contributing to KRONOS

KRONOS is a research platform. Its defining discipline is that **every
estimator is validated against synthetic ground truth before it is allowed to
touch real market data.** Contributions are welcome as long as they hold that
line.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[data]"      # or: pip install -r requirements.txt
python tests/run_all.py       # all verification gates (~75s)
```

To run fully offline (no Yahoo Finance), set `KRONOS_SYNTHETIC=1` — the whole
platform runs on a seeded synthetic regime-switching market. This is exactly
what CI does.

## The one rule: gate before you claim

Any new estimator, model, or statistical test must ship with a **gate** in
`tests/` that proves it works on data where the answer is known, *before* any
result on real data is reported. Concretely, a good gate demonstrates both:

- **Size / exoneration** — on a world where the effect is absent, the test
  does not fire (controls the false-positive rate).
- **Power / conviction** — on a world where the effect is present by
  construction, the test detects it.

See `tests/test_critical.py` (fold-bifurcation vs shock worlds) or
`tests/test_transfer.py` (same-mechanism vs different-mechanism worlds) for the
pattern. A finding without a gate is not a finding.

## Style

- Pure `numpy` / `pandas` / `scipy`. New heavyweight dependencies need a strong
  justification — the point of the project is that the models are transparent
  and hand-built.
- Strictly causal: no look-ahead. Filtered (not smoothed) probabilities, frozen
  betas, walk-forward refits, T+1 execution. If a change could leak the future,
  it needs a causality gate (see `tests/test_trade.py`).
- Report negative results as prominently as positive ones. The project's
  credibility rests on it.
- `ruff check .` should pass (config in `pyproject.toml`).

## Adding a research experiment

1. Write the pre-registration in `docs/design/DESIGN<n>.md` — the hypotheses
   and the kill criteria — *before* coding.
2. Implement the estimator in a `kronos/` module.
3. Add its gate in `tests/` and register it in `tests/run_all.py`.
4. Wire it into `run_research.py` (cached to `research/<name>.json`).
5. Optionally add a panel to `kronos/dashboard.py`.
6. Add a row to the research index in `docs/README.md`.
