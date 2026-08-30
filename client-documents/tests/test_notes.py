"""The advisory half of the tenet linter, proved the only way a check can be.

A GATE NOBODY HAS WATCHED FAIL IS NOT KNOWN TO WORK (SOFTWARE-TENETS S15).
Every advisory below is fired on purpose, against a document built to trip it,
and then the same check is run over the real corpus to confirm it stays quiet
there. Both halves matter: the first proves the check is not blind, the second
proves it is not noise. An advisory that fires on the firm's own approved copy
is worse than no advisory, because it takes the eight exact gates down with it
when somebody stops reading the report.

The measured baselines these tests pin come from `docs/tenet-mechanization.md`,
which counted every candidate by hand across the twelve templates and the
rendered packs before any of this was written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import notes
import presend

HERE = Path(__file__).resolve().parent
PACKS = HERE.parent / "out" / "exercise"


# ── a pack made to order ──────────────────────────────────────────────────

DOC = """<!doctype html><html><head><title>t</title>
<link rel="stylesheet" href="satc-doc.css"></head><body>
<doc-page><div class="sec">
<h2><span class="n">01</span>{heading}</h2>
{body}
</div></doc-page></body></html>"""


def write_pack(tmp_path: Path, body: str, heading: str = "What to send us",
               name: str = "letter.html") -> Path:
    pack = tmp_path / "pack"
    pack.mkdir(exist_ok=True)
    (pack / name).write_text(DOC.format(heading=heading, body=body),
                             encoding="utf-8")
    (pack / "MANIFEST.json").write_text(json.dumps(
        {"Documents": [{"key": "onboarding-letter", "files": [name]}],
         "Attachments": []}), encoding="utf-8")
    return pack


@pytest.fixture(scope="module")
def real_packs() -> list[Path]:
    """The rendered packs the harness produces, if they are on disk.

    Skipped rather than faked when they are not: the whole value of the
    quiet-on-the-corpus half is that the corpus is real.
    """
    found = sorted(p.parent for p in PACKS.glob("*/MANIFEST.json"))
    if not found:
        pytest.skip("no rendered packs in out/exercise; run `exercise.py` first")
    return found


# ── the property that makes this module safe to run ───────────────────────

def test_nothing_in_this_module_can_block(tmp_path):
    """Every finding notes.py produces is advisory. Not by convention -- by
    construction: `note()` is the only constructor, and it hard-codes it."""
    pack = write_pack(tmp_path, "<p>We typically file by the deadline. "
                                "We are unable to say more. You should not "
                                "wait.</p>")
    got = notes.findings(notes.review(pack))
    assert got, "the trip-wire document fired nothing, so this proves nothing"
    assert all(not f.blocking for f in got)


def test_every_advisory_declares_when_it_may_be_promoted():
    """A promotion condition that lives nowhere is a promotion that happens by
    accident. Every entry carries one, and every check maps to an entry."""
    assert len(notes.ADVISORIES) == 10
    for adv in notes.ADVISORIES:
        assert adv.promote_when.strip()
        assert adv.tenet.startswith("T")
    keys = {c.key for c in notes.review(Path("."))}
    assert keys == set(notes.BY_KEY)


# ── the sentence splitter, which every length check rests on ──────────────

@pytest.mark.parametrize("text,want", [
    ("One thing. Two things.", 2),
    ("Send it to SAT-C LLP. We will confirm.", 2),
    ("File the U.S. return. Then wait.", 2),
    ("Mr. Ellwood signed it.", 1),
    ("No full stop at all", 1),
    ("", 0),
])
def test_the_splitter_does_not_invent_boundaries(text, want):
    assert len(notes.sentences(text)) == want


def test_an_abbreviation_does_not_become_a_sentence():
    """The failure this guard exists for: "U.S." split in two turns a 30-word
    sentence into a 4-word fragment and a 26-word one, and the length check
    silently stops firing."""
    got = notes.sentences("We file the U.S. return and the state return.")
    assert got == ["We file the U.S. return and the state return."]


def test_a_document_is_read_block_by_block(tmp_path):
    """NOT one flattened string. Read flat, the masthead and the first heading
    run together into one 74-word "sentence" with no full stop in it, and the
    28-word check fired 162 times on a corpus where 21 was the right answer."""
    pack = write_pack(tmp_path, "<p>First one.</p><p>Second one.</p>"
                                "<ul><li>A bullet</li></ul>")
    doc = pack / "letter.html"
    blocks = notes.prose_blocks(doc.read_text(encoding="utf-8"))
    assert blocks == ["First one.", "Second one.", "A bullet"]
    # The heading is not in there, and that is the point.
    assert not any("What to send us" in b for b in blocks)


# ── A1 · certainty (T11) ──────────────────────────────────────────────────

def test_a1_fires_on_a_hedge_read_as_certainty(tmp_path):
    pack = write_pack(tmp_path, "<p>Your refund will likely arrive in "
                                "three weeks.</p>")
    got = notes.a1_certainty(pack)
    assert len(got.findings) == 1
    assert "will likely" in got.findings[0].detail
    assert got.examined == 1


def test_a1_is_quiet_on_the_real_corpus(real_packs):
    """Measured at 0 of 12 templates when the check was specified. It is the
    best promotion candidate in the set precisely because of this."""
    fired = sum(len(notes.a1_certainty(p).findings) for p in real_packs)
    assert fired == 0, "A1 is no longer at zero; re-read before promoting it"


# ── A2 · assurance vocabulary (T23b) ──────────────────────────────────────

def test_a2_fires_on_an_assurance_word_with_no_negation(tmp_path):
    pack = write_pack(tmp_path, "<p>Our audit of the accounts is enclosed.</p>")
    got = notes.a2_assurance(pack)
    assert len(got.findings) == 1
    assert "audit" in got.findings[0].detail


def test_a2_leaves_the_compliance_negation_alone(tmp_path):
    """The floor sentence itself. If this fired, the check would be telling
    the firm to delete the one paragraph T23 says may never be cut."""
    pack = write_pack(tmp_path, "<p>We do not perform audits, reviews, or any "
                                "assurance engagement.</p>")
    assert notes.a2_assurance(pack).findings == []


def test_a2_is_quiet_on_the_real_corpus(real_packs):
    fired = sum(len(notes.a2_assurance(p).findings) for p in real_packs)
    assert fired == 0


# ── A3 · long sentences (T20c) ────────────────────────────────────────────

def test_a3_fires_past_the_cap_and_not_before(tmp_path):
    short = "word " * 28
    long = "word " * 29
    pack = write_pack(tmp_path, f"<p>{short.strip()}.</p>")
    assert notes.a3_long_sentences(pack).findings == []
    pack = write_pack(tmp_path, f"<p>{long.strip()}.</p>")
    assert len(notes.a3_long_sentences(pack).findings) == 1


def test_a3_prints_the_worst_five_and_says_what_it_held_back(tmp_path):
    """Its job is to put the longest sentence in front of a human, not to
    print twenty-one lines nobody finishes. Holding some back SILENTLY would
    be the same lie in the other direction, so it says how many."""
    body = "".join(f"<p>{'word ' * (30 + i)}.</p>" for i in range(8))
    got = notes.a3_long_sentences(write_pack(tmp_path, body))
    shown = [f for f in got.findings if "words:" in f.detail]
    assert len(shown) == notes.LONG_SHOWN == 5
    held = [f for f in got.findings if "not listed" in f.detail]
    assert len(held) == 1 and "3 more" in held[0].detail
    # longest first
    lengths = [int(f.detail.split()[0]) for f in shown]
    assert lengths == sorted(lengths, reverse=True)


def test_a3_finds_the_officer_compensation_sentence(real_packs):
    """The one real hit the specification found by hand: a 50-word sentence
    written into the business and C-corporation letters on 26 August, after
    T20 was recorded. If this stops finding it, A3 has stopped working."""
    worst = 0
    for pack in real_packs:
        for f in notes.a3_long_sentences(pack).findings:
            if "words:" in f.detail:
                worst = max(worst, int(f.detail.split()[0]))
    assert worst >= 45, f"longest sentence found was {worst} words"


# ── A4 · long paragraphs (T19) ────────────────────────────────────────────

def test_a4_fires_on_four_sentences(tmp_path):
    pack = write_pack(tmp_path, "<p>One. Two. Three. Four.</p>")
    assert len(notes.a4_long_paragraphs(pack).findings) == 1


def test_a4_leaves_a_compliance_paragraph_alone(tmp_path):
    """The billing-and-suspension paragraph is four sentences in all four
    engagement letters, and every one of them is protected. Before the
    exclusion this check fired 27 times over 27 packs and the only fix it
    offered was to delete protected text."""
    pack = write_pack(tmp_path,
                      "<p>Invoices are due on presentation. Balances unpaid "
                      "after thirty days carry interest. We may suspend or "
                      "withdraw from the engagement if an invoice goes "
                      "unpaid. We are not responsible for a late filing that "
                      "results.</p>")
    got = notes.a4_long_paragraphs(pack)
    assert got.findings == []
    assert "1 compliance paragraph(s) left alone" in got.scope


def test_a4_is_quiet_on_the_real_corpus(real_packs):
    fired = sum(len(notes.a4_long_paragraphs(p).findings) for p in real_packs)
    assert fired == 0


# ── A5 · self-narration (T8) ──────────────────────────────────────────────

def test_a5_fires_on_narrating_our_own_inability(tmp_path):
    pack = write_pack(tmp_path, "<p>We cannot tell a missing document from "
                                "one that does not exist.</p>")
    assert len(notes.a5_self_narration(pack).findings) == 1


def test_a5_leaves_a_fact_about_the_law_alone(tmp_path):
    """A looser pattern -- bare "we cannot" -- catches this sentence and is
    wrong. That the pattern is tuned to miss it is exactly why A5 advises
    rather than blocks."""
    pack = write_pack(tmp_path, "<p>We cannot transmit anything until the "
                                "signed authorization is back with us.</p>")
    assert notes.a5_self_narration(pack).findings == []


def test_a5_is_quiet_on_the_real_corpus(real_packs):
    fired = sum(len(notes.a5_self_narration(p).findings) for p in real_packs)
    assert fired == 0


# ── A6 · disapproval (T15) ────────────────────────────────────────────────

def test_a6_fires_on_disapproving_of_a_choice(tmp_path):
    pack = write_pack(tmp_path, "<p>You should not email us your documents.</p>")
    assert len(notes.a6_disapproval(pack).findings) == 1


def test_a6_leaves_the_firms_own_replacement_alone(tmp_path):
    """"at your own risk" is the form the firm settled on for exactly this,
    and it is live in four templates."""
    pack = write_pack(tmp_path, "<p>Emailing or otherwise transmitting "
                                "unprotected documents is done at your own "
                                "risk.</p>")
    assert notes.a6_disapproval(pack).findings == []


def test_a6_is_quiet_on_the_real_corpus(real_packs):
    fired = sum(len(notes.a6_disapproval(p).findings) for p in real_packs)
    assert fired == 0


# ── A7 · virtue (T16) ─────────────────────────────────────────────────────

def test_a7_fires_on_a_published_kindness(tmp_path):
    page = tmp_path / "prices.html"
    page.write_text("<p>Reviewing a notice is free of charge.</p>",
                    encoding="utf-8")
    got = notes.a7_virtue(page)
    assert any("free of charge" in f.detail for f in got.findings)
    assert page.name in got.scope


def test_a7_never_reads_a_client_letter(tmp_path):
    """T16 killed a "$0 amendment" line because it was a marketing claim on a
    PUBLIC page. The same words in one client's own letter, about one specific
    favour, are the firm's own approved copy -- "Reading one and telling you
    what it actually says costs nothing." A7 does not take a pack at all."""
    import inspect
    params = inspect.signature(notes.a7_virtue).parameters
    assert list(params) == ["extra"]


