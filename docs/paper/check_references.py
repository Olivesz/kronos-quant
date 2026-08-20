#!/usr/bin/env python3
"""Verify every bibliography entry in paper.bib against a registered identifier.

Rules (all hard failures):
  1. Every entry must carry a `doi` field or an arXiv `eprint` field.
  2. Every identifier must resolve: DOIs against the Crossref API
     (https://api.crossref.org/works/<doi>), arXiv ids against the arXiv
     export API. Responses are cached in .ref_cache.json so re-runs are
     offline; an identifier that cannot be fetched (and is not cached) FAILS
     -- an unverified entry does not ship.
  3. The fetched record's title must match the entry's title (token overlap,
     case/punctuation/accent-insensitive, subset-tolerant so that subtitle
     variants pass) and the entry's first-author surname must appear among
     the fetched authors' family names.
  4. Every entry must be cited at least once in paper.tex, and every \\cite*
     key in paper.tex must exist in paper.bib.

Run:  make check   (second stage, after check_numbers.py)
      python3 check_references.py [--bib PATH] [--tex PATH]
Exit: 0 iff every check passes.
"""

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE_PATH = HERE / ".ref_cache.json"
USER_AGENT = "kronos-paper-refcheck/1.0 (preprint reference verification)"

failures = []
n_checks = 0


def check(label, ok, detail=""):
    global n_checks
    n_checks += 1
    if not ok:
        failures.append(f"{label}: {detail}")
        print(f"  FAIL  {label}  {detail}")


# ------------------------------------------------------------------ bib parse
def parse_bib(text):
    """Minimal BibTeX parser: returns {key: {field: value, '@type': type}}."""
    entries = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        etype, key = m.group(1).lower(), m.group(2)
        if etype in ("comment", "preamble", "string"):
            continue
        # scan to the matching closing brace of the entry
        depth, i = 1, m.end()
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[m.end():i - 1]
        fields = {"@type": etype}
        for fm in re.finditer(r"(\w+)\s*=\s*\{", body):
            fname = fm.group(1).lower()
            d, j = 1, fm.end()
            while j < len(body) and d:
                if body[j] == "{":
                    d += 1
                elif body[j] == "}":
                    d -= 1
                j += 1
            fields[fname] = body[fm.end():j - 1].strip()
        entries[key] = fields
    return entries


def delatex(s):
    """Strip TeX accents/braces/commands for plain-text comparison."""
    s = re.sub(r"\\['\"`^~=.uvHtcdbkr]\s*\{?(\w)\}?", r"\1", s)   # \'{o} etc.
    s = re.sub(r"\\[a-zA-Z]+", " ", s)                             # \ldots etc.
    s = s.replace("{", "").replace("}", "").replace("~", " ")
    return s


def norm(s):
    s = delatex(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"<[^>]+>", " ", s)                                 # HTML tags
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return s


def tokens(s):
    return {t for t in norm(s).split() if len(t) >= 2}


def first_author_surname(author_field):
    first = re.split(r"\s+and\s+", author_field)[0]
    surname = first.split(",")[0] if "," in first else first.split()[-1]
    return norm(surname).replace(" ", "")


# ------------------------------------------------------------------ fetching
def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as fh:
            return json.load(fh)
    return {}


def fetch(url, cache):
    """Return (payload, from_network). Caches successes only."""
    if url in cache:
        return cache[url], False
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = r.read().decode("utf-8", "replace")
            cache[url] = payload
            with open(CACHE_PATH, "w") as fh:
                json.dump(cache, fh)
            return payload, True
        except Exception as e:  # noqa: BLE001 - report any fetch failure
            last_err = e
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"fetch failed after retries: {last_err}")


def crossref_record(doi, cache):
    payload, from_net = fetch(
        f"https://api.crossref.org/works/{urllib.parse.quote(doi)}", cache)
    msg = json.loads(payload)["message"]
    title = (msg.get("title") or [""])[0]
    authors = [a.get("family") or a.get("name") or ""
               for a in msg.get("author", [])]
    if not authors:  # e.g. edited volumes: fall back to editors
        authors = [a.get("family") or "" for a in msg.get("editor", [])]
    return title, authors, from_net


