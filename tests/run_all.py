"""Run every KRONOS verification gate in sequence."""
import subprocess, sys, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
# Use the interpreter that launched this runner (works in the project .venv,
# in CI, and anywhere the deps are importable) rather than a hardcoded path.
PY = sys.executable
GATES = [
    # v1 platform gates
    "test_regime.py", "test_signals_pairs.py", "test_portfolio.py", "test_backtest.py",
    # KRONOS-X research gates
    "test_volest.py", "test_sjm.py", "test_dhmm.py", "test_vollab.py",
    "test_rough.py", "test_rmt.py", "test_statarb.py", "test_cvar.py",
    "test_ensemble.py", "test_forensics.py",
    # KRONOS-X² gates
    "test_thmm.py", "test_infer.py", "test_rfsv.py",
    # KRONOS-X² K-hallucination study (tails.py)
    "test_tails.py",
    # KRONOS-LAWS gates
    "test_laws.py", "test_clock.py", "test_surge.py",
    # KRONOS-BITS gates
    "test_infobudget.py", "test_entropyprod.py",
    # KRONOS-DECATHLON gate
    "test_decathlon.py",
    # KRONOS-CRITICAL gate
    "test_critical.py",
    # KRONOS-REFLEX gate
    "test_reflex.py",
    # KRONOS-CONSTANTS gate
    "test_constants.py",
    # KRONOS-TRADE gate
    "test_trade.py",
    # KRONOS-TRANSFER gate
    "test_transfer.py",
]

print("=" * 60)
print("KRONOS verification gates")
print("=" * 60)
t0 = time.time()
failed = []
for g in GATES:
    print(f"\n>>> {g}")
    r = subprocess.run([PY, os.path.join(HERE, g)], capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stdout.write(r.stderr)
        failed.append(g)

print("\n" + "=" * 60)
if failed:
    print(f"FAILED: {failed}")
    sys.exit(1)
print(f"ALL GATES PASSED in {time.time()-t0:.0f}s")
