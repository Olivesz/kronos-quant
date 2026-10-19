"""Gate X48 (DESIGN29 Stage 4): the paper-account trader trades the shipped
overlay and nothing else, and cannot touch a live account or leak its keys.

a. The client refuses every base URL except Alpaca's paper trading host.
b. The decision is the shipped overlay's: next_exposure on any prefix of
   closes equals kronos.volalpha.overlay_exposure (itself pinned to the
   shipped backtest by X47a) applied to the next day, exactly.
c. Sizing: whole shares toward exposure × equity, nothing inside the
   no-trade band, sells when over target.
d. Against a fake broker (no network): a dry run posts nothing and writes
   nothing; a submit posts one market-on-open order and appends one row; a
   second run for the same close is skipped; the next day's run records the
   earlier order's fill with the broker's own filled_at; the secret never
   appears in the ledger. Paged bar responses are concatenated in order.
Synthetic, no network.
"""
import io
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from config import CFG
from kronos import paper as P
from kronos.volalpha import overlay_exposure

# ---- a. paper host only ----------------------------------------------------
for bad in ("https://api.alpaca.markets", "http://paper-api.alpaca.markets", "https://example.com"):
    try:
        P.AlpacaPaper("k", "s", base=bad)
        raise AssertionError(f"accepted {bad}")
    except ValueError:
        pass
try:
    P.AlpacaPaper("", "s")
    raise AssertionError("accepted an empty key")
except ValueError:
    pass
print("X48a client refuses live / non-TLS / foreign hosts and empty keys")

# ---- b. the decision is the shipped overlay -------------------------------
rng = np.random.default_rng(48)
days = pd.bdate_range("2019-01-02", periods=900)
vol = 0.01 * np.exp(np.cumsum(rng.normal(0, 0.04, 900)) * 0.4)
closes = pd.Series(300 * np.exp(np.cumsum(rng.normal(0.0004, 1, 900) * vol)), index=days)
r = closes.pct_change().dropna()
applied = overlay_exposure(r, CFG)                 # value at j = decided at j-1
for k in (300, 517, 898):
    got = P.next_exposure(closes.iloc[:k + 1], CFG)  # decided at close k (return index k-1)
    want = float(applied.iloc[k])                  # applies to return index k = day k+1
    assert got == want, f"decision at {k}: {got} != {want}"
print("X48b next_exposure on every tested prefix == the shipped overlay's next-day exposure (exact)")

# ---- c. sizing ---------------------------------------------------------------
assert P.order_for(1.2, 100_000, 500.0, 0) == {"side": "buy", "qty": 240, "target_shares": 240}
assert P.order_for(0.5, 100_000, 500.0, 240) == {"side": "sell", "qty": 140, "target_shares": 100}
assert P.order_for(1.0, 100_000, 250.0, 399) is None, "a 0.25% change traded inside the band"
assert P.order_for(1.0, 100_000, 500.0, 200) is None
print("X48c whole-share sizing, sells over target, no-trade band holds")


# ---- d. against a fake broker --------------------------------------------------
class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Broker:
    def __init__(self, closes):
        self.closes, self.posts, self.orders, self.seen_headers = closes, [], {}, []

    def __call__(self, req, timeout=30):
        self.seen_headers.append(dict(req.header_items()))
        u = urllib.parse.urlparse(req.full_url)
        q = urllib.parse.parse_qs(u.query)
        if "/bars" in u.path:
            bars = [{"t": d.strftime("%Y-%m-%dT05:00:00Z"), "c": float(c)} for d, c in self.closes.items()]
            half = len(bars) // 2
            if "page_token" in q:
                return Resp(json.dumps({"bars": bars[half:], "next_page_token": None}).encode())
            return Resp(json.dumps({"bars": bars[:half], "next_page_token": "p2"}).encode())
        if u.path == "/v2/account":
            return Resp(b'{"equity": "100000"}')
        if u.path.startswith("/v2/positions/"):
            raise urllib.error.HTTPError(req.full_url, 404, "not found", {}, None)
        if u.path == "/v2/orders" and req.get_method() == "POST":
            body = json.loads(req.data)
            oid = f"ord-{len(self.posts)}"
            self.posts.append(body)
            self.orders[oid] = {"id": oid, "status": "accepted", "submitted_at": "2026-01-01T00:30:00Z"}
            return Resp(json.dumps(self.orders[oid]).encode())
        if u.path.startswith("/v2/orders/"):
            oid = u.path.rsplit("/", 1)[1]
            o = dict(self.orders[oid], status="filled", filled_at="2026-01-02T14:30:01.5Z",
                     filled_qty="240", filled_avg_price="501.25")
            return Resp(json.dumps(o).encode())
        raise AssertionError(f"unexpected request {req.get_method()} {req.full_url}")


SECRET = "s3cr3t-never-written"
with tempfile.TemporaryDirectory() as tmp:
    ledger = os.path.join(tmp, "paper_ledger.jsonl")
    b = Broker(closes.iloc[:600])
    cl = P.AlpacaPaper("key-id", SECRET, opener=b)
    dry = P.run(cl, CFG, ledger, submit=False)
    assert not b.posts and not os.path.exists(ledger), "dry run posted or wrote"
    assert dry["exposure"] == P.next_exposure(closes.iloc[:600], CFG)
    row = P.run(cl, CFG, ledger, submit=True)
    assert len(b.posts) == 1 and b.posts[0]["time_in_force"] == "opg" and b.posts[0]["type"] == "market"
    assert b.posts[0]["client_order_id"] == f"kronos-{row['as_of']}"
    assert P.run(cl, CFG, ledger, submit=True).get("skipped"), "decided twice for one close"
    assert len(b.posts) == 1
    b.closes = closes.iloc[:601]
    row2 = P.run(cl, CFG, ledger, submit=True)
    assert row2["fills_recorded"] and row2["fills_recorded"][0]["filled_at"] == "2026-01-02T14:30:01.5Z"
    assert row2["fills_recorded"][0]["order_id"] == row["order"]["id"]
    b.closes = closes.iloc[:602]
    row3 = P.run(cl, CFG, ledger, submit=True)
    assert all(f["order_id"] != row["order"]["id"] for f in row3["fills_recorded"]), "fill recorded twice"
    text = open(ledger).read()
    assert SECRET not in text and "key-id" not in text, "a credential reached the ledger"
    assert all(h.get("Apca-api-secret-key") == SECRET for h in b.seen_headers), "secret not sent as header"
    rows = P.ledger_rows(ledger)
    assert [x["as_of"] for x in rows] == sorted({x["as_of"] for x in rows}) and len(rows) == 3
print(f"X48d fake broker: dry run inert; one OPG order per close; fills from the broker's "
      f"filled_at, recorded once; {len(rows)} rows, no credential in the ledger")
print("GATE X48 PASSED")