def arxiv_record(eprint, cache):
    payload, from_net = fetch(
        "http://export.arxiv.org/api/query?id_list="
        + urllib.parse.quote(eprint), cache)
    entry = re.search(r"<entry>(.*?)</entry>", payload, re.S)
    if not entry:
        raise RuntimeError("no <entry> in arXiv response")
    body = entry.group(1)
    tm = re.search(r"<title>(.*?)</title>", body, re.S)
    title = tm.group(1).strip() if tm else ""
    if norm(title) == "error":
        raise RuntimeError("arXiv returned an error entry (unknown id)")
    authors = [re.sub(r"\s+", " ", a).strip().split()[-1]
               for a in re.findall(r"<name>(.*?)</name>", body, re.S)]
    return title, authors, from_net


# ------------------------------------------------------------------ matching
def title_match(bib_title, fetched_title):
    """Token overlap relative to the shorter title (subtitle-tolerant)."""
    bt, ft = tokens(bib_title), tokens(fetched_title)
    if not bt or not ft:
        return 0.0
    return len(bt & ft) / min(len(bt), len(ft))


def author_match(bib_author_field, fetched_families):
    surname = first_author_surname(bib_author_field)
    fetched = {norm(f).replace(" ", "") for f in fetched_families}
    return surname in fetched


TITLE_THRESHOLD = 0.6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bib", default=str(HERE / "paper.bib"))
    ap.add_argument("--tex", default=str(HERE / "paper.tex"))
    args = ap.parse_args()

    bib_text = Path(args.bib).read_text()
    tex_text = Path(args.tex).read_text()
    entries = parse_bib(bib_text)
    cache = load_cache()

    print(f"== reference verification ({len(entries)} entries)")
    check("bib has entries", len(entries) > 0)

    n_fetched = 0
    for key in sorted(entries):
        f = entries[key]
        doi, eprint = f.get("doi"), f.get("eprint")
        check(f"{key}: has identifier", bool(doi or eprint),
              "no doi/eprint field -- unverifiable entries do not ship")
        if not (doi or eprint):
            continue
        try:
            if doi:
                title, authors, from_net = crossref_record(doi, cache)
                ident = f"doi:{doi}"
            else:
                title, authors, from_net = arxiv_record(eprint, cache)
                ident = f"arXiv:{eprint}"
            n_fetched += from_net
        except Exception as e:  # noqa: BLE001
            check(f"{key}: identifier resolves", False, f"{doi or eprint}: {e}")
            continue
        check(f"{key}: identifier resolves", True)
        score = title_match(f.get("title", ""), title)
        check(f"{key}: title matches {ident}", score >= TITLE_THRESHOLD,
              f"overlap {score:.2f} < {TITLE_THRESHOLD}: bib "
              f"{f.get('title', '')!r} vs fetched {title!r}")
        check(f"{key}: first author matches", author_match(f.get("author", f.get("editor", "")), authors),
              f"bib first author {first_author_surname(f.get('author', ''))!r}"
              f" not in fetched {authors}")
        if from_net:
            time.sleep(1.0)

    # -------------------------------------------------- tex <-> bib coverage
    cited = set()
    for m in re.finditer(r"\\cite[tp]?\*?(?:\[[^\]]*\])*\{([^}]*)\}", tex_text):
        cited.update(k.strip() for k in m.group(1).split(","))
    for key in sorted(cited):
        check(f"cited key exists in bib: {key}", key in entries)
    for key in sorted(entries):
        check(f"bib entry is cited in tex: {key}", key in cited,
              "uncited entries are not load-bearing -- remove or cite")

    print()
    if failures:
        print(f"FAILED: {len(failures)} of {n_checks} reference checks")
        sys.exit(1)
    print(f"PASS: all {n_checks} reference checks "
          f"({len(entries)} entries, {n_fetched} fetched, rest cached)")


if __name__ == "__main__":
    main()
