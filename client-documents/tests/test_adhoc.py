"""Using pieces of this ad hoc: looking at one document, and sending one.

THE FIRM, 2 September 2026:

    we have a lot of, what i would consider to be, smaller functions. i would
    want to be able to re-print stuff, so obviously i dont want to have to do
    an interview every time i make an engagement letter. the GUI needs to have
    a way to use pieces of this stuff ad hoc.

and, on being told every one of those pieces would pass the blocking gate:

    this makes sense but what we need to be able to also like print it or
    something to screen - or a preview. something like it doesn't make sense
    to forcibly have one output

THE TWO ACTS THESE TESTS HOLD APART. Looking at a document is nobody's copy but
yours: it is never blocked, and it says on every page that it is not the copy
that goes out. Sending one is the artefact a client receives: same gate, same
written reason, same log as the pack.

The one refusal here that is NOT the gate's is `packaging`'s, wearing a
different hat: a document that travels with the signing pack may be looked at
alone and may not be SENT alone, because "an engagement letter without its fee
estimate asks somebody to sign for work at a price they have not been shown".
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import invoicing  # noqa: E402
import packaging  # noqa: E402
import previewing  # noqa: E402
import web  # noqa: E402

SAMPLES = ROOT / "samples"
JSON = {"Accept": "application/json"}
HTML = {"Accept": "text/html"}


def _drive(client, answers) -> str:
    """A whole interview, over the JSON door, exactly as `test_web` does."""
    sid = client.post("/interview", headers=JSON).get_json()["draft"]
    while True:
        state = client.get(f"/interview/{sid}", headers=JSON).get_json()
        if state["complete"]:
            break
        client.post(f"/interview/{sid}",
                    json={"answer": answers.get(state["question"]["id"])},
                    headers=JSON)
    return client.post(f"/interview/{sid}/finish",
                       headers=JSON).get_json()["ref"]


@pytest.fixture
def answers():
    return json.loads(
        (SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))


@pytest.fixture
def templates(tmp_path, monkeypatch):
    """A throwaway copy, so a test that changes a sentence cannot change the
    repository's own letters. The same trick `capture.py` uses, for the same
    reason."""
    into = tmp_path / "templates"
    shutil.copytree(ROOT.parent / "satc-handoff" / "04-TEMPLATES", into)
    monkeypatch.setattr(cli, "TEMPLATE_DIR", into)
    return into


@pytest.fixture
def paperless(monkeypatch):
    """No PDF engine, so a test that sends a document does not spend a minute
    in a browser writing one.

    THE ROUTE ALREADY DOWNGRADES -- a machine with no engine gets the HTML
    rather than an error -- so this exercises a path the software really has.
    Exactly one test below does it for real, and it is marked `renders`.
    """
    def none(*_a, **_k):
        raise cli.NoPdfEngine("no engine in this test")
    monkeypatch.setattr(cli, "pdf_engine", none)


@pytest.fixture
def billed(tmp_path, answers, templates):
    """An engagement with a bill raised against it, and a client for it.

    The bill matters: the invoice is the one document in the firm's set that
    goes out on its own, so it is the one this whole surface can be proved on.
    """
    store = tmp_path / "store"
    app = web.create_app(store=store)
    app.config.update(TESTING=True)
    client = app.test_client()
    ref = _drive(client, answers)
    assert cli.main(["invoice", "--engagement", ref, "--store", str(store),
                     "--billed", "2026 tax year", "--no-link"]) == 0
    client.store, client.ref = store, ref
    return client


def _tree(store: Path) -> set[str]:
    return {str(p.relative_to(store)) for p in store.rglob("*")}


# ── looking ───────────────────────────────────────────────────────────────

def test_a_document_can_be_reached_without_answering_an_interview(billed):
    """The firm's sentence, as a test. The interview ran once, days ago; the
    document comes back from the answers already on file."""
    ref = billed.ref
    shelf = billed.get(f"/engagement/{ref}/documents",
                       headers=JSON).get_json()["documents"]
    keys = [d["document"] for d in shelf]
    assert "invoice" in keys and "tax-letter" in keys
    # Every lifecycle document is on the shelf too, whether or not it is ready.
    for doc in ("delivery-letter", "organizer-letter", "extension-notice",
                "disengagement-letter"):
        assert doc in keys, f"{doc} is not reachable from the shelf"
    page = billed.get(f"/engagement/{ref}/documents/invoice/page/")
    assert page.status_code == 200
    assert b"Amount due" in page.data or b"AMOUNT DUE" in page.data.upper()


def test_looking_at_a_document_writes_nothing(billed):
    """A preview that leaves a file behind is a file somebody can attach.

    BOTH PLACES, AND THE SECOND ONE IS THE ONE THAT WAS MISSING. This test
    first checked only the engagement store, and passed with the staging
    directory deliberately left on disk -- a folder of un-stamped, un-gated
    documents under the system's temporary files, which is precisely the
    artefact this whole design exists to not produce. Found by breaking the
    cleanup on purpose and watching the test stay green.
    """
    import tempfile
    tmp = Path(tempfile.gettempdir())
    before = _tree(billed.store)
    strays = set(tmp.glob("satc-look-*"))
    billed.get(f"/engagement/{billed.ref}/documents")
    billed.get(f"/engagement/{billed.ref}/documents/invoice")
    billed.get(f"/engagement/{billed.ref}/documents/invoice/page/")
    billed.get(f"/engagement/{billed.ref}/documents/extension-notice/page/")
    assert _tree(billed.store) == before
    left = set(tmp.glob("satc-look-*")) - strays
    assert not left, f"looking left {len(left)} folder(s) of documents behind"


def test_a_document_that_is_not_finished_still_comes_back(billed):
    """THE MOST USEFUL PREVIEW THERE IS. The extension notice needs facts
    nobody has supplied; refusing to show it is refusing to show somebody what
    is missing."""
    ref = billed.ref
    got = billed.get(f"/engagement/{ref}/documents/extension-notice",
                     headers=JSON).get_json()
    assert got["ready"] is False
    assert got["wanting"], "it refused and would not say what it wants"
    page = billed.get(f"/engagement/{ref}/documents/extension-notice/page/")
    assert page.status_code == 200 and len(page.data) > 2000


def test_what_is_missing_is_said_in_the_words_a_preparer_knows(billed):
    """`plainspoken`'s complaint, one surface over: the merge's own refusal
    reads "unresolved fields: <<ExtendedDeadline>>", and no preparer mid-call
    should ever be shown that."""
    body = billed.get(f"/engagement/{billed.ref}/documents/extension-notice",
                      headers=HTML).get_data(as_text=True)
    assert "Extended filing deadline" in body
    for leak in ("unresolved fields", "ExtendedDeadline", "&lt;&lt;",
                 "MergeError"):
        assert leak not in body, f"the screen showed {leak!r} to a preparer"


def test_every_preview_says_on_every_page_what_it_is(billed):
    """Not on page one. On EVERY page -- the banner goes in the repeating
    header, because page two of an unstamped copy is byte-identical to page
    two of the real letter."""
    for doc in ("invoice", "tax-letter", "extension-notice"):
        page = billed.get(
            f"/engagement/{billed.ref}/documents/{doc}/page/"
        ).get_data(as_text=True)
        assert 'slot="header"' in page and "satc-draft-banner" in page
        assert "not the copy that goes to the client" in page


def test_a_failed_check_is_shown_on_a_preview_and_stops_nothing(billed,
                                                                templates):
    """The firm's correction, held in place. A check that blocks a SEND must
    not block a LOOK -- seeing the problem is the reason to look."""
    letter = templates / cli.DOCUMENTS["invoice"][0]
    letter.write_text(
        letter.read_text(encoding="utf-8").replace(
            "</doc-page>",
            "<p>Payment is due pursuant to the terms above.</p></doc-page>"),
        encoding="utf-8")
    got = billed.get(f"/engagement/{billed.ref}/documents/invoice",
                     headers=JSON).get_json()
    assert any("pursuant" in f["detail"] for f in got["blocking"]), \
        "the preview did not notice what a send would refuse over"
    page = billed.get(f"/engagement/{billed.ref}/documents/invoice/page/")
    assert page.status_code == 200, "a failing check stopped a preview"


def test_the_files_a_document_links_are_served_and_nothing_else_is(billed):
    """A document served without its stylesheet is the "these html files are
    plain text?" bug arriving by a new door."""
    base = f"/engagement/{billed.ref}/documents/invoice/page/"
    assert billed.get(base + "satc-doc.css").status_code == 200
    assert billed.get(base + "doc-page.js").status_code == 200
    assert billed.get(base + "firm-settings.yaml").status_code == 404
    assert billed.get(base + "record.json").status_code == 404


