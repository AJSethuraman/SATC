"""Open a template, open a section, edit it — without breaking the document.

The firm asked for this in as many words on 26 August 2026, and priced it
themselves: *"for editing these this may be overkill but i do not care. i want
it to be very straightforward and simple. like i can just click a template,
open a section, edit it"*.

The danger in a wording editor is not that it refuses an edit. It is that it
ACCEPTS one and quietly changes what the document says or fails to say: a
merge field dropped, so a real value silently stops printing; a conditional
mangled, so a block that should have vanished appears; markup rebuilt slightly
differently, so the page a person saved is not the page they were shown.

So the property under test is the round trip: `to_html(to_text(x))` returns
`x`, for every block in all ten templates. A block that cannot round-trip is
read-only rather than mangled, and that is checked too.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import editor  # noqa: E402
import merge  # noqa: E402

TEMPLATES = sorted(editor.TEMPLATE_DIR.glob("SATC*.html"))
assert TEMPLATES, "no templates found"


def _blocks(path):
    html = path.read_text(encoding="utf-8")
    return html, [b for s in editor.sections(html) for b in s.blocks]


# ── the round trip ────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.stem)
def test_every_editable_block_round_trips(path):
    """Text in, identical HTML out. The property the whole editor rests on."""
    _, blocks = _blocks(path)
    for b in blocks:
        if b.editable:
            assert editor.to_html(b.text, like=b.html) == b.html, (
                f"{path.name} {b.id}: the editor would rewrite this block "
                f"merely by opening and saving it"
            )


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.stem)
def test_a_block_it_cannot_rebuild_is_read_only(path):
    """The failure mode this replaces: mangling it instead."""
    _, blocks = _blocks(path)
    for b in blocks:
        if not b.editable:
            assert b.reason, f"{path.name} {b.id}: read-only with no reason given"


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.stem)
def test_saving_every_block_unchanged_changes_nothing(path):
    """The strongest version, and the one a person actually does: open a
    section, decide it is fine, and save it anyway."""
    html, blocks = _blocks(path)
    edits = {b.id: b.text for b in blocks if b.editable}
    after, changed = editor.apply(html, edits)
    assert changed == [], f"{path.name}: saving unchanged text reported changes"
    assert after == html, f"{path.name}: saving unchanged text rewrote the file"


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.stem)
def test_no_template_has_a_section_with_nothing_in_it(path):
    _, blocks = _blocks(path)
    assert blocks, f"{path.name}: the editor finds nothing to edit"


# ── what an edit may not do ───────────────────────────────────────────────

@pytest.fixture
def letter():
    p = editor.TEMPLATE_DIR / "SATC Engagement Letter - Tax Preparation.html"
    return p.read_text(encoding="utf-8")


def _first_with_field(html):
    for s in editor.sections(html):
        for b in s.blocks:
            if b.editable and b.fields:
                return b
    raise AssertionError("no editable block carries a field")


def test_dropping_a_merge_field_is_refused(letter):
    """The quiet one. The document still renders; a real value stops printing
    and nothing anywhere complains."""
    b = _first_with_field(letter)
    gone = b.text.replace(f"<<{b.fields[0]}>>", "")
    with pytest.raises(editor.EditError, match=f"drop <<{b.fields[0]}>>"):
        editor.apply(letter, {b.id: gone})


def test_inventing_a_merge_field_is_refused(letter):
    b = _first_with_field(letter)
    with pytest.raises(editor.EditError, match="registry does not record"):
        editor.apply(letter, {b.id: b.text + " <<ClientMiddleName>>"})


def test_writing_a_conditional_is_refused(letter):
    """`[[IF]]` decides whether whole blocks appear. That is structure."""
    b = _first_with_field(letter)
    with pytest.raises(editor.EditError, match="structure"):
        editor.apply(letter, {b.id: b.text + " [[IF JointReturn]]"})


def test_writing_an_open_decision_is_refused(letter):
    b = _first_with_field(letter)
    with pytest.raises(editor.EditError, match="structure|open decision"):
        editor.apply(letter, {b.id: b.text + " [CONFIRM: ask the firm]"})


def test_emptying_a_block_is_refused(letter):
    b = _first_with_field(letter)
    with pytest.raises(editor.EditError, match="gap in the document"):
        editor.apply(letter, {b.id: "   "})


def test_a_read_only_block_cannot_be_saved_through_the_editor(letter):
    locked = [b for s in editor.sections(letter) for b in s.blocks if not b.editable]
    if not locked:
        pytest.skip("this template has no read-only blocks")
    with pytest.raises(editor.EditError, match="read-only"):
        editor.apply(letter, {locked[0].id: "anything at all"})


def test_html_a_person_types_is_escaped_not_executed(letter):
    """Someone writing `<b>` in the box gets the characters, not a tag. The
    little markup is the only markup."""
    b = _first_with_field(letter)
    after, _ = editor.apply(letter, {b.id: b.text + " <script>x</script>"})
    block = editor.find(after, b.id)
    assert "<script>" not in block.html
    assert "&lt;script&gt;" in block.html


# ── all or nothing ────────────────────────────────────────────────────────

def test_one_bad_edit_in_a_section_saves_none_of_it(letter):
    """A section that saved half of itself would leave a document nobody can
    reason about, and the person would have to work out which half landed."""
    blocks = [b for s in editor.sections(letter) for b in s.blocks if b.editable]
    good, bad = blocks[0], _first_with_field(letter)
    with pytest.raises(editor.EditError):
        editor.apply(letter, {good.id: good.text + " Changed.",
                              bad.id: bad.text.replace(f"<<{bad.fields[0]}>>", "")})


def test_edits_to_several_blocks_all_land(letter):
    blocks = [b for s in editor.sections(letter) for b in s.blocks if b.editable][:3]
    edits = {b.id: b.text + f" Sentence {i}." for i, b in enumerate(blocks)}
    after, changed = editor.apply(letter, edits)
    assert sorted(changed) == sorted(edits)
    for i, b in enumerate(blocks):
        assert f"Sentence {i}." in editor.find(after, b.id).text


def test_a_later_block_is_not_shifted_by_an_earlier_edit(letter):
    """Applied back to front for exactly this reason: a longer first sentence
    must not move the second one out from under its own offsets."""
    blocks = [b for s in editor.sections(letter) for b in s.blocks if b.editable][:2]
    first, second = blocks
    after, _ = editor.apply(letter, {
        first.id: first.text + " " + ("padding " * 40),
        second.id: second.text + " Second."})
    assert "Second." in editor.find(after, second.id).text
    assert "padding" in editor.find(after, first.id).text


# ── the edit reaches a real document ──────────────────────────────────────

def test_an_edit_reaches_the_rendered_document(letter, tmp_path):
    """The point of the whole thing, end to end."""
    import cli
    import json

    b = [x for s in editor.sections(letter) for x in s.blocks
         if x.editable and not x.fields][0]
    edited, _ = editor.apply(letter, {b.id: "This sentence was typed into the editor."})
    tpl = tmp_path / "SATC Engagement Letter - Tax Preparation.html"
    tpl.write_text(edited, encoding="utf-8")

    record = cli.build_record(json.loads(
        (ROOT / "samples" / "tax-opening-package.json").read_text(encoding="utf-8")))
    html = merge.render(tpl.read_text(encoding="utf-8"), record).html
    assert "This sentence was typed into the editor." in html


def test_an_edited_template_still_renders_with_nothing_left_unresolved(letter, tmp_path):
    """An editor that produced a document with a hole in it would be worse
    than no editor: `merge.render` refuses, and the render is the thing the
    firm actually runs."""
    import cli
    import json

    blocks = [x for s in editor.sections(letter) for x in s.blocks if x.editable]
    edited, _ = editor.apply(letter, {b.id: b.text + " Reworded." for b in blocks})
    record = cli.build_record(json.loads(
        (ROOT / "samples" / "tax-opening-package.json").read_text(encoding="utf-8")))
    html = merge.render(edited, record).html
    assert "&lt;&lt;" not in html and "[CONFIRM:" not in html


# ── saving to disk ────────────────────────────────────────────────────────

def test_save_writes_nothing_when_an_edit_is_refused(tmp_path):
    name = "SATC Engagement Letter - Tax Preparation.html"
    src = (editor.TEMPLATE_DIR / name).read_text(encoding="utf-8")
    (tmp_path / name).write_text(src, encoding="utf-8")

    b = _first_with_field(src)
    with pytest.raises(editor.EditError):
        editor.save(name, {b.id: b.text.replace(f"<<{b.fields[0]}>>", "")},
                    template_dir=tmp_path)
    assert (tmp_path / name).read_text(encoding="utf-8") == src


def test_save_refuses_a_path_outside_the_template_folder(tmp_path):
    with pytest.raises(editor.EditError):
        editor.save("../../etc/passwd", {"top.1": "x"}, template_dir=tmp_path)


def test_save_writes_the_edit(tmp_path):
    name = "SATC Engagement Letter - Tax Preparation.html"
    src = (editor.TEMPLATE_DIR / name).read_text(encoding="utf-8")
    (tmp_path / name).write_text(src, encoding="utf-8")

    b = [x for s in editor.sections(src) for x in s.blocks if x.editable][0]
    changed = editor.save(name, {b.id: b.text + " Added."}, template_dir=tmp_path)
    assert changed == [b.id]
    assert "Added." in (tmp_path / name).read_text(encoding="utf-8")


# ── the crib at the bottom is not editable ────────────────────────────────

@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.stem)
def test_the_field_reference_is_not_offered_for_editing(path):
    """It is documentation for whoever wires the software, it is stripped
    before a client sees the page, and it quotes every merge token in the
    template — so offering it would invite an edit that looks like it changes
    the document and does not."""
    html, blocks = _blocks(path)
    ref_at = html.find(editor.REF)
    if ref_at == -1:
        pytest.skip("no reference block")
    assert all(b.end <= ref_at for b in blocks)


# ── one bold, not two ─────────────────────────────────────────────────────

def test_the_stylesheet_gives_b_and_strong_the_same_rule():
    """Measured in a browser on 26 August 2026, on the delivery letter:
    `<strong>` resolved to weight 600 in navy and `<b>` to the browser default
    700 in body ink. Two visibly different bolds sat in one paragraph of a
    client's letter, and nothing in the source hinted at it.

    Both tags mean the same thing to a reader and the templates use both, so
    the stylesheet has to agree with the reader. This also makes it safe for
    the editor to keep whichever tag a block already uses.
    """
    css = (editor.TEMPLATE_DIR / "satc-doc.css").read_text(encoding="utf-8")
    for context in ("body", "intro"):
        assert f".{context} strong,.{context} b{{" in css, (
            f".{context} styles <strong> without styling <b> the same way, so "
            f"the two render at different weights on a client's document"
        )


def test_no_editable_block_mixes_the_two_bold_tags():
    """A block using both cannot round-trip byte for byte, so it would either
    be read-only or be rewritten on save. Five did; they were normalised."""
    import re
    for path in TEMPLATES:
        html, blocks = _blocks(path)
        for b in blocks:
            if re.search(r"<b>", b.html) and re.search(r"<strong>", b.html):
                raise AssertionError(
                    f"{path.name} {b.id} mixes <b> and <strong>; normalise it "
                    f"to one or the editor cannot save it unchanged"
                )


# ── whole sections ────────────────────────────────────────────────────────
#
# "for editing stuff it has to be easy to add and take out sections as well"
# -- the firm, 26 August 2026. Easy is the ask; the tests are about what easy
# must not cost.

@pytest.fixture
def workshop(tmp_path):
    """A copy of the real templates, so a test can rewrite one."""
    import shutil
    d = tmp_path / "templates"
    shutil.copytree(editor.TEMPLATE_DIR, d)
    return d


ONBOARDING = "SATC Onboarding Letter.html"


def _numbers(html):
    return [s["number"] for s in editor.outline(html)]


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.stem)
def test_the_outline_finds_every_numbered_section(path):
    html = path.read_text(encoding="utf-8")
    secs = editor.outline(html)
    if not secs:
        pytest.skip("no numbered sections")

    # NOT 01..n. Two sections may share a number when they are exclusive
    # branches of one clause -- the delivery letter's 03 is "Signing the
    # e-file authorization" or "Filing the paper returns", never both. What
    # must hold is that the numbers start at 01 and never skip.
    seen = []
    for s in secs:
        if not seen or s["number"] != seen[-1]:
            seen.append(s["number"])
    assert seen == [f"{i:02d}" for i in range(1, len(seen) + 1)], (
        f"{path.name}: the numbers skip or repeat out of order: {seen}"
    )
    for s in secs:
        assert s["title"] and s["title"] != "(no heading)"


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.stem)
def test_a_section_span_stops_at_its_own_closing_div(path):
    """A `.sec` holds `.callout` divs. Taking the first `</div>` after the
    heading would cut a section in half and leave the rest orphaned."""
    html = path.read_text(encoding="utf-8")
    body = editor.body_of(html)
    for s in editor.outline(html):
        block = body[s["start"]:s["end"]]
        assert block.count("<div") == block.count("</div>"), (
            f"{path.name} section {s['number']}: unbalanced divs in the span"
        )


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.stem)
def test_renumbering_a_template_nobody_touched_changes_nothing(path):
    html = path.read_text(encoding="utf-8")
    assert editor.renumber(html) == html, f"{path.name} is not numbered in order"


# ── removing ──────────────────────────────────────────────────────────────

def test_removing_a_section_renumbers_the_rest():
    """Every FIELDS doc says it: a client should never see 03 followed by 05.
    The numbers exist so somebody can point at a clause on the phone."""
    html = (editor.TEMPLATE_DIR / ONBOARDING).read_text(encoding="utf-8")
    before = editor.outline(html)
    after, _ = editor.remove_section(html, "03")
    assert _numbers(after) == [f"{i:02d}" for i in range(1, len(before))]
    assert "Your previous accountant" not in editor.body_of(after)


def test_two_branches_of_one_clause_keep_sharing_their_number():
    """The delivery letter numbers both `[[IF EFiled]]` and `[[IF PaperFiled]]`
    03, because exactly one prints and they are one clause in two versions.

    A first version of `renumber` counted sections straight through. It would
    have made the paper branch 04 and pushed the real 04 to 05 -- a document
    broken by the tool that was tidying it. Caught by running the renumber
    over every template and asserting nothing moved.
    """
    name = "SATC Tax Return Delivery Letter.html"
    html = (editor.TEMPLATE_DIR / name).read_text(encoding="utf-8")
    shared = [s["number"] for s in editor.outline(html)]
    assert shared.count("03") == 2, "the branch pair this pins is gone"
    assert editor.renumber(html) == html


def test_removing_a_conditional_section_takes_its_markers_with_it():
    """Section 03 of the onboarding letter is wrapped in `[[IF PriorFirm]]`.
    Leaving the markers behind would wrap whatever followed it instead."""
    html = (editor.TEMPLATE_DIR / ONBOARDING).read_text(encoding="utf-8")
    after, taken = editor.remove_section(html, "03")
    assert "[[IF PriorFirm]]" not in editor.body_of(after)
    assert "PriorFirm" in taken, "the flag was not reported as removed"


def test_removing_a_section_reports_the_fields_it_took():
    html = (editor.TEMPLATE_DIR / ONBOARDING).read_text(encoding="utf-8")
    _, taken = editor.remove_section(html, "03")
    assert "PriorFirmName" in taken


def test_the_registry_stops_claiming_a_template_that_no_longer_uses_a_field(tmp_path):
    """The quiet half of removing a section. The document is fine; the
    registry now says a field is used somewhere it is not, and the next person
    to read it is misled."""
    reg = tmp_path / "fields.yaml"
    reg.write_text(
        "fields:\n"
        "  - field: SomeField\n"
        '    label: "Some field"\n'
        "    templates: [tax-letter, onboarding-letter]\n"
        "flags: []\nlists: []\n", encoding="utf-8")
    effect = editor.registry_effect("onboarding-letter", ["SomeField"], reg)
    assert effect == {"update": ["SomeField"], "orphan": []}
    editor.drop_from_registry("onboarding-letter", ["SomeField"], reg)
    assert "templates: [tax-letter]" in reg.read_text(encoding="utf-8")


def test_a_removal_that_would_orphan_a_field_is_refused(workshop, tmp_path):
    """Section 02 of the onboarding letter holds the only `<<ClientEmail>>` in
    it. Removing it is a decision about whether the field is retired, and that
    is not a change to this document."""
    with pytest.raises(editor.EditError, match="used by no template at all"):
        editor.save_section(ONBOARDING, "onboarding-letter", remove="02",
                            template_dir=workshop)
    assert "ClientEmail" in (workshop / ONBOARDING).read_text(encoding="utf-8"), \
        "a refused removal still edited the file"


def test_removing_an_unknown_section_is_refused(workshop):
    with pytest.raises(editor.EditError, match="no section"):
        editor.save_section(ONBOARDING, "onboarding-letter", remove="99",
                            template_dir=workshop)


# ── adding ────────────────────────────────────────────────────────────────

def test_a_new_section_lands_where_it_was_asked_for(workshop):
    editor.save_section(ONBOARDING, "onboarding-letter",
                        title="How we keep in touch",
                        text="We email once when it is ready.", after="02",
                        template_dir=workshop)
    secs = editor.outline((workshop / ONBOARDING).read_text(encoding="utf-8"))
    assert [s["title"] for s in secs][2] == "How we keep in touch"
    assert [s["number"] for s in secs] == [f"{i:02d}" for i in range(1, len(secs) + 1)]


def test_a_new_section_is_editable_like_any_other(workshop):
    """It is not a special block. Whatever was typed must come back through
    the same round trip as prose that was there all along."""
    editor.save_section(ONBOARDING, "onboarding-letter", title="A heading",
                        text="Something **important** to say.",
                        template_dir=workshop)
    html = (workshop / ONBOARDING).read_text(encoding="utf-8")
    block = next(b for s in editor.sections(html) for b in s.blocks
                 if "important" in b.text)
    assert block.editable and block.text == "Something **important** to say."


def test_a_new_section_cannot_carry_a_merge_field(workshop):
    """It would be registered against no template, and the render would refuse
    at the client's document rather than in this form."""
    with pytest.raises(editor.EditError, match="merge field"):
        editor.save_section(ONBOARDING, "onboarding-letter", title="Fees",
                            text="Your fee is <<EstimateTotal>>.",
                            template_dir=workshop)


