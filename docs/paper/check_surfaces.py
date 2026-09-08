"""Surface-agreement checker: every place a claim is ECHOED must agree with its source.

check_numbers.py asks "is this paper number derivable from research/*.json?" —
that is derivation. This asks the complementary question — propagation: the
gate count, experiment count, and shipped headline are each stated on several
surfaces (README badge and prose, CONTRIBUTING, METHODS, paper.tex, and the
GitHub repo description), and history shows they drift one surface at a time
when the source moves. Truths are read mechanically (AST of run_all.py /
run_research.py, research/momtilt.json), never from a remembered number.

Two frames, deliberately separate:
  LOCAL  — this working tree against its own truths. Any disagreement is a
           hard failure (exit 1), including DROPOUT: a surface that stops
           stating a claim at all is caught by the pinned assertion count,
           because the remaining surfaces still agree with each other.
  PUBLIC — the repo description (an API field no tracked file can see)
           against the PUBLIC artifact's own truths, via two read-only
           `gh api` GETs. Public drift is reported loudly but exits 0: it is
           only fixable by a push, and a permanently red check trains people
           to ignore it. Skipped under KRONOS_SYNTHETIC=1 (hermetic CI) or
           --local.

Patterns capture the number ADJACENT to its noun (e.g. `(\\d+) verification
gates`) — a windowed sweep around the noun once matched digits from a badge
URL's SVG path. Co-located is not attached.
"""
import ast
import base64
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO = "Olivesz/kronos-quant"

# Pinned totals, maintained like check_numbers.py's assertion count: if a
# surface legitimately stops echoing a claim, this constant moves in the same
# commit — silently losing an assertion is the dropout failure mode itself.
EXPECTED_LOCAL_ASSERTIONS = 26

MINUS = "−"  # README and paper use the true minus sign, not a hyphen


