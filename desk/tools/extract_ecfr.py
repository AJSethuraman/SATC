"""Turn a section of the eCFR into a desk's problem set and stored authority.

WHY THIS IS A SCRIPT AND NOT PART OF THE ENGINE. This is the one place a live
fetch belongs: building the record. Once built, the engine grades against stored
text and never reaches out, which is what keeps CI deterministic and offline.

WHAT IT REFUSES TO DO. It does not invent a conclusion. An example whose outcome
is not stated in terms this desk can score is left out and counted, because a
problem set that quietly drops what it could not parse reports a denominator
that means nothing -- and that is the first tenet in `docs/SOFTWARE-TENETS.md`,
which exists because a proof artifact once declared 190 documents fine when
every one of them was unreadable.

Run:  python tools/extract_ecfr.py <reg.xml> <desk-dir>
"""
from __future__ import annotations

import re
import sys
import textwrap
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

#: Conclusions this desk can score, and the exact wording that states each. Kept
#: narrow on purpose: a looser match would turn "is not required to capitalize
#: under paragraph (x), but must under (y)" into a confident wrong answer.
CONCLUSIONS = (
    ("must capitalize", re.compile(r"\bmust capitalize\b")),
    ("not required to capitalize", re.compile(r"\bis not required to capitalize\b")),
)

#: An example that leans on one not shown cannot be answered from what the desk
#: is given. Both spellings, because the regulation uses each -- and a filter
#: written for only the first missed a real case on this script's first run.
DEPENDENT = re.compile(r"same facts as(?: in)? Example|Assume the same facts", re.I)


def examples(xml_path: Path):
    """Walk the section in document order, tagging each example with its paragraph."""
    root = ET.parse(xml_path).getroot()
    para = sub = None
    n = 0
    for child in root:
        text = "".join(child.itertext()).strip()
        if child.tag == "P":
            m = re.match(r"^\((\d+)\) Examples?\..*?paragraph \(([a-z])\)", text)
            if m:
                sub, para, n = m.group(1), m.group(2), 0
        elif child.tag == "EXAMPLE" and para:
            n += 1
            head = "".join(child.find("HED").itertext()).strip()
            body = " ".join(
                " ".join("".join(p.itertext()).split())
                for p in child.findall("PSPACE")
            )
            yield {
                "para": para, "sub": sub, "n": n,
                "title": head.split(". ", 1)[-1] if ". " in head else head,
                "text": body,
            }


def classify(text: str):
    """Return the stated conclusion, or None. Ambiguity is None, never a guess."""
    hits = [name for name, rx in CONCLUSIONS if rx.search(text)]
    return hits[0] if len(hits) == 1 else None


def build(xml_path: Path, desk_dir: Path, *, section="1.263(a)-3",
          source_id="S1", today=None):
    today = today or date.today().isoformat()
    all_ex = list(examples(xml_path))
    kept, dropped = [], []
    for e in all_ex:
        why = None
        if DEPENDENT.search(e["text"]):
            why = "depends on an example not shown"
        elif classify(e["text"]) is None:
            why = "no single conclusion stated in capitalisation terms"
        (dropped if why else kept).append((e, why))

    wrap = lambda t: "\n".join(textwrap.wrap(t, 78, initial_indent="> ",
                                             subsequent_indent="> "))
    cite = lambda e: f"26 CFR {section}({e['para']})({e['sub']}) Example {e['n']}"

    problems = [
        f"## P{i} · {e['title']}\n\n"
        f"**Citation:** {cite(e)}\n\n"
        f"**Answer:** {classify(e['text'])}\n\n"
        f"**Facts:** {e['text']}\n"
        for i, (e, _) in enumerate(kept, 1)
    ]
    passages = [
        f"## {cite(e)}\n\n"
        f"**Source:** {source_id} · **Checked:** {today}\n\n"
        f"{wrap(e['text'])}\n"
        for e, _ in kept
    ]
    return all_ex, kept, dropped, problems, passages


def counts(all_ex, kept, dropped):
    """The denominator, and the reason for every exclusion."""
    reasons = {}
    for _, why in dropped:
        reasons[why] = reasons.get(why, 0) + 1
    return {"found": len(all_ex), "kept": len(kept), "dropped": len(dropped),
            "reasons": reasons}


if __name__ == "__main__":                                  # pragma: no cover
    xml_path, desk_dir = Path(sys.argv[1]), Path(sys.argv[2])
    all_ex, kept, dropped, problems, passages = build(xml_path, desk_dir)
    c = counts(all_ex, kept, dropped)
    print(f"found {c['found']} examples; kept {c['kept']}; left out {c['dropped']}")
    for why, n in sorted(c["reasons"].items()):
        print(f"  {n:>3}  {why}")
