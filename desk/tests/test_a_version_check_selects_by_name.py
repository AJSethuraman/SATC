"""A version read out of the listing must name the plugin it wants.

WHY THIS TEST EXISTS AND NOT A NOTE. `docs/TRY-IT.md` and `docs/FORGE-SEARCH.md`
tell the reader to check the installed version against the marketplace listing
RATHER THAN against a number typed into the prose -- because a document that
states a version goes stale the moment the version moves, which happened twice
in four hours on 7 September 2026.

Both then did it like this:

    json.load(open('.claude-plugin/marketplace.json'))['plugins'][1]['version']

WHICH IS THE SAME BUG IN A COSTUME. `[1]` is a typed constant standing in for
`desk`, correct only while the listing happens to hold canon then desk in that
order. Add a plugin sorting before `desk`, or reorder the file, and the command
silently prints ANOTHER PLUGIN'S VERSION -- and prints it to a reader who is
comparing it against `plugin list` to decide whether their install landed. It
would read as a failed install, or worse, certify a stale one.

The failure is quiet, it is in the instruction rather than the code, and it
defeats the very check the paragraph around it exists to make. So the rule is
mechanised where the six copy rules are mechanised: a version lookup names the
plugin, and a positional index into `plugins` is refused wherever it appears.
"""
from __future__ import annotations

import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parents[1]
ROOT = HERE.parent
LISTING = ROOT / ".claude-plugin" / "marketplace.json"

#: `['plugins'][0]` / `["plugins"][2]` — a subscript into the plugin list by
#: position. Selecting by name reads `p['name']=='desk'` instead.
BY_POSITION = re.compile(r"""\[['"]plugins['"]\]\[\d+\]""")


#: The snippet as the documents actually publish it. One of the three sits
#: inside a shell `$(...)`, so the expression is matched rather than sliced off
#: the end of a line.
PUBLISHED = r'''python3 -c "import json;print\((.*?)\)"'''


def _docs() -> list[pathlib.Path]:
    return sorted(HERE.glob("docs/*.md")) + sorted(HERE.glob("*.md"))


def test_no_command_a_reader_runs_reads_the_listing_by_position():
    """A COMMAND, not every mention of the string.

    The first version of this went red on the record of the very defect it
    guards: `DECISIONS-2026-09-07-EIGHTH.md` quotes the broken lookup in the
    paragraph explaining why it was broken. A guard that forbids a document from
    QUOTING a defect makes the log unwritable, and the log is how the next
    session learns the defect exists.

    So it applies to a line that is a command — one carrying `python3`, which is
    what the reader pastes. **This is deliberately narrower than the string.** A
    positional lookup published some other way, in a fenced block with no
    interpreter on the line, would pass here; the second test below is what
    actually exercises what the documents publish, and it would catch that."""
    bad = []
    for p in _docs():
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "python3" in line and BY_POSITION.search(line):
                bad.append(f"{p.relative_to(HERE)}:{n}")
    assert not bad, (
        "a command selects a plugin by position: " + ", ".join(bad)
        + ". Name it — `next(p['version'] for p in ... if p['name']=='desk')` — "
        "or the command prints another plugin's version the day the listing "
        "is reordered, to a reader using it to check their install")


def test_the_record_may_still_quote_the_defect_it_records():
    """Pinned, because the narrowing above is the kind that gets tightened back
    by a later session reading only the pattern and not the reason."""
    log = HERE / "docs" / "DECISIONS-2026-09-07-EIGHTH.md"
    body = log.read_text(encoding="utf-8")
    quoted = [ln for ln in body.splitlines() if BY_POSITION.search(ln)]
    assert quoted, "the log no longer quotes the lookup it was written about"
    assert not any("python3" in ln for ln in quoted), (
        "the log quotes it as a runnable command; quote the expression alone")


def test_the_command_the_documents_publish_actually_returns_this_plugin():
    """RUN, NOT READ. The snippet is the thing the firm pastes; a test that only
    grepped for the right shape would pass on a snippet that does not work."""
    # ONE OF THE THREE IS NESTED INSIDE A SHELL `$(...)`, which is why the
    # expression is matched rather than sliced off the end of the line.
    snippet = re.compile(PUBLISHED)
    published = [(p, m.group(1)) for p in _docs()
                 for m in snippet.finditer(p.read_text(encoding="utf-8"))]
    assert published, "no document publishes a version check any more"

    listing = json.loads(LISTING.read_text(encoding="utf-8"))
    want = next(p["version"] for p in listing["plugins"] if p["name"] == "desk")
    for where, code in published:
        got = eval(code,                                          # noqa: S307
                   {"json": json, "next": next,
                    "open": lambda f, *a, **k: open(LISTING, *a, **k)})
        assert got == want, (
            f"{where.name} publishes a check returning {got!r}; desk is "
            f"{want!r}. The firm pastes this to decide if their install landed")


def test_the_listing_and_the_plugin_manifest_agree():
    """The listing decides what `plugin update` installs; the manifest is what
    the installed copy says it is. They are two files and they have disagreed."""
    listing = json.loads(LISTING.read_text(encoding="utf-8"))
    said = next(p["version"] for p in listing["plugins"] if p["name"] == "desk")
    manifest = json.loads(
        (HERE / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["version"] == said, (
        f"the listing offers {said} and the plugin calls itself "
        f"{manifest['version']}; `plugin update` reads the listing")
