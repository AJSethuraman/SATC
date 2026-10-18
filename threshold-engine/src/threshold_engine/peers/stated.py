"""Stated acquisitions: the ones the FDIC record cannot see, each with the
filing that records it, read by ``peers build`` beside the FDIC record.

The firm, 17 Oct 2026, on the commercial proposal's question 14 ("agreed
with the recommendation" on the docket form): add a stated list of the
acquisitions the FDIC record cannot see, each with its 8-K, read by the build
like the FDIC record, so the windows holding them are left out with a reason.
The record misses three kinds (docs/commercial-2026-10/research-breaks.md on
main, sections B and C): a failure with no history row naming the acquirer
(JPMorgan and Washington Mutual Bank, 2008), a deal the FDIC codes as a branch
purchase (M&T and Wilmington Trust, 2011, code 712), and an asset purchase
from a company that is not a bank (Wells Fargo and GE Capital, 2016).

The list is a file (``config/stated-acquisitions.json``), never code, and every
key of every entry is required; nothing has a default:

    {"_what": "what the file is and what it leaves out",
     "acquisitions": [{
        "acquirer": "628",          # the acquirer's FDIC certificate, as the roster names it
        "quarter": "2008Q3",        # the Call Report quarter its first filing holds the deal
        "what": "one plain sentence: who bought what",
        "citation": "the filing that records it, with its date",
        "url": "https://... the filing itself"
     }]}

A malformed entry is refused by name, every problem at once. So is a key
given twice in one object (JSON would keep the last silently), and an
acquirer and quarter listed twice, however each is worded: the build reads
one quarter per entry, so two deals in one quarter go in one entry. What the build
does with an entry (``peers.run.build``): every product's four-quarter windows
holding the quarter are left out for that bank, with their own reason
(``books.WHY_STATED``), right after the recorded acquisitions; no share of the
book is measured, because the FDIC record holds no filing of what was bought.
The bank's book index treats the quarter as an acquisition too, marked
declared on the Run tab.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

TOP_KEYS = ("_what", "acquisitions")
KEYS = ("acquirer", "quarter", "what", "citation", "url")
_QUARTER = re.compile(r"\d{4}Q[1-4]")


class StatedError(ValueError):
    """A stated acquisitions file that cannot be read, with every problem found."""


def _one_line(text) -> bool:
    return isinstance(text, str) and bool(text.strip()) and text.splitlines() == [text]


def _keys(where: str, got, want, problems: List[str]) -> bool:
    if not isinstance(got, dict):
        problems.append("%s must be an object with the keys %s" % (where, ", ".join(want)))
        return False
    for k in want:
        if k not in got:
            problems.append("%s is missing %r (every key is required; none has a default)" % (where, k))
    for k in got:
        if k not in want:
            problems.append("%s has %r, which is not a key it takes (check the spelling)" % (where, k))
    return all(k in got for k in want)


def check(raw, name: str = "the stated acquisitions") -> List[dict]:
    """The entries, checked; ``StatedError`` listing every problem, each
    under its entry (its number, and its acquirer and quarter where they
    can be read), when anything is wrong."""
    problems: List[str] = []
    if not _keys(name, raw, TOP_KEYS, problems):
        raise StatedError("\n".join(problems))
    if not (isinstance(raw["_what"], str) and raw["_what"].strip()):
        problems.append("%s: _what must say what the file is" % name)
    entries = raw["acquisitions"]
    if not isinstance(entries, list):
        problems.append("%s: acquisitions must be a list of acquisitions ([] for none)" % name)
        raise StatedError("\n".join(problems))
    out, seen = [], {}
    for i, e in enumerate(entries, start=1):
        who = e.get("acquirer") if isinstance(e, dict) else None
        when = e.get("quarter") if isinstance(e, dict) else None
        where = ("acquisition %d (certificate %s, %s)" % (i, who, when)
                 if isinstance(who, str) and isinstance(when, str) else "acquisition %d" % i)
        if not _keys(where, e, KEYS, problems):
            continue
        before = len(problems)
        if not (isinstance(who, str) and who.isascii() and who.isdigit()):
            problems.append("%s: acquirer must be the FDIC certificate written as digits, like \"628\", not %r"
                            % (where, who))
        if not (isinstance(when, str) and _QUARTER.fullmatch(when)):
            problems.append("%s: quarter must be written like 2008Q3, not %r" % (where, when))
        for k, says in (("what", "one plain sentence on one line: who bought what"),
                        ("citation", "the filing that records it, on one line")):
            if not _one_line(e[k]):
                problems.append("%s: %s must be %s" % (where, k, says))
        if not (isinstance(e["url"], str) and re.fullmatch(r"https://\S+", e["url"])):
            problems.append("%s: url must be the filing's address, starting https://, not %r" % (where, e["url"]))
        if len(problems) == before:
            # The build reads an acquirer and quarter, never the wording, so
            # the same pair twice is the same acquisition, however worded.
            if (who, when) in seen:
                problems.append("%s: certificate %s in %s is already listed (acquisition %d); one entry per "
                                "acquirer and quarter, so two deals in one quarter go in one entry"
                                % (where, who, when, seen[who, when]))
                continue
            seen[who, when] = i
            out.append({k: e[k] for k in KEYS})
    if problems:
        raise StatedError("\n".join(problems))
    return out


class _KeyTwice(ValueError):
    """A key given twice in one JSON object."""


def _no_key_twice(pairs) -> dict:
    """``json.loads``' object hook: an object, refusing a key given twice in
    it, which JSON would otherwise settle by keeping the last silently."""
    out: dict = {}
    for k, v in pairs:
        if k in out:
            who = next((x for key, x in pairs if key == "acquirer" and isinstance(x, str)), None)
            raise _KeyTwice("the key %r is given twice in one object%s; give it once"
                            % (k, " (certificate %s)" % who if who else ""))
        out[k] = v
    return out


def load(path) -> List[dict]:
    """Read and check the stated acquisitions file at ``path``."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_key_twice)
    except FileNotFoundError:
        raise StatedError("the stated acquisitions file %s does not exist" % path) from None
    except json.JSONDecodeError as e:
        raise StatedError("%s is not valid JSON: %s" % (path.name, e)) from None
    except _KeyTwice as e:
        raise StatedError("%s: %s" % (path.name, e)) from None
    except UnicodeDecodeError:
        raise StatedError("%s is not a UTF-8 text file" % path) from None
    except OSError as e:
        raise StatedError("the stated acquisitions file %s cannot be read: %s" % (path, e.strerror or e)) from None
    return check(raw, path.name)


