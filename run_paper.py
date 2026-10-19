"""DESIGN29 Stage 4: trade the shipped overlay on SPY in the owner's broker
paper account (kronos/paper.py).

Usage:
  python run_paper.py            # dry run: print today's decision and order
  python run_paper.py --submit   # post the order and append live/paper_ledger.jsonl

Keys come only from the environment: ALPACA_PAPER_KEY_ID and
ALPACA_PAPER_SECRET_KEY (the owner's paper account). Without them the
script exits without contacting anyone.
"""
import json
import os
import sys

from config import CFG
from kronos.paper import AlpacaPaper, run

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live", "paper_ledger.jsonl")


def main():
    key, secret = os.environ.get("ALPACA_PAPER_KEY_ID"), os.environ.get("ALPACA_PAPER_SECRET_KEY")
    if not key or not secret:
        print("ALPACA_PAPER_KEY_ID / ALPACA_PAPER_SECRET_KEY not set: nothing to do")
        return 0
    submit = "--submit" in sys.argv
    feed = os.environ.get("ALPACA_DATA_FEED", "iex")
    row = run(AlpacaPaper(key, secret), CFG, LEDGER, submit=submit, feed=feed)
    print(("submitted" if submit else "dry run") + ": " + json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
