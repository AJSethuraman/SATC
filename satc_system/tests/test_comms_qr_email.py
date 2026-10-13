"""The invoice email's payment QR code reaches the client as a picture, or not at all.

FOUND BY CODEX ON PR #430. The app opened Outlook drafts as plain text, so the
literal marker "[[ QR code ]]" would have sat under a sentence promising a code.
Now a draft with a payment link carries an HTML body with the code embedded,
and the plain-text body (Copy, mailto) drops the promise instead of breaking it.

No test here drives the desktop Outlook: the COM objects are stand-ins.
"""
import sys
import types

from satc.comms import load_library, render
from satc.comms.html import QR_CID, qr_png
from satc.comms.render import QR_MARKER

LINK = "https://square.link/u/EXAMPLE1"


def _draft(link: str = LINK):
    lib = load_library()
    values = {"fee_amount_text": "$480", "payment_link": link,
              "jurisdiction_summary": "• Federal: $100 refund\n• State: nothing due",
              "salutation": "Pat", "tax_year": "2025", "primary_first_name": "Pat"}
    values.update(lib.firm_values())
    return render(lib.template("invoice_cover"), values, library=lib)


def test_plain_text_never_shows_the_marker_or_promises_a_picture():
    body = _draft().body
    assert QR_MARKER not in body
    assert "scan this code" not in body
    assert f"here: {LINK}." in body
    assert "[[scan]]" not in body and "[[noscan]]" not in body
    # ALSO CODEX, second pass: step 1 still said "the link or code above" in
    # a draft that has no code.
    assert "code above" not in body
    assert "using the link above" in body


def test_the_html_body_still_points_at_the_code():
    assert "using the link or code above" in _draft().html


def test_the_app_declares_what_draws_the_code():
    """ALSO CODEX: segno was declared only in client-documents, so a clean
    install of this app could not draw the code at all."""
    import pathlib
    toml = (pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    deps = toml.split("[project.optional-dependencies]")[0]
    assert '"segno' in deps


def test_the_html_body_embeds_the_code_and_keeps_the_firms_format():
    d = _draft()
    html = d.html
    assert f'src="cid:{QR_CID}"' in html
    assert "scan this code with your phone camera" in html
    assert "Arial" in html and "12pt" in html
    assert html.count("<li>") >= 4          # results bulleted, steps numbered
    assert "<ol>" in html and "<ul>" in html
    assert QR_MARKER not in html
    assert d.qr_url == LINK


def test_without_a_link_there_is_no_html_and_no_code():
    d = _draft(link="")
    assert d.html == ""
    assert "payment_link" in d.unfilled
    assert "scan this code" not in d.body


def test_other_templates_stay_plain_text():
    lib = load_library()
    d = render(lib.template("welcome"), dict(lib.firm_values()), library=lib)
    assert d.html == ""


def test_outlook_gets_the_html_and_the_image_under_its_content_id(monkeypatch):
    calls = {}

    class _Props:
        def SetProperty(self, name, value):
            calls.setdefault("props", []).append((name, value))

    class _Att:
        PropertyAccessor = _Props()

    class _Attachments:
        def Add(self, path, *args):
            calls.setdefault("attached", []).append(open(path, "rb").read())
            return _Att()

    class _Mail:
        Attachments = _Attachments()
        def Display(self, modal):
            calls["shown"] = True

    class _App:
        def CreateItem(self, kind):
            calls["mail"] = mail = _Mail()
            return mail

    client = types.SimpleNamespace(Dispatch=lambda name: _App())
    monkeypatch.setitem(sys.modules, "win32com", types.SimpleNamespace(client=client))
    monkeypatch.setitem(sys.modules, "win32com.client", client)
    monkeypatch.setitem(sys.modules, "pythoncom", types.SimpleNamespace(
        CoInitialize=lambda: None, CoUninitialize=lambda: None))
    monkeypatch.setattr(sys, "platform", "win32")

    # conftest swaps the real function out so no test opens the desktop
    # Outlook; this one has replaced every COM object above with a stand-in, so
    # it takes the real code back, as conftest says a COM-branch test should.
    import importlib
    from satc.intake import email_draft
    open_outlook_draft = importlib.reload(email_draft).open_outlook_draft
    d = _draft()
    png = qr_png(d.qr_url)
    result = open_outlook_draft(to="client@example.com", subject=d.subject, body=d.body,
                                html_body=d.html, inline_images={QR_CID: png})
    assert result.ok
    mail = calls["mail"]
    assert mail.HTMLBody == d.html
    assert not hasattr(mail, "Body") or mail.Body != d.body
    assert calls["attached"] == [png]
    assert calls["props"][0][1] == QR_CID
    assert calls["props"][0][0].endswith("0x3712001F")