# ── sending ───────────────────────────────────────────────────────────────

def test_sending_one_document_passes_the_same_gate(billed, paperless, templates):
    """The whole point of the split. Looking is free; sending is not."""
    doc = templates / cli.DOCUMENTS["invoice"][0]
    doc.write_text(
        doc.read_text(encoding="utf-8").replace(
            "</doc-page>",
            "<p>Payment is due pursuant to the terms above.</p></doc-page>"),
        encoding="utf-8")
    before = _tree(billed.store)
    got = billed.post(f"/engagement/{billed.ref}/documents/invoice",
                      json={}, headers=JSON)
    assert got.status_code == 409
    assert got.get_json()["status"] == "refused-gate"
    assert _tree(billed.store) == before, "a refused send wrote something"


def test_an_override_of_one_document_is_written_down(billed, paperless, templates):
    """A gate that can be waved through silently is not a gate."""
    doc = templates / cli.DOCUMENTS["invoice"][0]
    doc.write_text(
        doc.read_text(encoding="utf-8").replace(
            "</doc-page>",
            "<p>Payment is due pursuant to the terms above.</p></doc-page>"),
        encoding="utf-8")
    bare = billed.post(f"/engagement/{billed.ref}/documents/invoice",
                       json={"force": "1"}, headers=JSON)
    assert bare.get_json()["status"] == "no-reason"
    got = billed.post(f"/engagement/{billed.ref}/documents/invoice",
                      json={"force": "1", "reason": "client is on the phone"},
                      headers=JSON).get_json()
    assert got["status"] == "written" and got["override"]
    logged = json.loads(Path(got["override"]).read_text(encoding="utf-8"))
    assert "client is on the phone" in json.dumps(logged)


