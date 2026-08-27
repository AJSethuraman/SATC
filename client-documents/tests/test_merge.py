"""The merge engine, tested against the real templates.

The claim under test is the one the templates make about themselves: a document
either comes out complete, or it does not come out at all.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import merge  # noqa: E402
from merge import MergeError, render, render_file  # noqa: E402

TEMPLATE_DIR = ROOT.parent / "satc-handoff" / "04-TEMPLATES"
OPENING_PACKAGE = {
    "tax letter": "SATC Engagement Letter - Tax Preparation.html",
    "fee estimate": "SATC Fee Estimate.html",
    "onboarding letter": "SATC Onboarding Letter.html",
}


@pytest.fixture(scope="module")
def record():
    data = json.loads((ROOT / "samples" / "tax-opening-package.json").read_text(encoding="utf-8"))
    data.pop("_comment", None)
    return data


# ── the whole point ───────────────────────────────────────────────────────

@pytest.mark.parametrize("label,filename", OPENING_PACKAGE.items())
def test_opening_package_renders_complete(record, label, filename):
    """One record fills all three documents with nothing left unresolved."""
    result = render_file(TEMPLATE_DIR / filename, record)
    assert "&lt;&lt;" not in result.html, f"{label}: an unfilled field survived"
    assert "[[" not in result.html, f"{label}: an unresolved block survived"
    assert "[CONFIRM:" not in result.html, f"{label}: an undecided placeholder survived"


def test_shared_values_are_identical_across_the_package(record):
    """The reason to generate the three together is that they cannot disagree."""
    rendered = {k: render_file(TEMPLATE_DIR / v, record).html for k, v in OPENING_PACKAGE.items()}
    for shared in ("2027-0114", "February 3, 2027", "418 Rockwell Street"):
        present = [k for k, h in rendered.items() if shared in h]
        assert len(present) >= 2, f"{shared!r} should appear in the package, found in {present}"


def test_materials_deadline_matches_across_documents(record):
    """The organizer's field doc calls a mismatch here its most likely bug."""
    deadline = record["MaterialsDeadline"]
    for label, filename in OPENING_PACKAGE.items():
        html = render_file(TEMPLATE_DIR / filename, record).html
        if "deadline" in html.lower() or label != "fee estimate":
            pass  # only the letter and onboarding print it
    tax = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], record).html
    onb = render_file(TEMPLATE_DIR / OPENING_PACKAGE["onboarding letter"], record).html
    assert deadline in tax and deadline in onb


# ── failure is loud ───────────────────────────────────────────────────────

def test_missing_field_raises_rather_than_shipping(record):
    holed = dict(record)
    del holed["ClientFullName"]
    with pytest.raises(MergeError) as e:
        render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], holed)
    assert "ClientFullName" in str(e.value)


def test_confirm_placeholder_cannot_reach_a_client(record):
    """An undecided firm setting stops the render rather than printing.

    HOLED IN A FIELD THE TEMPLATE ACTUALLY MERGES, and the assertion below
    checks that. Until 26 August 2026 this test poked `ReturnInstruction`;
    when that field was retired the template stopped merging it, the
    placeholder never reached the output, and the test went on passing while
    checking nothing. The guard reads the RENDERED TEXT, not the record, so a
    value nothing prints can never fail it.

    Naming the field in an assertion is what makes the next retirement break
    this test loudly instead of quietly hollowing it out.
    """
    field = "PreparerName"
    template = (TEMPLATE_DIR / OPENING_PACKAGE["tax letter"]).read_text(encoding="utf-8")
    assert f"&lt;&lt;{field}&gt;&gt;" in template, (
        f"this test holes {field}, which the tax letter no longer merges — "
        f"point it at a field the template does merge, or it proves nothing"
    )
    undecided = dict(record)
    undecided[field] = "[CONFIRM: who is signing this one?]"
    with pytest.raises(MergeError) as e:
        render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], undecided)
    assert "CONFIRM" in str(e.value)


def test_a_list_must_be_a_list(record):
    broken = dict(record)
    broken["LineItems"] = "Federal Form 1040 — $450"
    with pytest.raises(MergeError):
        render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], broken)


# ── behaviour of the markers ──────────────────────────────────────────────

def test_conditional_block_is_dropped_when_false(record):
    joint = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], record).html
    assert "Maria Reyes" in joint

    single = dict(record, JointReturn=False)
    single.pop("SpouseName")
    out = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], single)
    assert "Maria Reyes" not in out.html
    assert "JointReturn" in out.blocks_dropped
    assert "both spouses" not in out.html.lower(), "the joint-representation note should go too"


