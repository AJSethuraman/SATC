"""Every invariant's citation points at a line that exists.

A rule cited to `file:line` is only a citation if the file is there and has
that line. This does not prove the line SAYS the rule -- that was checked by
reading when each invariant was written -- but it catches the drift that
makes a citation quietly point at nothing.
"""

from __future__ import annotations

import re

import pytest

from season_sim import invariants as I
from season_sim import paths

CITE = re.compile(r"^(?P<path>[^:]+?)(?::(?P<a>\d+)(?:-(?P<b>\d+))?)?$")


def _all_sources():
    for code, inv in sorted(I.REGISTRY.items()):
        for src in inv.sources:
            yield code, src


@pytest.mark.parametrize("code,src", list(_all_sources()))
def test_each_cited_file_and_line_exists(code, src):
    m = CITE.match(src)
    assert m, f"{code}: {src!r} is not path[:line[-line]]"
    path = paths.REPO / m.group("path")
    assert path.exists(), f"{code}: {path} does not exist"
    if m.group("a"):
        lines = path.read_text(encoding="utf-8", errors="replace").count("\n") + 1
        last = int(m.group("b") or m.group("a"))
        assert int(m.group("a")) <= last <= lines, f"{code}: {src} past the end ({lines} lines)"