def test_the_copy_that_goes_out_carries_no_preview_stamp(billed, paperless):
    """THE OTHER HALF OF THE STAMP. A stamp that leaked into the sent copy
    would put "not the copy that goes to the client" on the copy that goes to
    the client -- and nothing else in the suite looks at both halves."""
    got = billed.post(f"/engagement/{billed.ref}/documents/invoice",
                      json={}, headers=JSON).get_json()
    assert got["status"] == "written"
    folder = billed.store / billed.ref / "documents" / "invoice"
    sent = next(folder.glob("*.html")).read_text(encoding="utf-8")
    assert "satc-draft-banner" not in sent
    assert "not the copy that goes to the client" not in sent
    assert "not answered yet" not in sent
    # And the preview of the same document does carry it, so this test is
    # comparing two real things rather than asserting an absence twice.
    looked = billed.get(
        f"/engagement/{billed.ref}/documents/invoice/page/"
    ).get_data(as_text=True)
    assert "satc-draft-banner" in looked


def test_a_document_that_travels_with_the_pack_cannot_be_sent_alone(billed):
    """`packaging`'s rule, reached by the new door: "an engagement letter
    without its fee estimate asks somebody to sign for work at a price they
    have not been shown"."""
    before = _tree(billed.store)
    for doc in ("tax-letter", "fee-estimate", "onboarding-letter"):
        got = billed.post(f"/engagement/{billed.ref}/documents/{doc}",
                          json={}, headers=JSON)
        assert got.status_code == 409
        assert got.get_json()["status"] == "with-the-pack"
    assert _tree(billed.store) == before


def test_the_refusal_tells_you_what_to_do_instead(billed):
    """A refusal that does not name the way through is a dead end. The pack
    IS the reprint, and it needs no interview."""
    body = billed.post(f"/engagement/{billed.ref}/documents/tax-letter",
                       headers=HTML).get_data(as_text=True)
    assert "signing pack" in body and "no interview" in body.lower()


