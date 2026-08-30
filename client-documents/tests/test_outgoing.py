"""The pack, addressed — and the three things it refuses to guess at.

`sending.build` writes a pack to a folder and stops. It has no recipient and no
covering note, so the last step of getting an engagement out was a human
opening a portal, finding the client, attaching four files, and typing a note
from memory. These tests hold the assembly of that message, and hold the line
that stops the software writing to a client in the firm's name.
"""

from __future__ import annotations

import email
import email.policy
import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import engagements  # noqa: E402
import intake  # noqa: E402
import outgoing  # noqa: E402
import packaging  # noqa: E402
import signing  # noqa: E402


@pytest.fixture
def packed(tmp_path):
    """One engagement with a real pack on disk, built the way `package` does."""
    answers = json.loads(
        (ROOT / "samples" / "interview-answers.json").read_text(encoding="utf-8"))
    out = intake.finish(answers, store=tmp_path, today=date(2027, 2, 3))
    assert out.created, out.reason
    pack = tmp_path / "pack"
    assert cli.main(["package", "--engagement", out.ref, "--store",
                     str(tmp_path), "--out", str(pack), "--no-pdf"]) == 0
    record = cli.build_record(engagements.load(out.ref, tmp_path))
    return out.ref, tmp_path, record, pack


@pytest.fixture
def approved():
    """The registry as it reads once the firm has accepted the draft."""
    reg = json.loads(json.dumps(signing._registry()))
    for part in ("subject", "body"):
        reg["covering_note"][part] = outgoing.CONFIRM.sub(
            lambda m: m.group(1), reg["covering_note"][part])
    return reg


# ── the words are the firm's ──────────────────────────────────────────────

def test_it_will_not_write_to_a_client_in_wording_nobody_approved(packed):
    """The failure `CLAUDE.md` puts above the others: an agent writing to a
    client over the firm's name, in prose nobody read."""
    _, _, record, pack = packed
    with pytest.raises(outgoing.OutgoingError) as caught:
        outgoing.compose(record, pack, registry=signing._registry())
    said = str(caught.value)
    assert "waiting on the firm" in said
    assert "engagement letter" in said, "it must quote the draft back"
    assert "[CONFIRM:" in said, "and say exactly how to accept it"


def test_the_shipped_registry_is_the_one_that_refuses():
    """If somebody deletes the placeholder without reading it, that is a
    decision. Shipping it already accepted would be this file making it."""
    for part in ("subject", "body"):
        assert outgoing.CONFIRM.search(
            signing._registry()["covering_note"][part])


def test_the_draft_is_in_the_register_the_firm_actually_writes_in():
    """Rewritten 30 Aug 2026, and the rewrite is the point.

    This used to pin one exact sentence -- "Nothing begins until you have read
    it and signed" -- which made it a test of a string rather than of a rule,
    and the string was in the draft the firm then rejected outright:

        "This sounds awful. I can't explain why but it just does. I feel the
         tenets failed here. 'I will put it right'. That pathetic earnestness."

    Pinning wording cannot catch that, because the wording was the problem. What
    IS testable is the register: the firm's own letters are flat and second
    person -- "This letter tells you what to send us, where to send it, and what
    happens next", "We will not wait on them to start". They never perform
    feeling at the reader. So this asserts the three things that go wrong
    instead of one thing that went right once.
    """
    body = signing._registry()["covering_note"]["body"]

    # 1. No contract-desk verbs (DOCUMENT-TENETS, and CLAUDE.md rule 3).
    for word in ("pursuant", "governs", "herein", "constitutes", "shall be",
                 "accompanies", "at our discretion", "deemed"):
        assert word not in body.lower(), f"contract-desk wording: {word!r}"

    # 2. No pleading. The firm's actual objection, made testable so it cannot
    #    come back in a different sentence.
    for phrase in ("put it right", "happy to", "rest assured", "do not hesitate",
                   "don't hesitate", "apologi", "i hope", "we hope", "of course"):
        assert phrase not in body.lower(), f"earnestness: {phrase!r}"

    # 3. Length is the tell (CLAUDE.md rule 5). A client-facing sentence past
    #    ~25 words was written to be complete rather than to be read.
    prose = body.replace("[CONFIRM:", " ").replace("]", " ")
    for line in prose.split("\n"):
        for sentence in line.split(". "):
            words = [w for w in sentence.split() if w.strip()]
            assert len(words) <= 25, f"{len(words)} words: {sentence.strip()!r}"


