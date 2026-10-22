"""What each peer's consumer book holds, from its own 10-Q or 10-K.

The Call Report files "other consumer" as one line (RC-C 6.b + 6.d) that mixes
unsecured loans and lines, student loans and loans secured by anything but a
home or a car, so a bank's other consumer rate says little about its unsecured
lending alone. The holding company's quarterly filing breaks its loans out by
class (ASC 326-20-50-5 asks for amortized cost by class), and a bank with a
material student book shows it as a class of its own. The analyst, 15 Oct
2026: *"I don't know how to prove out that these guys don't have much student
and stuff. Is there a way to do that"*, then *"Build it in and tie it out"*.

Two halves, as the FDIC side has:

- :func:`pull` fetches, for each holding company, the filing for one quarter
  (a 10-Q, or the 10-K for a fourth quarter) from SEC EDGAR into a cache
  folder: the submissions record, the filing's extracted XBRL instance
  (``*_htm.xml``) and its label linkbase. SEC's fair-access policy requires a
  User-Agent naming who is asking, with an email; it is a required setting
  with no default and is never written to the cache.
- :func:`read` reads the cache only: every amortized-cost fact at the quarter
  end whose dimensions are portfolio segments or classes, with the filer's
  own label for each member.

Which class is student lending, unsecured lending or secured non-auto lending
is a judgement, stated per bank in a file of its own
(``config/peer-loan-classes.json``) with the filing's words quoted; the
amounts are never typed there, only looked up here by concept and members, so
every figure on the tab is the filing's own."""
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

XBRLI = "{http://www.xbrl.org/2003/instance}"
XBRLDI = "{http://xbrl.org/2006/xbrldi}"
LINK = "{http://www.xbrl.org/2003/linkbase}"
XLINK = "{http://www.w3.org/1999/xlink}"
#: Amortized cost before the allowance (ASC 326): the class tables' measure.
AMORTIZED_COST = "us-gaap:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss"
#: An axis that sorts loans into segments or classes, not by grade, age or
#: lateness. A fact with any other axis is a cell of a different table.
CLASS_AXIS = re.compile(r"PortfolioSegment|ClassOf|ByClass|LoansByType|LoanType|ProductOrService", re.I)
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
SEC = "https://www.sec.gov"
DATA = "https://data.sec.gov"


class Refused(ValueError):
    pass


def quarter_end(quarter: str) -> str:
    """'2026Q2' -> '2026-06-30'."""
    m = re.fullmatch(r"(\d{4})Q([1-4])", quarter or "")
    if not m:
        raise Refused("a quarter is written YYYYQn, for example 2026Q2, not %r" % (quarter,))
    return "%s-%s" % (m.group(1), ("03-31", "06-30", "09-30", "12-31")[int(m.group(2)) - 1])


def check_user_agent(user_agent: str) -> str:
    ua = (user_agent or "").strip()
    if not EMAIL.search(ua):
        raise Refused("SEC requires a contact email in every request (its fair-access policy): give "
                      "--user-agent as a name and an email, for example \"Your Firm you@yourfirm.com\". "
                      "It has no default and is not stored.")
    return ua


def _get(url: str, user_agent: str, pause: float) -> bytes:
    time.sleep(pause)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    if body[:200].lstrip().lower().startswith(b"<!doctype html") and b"Request Rate Threshold" in body[:2000]:
        raise Refused("SEC refused the request (\"Request Rate Threshold Exceeded\"): it does not accept the "
                      "User-Agent given, or too many requests were made; wait ten minutes and run again")
    return body


def filing_for(submissions: dict, period: str) -> Optional[dict]:
    """The quarterly (or, for a December quarter, annual) filing whose report
    date is ``period``, from an EDGAR submissions record: the latest filed if
    there are several (an amendment comes later than the original)."""
    rec = submissions["filings"]["recent"]
    forms = ("10-K", "10-K/A") if period.endswith("12-31") else ("10-Q", "10-Q/A")
    hits = [i for i, f in enumerate(rec["form"]) if f in forms and rec["reportDate"][i] == period]
    if not hits:
        return None
    i = max(hits, key=lambda k: rec["filingDate"][k])
    return {"form": rec["form"][i], "accession": rec["accessionNumber"][i], "filed": rec["filingDate"][i],
            "primary": rec["primaryDocument"][i]}