def test_each_repeats_once_per_item(record):
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], record).html
    for item in record["LineItems"]:
        assert item["Service"] in html
        assert item["Amount"] in html
    assert len(record["LineItems"]) >= 1


def test_empty_detail_renders_empty_not_none(record):
    """The field docs are explicit: an empty Item.Detail is '', never 'None'.

    Built here rather than leaned on the sample: the sample's estimate is
    generated from the engine now, and every line the engine writes happens to
    carry a detail. A test that depends on that would pass for the wrong
    reason the day a detail is added.
    """
    holed = dict(record)
    holed["LineItems"] = list(record["LineItems"]) + [
        {"Service": "Solon municipal return", "Detail": "",
         "Includes": "", "Amount": "$35.00"}]
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], holed).html
    assert "Solon municipal return" in html
    assert ">None<" not in html


def test_a_line_item_missing_a_sub_field_refuses(record):
    """Empty is a value; absent is a hole, and the two must not look alike.

    `Includes` was added to the estimate's rows on 26 August 2026 and every
    row carries it, empty where a line has nothing to list. A row assembled
    without the key at all is a caller that has not been updated, and it has
    to fail here rather than print `<<Item.Includes>>` on a fee estimate.
    """
    holed = dict(record)
    holed["LineItems"] = [{"Service": "A return", "Detail": "", "Amount": "$35.00"}]
    with pytest.raises(MergeError, match="Item.Includes"):
        render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], holed)


def test_the_estimate_and_the_letter_state_the_same_scope(record):
    """The firm, 26 August 2026, holding both sheets: "either it needs to list
    what we are doing in one place, or needs to be comparable in both."

    They were not comparable. The letter named schedules -- "Form 1040 with
    Schedules A, C, E, and SE" -- and the estimate named a package and a
    price, "Self-Employed $500", with the rest of it buried in a semicolon
    run-on inside a table cell. Everything was covered; nothing lined up.

    The estimate now repeats the letter's four scope lines from the same four
    fields. This asserts they are the same four VALUES on one record, which is
    what makes the two sheets comparable rather than merely consistent.
    """
    letter = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], record).html
    estimate = render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], record).html

    for field in ("FederalReturns", "StateReturns", "LocalReturns", "AdditionalForms"):
        value = record[field]
        assert value in letter, f"{field} is not on the engagement letter"
        assert value in estimate, f"{field} is not on the fee estimate"


def test_the_estimate_prices_every_schedule_its_scope_names(record):
    """The failure this pair is guarding against, stated directly.

    The bug that started it: the letter's scope said "Schedules A, C, and SE"
    while the estimate billed a $145 Rental schedule. Schedule E was on the
    bill and outside the scope the client had signed. Both documents render
    from one record now, so the two halves of that contradiction are here
    together and can be compared.
    """
    scope = record["FederalReturns"]
    if "E" in scope.replace("Schedules", ""):
        priced = " ".join(i["Service"] + " " + i["Includes"] for i in record["LineItems"])
        assert "Schedule E" in priced or "Rental" in priced, (
            "the letter's scope names Schedule E and nothing on the estimate "
            "prices it"
        )


# ── escaping ──────────────────────────────────────────────────────────────

def test_values_are_escaped(record):
    ampersand = dict(record, ClientFullName="Ross & Sons")
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["fee estimate"], ampersand).html
    assert "Ross &amp; Sons" in html
    assert "Ross & Sons" not in html


def test_a_value_cannot_inject_markup(record):
    hostile = dict(record, ClientFullName='<script>alert(1)</script>')
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], hostile).html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


# ── the proof chrome never ships ──────────────────────────────────────────

def test_field_chrome_is_stripped(record):
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], record).html
    assert 'class="f"' not in html, "merge-field styling should not reach a client"
    assert 'class="cond"' not in html, "conditional markers should not reach a client"


def test_screen_only_reference_block_is_removed(record):
    html = render_file(TEMPLATE_DIR / OPENING_PACKAGE["tax letter"], record).html
    assert 'class="ref"' not in html
    assert "Merge fields" not in html, "the field documentation must never reach a client"


# ── the four templates added after the opening package ────────────────────

LATER_DOCUMENTS = {
    "delivery letter": ("SATC Tax Return Delivery Letter.html", "delivery-letter.json"),
    "extension notice": ("SATC Extension Notice.html", "extension-notice.json"),
    "disengagement letter": ("SATC Disengagement Letter.html", "disengagement-letter.json"),
}


