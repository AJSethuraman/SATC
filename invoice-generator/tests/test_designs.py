"""The design gallery changes how an invoice looks and nothing else.

That sentence is the whole contract, and these tests are what make it one
rather than an intention. Two things have to hold for all 48:

1. **The money is identical.** A skin that could move a total would be a
   catastrophe of a different order than a skin that looks wrong.
2. **The markup is identical.** The editor reskins by swapping one stylesheet
   and touching nothing else, which is only safe if the document really is the
   same document underneath. It is also what keeps the on-screen preview and
   the printed PDF the same layout rather than two that resemble each other.
"""
import re

import pytest

from config import Config
from app import create_app
from designs import (
    DEFAULT_DESIGN,
    FAMILIES,
    PALETTES,
    all_designs,
    is_design,
    resolve,
)
from models import Invoice, LineItem


@pytest.fixture
def app(tmp_path):
    class DesignConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path}/designs-test.db"
        INVOICES_DIR = tmp_path / "invoices"
        SECRET_KEY = "test-secret-not-a-real-key"
        ENV = "development"
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False

    return create_app(DesignConfig)


def _invoice(design=None):
    inv = Invoice(
        invoice_number="INV-0007",
        from_info="Bramble & Finch Consulting\n4 Tinder Lane",
        bill_to="Northwind Traders LLC\n9 Harbor Way",
        currency="USD",
        tax_value=8.25,
        tax_is_percent=True,
        discount_value=50,
        discount_is_percent=False,
        shipping=0.0,
        amount_paid=100.0,
        status="Draft",
        design=design,
    )
    inv.items.append(LineItem(position=0, description="Return", quantity=1, rate=450))
    inv.items.append(LineItem(position=1, description="Review", quantity=2, rate=175))
    inv.items.append(LineItem(position=2, description="Worksheet", quantity=4, rate=60))
    return inv


# --- the gallery itself ---------------------------------------------------

def test_the_gallery_is_every_family_crossed_with_every_palette():
    # The count is asserted from the two lists rather than written down, so it
    # cannot go stale when a family or a palette is added.
    assert len(all_designs()) == len(FAMILIES) * len(PALETTES)


def test_every_design_id_is_unique():
    ids = [d["id"] for d in all_designs()]
    assert len(ids) == len(set(ids))


def test_every_design_resolves_to_a_complete_token_set():
    required = {
        "id", "family", "palette", "label", "blurb", "ink", "accent", "soft",
        "font", "head", "thead", "muted", "body", "line", "zebra",
    }
    for d in all_designs():
        assert required <= set(d), f"{d['id']} is missing {required - set(d)}"


@pytest.mark.parametrize("bogus", [None, "", "not-a-design", "classic", "x-y-z", 7, []])
def test_an_unrecognised_design_falls_back_rather_than_failing(bogus):
    # Deliberately a default and not a refusal — see designs.resolve. A stale
    # bookmark must not stop an invoice rendering, and no money moves either way.
    assert resolve(bogus)["id"] == DEFAULT_DESIGN
    assert not is_design(bogus)


def test_the_default_design_is_a_real_design():
    assert is_design(DEFAULT_DESIGN)


# --- the money invariant --------------------------------------------------

def test_every_design_totals_the_same_invoice_identically():
    """The one thing a skin may never do."""
    expected = None
    for d in all_designs():
        inv = _invoice(d["id"])
        got = (inv.subtotal, inv.discount_amount, inv.tax_amount,
               inv.total, inv.balance_due)
        if expected is None:
            expected = got
        assert got == expected, f"{d['id']} changed the money"
    assert expected == (1040.0, 50.0, 81.67, 1071.67, 971.67)


# --- the stylesheet -------------------------------------------------------

def test_no_design_stylesheet_contains_an_html_entity(app):
    """Jinja autoescaping inside a <style> block is silent and total.

    ``font-family: "Helvetica Neue", ...`` interpolated through Jinja became
    ``font-family: &#34;Helvetica Neue&#34;, ...``, which is not a valid
    declaration — so every design that asked for a sans stack printed in the
    renderer's default serif, and the browser (which recovers differently from
    WeasyPrint) disagreed with the PDF. Nothing failed; the PDFs rendered
    beautifully in the wrong face.

    Asserted over the whole sheet rather than the font line alone so the next
    interpolated value carrying a quote or an ampersand is caught too.
    """
    with app.test_request_context():
        from flask import render_template

        for d in all_designs():
            css = render_template("_invoice_css.html", design=d)
            for entity in ("&#34;", "&#39;", "&amp;", "&lt;", "&gt;"):
                assert entity not in css, f"{d['id']} emitted {entity}"


def test_every_design_names_a_font_stack_that_ends_in_a_generic_family(app):
    # The container that renders the PDF has neither Helvetica nor Georgia.
    # Without a generic at the end of the stack the engine picks its own
    # default, which is how the serif bug above stayed invisible.
    with app.test_request_context():
        from flask import render_template

        for d in all_designs():
            css = render_template("_invoice_css.html", design=d)
            stacks = re.findall(r"font-family:\s*([^;]+);", css)
            assert stacks, f"{d['id']} declared no font at all"
            for stack in stacks:
                assert re.search(
                    r"(sans-serif|serif|monospace)\s*$", stack.strip()
                ), f"{d['id']}: {stack!r} has no generic fallback"


def test_switching_design_changes_the_stylesheet_and_not_the_markup(app):
    """The promise behind 'switching a design keeps everything you have typed'.

    The editor swaps one <style> block. If two designs produced different
    document markup, that swap would leave the page in a state neither design
    describes — and the editor's DOM would no longer be the PDF's DOM.
    """
    from flask import render_template

    with app.test_request_context():
        rendered = {}
        for d in all_designs():
            rendered[d["id"]] = render_template(
                "_invoice_document.html", design=d
            ) + render_template(
                "invoice_pdf.html",
                invoice=_invoice(d["id"]),
                business={"name": "B", "lines": [], "address_text": "", "logo_uri": None},
                design=d,
                doc_title="INVOICE",
                pay_url=None,
            )

    def body_only(html):
        # Strip the <style> block; what remains is the document's markup.
        return re.sub(r"<style>.*?</style>", "", html, flags=re.S)

    bodies = {k: body_only(v) for k, v in rendered.items()}
    first = bodies[DEFAULT_DESIGN]
    for design_id, markup in bodies.items():
        assert markup == first, f"{design_id} rendered different markup"


@pytest.mark.parametrize("design_id", [d["id"] for d in all_designs()])
def test_every_design_renders_a_real_pdf_with_the_right_total(app, design_id, tmp_path):
    """Opened, not counted. Each design's PDF is parsed and the total read back.

    The first tenet in docs/SOFTWARE-TENETS.md exists because a proof artifact
    once declared 190 documents fine when every one was unreadable.
    """
    pypdf = pytest.importorskip("pypdf")
    from pdf import render_invoice_pdf

    out = tmp_path / f"{design_id}.pdf"
    with app.app_context():
        render_invoice_pdf(_invoice(design_id), out)

    assert out.exists() and out.stat().st_size > 1000
    assert out.read_bytes()[:5] == b"%PDF-"
    text = pypdf.PdfReader(str(out)).pages[0].extract_text()
    assert "$1,071.67" in text, f"{design_id} lost the total"
    assert "$971.67" in text, f"{design_id} lost the balance due"
    assert "Northwind Traders LLC" in text
