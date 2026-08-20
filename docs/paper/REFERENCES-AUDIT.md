# References audit — mechanical verification summary

Generated from the results of `check_references.py` (the hard gate wired
into `make check`). Every entry in `paper.bib` carries a DOI that was
resolved against the Crossref API; the gate re-verifies on every run
(responses cached in `.ref_cache.json`, so re-runs are offline) and fails
on any missing identifier, failed fetch, title mismatch (token overlap
against the fetched record, threshold 0.60), or first-author mismatch.
It also fails on any bib entry not cited in `paper.tex` and any cited key
missing from the bib. The gate was falsified before being trusted: a
planted fabricated entry (invented DOI) failed on resolution (HTTP 404)
and a planted real-paper-with-wrong-DOI entry failed on both title
overlap (0.22) and first-author mismatch; both plants were then removed.

Entries considered and dropped for lack of a verifiable identifier
(sentences rewritten instead): Grossman--Stiglitz (1980, AER) and
Gennotte--Leland (1990, AER) — not in Crossref, DOI handles nonexistent;
Black (1976, ASA proceedings) — unregistered; attribution moved to
Christie (1982). Samuelson (1965) is verified via the DOI of its 2015
World Scientific reprint, noted in the entry itself.

| Key | Identifier | Fetch | Title match | 1st author | Cited in |
|---|---|---|---|---|---|
| `adrian2010` | `10.1016/j.jfi.2008.12.002` | ok (Crossref) | 1.00 | ok | Order flow, price impact, and de-leveraging feedback; The base market |
| `bailey2014` | `10.3905/jpm.2014.40.5.094` | ok (Crossref) | 1.00 | ok | Multiple testing and pre-registration in finance; Reproducibility discipline |
| `bailey2017` | `10.21314/JCF.2016.322` | ok (Crossref) | 1.00 | ok | Multiple testing and pre-registration in finance; Reproducibility discipline |
| `bekaert2000` | `10.1093/rfs/13.1.1` | ok (Crossref) | 1.00 | ok | External validity: the leverage effect across market structures; The leverage effect |
| `bollerslev1986` | `10.1016/0304-4076(86)90063-1` | ok (Crossref) | 1.00 | ok | Stylized facts of asset returns |
| `bouchaud2001` | `10.1103/PhysRevLett.87.228701` | ok (Crossref) | 1.00 | ok | The leverage effect |
| `bouchaud2009` | `10.1016/b978-012374258-2.50006-3` | ok (Crossref) | 1.00 | ok | Order flow, price impact, and de-leveraging feedback |
| `bouchaud2018` | `10.1017/9781316659335` | ok (Crossref) | 1.00 | ok | Order flow, price impact, and de-leveraging feedback |
| `brock1997` | `10.2307/2171879` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `brock1998` | `10.1016/S0165-1889(98)00011-6` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `brunnermeier2009` | `10.1093/rfs/hhn098` | ok (Crossref) | 1.00 | ok | Order flow, price impact, and de-leveraging feedback; The base market |
| `challet1997` | `10.1016/S0378-4371(97)00419-6` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `challet2004` | `10.1093/oso/9780198566403.001.0001` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `chiarella2009` | `10.1016/b978-012374258-2.50009-9` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `christie1982` | `10.1016/0304-405X(82)90018-6` | ok (Crossref) | 1.00 | ok | External validity: the leverage effect across market structures; The leverage effect |
| `cont2000` | `10.1017/S1365100500015029` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `cont2001` | `10.1080/713665670` | ok (Crossref) | 1.00 | ok | Introduction; Stylized facts of asset returns |
| `ding1993` | `10.1016/0927-5398(93)90006-D` | ok (Crossref) | 1.00 | ok | Stylized facts of asset returns |
| `engle1982` | `10.2307/1912773` | ok (Crossref) | 1.00 | ok | Stylized facts of asset returns |
| `fama1970` | `10.2307/2325486` | ok (Crossref) | 1.00 | ok | Market efficiency and the sign channel |
| `farmer2002` | `10.1016/S0167-2681(02)00065-3` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `filimonov2012` | `10.1103/PhysRevE.85.056108` | ok (Crossref) | 1.00 | ok | Reflexivity and endogeneity |
| `garman1980` | `10.1086/296072` | ok (Crossref) | 1.00 | ok | External validity: the leverage effect across market structures; Foreign exchange |
| `gatheral2018` | `10.1080/14697688.2017.1393551` | ok (Crossref) | 1.00 | ok | Stylized facts of asset returns |
| `giardina2003` | `10.1140/epjb/e2003-00050-6` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `glosten1993` | `10.1111/j.1540-6261.1993.tb05128.x` | ok (Crossref) | 1.00 | ok | Stylized facts of asset returns; The ten-event battery |
| `hardiman2013` | `10.1140/epjb/e2013-40107-3` | ok (Crossref) | 1.00 | ok | Reflexivity and endogeneity |
| `harvey2016` | `10.1093/rfs/hhv059` | ok (Crossref) | 1.00 | ok | Multiple testing and pre-registration in finance; Reproducibility discipline |
| `hommes2006` | `10.1016/S1574-0021(05)02023-X` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `kraskov2004` | `10.1103/PhysRevE.69.066138` | ok (Crossref) | 1.00 | ok | The battery: exact criteria and calibration statistics |
| `lebaron2000` | `10.1016/S0165-1889(99)00022-6` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models |
| `lebaron2006` | `10.1016/S1574-0021(05)02024-1` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models; Introduction |
| `lux1999` | `10.1038/17290` | ok (Crossref) | 1.00 | ok | Heterogeneous-agent models; Introduction |
| `mandelbrot1963` | `10.1086/294632` | ok (Crossref) | 1.00 | ok | Stylized facts of asset returns |
| `paninski2003` | `10.1162/089976603321780272` | ok (Crossref) | 1.00 | ok | The battery: exact criteria and calibration statistics |
| `samuelson1965` | `10.1142/9789814566926_0002` (reprint DOI, noted in entry) | ok (Crossref) | 1.00 | ok | Market efficiency and the sign channel |
| `urquhart2016` | `10.1016/j.econlet.2016.09.019` | ok (Crossref) | 1.00 | ok | Stylized facts of asset returns |
| `zhang2018` | `10.1080/00036846.2018.1488076` | ok (Crossref) | 1.00 | ok | Stylized facts of asset returns |
| `zumbach2009` | `10.1080/14697680802616712` | ok (Crossref) | 1.00 | ok | Stylized facts of asset returns |

Totals: 39 entries, 39 verified via Crossref, 0 on
recall alone. Confidence is uniform: every identifier fetched and
matched mechanically (the two 'certain vs high' tiers of the original
instruction are superseded by fetch-verification for every entry).

Regenerate the underlying verification at any time with
`make check` (stage 2) or `python3 check_references.py`.