def test_a7_examines_the_fee_schedule_and_is_quiet():
    got = notes.a7_virtue()
    assert got.examined > 0, "A7 read no published phrase at all"
    assert got.findings == []


# ── A8 · two-clause labels (T18) ──────────────────────────────────────────

def test_a8_reads_every_label_in_the_registry():
    got = notes.a8_two_clause_labels()
    assert got.examined >= 17, f"only {got.examined} labels found"
    assert got.findings == []


def test_a8_walks_the_registry_rather_than_indexing_into_one_shape():
    """The registry has been reshaped twice. A check that reaches for a known
    path reports "0 labels examined" the day it changes, and zero reads as
    clean."""
    shaped = {"a": {"b": [{"document": "One thing"},
                          {"nested": {"document": "Another. And more."}}]}}
    found = notes._walk_requests(shaped)
    assert len(found) == 2


def test_a8_fires_on_two_clauses_in_one_label(tmp_path, monkeypatch):
    reg = tmp_path / "document-requests.yaml"
    reg.write_text("items:\n  - document: 'The ID only if new. We need the "
                   "numbers, not the cards'\n", encoding="utf-8")
    monkeypatch.setattr(notes, "REGISTRY", tmp_path)
    got = notes.a8_two_clause_labels()
    assert len(got.findings) == 1 and got.examined == 1


