"""The TIN/SSN byte-scan shared by each tool's no-PII-leak guard.

A deterministic, dependency-free scan for taxpayer-identifier patterns in text
(and, by extension, the XML members of a saved workbook). Each tool points this
at the surfaces it must keep clean — for ``credit-population-bench`` that is the
shipped tool / repo / demo fixtures (the runtime populated workbook is
deliberately out of scope; it runs only on bank equipment). Keeping the pattern
set in one place means a tightening here strengthens every tool at once.
"""

from __future__ import annotations

import io
import re
import zipfile

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EIN_RE = re.compile(r"\b\d{2}-\d{7}\b")
NINE_DIGIT_RE = re.compile(r"\b\d{9}\b")

_ALL = (("ssn", SSN_RE), ("ein", EIN_RE), ("nine_digit", NINE_DIGIT_RE))


def find_tin(text: str) -> list[tuple[str, str]]:
    """Return ``(kind, match)`` for every TIN-shaped hit in ``text``."""
    hits: list[tuple[str, str]] = []
    for kind, rx in _ALL:
        hits.extend((kind, m.group(0)) for m in rx.finditer(text))
    return hits


def assert_no_tin(text: str, where: str = "text") -> None:
    """Raise ``AssertionError`` if any TIN-shaped pattern appears in ``text``."""
    hits = find_tin(text)
    assert not hits, f"TIN-shaped pattern(s) found in {where}: {hits[:5]}"


def workbook_xml_text(data: bytes) -> str:
    """Concatenate every ``.xml`` member of a saved ``.xlsx``/``.xlsm`` for scanning."""
    out: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.endswith(".xml"):
                out.append(z.read(name).decode("utf-8", errors="ignore"))
    return "\n".join(out)


def assert_workbook_no_tin(data: bytes, where: str = "workbook") -> None:
    assert_no_tin(workbook_xml_text(data), where)
