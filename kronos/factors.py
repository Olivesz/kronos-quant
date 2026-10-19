"""Survivorship-free factor portfolios (DESIGN29), hash-verified.

Ken French's factor files and AQR's daily BAB are archived in data/vendor/
(git-ignored; third-party files are not redistributed). data/vendor/MANIFEST.json
is committed and defines the data: French revises history, so a URL is not an
identity. Every loader hashes the file's bytes against the manifest before
parsing and fails closed on a mismatch. A missing file raises VendorUnavailable
so callers can say exactly what they could not check.

Returns are decimals (French publishes percent). French's CSVs are parsed with
float_precision="round_trip" (see kronos.data.FLOAT_PARSE); AQR's xlsx stores
shortest-repr decimal text, parsed by float(), which is correctly rounded.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pandas as pd

from kronos.data import FLOAT_PARSE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "data", "vendor")
MANIFEST = os.path.join(VENDOR, "MANIFEST.json")

FF3 = "F-F_Research_Data_Factors"
FF5 = "F-F_Research_Data_5_Factors_2x3"
MOM = "F-F_Momentum_Factor"
BAB = "Betting-Against-Beta-Equity-Factors-Daily.xlsx"


class VendorUnavailable(Exception):
    """A manifest-listed vendor file is not present in this checkout."""


def manifest_digest() -> str:
    """SHA-256 of MANIFEST.json's bytes: the identity of the whole input set."""
    with open(MANIFEST, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _verified_bytes(name: str) -> bytes:
    with open(MANIFEST) as fh:
        entry = json.load(fh)["files"].get(name)
    if entry is None:
        raise ValueError(f"{name} is not in {MANIFEST}")
    path = os.path.join(VENDOR, name)
    if not os.path.exists(path):
        raise VendorUnavailable(f"{name} missing from data/vendor/ (fetch {entry['url']})")
    with open(path, "rb") as fh:
        b = fh.read()
    got = hashlib.sha256(b).hexdigest()
    if got != entry["sha256"] or len(b) != entry["bytes"]:
        raise ValueError(f"{name}: sha256 {got[:16]}… does not match the manifest "
                         f"{entry['sha256'][:16]}… — a different vintage; refusing to parse")
    return b


def _french_first_table(name: str) -> pd.DataFrame:
    """The first table of a French CSV (monthly or daily), percent -> decimal.
    Monthly files carry a second, annual table after a blank line; it is not read."""
    zf = zipfile.ZipFile(io.BytesIO(_verified_bytes(name)))
    lines = zf.read(zf.namelist()[0]).decode("latin-1").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith(","))
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].strip()), len(lines))
    body = "\n".join(["date" + lines[start]] + lines[start + 1:end])
    df = pd.read_csv(io.StringIO(body), skipinitialspace=True, dtype={"date": str},
                     float_precision=FLOAT_PARSE)
    df.columns = [c.strip() for c in df.columns]
    d = df.pop("date").str.strip()
    if d.str.len().eq(8).all():
        idx = pd.to_datetime(d, format="%Y%m%d")
    elif d.str.len().eq(6).all():
        idx = pd.PeriodIndex(pd.to_datetime(d, format="%Y%m"), freq="M")
    else:
        raise ValueError(f"{name}: unrecognized date column")
    df.index = idx
    df = df.mask(df.isin([-99.99, -999.0])) / 100.0
    if df.index.has_duplicates or not df.index.is_monotonic_increasing:
        raise ValueError(f"{name}: dates not strictly increasing")
    return df.rename(columns={"Mom": "UMD"})


def french(freq: str = "daily") -> pd.DataFrame:
    """Mkt-RF, SMB, HML, RMW, CMA, UMD, RF on French's own calendar.
    RMW/CMA are NaN before 1963-07 and UMD before momentum begins."""
    suffix = "_daily_CSV.zip" if freq == "daily" else "_CSV.zip"
    ff3 = _french_first_table(FF3 + suffix)
    ff5 = _french_first_table(FF5 + suffix)
    mom = _french_first_table(MOM + suffix)
    # the FF5 file restates Mkt-RF/SMB/HML/RF from 1963; FF3's are the long ones
    out = ff3.join(ff5[["RMW", "CMA"]], how="left").join(mom[["UMD"]], how="left")
    return out[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "UMD", "RF"]]


_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _col(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def bab_daily(region: str = "USA") -> pd.Series:
    """AQR's daily BAB factor (self-financing excess return) for one region,
    read from the 'BAB Factors' sheet. A minimal OOXML reader: the repo has no
    spreadsheet dependency, and the sheet is a plain grid of shared-string
    dates and numeric cells. The XML is parsed only after its bytes match the
    manifest hash; stdlib ElementTree resolves no external entities, and
    expat >= 2.4 bounds entity amplification."""
    zf = zipfile.ZipFile(io.BytesIO(_verified_bytes(BAB)))
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid = next(s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
               for s in wb.iter(_NS + "sheet") if s.get("name") == "BAB Factors")
    target = next(r.get("Target") for r in rels if r.get("Id") == rid).lstrip("/")
    target = target if target.startswith("xl/") else "xl/" + target
    strings = ["".join(t.text or "" for t in si.iter(_NS + "t"))
               for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).iter(_NS + "si")]

    def value(c):
        v = c.find(_NS + "v")
        if v is None:
            return None
        return strings[int(v.text)] if c.get("t") == "s" else v.text

    date_col = val_col = None
    dates, vals = [], []
    for _, el in ET.iterparse(zf.open(target)):
        if el.tag != _NS + "row":
            continue
        cells = {_col(c.get("r")): value(c) for c in el.iter(_NS + "c")}
        if date_col is None:
            if "DATE" in cells.values():
                date_col = next(k for k, v in cells.items() if v == "DATE")
                val_col = next(k for k, v in cells.items() if v == region)
        else:
            d, x = cells.get(date_col), cells.get(val_col)
            if d is not None and x not in (None, ""):
                dates.append(d)
                vals.append(float(x))
        el.clear()
    if date_col is None:
        raise ValueError(f"{BAB}: header row with DATE/{region} not found")
    s = pd.Series(vals, index=pd.to_datetime(dates, format="%m/%d/%Y"), name="BAB")
    if s.index.has_duplicates or not s.index.is_monotonic_increasing:
        raise ValueError(f"{BAB}: dates not strictly increasing")
    return s


def monthly_rv(daily: pd.Series) -> pd.Series:
    """Moreira & Muir's RV²: the demeaned sum of squared daily returns within
    each calendar month, indexed by monthly Period."""
    s = daily.dropna()
    g = s.groupby(s.index.to_period("M"))
    return g.apply(lambda x: float(((x - x.mean()) ** 2).sum()))


def merge_saturdays(daily: pd.DataFrame) -> pd.DataFrame:
    """DESIGN29 Stage 2: compound each Saturday session into the next
    observation, so every observation spans one weekday close-to-close interval
    (a Monday then runs Friday close -> Monday close, as it does today)."""
    df = daily.copy()
    sat = df.index.dayofweek == 5
    if sat[-1]:
        raise ValueError("series ends on a Saturday session")
    grp = np.cumsum(np.r_[True, ~sat[:-1]])            # a Saturday joins the next row
    out = (1.0 + df).groupby(grp).prod(min_count=1) - 1.0
    out.index = df.index[~sat]
    return out
