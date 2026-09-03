"""The walkthrough, and the three ways it could quietly start lying.

The firm rejected the last set of procedures in one line -- *"These are not
pleasant procedures for a user"* -- and the replacement is a photographed
walkthrough of the browser. The risk in a photographed document is not that it
is unpleasant. It is that the software moves and the document does not, and a
reader trusts it, follows it, and ends up somewhere the page does not go.

So the document refuses to be written when it would be wrong. These tests are
that refusal, held in place.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import walkthrough as wt  # noqa: E402
import walkthrough_html as wh  # noqa: E402


@pytest.fixture
def screens():
    """The last inventory anybody photographed out of the running software."""
    return wt.from_json(wt.INVENTORY_FILE.read_text(encoding="utf-8"))


@pytest.fixture
def registry():
    return wt.load_registry()


# ── the document cannot be wrong about the software ───────────────────────

def test_every_control_on_every_screen_is_answered_for(screens, registry):
    """The check that makes the whole thing worth reading."""
    gaps = wt.missing(screens, registry)
    assert not gaps, "\n  ".join(["the walkthrough would be wrong about:"]
                                 + gaps)


def test_a_control_nobody_wrote_about_stops_the_document(screens, registry):
    extra = wt.Screen(key=screens[0].key, heading="x", controls=[
        wt.Control(kind="button", shape="button||new", label="Do the thing")])
    gaps = wt.missing([extra], {**registry, extra.key: {}})
    assert any("Do the thing" in g for g in gaps)
    with pytest.raises(RuntimeError, match="wrong about"):
        wh.render([extra], {**registry, extra.key: {}}, Path("/nowhere"))


def test_a_note_about_a_control_that_has_gone_stops_the_document(screens,
                                                                 registry):
    """The worse of the two: it tells a preparer to press something that is
    not there, and they will look for it."""
    one = screens[0]
    said = {one.key: {**(registry.get(one.key) or {}),
                      "button:Press the old thing": "long gone"}}
    gaps = wt.missing([one], {**registry, **said})
    assert any("not on the screen any more" in g for g in gaps)


def test_a_screen_that_was_never_reached_is_reported(registry):
    gaps = wt.missing([], registry)
    assert len(gaps) >= len(wt.SCREENS)
    assert all("never reached" in g for g in gaps[:len(wt.SCREENS)])


def test_the_chrome_is_explained_once_and_has_to_be_somewhere(screens,
                                                             registry):
    """`_everywhere` covers a control on every screen. An entry there for
    something on no screen is the same staleness as any other."""
    assert registry["_everywhere"], "nothing is claimed to be on every screen"
    invented = {**registry, "_everywhere": {**registry["_everywhere"],
                                            "link:Nowhere": "gone"}}
    gaps = wt.missing(screens, invented)
    assert any("is explained as being on every screen and is on none"
               in g for g in gaps)


# ── the inventory is folded the way a reader needs it ─────────────────────

def test_a_row_drawn_many_times_is_one_thing_to_explain():
    """The review page has thirty-eight `Change` buttons and one affordance."""
    raw = [{"kind": "button", "label": "Change", "shape": "b|link|/back{to}"}
           for _ in range(38)]
    got = wt.fold(raw)
    assert len(got) == 1 and got[0].count == 38
    assert got[0].label == "Change"


def test_two_controls_that_look_alike_but_go_elsewhere_stay_apart():
    """`← Back` and `Never mind` are both `button.link` on the same page and
    are two different things. The form each posts tells them apart; the
    styling does not."""
    raw = [{"kind": "button", "label": "← Back", "shape": "b|link|/back"},
           {"kind": "button", "label": "Never mind — nothing to change",
            "shape": "b|link|/back{resume}"}]
    got = wt.fold(raw)
    assert len(got) == 2
    assert {c.label for c in got} == {"← Back",
                                      "Never mind — nothing to change"}


def test_a_label_that_is_an_identifier_is_not_used_as_a_name():
    """The home page's link to an engagement is captioned `2026-0001`, which is
    a different string next week. Keying an explanation to it would mean the
    registry went stale every time anybody looked."""
    got = wt.fold([{"kind": "link", "label": "2026-0001",
                    "shape": "a|main|/engagement/<x>"}])
    assert got[0].label == "", got[0]
    assert got[0].examples == ("2026-0001",)
    assert "2026-0001" not in got[0].key


def test_the_visibility_test_does_not_count_what_a_preparer_cannot_see():
    """MEASURED, NOT ASSUMED, and it was wrong the first time.

    `offsetParent !== null` is true for a textarea inside a CLOSED <details> in
    Chromium, which reports a 36px box as well. The first cut of this harness
    used it and counted twenty-nine sentence boxes on a screen showing two --
    the same proxy failure, from the other side, as `innerText` reading '' for
    a subtree that is laid out but not rendered.

    This test holds the fix in the source rather than in anybody's memory.
    """
    assert "checkVisibility" in wt.INVENTORY
    assert "offsetParent !== null;" not in wt.INVENTORY, (
        "the harness is back to asking a question that has the wrong answer"
    )


# ── the document itself ───────────────────────────────────────────────────

def test_the_walkthrough_is_one_file(screens, registry):
    shots = ROOT / "out" / "walkthrough" / "shots"
    if not shots.exists():
        pytest.skip("nothing photographed here; run `python capture.py` first")
    doc = wh.render(screens, registry, shots)
    assert wh.external_references(doc) == [], (
        "the walkthrough would arrive somewhere else with holes in it"
    )
    assert "data:image/png;base64," in doc, "no screenshot reached the page"
    for key, heading in wt.SCREENS:
        assert heading in doc, f"{key} is not in the document"


def test_nothing_real_is_photographed():
    """`leads.xlsx` is the firm's real workbook and holds real people. The
    harness reads a fabricated file that says so in its first line."""
    import re

    spec = json.loads(wt.DEMO.read_text(encoding="utf-8"))
    assert "FABRICATED" in spec["_comment"]
    assert not any("leads.xlsx" in str(v) for v in spec["rows"])

    # Every mention of the workbook, and what it is. `demo-leads.xlsx` is the
    # throwaway one this builds; a bare `leads.xlsx` is the firm's, and the
    # only place it may appear is a line saying not to open it.
    named = re.compile(r"(?<!demo-)\bleads\.xlsx")
    for source in (ROOT / "capture.py", ROOT / "walkthrough.py"):
        lines = source.read_text(encoding="utf-8").splitlines()
        for n, line in enumerate(lines, 1):
            if not named.search(line):
                continue
            # The warning is a sentence, and a sentence wraps. Read the line
            # with its neighbours rather than demanding the words land on the
            # same one.
            near = " ".join(lines[max(0, n - 2):n + 1]).lower()
            assert "never" in near or "real" in near, (
                f"{source.name}:{n} names the firm's real workbook, and not "
                f"in a warning about it: {line.strip()!r}"
            )


def test_an_explanation_is_written_for_a_person_doing_the_work(registry):
    """The register the firm set: no term of art, and nothing built out of the
    software's own vocabulary. `pricing.spec.py` enforces the same thing over
    the published price page; this is that idea, on the other document."""
    banned = ("engagement letter governs", "pursuant", "herein", "shall be",
              "at our discretion", "constitutes", "deemed")
    for screen, entries in registry.items():
        for key, said in (entries or {}).items():
            if not said:
                continue
            low = str(said).lower()
            for word in banned:
                assert word not in low, f"{screen}/{key}: {word!r}"
            longest = max((len(s.split())
                           for s in str(said).replace(";", ".").split(". ")),
                          default=0)
            assert longest <= 34, (
                f"{screen}/{key}: a {longest}-word sentence was written to be "
                f"complete rather than to be read"
            )
