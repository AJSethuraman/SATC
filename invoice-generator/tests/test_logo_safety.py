"""An uploaded logo is a document, and a document can reach out.

`/generator/pdf` takes a logo upload with no login. SVG is a document format:
it can reference other URLs, and WeasyPrint will dereference them **from the
application server** while rendering. That turned the anonymous generator into
an unauthenticated SSRF — post an SVG carrying

    <image href="http://169.254.169.254/latest/meta-data/..."/>

and the container fetches it, with the response able to land in the PDF handed
straight back to the poster. Cloud metadata, internal services, anything the
container can route to.

Two independent layers, tested independently here, because the renderer is the
real boundary and the upload check is the one that gives a clean refusal:

1. `pdf._no_network_fetcher` resolves `data:` and refuses every other scheme,
   which covers routes into the renderer that do not exist yet.
2. `app._svg_reaches_outside` drops the upload at the door.

Raised by Codex on PR #289, round five.
"""
import pytest

from config import Config
from app import create_app, _svg_reaches_outside, _read_logo
from models import Invoice
import pdf as pdf_module


PLAIN_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    b'<rect width="10" height="10" fill="#059669"/></svg>'
)
# Note the xmlns above: an ordinary SVG carries an http URL in its namespace
# declaration, which is why the check cannot simply be "contains http".
REACHING_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    b'<image href="http://169.254.169.254/latest/meta-data/iam/'
    b'security-credentials/" width="10" height="10"/></svg>'
)
SCRIPTED_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg">'
    b'<script>fetch("http://internal/")</script></svg>'
)
ENTITY_SVG = (
    b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    b'<svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>'
)


@pytest.fixture
def app(tmp_path):
    class LogoConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path}/logo-test.db"
        INVOICES_DIR = tmp_path / "invoices"
        SECRET_KEY = "test-secret-not-a-real-key"
        ENV = "development"
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        REQUIRE_EMAIL_VERIFICATION = "never"

    return create_app(LogoConfig)


# --- layer one: the renderer refuses to fetch -----------------------------

def test_the_renderer_resolves_a_data_uri():
    # One transparent GIF, inline. Nothing leaves the process.
    uri = (
        "data:image/gif;base64,"
        "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    )
    result = pdf_module._no_network_fetcher(uri)
    assert result  # a dict WeasyPrint can read; the point is it did not raise


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "https://example.invalid/pixel.png",
        "file:///etc/passwd",
        "ftp://example.invalid/x",
        "//example.invalid/x",
    ],
)
def test_the_renderer_refuses_every_other_scheme(url):
    with pytest.raises(ValueError) as caught:
        pdf_module._no_network_fetcher(url)
    assert "Refused to fetch" in str(caught.value)


def test_a_pdf_of_an_invoice_carrying_a_reaching_svg_still_renders(
    app, tmp_path
):
    """The fetcher refuses the URL; it must not take the whole render down.

    A logo that reaches outside is dropped by the upload check, so this can
    only be reached by a row that predates the check — but a stored invoice
    that can no longer be printed at all would be a worse outcome than one
    printed without its logo.
    """
    with app.app_context():
        # Never added to the session: this stands for a row written before
        # the upload check existed, and the render must not need the database.
        invoice = Invoice(
            invoice_number="INV-SSRF-1",
            from_info="Bramble & Finch\n4 Tinder Lane",
            bill_to="Northwind Traders",
            currency="USD",
            status="Draft",
            amount_paid=0.0,
            tax_is_percent=True,
            discount_is_percent=True,
            logo_data=REACHING_SVG,
            logo_mimetype="image/svg+xml",
        )
        out = tmp_path / "ssrf.pdf"
        pdf_module.render_invoice_pdf(invoice, out)
        assert out.read_bytes()[:5] == b"%PDF-"


# --- layer two: the upload never gets in ----------------------------------

def test_a_plain_svg_is_allowed():
    assert _svg_reaches_outside(PLAIN_SVG) is False


@pytest.mark.parametrize(
    "payload", [REACHING_SVG, SCRIPTED_SVG, ENTITY_SVG],
    ids=["external-image", "script", "external-entity"],
)
def test_an_svg_that_reaches_outside_is_refused(payload):
    assert _svg_reaches_outside(payload) is True


def test_the_upload_drops_a_reaching_svg_and_keeps_a_plain_one(app):
    from io import BytesIO
    from werkzeug.datastructures import FileStorage

    def upload(data):
        return _read_logo(
            FileStorage(
                stream=BytesIO(data),
                filename="logo.svg",
                content_type="image/svg+xml",
            )
        )

    with app.app_context():
        good, mime = upload(PLAIN_SVG)
        assert good == PLAIN_SVG and mime == "image/svg+xml"
        bad, bad_mime = upload(REACHING_SVG)
        assert bad is None and bad_mime is None


def test_the_anonymous_generator_will_not_store_a_reaching_svg(app):
    """End to end on the door that made this reachable in the first place."""
    from io import BytesIO

    client = app.test_client()
    data = {
        "from_name": "Bramble & Finch Consulting",
        "bill_to_name": "Northwind Traders LLC",
        "invoice_number": "INV-SSRF-2",
        "invoice_date": "2026-09-06",
        "currency": "USD",
        "design": "band-emerald",
        "item_description": ["Return"],
        "item_quantity": ["1"],
        "item_rate": ["450"],
        "logo": (BytesIO(REACHING_SVG), "logo.svg"),
    }
    r = client.post(
        "/generator/pdf", data=data, content_type="multipart/form-data"
    )
    assert r.status_code == 200
    assert r.data[:5] == b"%PDF-"
    # The address is not in the PDF because the logo never made it in.
    assert b"169.254.169.254" not in r.data
