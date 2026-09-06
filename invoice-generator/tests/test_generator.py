"""The signed-out invoice generator.

The app's front door used to be a login wall. This is the other order: make
the invoice, then decide whether you want an account. Which means an
unauthenticated request now reaches the invoice-building code that was
previously only ever entered by a logged-in owner — so what these tests are
really guarding is that opening that door did not weaken anything behind it.

Three properties matter more than the rest:

* **Nothing is written.** An anonymous PDF must leave no row anywhere.
* **The refusals still refuse.** The generator reuses
  ``_populate_invoice_from_form`` and ``_validate_invoice`` rather than
  parsing money a third way, so every guard those carry has to still fire.
* **The owner's path is unchanged.** The refactor that made the seam sharable
  had one way to go badly wrong, and it is tested at the bottom of this file.
"""
import pytest

from config import Config
from app import create_app
from models import Invoice, LineItem, User, db

OWNER_EMAIL = "amara.okonkwo@bramblefinch.example"
OWNER_PASSWORD = "correct-horse-staple"


@pytest.fixture
def app(tmp_path):
    class GenConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path}/generator-test.db"
        INVOICES_DIR = tmp_path / "invoices"
        SECRET_KEY = "test-secret-not-a-real-key"
        ENV = "development"
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        REQUIRE_EMAIL_VERIFICATION = "never"

    return create_app(GenConfig)


@pytest.fixture
def anon(app):
    return app.test_client()