# ── A9 · heading echo (T2) ────────────────────────────────────────────────

def test_a9_fires_when_a_bullet_says_its_whole_heading_back(tmp_path):
    """The failure that actually happened: five estimate bullets each opening
    "this estimate assumes", under a heading reading "What this estimate
    assumes"."""
    pack = write_pack(
        tmp_path,
        "<ul><li>This estimate assumes your records arrive complete</li></ul>",
        heading="What this estimate assumes")
    got = notes.a9_heading_echo(pack)
    assert len(got.findings) == 1
    assert got.examined == 1


def test_a9_leaves_a_bullet_that_adds_a_fact_alone(tmp_path):
    pack = write_pack(
        tmp_path, "<ul><li>Every W-2 for the year</li></ul>",
        heading="What this estimate assumes")
    assert notes.a9_heading_echo(pack).findings == []


def test_a9_counts_the_items_it_could_not_judge(tmp_path):
    """A heading of one content word cannot be echoed in any useful sense.
    Dropping those items SILENTLY is how a check reports clean having looked
    at nothing."""
    pack = write_pack(tmp_path, "<ul><li>Anything at all</li></ul>",
                      heading="Questions")
    got = notes.a9_heading_echo(pack)
    assert got.examined == 0
    assert "too short to echo" in got.scope


