"""Bring SATC's tenets across, once, with their evidence intact.

WHOLESALE, NOT RE-PARSED. Each tenet in `SATC/docs/SOFTWARE-TENETS.md` carries
its evidence as prose -- quoted incidents, commit hashes, the firm's own words,
test docstrings. Pulling individual citations out of that would mean inventing
structure the source does not have, and inventing structure is how a migration
loses the half nobody checks. So each body is carried as ONE evidence entry,
cited to where it came from, and future incidents append beside it properly
structured.

WHAT IS ALREADY HERE IS NOT TOUCHED. S31 carries two hand-written entries from
this week; the migration leaves them and does not add a bulk duplicate on top.
A migration that overwrites curation is a migration that destroys the thing it
was moving.

RUN ONCE. It is kept because how the record was populated is part of the
record, and because a reader a year from now should be able to see that these
were carried rather than composed.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import record as R  # noqa: E402

SOURCE = Path(__file__).resolve().parents[1] / "docs" / "SOFTWARE-TENETS.md"
MINED = "2026-08-27"          # the date the source file says it was mined
CITATION = "docs/SOFTWARE-TENETS.md — mined from the whole history of that repository"

HEAD = re.compile(r"^## (S\d+) · (.+)$", re.M)


def read_source(text: str) -> list[tuple[str, str, str]]:
    """(id, title, body) for every tenet in the source."""
    heads = list(HEAD.finditer(text))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[h.end():end].strip()
        # THE SOURCE'S OWN FURNITURE IS NOT EVIDENCE. That file separates
        # tenets with `---` and groups them under `# Part N` headings, so a
        # naive slice carries the separator and the next section's title into
        # the body -- and the renderer then emits a SECOND separator beside the
        # first. Caught by the round-trip check, which is the second real bug
        # it has found.
        while True:
            lines = body.splitlines()
            while lines and not lines[-1].strip():
                lines.pop()
            if lines and (lines[-1].strip() == "---" or lines[-1].startswith("# ")):
                lines.pop()
                body = "\n".join(lines).strip()
                continue
            break
        out.append((h.group(1), h.group(2).strip(), body))
    return out


def main() -> int:
    source = read_source(SOURCE.read_text(encoding="utf-8"))
    have = {t.id: t for t in R.parse_tenets(R.TENETS.read_text(encoding="utf-8"))}

    merged: list[R.Tenet] = []
    carried = kept = 0
    for tid, title, body in sorted(source, key=lambda r: int(r[0][1:])):
        if tid in have and have[tid].evidence:
            merged.append(have[tid])          # curation wins over bulk
            kept += 1
            continue
        merged.append(R.Tenet(id=tid, title=title, evidence=(
            R.Evidence(project="SATC", when=MINED, citation=CITATION, detail=body),)))
        carried += 1

    text = R.render_tenets(merged)
    R.TENETS.write_text(text, encoding="utf-8")

    back = R.parse_tenets(text)
    bare = [t.id for t in back if t.bare]
    print(f"{len(source)} tenet(s) in the source, {len(back)} in the record")
    print(f"  {carried} carried across, {kept} left as already curated")
    print(f"  bare (no evidence): {bare or 'none'}")
    print(f"  round-trips byte-identical: {R.render_tenets(back) == text}")
    return 0 if not bare and R.render_tenets(back) == text else 1


if __name__ == "__main__":
    raise SystemExit(main())