def _repdte(quarter: str) -> str:
    return "%s%s" % (quarter[:4], ("0331", "0630", "0930", "1231")[int(quarter[5]) - 1])


def by_cert(entries: Sequence[dict], roster_certs: Iterable[str],
            quarters: Sequence[str]) -> Tuple[Dict[str, List[str]], List[dict]]:
    """``({cert: [YYYYMMDD]}, outside)``: each entry's quarter-end for its
    acquirer, when the quarter is one of ``quarters`` (the build's
    ``YYYYMMDD`` quarter-ends), and the entries whose quarter is not, which
    the build reports rather than reads. An acquirer not on the roster is
    refused by entry: a typo there would otherwise be ignored and the
    acquisition read as growth."""
    certs = set(str(c) for c in roster_certs)
    off = ["acquisition %d (certificate %s, %s)" % (i, e["acquirer"], e["quarter"])
           for i, e in enumerate(entries, start=1) if e["acquirer"] not in certs]
    if off:
        raise StatedError("the stated acquisitions name a certificate not on the roster: %s" % "; ".join(off))
    held = set(quarters)
    out: Dict[str, List[str]] = {}
    outside = []
    for e in entries:
        q = _repdte(e["quarter"])
        if q in held:
            if q not in out.setdefault(e["acquirer"], []):
                out[e["acquirer"]].append(q)
        else:
            outside.append(e)
    return {c: sorted(qs) for c, qs in sorted(out.items())}, outside


__all__: List[str] = ["StatedError", "check", "load", "by_cert", "KEYS", "TOP_KEYS"]