def _sample(name):
    data = json.loads((ROOT / "samples" / name).read_text(encoding="utf-8"))
    data.pop("_comment", None)
    return data


@pytest.mark.parametrize("label,pair", LATER_DOCUMENTS.items())
def test_later_documents_render_complete(label, pair):
    """Each FIELDS doc's example payload fills its own template.

    §7 of the authoring contract calls the example payload the acceptance test:
    "if it does not render a clean document, the pair is not done". These
    samples are lifted from the FIELDS docs, so the documentation and the test
    cannot drift apart.
    """
    filename, sample = pair
    result = render_file(TEMPLATE_DIR / filename, _sample(sample))
    assert "&lt;&lt;" not in result.html, f"{label}: an unfilled field survived"
    assert "[[" not in result.html, f"{label}: an unresolved block survived"
    assert "[CONFIRM:" not in result.html, f"{label}: an undecided placeholder survived"


def test_business_letter_renders_now_that_the_confirm_is_answered():
    """It used to carry one open [CONFIRM], on officer compensation under an S
    election, and this test asserted the letter could not reach a client while
    it was there. Its own docstring said it would go green the moment a human
    resolved it. The firm did, on 26 August 2026 — "exclude unless specified as
    part of the engagement" — so it is inverted rather than deleted.

    A `[CONFIRM:` coming BACK to this template is now the failure.
    """
    result = render_file(TEMPLATE_DIR / "SATC Engagement Letter - Business Return.html",
                         _sample("business-engagement.json"))
    assert "[CONFIRM:" not in result.html


def test_the_business_letter_still_excludes_officer_compensation_by_default():
    """The half of the ruling that protects the firm.

    "Exclude unless specified" only works if the exclusion is unconditional in
    the text and the inclusion has to be written in. A letter that merely
    offered the service without excluding it would leave a client free to say
    afterwards that they assumed it was covered.
    """
    result = render_file(TEMPLATE_DIR / "SATC Engagement Letter - Business Return.html",
                         _sample("business-engagement.json"), strict=False)
    assert "not within this engagement" in result.html
    assert "in writing before we start" in result.html


def test_business_letter_is_otherwise_complete():
    """Everything except that one marker resolves.

    Without this, the test above would also pass on a letter riddled with
    unfilled fields -- it would just report the first problem it found.
    """
    result = render_file(TEMPLATE_DIR / "SATC Engagement Letter - Business Return.html",
                         _sample("business-engagement.json"), strict=False)
    assert "&lt;&lt;" not in result.html, "an unfilled field survived"
    assert "[[" not in result.html, "an unresolved block survived"
    assert result.html.count("[CONFIRM:") == 0, (
        "the last open decision on this template was answered on 26 Aug 2026; "
        "a [CONFIRM: here again is one somebody re-opened"
    )


INVERSE_PAIRS = [
    ("SATC Tax Return Delivery Letter.html", "delivery-letter.json", "EFiled", "PaperFiled"),
    ("SATC Extension Notice.html", "extension-notice.json", "PaymentEnclosed", "NoPaymentRequired"),
    ("SATC Disengagement Letter.html", "disengagement-letter.json", "ClientInitiated", "FirmInitiated"),
    ("SATC Disengagement Letter.html", "disengagement-letter.json", "BalanceOutstanding", "AccountSettled"),
    ("SATC Engagement Letter - Business Return.html", "business-engagement.json",
     "OwnerReturnsPrepared", "OwnerReturnsElsewhere"),
]


@pytest.mark.parametrize("filename,sample,a,b", INVERSE_PAIRS)
def test_inverse_flags_render_exactly_one_branch(filename, sample, a, b):
    """Both states, and only ever one of them.

    Every one of these pairs exists because the alternative -- a section that
    can be silent -- is the failure mode. A delivery letter that says nothing
    about how a return gets filed, or a disengagement letter that says nothing
    about money, is worse than no letter. Two independent booleans can both be
    false; this test is what says they must not.
    """
    for on, off in ((a, b), (b, a)):
        record = dict(_sample(sample))
        record[on], record[off] = True, False
        result = render_file(TEMPLATE_DIR / filename, record, strict=False)
        assert on in result.blocks_kept, f"{on} true but its block was dropped"
        assert off in result.blocks_dropped, f"{off} false but its block was kept"


