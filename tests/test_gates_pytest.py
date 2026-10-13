"""pytest entry point: one test per gate in tests/run_all.py.

`pytest -q` runs every gate as its own item, in the same mode run_all.py
would (real prices by default, the synthetic market under KRONOS_SYNTHETIC=1),
and applies the same rule: outside hermetic mode a gate that prints SKIPPED
fails. run_all.py stays the canonical runner; this file only reuses its list.
"""
import ast
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
HERMETIC = os.environ.get("KRONOS_SYNTHETIC", "").lower() in ("1", "true", "yes")


def _gates():
    tree = ast.parse(open(os.path.join(HERE, "run_all.py")).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "GATES":
            return [elt.value for elt in node.value.elts]
    raise RuntimeError("GATES not found in run_all.py")


@pytest.mark.parametrize("gate", _gates())
def test_gate(gate):
    r = subprocess.run([sys.executable, os.path.join(HERE, gate)],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"{gate} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
    if not HERMETIC:
        skipped = [ln for ln in r.stdout.splitlines() if "SKIPPED" in ln]
        assert not skipped, f"{gate} skipped on real data: {skipped}"
