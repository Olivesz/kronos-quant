"""DESIGN29 Stage 4: the shipped overlay traded on SPY in a broker paper
account, so every decision, order and fill carries a third-party timestamp.

The account and its keys belong to the owner. They arrive only through the
environment (ALPACA_PAPER_KEY_ID, ALPACA_PAPER_SECRET_KEY), are sent only as
request headers to Alpaca's paper endpoints, and are never logged or written.
The client refuses any base URL other than the paper trading host.

Each run, after the US close:
  1. record fills of earlier orders (the broker's own filled_at timestamps);
  2. read SPY's adjusted daily closes from the broker's data API;
  3. decide tomorrow's exposure with the shipped overlay (kronos.risk
     .exposure_series, shipped CFG, tilt on SPY's 21-day log return);
  4. size a whole-share market-on-open order toward exposure × equity,
     skipping changes smaller than NO_TRADE_BAND of equity;
  5. append one row to live/paper_ledger.jsonl.
The model's return for day t+1 is close-to-close; the paper account fills at
t+1's open. The overnight gap is part of what this check measures.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from kronos.risk import exposure_series
from kronos.volalpha import tilt_series

PAPER_BASE = "https://paper-api.alpaca.markets"
DATA_BASE = "https://data.alpaca.markets"
SYMBOL = "SPY"
NO_TRADE_BAND = 0.005          # of equity
HISTORY_DAYS = 6 * 365         # HAR, CVaR and drawdown windows need ~2y; take 6


def next_exposure(closes: pd.Series, cfg) -> float:
    """The exposure the shipped overlay decides at the last close, to apply
    to the next day: exposure_series on the daily total return (adjusted
    closes), tilt on the 21-day log return, as in the shipped backtest."""
    r = closes.pct_change().dropna()
    tilt = tilt_series(np.log1p(r), getattr(cfg, "mom_tilt", 0.0))
    return float(exposure_series(r, cfg, tilt=tilt)["exposure"].iloc[-1])


def order_for(exposure: float, equity: float, price: float, shares_held: float) -> dict | None:
    """Whole-share order moving the position toward exposure × equity, or None
    inside the no-trade band."""
    target = int(np.floor(exposure * equity / price))
    delta = target - shares_held
    if abs(delta) * price < NO_TRADE_BAND * equity or delta == 0:
        return None
    return {"side": "buy" if delta > 0 else "sell", "qty": int(abs(delta)), "target_shares": target}


class AlpacaPaper:
    """Minimal REST client for Alpaca's paper trading and market-data APIs."""

    def __init__(self, key_id: str, secret: str, base: str = PAPER_BASE,
                 opener=urllib.request.urlopen):
        if base != PAPER_BASE:
            raise ValueError(f"refusing {base!r}: this client trades the paper account only")
        if not key_id or not secret:
            raise ValueError("paper key id and secret are required")
        self._headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret,
                         "Accept": "application/json"}
        self._open = opener

    def _req(self, method: str, url: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        headers = dict(self._headers, **({"Content-Type": "application/json"} if body else {}))
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        with self._open(req, timeout=30) as resp:
            return json.loads(resp.read().decode() or "null")

    def daily_closes(self, symbol: str = SYMBOL, feed: str = "iex",
                     start: str | None = None) -> pd.Series:
        start = start or (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
        out, token = [], None
        while True:
            q = {"timeframe": "1Day", "start": start, "adjustment": "all", "feed": feed, "limit": 10000}
            if token:
                q["page_token"] = token
            page = self._req("GET", f"{DATA_BASE}/v2/stocks/{symbol}/bars?" + urllib.parse.urlencode(q))
            out += page.get("bars") or []
            token = page.get("next_page_token")
            if not token:
                break
        if not out:
            raise RuntimeError(f"no {symbol} bars returned")
        s = pd.Series([b["c"] for b in out],
                      index=pd.to_datetime([b["t"] for b in out]).tz_convert("America/New_York").normalize()
                      .tz_localize(None), name=symbol)
        if s.index.has_duplicates or not s.index.is_monotonic_increasing:
            raise RuntimeError("bars not strictly increasing")
        return s

    def equity(self) -> float:
        return float(self._req("GET", f"{PAPER_BASE}/v2/account")["equity"])

    def shares_held(self, symbol: str = SYMBOL) -> float:
        try:
            return float(self._req("GET", f"{PAPER_BASE}/v2/positions/{symbol}")["qty"])
        except urllib.error.HTTPError as e:
            if e.code == 404:                     # no open position
                return 0.0
            raise

    def submit_opg(self, symbol: str, side: str, qty: int, client_id: str) -> dict:
        return self._req("POST", f"{PAPER_BASE}/v2/orders",
                         {"symbol": symbol, "qty": str(qty), "side": side, "type": "market",
                          "time_in_force": "opg", "client_order_id": client_id})

    def order(self, order_id: str) -> dict:
        return self._req("GET", f"{PAPER_BASE}/v2/orders/{order_id}")


def ledger_rows(path: str) -> list[dict]:
    try:
        with open(path) as fh:
            return [json.loads(line) for line in fh if line.strip()]
    except FileNotFoundError:
        return []


def run(client: AlpacaPaper, cfg, ledger_path: str, submit: bool, feed: str = "iex") -> dict:
    """One daily step. With submit=False nothing is posted to the broker and
    nothing is written; the row that would be appended is returned."""
    rows = ledger_rows(ledger_path)
    recorded = {f["order_id"] for r in rows for f in r.get("fills_recorded", [])}
    fills = []
    for r in rows:
        o = r.get("order")
        if o and o["id"] not in recorded:
            got = client.order(o["id"])
            if got.get("filled_at"):
                fills.append({"order_id": o["id"], "for_as_of": r["as_of"], "filled_at": got["filled_at"],
                              "filled_qty": got.get("filled_qty"), "filled_avg_price": got.get("filled_avg_price"),
                              "status": got.get("status")})
            elif got.get("status") in ("canceled", "expired", "rejected"):
                fills.append({"order_id": o["id"], "for_as_of": r["as_of"], "filled_at": None,
                              "status": got.get("status")})
    closes = client.daily_closes(feed=feed)
    as_of = str(closes.index[-1].date())
    if rows and rows[-1]["as_of"] == as_of:
        return {"skipped": f"already decided for {as_of}"}
    e = next_exposure(closes, cfg)
    eq, held, px = client.equity(), client.shares_held(), float(closes.iloc[-1])
    plan = order_for(e, eq, px, held)
    row = {"as_of": as_of, "decided_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "exposure": e, "close": px, "equity": eq, "shares_held": held, "feed": feed,
           "plan": plan, "order": None, "fills_recorded": fills}
    if submit and plan:
        o = client.submit_opg(SYMBOL, plan["side"], plan["qty"], f"kronos-{as_of}")
        row["order"] = {"id": o["id"], "submitted_at": o.get("submitted_at"), "status": o.get("status"),
                        "side": plan["side"], "qty": plan["qty"], "time_in_force": "opg"}
    if submit:
        with open(ledger_path, "a") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row