def truth_len_of_dict(path, name):
    tree = ast.parse(open(path).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
            if not isinstance(node.value, ast.Dict):
                sys.exit(f"FATAL: {name} in {path} is no longer a dict literal — teach check_surfaces.py the new shape")
            return len(node.value.keys)
    sys.exit(f"FATAL: no {name} assignment found in {path}")


def truth_len_of_list(path, name):
    tree = ast.parse(open(path).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
            if not isinstance(node.value, ast.List):
                sys.exit(f"FATAL: {name} in {path} is no longer a list literal — teach check_surfaces.py the new shape")
            return len(node.value.elts)
    sys.exit(f"FATAL: no {name} assignment found in {path}")


def fmt_row(r):
    """A research JSON row rendered at README-table display precision."""
    return {
        "cagr": f"+{r['cagr'] * 100:.1f}%",
        "vol": f"{r['vol'] * 100:.1f}%",
        "sharpe": f"{r['sharpe']:.2f}",
        "max_dd": f"{MINUS}{abs(r['max_dd']) * 100:.1f}%",
        "cvar95": f"{r['cvar95'] * 100:.2f}%",
    }


failures = []
n_checks = 0


def check(surface, label, ok, detail):
    global n_checks
    n_checks += 1
    status = "ok" if ok else "FAIL"
    print(f"  [{status}] {surface}: {label}" + ("" if ok else f" — {detail}"))
    if not ok:
        failures.append(f"{surface}: {label} — {detail}")


def count_and_values(text, pattern):
    return [m.groups() if len(m.groups()) > 1 else m.group(1) for m in re.finditer(pattern, text)]


def main():
    n_gates = truth_len_of_list(os.path.join(ROOT, "tests", "run_all.py"), "GATES")
    n_exps = truth_len_of_dict(os.path.join(ROOT, "run_research.py"), "EXPERIMENTS")
    mom = json.load(open(os.path.join(ROOT, "research", "momtilt.json")))
    shipped = fmt_row(mom["rows"]["shipped_tilted"])
    untilted = fmt_row(mom["rows"]["untilted_control"])

    print(f"truths: gates={n_gates} (tests/run_all.py), experiments={n_exps} (run_research.py), "
          f"headline={shipped['sharpe']} @ {shipped['max_dd']} (research/momtilt.json)")

    readme = open(os.path.join(ROOT, "README.md")).read()
    contributing = open(os.path.join(ROOT, "CONTRIBUTING.md")).read()
    methods = open(os.path.join(ROOT, "docs", "METHODS.md")).read()
    paper = open(os.path.join(ROOT, "docs", "paper", "paper.tex")).read()

    # ---- gates -------------------------------------------------------------
    hits = count_and_values(readme, r"gates-(\d+)%20passing")
    check("README", "gate badge", hits == [str(n_gates)], f"expected 1 badge at {n_gates}, saw {hits}")

    hits = count_and_values(readme, r"all (\d+) verification gates")
    check("README", "quickstart gate count", hits == [str(n_gates)], f"expected [{n_gates}], saw {hits}")

    hits = count_and_values(readme, r"(\d+) such gates run in")
    check("README", "discipline-paragraph gate count", hits == [str(n_gates)], f"expected [{n_gates}], saw {hits}")

    hits = count_and_values(readme, r"\*\*(\d+) verification gates\*\* — (\d+) proving")
    check("README", "highlights gate count", [h[0] for h in hits] == [str(n_gates)], f"expected [{n_gates}], saw {hits}")
    check("README", "highlights synthetic split", bool(hits) and hits[0][1] == str(n_gates - 2),
          f"expected {n_gates - 2} synthetic, saw {hits}")

    hits = count_and_values(readme, r"(\d+) gates \((\d+) synthetic ground truth \+ (\d+) real-data")
    check("README", "layout gate count", [h[0] for h in hits] == [str(n_gates)], f"expected [{n_gates}], saw {hits}")
    check("README", "layout synthetic split", bool(hits) and hits[0][1:] == (str(n_gates - 2), "2"),
          f"expected ({n_gates - 2}, 2), saw {hits}")

    hits = count_and_values(contributing, r"all (\d+) verification gates")
    check("CONTRIBUTING", "gate count", hits == [str(n_gates)], f"expected [{n_gates}], saw {hits}")

    hits = count_and_values(methods, r"(\d+) gates at this")
    check("METHODS", "gate count", hits == [str(n_gates)], f"expected [{n_gates}], saw {hits}")

    hits = count_and_values(paper, r"all (\d+) verification gates \(the numbered gates X1--X(\d+)")
    check("paper.tex", "gate count", [h[0] for h in hits] == [str(n_gates)], f"expected [{n_gates}], saw {hits}")
    check("paper.tex", "numbered-gate ceiling", bool(hits) and hits[0][1] == str(n_gates - 4),
          f"expected X{n_gates - 4} (four platform gates unnumbered), saw {hits}")

    # ---- experiments -------------------------------------------------------
    hits = count_and_values(readme, r"(\d+)\s+experiments ask what")
    check("README", "intro experiment count", hits == [str(n_exps)], f"expected [{n_exps}], saw {hits}")

    hits = count_and_values(readme, r"(\d+) research experiments, cached")
    check("README", "quickstart experiment count", hits == [str(n_exps)], f"expected [{n_exps}], saw {hits}")

    hits = count_and_values(readme, r"(\d+) experiments, pre-registered")
    check("README", "research-program experiment count", hits == [str(n_exps)], f"expected [{n_exps}], saw {hits}")

    # ---- shipped headline --------------------------------------------------
    hits = count_and_values(readme, rf"net Sharpe of ([\d.]+) at {MINUS}([\d.]+)% max drawdown")
    check("README", "prose headline Sharpe", bool(hits) and hits[0][0] == shipped["sharpe"],
          f"expected {shipped['sharpe']}, saw {hits}")
    check("README", "prose headline MaxDD", bool(hits) and MINUS + hits[0][1] + "%" == shipped["max_dd"],
          f"expected {shipped['max_dd']}, saw {hits}")

    for anchor, row, label in [
        (r"KRONOS \(\+ momentum tilt, shipped\)", shipped, "shipped row"),
        (r"KRONOS \(HAR lever \+ t-HMM regimes\)", untilted, "untilted-control row"),
    ]:
        m = re.search(rf"\| \**{anchor}\** \|(.+)\|", readme)
        cells = [c.strip().strip("*") for c in m.group(1).split("|")] if m else []
        for i, key in enumerate(["cagr", "vol", "sharpe", "max_dd", "cvar95"]):
            got = cells[i] if i < len(cells) else "<missing>"
            check("README", f"table {label} {key}", got == row[key], f"expected {row[key]}, saw {got}")

    # ---- pinned total (dropout guard) --------------------------------------
    if n_checks != EXPECTED_LOCAL_ASSERTIONS:
        failures.append(f"assertion count {n_checks} != pinned {EXPECTED_LOCAL_ASSERTIONS} "
                        "— a surface stopped (or started) stating a claim; re-pin deliberately")

    # ---- public frame ------------------------------------------------------
    if os.environ.get("KRONOS_SYNTHETIC") == "1" or "--local" in sys.argv:
        print("public frame: skipped (hermetic)")
    else:
        check_public(n_gates, n_exps, shipped)

    print("=" * 60)
    if failures:
        print(f"check_surfaces: {len(failures)} FAILURE(S)")
        for f in failures:
            print("  - " + f)
        sys.exit(1)
    print(f"check_surfaces: {n_checks} local surface assertions green")


def gh_get(args):
    r = subprocess.run(["gh", "api"] + args, capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def check_public(n_gates, n_exps, shipped):
    try:
        desc = gh_get([f"repos/{REPO}", "--jq", ".description"]).strip()
        pub = {}
        for path, name, kind in [("tests/run_all.py", "GATES", "list"),
                                 ("run_research.py", "EXPERIMENTS", "dict")]:
            raw = base64.b64decode(json.loads(gh_get([f"repos/{REPO}/contents/{path}"]))["content"])
            tree = ast.parse(raw.decode())
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
                    pub[name] = len(node.value.elts if kind == "list" else node.value.keys)
    except Exception as e:  # network, auth, rate limit — loud, never silent
        print(f"public frame: UNCHECKED ({e}) — description not verified this run")
        return

    drift = []
    d_gates = re.findall(r"(\d+)\s+(?:verification\s+)?gates", desc)
    d_exps = re.findall(r"(\d+)\s+(?:pre-registered\s+|research\s+)?experiments", desc)
    d_sharpe = re.findall(r"Sharpe\s+([\d.]+)", desc)
    d_dd = re.findall(rf"[{MINUS}-]\s?([\d.]+)%\s+max", desc)
    if not any([d_gates, d_exps, d_sharpe, d_dd]):
        print("public frame: description carries no volatile numbers — nothing to drift")
    else:
        for got, want, label in [
            (d_gates, str(pub.get("GATES", "?")), "gates vs public run_all.py"),
            (d_exps, str(pub.get("EXPERIMENTS", "?")), "experiments vs public run_research.py"),
            (d_sharpe, shipped["sharpe"], "Sharpe vs research/momtilt.json"),
            ([MINUS + d + "%" for d in d_dd], shipped["max_dd"], "MaxDD vs research/momtilt.json"),
        ]:
            if got and any(g != want for g in got):
                drift.append(f"description says {got}, truth {want} ({label})")
        if drift:
            print("public frame: PUBLIC SURFACE DRIFT — the description disagrees with the public artifact.")
            print("  Only a repo-settings edit fixes this; it must ride with the next push:")
            for d in drift:
                print("  - " + d)
        else:
            print(f"public frame: description agrees with the public artifact "
                  f"(gates={pub.get('GATES')}, experiments={pub.get('EXPERIMENTS')})")

    for name, local in [("GATES", n_gates), ("EXPERIMENTS", n_exps)]:
        if pub.get(name) not in (None, local):
            print(f"  PUSH NOTE: local {name.lower()} truth is {local}, public is {pub[name]} — "
                  "pushing stales every public echo; move the description in the same breath.")


if __name__ == "__main__":
    main()