def test_a_new_section_cannot_carry_a_conditional(workshop):
    with pytest.raises(editor.EditError, match="structure|conditional"):
        editor.save_section(ONBOARDING, "onboarding-letter", title="Maybe",
                            text="[[IF JointReturn]] Both of you sign.",
                            template_dir=workshop)


def test_a_section_needs_a_heading_and_something_to_say(workshop):
    with pytest.raises(editor.EditError, match="heading"):
        editor.save_section(ONBOARDING, "onboarding-letter", title="",
                            text="words", template_dir=workshop)
    with pytest.raises(editor.EditError, match="gap"):
        editor.save_section(ONBOARDING, "onboarding-letter", title="A heading",
                            text="  ", template_dir=workshop)


def test_html_typed_into_a_new_section_is_escaped(workshop):
    editor.save_section(ONBOARDING, "onboarding-letter", title="Notes",
                        text="Use <script>alert(1)</script> carefully.",
                        template_dir=workshop)
    html = (workshop / ONBOARDING).read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_an_added_section_still_renders(workshop):
    """The point of the whole thing: the document still merges afterwards."""
    import cli
    import json
    editor.save_section("SATC Engagement Letter - Tax Preparation.html",
                        "tax-letter", title="How we keep in touch",
                        text="We email once when it is ready.",
                        template_dir=workshop)
    record = cli.build_record(json.loads(
        (ROOT / "samples" / "tax-opening-package.json").read_text(encoding="utf-8")))
    html = merge.render(
        (workshop / "SATC Engagement Letter - Tax Preparation.html").read_text(encoding="utf-8"),
        record).html
    assert "We email once when it is ready." in html
    assert "&lt;&lt;" not in html and "[CONFIRM:" not in html
