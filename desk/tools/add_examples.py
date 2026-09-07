"""Add a section's worked examples to a desk that already holds its rules.

WHY THIS IS NOT `extract_ecfr.py`. That tool BUILDS a desk: it writes both the
extracted authority and `PROBLEMS.md`, which is the answer key. Exactly one file
in this record was written by it -- `fixed-assets`. Every other desk was
assembled by hand, with problems a person chose, and re-running the builder over
one would overwrite that curation while reporting success.

So this is additive and nothing else. It appends worked examples to the file that
already holds a source's rules, and it touches no problem, no existing passage
and no other source. A desk it has run over is the desk it was, plus authority.

WHAT IT REFUSES, rather than working around:

  a source that is not `public_fetch`     it is not ours to fetch
  a source that is not `may_store: full_text`  it is not ours to copy
  a citation the desk already holds       re-running must not duplicate
  a section `outline()` cannot place      the citation would be a guess

THE LAST ONE IS THE INTERESTING REFUSAL. Five of this record's eCFR sections --
§ 1.446-1, § 1.274-5, § 1.274-5T, § 1.62-2, § 1.6050W-1 -- have label sequences
`outline()` cannot read as a single consistent CFR outline, so it raises. An
example whose paragraph path is a guess is cited to a rule that may not be its
own, which is the defect this record spent 7 September 2026 correcting. Leaving
those sections without their examples is the smaller cost.

    python tools/add_examples.py <desk-dir> <source-id> <YYYY-MM-DD>

where the date is the day the section was FETCHED -- never the day this ran.
"""
from __future__ import annotations

import re
import sys
import tempfile
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import extract_ecfr as ex                                    # noqa: E402
import record                                                # noqa: E402
import tieout                                                # noqa: E402


class Refused(Exception):
    """This section's examples may not be added, and the reason is the message."""


def _file_holding(desk_dir: Path, source_id: str) -> Path:
    """The extracted file this source's passages already live in.

    Found by reading the files rather than by guessing a name: the desks spell
    them `S1.md`, `S1-treas-reg-1-274-12.md` and `treas-reg-1-263a-3.md`, and a
    convention six records each have to remember is not a convention.
    """
    hits = [f for f in sorted((desk_dir / "extracted").glob("*.md"))
            if re.search(rf"^\*\*Source:\*\* {re.escape(source_id)} ",
                         f.read_text(encoding="utf-8"), re.M)]
    if len(hits) != 1:
        raise Refused(f"{source_id} is held in {len(hits)} files, not 1: "
                      f"{[h.name for h in hits]}")
    return hits[0]


def gather(desk: record.Desk, source_id: str, checked: str) -> list[str]:
    """The passage blocks to append. Fetches; does not write."""
    source = desk.source(source_id)
    if source.access != "public_fetch":
        raise Refused(f"{source_id} is access={source.access!r}; not ours to fetch")
    if source.may_store != "full_text":
        raise Refused(f"{source_id} is may_store={source.may_store!r}; not ours "
                      f"to copy")
    if "ecfr.gov" not in source.url:
        raise Refused(f"{source_id} is not an eCFR section: {source.url}")

    raw = tieout._fetch(tieout._ecfr_url(source.url))
    if not any(c.tag == "EXAMPLE" for c in ET.fromstring(raw)):
        raise Refused(f"{source_id} ({source.citation_prefix}) carries no worked "
                      f"examples")
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        f.write(raw)
        tmp = Path(f.name)
    try:
        walked = list(ex.examples(tmp))                 # raises if unplaceable
    finally:
        tmp.unlink(missing_ok=True)

    held = {p.citation for p in desk.passages}
    # THE SAME WRAP AS THE BUILDER, `break_on_hyphens=False` INCLUDED. The
    # default splits "load-carrying" across lines and `parse_passages` rejoins
    # with a space, storing text the publisher never printed.
    wrap = lambda t: "\n".join(textwrap.wrap(t, 78, initial_indent="> ",
                                             subsequent_indent="> ",
                                             break_on_hyphens=False))
    blocks, seen = [], set()
    for e in walked:
        citation = f"{source.citation_prefix}{e['path']} Example {e['n']}"
        if citation in held:
            raise Refused(f"{citation!r} is already in the record; this tool "
                          f"appends and never rewrites")
        if citation in seen:
            raise Refused(f"{citation!r} would be written twice")
        seen.add(citation)
        blocks.append(f"## {citation}\n\n"
                      f"**Source:** {source_id} · **Checked:** {checked} · "
                      f"**Kind:** example\n\n{wrap(e['text'])}\n")
    return blocks


def add(desk_dir: Path, source_id: str, checked: str) -> int:
    ex._date_only(checked)
    desk_dir = Path(desk_dir)
    desk = record.load(desk_dir)
    blocks = gather(desk, source_id, checked)
    target = _file_holding(desk_dir, source_id)
    text = target.read_text(encoding="utf-8").rstrip("\n")
    target.write_text(text + "\n\n---\n\n" + "\n---\n\n".join(blocks),
                      encoding="utf-8")
    record.load(desk_dir)                    # it must still parse, or we broke it
    return len(blocks)


if __name__ == "__main__":                                  # pragma: no cover
    if len(sys.argv) != 4:
        sys.exit(__doc__.strip().splitlines()[-3].strip())
    n = add(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
    print(f"added {n} worked example(s) to {sys.argv[1]} from {sys.argv[2]}")