def test_the_alone_rule_follows_the_pack_rather_than_a_list_of_its_own(
        monkeypatch):
    """CHECK THE CHECKER. A second hand-kept list of what may go alone would
    drift from `packaging.PACKS` the first time a return type is added -- and
    it would drift in the direction that lets a lone engagement letter out."""
    record = {"_return_type": "individual"}
    assert previewing.alone_ok(record, "tax-letter")[0] is False
    assert previewing.alone_ok(record, "invoice")[0] is True
    monkeypatch.setitem(packaging.PACKS, "individual", ["invoice"])
    assert previewing.alone_ok(record, "invoice")[0] is False, (
        "the rule is not derived from the pack -- it is a copy of it")
    assert previewing.alone_ok(record, "tax-letter")[0] is True


def test_a_record_that_does_not_say_what_it_is_may_not_send_anything(billed):
    """The permissive guess is the one that costs something."""
    allowed, why = previewing.alone_ok({}, "invoice")
    assert allowed is False and why


def test_sending_one_document_leaves_the_signing_pack_alone(billed, paperless):
    """`sending.build` OWNS its output folder and replaces what it wrote
    there. Point a one-document send at the pack's folder and the pack is
    gone."""
    ref = billed.ref
    built = billed.post(f"/engagement/{ref}/package", json={},
                        headers=JSON).get_json()
    assert built["status"] == "written"
    pack_before = sorted(p.name for p in (billed.store / ref / "pack").iterdir())
    sent = billed.post(f"/engagement/{ref}/documents/invoice", json={},
                       headers=JSON).get_json()
    assert sent["status"] == "written"
    assert sorted(p.name for p in (billed.store / ref / "pack").iterdir()) \
        == pack_before
    assert (billed.store / ref / "documents" / "invoice").is_dir()


# ── the bill lives beside the engagement, and both doors have to know ──────

def test_the_invoice_carries_its_bill_by_either_door(billed, tmp_path):
    """The regression this surface was built on top of. `render --docs
    invoice` remembered to fetch the bill; the browser did not."""
    ref = billed.ref
    got = billed.get(f"/engagement/{ref}/documents/invoice",
                     headers=JSON).get_json()
    assert got["ready"] is True, got
    out = tmp_path / "byhand"
    assert cli.main(["render", "--engagement", ref, "--store",
                     str(billed.store), "--docs", "invoice", "--out",
                     str(out), "--no-pdf"]) == 0


def test_the_pack_screen_can_actually_include_the_invoice(billed, paperless):
    """FOUND BY TICKING THE BOX. "Put the invoice in too" refused the whole
    pack every time -- and because a pack is atomic, that meant no letter, no
    estimate and no onboarding letter either."""
    got = billed.post(f"/engagement/{billed.ref}/package",
                      json={"invoice": "1"}, headers=JSON).get_json()
    assert got["status"] == "written", got
    assert any("Invoice" in name for name in got["written"])


def test_asking_for_an_invoice_before_one_is_raised_says_so(tmp_path, answers,
                                                            templates):
    app = web.create_app(store=tmp_path / "store")
    client = app.test_client()
    ref = _drive(client, answers)
    got = client.post(f"/engagement/{ref}/package", json={"invoice": "1"},
                      headers=JSON)
    assert got.status_code == 400
    assert "no bill raised" in got.get_json()["detail"]


# ── the structural rules this front door lives under ──────────────────────

def test_web_decides_nothing_about_looking_or_sending():
    """Same rule the interview and the packaging screens live under."""
    src = (ROOT / "web.py").read_text(encoding="utf-8")
    for smell in ("presend.gate(", "PACK_ASSETS", "record_override(",
                  "tempfile.mkdtemp", "packaging.PACKS", "merge.render("):
        assert smell not in src, (
            f"web.py contains {smell!r} -- that decision belongs in "
            f"previewing or sending, where the terminal reaches it too")


def test_a_document_that_is_not_finished_is_not_offered_for_sending(billed):
    """A button that we already know refuses is not a button. The extension
    notice has no answers behind it, so the page says so instead."""
    body = billed.get(
        f"/engagement/{billed.ref}/documents/extension-notice",
        headers=HTML).get_data(as_text=True)
    assert "Send this one" not in body
    assert "nothing to send yet" in body.lower()
    # And the invoice, which IS finished, still is.
    ready = billed.get(f"/engagement/{billed.ref}/documents/invoice",
                       headers=HTML).get_data(as_text=True)
    assert "Send this one" in ready


