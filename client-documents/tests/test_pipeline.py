"""End to end: a record goes in, documents come out — or nothing does.

The suites either side of this one test parts. `test_merge` proves the engine
fills a template; `test_registry` proves the templates, the registry and the
interview agree. Neither proves you can *run* anything, which is what this file
is for: the CLI, the firm-settings mapping, and the two modes.

The claim under test is the one that keeps a half-finished letter off a client's
desk: **real mode writes nothing at all when a document would be holed, and a
draft is impossible to mistake for the real thing.**
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import merge  # noqa: E402
import settings as firm  # noqa: E402

SAMPLES = ROOT / "samples"


def _load(name):
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


# ── the firm-settings mapping ─────────────────────────────────────────────

@pytest.mark.parametrize("return_type", sorted(firm.RETURN_TYPES))
def test_every_return_type_resolves_a_deadline(return_type):
    """A regression: `partnership_1065:"[CONFIRM…` was missing the space.

    YAML read the key as `partnership_1065:"[CONFIRM`, so the 1065 deadline
    silently did not exist and a partnership letter would have looked up a key
    that was not there. One character, invisible to every other test, caught the
    first time anything actually ran.
    """
    fields = firm.firm_fields("2026", return_type)
    assert fields["MaterialsDeadline"], f"no deadline for {return_type}"


FIRM_BLOCK = ("FirmName", "FirmLegalName", "FirmAddress1", "FirmCity",
              "FirmState", "FirmZip", "FirmWebsite", "FirmJurisdiction")


def test_the_firm_block_reaches_every_document_from_settings_alone():
    """Change the firm's address in one file and all ten documents follow.

    Until 26 August 2026 the masthead, the footer and the sign-off were typed
    into each template, byte-identical across eleven files. The firm asked for
    exactly this: "things like the email and phone number are generated from a
    template - this could change in the future, we could hire, etc. software
    needs to be made to be robust and scalable." So the test moves the firm
    rather than checking a spelling.
    """
    from tests.test_registry import TEMPLATES

    moved = firm.load()
    moved["firm"] = dict(moved["firm"],
                         name="SATC Group LLP",
                         address1="1 Public Square",
                         city="Cleveland", zip="44113",
                         website="satcgroup.example")
    record = firm.firm_fields("2026", settings=moved)

    for name, filename in TEMPLATES.items():
        template = (cli.TEMPLATE_DIR / filename).read_text(encoding="utf-8")
        html = merge.render(template, record, strict=False).html
        assert "SATC Group LLP" in html, f"{name}: the firm name did not follow"
        assert "1 Public Square" in html, f"{name}: the address did not follow"
        assert "6544 Copley" not in html, f"{name}: the old address is still typed in"
        assert "SAT-C LLP" not in html, f"{name}: the old name is still typed in"


def test_no_sample_can_drift_from_the_firm_settings():
    """The samples carry the firm block because `test_merge` renders them raw.

    That is a second copy of an address whose whole point is having one copy,
    so it is pinned rather than trusted.
    """
    for path in SAMPLES.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        settings = firm.firm_fields(record.get("_season", "2026"))
        for field in FIRM_BLOCK:
            if field in record:
                assert record[field] == settings[field], (
                    f"{path.name}: {field} has drifted from firm-settings.yaml"
                )


def test_no_sample_states_a_firm_value_the_firm_does_not_set():
    """Three samples said `arjun@satcllp.com` while settings said
    `arjun_sethuraman@satcllp.com`. The drift test only covered the Firm block
    when it was written, so the preparer's own address went unchecked -- on
    the three documents that print it as the way to reach us.
    """
    settings = firm.firm_fields("2026")
    for path in SAMPLES.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        for field in ("PreparerName", "PreparerTitle", "PreparerEmail",
                      "BillingContactName", "BillingContactEmail",
                      "PaymentInstruction"):
            if field in record:
                assert record[field] == settings[field], (
                    f"{path.name}: {field} has drifted from firm-settings.yaml"
                )


def test_no_sample_states_a_deadline_the_firm_does_not_set():
    """A sample carrying its own date is a second copy of the deadline rule.

    Both opening samples had one, and both were wrong: the rule is three weeks
    before the filing deadline, and they said March 15 and February 15 against
    the firm's March 25 and February 22. A per-engagement override IS
    legitimate -- `build_record` lets the record win on purpose -- which is
    exactly why a sample must not quietly demonstrate one.

    Skipped where a sample has no `_return_type`: the extension notice's
    deadline is the extended one, which is not on this table at all.
    """
    for path in SAMPLES.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if "MaterialsDeadline" not in record or "_return_type" not in record:
            continue
        expected = firm.firm_fields(record.get("_season", "2026"),
                                    record["_return_type"])["MaterialsDeadline"]
        assert record["MaterialsDeadline"] == expected, (
            f"{path.name} states {record['MaterialsDeadline']!r}; the firm's "
            f"deadline for a {record['_return_type']} return is {expected!r}"
        )


def test_an_unknown_return_type_is_refused():
    with pytest.raises(KeyError):
        firm.firm_fields("2026", "sole_trader")


def test_a_season_nobody_typed_still_produces_a_real_date():
    """THE GUARANTEE HELD, THE MECHANISM CHANGED. This used to read "a season
    with no deadlines is refused", because a season missing from
    `firm-settings.yaml` left `MaterialsDeadline` blank and three documents
    printed the hole. Refusing was the only defence available.

    `deadlines.py` derives the date from IRC 6072 and 7503 now, so a season
    nobody typed is answered rather than refused — and the annual chore of
    rolling four dates forward by hand is gone with it. What must still hold is
    the thing the old test was protecting: **the field is never blank.**
    """
    got = firm.firm_fields("1999")["MaterialsDeadline"]
    assert got and got.strip(), "the blank date the old refusal existed to stop"
    assert "2000" in got, f"a 1999 tax year is filed in 2000: {got}"


def test_a_season_that_cannot_be_derived_is_still_refused():
    """The other half. When neither the file nor the statute can answer, nothing
    is printed — which is the original guarantee, kept for the case that still
    needs it."""
    import settings as st

    with pytest.raises(KeyError, match="not derivable"):
        st._materials_deadline("not-a-year", "individual_1040", {})


def test_open_decisions_are_reported_with_their_question():
    """Every [CONFIRM] still in the settings comes back with the question that
    would settle it.

    This deliberately pins no particular key. It used to assert `legal_name`
    was open, which made answering it look like a regression — a test that
    fails when the project succeeds is worse than no test. What must hold is
    that whatever is still open is reported, and reported answerably."""
    decisions = firm.open_decisions()
    assert all(q for _, q in decisions), "a decision with no question is useless"

    # Comment lines are excluded: the file's own header explains the
    # "[CONFIRM: ...]" convention and would otherwise count as a decision.
    placeholders = sum(
        1 for line in firm.SETTINGS.read_text(encoding="utf-8").splitlines()
        if "[CONFIRM:" in line and not line.lstrip().startswith("#")
    )
    assert len(decisions) == placeholders, (
        "a placeholder in the file that open_decisions() does not report is a "
        "blank nobody will be asked about"
    )


# ── record assembly ───────────────────────────────────────────────────────

def test_firm_settings_fill_in_behind_the_record():
    record = cli.build_record({"_season": "2026", "ClientFullName": "Mr. and Mrs. Daniel Reyes"})
    assert record["PreparerName"], "firm settings did not reach the record"
    assert record["ClientFullName"] == "Mr. and Mrs. Daniel Reyes"


def test_the_record_wins_over_a_firm_default():
    """A per-engagement override is legitimate; ignoring it silently is not."""
    record = cli.build_record({"_season": "2026", "PreparerTitle": "Managing Partner"})
    assert record["PreparerTitle"] == "Managing Partner"


def test_a_record_without_a_season_is_refused():
    with pytest.raises(SystemExit):
        cli.build_record({"ClientFullName": "Mr. and Mrs. Daniel Reyes"})


def test_metadata_cannot_reach_a_document():
    """`_`-prefixed keys ride along for the filename; templates never ask for
    them, so they cannot be substituted into one."""
    record = cli.build_record(_load("tax-opening-package.json"))
    template = (cli.TEMPLATE_DIR / cli.DOCUMENTS["tax-letter"][0]).read_text(encoding="utf-8")
    import merge
    html = merge.render(template, record).html
    assert "_season" not in html and "_website_claims" not in html


# ── the two modes ─────────────────────────────────────────────────────────

def test_a_client_with_no_predecessor_gets_no_records_release():
    """The attachment goes out BY DEFAULT, which is not the same as always.
    A client with nobody to ask has nothing to sign."""
    record = cli.build_record(_load("tax-opening-package.json"))
    assert "records-release" in cli.opening_package(record)
    assert "records-release" not in cli.opening_package(dict(record, PriorFirm=False))


def test_a_complete_record_renders_the_whole_opening_package(tmp_path):
    rc = cli.main(["render", str(SAMPLES / "tax-opening-package.json"),
                   "--out", str(tmp_path), "--no-pdf"])
    assert rc == 0
    written = sorted(p.name for p in tmp_path.glob("*.html"))
    # NOT `OPENING_PACKAGE`: the demo record has a previous accountant, so
    # the package carries the records release as well. `opening_package()` is
    # what decides, and holding the test to the fixed list would have made
    # sending that attachment by default look like a bug.
    record = cli.build_record(_load("tax-opening-package.json"))
    assert len(written) == len(cli.opening_package(record)), written
    for f in tmp_path.glob("*.html"):
        text = f.read_text(encoding="utf-8")
        assert "&lt;&lt;" not in text, f"{f.name}: an unfilled field survived"
        assert "[CONFIRM:" not in text, f"{f.name}: an open decision survived"
        assert "DRAFT" not in text, f"{f.name}: a real render must not be stamped"


def test_real_mode_writes_nothing_when_a_document_would_be_holed(tmp_path):
    """The point of the whole thing. A refusal that still left a file on disk
    would be worse than no refusal — somebody would send the file."""
    thin = {"_season": "2026", "ClientFullName": "Mr. and Mrs. Daniel Reyes"}
    path = tmp_path / "thin.json"
    path.write_text(json.dumps(thin), encoding="utf-8")

    rc = cli.main(["render", str(path), "--docs", "tax-letter",
                   "--out", str(tmp_path / "out"), "--no-pdf"])
    assert rc == 1
    assert not list((tmp_path / "out").glob("*.html")), "a refused render left a file"


def test_draft_mode_renders_the_same_record_and_stamps_it(tmp_path):
    thin = {"_season": "2026", "ClientFullName": "Mr. and Mrs. Daniel Reyes"}
    path = tmp_path / "thin.json"
    path.write_text(json.dumps(thin), encoding="utf-8")

    rc = cli.main(["render", str(path), "--docs", "tax-letter", "--draft",
                   "--out", str(tmp_path / "out"), "--no-pdf"])
    assert rc == 0
    written = list((tmp_path / "out").glob("*.html"))
    assert len(written) == 1
    text = written[0].read_text(encoding="utf-8")
    assert "DRAFT" in written[0].name, "a draft must say so in its filename"
    assert "satc-draft-banner" in text
    assert 'slot="header"' in text, (
        "the banner must be in doc-page's running header slot, or it lands on "
        "page one only and page two looks exactly like the real letter"
    )
    assert "satc-open-decision" in text, "open decisions must be marked"


def test_a_draft_never_shares_a_filename_with_the_real_document():
    record = cli.build_record(_load("tax-opening-package.json"))
    real = cli.output_name("tax-letter", record, draft=False)
    draft = cli.output_name("tax-letter", record, draft=True)
    assert real != draft and "DRAFT" in draft and "DRAFT" not in real


def test_the_filename_carries_client_and_season():
    record = cli.build_record(_load("tax-opening-package.json"))
    name = cli.output_name("tax-letter", record, draft=False)
    assert "Reyes" in name and "2026" in name


# ── the lead path ─────────────────────────────────────────────────────────

def test_a_website_lead_becomes_a_record_skeleton(tmp_path):
    out = tmp_path / "record.json"
    rc = cli.main(["from-lead", str(SAMPLES / "website-lead.json"),
                   "--out", str(out), "--season", "2026", "--ref", "2027-0114"])
    assert rc == 0
    record = json.loads(out.read_text(encoding="utf-8"))

    # what the website genuinely knows is carried across
    assert record["ClientEmail"] == "dreyes@example.com"
    assert record["ClientCity"] == "Solon" and record["ClientState"] == "OH"
    assert record["EngagementRef"] == "2027-0114"

    # and what it does not know is marked, not guessed
    assert "[CONFIRM:" in record["ClientFullName"], (
        "the interview schema is explicit that a website answer is a claim, "
        "not a fact; a legal name must never be inferred from a first name. "
        "Since 26 August the salutation uses this same field, so a guess here "
        "would reach the top of every letter as well as the address block."
    )


def test_a_lead_skeleton_cannot_render_for_real(tmp_path):
    """It is a to-do list, not a record. Proving it refuses is the point."""
    out = tmp_path / "record.json"
    cli.main(["from-lead", str(SAMPLES / "website-lead.json"), "--out", str(out),
              "--season", "2026"])
    rc = cli.main(["render", str(out), "--docs", "tax-letter",
                   "--out", str(tmp_path / "out"), "--no-pdf"])
    assert rc == 1


# ── every template is reachable ───────────────────────────────────────────

def test_every_registered_template_is_wired_into_the_cli():
    """A template nobody can render is a template that does not exist."""
    from tests.test_registry import TEMPLATES
    assert set(cli.DOCUMENTS) == set(TEMPLATES), (
        "cli.DOCUMENTS and the registry disagree about which templates exist"
    )
    for name, (filename, _) in cli.DOCUMENTS.items():
        assert TEMPLATES[name] == filename, f"{name}: filename mismatch"
        assert (cli.TEMPLATE_DIR / filename).exists(), f"{name}: file missing"


# ── PDF, only where an engine exists ──────────────────────────────────────

def _engine():
    try:
        return cli.pdf_engine()[0]
    except cli.NoPdfEngine:
        return None


@pytest.mark.skipif(_engine() is None, reason="no PDF engine installed")
@pytest.mark.renders
def test_the_opening_package_reaches_pdf(tmp_path):
    rc = cli.main(["render", str(SAMPLES / "tax-opening-package.json"),
                   "--out", str(tmp_path)])
    assert rc == 0
    pdfs = sorted(tmp_path.glob("*.pdf"))
    record = cli.build_record(_load("tax-opening-package.json"))
    assert len(pdfs) == len(cli.opening_package(record)), [p.name for p in pdfs]
    for p in pdfs:
        assert p.stat().st_size > 4000, f"{p.name} is too small to be a document"
        assert p.read_bytes().startswith(b"%PDF"), f"{p.name} is not a PDF"


# ── an estimate with nothing on it ────────────────────────────────────────

def test_a_fee_estimate_with_no_line_items_is_refused(tmp_path):
    """The whole-document version of the merge-level guard.

    Rendered before this landed: a services table with no rows, and "Total
    estimate $785" underneath it. Every field resolved, no [CONFIRM] survived,
    and the render reported success -- because an `[[EACH]]` block over an
    empty list leaves nothing behind to object to. A bill has to say what it
    is billing for.
    """
    record = cli.build_record(_load("tax-opening-package.json"))
    record["LineItems"] = []
    with pytest.raises(merge.MergeError, match="LineItems is required"):
        cli._render_one("fee-estimate", record, tmp_path, draft=False, want_pdf=False)


def test_a_fee_estimate_with_no_assumptions_is_refused(tmp_path):
    """`pricing.price()`'s docstring records this exact collapse happening
    once already -- the assumptions block rendering to nothing "without the
    render so much as warning about it". The assumptions are not decoration:
    they are the half of the price that says what it stops covering.
    """
    record = cli.build_record(_load("tax-opening-package.json"))
    record["Assumptions"] = []
    with pytest.raises(merge.MergeError, match="Assumptions is required"):
        cli._render_one("fee-estimate", record, tmp_path, draft=False, want_pdf=False)


def test_a_draft_still_renders_without_line_items(tmp_path):
    """Draft mode exists to exercise the pipeline before the answers exist,
    and already tolerates unresolved fields. An empty list is the same kind of
    incompleteness, so it must not become the one thing a draft cannot survive.
    """
    record = cli.build_record(_load("tax-opening-package.json"))
    record["LineItems"] = []
    _, written = cli._render_one("fee-estimate", record, tmp_path,
                                 draft=True, want_pdf=False)
    assert written[0].exists()


def test_the_registry_is_what_decides_which_lists_are_required():
    """Not a hard-coded tuple in the front door. A document that later needs
    a list guarded gets one line of YAML, and this test proves the wiring
    rather than the particular answer.
    """
    required = cli._required_lists()
    assert "LineItems" in required.get("fee-estimate", ())
    assert "Assumptions" in required.get("fee-estimate", ())
    assert "LineItems" in required.get("invoice", ())
    # An extension notice with nothing outstanding is a real document.
    assert "OutstandingItems" not in required.get("extension-notice", ())


# ── doctor and render must agree ──────────────────────────────────────────

def test_doctor_and_render_agree_about_every_document(tmp_path):
    """They did not. `doctor --engagement` reported the organizer cover letter
    "Ready now" while `render` refused it, because doctor's readiness check
    left out the required-lists guard that render applies.

    Two halves of one tool disagreeing about the same document is worse than
    either answer on its own: whichever a person happens to run is the one
    they believe.
    """
    import engagements
    import merge as m

    record = cli.build_record(_load("tax-opening-package.json"))
    for doc, (filename, _) in cli.DOCUMENTS.items():
        template = (cli.TEMPLATE_DIR / filename).read_text(encoding="utf-8")

        def renders(**kw):
            try:
                m.render(template, record, **kw)
                return True
            except m.MergeError:
                return False

        doctor_says = renders(required_lists=cli._required_lists().get(doc, ()))
        try:
            cli._render_one(doc, record, tmp_path, draft=False, want_pdf=False)
            render_says = True
        except m.MergeError:
            render_says = False
        assert doctor_says == render_says, (
            f"{doc}: doctor says {'ready' if doctor_says else 'blocked'} and "
            f"render says {'ready' if render_says else 'blocked'}"
        )


def test_the_organizer_cover_letter_refuses_without_its_list():
    """It promises an enclosed organizer and a "what to send" list. With no
    `Requested`, section 01 is a heading with nothing under it."""
    record = cli.build_record(_load("tax-opening-package.json"))
    assert "Requested" not in record
    assert "Requested" in cli._required_lists()["organizer-letter"]
