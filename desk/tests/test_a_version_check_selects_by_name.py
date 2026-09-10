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


# ---------------------------------------------------------------------------
# THE SAME DEFECT AGAIN, IN THE FIX FOR ANOTHER ONE.
#
# 0.7.3 replaced the KeyError-raising first line of `ask-desk` with a snippet
# that resolves the newest installed release out of the versioned plugin cache.
# It read `sorted(os.listdir(ROOT))[-1]` — a STRING sort over version directory
# names. Correct today, correct through 0.9.x, and wrong forever after:
#
#     sorted(["0.7.3", "0.10.0"])[-1]  ->  "0.7.3"
#
# The Forge, reading the fix rather than running it, 7 September 2026: *"an
# agent following the documented snippet loads a stale plugin while believing it
# is current — which is the same failure class as [the stale SKILL.md], shipped
# inside the fix for it. Nothing will announce it."*
#
# So the rule above generalises: a version selected by anything other than what
# makes it a version — its NAME in a listing, its NUMBERS in a directory — is
# right by accident. These run the published snippet against a cache that has
# already crossed .9, because that is the only way to fail today on a bug that
# does not bite until then.
# ---------------------------------------------------------------------------

SKILL = HERE / "skills" / "be-the-desk" / "SKILL.md"


def _resolver():
    """The published snippet, up to the point it starts importing the desk."""
    body = SKILL.read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", body, re.S)
    found = [b for b in blocks if "listdir" in b]
    assert len(found) == 1, f"{len(found)} snippets resolve a version; expected 1"
    return found[0].split("sys.path.insert")[0]


def _resolve_in(tmp_path, names):
    """Run it against a plugin cache holding exactly `names`."""
    for n in names:
        (tmp_path / n / "corpus").mkdir(parents=True)
    env = {"os": __import__("os"), "sys": __import__("sys"),
           "SystemExit": SystemExit}
    import os
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(tmp_path)
    try:
        exec(_resolver(), env)                                     # noqa: S102
    finally:
        del os.environ["CLAUDE_PLUGIN_ROOT"]
    return pathlib.Path(env["ROOT"]).name


def test_the_snippet_picks_the_newest_release_today(tmp_path):
    assert _resolve_in(tmp_path, ["0.4.0", "0.7.3", "0.6.2"]) == "0.7.3"


def test_the_snippet_still_picks_the_newest_after_the_minor_passes_nine(tmp_path):
    """THE ONE THAT WOULD HAVE CAUGHT IT. A string sort answers 0.7.3 here."""
    assert _resolve_in(tmp_path, ["0.7.3", "0.9.9", "0.10.0"]) == "0.10.0"


def test_and_after_the_major_does(tmp_path):
    assert _resolve_in(tmp_path, ["0.10.0", "1.0.0", "2.0.0", "10.0.0"]) == "10.0.0"


def test_a_directory_that_is_not_a_version_is_never_chosen(tmp_path):
    """`listdir` returns whatever is there. A crash here would be a dead skill."""
    assert _resolve_in(tmp_path, ["0.7.3", "backup", ".tmp"]) == "0.7.3"


#: A line of the defect as PUBLISHED CODE, after inline-code spans are removed.
#:
#: THE NARROWING IS THE SAME ONE THE TEST ABOVE ALREADY PAID FOR, and I walked
#: into it again the same evening: the first version of this went red on
#: `DECISIONS-2026-09-08-TENTH.md`, the log written to record this very defect,
#: which quotes the broken sort inline while explaining it. A guard that forbids
#: the record from quoting what it records makes the record unwritable.
#:
#: So: a document QUOTING it inline, in backticks, is recording it. A bare line
#: is publishing it, and a bare line is what somebody runs.
_STRING_SORT = re.compile(r"sorted\(os\.listdir\([^)]*\)\)")
_INLINE = re.compile(r"`[^`]*`")


def test_no_document_orders_releases_as_strings():
    """Mechanised, because this shipped once inside the fix for something else."""
    bad = []
    for p in _docs() + [SKILL]:
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _STRING_SORT.search(_INLINE.sub("", line)):
                bad.append(f"{p.relative_to(HERE)}:{n}")
    assert not bad, (
        "a release is chosen by string order: " + ", ".join(bad)
        + ". '0.10.0' sorts BELOW '0.7.3'. Order by the numbers — "
        "key=lambda v: [int(n) for n in v.split('.')]")


def test_the_record_may_still_quote_the_string_sort_it_records():
    """Pinned, for the same reason its sibling above is: the narrowing is the
    kind a later session tightens back after reading the pattern and not the
    reason. Twice in one evening is enough to hold it open with a test."""
    log = HERE / "docs" / "DECISIONS-2026-09-08-TENTH.md"
    body = log.read_text(encoding="utf-8")
    quoted = [ln for ln in body.splitlines() if _STRING_SORT.search(ln)]
    assert quoted, "the log no longer quotes the sort it was written about"
    assert not any(_STRING_SORT.search(_INLINE.sub("", ln)) for ln in quoted), (
        "the log publishes it as a bare line; quote it inline, in backticks")
