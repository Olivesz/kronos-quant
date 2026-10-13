"""Data layer: the committed price snapshot, an explicit Yahoo refresh path,
and a hermetic synthetic market.

Sources, in the only order they are ever chosen:
  KRONOS_SYNTHETIC=1   seeded synthetic market (CI's hermetic job; labeled)
  default ("pinned")   live/genesis/*.csv.gz, digest-verified against META.json
                       — every headline number is computed from this file
  KRONOS_DATA=yahoo    cache / fresh Yahoo download (drifts with dividend
                       re-adjustments; for refreshing, not for reproducing)
A failed real-data load RAISES; nothing silently substitutes synthetic data.
All paths emit a clean (date x ticker) DataFrame with no NaNs.
"""
from __future__ import annotations

import hashlib
import io
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(ROOT, "data", "cache")
PINNED_DIR = os.path.join(ROOT, "live", "genesis")
OHLC_FIELDS = ("open", "high", "low", "close")


class DataUnavailable(RuntimeError):
    """A real-data load failed. Raised instead of falling back to synthetic."""


# ----------------------------------------------------------------------------
# Real data path
# ----------------------------------------------------------------------------

def _cache_path(start: str, end: str) -> str:
    return os.path.join(CACHE_DIR, f"prices_{start}_{end}.csv")


