"""Gate X39: the pinned price snapshot is verified, complete, and fail-closed.

Every real-data number in the repo reads live/genesis/*.csv.gz through
kronos.data.load_pinned_ohlc. This gate attacks a scratch copy of the
snapshot and requires a loud DataUnavailable for each attack:
  (a) intact snapshot loads, all four fields, and matches META.json;
  (b) one byte changed in ANY of the four files -> refused (all fields are
      verified, not just close);
  (c) two ticker columns relabeled with values untouched -> refused, and the
      values-only META digest is shown to be blind to it (why the manifest
      hashes file bytes);
  (d) a dropped trading day (dates shifted) -> refused;
  (e) a ticker outside the snapshot and the exclusion list -> refused; a span
      beyond the snapshot -> refused (never silently truncated);
  (f) the documented exclusion (META, below min_coverage) is allowed;
  (g) the transfer study's foreign panels (data/pinned/) load verified, and a
      flipped byte in one is refused.
Runs from committed files only, so it runs identically in the hermetic job.
"""
import os
import shutil
import sys
import tempfile
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from config import CFG
from kronos.data import (MANIFEST_PATH, PINNED_DIR, DataUnavailable,
                         _pinned_window, load_pinned_ohlc, pinned_digest)


def refused(fn, label):
    try:
        fn()
    except DataUnavailable as e:
        print(f"  refused ({label}): {str(e)[:90]}")
        return True
    raise AssertionError(f"NOT refused: {label}")


tmp = tempfile.mkdtemp(prefix="kronos_x39_")
try:
    def fresh():
        d = os.path.join(tmp, "g")
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(PINNED_DIR, d)
        return d

    # (a) intact
    ohlc = load_pinned_ohlc()
    assert set(ohlc) == {"open", "high", "low", "close"}
    shapes = {f: v.shape for f, v in ohlc.items()}
    assert len(set(shapes.values())) == 1, f"field shapes differ: {shapes}"
    print(f"X39a intact: 4 fields {shapes['close']}, file hashes + META digest verified")

    # (b) one byte in each file
    for f in ("open", "high", "low", "close"):
        d = fresh()
        path = os.path.join(d, f"{f}.csv.gz")
        raw = bytearray(open(path, "rb").read())
        raw[len(raw) // 2] ^= 0x01
        open(path, "wb").write(bytes(raw))
        refused(lambda: load_pinned_ohlc((f,), pinned_dir=d), f"byte flip in {f}")
    print("X39b every field verified: a one-byte change in any file is refused")

    # (c) relabel two tickers, values untouched
    d = fresh()
    close = pd.read_csv(os.path.join(d, "close.csv.gz"), index_col=0, parse_dates=True)
    a, b = close.columns[0], close.columns[1]
    swapped = close.rename(columns={a: b, b: a})
    assert pinned_digest(swapped) == pinned_digest(close), \
        "precondition: the values-only digest should be blind to relabeling"
    swapped.to_csv(os.path.join(d, "close.csv.gz"), compression="gzip")
    refused(lambda: load_pinned_ohlc(("close",), pinned_dir=d), f"{a}<->{b} relabel")
    print(f"X39c relabel {a}<->{b}: values-only digest passes it, file hash refuses it")

    # (d) a dropped trading day (dates shift against values)
    d = fresh()
    c2 = close.drop(close.index[2000])
    c2.to_csv(os.path.join(d, "close.csv.gz"), compression="gzip")
    refused(lambda: load_pinned_ohlc(("close",), pinned_dir=d), "dropped day")
    print("X39d a dropped trading day is refused")

    # (e) fail-closed on requests the snapshot cannot serve
    full = ohlc["close"]
    refused(lambda: _pinned_window(full, replace(CFG, universe=list(CFG.universe) + ["TSLA"])),
            "ticker outside snapshot")
    refused(lambda: _pinned_window(full, replace(CFG, end="2026-12-31")), "span beyond snapshot")
    refused(lambda: _pinned_window(full, replace(CFG, start="2005-01-01")), "span before snapshot")
    print("X39e unserveable tickers/spans are refused, never truncated")

    # (f) the documented exclusion is the only tolerated gap
    win = _pinned_window(full, CFG)
    assert "META" in CFG.universe and "META" not in win.columns
    assert win.shape[1] == len(CFG.universe) - 1
    print(f"X39f documented exclusion only: {win.shape[1]} of {len(CFG.universe)} "
          f"universe tickers served (META excluded per {os.path.basename(MANIFEST_PATH)})")
    # (g) the transfer study's foreign panels (data/pinned/) under the same rule
    import json
    from kronos.data import PINNED_EXTRA_DIR, load_pinned_panel
    with open(os.path.join(PINNED_EXTRA_DIR, "MANIFEST.json")) as fh:
        extra = sorted(json.load(fh)["files"])
    for name in extra:
        df = load_pinned_panel(name)
        assert len(df) > 1000 and df.shape[1] >= 10, f"{name} too small: {df.shape}"
    d = os.path.join(tmp, "extra")
    shutil.copytree(PINNED_EXTRA_DIR, d)
    victim = os.path.join(d, extra[0])
    raw = bytearray(open(victim, "rb").read())
    raw[len(raw) // 3] ^= 0x01
    open(victim, "wb").write(bytes(raw))
    refused(lambda: load_pinned_panel(extra[0], pinned_dir=d), f"byte flip in {extra[0]}")
    print(f"X39g {len(extra)} foreign transfer panels verified; a flipped byte is refused")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("GATE X39 PASSED")