def test_a9_is_quiet_on_the_real_corpus(real_packs):
    fired = sum(len(notes.a9_heading_echo(p).findings) for p in real_packs)
    assert fired == 0


# ── A10 · strict citations (T21) ──────────────────────────────────────────

def test_a10_fires_when_the_cited_letter_is_not_in_this_pack(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "delivery.html").write_text(DOC.format(
        heading="Your copies",
        body="<p>See the <b>Ending this engagement</b> section of your "
             "engagement letter.</p>"), encoding="utf-8")
    (pack / "SATC Engagement Letter.html").write_text(DOC.format(
        heading="Fees and billing", body="<p>Nothing.</p>"), encoding="utf-8")
    got = notes.a10_strict_citations(pack)
    assert len(got.findings) == 1
    assert "Ending this engagement" in got.findings[0].detail
    assert got.examined == 1


def test_a10_is_satisfied_when_the_section_is_there(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "delivery.html").write_text(DOC.format(
        heading="Your copies",
        body="<p>See the <b>Fees and billing</b> section of your engagement "
             "letter.</p>"), encoding="utf-8")
    (pack / "SATC Engagement Letter.html").write_text(DOC.format(
        heading="Fees and billing", body="<p>Nothing.</p>"), encoding="utf-8")
    assert notes.a10_strict_citations(pack).findings == []


def test_a10_examines_nothing_on_an_opening_pack(real_packs):
    """All seven live citations are in the delivery letter, the disengagement
    letter, the extension notice and the invoice. None of those is in an
    opening pack, so this correctly examines zero -- and must SAY zero."""
    for pack in real_packs:
        assert notes.a10_strict_citations(pack).examined == 0


# ── the report ────────────────────────────────────────────────────────────

def test_a_check_that_examined_nothing_prints_skip_not_ok(tmp_path):
    """The sentence this whole design exists to stop producing is "0 of 0,
    clean"."""
    pack = write_pack(tmp_path, "<p>Short.</p>")
    line = [c for c in notes.review(pack) if c.key == "A10"][0].line()
    assert line.strip().startswith("SKIP")
    assert "nothing is known" in line


def test_the_report_names_every_advisory_whether_or_not_it_fired(tmp_path):
    pack = write_pack(tmp_path, "<p>Short.</p>")
    text = notes.format_notes(notes.review(pack))
    for adv in notes.ADVISORIES:
        assert adv.key in text, f"{adv.key} is missing from the report"


def test_the_report_says_out_loud_that_none_of_it_blocks(tmp_path):
    pack = write_pack(tmp_path, "<p>Your refund will likely arrive soon.</p>")
    text = notes.format_notes(notes.review(pack))
    assert "readings, not rulings" in text
    assert "exit code" in text


def test_an_empty_pack_examines_nothing_everywhere(tmp_path):
    """S2, in its purest form. Every per-pack check on a pack with no
    documents must report zero, and none of them may say ok."""
    pack = tmp_path / "empty"
    pack.mkdir()
    for check in notes.review(pack):
        if check.key in ("A7", "A8"):
            continue          # neither reads the pack; both read the registry
        assert check.examined == 0, f"{check.key} examined {check.examined}"
        assert check.line().strip().startswith("SKIP")