def _normalize_yf(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Flatten yfinance output (single- or multi-ticker) to (date x ticker) closes."""
    if isinstance(raw.columns, pd.MultiIndex):
        level0 = raw.columns.get_level_values(0)
        if "Close" in level0:
            px = raw["Close"]
        else:  # ticker-first layout
            px = raw.xs("Close", axis=1, level=1)
    else:
        px = raw[["Close"]]
        px.columns = tickers[:1]
    return px


def fetch_yahoo(tickers: list[str], start: str, end: str) -> pd.DataFrame | None:
    try:
        import yfinance as yf
        raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                          progress=False, threads=True)
        if raw is None or len(raw) < 500:
            return None
        px = _normalize_yf(raw, tickers)
        px.index = pd.to_datetime(px.index).tz_localize(None)
        return px
    except Exception:
        return None


# ----------------------------------------------------------------------------
# Synthetic fallback: regime-switching multivariate market
# ----------------------------------------------------------------------------

# (annualized drift, annualized vol, expected regime length in days)
_SYN_REGIMES = [
    (0.14, 0.11, 180),   # bull
    (0.02, 0.22, 45),    # volatile
    (-0.25, 0.38, 30),   # bear
]

_SECTORS = {  # crude sector map for factor structure
    "tech": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "CRM", "ADBE", "INTC",
             "CSCO", "ORCL", "QQQ", "XLK", "AMZN", "NFLX"],
    "fin": ["JPM", "BAC", "GS", "XLF"],
    "health": ["UNH", "JNJ", "PFE"],
    "energy": ["XOM", "CVX", "XLE"],
    "indus": ["CAT", "HON", "BA", "FDX", "UPS"],
    "staples": ["WMT", "PG", "KO", "PEP", "MCD", "HD", "DIS"],
    "telecom": ["T", "VZ"],
    "util": ["NEE", "DUK", "XLU", "LIN"],
    "broad": ["SPY", "IWM", "DIA"],
    "defensive": ["GLD", "TLT", "HYG", "LQD"],
}


def generate_synthetic(tickers: list[str], start: str, end: str, seed: int) -> pd.DataFrame:
    """Regime-switching factor model: market + sector + idiosyncratic returns.

    Produces fat tails, vol clustering and regime shifts so every downstream
    model has real structure to find.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    T = len(dates)

    # Markov chain over regimes
    P = np.zeros((3, 3))
    for i, (_, _, dur) in enumerate(_SYN_REGIMES):
        stay = 1 - 1 / dur
        P[i] = (1 - stay) / 2
        P[i, i] = stay
    states = np.zeros(T, dtype=int)
    for t in range(1, T):
        states[t] = rng.choice(3, p=P[states[t - 1]])

    mu_d = np.array([m / 252 for m, _, _ in _SYN_REGIMES])[states]
    sig_d = np.array([s / np.sqrt(252) for _, s, _ in _SYN_REGIMES])[states]
    # market factor with Student-t innovations (fat tails)
    mkt = mu_d + sig_d * rng.standard_t(df=5, size=T) / np.sqrt(5 / 3)

    sector_of = {}
    for sec, names in _SECTORS.items():
        for n in names:
            sector_of[n] = sec
    sec_shocks = {sec: rng.normal(0, 0.004, T) for sec in _SECTORS}

    cols = {}
    for tk in tickers:
        sec = sector_of.get(tk, "broad")
        if tk in ("GLD", "TLT", "LQD"):
            beta = rng.uniform(-0.25, 0.1)
        elif tk in ("HYG",):
            beta = 0.4
        elif sec in ("staples", "util", "telecom"):
            beta = rng.uniform(0.5, 0.8)
        elif sec == "tech":
            beta = rng.uniform(1.1, 1.5)
        else:
            beta = rng.uniform(0.8, 1.2)
        idio = rng.normal(0, rng.uniform(0.006, 0.014), T)
        drift = rng.normal(0.00015, 0.0001)
        r = drift + beta * mkt + sec_shocks[sec] + idio
        cols[tk] = 100 * np.exp(np.cumsum(r))

    px = pd.DataFrame(cols, index=dates)
    # make the market proxy nearly the pure market factor
    if "SPY" in tickers:
        px["SPY"] = 100 * np.exp(np.cumsum(mkt + rng.normal(0, 0.0005, T)))
    return px


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def clean_panel(px: pd.DataFrame, min_coverage: float, max_ffill: int) -> pd.DataFrame:
    cov = px.notna().mean()
    px = px.loc[:, cov >= min_coverage]
    px = px.ffill(limit=max_ffill)
    px = px.dropna(axis=0, how="any")
    # clip absurd single-day moves (bad ticks); >60% daily on this universe is data error
    rets = px.pct_change()
    bad = rets.abs() > 0.60
    if bad.to_numpy().any():
        rets = rets.where(~bad, 0.0).fillna(0.0)
        px = (1 + rets).cumprod().mul(px.iloc[0], axis=1)
    return px


def _force_synthetic() -> bool:
    """CI / offline hermetic mode: KRONOS_SYNTHETIC=1 skips cache and Yahoo and
    runs the whole platform on the seeded synthetic market (deterministic,
    network-free). Used by CI so the gates never depend on a live data feed."""
    return os.environ.get("KRONOS_SYNTHETIC", "").lower() in ("1", "true", "yes")


def _data_mode() -> str:
    mode = os.environ.get("KRONOS_DATA", "pinned").lower()
    if mode not in ("pinned", "yahoo"):
        raise ValueError(f"KRONOS_DATA must be 'pinned' or 'yahoo', got {mode!r}")
    return mode


def pinned_digest(df: pd.DataFrame) -> str:
    """Same convention as kronos/live.py: sha256 of the raw float64 buffer."""
    return hashlib.sha256(df.to_numpy().tobytes()).hexdigest()[:16]


MANIFEST_PATH = os.path.join(ROOT, "data", "pinned_manifest.json")
SPAN_SLACK_DAYS = 7          # cfg.start/end may sit on a non-trading day


def _read_manifest(path: str = MANIFEST_PATH) -> dict:
    if not os.path.exists(path):
        raise DataUnavailable(f"pinned manifest missing: {path}")
    with open(path) as fh:
        return json.load(fh)


def load_pinned_ohlc(fields=OHLC_FIELDS, pinned_dir: str = PINNED_DIR,
                     manifest_path: str = MANIFEST_PATH) -> dict:
    """The committed snapshot. Every requested file is checked against the
    manifest's SHA-256 of its exact bytes BEFORE it is parsed (covers dates,
    tickers and values of all four fields), and the parsed close panel is
    additionally checked against META.json's value digest."""
    man = _read_manifest(manifest_path)
    out = {}
    for f in fields:
        name = f"{f}.csv.gz"
        path = os.path.join(pinned_dir, name)
        if name not in man["sha256"]:
            raise DataUnavailable(f"no manifest hash for {name}")
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError as e:
            raise DataUnavailable(f"pinned snapshot unreadable: {path}: {e}") from e
        got = hashlib.sha256(raw).hexdigest()
        if got != man["sha256"][name]:
            raise DataUnavailable(f"pinned snapshot modified: sha256({name}) = "
                                  f"{got[:16]}… != manifest "
                                  f"{man['sha256'][name][:16]}…")
        out[f] = pd.read_csv(io.BytesIO(raw), compression="gzip",
                             index_col=0, parse_dates=True)
    if "close" in out:
        with open(os.path.join(pinned_dir, "META.json")) as fh:
            meta = json.load(fh)
        if pinned_digest(out["close"]) != meta["close_digest"]:
            raise DataUnavailable("pinned close panel disagrees with META.json")
    return out


def _pinned_window(df: pd.DataFrame, cfg,
                   manifest_path: str = MANIFEST_PATH) -> pd.DataFrame:
    """Restrict to cfg's universe and span — refusing, never truncating, when
    the snapshot cannot serve the request."""
    man = _read_manifest(manifest_path)
    excluded = set(man.get("excluded_tickers", {}))
    missing = [t for t in cfg.universe if t not in df.columns and t not in excluded]
    if missing:
        raise DataUnavailable(f"pinned snapshot lacks requested tickers {missing}; "
                              "use KRONOS_DATA=yahoo for other universes")
    lo, hi = pd.Timestamp(cfg.start), pd.Timestamp(cfg.end)
    slack = pd.Timedelta(days=SPAN_SLACK_DAYS)
    if lo < df.index[0] - slack or hi > df.index[-1] + slack:
        raise DataUnavailable(f"requested span {cfg.start}..{cfg.end} exceeds the "
                              f"pinned snapshot {df.index[0].date()}..{df.index[-1].date()}")
    cols = [c for c in df.columns if c in set(cfg.universe)]
    return df.loc[lo:hi, cols]


def load_prices(cfg) -> tuple[pd.DataFrame, str]:
    """Returns (prices, source); source is 'pinned', 'yahoo' or 'synthetic'."""
    if _force_synthetic():
        px = generate_synthetic(cfg.universe, cfg.start, cfg.end, cfg.seed)
        return clean_panel(px, cfg.min_coverage, cfg.max_ffill_days), "synthetic"
    if _data_mode() == "pinned":
        close = load_pinned_ohlc(("close",))["close"]
        return clean_panel(_pinned_window(close, cfg), cfg.min_coverage,
                           cfg.max_ffill_days), "pinned"
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = _cache_path(cfg.start, cfg.end)
    if os.path.exists(cache):
        px = pd.read_csv(cache, index_col=0, parse_dates=True)
        return clean_panel(px, cfg.min_coverage, cfg.max_ffill_days), "yahoo"
    px = fetch_yahoo(cfg.universe, cfg.start, cfg.end)
    if px is not None and px.notna().mean().mean() > 0.80 and len(px) > 1000:
        px.to_csv(cache)
        return clean_panel(px, cfg.min_coverage, cfg.max_ffill_days), "yahoo"
    raise DataUnavailable("Yahoo download failed or was too sparse; refusing to "
                          "substitute synthetic data (set KRONOS_SYNTHETIC=1 to "
                          "run on the synthetic market deliberately)")


def is_real(src: str) -> bool:
    """True for real-market sources (pinned snapshot or Yahoo)."""
    return src in ("pinned", "yahoo")


# ----------------------------------------------------------------------------
# OHLC for range-based volatility estimators (KRONOS-X)
# ----------------------------------------------------------------------------

def fetch_yahoo_ohlc(tickers: list[str], start: str, end: str) -> dict | None:
    try:
        import yfinance as yf
        raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                          progress=False, threads=True)
        if raw is None or len(raw) < 500 or not isinstance(raw.columns, pd.MultiIndex):
            return None
        out = {}
        for field in ("Open", "High", "Low", "Close"):
            df = raw[field] if field in raw.columns.get_level_values(0) \
                else raw.xs(field, axis=1, level=1)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            out[field.lower()] = df
        return out
    except Exception:
        return None