# ── a money document with no money in it ──────────────────────────────────
#
# `[[EACH LineItems]]` over a missing or empty list renders to nothing, and
# nothing is indistinguishable from a list that was never there. A fee
# estimate came out of this with a blank services table and "Total estimate
# $785" underneath it, and merge did not complain. `pricing.price()`'s own
# docstring records the same failure happening to the assumptions block once
# before -- "collapsed to nothing without the render so much as warning about
# it" -- so this is the second time, not the first.
#
# Which lists may be empty is a judgement, so it lives in the registry rather
# than here: `lists:` entries carry `required: true` where empty is broken by
# definition. An extension notice with no outstanding items is fine. A bill
# with no lines is not.

# Fields are HTML-escaped in the real templates -- `&lt;&lt;Field&gt;&gt;` --
# because they are authored as visible text in a browser. merge matches that
# form, so a test template written with raw angle brackets silently resolves
# nothing.
REQUIRED_LIST_TPL = (
    "<table>[[EACH LineItems]]<tr><td>&lt;&lt;Item.Service&gt;&gt;</td>"
    "<td>&lt;&lt;Item.Amount&gt;&gt;</td></tr>[[END EACH]]</table>"
    "<p>Total &lt;&lt;EstimateTotal&gt;&gt;</p>"
)


def test_a_required_list_that_is_empty_is_refused():
    with pytest.raises(MergeError, match="LineItems"):
        render(REQUIRED_LIST_TPL,
                     {"LineItems": [], "EstimateTotal": "$785"},
                     required_lists=("LineItems",))


def test_a_required_list_that_is_missing_is_refused():
    with pytest.raises(MergeError, match="LineItems"):
        render(REQUIRED_LIST_TPL, {"EstimateTotal": "$785"},
                     required_lists=("LineItems",))


def test_a_required_list_with_items_renders():
    out = render(REQUIRED_LIST_TPL,
                       {"LineItems": [{"Service": "Essentials", "Amount": "$200"}],
                        "EstimateTotal": "$200"},
                       required_lists=("LineItems",))
    assert "Essentials" in out.html and "$200" in out.html


def test_an_unrequired_empty_list_still_renders():
    """An extension notice with nothing outstanding is a real document."""
    out = render(REQUIRED_LIST_TPL,
                       {"LineItems": [], "EstimateTotal": "$0.00"})
    assert "$0.00" in out.html


def test_a_required_list_is_not_enforced_in_draft():
    """Draft mode exists to exercise the pipeline before the answers exist.
    It already tolerates unresolved fields; an empty list is the same kind of
    incompleteness and must not become the one thing that stops a draft."""
    out = render(REQUIRED_LIST_TPL, {"LineItems": []},
                       strict=False, required_lists=("LineItems",))
    assert out.html is not None


# ── section numbering, after the conditionals resolve ─────────────────────

def test_a_dropped_section_renumbers_the_ones_below_it():
    """THE LIVE DEFECT. `[[IF PriorFirm]]` drops section 03 of the onboarding
    letter and nothing renumbered, so 26 of 27 packs went out reading
    01, 02, 04, 05. The template's own FIELDS spec asked for this in writing
    -- "Renumber the remaining sections in code" -- and it was never built."""
    out, moved = merge._renumber_sections(
        '<h2><span class="n">01</span>A</h2>'
        '<h2><span class="n">02</span>B</h2>'
        '<h2><span class="n">04</span>C</h2>'
        '<h2><span class="n">05</span>D</h2>')
    assert re.findall(r'class="n">(\d+)<', out) == ["01", "02", "03", "04"]
    assert moved == {"01": "01", "02": "02", "04": "03", "05": "04"}


def test_prose_that_cites_a_section_moves_with_it():
    """Renumbering the headings alone would leave "section 04 tells you what
    to do" pointing at whatever now occupies 04 — worse than the gap."""
    out, _ = merge._renumber_sections(
        '<h2><span class="n">01</span>A</h2><p>Section 04 explains it.</p>'
        '<h2><span class="n">02</span>B</h2>'
        '<h2><span class="n">04</span>C</h2>')
    assert "Section 03 explains it." in out


def test_a_document_that_already_numbers_correctly_is_untouched():
    src = ('<h2><span class="n">01</span>A</h2>'
           '<h2><span class="n">02</span>B</h2><p>see section 02</p>')
    out, moved = merge._renumber_sections(src)
    assert out == src and moved == {}


