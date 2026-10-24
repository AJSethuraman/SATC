"""The onboarding and organizer letters are emails, not attachments.

The firm, 24 Oct 2026, marking both on the template review: "this is actually
supposed to be sent as an email not an attachment." So their templates are
email bodies, the opening pack sends the onboarding email AS its message, and
the organizer event writes its email as a draft to open and send.
"""
from __future__ import annotations

import email
from email import policy

import pytest

import cli
import emails
import presend

ONBOARDING = cli.TEMPLATE_DIR / "SATC Onboarding Email.html"
ORGANIZER = cli.TEMPLATE_DIR / "SATC Organizer Email.html"


@pytest.mark.parametrize("template", [ONBOARDING, ORGANIZER], ids=lambda p: p.stem)
def test_the_template_is_an_email_with_a_subject(template):
    html = template.read_text(encoding="utf-8")
    assert emails.is_email(html)
    assert "<doc-page" not in html, "an email body has no page component"
    subject, body = emails.parts(html)
    assert subject and '<div class="subject">' not in body


def test_neither_is_rendered_to_pdf(tmp_path):
    for doc in ("onboarding-letter", "organizer-letter"):
        assert emails.is_email((cli.TEMPLATE_DIR / cli.DOCUMENTS[doc][0]).read_text(encoding="utf-8"))


def test_the_plain_text_keeps_the_list_and_the_paragraphs():
    html = ('<div class="email"><p>Dear Ann,</p><p><b>What to send</b></p>'
            '<ul><li><b>W-2s</b> — both</li><li>1099s</li></ul>'
            '<p>Sincerely,<br/>Arjun</p></div>')
    plain = emails.to_plain(html)
    assert plain.startswith("Dear Ann,\n\nWhat to send\n\n• W-2s — both\n• 1099s\n")
    assert plain.rstrip().endswith("Sincerely,\nArjun")


def test_a_draft_is_crlf_and_base64_never_quoted_printable(tmp_path):
    """Outlook mis-read an LF, quoted-printable file on 13 Oct 2026 and
    scattered "=" through a client email."""
    att = tmp_path / "Letter.pdf"
    att.write_bytes(b"%PDF-1.4 x")
    raw = emails.to_eml("Subject", '<div class="email"><p>Hi = there</p></div>',
                        "Hi = there\n", to="a@example.com", attachments=[att])
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert b"quoted-printable" not in raw
    msg = email.message_from_bytes(raw, policy=policy.default)
    assert msg["X-Unsent"] == "1" and msg["To"] == "a@example.com"
    assert [p.get_filename() for p in msg.iter_attachments()] == ["Letter.pdf"]
    assert msg.get_body(("plain",)).get_content().strip() == "Hi = there"


def test_the_gate_reads_an_email_body_as_an_email(tmp_path):
    """`renders` demanded the page component and the firm's print face of
    every document, which an email has neither of by design. An email set in
    the browser's default serif is still unreadable, and still caught."""
    good = tmp_path / "good.html"
    good.write_text('<!doctype html><html><body><div class="email" '
                    'style="font-family:Arial,sans-serif"><p>Hi</p></div></body></html>',
                    encoding="utf-8")
    bad = tmp_path / "bad.html"
    bad.write_text('<!doctype html><html><body><div class="email"><p>Hi</p></div>'
                   '</body></html>', encoding="utf-8")
    found = presend.renders([good, bad])
    assert [f.document for f in found] == ["bad.html"], [(f.document, f.detail) for f in found]


def test_the_organizer_event_writes_a_draft_to_send(tmp_path):
    """`render` of an email writes the .eml beside it: an .html file is no
    use to somebody who has to send it."""
    import json
    record = json.loads((cli.SAMPLES / "tax-opening-package.json").read_text(encoding="utf-8"))
    record.pop("_comment", None)
    record.update(TaxYear="2026", FeeChange=False,
                  Requested=[{"Category": "W-2s", "Detail": "Both employers"}])
    src = tmp_path / "record.json"
    src.write_text(json.dumps(record), encoding="utf-8")
    out = tmp_path / "out"
    assert cli.main(["render", str(src), "--docs", "organizer-letter", "--out", str(out),
                     "--no-pdf", "--skip-render"]) == 0
    drafts = sorted(out.glob("*.eml"))
    assert len(drafts) == 1, sorted(p.name for p in out.iterdir())
    msg = email.message_from_bytes(drafts[0].read_bytes(), policy=policy.default)
    assert msg["Subject"] == "Your 2026 tax organizer"
    assert "is attached" in msg.get_body(("plain",)).get_content()
    assert not sorted(out.glob("*.pdf"))


def _opening_record(tmp_path, **changes):
    import json
    record = json.loads((cli.SAMPLES / "tax-opening-package.json").read_text(encoding="utf-8"))
    record.pop("_comment", None)
    record.update(changes)
    src = tmp_path / "record.json"
    src.write_text(json.dumps(record), encoding="utf-8")
    return src


def test_the_onboarding_draft_carries_what_it_says_is_attached(tmp_path):
    """Found by Codex on #478: `render` of the opening package wrote the
    onboarding draft with nothing attached, beside the letter and estimate it
    tells the client are attached."""
    out = tmp_path / "out"
    assert cli.main(["render", str(_opening_record(tmp_path)), "--out", str(out),
                     "--no-pdf", "--skip-render"]) == 0
    drafts = sorted(out.glob("*.eml"))
    assert len(drafts) == 1, sorted(p.name for p in out.iterdir())
    msg = email.message_from_bytes(drafts[0].read_bytes(), policy=policy.default)
    names = sorted(p.get_filename() for p in msg.iter_attachments())
    written = sorted(p.name for p in out.glob("*.html") if not emails.is_email(p.read_text(encoding="utf-8")))
    assert names == written and len(names) >= 2, (names, written)
    plain = msg.get_body(("plain",)).get_content()
    if "authorization" in plain:
        assert any("Release" in n for n in names), names


def test_no_draft_promises_a_document_the_run_did_not_render(tmp_path, capsys):
    out = tmp_path / "out"
    assert cli.main(["render", str(_opening_record(tmp_path)), "--docs", "onboarding-letter",
                     "--out", str(out), "--no-pdf", "--skip-render"]) == 0
    assert not sorted(out.glob("*.eml"))
    said = capsys.readouterr().out
    assert "no draft" in said and "engagement letter" in said, said


def test_the_organizer_draft_says_to_attach_the_organizer(tmp_path, capsys):
    """The organizer itself is printed from Drake; this software cannot attach
    it, so the run says to."""
    out = tmp_path / "out"
    src = _opening_record(tmp_path, TaxYear="2026", FeeChange=False,
                          Requested=[{"Category": "W-2s", "Detail": "Both employers"}])
    assert cli.main(["render", str(src), "--docs", "organizer-letter", "--out", str(out),
                     "--no-pdf", "--skip-render"]) == 0
    assert "before sending, attach: The organizer itself, printed from Drake." in capsys.readouterr().out