def test_a_blank_in_a_preview_is_named_not_spelled(billed):
    """The document itself is a screen a preparer reads. A raw token in the
    middle of a letter is the same failure `plainspoken` catches on the pages
    around it."""
    page = billed.get(
        f"/engagement/{billed.ref}/documents/extension-notice/page/"
    ).get_data(as_text=True)
    assert "&lt;&lt;" not in page and "<<Payment" not in page
    assert "Payment due by — not answered yet" in page \
        or "Payment due by &mdash; not answered yet" in page


def test_two_flags_that_are_one_question_are_listed_once(billed):
    """"Nothing to pay with the extension" and "a payment goes with the
    extension" side by side reads as a contradiction. They are one answer
    nobody has given, and `lifecycle` already knows the question."""
    got = billed.get(f"/engagement/{billed.ref}/documents/extension-notice",
                     headers=JSON).get_json()["wanting"]
    assert any("payment due with the extension" in w.lower() for w in got)
    assert not any(w.lower().startswith("nothing to pay") for w in got)


def test_what_failed_is_named_above_the_table_that_marks_it_failed(billed):
    """The packaging screen already has this test; this is the same screen
    one door over. A page that marks a check FAIL in the table and says
    nothing about it above is a page whose two halves disagree.

    Reached on a document that is NOT ready, which is where it was wrong: the
    failures were drawn inside the "can this be sent" branch.
    """
    body = billed.get(f"/engagement/{billed.ref}/documents/extension-notice",
                      headers=HTML).get_data(as_text=True)
    got = billed.get(f"/engagement/{billed.ref}/documents/extension-notice",
                     headers=JSON).get_json()
    assert got["blocking"], "no failures to check the page against"
    assert "would stop this going out" in body
    for f in got["blocking"]:
        assert web.esc(f["detail"])[:60] in body, (
            "the table marks this FAIL and the page never says what it was")


def test_the_new_screens_answer_both_a_human_and_a_script(billed):
    ref = billed.ref
    for path in (f"/engagement/{ref}/documents",
                 f"/engagement/{ref}/documents/invoice"):
        as_html = billed.get(path, headers=HTML)
        as_json = billed.get(path, headers=JSON)
        assert as_html.status_code == as_json.status_code == 200
        assert as_html.data.startswith(b"<!doctype html")
        assert as_json.is_json


def test_the_engagement_page_offers_the_shelf(billed):
    """A door nothing links to is a door nobody finds."""
    body = billed.get(f"/engagement/{billed.ref}",
                      headers=HTML).get_data(as_text=True)
    assert f"/engagement/{billed.ref}/documents" in body


def test_the_shelf_does_not_offer_a_document_nothing_can_place(billed):
    """The bookkeeping engagement letter is in no pack and no lifecycle event,
    so nothing in the software says when a client should get one. Offering it
    would be this screen inventing a rule the rest of the system has not
    got."""
    keys = [d["document"] for d in
            billed.get(f"/engagement/{billed.ref}/documents",
                       headers=JSON).get_json()["documents"]]
    assert "bookkeeping-letter" not in keys
    assert "business-letter" not in keys, "an individual was offered the entity letter"


# ── and once, for real ────────────────────────────────────────────────────

@pytest.mark.renders
def test_a_document_sent_on_its_own_comes_out_as_a_pdf_a_client_can_open(
        billed):
    """S1. Nothing here may claim a document works without opening it.

    Every test above this line reads HTML as a string, which is exactly right
    for checking a merge and totally blind to whether the thing renders. This
    one puts the invoice through the real engine -- the gate's own browser
    check included -- and looks at what came out.
    """
    got = billed.post(f"/engagement/{billed.ref}/documents/invoice",
                      json={}, headers=JSON).get_json()
    assert got["status"] == "written", got
    folder = billed.store / billed.ref / "documents" / "invoice"
    pdfs = list(folder.glob("*.pdf"))
    assert pdfs, f"no PDF in {sorted(p.name for p in folder.iterdir())}"
    assert pdfs[0].stat().st_size > 20_000, "a PDF that small is a blank page"
    assert pdfs[0].read_bytes().startswith(b"%PDF")
    # The stylesheet and the script travel with it, or it opens as plain text.
    assert (folder / "satc-doc.css").is_file()
    assert (folder / "doc-page.js").is_file()