def test_a_reference_to_a_section_that_is_not_there_is_refused():
    """A client reading "section 09 explains what to do" and finding no
    section 09 is the same failure as an unresolved token: the document says
    something that is not true of itself."""
    with pytest.raises(merge.MergeError) as exc:
        merge.render('<h2><span class="n">01</span>A</h2>'
                     '<p>Section 09 explains it.</p>', {})
    assert "section(s) 09" in str(exc.value)


def test_the_result_says_whether_anything_moved():
    """A silent renumber and no renumber look identical from outside, and one
    of them means a condition dropped a section."""
    quiet = merge.render('<h2><span class="n">01</span>A</h2>', {})
    assert quiet.renumbered == {}
    moved = merge.render('<h2><span class="n">01</span>A</h2>'
                         '<h2><span class="n">03</span>B</h2>', {})
    assert moved.renumbered == {"01": "01", "03": "02"}


# ── a sentence can only be given a phrase ─────────────────────────────────

def test_a_list_handed_to_a_sentence_is_refused():
    """A disengagement letter went out reading: "It covers [{'Item': '2026
    federal and Ohio returns', 'Status': 'Complete'}]". `str(value)` will
    render a Python repr straight into a client's letter and nothing
    downstream can tell that apart from a phrase somebody meant to write."""
    with pytest.raises(MergeError) as exc:
        render('<p>It covers &lt;&lt;Work&gt;&gt;.</p>',
               {"Work": [{"Item": "2026 returns", "Status": "Complete"}]})
    assert "Work is a list" in str(exc.value)
    assert "Python" in str(exc.value)


def test_a_dict_handed_to_a_sentence_is_refused():
    with pytest.raises(MergeError):
        render('<p>&lt;&lt;Where&gt;&gt;</p>', {"Where": {"city": "Dublin"}})


@pytest.mark.parametrize("value", ["a phrase", 42, 3.5, True, None])
def test_every_ordinary_value_still_renders(value):
    """The gate must not become a reason to fear the record."""
    render('<p>&lt;&lt;A&gt;&gt;</p>', {"A": value})


def test_a_row_that_is_not_a_set_of_fields_is_refused():
    """`[[EACH]]` has refused a non-list since it was written; this is the
    same gate one level down. A list of strings cannot fill a table whose
    columns have names — it used to raise AttributeError from inside the
    engine, which tells a preparer nothing."""
    with pytest.raises(MergeError) as exc:
        render('[[EACH Rows]]<td>&lt;&lt;Item.A&gt;&gt;</td>[[END EACH]]',
               {"Rows": ["just a string"]})
    assert "row 1 of Rows" in str(exc.value)


# ── two faces of one decision ─────────────────────────────────────────────

EXT = ('<p>Your payment deadline does not move, and section 02 tells you what '
       'to do about that.</p>'
       '<h2><span class="n">02</span>Money</h2>'
       '[[IF PaymentEnclosed]]<p>Pay $450 by 15 April.</p>[[END IF]]'
       '[[IF NoPaymentRequired]]<p>There is nothing to pay.</p>[[END IF]]')
PAIR = (("PaymentEnclosed", "NoPaymentRequired"),)


def test_neither_half_of_an_inverse_pair_is_refused():
    """THE WORST POSSIBLE VERSION OF THIS LETTER, in the template's own words.
    Two independent booleans can both be false, and when they were, the
    extension notice printed a warning that the payment deadline has not
    moved, an intro saying section 02 tells you what to do about it, and then
    nothing at all in section 02."""
    with pytest.raises(MergeError) as exc:
        render(EXT, {}, inverse_flags=PAIR)
    assert "neither is set" in str(exc.value)
    assert "come out empty" in str(exc.value)


def test_both_halves_of_an_inverse_pair_is_refused():
    with pytest.raises(MergeError) as exc:
        render(EXT, {"PaymentEnclosed": True, "NoPaymentRequired": True},
               inverse_flags=PAIR)
    assert "both are set" in str(exc.value)


def test_exactly_one_renders():
    out = render(EXT, {"PaymentEnclosed": True, "NoPaymentRequired": False},
                 inverse_flags=PAIR)
    assert "Pay $450" in out.html
    assert "nothing to pay" not in out.html


def test_a_pair_this_document_does_not_use_is_not_its_problem():
    """The delivery letter's EFiled/PaperFiled pair has nothing to do with an
    engagement letter, and requiring it there would block every send."""
    render("<p>Nothing conditional here.</p>", {}, inverse_flags=PAIR)
