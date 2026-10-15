"""The source side of the tie-out: every loan-class amount, read out of each
10-Q as filed, not out of the tool's cache.

    python filed.py CLASSES.json OUT.json

For each bank in the loan classes file this fetches the 10-Q's primary
document from SEC EDGAR, fresh, and reads its inline XBRL: the
``ix:nonFraction`` elements the rendered tables are made of, each with its
own context, scale and sign. That is a different file (the document the
reader sees, not the extracted instance the build reads) and a different
parser (this one, not ``peers.classes``), so a fault in either shows as a
difference. SEC's fair-access policy requires a contact; it is read from the
environment variable SEC_USER_AGENT and never written down.

Writes ``{short: {"url", "facts": [[members, value_in_dollars, shown_text, copies]]}}`` and, beside
it, each document's text with table cells separated by " | " (``text/<short>.txt``), which is where a
class the filing prints but does not tag is looked for."""
import json
import os
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser

CONCEPT = "us-gaap:FinancingReceivableExcludingAccruedInterestBeforeAllowanceForCreditLoss"


class Text(HTMLParser):
    """The document as text: a cell ends with " | ", a row or block with a new line."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("script", "style", "ix:header"):
            self._skip += 1

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style", "ix:header"):
            self._skip -= 1
        elif t in ("td", "th"):
            self.parts.append(" | ")
        elif t in ("tr", "p", "div", "br"):
            self.parts.append(chr(10))

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def text(self):
        return re.sub("[ " + chr(9) + chr(160) + "]+", " ", "".join(self.parts))


class InlineXBRL(HTMLParser):
    """Contexts (id -> instant, explicit members) and ix:nonFraction facts."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.contexts, self.facts, self._ctx, self._in_instant, self._member, self._fact = {}, [], None, False, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        t = tag.lower()
        if t == "xbrli:context":
            self._ctx = {"id": a["id"], "instant": None, "members": [], "typed": False}
        elif t == "xbrli:instant" and self._ctx is not None:
            self._in_instant = True
        elif t == "xbrldi:explicitmember" and self._ctx is not None:
            self._member = a.get("dimension")
        elif t == "xbrldi:typedmember" and self._ctx is not None:
            self._ctx["typed"] = True
        elif t == "ix:nonfraction":
            self._fact = {"name": a.get("name"), "context": a.get("contextref"), "scale": int(a.get("scale", "0")),
                          "sign": a.get("sign"), "format": a.get("format", ""), "text": ""}

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == "xbrli:context" and self._ctx is not None:
            self.contexts[self._ctx["id"]] = self._ctx
            self._ctx = None
        elif t == "xbrli:instant":
            self._in_instant = False
        elif t == "xbrldi:explicitmember":
            self._member = None
        elif t == "ix:nonfraction" and self._fact is not None:
            self.facts.append(self._fact)
            self._fact = None

    def handle_data(self, data):
        if self._in_instant and self._ctx is not None:
            self._ctx["instant"] = data.strip()
        elif self._member is not None and self._ctx is not None and data.strip():
            self._ctx["members"].append(data.strip())
        if self._fact is not None:
            self._fact["text"] += data


def value(f):
    """The fact's value in dollars, as ixt formats write it: digits with
    commas, a dash or 'zerodash' for zero, scaled and signed."""
    text = f["text"].strip()
    if "zerodash" in f["format"] or text in ("-", "—", "–"):
        return 0.0
    digits = re.sub(r"[^\d.]", "", text)
    if not digits:
        raise ValueError("a fact with no number: %r" % f)
    v = float(digits) * 10 ** f["scale"]
    return -v if f["sign"] == "-" else v


def read(url, period, user_agent):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=180) as r:
        html = r.read().decode("utf-8", errors="replace")
    p = InlineXBRL()
    p.feed(html)
    t = Text()
    t.feed(html)
    out = {}
    for f in p.facts:
        c = p.contexts.get(f["context"])
        if f["name"] != CONCEPT or c is None or c["instant"] != period or c["typed"]:
            continue
        key = tuple(sorted(c["members"]))
        out.setdefault(key, set()).add((value(f), f["text"].strip()))
    return out, t.text()


def main(classes_path, out_path):
    ua = os.environ.get("SEC_USER_AGENT", "")
    if "@" not in ua:
        sys.exit("set SEC_USER_AGENT to a name and a contact email, as SEC requires")
    spec = json.load(open(classes_path, encoding="utf-8"))
    period = {"Q1": "03-31", "Q2": "06-30", "Q3": "09-30", "Q4": "12-31"}[spec["quarter"][4:]]
    period = "%s-%s" % (spec["quarter"][:4], period)
    result = {}
    for b in spec["banks"]:
        time.sleep(0.3)
        got, text = read(b["filing_url"], period, ua)
        os.makedirs(os.path.join(os.path.dirname(out_path) or ".", "text"), exist_ok=True)
        open(os.path.join(os.path.dirname(out_path) or ".", "text", b["short"] + ".txt"), "w",
             encoding="utf-8").write(text)
        result[b["short"]] = {"url": b["filing_url"],
                              "facts": [[list(k), sorted(v)[0][0], sorted(v)[0][1], len(v)] for k, v in got.items()]}
        print(b["short"], len(got), "amortized-cost facts at", period)
    json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