def pull(cache, holders: Sequence[dict], quarter: str, user_agent: str, refresh: bool = False,
         say: Callable[[str], None] = print, fetch: Optional[Callable[[str], bytes]] = None,
         pause: float = 0.15) -> Dict[str, dict]:
    """Fetch each holder's filing for ``quarter`` into ``cache/<cik>/``.
    ``holders``: ``[{short, cik}]``. Returns ``{cik: filing record}``; a holder
    with no such filing yet is reported and left out."""
    period = quarter_end(quarter)
    ua = check_user_agent(user_agent)
    get = fetch or (lambda url: _get(url, ua, pause))
    cache = Path(cache)
    out = {}
    for h in holders:
        cik = int(h["cik"])
        folder = cache / str(cik)
        record = folder / ("%s.json" % period)
        if record.exists() and not refresh:
            out[str(cik)] = json.loads(record.read_text(encoding="utf-8"))
            say("%s: %s already held" % (h["short"], out[str(cik)]["accession"]))
            continue
        sub = json.loads(get("%s/submissions/CIK%010d.json" % (DATA, cik)))
        f = filing_for(sub, period)
        if f is None:
            say("%s: no 10-Q or 10-K for %s filed yet" % (h["short"], period))
            continue
        base = "%s/Archives/edgar/data/%d/%s/" % (SEC, cik, f["accession"].replace("-", ""))
        names = [x["name"] for x in json.loads(get(base + "index.json"))["directory"]["item"]]
        inst = [n for n in names if n.endswith("_htm.xml")]
        lab = [n for n in names if n.endswith("_lab.xml")]
        if len(inst) != 1 or len(lab) != 1:
            say("%s: %s has %d extracted instances and %d label files, not one of each; not read"
                % (h["short"], f["accession"], len(inst), len(lab)))
            continue
        folder.mkdir(parents=True, exist_ok=True)
        for n in (inst[0], lab[0]):
            (folder / n).write_bytes(get(base + n))
        f.update(cik=cik, name=sub.get("name", ""), period=period, instance=inst[0], labels=lab[0],
                 url=base + f["primary"], folder=base)
        record.write_text(json.dumps(f, indent=1), encoding="utf-8")
        out[str(cik)] = f
        say("%s: %s %s filed %s" % (h["short"], f["form"], f["accession"], f["filed"]))
    return out


def labels(path) -> Dict[str, str]:
    """``{prefix:LocalName: label}`` from a filer's label linkbase (standard labels)."""
    root = ET.parse(path).getroot()
    out = {}
    for lk in root.iter(LINK + "labelLink"):
        loc, lab = {}, {}
        for el in lk:
            t = el.get(XLINK + "type")
            if t == "locator":
                href = el.get(XLINK + "href").split("#")[1]
                loc[el.get(XLINK + "label")] = href.replace("_", ":", 1)
            elif t == "resource" and el.get(XLINK + "role", "").endswith("/label"):
                lab[el.get(XLINK + "label")] = el.text
        for el in lk:
            if el.get(XLINK + "type") == "arc" and el.get(XLINK + "from") in loc and el.get(XLINK + "to") in lab:
                out[loc[el.get(XLINK + "from")]] = lab[el.get(XLINK + "to")]
    return out


def _qname(tag: str, nsmap: Dict[str, str]) -> str:
    ns, local = tag[1:].split("}")
    return "%s:%s" % (nsmap.get(ns, ns), local)


def facts(path, period: str, concept: str = AMORTIZED_COST) -> Dict[Tuple[str, ...], float]:
    """``{(member, ...): value}``: ``concept`` at instant ``period`` in an
    extracted instance, for contexts whose every dimension is a segment or
    class axis. Members are sorted, so the order a filer wrote them in does not
    matter. Two different values for one set of members are refused."""
    nsmap = {}
    for _, (prefix, uri) in ET.iterparse(path, events=["start-ns"]):
        nsmap.setdefault(uri, prefix)
    root = ET.parse(path).getroot()
    ctx = {}
    for c in root.iter(XBRLI + "context"):
        inst = c.find(".//" + XBRLI + "instant")
        typed = c.find(".//" + XBRLDI + "typedMember")
        dims = [(m.get("dimension"), m.text.strip()) for m in c.iter(XBRLDI + "explicitMember")]
        if inst is None or inst.text.strip() != period or typed is not None:
            continue
        if not all(CLASS_AXIS.search(a) for a, _ in dims):
            continue
        ctx[c.get("id")] = tuple(sorted(m for _, m in dims))
    out: Dict[Tuple[str, ...], float] = {}
    for el in root:
        if el.get("contextRef") not in ctx or el.text is None or _qname(el.tag, nsmap) != concept:
            continue
        key, v = ctx[el.get("contextRef")], float(el.text)
        if key in out and out[key] != v:
            raise Refused("%s: %s has two values at %s for %s: %s and %s"
                          % (Path(path).name, concept, period, ", ".join(key) or "no dimension", out[key], v))
        out[key] = v
    return out


def read(cache, cik, period: str) -> Tuple[dict, Dict[Tuple[str, ...], float], Dict[str, str]]:
    """A cached filing: its record, its amortized-cost facts by members, and its labels."""
    folder = Path(cache) / str(int(cik))
    record = folder / ("%s.json" % period)
    if not record.exists():
        raise Refused("no filing for certificate-holder CIK %s at %s in %s: run the SEC pull first"
                      % (cik, period, cache))
    f = json.loads(record.read_text(encoding="utf-8"))
    return f, facts(folder / f["instance"], period), labels(folder / f["labels"])


def member_label(member: str, labs: Dict[str, str]) -> str:
    """The filer's label for a member, without the taxonomy's " [Member]"."""
    text = labs.get(member) or re.sub(r"(?<=[a-z])(?=[A-Z])", " ", member.split(":")[1].replace("Member", ""))
    return re.sub(r"\s*\[Member\]$", "", text)