def load_ohlc(cfg) -> tuple[dict, str]:
    """Returns ({open,high,low,close}, source) from the same source rules as
    load_prices (pinned by default; Yahoo only on request; never a silent
    synthetic fallback)."""
    if _force_synthetic():
        return _synthetic_ohlc(cfg), "synthetic"
    if _data_mode() == "pinned":
        raw = load_pinned_ohlc()
        return {f: _pinned_window(v, cfg) for f, v in raw.items()}, "pinned"
    os.makedirs(CACHE_DIR, exist_ok=True)
    paths = {f: os.path.join(CACHE_DIR, f"ohlc_{f}_{cfg.start}_{cfg.end}.csv")
             for f in OHLC_FIELDS}
    if all(os.path.exists(p) for p in paths.values()):
        out = {f: pd.read_csv(p, index_col=0, parse_dates=True)
               for f, p in paths.items()}
        return out, "yahoo"
    out = fetch_yahoo_ohlc(cfg.universe, cfg.start, cfg.end)
    if out is not None:
        for f, p in paths.items():
            out[f].to_csv(p)
        return out, "yahoo"
    raise DataUnavailable("Yahoo OHLC download failed; refusing to substitute "
                          "synthetic data")


def _synthetic_ohlc(cfg) -> dict:
    """Plausible OHLC built around the seeded synthetic closes."""
    c = generate_synthetic(cfg.universe, cfg.start, cfg.end, cfg.seed)
    rng = np.random.default_rng(cfg.seed + 1)
    o = c.shift(1) * np.exp(rng.normal(0, 0.003, c.shape))
    span = np.abs(rng.normal(0, 0.008, c.shape)) + 0.002
    h = np.maximum(o, c) * (1 + span / 2)
    low = np.minimum(o, c) * (1 - span / 2)
    return {"open": o, "high": h, "low": low, "close": c}