def test_a_token_it_cannot_fill_stops_the_message(packed, approved):
    """A note that greets a client by the name of a field is worse than one
    that never went."""
    _, _, record, pack = packed
    thin = dict(record)
    thin.pop("ClientFullName")
    with pytest.raises(outgoing.OutgoingError, match="ClientFullName"):
        outgoing.compose(thin, pack, registry=approved)


# ── what travels with it ──────────────────────────────────────────────────

def test_only_the_documents_and_only_one_format_each(packed):
    """A pack folder holds the HTML, the stylesheet and the manifest too.
    Attaching all of it sends the firm's working files to a client."""
    _, _, _, pack = packed
    got = [p.name for p in outgoing.attachments_in(pack)]
    assert len(got) == 4
    assert not any("MANIFEST" in n or n.endswith(".css") or n.endswith(".js")
                   for n in got)
    assert len({n.rsplit(".", 1)[0] for n in got}) == len(got), "one per document"


def test_the_pdf_wins_where_there_is_one(tmp_path):
    """A client should get the PDF. HTML is the fallback for a machine with no
    PDF engine, not a second attachment."""
    for name in ("Letter.html", "Letter.pdf", "Estimate.html"):
        (tmp_path / name).write_bytes(b"x")
    got = [p.name for p in outgoing.attachments_in(tmp_path)]
    assert got == ["Estimate.html", "Letter.pdf"]


def test_a_covering_note_with_nothing_attached_is_refused(packed, approved):
    _, _, record, _ = packed
    empty = Path(packed[1]) / "nothing"
    empty.mkdir()
    with pytest.raises(outgoing.OutgoingError, match="nothing in"):
        outgoing.compose(record, empty, registry=approved)


def test_a_client_with_no_address_is_refused(packed, approved):
    _, _, record, pack = packed
    with pytest.raises(outgoing.OutgoingError, match="no email address"):
        outgoing.compose(dict(record, ClientEmail=""), pack, registry=approved)


# ── the file a mail client opens ──────────────────────────────────────────

def test_the_eml_is_an_ordinary_email_that_round_trips(packed, approved):
    """RFC 5322, which every mail client on earth opens. No credential, no
    connection, no vendor: the file is the handoff."""
    ref, store, record, pack = packed
    message = outgoing.compose(record, pack, registry=approved)
    path = outgoing.write(message, store, sender="arjun@example.com")

    back = email.message_from_bytes(path.read_bytes(),
                                    policy=email.policy.default)
    assert back["To"] == record["ClientEmail"]
    assert back["From"] == "arjun@example.com"
    # The engagement is identified by a HEADER, not by the subject. The subject
    # is the firm's copy -- asserting the ref appeared in it made this test pin
    # their wording, and it duly broke the moment they rewrote the draft.
    assert back["X-SATC-Engagement"] == ref
    assert record["PeriodLabel"] in back["Subject"]
    assert [a.get_filename() for a in back.iter_attachments()] == \
        [p.name for p in message.attachments]
    assert record["ClientFullName"] in back.get_body(("plain",)).get_content()


def test_the_note_keeps_its_paragraphs(packed, approved):
    """FOUND BY READING THE COMPOSED MESSAGE. YAML's folded block (`>-`) turns
    every line break into a space, which collapsed the covering note into one
    paragraph — a letter to a client with no paragraphs in it."""
    _, _, record, pack = packed
    body = outgoing.compose(record, pack, registry=approved).body
    assert "\n\n" in body
    assert body.count("\n\n") >= 2


def test_nothing_is_sent(packed, approved, monkeypatch):
    """The send is the one irreversible step in the pipeline, and it stays
    attached to a person. Nothing here opens a connection."""
    import smtplib

    def refuse(*a, **kw):                                   # pragma: no cover
        raise AssertionError("something tried to send")

    monkeypatch.setattr(smtplib, "SMTP", refuse)
    monkeypatch.setattr(smtplib, "SMTP_SSL", refuse)
    ref, store, record, pack = packed
    outgoing.write(outgoing.compose(record, pack, registry=approved), store)

    source = (ROOT / "outgoing.py").read_text(encoding="utf-8")
    for reach in ("smtplib", "requests", "urllib", "socket"):
        assert reach not in source, f"outgoing.py reaches for {reach}"


def test_the_pack_still_builds_when_the_note_is_unwritten(packed):
    """The covering note waiting on the firm must not cost anybody their
    pack — the documents are the deliverable, the note is a convenience."""
    ref, store, _, _ = packed
    out = store / "again"
    assert cli.main(["package", "--engagement", ref, "--store", str(store),
                     "--out", str(out), "--no-pdf", "--ready"]) == 0
    assert list(out.glob("*.html"))
    assert not list(out.glob("*.eml"))