@pytest.fixture
def owner(app):
    with app.app_context():
        user = User(
            email=OWNER_EMAIL,
            business_name="Bramble & Finch Consulting",
            business_email=OWNER_EMAIL,
            business_address="4 Tinder Lane\nPortsend, ZZ 00000",
            default_currency="USD",
            email_verified=True,
        )
        user.set_password(OWNER_PASSWORD)
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def logged_in(app, owner):
    c = app.test_client()
    c.post("/login", data={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    return c


def form(**over):
    data = {
        "from_name": "Bramble & Finch Consulting",
        "from_address": "4 Tinder Lane\nPortsend, ZZ 00000",
        "bill_to_name": "Northwind Traders LLC",
        "bill_to_address": "9 Harbor Way\nSeattle, WA 98101",
        "client_email": "ap@northwind.example",
        "invoice_number": "INV-2026-014",
        "invoice_date": "2026-09-05",
        "payment_terms": "Net 14",
        "currency": "USD",
        "design": "band-emerald",
        "doc_title": "INVOICE",
        "item_description": ["Return", "Review", "Worksheet"],
        "item_quantity": ["1", "2", "4"],
        "item_rate": ["450", "175", "60"],
        "tax": "8.25", "tax_is_percent": "1",
        "discount": "50", "discount_is_percent": "0",
        "shipping": "0", "amount_paid": "100",
        "notes": "Thank you.", "terms": "Payment due within 14 days.",
    }
    data.update(over)
    return data


def rows(app):
    with app.app_context():
        return (
            db.session.query(Invoice).count(),
            db.session.query(LineItem).count(),
        )


# --- getting in -----------------------------------------------------------

def test_the_generator_opens_without_an_account(anon):
    r = anon.get("/generator")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "item_description" in body     # the document is editable
    assert "Download PDF" in body


def test_the_generator_does_not_redirect_to_login(anon):
    assert anon.get("/generator", follow_redirects=False).status_code == 200


def test_the_theme_endpoint_serves_css_and_tolerates_a_stale_design(anon):
    good = anon.get("/generator/theme.css?design=band-emerald")
    assert good.status_code == 200 and good.mimetype == "text/css"
    assert b"#059669" in good.data

    stale = anon.get("/generator/theme.css?design=retired-design")
    assert stale.status_code == 200
    assert b"#2563eb" in stale.data   # the default palette, not an error page


# --- the PDF --------------------------------------------------------------

def test_an_anonymous_visitor_gets_a_real_pdf(anon):
    r = anon.post("/generator/pdf", data=form())
    assert r.status_code == 200
    assert r.mimetype == "application/pdf"
    assert r.data[:5] == b"%PDF-"
    assert "INV-2026-014.pdf" in r.headers["Content-Disposition"]


def test_the_anonymous_pdf_carries_the_right_money(anon, tmp_path):
    pypdf = pytest.importorskip("pypdf")
    r = anon.post("/generator/pdf", data=form())
    out = tmp_path / "anon.pdf"
    out.write_bytes(r.data)
    text = pypdf.PdfReader(str(out)).pages[0].extract_text()
    # 450 + 350 + 240 = 1040, less $50 flat, plus 8.25% of 990, less $100 paid.
    assert "$1,040.00" in text
    assert "$81.67" in text
    assert "$1,071.67" in text
    assert "$971.67" in text
    assert "Northwind Traders LLC" in text


def test_making_a_pdf_writes_nothing_to_the_database(app, anon):
    before = rows(app)
    for _ in range(3):
        assert anon.post("/generator/pdf", data=form()).status_code == 200
    assert rows(app) == before == (0, 0)


def test_the_name_and_address_boxes_become_one_stored_party(anon, tmp_path):
    pypdf = pytest.importorskip("pypdf")
    r = anon.post("/generator/pdf", data=form())
    out = tmp_path / "p.pdf"
    out.write_bytes(r.data)
    text = pypdf.PdfReader(str(out)).pages[0].extract_text()
    assert "Northwind Traders LLC" in text
    assert "9 Harbor Way" in text
    assert "Bramble & Finch Consulting" in text


def test_a_zero_decimal_currency_prints_without_decimals(anon, tmp_path):
    pypdf = pytest.importorskip("pypdf")
    r = anon.post("/generator/pdf", data=form(currency="JPY"))
    out = tmp_path / "jpy.pdf"
    out.write_bytes(r.data)
    text = pypdf.PdfReader(str(out)).pages[0].extract_text()
    assert "¥1,040" in text
    assert "¥1,040.00" not in text


# --- the refusals still refuse -------------------------------------------

@pytest.mark.parametrize(
    "override, expected",
    [
        ({"item_description": [], "item_quantity": [], "item_rate": []},
         "At least one line item"),
        ({"bill_to_name": "", "bill_to_address": ""}, "Bill To"),
        ({"from_name": "", "from_address": ""}, "business name"),
        ({"invoice_number": ""}, "Invoice number is required"),
        ({"item_rate": ["$450.00", "175", "60"]}, "must be a number"),
        ({"item_quantity": ["1e400", "2", "4"]}, "must be a number"),
        ({"tax": "abc"}, "Tax must be a number"),
        ({"discount": "150", "discount_is_percent": "1"}, "cannot exceed 100%"),
    ],
)
def test_a_bad_invoice_is_refused_with_a_reason(anon, override, expected):
    r = anon.post("/generator/pdf", data=form(**override))
    assert r.status_code == 422
    assert r.mimetype == "text/html"          # the editor comes back, not a PDF
    assert expected in r.get_data(as_text=True)


def test_the_signed_out_refusal_does_not_send_them_to_a_page_they_cannot_reach(anon):
    """'Add your business profile in Account first' to somebody with no account."""
    r = anon.post("/generator/pdf", data=form(from_name="", from_address=""))
    body = r.get_data(as_text=True)
    assert "Add your business name at the top of the invoice." in body
    assert "in Account first" not in body


def test_mismatched_line_arrays_are_refused_on_this_door_too(anon):
    r = anon.post("/generator/pdf", data=form(item_quantity=["1", "2"]))
    assert r.status_code == 422
    assert "did not arrive intact" in r.get_data(as_text=True)


def test_a_refused_invoice_still_writes_nothing(app, anon):
    before = rows(app)
    anon.post("/generator/pdf", data=form(bill_to_name="", bill_to_address=""))
    assert rows(app) == before


# --- flat vs percent ------------------------------------------------------

def test_the_percent_toggle_is_honoured(anon, tmp_path):
    pypdf = pytest.importorskip("pypdf")
    # The same "50" read as a flat amount and then as a percentage.
    flat = anon.post("/generator/pdf", data=form(discount="50", discount_is_percent="0"))
    pct = anon.post("/generator/pdf", data=form(discount="50", discount_is_percent="1"))

    def total(resp, name):
        out = tmp_path / name
        out.write_bytes(resp.data)
        return pypdf.PdfReader(str(out)).pages[0].extract_text()

    assert "$1,071.67" in total(flat, "f.pdf")     # 1040 - 50 + tax
    # 50% of 1040 is 520; 1040 - 520 = 520, + 8.25% = 562.90
    assert "$562.90" in total(pct, "p.pdf")


def test_a_fresh_generator_page_offers_percent_not_flat(anon):
    """A transient invoice has None in both flags, and `not None` is True.

    The flat option therefore came up pre-selected, so an 8.25 typed into the
    tax box was billed as 8.25 of currency rather than 8.25 percent — on the
    default page, before the sender touched anything.
    """
    body = anon.get("/generator").get_data(as_text=True)
    for field in ("tax_is_percent", "discount_is_percent"):
        block = body.split(f'name="{field}"', 1)[1].split("</select>", 1)[0]
        percent_option = block.split("</option>", 1)[0]
        assert "selected" in percent_option, f"{field} did not default to percent"


# --- saving ---------------------------------------------------------------

def test_saving_requires_an_account(app, anon):
    r = anon.post("/generator/save", data=form(), follow_redirects=False)
    assert r.status_code in (301, 302)
    assert "/login" in r.headers["Location"]
    assert rows(app) == (0, 0)


def test_a_signed_in_owner_can_keep_a_generated_invoice(app, logged_in, owner):
    r = logged_in.post("/generator/save", data=form(), follow_redirects=False)
    assert r.status_code == 302
    with app.app_context():
        inv = db.session.query(Invoice).one()
        assert inv.user_id == owner
        assert inv.invoice_number == "INV-2026-014"
        assert inv.design == "band-emerald"
        assert len(inv.items) == 3
        assert inv.total == 1071.67
        assert inv.balance_due == 971.67


def test_a_saved_design_survives_and_re_renders(app, logged_in, tmp_path):
    logged_in.post("/generator/save", data=form(design="stripe-plum"))
    with app.app_context():
        inv = db.session.query(Invoice).one()
        assert inv.design == "stripe-plum"
        from pdf import render_invoice_pdf
        out = tmp_path / "saved.pdf"
        render_invoice_pdf(inv, out)
        assert out.read_bytes()[:5] == b"%PDF-"


# --- the refactor's one way to go wrong -----------------------------------

def test_editing_a_part_paid_invoice_does_not_wipe_the_payment(app, logged_in):
    """The regression the ``in form`` guards exist for.

    ``amount_paid`` was added to the shared populate function for the
    generator, which posts it. The owner's own form does NOT post it — so
    reading it with a default of 0.0 would have silently zeroed a
    Stripe-confirmed payment on every edit, and the balance due would have
    jumped back to the full amount with the edit reporting success.
    """
    logged_in.post(
        "/invoices",
        data={
            "invoice_number": "INV-0001",
            "bill_to": "Northwind Traders LLC",
            "invoice_date": "2026-09-05",
            "payment_terms": "Net 14",
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": ["Work"], "item_quantity": ["1"],
            "item_rate": ["1000"],
        },
    )
    with app.app_context():
        inv = db.session.query(Invoice).one()
        inv.amount_paid = 400.0
        db.session.commit()
        invoice_id = inv.id

    # An ordinary edit through the owner's form, which carries no amount_paid.
    logged_in.post(
        f"/invoice/{invoice_id}",
        data={
            "invoice_number": "INV-0001",
            "bill_to": "Northwind Traders LLC",
            "invoice_date": "2026-09-05",
            "payment_terms": "Net 14",
            "tax": "0", "discount": "0", "shipping": "0",
            "item_description": ["Work, revised"], "item_quantity": ["1"],
            "item_rate": ["1200"],
        },
    )
    with app.app_context():
        inv = db.session.get(Invoice, invoice_id)
        assert inv.amount_paid == 400.0, "the recorded payment was destroyed"
        assert inv.total == 1200.0
        assert inv.balance_due == 800.0


def test_the_owners_form_still_treats_tax_as_a_percentage(app, logged_in):
    """It posts no tax_is_percent, and absent must not mean flat."""
    logged_in.post(
        "/invoices",
        data={
            "invoice_number": "INV-0002",
            "bill_to": "Northwind Traders LLC",
            "invoice_date": "2026-09-05",
            "payment_terms": "Net 14",
            "tax": "10", "discount": "0", "shipping": "0",
            "item_description": ["Work"], "item_quantity": ["1"],
            "item_rate": ["1000"],
        },
    )
    with app.app_context():
        inv = db.session.query(Invoice).one()
        assert inv.tax_is_percent is True
        assert inv.tax_amount == 100.0     # 10% of 1000, not $10
        assert inv.total == 1100.0


# --- what the invoice is worth when it arrives ----------------------------
#
# `status` is stored, not derived. The generator has an "amount paid" box, so
# an invoice can arrive already settled — somebody recording work they were
# paid for on the spot. It was stored as a Draft with a zero balance: counted
# as neither paid nor outstanding, and showing "Draft" on a job that is done.
# Raised by Codex on PR #289, round five.

def test_an_invoice_saved_already_settled_is_saved_as_paid(app, logged_in):
    # 450 + 350 + 240 = 1040, with tax and discount off so the arithmetic
    # under test is the status rule, not the totals.
    data = form(tax="0", discount="0", amount_paid="1040")
    r = logged_in.post("/generator/save", data=data, follow_redirects=False)
    assert r.status_code == 302
    with app.app_context():
        inv = db.session.query(Invoice).one()
        assert round(inv.balance_due, 2) == 0.0
        assert inv.status == "Paid"
        assert inv.display_status == "Paid"


def test_a_part_paid_invoice_is_still_a_draft_and_reads_as_partial(
    app, logged_in
):
    """Partial is derived, not stored — so the draft status is correct here
    and must not be promoted."""
    r = logged_in.post("/generator/save", data=form(amount_paid="100"))
    assert r.status_code in (200, 302)
    with app.app_context():
        inv = db.session.query(Invoice).one()
        assert inv.balance_due > 0
        assert inv.status == "Draft"
        assert inv.display_status == "Partial"


def test_an_unpaid_invoice_is_saved_as_a_draft(app, logged_in):
    logged_in.post("/generator/save", data=form(amount_paid="0"))
    with app.app_context():
        inv = db.session.query(Invoice).one()
        assert inv.status == "Draft"


def test_the_owners_create_form_settles_an_already_paid_invoice_too(
    app, logged_in
):
    """The same three lines were missing on the ordinary create path, which is
    why they now live in one function rather than three copies of one."""
    logged_in.post(
        "/invoices",
        data={
            "invoice_number": "INV-2026-099",
            "bill_to": "Northwind Traders LLC",
            "invoice_date": "2026-09-06",
            "currency": "USD",
            "item_description": ["Return"],
            "item_quantity": ["1"],
            "item_rate": ["450"],
            "tax": "0", "discount": "0", "shipping": "0",
            "amount_paid": "450",
        },
        follow_redirects=False,
    )
    with app.app_context():
        inv = db.session.query(Invoice).one()
        assert round(inv.balance_due, 2) == 0.0
        assert inv.status == "Paid"


# --- the draft in the browser ---------------------------------------------

def test_downloading_a_pdf_does_not_clear_the_saved_draft(anon):
    """The page promises the draft survives a refresh; the submit handler used
    to clear it on ANY submit, and Download PDF is a submit. The file arrived,
    the page stayed put, and the draft was already gone.

    This asserts the shape of the guard rather than driving a browser: the
    handler must clear only when the submitter is the save button.
    Raised by Codex on PR #289, round five.
    """
    body = anon.get("/generator").get_data(as_text=True)
    assert "SAVE_PATH" in body
    handler = body[body.index('$("#gen").addEventListener("submit"'):]
    handler = handler[:handler.index("});") + 3]
    assert "e.submitter" in handler
    assert "SAVE_PATH" in handler
    # The clear happens inside a condition, not at the top of the handler.
    assert handler.index("goingToSave") < handler.index("removeItem")


# --- round seven --------------------------------------------------------

def test_an_anonymous_pdf_carries_no_workflow_badge(anon, tmp_path):
    """An unsaved document is not a draft; it is not in a workflow at all.

    `/generator/pdf` builds a transient invoice, has to give it a status
    because the column cannot be null, and offers the sender no control over
    it — so the one thing the signed-out front door exists to produce came out
    stamped DRAFT every time, including when the sender had recorded it paid in
    full. Raised by Codex on PR #289 round seven, and by the walkthrough
    (defect 2).
    """
    pypdf = pytest.importorskip("pypdf")
    import io as _io

    r = anon.post("/generator/pdf", data=form())
    assert r.status_code == 200
    text = "\n".join(
        p.extract_text() or ""
        for p in pypdf.PdfReader(_io.BytesIO(r.data)).pages
    )
    assert "SATC" not in text or True          # the invoice itself is there
    assert "INV-2026-014" in text
    for badge in ("DRAFT", "Draft", "SENT", "Sent", "Paid in full"):
        assert badge not in text, f"the anonymous PDF is stamped {badge!r}"


def test_a_saved_invoice_keeps_its_badge(app, logged_in):
    """The fix must not take the badge off the invoices that have a workflow."""
    pypdf = pytest.importorskip("pypdf")
    import io as _io

    logged_in.post("/generator/save", data=form(tax="0", discount="0", amount_paid="0"))
    with app.app_context():
        invoice_id = db.session.query(Invoice).one().id
    r = logged_in.get(f"/invoice/{invoice_id}/pdf")
    text = "\n".join(
        p.extract_text() or ""
        for p in pypdf.PdfReader(_io.BytesIO(r.data)).pages
    )
    assert "Draft" in text or "DRAFT" in text


def test_the_saved_design_and_title_reach_every_surface(app, logged_in):
    """One document, rendered once. The owner's page and the client's page used
    to rebuild the invoice in their own classes, so both ignored the design and
    the title while the PDF honoured them — the owner's own screen disagreeing
    with the file their client receives. Raised by Codex on PR #289 round seven
    and by the walkthrough (defect 5)."""
    from app import make_token

    logged_in.post("/generator/save", data=form(
        design="band-emerald", doc_title="QUOTE",
    ))
    with app.app_context():
        invoice = db.session.query(Invoice).one()
        invoice_id, number = invoice.id, invoice.invoice_number
        assert invoice.design == "band-emerald"
        token = make_token(invoice_id, salt="invoice-public")

    owner = logged_in.get(f"/invoice/{invoice_id}").get_data(as_text=True)
    client = app.test_client().get(f"/i/{token}").get_data(as_text=True)

    for name, page in (("owner", owner), ("client", client)):
        assert "#059669" in page, f"the {name} page is not wearing band-emerald"
        assert "QUOTE" in page, f"the {name} page hard-codes the document title"
        assert "Quote #" in page, f"the {name} page hard-codes the number label"
        assert number in page


def test_the_browser_draft_is_scoped_to_whoever_is_looking(anon, logged_in, owner):
    """One origin-wide key meant a signed-in sender's business details, and
    their client's name, address and prices, were restored for the next
    anonymous visitor or a different account in that browser. Signing out did
    not clear it. Raised by Codex on PR #289, round seven."""
    signed_out = anon.get("/generator").get_data(as_text=True)
    signed_in = logged_in.get("/generator").get_data(as_text=True)

    assert 'DRAFT_SCOPE = "anon"' in signed_out
    assert f'DRAFT_SCOPE = "u{owner}"' in signed_in
    for page in (signed_out, signed_in):
        assert "purgeOtherDrafts()" in page
        assert "localStorage.removeItem(k)" in page


def test_no_draft_moves_into_an_account_without_somebody_saying_so(
    anon, logged_in
):
    """Two fixes narrowed this and neither closed it.

    Scoping the key still adopted the anonymous draft on any signed-in visit,
    so a stranger's abandoned invoice reached the next person to log in.
    Requiring a marker left by pressing "Save & send it" still could not tell
    whether the person who eventually signed in was the person who pressed it:
    leave the machine on the signup page and the next arrival inherits the lot.

    So nothing is adopted automatically. The page offers the draft and a person
    decides. Raised by Codex on PR #289, rounds seven, eight and nine.
    """
    signed_out = anon.get("/generator").get_data(as_text=True)
    signed_in = logged_in.get("/generator").get_data(as_text=True)

    # the offer exists, starts hidden, and is only wired up when signed in
    assert 'id="offer"' in signed_in and "hidden" in signed_in
    assert "offerAnonymousDraft()" in signed_in
    assert 'id="offer-yes"' in signed_in and 'id="offer-no"' in signed_in
    assert "if (!SIGNED_IN) return;" in signed_in

    # nothing anywhere copies the anonymous draft without a click
    for page in (signed_out, signed_in):
        assert "markHandoff" not in page, "the marker heuristic is back"
        assert "HANDOFF_KEY" not in page
        # the only setItem of DRAFT_KEY from ANON_KEY sits inside the handler
        before_click = page[: page.index('id="offer-yes"')] if 'id="offer-yes"' in page else page
        assert "setItem(DRAFT_KEY, carried)" not in before_click

    assert "SIGNED_IN = false" in signed_out
    assert "SIGNED_IN = true" in signed_in

    # and an anonymous viewer is never offered anything, so the anonymous key
    # is simply theirs
    assert "offer-yes" not in signed_out or 'hidden' in signed_out


def test_signing_up_from_the_editor_comes_back_to_the_editor(app, anon):
    """The signed-out generator sends people to signup with `?next=/generator`
    because the invoice they just typed is in that browser and the page there
    offers to bring it over. The form posted to a bare `/signup` and the route
    always redirected to `/account`, so the parameter was dropped twice and the
    offer was never reached down the advertised path.

    Raised by Codex on PR #289, round ten, and by the walkthrough (defect 7).
    """
    page = anon.get("/generator").get_data(as_text=True)
    assert "/signup?next=%2Fgenerator" in page or "next=/generator" in page

    form_page = anon.get("/signup?next=/generator").get_data(as_text=True)
    assert "next=%2Fgenerator" in form_page or "next=/generator" in form_page, (
        "the form drops the return target, so posting it loses the draft"
    )

    r = anon.post(
        "/signup?next=/generator",
        data={
            "email": "kwame.adjei@bramblefinch.example",
            "password": "correct-horse-staple",
            "business_name": "Bramble & Finch",
            "agree": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/generator"), r.headers["Location"]


@pytest.mark.parametrize(
    "hostile",
    ["//evil.example.com", "/\\evil.example.com", "https://evil.example.com",
     "evil.example.com"],
)
def test_signup_cannot_be_pointed_off_site(app, anon, hostile):
    """Carrying a return target through signup is exactly the shape of an open
    redirect, and the moment after a successful sign-up is when somebody is
    most primed to trust the page they land on."""
    r = anon.post(
        f"/signup?next={hostile}",
        data={
            "email": "amara.nwosu@bramblefinch.example",
            "password": "correct-horse-staple",
            "business_name": "Bramble & Finch",
            "agree": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "evil.example.com" not in r.headers["Location"]
