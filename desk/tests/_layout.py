"""Where this plugin's own files are, in BOTH layouts it is ever run from.

THE DEFECT THIS EXISTS TO END, reported by Forge-Desk on 14 September 2026 and
reproduced here on 0.28.0. Three checks assert a fact about the **installed**
plugin — that the marketplace listing and the plugin manifest agree, and that
the version command the documents publish returns this plugin. Every one of
them resolved the listing as `<desk>/../.claude-plugin/marketplace.json`, which
is the REPOSITORY layout, so **none of them could run where the thing they
check is true**:

    cd ~/.claude/plugins/cache/satc/desk/0.28.0 && python -m pytest -q
    ...
    FileNotFoundError: .../plugins/cache/satc/desk/desk/.claude-plugin/plugin.json
    3 failed, 1251 passed, 1 skipped

That is the same shape as the canon-lookup bug of 4 September (`_canon.py`),
which this file deliberately copies the fix for: *"the repository is the only
place the tests ran, and there the wrong rule and the right one agree."*

THE TWO LAYOUTS, and only one of them is obvious.

    repository      <repo>/desk/                        listing at <repo>/.claude-plugin/
    installed       <plugins>/cache/<market>/desk/<v>/  listing at <plugins>/marketplaces/<market>/.claude-plugin/

The plugin's OWN manifest is at `<plugin>/.claude-plugin/plugin.json` in both,
which is why only the listing needs finding.

IT RAISES RATHER THAN SKIPPING. A skipped check is not a passed one, and these
three already spent a week reporting green from the one place they could not
fail. If the listing is genuinely absent the message names every path tried, so
the reader can tell a broken install from a broken test.
"""
from __future__ import annotations

import os
from pathlib import Path

#: This plugin's root — the directory holding `pool.py`, `corpus/` and
#: `.claude-plugin/`. True in both layouts, which is why nothing below has to
#: find it.
PLUGIN = Path(__file__).resolve().parents[1]

#: The plugin's own manifest. Same relative place in both layouts.
MANIFEST = PLUGIN / ".claude-plugin" / "plugin.json"


class ListingMissing(RuntimeError):
    """The marketplace listing is not where either layout puts it."""


def _candidates() -> list[Path]:
    """Everywhere the listing can legitimately be, in the order to try."""
    out: list[Path] = []
    if env := os.environ.get("SATC_MARKETPLACE"):
        out.append(Path(env))
    # Repository: a sibling of this plugin's folder.
    out.append(PLUGIN.parent / ".claude-plugin" / "marketplace.json")
    # Installed: the cache nests <market>/<plugin>/<version> under `cache/`,
    # and the listing lives beside it under `marketplaces/<market>/`. The
    # `cache` check is what stops a repository path being read as one of these.
    parents = PLUGIN.parents
    if len(parents) > 3 and parents[2].name == "cache":
        out.append(parents[3] / "marketplaces" / parents[1].name
                   / ".claude-plugin" / "marketplace.json")
    return out


def listing() -> Path:
    """The marketplace listing, whichever layout this is running from."""
    tried = _candidates()
    for path in tried:
        if path.is_file():
            return path
    raise ListingMissing(
        "no marketplace listing where either layout puts it. Tried:\n  "
        + "\n  ".join(str(p) for p in tried)
        + "\nSet SATC_MARKETPLACE to point at one, or this is a broken "
          "install rather than a broken test.")
