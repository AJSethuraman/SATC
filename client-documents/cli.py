"""satc-docs — turn a client record into the documents a client receives.

The entry point the rest of this folder was missing.

    interview   run the consultation call; it creates the engagement
    engagements list what exists
    doctor      what is still blocking a real render, and who has to answer it
    from-lead   a website intake payload -> answers to prefill the interview
    render      a record, or an engagement ref -> client-ready HTML and PDF
    demo        the whole chain end to end, from a fixture, in one command

Two modes, and the difference matters:

    real  (default)  refuses to produce anything holed. An unresolved field or a
                     surviving [CONFIRM] raises, and nothing is written.
    draft (--draft)  renders anyway so the pipeline can be exercised before the
                     firm's decisions are made -- but stamps every page DRAFT,
                     marks every open decision in oxblood, and puts "DRAFT" in
                     the filename. A draft is never mistakable for the real one.

Run `python cli.py --help` from `client-documents/`.
"""

from __future__ import annotations

import argparse
import html
import datetime as _dt
import json
import os
import re
import shutil
import tempfile
import sys
import textwrap
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

import console
import dates
import money as m
import engagements
import invoicing
import lifecycle
import packaging
import payments
import notes
import outgoing
import presend
import sending
import procedures
import fees
import intake
import interview as iv
import closeout
import consistency
import merge
import pricing
import requote
import signing
import settings as firm
import timelog
import tins

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT.parent / "satc-handoff" / "04-TEMPLATES"
SAMPLES = ROOT / "samples"

# Registry name -> (template file, human name for the output file). The keys
# match registry/fields.yaml and tests/test_registry.py, so a template renamed
# in one place fails in all of them rather than dropping out silently.
DOCUMENTS = {
    "tax-letter":           ("SATC Engagement Letter - Tax Preparation.html", "Engagement Letter"),
    "business-letter":      ("SATC Engagement Letter - Business Return.html", "Business Engagement Letter"),
    "bookkeeping-letter":   ("SATC Engagement Letter - Bookkeeping.html",     "Bookkeeping Engagement Letter"),
    "fee-estimate":         ("SATC Fee Estimate.html",                        "Fee Estimate"),
    "invoice":              ("SATC Invoice.html",                             "Invoice"),
    "onboarding-letter":    ("SATC Onboarding Letter.html",                   "Onboarding Letter"),
    "organizer-letter":     ("SATC Organizer Cover Letter.html",              "Organizer Cover Letter"),
    "delivery-letter":      ("SATC Tax Return Delivery Letter.html",          "Return Delivery"),
    "extension-notice":     ("SATC Extension Notice.html",                    "Extension Notice"),
    "disengagement-letter": ("SATC Disengagement Letter.html",                "Disengagement"),
    "ccorp-letter":         ("SATC Engagement Letter - C Corporation.html",  "C Corporation Engagement Letter"),
    "records-release":      ("SATC Records Release Authorization.html",     "Records Release"),
}

def opening_package(record: dict) -> list[str]:
    """The documents this engagement's opening package actually contains.

    ONE LIST, AND IT LIVES IN `packaging`. This used to be its own hard-coded
    `["tax-letter", "fee-estimate", "onboarding-letter"]` plus the conditional
    records release, sitting beside `packaging.PACKS`, which keys the letter on
    `_return_type`. The two disagreed in both directions and each was right
    about the half the other got wrong:

    * `render --engagement` on an S corporation reached for the INDIVIDUAL
      engagement letter, which then refused on `TaxpayerName` -- so the
      business letter its own pack would have sent was never rendered at all.
    * `package` never carried the records release, so a client with a
      predecessor got a pack whose onboarding letter says "We have included a
      short authorization for you to sign" and did not include one.

    Both found on 26 August 2026 by running an entity engagement end to end.
    """
    return packaging.documents_for(record)

# When in an engagement's life a document becomes due. Readiness is only
# meaningful against a stage: a disengagement letter that cannot render at
# engagement creation is not blocked, it is not due, and reporting the two the
# same way buries the one that matters.
STAGE = {
    "tax-letter": "opening", "business-letter": "opening",
    "ccorp-letter": "opening",
    "bookkeeping-letter": "opening", "fee-estimate": "opening",
    "onboarding-letter": "opening", "organizer-letter": "opening",
    "extension-notice": "in flight",
    "delivery-letter": "delivery", "invoice": "delivery",
    "disengagement-letter": "ending",
    # Travels WITH the engagement letter, to any client who had a
    # previous accountant. Opening-stage for that reason.
    "records-release": "opening",
}

# Which opening document an engagement actually uses, by return type. The rest
# belong to a different engagement and are not this one's business.
OPENING_BY_RETURN = {
    "individual": "tax-letter", "s_corp": "business-letter",
    "partnership": "business-letter", "c_corp": "ccorp-letter",
}


# ── PDF backends ───────────────────────────────────────────────────────────
# The templates are flexbox: .mast, .lock, .sec>h2 and .led all rely on it, and
# they were designed and proofed in a browser. WeasyPrint's flex support is
# partial -- it drops `gap` and mis-stacks the wordmark, so the SAT-C lockup
# renders as overlapping letters and clause numerals collide with their
# headings. The document is CORRECT either way; it just does not look like the
# brand. So a headless browser is the primary engine and WeasyPrint the
# fallback, which is the same choice invoice-generator/pdf.py made for the same
# reason in reverse.

class NoPdfEngine(RuntimeError):
    pass


def _pdf_chromium(html: str, out: Path, base: Path, draft: bool = False) -> None:
    from playwright.sync_api import sync_playwright
    import tempfile
    # A file on disk rather than set_content, so relative links resolve exactly
    # as they do when the template is opened.
    #
    # IN A SCRATCH DIRECTORY, NOT IN `base`. Until 26 August 2026 this wrote
    # straight into 04-TEMPLATES, which meant a RENDERED CLIENT DOCUMENT --
    # real name, real address -- sat in the tracked template library for the
    # length of every render. That is the exact condition
    # `test_the_template_directory_holds_only_templates` exists to catch, and
    # it caught it: the test flaked whenever it ran beside a PDF render. A
    # guard tripping over the thing it guards against is the guard working.
    #
    # The two assets every template links are copied in beside it, so the
    # render is byte-identical to the old one.
    scratch = Path(tempfile.mkdtemp(prefix="satc-render-"))
    for asset in ("satc-doc.css", "doc-page.js"):
        src = base / asset
        if src.exists():
            (scratch / asset).write_bytes(src.read_bytes())
    tmp = scratch / "render.html"
    tmp.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**presend.launch_args())
            page = browser.new_page()
            page.goto(tmp.as_uri(), wait_until="networkidle")
            page.wait_for_timeout(700)          # doc-page.js defines the layout
            # Margins stay zero and the draft stamp is NOT done here.
            # doc-page.js injects `@page { margin: 0 }` at print, and Chromium
            # honours the stylesheet over the API -- so header_template and the
            # margin option are both silently ignored. The stamp goes in the
            # component's own `slot="header"`, which is documented to repeat on
            # every printed page. See _stamp_draft.
            page.pdf(path=str(out), format="Letter", print_background=True,
                     margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
            browser.close()
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)


def _pdf_weasyprint(html: str, out: Path, base: Path, draft: bool = False) -> None:
    from weasyprint import HTML as WeasyHTML
    WeasyHTML(string=html, base_url=str(base)).write_pdf(str(out))


PDF_ENGINES = [("chromium", _pdf_chromium), ("weasyprint", _pdf_weasyprint)]


def pdf_engine():
    """(name, fn) for the best available engine, or raise NoPdfEngine."""
    import importlib
    for name, fn in PDF_ENGINES:
        mod = "playwright.sync_api" if name == "chromium" else "weasyprint"
        try:
            importlib.import_module(mod)
            return name, fn
        except Exception:
            continue
    raise NoPdfEngine(
        "no PDF engine. `pip install playwright && playwright install chromium` "
        "for full brand fidelity, or `pip install weasyprint` for a usable "
        "fallback that renders the wordmark and clause numerals imperfectly."
    )


# ── the draft stamp ────────────────────────────────────────────────────────

_DRAFT_CSS = """
<style id="satc-draft-stamp">
  /* Injected by cli.py --draft. Never present on a real render. */
  .satc-draft-banner{
    background:#6A2833; color:#fff; text-align:center;
    font-family:"IBM Plex Mono","Courier New",monospace;
    font-size:9pt; letter-spacing:.18em; text-transform:uppercase;
    padding:6pt 8pt;
  }
  .satc-open-decision{
    background:rgba(106,40,51,.12); border-bottom:1pt solid #6A2833;
    color:#6A2833; font-family:"IBM Plex Mono","Courier New",monospace;
    font-size:.9em; padding:0 .2em;
  }
  @media print{
    /* Page 2 onward is handled by the PDF engine's repeating header, not here:
       Chromium ignores `@page { @top-center { content } }`, so a CSS-only stamp
       marks page one and leaves the rest looking exactly like the real
       document -- the one way a draft could be mistaken for sendable. */
  }
</style>
"""

_BANNER = ('<div slot="header" class="satc-draft-banner">Draft &middot; not for '
           'client use &middot; open decisions marked in oxblood</div>')

# WHAT A PREVIEW SAYS ABOUT ITSELF. A preview is served into a browser, and a
# browser can print it, save it, and attach it to an email. Nothing here can
# stop that, so the only honest defence is that the sheet which comes out of
# the printer says what it is -- on every page, for the same reason the draft
# stamp does.
_PREVIEW_BANNER = ('<div slot="header" class="satc-draft-banner">Preview '
                   '&middot; not the copy that goes to the client</div>')


def _stamp_draft(html: str, banner: str = _BANNER) -> str:
    """Make a draft impossible to mistake for the real document.

    The banner goes in doc-page's `slot="header"`, which the component prints
    inside a repeating <thead> spacer -- so it lands on EVERY page, not just
    the first. That matters: page two of an unstamped draft is byte-identical
    to page two of the real letter, and page two is what gets handed across a
    desk on its own.
    """
    html = html.replace("</head>", _DRAFT_CSS + "</head>", 1)
    # after the opening <doc-page ...> tag, so the component owns it
    html = re.sub(r"(<doc-page\b[^>]*>)", r"\1\n" + banner, html, count=1)
    # highlight every decision nobody has made yet
    return re.sub(r"(\[CONFIRM:[^\]]*\])",
                  r'<span class="satc-open-decision">\1</span>', html)


def stamp_preview(html: str, labels: dict | None = None) -> str:
    """The same stamp, saying the other thing, with the blanks named.

    Public because `previewing` is a second caller and the stamp is the whole
    reason looking at a document is safe to allow past the gate.

    AND THE BLANKS READ AS BLANKS. A preview of an unfinished document leaves
    the token where the answer will go, and the token is spelled the way the
    template spells it -- `<<PaymentDeadline>>`, in the middle of a letter, at
    a preparer who is looking at a document and not at software. Marked the
    same way an undecided sentence is marked, and named the way the rest of
    the software names it.
    """
    html = _stamp_draft(html, _PREVIEW_BANNER)

    def blank(m):
        name = m.group(1)
        said = (labels or {}).get(name) or name
        return (f'<span class="satc-open-decision">{said} '
                f'&mdash; not answered yet</span>')

    return re.sub(r"&lt;&lt;([A-Za-z0-9_]+)&gt;&gt;", blank, html)


# ── record assembly ────────────────────────────────────────────────────────

def build_record(record: dict) -> dict:
    """Fold the firm's settings in under the record's own values.

    The record wins where it sets something -- a per-engagement override of a
    firm default is legitimate, and silently ignoring it would be worse than
    letting it through.
    """
    season = str(record.get("_season") or "").strip()
    if not season:
        raise SystemExit(
            "record has no `_season` (the tax year being filed, e.g. \"2026\"). "
            "It selects the materials deadline; guessing it would print the "
            "wrong date on three documents."
        )
    fields = firm.firm_fields(season, record.get("_return_type", "individual"))
    out = {k: v for k, v in fields.items() if v is not None}
    out.update(record)
    # AN ENGAGEMENT PRICED BEFORE THE ESTIMATE HAD ITS OWN DATE. `EstimateDate`
    # arrived with the re-quote -- until then the estimate was dated to the
    # letter, and every record already on disk carries only `LetterDate`.
    # Backfilled here rather than migrating the store: the value is the same on
    # an engagement nobody has re-quoted, and a render that refused on a
    # record written last week would be this change breaking real work.
    if not out.get("EstimateDate") and out.get("LetterDate"):
        out["EstimateDate"] = out["LetterDate"]
    # `_`-prefixed keys are metadata, not merge fields: the season and return
    # type that chose the deadline, and the website's unsharpened claims. They
    # ride along because the filename needs the season, and merge.render only
    # looks up names the TEMPLATE asks for, so they cannot reach a document.
    return out


def _slug(record: dict) -> str:
    """Surname-ish handle for the filename. A client keeps these for years."""
    name = (record.get("ClientFullName") or "client").strip()
    name = re.sub(r"^(Mr\.|Mrs\.|Ms\.|Mx\.|Dr\.)\s+", "", name)
    name = re.split(r"\s+and\s+|\s*&\s*", name)[0]
    return (name.split()[-1] if name.split() else "client").strip(",.")


def output_name(doc: str, record: dict, draft: bool) -> str:
    """`SAT-C Engagement Letter - Reyes - 2026`, per the field docs."""
    _, label = DOCUMENTS[doc]
    parts = ["SAT-C", label, "-", _slug(record), "-", str(record.get("_season", ""))]
    stem = " ".join(p for p in parts if p).replace(" - -", " -")
    return stem + (" - DRAFT" if draft else "")


# ── commands ───────────────────────────────────────────────────────────────

def _engagement_readiness(ref: str, store: Path) -> int:
    """What one engagement still needs, per document.

    The firm-wide report says what blocks everybody. This says what blocks
    *this* client, which is the question you actually have with a record open.
    """
    record = build_record(engagements.load(ref, store))
    print(f"Engagement {ref} - {record.get('ClientFullName', '(no name)')}\n")

    letter = OPENING_BY_RETURN.get(record.get("_return_type", "individual"))
    # A DOCUMENT THIS CLIENT WILL NEVER BE SENT CANNOT BE BLOCKING THEM.
    # The records release goes only to a client who had a previous accountant
    # -- `opening_package` has always known that and this report did not, so
    # every engagement with no predecessor was told, in red, that a document
    # it is never going to send is "Blocked, and due now", and `doctor`
    # exited 1 on a perfectly healthy engagement. A readiness tool that
    # overstates what is broken teaches whoever reads it to stop believing
    # the parts that are true -- the same argument that put `hard_no` in
    # settings.POLICY_ONLY.
    relevant = [d for d in DOCUMENTS
                if STAGE[d] != "opening" or d == letter
                or d in ("fee-estimate", "onboarding-letter", "organizer-letter")
                or (d == "records-release" and record.get("PriorFirm"))]

    ready, blocked = [], {}
    for doc in relevant:
        template = (TEMPLATE_DIR / DOCUMENTS[doc][0]).read_text(encoding="utf-8")
        try:
            # THE SAME CALL `render` MAKES, required lists and all. It used to
            # omit them, so `doctor` reported the organizer letter "Ready now"
            # while `render` refused it -- two halves of one tool disagreeing
            # about the same document, which is worse than either answer.
            merge.render(template, record,
                         required_lists=_required_lists().get(doc, ()))
            ready.append(doc)
        except merge.MergeError as exc:
            blocked[doc] = html.unescape(str(exc))

    opening_blocked = {d: w for d, w in blocked.items() if STAGE[d] == "opening"}
    later_blocked = {d: w for d, w in blocked.items() if STAGE[d] != "opening"}

    if ready:
        print("  Ready now:")
        for doc in ready:
            print(f"    {doc}")

    if opening_blocked:
        print(f"\n  Blocked, and due now ({len(opening_blocked)}):")
        for doc, why in opening_blocked.items():
            print(f"    {doc}")
            for part in why.split("; "):
                print(f"        {part}")

    if later_blocked:
        print(f"\n  Not due yet - these need facts that do not exist at "
              f"engagement creation:")
        for doc, why in later_blocked.items():
            fields = ""
            for part in why.split("; "):
                if part.startswith("unresolved fields:"):
                    fields = part.split(":", 1)[1].strip()
            print(f"    {doc:22s} ({STAGE[doc]})"
                  + (f"  awaiting {fields}" if fields else ""))

    print("\n  A [CONFIRM] is a firm decision -- `doctor` with no argument "
          "lists them all.\n  An unresolved field is missing from this record.")
    return 1 if opening_blocked else 0


def _previous_pack(outdir: Path) -> str | None:
    """Moved to `sending`, where the code that acts on it lives."""
    return sending.previous_pack(outdir)


def cmd_package(args) -> int:
    """The terminal's door onto `sending.build` -- reporting, not deciding.

    Every rule this command used to enforce lives in `sending` now, so the
    browser enforces the same ones by calling the same function. What is left
    here is what a terminal is for: reading the arguments, and saying in words
    what was decided.
    """
    store = Path(args.store) if args.store else engagements.STORE
    try:
        raw = engagements.load(args.engagement, store)
    except engagements.EngagementError as exc:
        print(exc)
        return 1
    record = build_record(raw)

    try:
        docs = packaging.documents_for(record, with_invoice=args.with_invoice)
        # Asked here, before anything renders. The same question `manifest`
        # asks -- the same function, so the two cannot come to differ -- but a
        # typo in --attach is worth catching in a second rather than after
        # three merges and three browser renders.
        packaging.check_attachments(getattr(args, "attach", None))
    except packaging.PackageError as exc:
        print(f"\n{exc}\n")
        return 1

    want_pdf = not args.no_pdf
    if want_pdf:
        try:
            pdf_engine()
        except NoPdfEngine as exc:
            print(f"note: {exc}\n      writing HTML only\n", file=sys.stderr)
            want_pdf = False

    outdir = Path(args.out)
    pack = sending.build(
        record, outdir, render=render_one,
        ref=record.get("EngagementRef") or args.engagement, store=store,
        template_dir=TEMPLATE_DIR, documents=docs, want_pdf=want_pdf,
        attach=getattr(args, "attach", None),
        skip_render=getattr(args, "skip_render", False),
        readings=bool(getattr(args, "notes", False)),
        force=bool(getattr(args, "force", False)),
        reason=getattr(args, "reason", "") or "")

    if pack.status == "not-ours":
        print(f"\n{outdir} already has files in it and no MANIFEST.json, so it "
              f"is not a pack this\ncommand wrote. Refusing to mix a signing "
              f"pack into somebody else's folder —\ngive --out a new directory.\n")
        return 1

    if pack.status == "refused-merge":
        print(f"\nNo pack written. {len(pack.refused)} of {len(docs)} "
              f"document(s) refused, and a pack with a hole in it is worse "
              f"than none —\nthe client signs what arrived and the rest turns "
              f"up later saying something different.\n")
        for doc, why in pack.refused:
            print(f"  {DOCUMENTS[doc][1]}")
            for line in textwrap.wrap(why, 74):
                print(f"      {line}")
            print()
        if pack.stale:
            print(f"  WARNING: {outdir} still holds the pack written for "
                  f"{pack.stale}.\n           It is not this engagement's and "
                  f"it has not been updated. Do not send it.\n")
        return 1

    check = pack.check
    print(f"\nBefore sending — {len(check.checked)} check(s):")
    print(presend.format_result(check))
    if getattr(args, "notes", False):
        print(f"\nReadings — {len(pack.readings)} advisory check(s), none of "
              f"which can stop a pack:")
        print(notes.format_notes(pack.readings))

    if pack.status == "refused-gate":
        print(f"\nNo pack written. {len(check.blocking)} check(s) failed, "
              f"and a pack that does not\nsurvive being opened is not a "
              f"pack — it is a folder the client cannot read.\n"
              f"\n  Fix it, or send anyway with --force and a reason:\n"
              f"      --force --reason \"why this is going out as it is\"\n")
        return 1

    if pack.status == "no-reason":
        print("\n--force needs --reason. An override with no recorded "
              "reason is just a\nquieter way to send a pack that did "
              "not pass.\n")
        return 1

    if pack.status == "not-logged":
        print(f"\nCould not record the override ({pack.detail}), so the pack "
              f"was not written.\nThe log is the only thing that makes "
              f"--force different from no gate at all.\n")
        return 1

    if pack.override:
        print(f"\n  Override recorded — {pack.override}")

    print(f"\nSigning pack for {record.get('EngagementRef') or args.engagement}"
          f" — {record.get('ClientFullName', '')}")
    print(f"    {outdir}\n")
    for doc in docs:
        print(f"  {DOCUMENTS[doc][1]}")
        print(f"      {packaging.PURPOSE.get(doc, '')}")
    print(f"\n  Estimate  {record.get('EstimateTotal', '(none)')}")
    print(f"  Manifest  {outdir / 'MANIFEST.json'}")

    # ONE PRESS FROM SENT. The pack is four files in a folder and a covering
    # note somebody types from memory; this writes it as an ordinary `.eml`
    # that opens in the mail client already addressed, attached and written.
    # Nothing is sent -- the human reads it and presses send, which keeps the
    # one irreversible step in the pipeline attached to a person.
    if getattr(args, "ready", False):
        try:
            message = outgoing.compose(record, outdir,
                                       registry=signing._registry())
            path = outgoing.write(message, outdir,
                                  sender=firm.firm_fields(
                                      str(record.get("_season", "")))
                                  .get("BillingContactEmail", ""))
        except outgoing.OutgoingError as exc:
            # PRINTED LINE BY LINE, NOT REFLOWED. The refusal quotes the
            # draft covering note back, and running a proposed letter through
            # a paragraph filler turns it into a wall the reader skips.
            print("\n  Not ready to send.")
            for line in str(exc).splitlines():
                print("  " + line if line.strip() else "")
            print()
            return 0
        print(f"\n  Ready to send  {path}")
        print(f"      {message.summary()}")
        print(f"      Open it, read it, press send. Nothing has gone "
              f"anywhere.\n")
    return 0


def cmd_invoice(args) -> int:
    """A priced engagement -> an invoice, and optionally the rendered document.

    The bridge the firm asked for. Everything the invoice says about money is
    read off the estimate that was already agreed, so the two cannot disagree.
    """
    store = Path(args.store) if args.store else engagements.STORE
    try:
        record = engagements.load(args.engagement, store)
    except engagements.EngagementError as exc:
        print(exc)
        return 1

    number = args.number or invoicing.next_number(store)
    credits = []
    if args.credit:
        for entry in args.credit:
            label, _, amount = entry.rpartition("=")
            try:
                credits.append({"label": label or "Credit", "detail": "",
                                "amount": float(amount)})
            except ValueError:
                print(f"--credit wants LABEL=AMOUNT, got {entry!r}")
                return 1

    # MONEY THIS CLIENT HAS ALREADY OVERPAID. Refunding it costs the firm the
    # processing fee -- Square keeps that on refunds -- so it belongs on the
    # next bill. Which is this one, and nobody should have to remember.
    over = payments.unapplied_overpayments(store, args.engagement)
    taken = [o for o in over
             if any(o["invoice"] in c["label"] for c in credits)]
    for o in [o for o in over if o not in taken]:
        print(f"\n  {args.engagement} overpaid invoice {o['invoice']} by "
              f"${o['cents'] / 100:,.2f}, and it has not been given back.\n"
              f"  Put it on this bill instead of refunding it — Square keeps "
              f"the processing\n  fee on a refund, so sending it back costs "
              f"the fee on money nobody asked for:\n\n"
              f"    --credit 'Overpayment on invoice {o['invoice']}"
              f"={o['cents'] / 100:.2f}'\n\n"
              f"  Naming the invoice in the label is what stops this saying it "
              f"again.\n")

    try:
        fields = invoicing.build(record, number=number, billed=args.billed,
                                 credits=credits,
                                 variance_note=args.variance_note or "")
    except invoicing.InvoiceError as exc:
        print(f"\n{exc}\n")
        return 1

    # AFTER the bill is built, never before: a credit that was refused is not
    # a credit that was given, and marking it applied would lose the money.
    for o in taken:
        payments.apply_overpayment(store, args.engagement,
                                   invoice=o["invoice"], applied_to=number)

    # THE LINK IS MADE BEFORE THE BILL IS WRITTEN, so a processor that refuses
    # leaves no invoice claiming a link it never got. The bill is the thing the
    # client reads; a half-made one is worse than none.
    note = ""
    # THE LINK FOLLOWS THE STORE. A run scoped to a scratch directory used to
    # reach production Square anyway, because --store routed only the files.
    try:
        choice = payments.link_follows_the_store(
            store=store, default_store=engagements.STORE,
            no_link=args.no_link, link=args.link)
    except payments.PaymentError as exc:
        print(f"\n{exc}\n")
        return 1
    if not choice.wanted:
        # SAID OUT LOUD, never silently. A suppressed link that nobody
        # mentioned is somebody re-running the command wondering where it went.
        note = "    " + textwrap.fill(choice.reason, 66,
                                      subsequent_indent="                ")
    else:
        try:
            link = payments.link_for(
                fields, using=payments.processor(sandbox=args.sandbox))
            fields.update(link.as_record())
            note = f"    Pay online  {link.url}"
        except payments.PaymentError as exc:
            # NOT FATAL, AND SAID OUT LOUD. An invoice with no link is the
            # invoice this firm sent all year; one that silently lost its link
            # is a client told to click something that is not there.
            note = ("    No link on this bill — "
                    + textwrap.fill(str(exc), 66,
                                    subsequent_indent="                ").strip())

    path = store / args.engagement / "invoices"
    path.mkdir(parents=True, exist_ok=True)
    out = path / f"{number}.json"
    out.write_text(json.dumps(fields, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"\nInvoice {number} for engagement {args.engagement}")
    print(f"    {out}")
    print(f"\n    Subtotal    {fields['Subtotal']}")
    if fields.get("CreditAmount"):
        print(f"    Credits     {fields['CreditAmount']}")
    print(f"    Amount due  {fields['AmountDue']}")
    if fields.get("EstimateTotal"):
        print(f"    Estimated   {fields['EstimateTotal']}"
              + ("   (this bill differs — the note says why)"
                 if fields.get("VarianceNote") else ""))
    if note:
        print(f"\n{note}")
    print(f"\nNext:  python cli.py render --engagement {args.engagement} "
          f"--docs invoice --out out")
    return 0


def _one_account(sandbox: bool, *, reg, env, offer_to_remember: bool) -> bool:
    """Set up one Square account. True if the location id ended up written."""
    import getpass
    import square_setup as setup

    which = "sandbox_location_id" if sandbox else "location_id"
    label = "TEST" if sandbox else "LIVE"

    print("-" * 68)
    print(f"  {label} account")
    print("-" * 68)

    token = os.environ.get(env, "").strip() or setup.stored_token(sandbox)
    if token:
        print("  Already have this token. Not asking again.\n")
    else:
        print(f"  Paste the {label} ACCESS TOKEN (not an id — this finds the id "
              f"for you).")
        print("  Square dashboard -> Developer -> your app -> Credentials, "
              f"{label} tab.")
        print("  Nothing appears as you paste. Press Enter on its own to skip.\n")
        try:
            token = getpass.getpass("  Token: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Skipped.\n")
            return False
        if not token:
            print("\n  Skipped — no token given.\n")
            return False

    try:
        api = payments.processor(
            sandbox=sandbox,
            reg={**reg, "square": {**(reg.get("square") or {}), which: "unknown"}},
            token=token)
        found = api.locations()
    except payments.PaymentError as exc:
        print(f"\n  Square would not answer: {exc}")
        print(f"  Nothing written for the {label} account. The usual cause is "
              f"the other\n  account's token — they cannot see each other.\n")
        return False

    if not found:
        print(f"\n  This token can see no locations. Nothing written.\n")
        return False

    if len(found) == 1:
        chosen = found[0]
        print(f"  One location: {chosen.get('name') or '(unnamed)'}\n")
    else:
        for n, loc in enumerate(found, 1):
            print(f"    {n}.  {loc.get('name') or '(unnamed)'}      {loc.get('id')}")
        print()
        try:
            raw = input(f"  Which one holds the firm's money? [1-{len(found)}] ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Skipped.\n")
            return False
        if not raw.isdigit() or not 1 <= int(raw) <= len(found):
            print("\n  Not one of the numbers offered. Nothing written.\n")
            return False
        chosen = found[int(raw) - 1]

    try:
        setup.save_location(which, str(chosen.get("id", "")))
    except setup.SetupError as exc:
        print(f"\n  Not written: {exc}\n")
        return False
    print(f"  Written:  {which} = {chosen.get('id')}")

    if offer_to_remember and not setup.stored_token(sandbox):
        try:
            keep = setup.remember_token(token, sandbox=sandbox)
            print(f"  Remembered, sealed to this Windows account: {keep.name}")
        except setup.SetupError as exc:
            print(f"  Token not stored: {exc}")
    print()
    return True


def _payments_setup(args) -> int:
    """Both Square accounts, both location ids, both tokens — in one run.

    THE FIRM, 4 September 2026: *"i dont want to have to do this in multiple
    places or keep track of multiple things."*

    So there are no flags to choose between and no second command to remember.
    It asks for the test token and the live token, finds each account's
    locations itself, writes both ids, and seals both tokens so nothing has to
    be typed again. Either half can be skipped with Enter and filled in later
    by running it again -- what is already there is never asked for twice.
    """
    import square_setup as setup

    reg = payments.settings()
    env = ((reg.get("square") or {}).get("token_env")) or "SATC_SQUARE_TOKEN"

    print("\n  Setting up Square. Two accounts, asked for once each.\n")
    ok_test = _one_account(True, reg=reg, env=env,
                           offer_to_remember=not args.no_remember)
    reg = payments.settings()          # re-read: the first half wrote to it
    ok_live = _one_account(False, reg=reg, env=env,
                           offer_to_remember=not args.no_remember)

    print("=" * 68)
    print(f"  TEST account   {'ready' if ok_test else 'not set up'}")
    print(f"  LIVE account   {'ready' if ok_live else 'not set up'}")
    print("=" * 68)
    if ok_test:
        print("\n  Proving the test account end to end now.\n")
        return _payments_check(_Args(production=False, cents=100))
    print("\n  Run this again when you have a token for the missing one.\n")
    return 0 if (ok_test or ok_live) else 1


class _Args:
    """The two fields `_payments_check` reads, so setup can call it directly."""
    def __init__(self, *, production: bool, cents: int):
        self.production, self.cents = production, cents


def _payments_check(args) -> int:
    """Prove the payment path works, against the live processor, end to end.

    THE QUESTION THIS ANSWERS, from the firm on 2 September 2026: *"how do we
    truly confirm the square thing works - i want to know i'll get paid and the
    client isn't just sending money to the void"*.

    Every automated test runs against a stand-in for the network. They prove
    this software behaves correctly; they cannot tell a working Square account
    from a closed one. This asks Square.
    """
    sandbox = not args.production
    if args.production:
        # A REAL LINK TAKES REAL MONEY. It is the only thing that proves the
        # production location is the firm's own and the payout reaches the
        # bank -- so it is offered, and it is never the default.
        print("\nThis will create a REAL payment link on the live account for "
              f"${args.cents / 100:,.2f}.\nPaying it moves real money onto a "
              "real statement.\n")

    steps, link, got = payments.live_check(sandbox=sandbox, amount_cents=args.cents)

    where = "Square's test account" if sandbox else "the LIVE Square account"
    print(f"\nChecking the payment path against {where}.\n")
    for step in steps:
        print(f"  {'yes' if step.ok else 'NO ':4} {step.name}")
        if step.detail:
            print(f"       {step.detail}")
    done = sum(1 for s in steps if s.ok)
    print(f"\n  {done} of {payments.CHECK_STEPS} checked.\n")

    if len(steps) < payments.CHECK_STEPS:
        print("It stopped at the first thing that failed, so the steps after "
              "it\nwere not reached — not passed.\n")
        return 1

    if got is not None and got.paid:
        print("The whole loop is proven: a link was made, somebody paid it, "
              "and\nthis software saw the money.\n")
        if sandbox:
            print("What this does NOT prove is the live account: that is a "
                  "different\nlocation id and a different token. Run "
                  "`--production` once, pay a\ndollar with your own card, and "
                  "watch it land in your bank.\n")
        return 0

    print(f"{payments.CHECK_STEPS - 1} of the {payments.CHECK_STEPS} are "
          f"proven. The last one needs a card, because no\nsoftware can pay "
          f"itself:\n")
    print(f"  1. Open   {link.url if link else ''}")
    if sandbox:
        # Square publishes the sandbox card numbers; they are printed here so
        # nobody has to go looking, and sourced so nobody has to trust this.
        print("  2. Pay it with a Square sandbox test card — no money moves.")
        print("     Square lists them at "
              "https://developer.squareup.com/docs/devtools/sandbox/payments")
        print("     (the Visa is 4111 1111 1111 1111, CVV 111, any future "
              "expiry,\n      postal 94103 — check the page if it is refused).")
    else:
        print("  2. Pay it with your own card. It is a real charge for "
              f"${args.cents / 100:,.2f};\n     refund it from the Square "
              "dashboard afterwards.")
    print("  3. Run this command again. It reuses the same link, so it will\n"
          "     find the payment and tell you the money arrived.\n")
    if not sandbox:
        print("Then check your bank. The transfer is Square's to make and this\n"
              "software cannot see it — that last step is yours, once.\n")
    return 0


def cmd_payments(args) -> int:
    """Ask the processor which bills have been paid, and write down the answer.

    POLLED, NOT PUSHED. A webhook would need a public server this firm does not
    have; this asks the question when somebody wants the answer, from a laptop,
    with nothing listening on the internet.

    ONLY A SETTLEMENT IS EVER RECORDED. An unpaid order is left alone rather
    than written down as unpaid -- a cached "no" goes stale the moment somebody
    pays, and a bill marked unpaid that has since been settled is the error that
    ends up in front of a client.
    """
    if getattr(args, "check", False):
        return _payments_check(args)
    if getattr(args, "setup", False):
        return _payments_setup(args)
    if getattr(args, "forget_token", False):
        import square_setup as setup
        gone = setup.forget_token()          # both slots
        if gone:
            print("\nForgotten: " + ", ".join(p.name for p in gone) + "\n")
        else:
            print("\nThere was no remembered token to forget.\n")
        return 0
    store = Path(args.store) if args.store else engagements.STORE
    waiting = payments.outstanding(store)
    if not waiting:
        print("\nNo bill is waiting on a payment.\n")
        return 0
    try:
        square = payments.processor(sandbox=args.sandbox)
        answers = square.settled([w["order_id"] for w in waiting])
    except payments.PaymentError as exc:
        print(f"\n{exc}\n")
        return 1

    moved = 0
    trouble = []
    print(f"\n{len(waiting)} bill(s) with a link out:\n")
    for row in waiting:
        got = answers.get(row["order_id"])
        posted = (payments.record_settlement(row["path"], got) if got
                  else payments.Posting())
        if posted.settled:
            moved += 1
        if posted.problem:
            trouble.append((row, posted))
        # SHORT IS NOT "waiting". Money arrived and did not cover the bill; a
        # line reading `waiting` would say nobody had paid, which is false and
        # is the reading somebody would act on.
        state = ("SHORT" if posted.short
                 else "PAID" if (got and got.paid) else "waiting")
        when = f"  {got.when}" if got and got.paid and got.when else ""
        print(f"  {state:8} {row['ref']}  invoice {row['invoice']:10} "
              f"{row['amount']:>10}{when}")
    print(f"\n{moved} newly settled.\n" if moved
          else "\nNothing new has settled.\n")
    for row, posted in trouble:
        print(f"  {row['ref']}  invoice {row['invoice']}:\n    "
              + posted.problem + "\n")
    return 0


def cmd_ladder(args) -> int:
    """Are the packages sensible against the prices?

    Asked for by the firm, 25 August 2026: "it is a good check, too, we should
    ensure that our tiers are sensical with our pricing altogether".

    The engine picks the cheapest package a client is eligible for, which
    means a pricing mistake no longer shows up as an overcharge -- it shows up
    as SILENCE. A package priced above what its own allowances are worth
    simply stops being selected and nothing complains. This is the report that
    listens for that.
    """
    rows = pricing.ladder_report(form=args.form)
    if not rows:
        print(f"base.{args.form} is not a ladder — nothing to report.")
        return 0

    print(f"How the {args.form} packages behave across a sweep of client shapes.\n")
    print(f"  {'Package':<22}{'Price':>8}{'Eligible':>10}{'Chosen':>8}   Beaten by")
    dead = []
    for r in rows:
        amount = r["amount"]
        price = m.money(amount, "USD") if isinstance(amount, (int, float)) else "open"
        beaten = ", ".join(f"{k} ×{n}" for k, n in
                           sorted(r["beaten_by"].items(), key=lambda kv: -kv[1]))
        print(f"  {r['label']:<22}{price:>8}{r['eligible']:>10}{r['chosen']:>8}   {beaten or '—'}")
        if r["eligible"] and not r["chosen"]:
            dead.append(r)
        elif not r["eligible"]:
            dead.append(r)

    print()
    for r in dead:
        if not r["eligible"]:
            print(f"  {r['label']}: NO CLIENT IS EVER ELIGIBLE. Its gate cannot "
                  f"hold — check it against what the interview actually asks.")
        else:
            who = ", ".join(sorted(r["beaten_by"]))
            print(f"  {r['label']}: ELIGIBLE BUT NEVER CHOSEN. Every client who "
                  f"qualifies for it\n      does better on {who}, so it is priced "
                  f"above what it covers.\n      Either the price is wrong or the "
                  f"allowances are too small.")
    if not dead:
        print("  Every package is reachable and is the best deal for somebody.")

    # ── is each step worth what it costs? ─────────────────────────────────
    print(f"\nWhat each rung adds, against its own price step.\n")
    odd = []
    for r in pricing.ladder_value(form=args.form):
        if r["step"] is None:
            print(f"  {r['label']:<22} {m.money(r['amount'], 'USD'):>8}   "
                  f"stands alone — no rung below it to compare against")
            continue
        parts = ", ".join(f"{n}x {k.replace('count_', '')} @ {m.money(p, 'USD')}"
                          for k, n, p in r["items"]) or "nothing priced"
        print(f"  {r['label']:<22} {m.money(r['amount'], 'USD'):>8}   "
              f"step {m.money(r['step'], 'USD')} for {parts}")
        if r["delta"] > 0:
            print(f"  {'':<22} {'':>8}   -> a {m.money(r['delta'], 'USD')} "
                  f"discount on buying the parts")
        elif r["delta"] < 0:
            odd.append(r)
            print(f"  {'':<22} {'':>8}   -> COSTS {m.money(-r['delta'], 'USD')} "
                  f"MORE than buying the parts")
        else:
            print(f"  {'':<22} {'':>8}   -> exactly break-even")
    if odd:
        print()
        for r in odd:
            print(f"  {r['label']}: a client who does the arithmetic is better "
                  f"off\n      without this package. Either the step is too "
                  f"steep or it does not\n      absorb enough to justify it.")
    return 1 if (dead or odd) else 0


def cmd_doctor(args) -> int:
    if args.engagement:
        store = Path(args.store) if args.store else engagements.STORE
        return _engagement_readiness(args.engagement, store)

    decisions = firm.open_decisions()
    unpriced = pricing.open_amounts()
    print("SAT-C document pipeline - readiness\n")

    missing = [n for n, (f, _) in DOCUMENTS.items() if not (TEMPLATE_DIR / f).exists()]
    print(f"  templates      {len(DOCUMENTS) - len(missing)}/{len(DOCUMENTS)} present"
          + (f"  MISSING: {', '.join(missing)}" if missing else ""))

    try:
        name, _ = pdf_engine()
        note = "" if name == "chromium" else "  (partial flexbox - wordmark and clause numerals render imperfectly)"
        print(f"  pdf engine     {name}{note}")
    except NoPdfEngine as exc:
        print(f"  pdf engine     none - HTML only\n                 {exc}")

    if unpriced:
        print(f"\n  {len(unpriced)} unpriced item(s) in the fee schedule. These "
              f"block the FEE ESTIMATE only;\n  every other document renders "
              f"without them. registry/fee-schedule.yaml.\n")
        for path, q in unpriced:
            print(f"    {path}\n        {q}\n")

    # Split by what an unanswered decision actually costs. `hard_no` was
    # being reported as blocking every real render while real packs rendered
    # perfectly well; a readiness tool that overstates what is broken teaches
    # whoever reads it to stop believing the parts that are true.
    blocking = [(p, q) for p, q in decisions if firm.blocks_render(p)]
    policy = [(p, q) for p, q in decisions if not firm.blocks_render(p)]

    if not decisions and not unpriced:
        print("\n  No open decisions. Real renders will produce documents.")
        return 0

    if blocking:
        print(f"\n  {len(blocking)} open decision(s) block every REAL render.")
        print("  Each is a question only a human can answer. Edit "
              "registry/firm-settings.yaml.\n")
        for path, q in blocking:
            print(f"    {path}\n        {q}\n")

    if policy:
        print(f"\n  {len(policy)} open decision(s) about how the firm WORKS. "
              f"Documents render\n  without these — they govern what work is "
              f"taken, not what a letter says.\n")
        for path, q in policy:
            print(f"    {path}\n        {q}\n")

    if not blocking and not unpriced:
        print("  Nothing blocks a real render.")
        return 0
    if blocking:
        print("  Until then, use --draft to exercise the pipeline end to end.")
    return 1
    return 1


def cmd_from_lead(args) -> int:
    """Website intake `_json` payload -> a record skeleton to finish by hand.

    Deliberately partial. The interview schema says every prefilled answer is
    still asked and sharpened: the website answer is a claim, not a fact. This
    carries the claims across so nobody retypes them, and marks everything the
    interview still owes.
    """
    lead = json.loads(Path(args.lead).read_text(encoding="utf-8"))
    contact = lead.get("contact") or {}

    city, state = "", ""
    loc = (contact.get("location") or "").split(",")
    if loc:
        city = loc[0].strip()
        if len(loc) > 1:
            state = loc[1].strip()

    todo = "[CONFIRM: ask in the interview]"
    record = {
        "_comment": (f"Built from a website lead by cli.py from-lead. Every "
                     f"{todo} is a question the interview must answer -- see "
                     f"registry/interview.yaml."),
        "_season": args.season,
        "_return_type": args.return_type,
        "LetterDate": dates.long_date(date.today()),
        "EngagementRef": args.ref or todo,
        "PeriodLabel": f"{args.season} tax year",
        # The lead gives us a name to greet somebody by; the letters want the
        # full legal name, because the salutation and the addressee block are
        # the same string now. A lead's "Dan" is not that, so this stays a
        # question for the interview.
        "ClientFullName": todo,
        "ClientEmail": contact.get("email") or todo,
        "ClientAddress1": todo,
        "ClientCity": city or todo,
        "ClientState": state or todo,
        "ClientZip": todo,
        "_website_claims": {k: v for k, v in lead.items() if k != "contact"},
    }
    out = Path(args.out)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    n = sum(1 for v in record.values() if v == todo)
    print(f"wrote {out}  ({n} answers still owed by the interview)")
    return 0


def _ask(section: dict, q: dict, default, said: str = "") -> object:
    """One question at a terminal. The only part of the interview that is I/O."""
    print(f"\n  {section['title']}  ·  {q['id']}")
    print(f"  {q['question']}")
    if q.get("help"):
        for line in str(q["help"]).strip().split("\n"):
            print(f"      {line.strip()}")

    options = q.get("options") or []
    for i, opt in enumerate(options, 1):
        mark = "  HARD NO" if opt.get("hard_no") else ""
        print(f"      {i}. {opt['label']}{mark}")

    hint = {"list": "comma-separated, blank for none",
            "multi": "numbers, comma-separated, blank for none",
            "single": "a number",
            "number": "a number",
            "textarea": "one line"}.get(q["type"], "")
    # A claim the question would reject is shown, but not acceptable with enter.
    has_default = iv.prefill_is_answerable(q, default)
    if default not in (None, "", []) and not has_default:
        print(f"      website said: {default!r} -- not a valid answer here, "
              f"so it needs a real one")
    if has_default:
        # Enter accepts it. The schema calls a prefilled answer a claim to
        # confirm rather than a fact, and pressing enter on a value you can see
        # IS confirming it -- retyping it character for character is not a
        # stronger confirmation, it is just friction, and friction is what makes
        # someone stop reading the value before they accept it.
        #
        # WHAT THEY SAID, WHEN A MAP CHANGED IT. `services: [tax_planning]`
        # translates to "1040", and this line then told the preparer the
        # website said "1040" -- which the client never said. The firm on what
        # a lead is for: "we would confirm what they put there. they didn't
        # necessarily know what they needed." Confirming what they put there
        # needs it shown. See interview.prefill_source.
        hint = (f"website said: {default!r}"
                + (f" (they asked about {said})" if said else "")
                + " -- enter to accept, '-' to clear"
                + (f"; {hint}" if hint else ""))
    req = "required" if q.get("required") else "optional"
    raw = input(f"      [{req}{'; ' + hint if hint else ''}] > ").strip()

    if raw == "-":
        # An explicit "the website is wrong and the answer is nothing".
        return [] if q["type"] in ("multi", "list") else None

    if not raw:
        if has_default:
            return default
        if q["type"] in ("multi", "list"):
            return []
        return None

    if q["type"] == "single":
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]["value"]
        return raw
    if q["type"] == "multi":
        picked = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(options):
                picked.append(options[int(part) - 1]["value"])
            elif part:
                picked.append(part)
        return picked
    if q["type"] == "list":
        return [p.strip() for p in raw.split(",") if p.strip()]
    if q["type"] == "number":
        try:
            return int(raw)
        except ValueError:
            return raw
    return raw


def cmd_interview(args) -> int:
    lead = json.loads(Path(args.lead).read_text(encoding="utf-8")) if args.lead else None
    carried = dict(getattr(args, "carried", None) or {})
    session = iv.Interview(
        lead=lead, carried=carried,
        # The operator has already said this block is wrong, so the sitting is
        # not ended by it. `intake.finish` still records the override.
        override_hard_no=getattr(args, "override_hard_no", False))

    # A saved answers file replays an interview without a human at the
    # keyboard: how the tests drive it, and how you resume one you abandoned.
    # Answers are keyed by question id, so a schema change that renumbers the
    # flow cannot silently shift them onto the wrong questions.
    if args.answers:
        canned = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        while True:
            nxt = session.next_question()
            if nxt is None:
                break
            _, q = nxt
            if q["id"] not in canned and q["id"] in carried:
                session.answer(q["id"], carried[q["id"]])
                continue
            if q["id"] not in canned:
                if q.get("required"):
                    raise SystemExit(
                        f"answers file has nothing for required question "
                        f"{q['id']!r} ({q['question']})"
                    )
                session.answer(q["id"], [] if q["type"] in ("multi", "list") else None)
                continue
            session.answer(q["id"], canned[q["id"]])
        unused = {k for k in canned if not k.startswith("_")} - set(session.answers)
        if unused:
            print(f"note: {len(unused)} answer(s) unused -- their questions were "
                  f"not asked: {', '.join(sorted(unused))}")
        return _finish(session, args)

    print("SAT-C consultation interview")
    print(f"  {sum(1 for _ in iv.all_questions(session.schema))} questions, "
          f"branching. Blank skips an optional one; Ctrl-C abandons.")
    if lead:
        print("  A website lead is loaded. Its answers are shown as claims to "
              "confirm, never taken as given.")

    while True:
        nxt = session.next_question()
        if nxt is None:
            break
        section, q = nxt
        try:
            # LAST YEAR'S ANSWER IS A CLAIM, and a weaker one than the
            # website's, because a year has passed. It is offered as the
            # default and never taken as given -- the question is still asked.
            value = _ask(section, q,
                         carried.get(q["id"], iv.prefill_for(q, lead)),
                         iv.prefill_source(q, lead))
            session.answer(q["id"], value)
        except iv.InterviewError as exc:
            print(f"      {exc} -- asking again")
        except (KeyboardInterrupt, EOFError):
            print("\n\nabandoned; nothing was written")
            return 1

    return _finish(session, args)


def _wrap_flag(text: str) -> str:
    """A review note, indented and wrapped so it reads as one note.

    Left unwrapped these run to whatever the terminal is wide, and two of them
    become a wall nobody reads -- which is the failure mode of every advisory
    message ever written.
    """
    return textwrap.fill(text, width=76, initial_indent="    ",
                         subsequent_indent="      ")


def _finish(session, args) -> int:
    """Print what the core decided. The gates are NOT here.

    Every rule this function used to enforce now lives in `intake.finish`, so
    the web UI and anything else driving the interview hits the same ones. This
    is a renderer over the outcome and nothing more -- if a decision appears in
    this function again, the other front doors have quietly lost it.
    """
    outcome = intake.finish(
        session.answers,
        store=Path(args.store) if args.store else None,
        ref=getattr(args, "ref", None),
        fee_schedule=getattr(args, "fee_schedule", None),
        override_hard_no=getattr(args, "override_hard_no", False),
    )

    if outcome.blockers:
        print("\nHARD NO flagged:")
        for b in outcome.blockers:
            print(f"    {b}")
        if outcome.overridden:
            print("  overridden on the command line")

    if outcome.flags:
        print("\nWorth a look before this is quoted:")
        for f in outcome.flags:
            print(_wrap_flag(f))

    if outcome.status == "refused":
        print(f"\nNo engagement created. {outcome.reason}")
    elif outcome.status == "declined":
        print(f"\n{outcome.reason}")
    elif outcome.status == "error":
        print(f"\n{outcome.reason}")
        print("engagement not created -- fix registry/fee-schedule.yaml first")
    else:
        print(f"\nEngagement {outcome.ref} created")
        print(f"    {outcome.path}/record.json      the merge fields")
        print(f"    {outcome.path}/interview.json   every answer, including the internal ones")
        print(f"\nNext:  python cli.py render --engagement {outcome.ref} --out out")

    return outcome.exit_code


def cmd_returning(args) -> int:
    """This year's interview, seeded from last year's answers.

    The firm chose this over building an organizer, and gave the reason:
    "we are not copying out of drake - drake is only system of record for
    info. but our interview and such is system of record until proven wrong."
    A returning client does not need last year's FIGURES typed back at them.
    They need last year's ANSWERS shown back for confirmation, plus the events
    that move a return.

    NOTHING IS ASSUMED. Every carried answer is still asked, offered as last
    year's claim, exactly the way a website lead's answer is offered. A carried
    answer that answered itself would be an assumption wearing a
    confirmation's clothes.
    """
    store = Path(args.store) if args.store else engagements.STORE
    prior_path = engagements._dir(store, args.engagement) / "interview.json"
    if not prior_path.exists():
        print(f"\n{args.engagement} has no saved interview, so there is nothing "
              f"to carry forward.\nRun `interview` instead — a client we cannot "
              f"show last year's answers to is\na new client as far as this "
              f"command is concerned.\n")
        return 1

    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    carried, dropped = iv.carry_forward(prior)

    name = prior.get("client_full_name", args.engagement)
    print(f"\nReturning client — {name}")
    print(f"  last year: {args.engagement}\n")
    print(f"  {len(carried)} answer(s) carried forward, each shown for you to "
          f"confirm:")
    for key in sorted(carried):
        shown = carried[key]
        if isinstance(shown, list):
            shown = ", ".join(str(x) for x in shown)
        print(f"      {key:22} {str(shown)[:52]}")
    if dropped:
        print(f"\n  {len(dropped)} answer(s) deliberately NOT carried:")
        for key in dropped:
            print(f"      {key:22} {iv.DOES_NOT_CARRY.get(key, '')}")
    print("\n  Everything else is asked fresh. A count is a fact about one "
          "year, and\n  carrying it would be inventing this year's return out "
          "of last year's.\n")

    args.lead = None
    args.carried = carried
    # The change questions exist for exactly this flow, and this is the one
    # place that knows the answer to their gate.
    args.carried = {**carried, "returning_client": "yes"}
    return cmd_interview(args)


def cmd_close(args) -> int:
    """Record what was actually filed, and say where it differs from what we
    were told.

    The end of the cycle, and the half of the control a person does. Nothing
    is read out of Drake: the preparer answers a short set of questions from
    the filed return, in-house, which is what the firm asked for.
    """
    store = Path(args.store) if args.store else engagements.STORE
    try:
        record = engagements.load(args.engagement, store)
    except engagements.EngagementError as exc:
        print(exc)
        return 1

    answers_path = engagements._dir(store, args.engagement) / "interview.json"
    if not answers_path.exists():
        print(f"\n{args.engagement} has no saved interview, so there is nothing "
              f"to reconcile against.\n")
        return 1
    answers = json.loads(answers_path.read_text(encoding="utf-8"))
    return_type = record.get("_return_type", "individual")
    asked = closeout.questions_for(return_type)

    if args.filed:
        filed = json.loads(Path(args.filed).read_text(encoding="utf-8"))
    else:
        print(f"\nClosing {args.engagement} — "
              f"{record.get('ClientFullName', '')}")
        print(f"  {len(asked)} question(s) about what was actually filed. "
              f"Blank leaves one unanswered,\n  and an unanswered question is "
              f"reported as unanswered, never as agreement.\n")
        filed = {}
        for q in asked:
            print(f"\n  {q['id']}")
            print(f"  {q['question']}")
            if q.get("options"):
                print(f"      one of: {', '.join(q['options'])}")
            try:
                value = input("  > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\nabandoned; nothing was written")
                return 1
            if value:
                filed[q["id"]] = value

    closeout.save(args.engagement, filed, store)
    divergences = closeout.compare(answers, filed, return_type)
    unanswered = closeout.missing(filed, return_type)

    print(f"\n{args.engagement} closed — {len(filed)} of {len(asked)} answered")
    if unanswered:
        print(f"\n  {len(unanswered)} question(s) unanswered, so not checked:")
        for qid in unanswered:
            print(f"      {qid}")
    if not divergences:
        print("\n  Nothing on the return disagrees with what we were told.\n")
        return 0

    print(f"\n  {len(divergences)} divergence(s) — the return and the "
          f"interview disagree:\n")
    for d in divergences:
        print(d.line())
        for line in textwrap.wrap(d.why, 68):
            print(f"      {line}")
        print()
    print("  A divergence is not an error. Either the return changed after the\n"
          "  interview, or the interview was wrong, or the wrong thing was\n"
          "  filed — and only you can tell which. When the return is right:\n"
          f"      python cli.py reconcile --engagement {args.engagement} --apply\n")
    return 0


def cmd_reconcile(args) -> int:
    """THE END-OF-CYCLE CONTROL. Every engagement, closed or not.

    The firm: "our interview and such is system of record until proven wrong.
    we should update the data to match what we file if required. this should
    be a control we build at the end of the cycle."

    An engagement with no close-out is reported as NOT CLOSED rather than
    skipped. A control that only examines the work somebody remembered to
    close is a control over the diligent, which is not where the problem is.
    """
    store = Path(args.store) if args.store else engagements.STORE
    reviewed = closeout.sweep(store)
    if args.engagement:
        reviewed = [r for r in reviewed if r.ref == args.engagement]
        if not reviewed:
            print(f"no engagement {args.engagement} in {store}")
            return 1

    if not reviewed:
        print(f"\nNothing in {store} to reconcile.\n")
        return 0

    open_ones = [r for r in reviewed if not r.closed]
    diverged = [r for r in reviewed if r.divergences]

    print(f"\nEnd-of-cycle reconciliation — {len(reviewed)} engagement(s)\n")
    for r in reviewed:
        if not r.closed:
            print(f"  NOT CLOSED  {r.ref}  {r.client}")
            continue
        if not r.divergences:
            note = "agrees"
            if r.unanswered:
                note += f", {len(r.unanswered)} question(s) unanswered"
            print(f"  ok          {r.ref}  {r.client} — {note}")
            continue
        print(f"  DIVERGES    {r.ref}  {r.client}")
        for d in r.divergences:
            print(f"      {d.against}: we were told {d.asked!r}, "
                  f"filed as {d.filed!r}")

    if args.apply:
        moved_total = 0
        for r in diverged:
            moved = closeout.apply_to_answers(r.ref, r.divergences, store)
            moved_total += len(moved)
            for m in moved:
                print(f"\n  moved  {r.ref}  {m['answer']}: "
                      f"{m['was']!r} -> {m['now']!r}")
        print(f"\n  {moved_total} answer(s) moved to match what was filed, "
              f"and every move is\n  recorded in the engagement's own "
              f"reconciled.json. Next year's interview\n  is seeded from "
              f"these answers, which is why it matters that they are right.\n")
        return 0

    print(f"\n  {len(reviewed) - len(open_ones)} closed · "
          f"{len(open_ones)} still open · {len(diverged)} diverging")
    if diverged:
        print("\n  Nothing has been changed. When the returns are right and the\n"
              "  record should follow:  python cli.py reconcile --apply\n")
    else:
        print()
    return 0


def cmd_procedures(args) -> int:
    """Write the operating procedures, or check the committed copy is current.

    Generated from the software that performs them, so a procedure cannot
    describe a command that does not exist or a document a return type does
    not get. `--check` runs in the suite: a procedure that has quietly stopped
    being true is the same failure as a document that promises an enclosure it
    does not carry.
    """
    def _shown(path: Path) -> str:
        # A path outside the repo is printed whole rather than crashing.
        # `relative_to` raises on anything it cannot shorten, and a command
        # that dies while reporting where a file is has lost the plot.
        try:
            return str(path.relative_to(ROOT.parent))
        except ValueError:
            return str(path)

    if args.check:
        if procedures.is_current(procedures.OUT):
            print(f"{_shown(procedures.OUT)} is what the software generates "
                  f"today.")
            return 0
        print(f"\n{_shown(procedures.OUT)} is out of date — the software has "
              f"changed\nand the procedures have not. Regenerate:\n\n"
              f"    python cli.py procedures\n")
        return 1
    path = procedures.write(procedures.OUT)
    print(f"wrote {_shown(path)} from the software itself")

    if getattr(args, "html", None):
        # THE MARKDOWN IS WRITTEN FIRST, ALWAYS. The reading copy is a
        # rendering of the committed source, so the two cannot describe
        # different software: there is one generation and one document behind
        # both of them.
        import procedures_html
        doc = procedures_html.render(path)
        lost = procedures_html.dropped(path.read_text(encoding="utf-8"), doc)
        if lost:
            print(f"\nThe reading copy was NOT written: it would have dropped "
                  f"{lost}.\nA rendering that loses a step is worse than no "
                  f"rendering.\n")
            return 1
        out = Path(args.html)
        out.write_text(doc, encoding="utf-8")
        print(f"wrote {_shown(out)} — one file, nothing beside it")
    return 0


def _ask_rows(spec: dict) -> list[dict]:
    """One repeating list, at a terminal. Blank line ends it."""
    cols = spec["columns"]
    print(f"\n  {spec['prompt']} — {', '.join(cols)}")
    print(f"      one per line, {' | '.join(c.lower() for c in cols)}; "
          f"blank to finish")
    rows = []
    while True:
        try:
            line = input("  > ").strip()
        except (KeyboardInterrupt, EOFError):
            raise
        if not line:
            break
        parts = [p.strip() for p in line.split("|")]
        parts += [""] * (len(cols) - len(parts))
        rows.append(dict(zip(cols, parts[:len(cols)])))
    return rows


def cmd_walkthrough(args) -> int:
    """The guided walkthrough, from screens photographed out of the software.

    Two halves, deliberately: `capture.py` drives the real application in a
    real browser and writes down what is on each screen; this turns that plus
    the sentences in `registry/walkthrough.yaml` into one file. Neither half
    can quietly go stale, because a control with nothing written about it and a
    sentence about a control that has gone both stop the document being
    written at all.
    """
    import walkthrough as wt
    import walkthrough_html

    if args.check:
        if not wt.INVENTORY_FILE.exists():
            print(f"\nthere is no committed inventory of screens at "
                  f"{wt.INVENTORY_FILE.name}. Run:\n\n    python capture.py\n")
            return 1
        screens = wt.from_json(
            wt.INVENTORY_FILE.read_text(encoding="utf-8"))
        gaps = wt.missing(screens, wt.load_registry())
        if not gaps:
            print(f"{len(screens)} screen(s), "
                  f"{sum(len(s.controls) for s in screens)} control(s), all "
                  f"accounted for.")
            return 0
        print(f"\n{len(gaps)} thing(s) the walkthrough would be wrong about:")
        for g in gaps:
            print(f"    {g}")
        print(f"\nFix `registry/walkthrough.yaml`, or re-photograph the "
              f"software with `python capture.py`.\n")
        return 1

    shots = Path(walkthrough_html.SHOTS) / "shots"
    live = shots.parent / "screens.json"
    if not live.exists():
        print(f"\nnothing has been photographed yet. Run:\n\n"
              f"    python capture.py\n")
        return 1
    screens = wt.from_json(live.read_text(encoding="utf-8"))
    try:
        doc = walkthrough_html.render(screens, wt.load_registry(), shots)
    except RuntimeError as exc:
        print(f"\n{exc}\n")
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out} — {len(screens)} screen(s), one file, nothing beside "
          f"it")
    return 0


def cmd_event(args) -> int:
    """A lifecycle event, and the document it produces.

    Four documents could not be produced by any command a preparer can run --
    the delivery letter, the organizer cover, the extension notice and the
    disengagement letter. Each needs facts that do not exist when the
    engagement is created, and nothing collected them, so the opening pack was
    a third of the process and the other two thirds had no front door.
    """
    store = Path(args.store) if args.store else engagements.STORE
    try:
        ev = lifecycle.event(args.kind)
    except lifecycle.LifecycleError as exc:
        print(f"\n{exc}\n")
        return 1
    try:
        raw = engagements.load(args.engagement, store)
    except engagements.EngagementError as exc:
        print(exc)
        return 1

    saved = lifecycle.load_saved(args.engagement, args.kind, store) or {}
    if args.answers:
        payload = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        answers = payload.get("answers", payload)
        rows = payload.get("rows", {})
    elif saved and not args.again:
        answers, rows = saved.get("answers", {}), saved.get("rows", {})
        print(f"\nUsing the answers already recorded for {args.kind}. "
              f"`--again` asks them afresh.")
    else:
        print(f"\n{args.kind} — {ev.what}")
        print(f"  {args.engagement}  {raw.get('ClientFullName', '')}\n")
        answers, rows = {}, {}
        try:
            for q in ev.questions:
                if not lifecycle.asks(q, answers):
                    continue
                print(f"\n  {q['question']}")
                if q.get("options"):
                    print(f"      one of: {', '.join(q['options'])}")
                if q.get("why"):
                    for line in textwrap.wrap(" ".join(q["why"].split()), 66):
                        print(f"      {line}")
                answers[q["id"]] = input("  > ").strip()
            for spec in ev.rows:
                rows[spec["list"]] = _ask_rows(spec)
        except (KeyboardInterrupt, EOFError):
            print("\n\nabandoned; nothing was written")
            return 1

    merged = lifecycle.fields(args.kind, answers, rows)
    short = lifecycle.missing(args.kind, merged)
    if short:
        print(f"\nNot enough to write the {ev.document} yet — still needs: "
              f"{', '.join(short)}.\nNothing was saved. A document that cannot "
              f"be honest is not written.\n")
        return 1

    lifecycle.save(args.engagement, args.kind,
                   {"answers": answers, "rows": rows}, store)

    record = build_record({**raw, **merged})
    outdir = Path(args.out) if args.out else Path("out") / args.engagement
    rc = cmd_render(argparse.Namespace(
        record=None, engagement=None, store=None, docs=[ev.document],
        out=str(outdir), no_pdf=args.no_pdf, draft=False,
        _record_override=record))
    return rc


def _requote_questions(ref: str, store: Path) -> int:
    """What can be changed, and what it says today. The no-argument case.

    `store` is passed rather than reached for. It defaulted to the real
    engagement store while every other line of this command honoured
    `--store`, so the listing reported "no saved interview" for an engagement
    that was sitting right there in the store the caller named. Found by
    running the command, which is the only way that class of bug is found.
    """
    try:
        answers = requote._answers(ref, store)
    except requote.RequoteError as exc:
        print(f"\n{exc}\n")
        return 1
    print(f"\nThese are the answers that move money on {ref}.")
    print("Change one with --set, and give --reason to write it:\n")
    print(f"    python cli.py requote --engagement {ref} \\")
    print(f"        --set count_rentals=2 --reason 'bought a second rental "
          f"in April'\n")
    print("  Changing one can reveal another — how many rentals is only asked\n"
          "  once Schedule E is on the return.\n")
    for q in requote.questions(answers):
        held = answers.get(q["id"])
        shown = ", ".join(str(x) for x in held) if isinstance(held, list) \
            else ("" if held in (None, "") else str(held))
        print(f"  {q['id']:26} {shown[:30]:32} {q['question'][:52]}")
    print()
    return 0


def _print_quote(quote, ref: str) -> None:   # noqa: ARG001
    """The plan, as a preparer reads it out loud. Nothing has been written."""
    for line in quote.blockers:
        print("\n  " + textwrap.fill(line, 72, subsequent_indent="  "))
    if quote.blockers:
        print()
        return
    print("\n  What changed in the interview")
    for change in quote.changed:
        print(f"      {requote._question_text(change.question)}")
        print(f"          {change.line()}")
    if not quote.changed:
        print("      nothing — these are the answers already on file")

    print("\n  The estimate")
    if quote.moved:
        for mv in quote.moved:
            was = mv.before if mv.before is not None else "—"
            now = mv.after if mv.after is not None else "— (gone)"
            print(f"      {mv.service[:38]:40} {was:>12}  →  {now}")
    else:
        print("      no line moves")
    print(f"      {'TOTAL':40} {quote.before_total:>12}  →  "
          f"{quote.after_total}")
    print(f"\n  {quote.difference}.")

    if quote.scope_moved:
        # SAID SEPARATELY, AND SAID SECOND. The price is the headline and the
        # scope is the thing that gets missed -- it is on a letter the client
        # has already signed.
        print("\n  The scope on the engagement letter moves too")
        for change in quote.scope_moved:
            print(f"      {change.line()}")
    for note in quote.notes:
        print("\n  " + textwrap.fill(note, 72, subsequent_indent="  "))
    print()


def cmd_requote(args) -> int:
    """Quote a live engagement again, because the work changed.

    NOBODY TYPES A FIGURE. The answers move and the same engine that priced
    the engagement the first time prices it again -- see `requote.py` for why
    that is not a stylistic preference.

    WITHOUT `--reason`, THIS WRITES NOTHING. The plan prints and the command
    stops. A re-quote that could happen by accident is a price that moved and
    cannot be explained, and the reason is what makes it explicable a year
    later.
    """
    store = Path(args.store) if args.store else engagements.STORE
    if not args.set:
        return _requote_questions(args.engagement, store)

    changes = {}
    schema = iv.load_schema()
    asked = {q["id"]: q for _, q in iv.all_questions(schema)}
    for pair in args.set:
        if "=" not in pair:
            print(f"\n--set wants question=value, got {pair!r}.\n")
            return 1
        qid, raw = pair.split("=", 1)
        qid = qid.strip()
        q = asked.get(qid)
        if q is None:
            print(f"\nThe interview asks no question called {qid!r}. Run this "
                  f"without --set to see the ones that move money.\n")
            return 1
        # The same conversion the browser does, from the same function: "2"
        # has to become the integer 2 in both doors or they price differently.
        changes[qid] = iv.coerce(q, raw)

    try:
        quote = requote.plan(args.engagement, changes, store=store)
    except (engagements.EngagementError, requote.RequoteError) as exc:
        print(f"\n{exc}\n")
        return 1

    print(f"\n{args.engagement} — "
          f"{engagements.load(args.engagement, store).get('ClientFullName','')}")
    _print_quote(quote, args.engagement)
    if not quote.ok:
        return 1

    if not args.reason:
        print("  Nothing has been written. Add --reason to record it, in one\n"
              "  sentence, for whoever reads this engagement next year.\n")
        return 0

    try:
        path = requote.apply(quote, args.reason, store=store)
    except (requote.RequoteError, tins.TinRefused) as exc:
        print(f"  {exc}\n")
        return 1

    print(f"  Recorded. {path}")
    print(f"\n  Next: python cli.py package --engagement {args.engagement} "
          f"--out packs/{args.engagement}")
    if quote.scope_moved:
        print("        — the scope moved, so the whole pack is out of date. "
              "It is rebuilt from\n          the new answers and goes through "
              "the same pre-send gate as the first one.\n")
    else:
        print("        — the estimate is rebuilt from the new figure. The "
              "engagement letter still\n          reads correctly, so the "
              "estimate can go on its own if you prefer.\n")
    return 0


def _signing_state(ref: str, store: Path):
    """(record, documents, standing) for one engagement, or None with a note."""
    record = engagements.load(ref, store)
    docs = packaging.documents_for(record)
    deadline = ""
    saved = lifecycle.load_saved(ref, "delivery", store) or {}
    for qid, value in (saved.get("answers") or {}).items():
        if qid == "signature_deadline":
            deadline = value
    return record, docs, signing.standing(
        ref, record, docs, TEMPLATE_DIR, store=store, deadline=deadline)


def _signing_sweep(store: Path) -> int:
    """Who to chase this morning, across every engagement.

    THE HALF THAT PAYS. Sending a pack is three minutes of clicking; knowing
    which clients have not signed, and which are past the date they were
    given, is what nothing supported at all.
    """
    rows = signing.waiting(store, template_dir=TEMPLATE_DIR)
    if not rows:
        seen = len(engagements.listing(store))
        print(f"\nNothing outstanding — {seen} engagement(s) looked at.\n"
              if seen else "\nNo engagements yet.\n")
        return 0
    print(f"\n{len(rows)} engagement(s) waiting on a signature, "
          f"longest first:\n")
    for w in rows:
        days = w.waiting_days()
        out = f"{days}d" if days is not None else "not sent"
        mark = "!!" if w.overdue else "  "
        print(f"  {mark} {w.ref}  {w.client[:26]:28} {out:>9}  "
              f"{len(w.missing)} of {w.examined} outstanding"
              + (f"  — due {w.deadline}" if w.deadline else ""))
        for line in w.missing:
            print(f"        {line.document:22} {line.who}")
    # The legend only where there is something to explain. A key under a list
    # with no marks in it is noise, and noise is what gets skimmed past.
    if any(w.overdue for w in rows):
        print("\n  !! past the date the client was given.")
    print()
    return 0


def cmd_sign(args) -> int:
    """Who has signed what, and record one that has come back.

    NOBODY TYPES A LIST OF WHO MUST SIGN. The templates carry the signature
    blocks and this reads them, so a block that moves or gains a signer is
    followed automatically -- and the spouse's line is expected only on a
    joint return, because that is how the letter is drawn and what the
    delivery letter tells the client.
    """
    store = Path(args.store) if args.store else engagements.STORE
    if not args.engagement:
        return _signing_sweep(store)
    try:
        record, docs, where = _signing_state(args.engagement, store)
    except engagements.EngagementError as exc:
        print(f"\n{exc}\n")
        return 1

    name = record.get("ClientFullName", "")
    if not args.record and not args.sent:
        print(f"\n{args.engagement} — {name}")
        if where.sent:
            days = where.waiting_days()
            print(f"  sent {where.sent}"
                  + (f", {days} day(s) ago" if days is not None else ""))
        else:
            print("  not recorded as sent — `--sent encyro` starts the clock")
        print(f"\n  {where.examined} signature(s) this pack asks for:\n")
        got = {(s.document, s.field): s for s in where.have}
        for line in where.expected:
            have = got.get((line.document, line.field))
            mark = "signed" if have else "OUTSTANDING"
            when = f"  {have.when}" if have else ""
            # THE NAME `--record` WANTS, PRINTED WHERE IT IS READ. This
            # column used to show only `line.who` -- "Taxpayer", "Spouse" --
            # while `--record` matches `line.field` ("TaxpayerName",
            # "SpouseName"), and the refusal for a wrong one said "run without
            # --record to see the ones it does", which printed the names it
            # rejects. Recording a spouse's signature, required on every joint
            # return, was a closed loop.
            print(f"      {mark:12} {line.document:20} {line.who:22}"
                  f"{when}")
            print(f"      {'':12} {'':20} --record "
                  f"{line.document}/{line.field}")
        if where.deadline:
            print(f"\n  Due by {where.deadline}"
                  + ("  — PASSED" if where.overdue else ""))
        gate = signing.may_file(args.engagement, record, docs, TEMPLATE_DIR,
                                store=store, deadline=where.deadline)
        for blocker in gate.blockers:
            print("\n  " + textwrap.fill(blocker, 72, subsequent_indent="  "))
        for said in gate.unknown:
            print("\n  NOT KNOWN HERE: "
                  + textwrap.fill(said, 72, subsequent_indent="  "))
        print(f"\n  Record one:  python cli.py sign --engagement "
              f"{args.engagement} \\\n"
              f"                   --record tax-letter/TaxpayerName "
              f"--on 'February 9, 2027' --how in-person\n")
        return 0

    if args.sent:
        try:
            path = signing.mark_sent(args.engagement, args.sent,
                                     when=args.on or "", store=store)
        except signing.SigningError as exc:
            print(f"\n{exc}\n")
            return 1
        print(f"\n  Recorded as sent. {path}\n")
        return 0

    if "/" not in args.record:
        print("\n--record wants document/Field, as the list above prints it.\n")
        return 1
    doc, fieldname = args.record.split("/", 1)
    # EITHER NAME. The field id is what this matched, and the listing showed
    # the human label; somebody typing what they were shown was refused. Both
    # are accepted now, and a wrong one is answered with the names that work
    # rather than a pointer back to the listing that rejected it.
    line = next((ln for ln in where.expected
                 if ln.document == doc
                 and fieldname.casefold() in (ln.field.casefold(),
                                              ln.who.casefold())), None)
    if line is None:
        print(f"\nThis pack has no signature line {args.record!r}. It asks "
              f"for:\n")
        for ln in where.expected:
            print(f"      --record {ln.document}/{ln.field}"
                  f"      ({ln.who})")
        print()
        return 1
    try:
        path = signing.record_signature(
            args.engagement, line, when=args.on or "", how=args.how or "",
            reference=args.reference or "", store=store)
    except signing.SigningError as exc:
        print(f"\n{exc}\n")
        return 1
    print(f"\n  Recorded. {path}\n")
    return 0


def cmd_spent(args) -> int:
    """What an engagement has actually taken, beside what its price budgeted.

    THE LOOP THAT WAS NEVER CLOSED. The fee schedule is priced in hours; the
    software budgets in hours and rounds to the quarter-hour a timesheet takes.
    Nothing ever recorded one, so no engagement has been compared against its
    own budget and every price in the schedule is still the estimate it was
    written with.
    """
    store = Path(args.store) if args.store else engagements.STORE
    ref = args.engagement

    try:
        record = engagements.load(ref, store)
    except Exception as exc:      # noqa: BLE001 - say which engagement, not a trace
        print(f"  {exc}")
        return 1

    if args.add is not None:
        try:
            timelog.add(store, ref, args.add, args.what or "")
        except (ValueError, FileNotFoundError) as exc:
            print(f"  {exc}")
            return 1
        print(f"  recorded {args.add}h against {ref}: {args.what}")

    schedule = pricing.load()
    try:
        _, _, floor = fees.basis_of(schedule)
    except fees.FeeBasisError:
        floor = 0.25
    got = timelog.spent(store, ref, floor=floor)

    print(f"\n  {ref}  {record.get('ClientFullName') or '(no name)'}\n")

    # S2: A REPORT WITH NOTHING IN IT SAYS SO. "0.0 hours" beside a budget reads
    # as a job that took no time, which is a claim; "nothing recorded" is the
    # truth, and they are different sentences.
    if got.examined_nothing:
        print("  nothing recorded yet. Time is written here automatically as")
        print("  commands run against this engagement, so this fills in by")
        print("  itself — and `--add` is for the work in Drake, which this")
        print("  software cannot see.")
        return 0

    print(f"  measured   {got.measured:>6.2f} h   "
          f"across {len(got.sittings)} sitting(s), from {got.touches} touch(es)")
    for sitting in got.sittings:
        print(f"      {sitting.started:%d %b %H:%M}-{sitting.ended:%H:%M}  "
              f"{sitting.hours(floor=floor):>5.2f} h   "
              + ", ".join(sitting.what[:4]))
    print(f"  stated     {got.stated:>6.2f} h   "
          f"across {len(got.stated_entries)} entr(y/ies)")
    for said in got.stated_entries:
        print(f"      {said.when:%d %b %H:%M}  {said.hours:>5.2f} h   {said.what}")

    # THE TWO ARE NEVER ADDED. A single total would look authoritative and would
    # not be: measured is a FLOOR -- it sees the software and not Drake, where
    # most of the return is prepared -- and stated is somebody's recollection.
    # Summing a floor and a recollection produces a number nobody can defend.
    print("\n  These are not added together. `measured` is what the software")
    print("  saw and is a floor — it cannot see Drake. `stated` is what a")
    print("  person said. A single total would look more certain than either.")

    budget = record.get("BudgetHours") or record.get("EstimatedHours")
    if budget:
        try:
            budget = float(budget)
            print(f"\n  budgeted   {budget:>6.2f} h   from the price on this "
                  f"engagement")
            print(f"  measured is {got.measured / budget:.0%} of it; "
                  f"measured plus stated is "
                  f"{(got.measured + got.stated) / budget:.0%}")
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    else:
        # NOT SILENCE. The comparison is the entire point of the command, and
        # its absence is a fact about the engagement worth saying out loud.
        print("\n  no budget on this engagement to compare against — the record")
        print("  carries no BudgetHours. `python cli.py hours` shows what the")
        print("  schedule's prices imply, which is the same arithmetic one")
        print("  level up.")
    return 0


def cmd_season(args) -> int:
    """What is due across the whole book, soonest first.

    THE SCREEN THAT DID NOT EXIST. Everything else here acts on one engagement;
    nothing looked across all of them and said what season it is. That is what a
    person otherwise holds in their head through February.
    """
    import deadlines

    store = Path(args.store) if args.store else engagements.STORE
    refs = [r["ref"] for r in engagements.listing(store)]
    if not refs:
        print("no engagements yet -- `python cli.py interview` creates one")
        return 0

    records = []
    unreadable = []
    for ref in refs:
        try:
            records.append((ref, engagements.load(ref, store)))
        except Exception:      # noqa: BLE001 - a bad record is reported, not skipped
            unreadable.append(ref)

    today = date.fromisoformat(args.today) if args.today else date.today()
    due, unplaced = deadlines.board(records, today=today, within_days=args.within)

    # THE DENOMINATOR, FIRST. A board that says "nothing due" is only good news
    # if it looked at something -- see S2. This line is why.
    print(f"{len(refs)} engagement(s) read, {today.isoformat()}"
          + (f", looking {args.within} days ahead" if args.within else "") + "\n")

    if not due:
        print("  nothing due in that window.")
    for row in due:
        when = "OVERDUE" if row.overdue else f"{row.days:>4}d"
        mark = "!!" if row.overdue else ("  " if row.statutory else "· ")
        print(f"{mark} {row.when}  {when:>7}  {row.ref}  "
              f"{row.client[:28]:30s} {row.what}")

    if unplaced:
        # NAMED, NOT DROPPED. An engagement whose form or year we cannot read
        # has an UNKNOWN deadline, and leaving it off the board says the season
        # is quieter than it is.
        print(f"\n  {len(unplaced)} could not be placed on a date "
              f"(no federal form or no tax year): " + ", ".join(unplaced))
    if unreadable:
        print(f"  {len(unreadable)} record(s) could not be read: "
              + ", ".join(unreadable))
    return 0


def cmd_engagements(args) -> int:
    rows = engagements.listing(Path(args.store) if args.store else engagements.STORE)
    if not rows:
        print("no engagements yet -- `python cli.py interview` creates one")
        return 0
    for r in rows:
        print(f"  {r['ref']}  {r['client'][:40]:42s} {r.get('period','')}")
    return 0


# Which `[[EACH]]` lists may not be empty, read from the registry rather than
# decided here. An EACH block over an empty list renders to the same nothing
# as one over a missing list, so a fee estimate with no line items produced a
# blank services table with a total underneath it and nothing objected. Which
# lists may legitimately be empty is a judgement about the document -- an
# extension notice with nothing outstanding is real; a bill with no lines is
# not -- so it is declared in registry/fields.yaml, not in this front door.
@lru_cache(maxsize=1)
def _required_lists() -> dict:
    spec = yaml.safe_load(
        (ROOT / "registry" / "fields.yaml").read_text(encoding="utf-8")) or {}
    out: dict[str, tuple] = {}
    for entry in spec.get("lists") or []:
        if not entry.get("required"):
            continue
        for tpl in entry.get("templates") or []:
            out[tpl] = out.get(tpl, ()) + (entry["list"],)
    return out


def _inverse_flags() -> tuple:
    """Flag pairs that are two faces of one decision, from the registry.

    The relationship used to live only in the prose note beside each flag
    ("Inverse of PaymentEnclosed"), which nothing read -- so a record could
    leave both of a pair false and the section they control came out empty
    under a heading that promised it said something.
    """
    spec = yaml.safe_load(
        (ROOT / "registry" / "fields.yaml").read_text(encoding="utf-8")) or {}
    seen, pairs = set(), []
    for entry in spec.get("flags") or []:
        other = entry.get("inverse_of")
        if not other:
            continue
        key = frozenset((entry["flag"], other))
        if key in seen:
            continue                    # declared on both halves, one pair
        seen.add(key)
        pairs.append((entry["flag"], other))
    return tuple(pairs)


def merge_one(doc: str, record: dict, draft: bool = False):
    """Fill one document's template. NOTHING IS WRITTEN.

    Split out of `render_one` so that LOOKING at a document does not have to
    produce a file to look at. `previewing.look` needs the merged text and the
    refusal, and had no way to ask for either without also writing the thing to
    disk -- which is the exact difference between reading a letter and sending
    one.

    `draft` is the same switch it has always been: render past what is not
    decided yet, rather than refusing.
    """
    filename, _ = DOCUMENTS[doc]
    template = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
    return merge.render(template, record, strict=not draft,
                        required_lists=_required_lists().get(doc, ()),
                        inverse_flags=_inverse_flags())


def tokens_for(doc: str) -> dict:
    """Every blank one document has. Reads the template, decides nothing.

    A preview has to say what is still missing in the words a preparer knows,
    and the merge's own refusal is written for whoever is filling a template.
    This is the census that gets turned into those words.
    """
    filename, _ = DOCUMENTS[doc]
    return merge.tokens_in((TEMPLATE_DIR / filename).read_text(encoding="utf-8"))


def render_one(doc: str, record: dict, outdir: Path, draft: bool, want_pdf: bool):
    result = merge_one(doc, record, draft)

    html = _stamp_draft(result.html) if draft else result.html
    stem = output_name(doc, record, draft)
    written = [outdir / f"{stem}.html"]
    written[0].write_text(html, encoding="utf-8")

    if want_pdf:
        _, render_pdf = pdf_engine()
        pdf_path = outdir / f"{stem}.pdf"
        render_pdf(html, pdf_path, TEMPLATE_DIR, draft)
        written.append(pdf_path)
    return result, written


# `_render_one` was private while the terminal was its only caller. It has two
# now, and the tests written against the old name still hold.
_render_one = render_one


def cmd_render(args) -> int:
    if args.engagement:
        store = Path(args.store) if args.store else engagements.STORE
        raw = engagements.load(args.engagement, store)
        # THE BILL LIVES BESIDE THE ENGAGEMENT, NOT INSIDE IT. One engagement
        # has many invoices, so `invoice` writes each to its own file rather
        # than overwriting the record -- and this front door read only the
        # record, so the command `invoice` tells you to run next refused on
        # every invoice field there is. The invoice's own fields win where
        # they overlap: `PeriodLabel` is the engagement's period on the
        # estimate and the period BILLED here, which is the one value the two
        # documents must NOT share.
        try:
            folded = invoicing.fold_in(raw, args.docs or (), store,
                                       args.engagement,
                                       getattr(args, "invoice", None))
        except invoicing.InvoiceError as exc:
            print(f"{exc}\n  Raise one first:\n  python cli.py invoice "
                  f"--engagement {args.engagement} --billed 'March 2027'\n")
            return 1
        if folded is not raw:
            print(f"  invoice {folded.get('InvoiceNumber', '')}\n")
        raw = folded
    elif getattr(args, "_record_override", None) is not None:
        # A caller that has already composed the record -- `event` merges the
        # engagement with the facts a preparer just supplied. Passing a path
        # would mean writing a temporary file whose only reader is the next
        # line of the same function.
        raw = None
    elif args.record:
        raw = json.loads(Path(args.record).read_text(encoding="utf-8"))
    else:
        raise SystemExit("give a record file or --engagement REF")
    record = (args._record_override if raw is None
              else build_record(raw))

    docs = args.docs or opening_package(record)
    unknown = [d for d in docs if d not in DOCUMENTS]
    if unknown:
        raise SystemExit(f"unknown document(s): {', '.join(unknown)}\n"
                         f"known: {', '.join(sorted(DOCUMENTS))}")

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # THE OTHER FRONT DOOR HAD THE SAME HOLE. `package` was taught to carry
    # `satc-doc.css` and `doc-page.js` on 27 August 2026, after the firm opened
    # a pack and found plain text. `render` was not -- and `render` is the
    # command this CLI itself tells you to run next after raising an invoice:
    #
    #     Next:  python cli.py render --engagement 2026-0001 --docs invoice
    #
    # So every invoice, every delivery letter, every one-off document produced
    # through this door opened as browser-default Times with the masthead
    # collapsed into one line. Found by opening 303 rendered documents rather
    # than by any test, because the harness only ever looked inside pack
    # folders. Fixing one door and not the other is how a bug survives being
    # fixed.
    for asset in presend.PACK_ASSETS:
        src = TEMPLATE_DIR / asset
        if src.exists():
            shutil.copy2(src, outdir / asset)

    want_pdf = not args.no_pdf
    if want_pdf:
        try:
            name, _ = pdf_engine()
            if name != "chromium":
                print(f"note: using {name}; install playwright for full brand "
                      f"fidelity\n", file=sys.stderr)
        except NoPdfEngine as exc:
            print(f"note: {exc}\n      writing HTML only\n", file=sys.stderr)
            want_pdf = False

    if args.draft:
        print("DRAFT MODE - output is stamped and must not reach a client\n")

    failures = 0
    for doc in docs:
        try:
            result, written = render_one(doc, record, outdir, args.draft, want_pdf)
        except merge.MergeError as exc:
            failures += 1
            print(f"  {doc:22s} REFUSED\n      {exc}\n", file=sys.stderr)
            continue
        kept = ", ".join(sorted(result.blocks_kept)) or "none"
        print(f"  {doc:22s} ok   {len(result.fields_used)} fields, blocks kept: {kept}")
        for p in written:
            print(f"      {p}")

    if failures:
        print(f"\n{failures} document(s) refused rather than shipping a hole in one.",
              file=sys.stderr)
        print("Run `python cli.py doctor` to see what is blocking, or add --draft "
              "to exercise the pipeline anyway.", file=sys.stderr)
        return 1
    return 0


def cmd_demo(args) -> int:
    """The whole chain, from a fixture, in one command.

    lead -> record -> the opening package as HTML and PDF. Draft mode, because
    the firm's decisions are open; the point is that the PIPELINE runs, not that
    the output is sendable.
    """
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    lead = ROOT / "samples" / "website-lead.json"
    skeleton = outdir / "record-from-lead.json"

    print("1. website lead -> record skeleton")
    cmd_from_lead(argparse.Namespace(lead=str(lead), out=str(skeleton),
                                     season="2026", return_type="individual",
                                     ref="2027-0114"))

    # The RECORD decides the package, so the record has to be loaded rather
    # than named. Passing the path here read `opening_package("/…/x.json")`,
    # which asked a string for `.get` and killed the command outright --
    # `demo` is the one command a newcomer runs first and it had not been run
    # since the conditional records release landed. Caught 26 Aug 2026 by a
    # scenario that simply ran every CLI verb.
    record = str(ROOT / "samples" / "tax-opening-package.json")
    loaded = json.loads(Path(record).read_text(encoding="utf-8"))
    common = dict(record=record, docs=opening_package(loaded), out=str(outdir),
                  no_pdf=args.no_pdf, engagement=None, store=None)

    print("\n2. a finished record (the interview's answers) -> documents")
    rc = cmd_render(argparse.Namespace(draft=False, **common))
    if rc == 0:
        print("\nReal render. These are sendable documents.")
        return 0

    # The record did not carry every answer, so the firm's open decisions
    # showed through. Prove the pipeline runs anyway -- stamped, so the output
    # cannot be mistaken for the real thing.
    print("\n   ...falling back to a draft so the chain still completes.\n",
          file=sys.stderr)
    return cmd_render(argparse.Namespace(draft=True, **common))


def _ask_hours(label: str) -> float | None:
    """One item. Blank leaves it unpriced -- which is the honest answer when
    the firm genuinely does not know, and the whole point of the placeholder."""
    while True:
        raw = input(f"  hours for {label}\n  > ").strip()
        if not raw:
            return None
        try:
            h = float(raw)
        except ValueError:
            print("    a number of hours, e.g. 2 or 1.5. Blank to leave unpriced.")
            continue
        if h < 0:
            print("    hours cannot be negative.")
            continue
        return h


def cmd_hours(args) -> int:
    """What each price buys, in hours, at the rate the schedule itself carries.

    The inverse of `price`, and the one people actually use: `price` is run
    once when the firm sets its fees, and this is run whenever someone wants to
    know how long they have got before a job stops earning its rate.
    """
    schedule = pricing.load()
    try:
        rate, step, floor = fees.basis_of(schedule)
    except fees.FeeBasisError as exc:
        print(f"  {exc}")
        return 1

    budgets = fees.expected_hours(schedule)
    labels = dict(fees.ITEMS)

    print(f"\nWhat each price buys, at ${rate:,.0f}/h")
    print(f"  time booked to the nearest {step:g} h, minimum {floor:g} h\n")

    if not budgets:
        print("  Nothing is priced yet, so nothing has a budget.")
        print("  Every amount in registry/fee-schedule.yaml is still [CONFIRM:].")
        print("  `python cli.py price` sets them; the budgets follow on their own.\n")
        return 0

    width = max(len(labels[p]) for p in budgets)
    under = []
    for path, _ in fees.ITEMS:
        b = budgets.get(path)
        if b is None:
            continue
        amount = fees._dig(schedule, path)
        flag = "  <-- under the minimum increment" if b.under_floor else ""
        print(f"  ${amount:>7,.0f}   {b.hours:>5.2f} h   {labels[path]:<{width}}{flag}")
        if b.under_floor:
            under.append(path)

    missing = len(fees.ITEMS) - len(budgets)
    print()
    if missing:
        print(f"  {missing} item(s) still unpriced, so still without a budget.")
    if under:
        print(f"  {len(under)} price(s) buy less than {floor:g} h — less than the")
        print(f"  smallest amount of time the firm bills. That is worth a look:")
        print(f"  either the work really is that quick, or the line is subsidised")
        print(f"  by whatever it is attached to.")
    if not missing and not under:
        print("  Every line is priced and every line clears the floor.")
    print()
    return 0


def cmd_price(args) -> int:
    """Price the firm from what its work takes, rather than from thin air."""
    if args.list:
        for path, meaning in fees.ITEMS:
            print(f"{path}\n    {meaning}")
        return 0

    source = Path(args.schedule) if args.schedule else fees.SCHEDULE
    source_text = source.read_text(encoding="utf-8")
    schedule = pricing.load(source)
    hours: dict[str, float] = {}
    covers = args.base_covers

    if args.hours:
        given = yaml.safe_load(Path(args.hours).read_text(encoding="utf-8")) or {}
        covers = covers or given.pop("base_covers", None)
        # Both come out before the rest becomes hours: they are settings that
        # ride along in the same file, not priceable items.
        rate = args.rate if args.rate is not None else given.pop("rate", None)
        hours = {k: v for k, v in given.items() if v is not None}
    else:
        rate = args.rate
        print("Pricing the firm")
        print("  Nobody knows their own prices in the abstract; they know their")
        print("  own work. So: what does each of these take you, in hours?")
        print("  Blank leaves an item unpriced -- an honest blank beats a guess.")
        print()
        if rate is None:
            while True:
                raw = input("  What is an hour of your time worth, in dollars?\n  > ").strip()
                try:
                    rate = float(raw)
                    if rate > 0:
                        break
                except ValueError:
                    pass
                print("    a number, e.g. 175.")
        print()
        if covers is None:
            print("  One structural question first, because it changes every")
            print("  number under it: does the base fee cover the first state and")
            print("  locality, or the federal return only?")
            while True:
                raw = input("  > [federal_only / one_included, blank to leave open]\n  > ").strip()
                if not raw:
                    break
                if raw in ("federal_only", "one_included"):
                    covers = raw
                    break
                print("    'federal_only' or 'one_included'.")
            print()
        for path, meaning in fees.ITEMS:
            h = _ask_hours(meaning)
            if h is not None:
                hours[path] = h

    out = fees.derive(rate, hours, increment=args.round_to,
                      base_covers=covers, schedule=schedule)

    open_now = fees.still_open(out)
    # Rewritten in place rather than dumped, so the file keeps the comments
    # that make it fillable by hand.
    text = fees.apply_to_text(source_text, schedule, out)

    if args.write:
        target = Path(args.write)
        target.write_text(text, encoding="utf-8")
        print(f"\nwrote {target}")
        if target.resolve() == fees.SCHEDULE.resolve() and not open_now:
            print("  The firm is priced. `tests/test_pricing.py::"
                  "test_the_firms_schedule_is_still_unpriced` guards the "
                  "placeholders and will now fail -- delete that test, it has "
                  "done its job.")
    else:
        print()
        print(text, end="")

    if open_now:
        print(f"\n{len(open_now)} item(s) still unpriced:")
        for path, _ in open_now:
            print(f"  {path}")
        print("The estimate will refuse to render until these are set, which is"
              "\ncorrect -- it will not quote a client $0 for a service.")
    return 0


def cmd_sample(args) -> int:
    """Rebuild `samples/tax-opening-package.json` from the demo answers.

    The demo record is what anyone looks at first to see what a client
    receives, and until 26 August 2026 it was typed by hand. It had drifted
    into quoting $450 for a 1040 and into a scope that had lost the Schedule E
    its own estimate billed for -- two documents in one package contradicting
    each other. `test_pricing.py` pins it to the engine now, so a schedule
    change fails the suite; this is the command that answers the failure
    instead of somebody editing JSON to match.

    Only the generated half is rewritten. The client, the dates and the
    reference are the sample's own and are left exactly as they are.
    """
    import requests as document_requests

    answers = json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))
    path = SAMPLES / "tax-opening-package.json"
    record = json.loads(path.read_text(encoding="utf-8"))

    before = json.dumps(record, ensure_ascii=False, sort_keys=True)
    record.update(iv.compose(answers))
    record.update(pricing.price(answers))
    # The onboarding letter's checklist, on the same footing as the estimate.
    # It was hand-written too, and it asked for five things where the answers
    # call for nine -- no signed engagement letter, no ID, and nothing about
    # the Schedule C business the estimate was pricing a package around.
    record["RequestList"] = document_requests.for_answers(answers)
    after = json.dumps(record, ensure_ascii=False, sort_keys=True)

    if before == after:
        print("samples/tax-opening-package.json is already what the engine produces")
        return 0
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print("rewrote samples/tax-opening-package.json from interview-answers.json")
    return 0


def cmd_forms(args) -> int:
    """Do our forms eliminate work, or only claim to?

    The firm's tenet, 2 September 2026: "a tenet of any checklist or
    interview-like form we make ... no matter if for clients or internal use,
    should be it directionally eliminates work where possible. for instance, if
    something is not applicable why would you want to answer questions around
    it."

    A condition on a question is a CLAIM that the question can be skipped. This
    runs each one to see whether any answer a person can actually give makes it
    false. See elimination.py -- and note the sweep reports what it examined,
    because "no dead conditions" is only good news beside a denominator.
    """
    import elimination

    sweeps = elimination.sweep_all()
    print("\nDo our forms eliminate work?\n")
    for line in elimination.report(sweeps):
        print(line)

    dead = [d for s in sweeps.values() for d in s.dead]
    print()
    if dead:
        print(f"  {len(dead)} condition(s) above read like a filter and are not "
              f"one:\n  the question is put to everybody. Either the condition "
              f"is wrong, or the\n  question belongs to everybody and should "
              f"not pretend otherwise.")
        return 1
    print("  Every condition can say no to somebody.")
    return 0


def cmd_hourly(args) -> int:
    """Put hourly work on an engagement, so it can be billed.

    THE GAP THIS CLOSES. $150 an hour is on the firm's price page under five
    named situations; `assumed.cleanup` promises clients in writing that
    reconciling their records is billed hourly against the estimate; the time
    log measures the hours. And nothing turned an hour into a line, because the
    fee schedule had no hourly construct and the invoice takes its lines from
    the priced record and nothing else. Work the firm already sold, and had
    already told clients it would bill, could not be billed.

    HOURS, NEVER AN AMOUNT. The preparer says how long it took; the schedule
    says what an hour costs. `requote` refuses a typed figure on purpose and
    this must not become the way around it -- so there is no `--amount`.

    THE MEASURED TIME IS OFFERED AS A CLAIM, not taken as the answer. The time
    log knows what the software watched, and it cannot see Drake, so it is a
    floor and a starting point -- the same standing a website lead's answer
    has, and it is confirmed the same way.
    """
    store = Path(args.store) if args.store else engagements.STORE
    ref = args.engagement
    situations = pricing.hourly_situations()

    if not args.situation:
        print("\n  The firm's hourly situations, in the words the price page "
              "already uses:\n")
        for key, label in situations.items():
            print(f"      {key:18} {label}")
        rate = (pricing.load().get("basis") or {}).get("rate")
        print(f"\n  Billed at {m.money(rate)} an hour, to the quarter hour.")
        print(f"\n  Add one:  python cli.py hourly --engagement {ref} "
              f"--for cleanup --hours 1.5")
        return 0

    path = engagements._dir(store, ref) / "interview.json"
    if not path.exists():
        print(f"\n  no engagement {ref} in {store}")
        return 1
    answers = json.loads(path.read_text(encoding="utf-8"))

    hours = args.hours
    if hours is None:
        spent = timelog.spent(store, ref)
        if spent.examined_nothing:
            print("\n  No hours given, and the time log has nothing recorded "
                  "for this\n  engagement to offer instead. Pass --hours.")
            return 2
        print(f"\n  The software measured {spent.measured:g} h on {ref}. It "
              f"cannot see Drake,\n  so that is a floor, not the answer.\n")
        print(f"  Bill that:  python cli.py hourly --engagement {ref} "
              f"--for {args.situation} --hours {spent.measured:g}")
        return 2

    # EVERYTHING IS CHECKED BEFORE ANYTHING IS WRITTEN. The date parse used to
    # sit after the line was priced and saved, so a refused `--on` returned 1
    # having already put a billing line on the engagement -- the shape the
    # atomic pack exists to prevent, reintroduced in a new command. Caught by
    # running it: the refusal printed, and the next run said "2 hourly lines".
    worked = None
    if getattr(args, "on", None):
        try:
            worked = _dt.datetime.fromisoformat(args.on)
        except ValueError:
            print(f"\n  --on wants a date as 2027-02-09. {args.on!r} could be "
                  f"read two ways\n  and this will not pick one. Nothing was "
                  f"written.")
            return 1

    try:
        line = pricing.hourly_line(args.situation, hours)
    except pricing.PricingError as exc:
        print(f"\n  {exc}")
        return 1

    work = list(answers.get("hourly_work") or [])
    work.append({"kind": args.situation, "hours": float(hours),
                 "note": args.note or ""})
    answers["hourly_work"] = work
    # THE FIFTH SEAM CATCHES THE NOTE, and it catches it HERE -- before the
    # line is written -- because the note travels on the interview answers.
    # So an identification number in "what the time was" refuses the whole
    # command and leaves no billing line behind, which is the right end of the
    # trade: the note can be retyped, and a TIN in a file that lives in
    # OneDrive and is read back every season cannot be unwritten.
    try:
        engagements.save_answers(answers, ref, store)
    except tins.TinRefused as exc:
        print(f"\n  {exc}\n\n  Nothing was written.")
        return 1

    # AND THE RECORD, WHICH IS WHAT GETS BILLED. Saving the answers alone put
    # the hour on the estimate and nowhere else: the invoice reads `LineItems`
    # and `EstimateTotal` off the RECORD, so it went on billing the old total
    # and printing "Estimated $325.00" beside it while the estimate said $550.
    # Caught by walking one client through, not by any test -- the pricing was
    # right, the command was right, and nothing carried one to the other (S28).
    priced = pricing.price(answers)
    try:
        record = engagements.load(ref, store)
    except Exception:
        record = None
    if record is not None:
        record.update(priced)
        engagements.save(record, ref, store)

    # AN HOUR BILLED IS AN HOUR WORKED. The firm on why time capture is
    # automatic at all: "i am bad at doing so." So an hour they have just told
    # the software about, in order to bill it, is not left out of the time
    # picture -- `spent` reported 0.00 stated on an engagement carrying a 1.5
    # hour cleanup line, which is the software knowing something and not
    # saying it. Recorded as STATED, not measured: a person asserted it, and
    # `spent` keeps the two apart on purpose.
    #
    # Failure here does not lose the billing. The line is already written and
    # priced; the time entry is the lesser record, and refusing the whole
    # command over it would be the tail wagging the dog.
    try:
        timelog.add(store, ref, float(hours),
                    args.note or f"{line['Service']} (billed hourly)",
                    when=worked)
    except Exception as exc:
        print(f"\n  (the hourly line is recorded; the time entry was not: "
              f"{exc})")

    print(f"\n  {line['Service']}")
    print(f"      {line['Detail']}   {line['Amount']}")
    if args.note:
        print(f"      {args.note}")
    print(f"\n  {len(work)} hourly line(s) on {ref}. "
          f"Estimate now {priced['EstimateTotal']}.")
    print("\n  The invoice will refuse to exceed this without a written "
          "reason,\n  which is what makes an estimate worth putting a number "
          "on.")
    return 0


def cmd_check(args) -> int:
    """Does this package agree with itself?

    Not the same question as `doctor`, which asks what is missing. This asks
    the harder one: everything resolved, everything rendered -- do the
    documents tell one story. The firm's ask of 26 August 2026, "show me how
    you can tell it all goes together (so i can see consistency)."
    """
    record = build_record(json.loads(Path(args.record).read_text(encoding="utf-8")))
    rendered = consistency.render_package(record, DOCUMENTS, TEMPLATE_DIR,
                                          _required_lists(), _inverse_flags())
    if not rendered:
        print("No document in the set renders from this record, so there is "
              "nothing to compare. `doctor` says what is missing.")
        return 1

    checks = consistency.report(record, rendered)
    ref = record.get("EngagementRef") or "(no reference)"
    print(f"SAT-C package agreement - {ref}\n")
    print(f"  {len(rendered)} document(s) rendered: {', '.join(sorted(rendered))}\n")

    for c in checks:
        print(f"  {'ok  ' if c.ok else 'FAIL'}  {c.name}")
        print(f"          {c.detail}")
    failed = [c for c in checks if not c.ok]
    print()
    if failed:
        print(f"  {len(failed)} of {len(checks)} disagree. A client reading two "
              f"of these documents\n  side by side would find the difference.")
        return 1
    print(f"  All {len(checks)} agree.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """The whole CLI, as a parser.

    SPLIT OUT OF `main` so something other than a person can ask it what is
    real. `procedures.py` prints command lines into the operating procedures
    and, until this existed, nothing checked them: the first command in the
    first procedure had been `from-lead --lead lead.json` since it was
    written, and `lead` is a positional -- argparse refuses the flag. The
    document promised it could not name a command that does not exist, and
    that promise covered only the NAME.

    Handing out the real parser rather than a description of it is the same
    rule as everywhere else here: one thing, asked, not two things agreeing.
    """
    p = argparse.ArgumentParser(
        prog="satc-docs", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pk = sub.add_parser("package",
                        help="every document a client signs, in one atomic write")
    pk.add_argument("--engagement", required=True)
    pk.add_argument("--store")
    pk.add_argument("--out", default="pack")
    pk.add_argument("--with-invoice", action="store_true",
                    help="include the invoice, which is not part of what is signed")
    pk.add_argument("--no-pdf", action="store_true")
    pk.add_argument("--ready", action="store_true",
                    help="also write the covering email as a .eml, addressed "
                         "and attached, for you to read and send")
    pk.set_defaults(fn=cmd_package)

    pk.add_argument("--attach", action="append", metavar="ID",
                    help="declare something going in the envelope that this "
                         "software does not render (organizer, payment-voucher, "
                         "estimate-vouchers, client-records, work-copies, "
                         "return-copies). Repeatable.")
    pk.add_argument("--force", action="store_true",
                    help="write the pack even though a pre-send check failed "
                         "(needs --reason; the override is logged)")
    pk.add_argument("--reason", default="",
                    help="why this pack is going out despite a failed check")
    pk.add_argument("--skip-render", action="store_true",
                    help="do not open the documents in a browser. Faster, and "
                         "it stops the gate proving the one thing it exists to "
                         "prove")
    pk.add_argument("--notes", action="store_true",
                    help="also print the ten advisory tenet checks. They never "
                         "block and never change the exit code")
    pay = sub.add_parser("payments",
                         help="which bills have been paid, and which have not")
    pay.add_argument("--store")
    pay.add_argument("--sandbox", action="store_true",
                     help="ask Square's test account, where no money is real")
    pay.add_argument("--check", action="store_true",
                     help="prove the payment path works, step by step, against "
                          "Square itself")
    pay.add_argument("--production", action="store_true",
                     help="with --check: use the LIVE account and a real "
                          "charge (the only thing that proves you get paid)")
    pay.add_argument("--cents", type=int, default=100,
                     help="with --check: how much the check link asks for "
                          "(default 100, i.e. $1.00)")
    pay.add_argument("--setup", action="store_true",
                     help="ask Square which locations exist, write the one you "
                          "pick into registry/payments.yaml, and offer to "
                          "remember the token")
    pay.add_argument("--no-remember", action="store_true",
                     help="with --setup: do not offer to store the token")
    pay.add_argument("--forget-token", action="store_true",
                     help="delete the remembered Square token")
    pay.set_defaults(fn=cmd_payments)

    iv = sub.add_parser("invoice", help="a priced engagement -> an invoice")
    iv.add_argument("--engagement", required=True)
    iv.add_argument("--store")
    iv.add_argument("--number", help="default: the next unused one")
    iv.add_argument("--billed", required=True,
                    help="the period this invoice BILLS, e.g. '2026 tax year'")
    iv.add_argument("--credit", action="append", metavar="LABEL=AMOUNT",
                    help="a credit, entered as what it is worth")
    iv.add_argument("--no-link", action="store_true",
                    help="do not create a payment link for this bill")
    iv.add_argument("--link", action="store_true",
                    help="create a live payment link even though --store is "
                         "not the engagement store (the default is not to)")
    iv.add_argument("--sandbox", action="store_true",
                    help="use Square's test account; no money is real")
    iv.add_argument("--variance-note",
                    help="required when the bill exceeds the estimate")
    iv.set_defaults(fn=cmd_invoice)

    la = sub.add_parser("ladder", help="are the packages sensible against the prices?")
    la.add_argument("--form", default="1040")
    la.set_defaults(fn=cmd_ladder)

    d0 = sub.add_parser("doctor", help="what is blocking a real render")
    d0.add_argument("--engagement", metavar="REF",
                    help="what blocks THIS engagement, document by document")
    d0.add_argument("--store", help="engagements directory")
    d0.set_defaults(fn=cmd_doctor)

    fl = sub.add_parser("from-lead", help="website intake payload -> record skeleton")
    fl.add_argument("lead")
    fl.add_argument("--out", default="record.json")
    fl.add_argument("--season", default=str(date.today().year - 1))
    fl.add_argument("--return-type", default="individual", dest="return_type")
    fl.add_argument("--ref", default=None, help="EngagementRef, YYYY-NNNN")
    fl.set_defaults(fn=cmd_from_lead)

    i = sub.add_parser("interview", help="run the consultation; creates the engagement")
    i.add_argument("--lead", help="website intake payload, to prefill from")
    i.add_argument("--answers", help="replay a saved answers file, no prompts")
    i.add_argument("--fee-schedule", dest="fee_schedule",
                   help="price against a different schedule than the firm's")
    i.add_argument("--override-hard-no", action="store_true",
                   dest="override_hard_no",
                   help="create the engagement despite a HARD NO flag")
    i.add_argument("--ref", help="engagement ref; allocated sequentially if omitted")
    i.add_argument("--store", help="engagements directory")
    i.set_defaults(fn=cmd_interview)

    rt = sub.add_parser("returning",
                        help="this year's interview, seeded from last year's "
                             "answers")
    rt.add_argument("--engagement", required=True,
                    help="last year's engagement reference")
    rt.add_argument("--store")
    rt.add_argument("--answers", help="replay from a saved answers file")
    rt.add_argument("--out")
    rt.add_argument("--ref")
    rt.add_argument("--override-hard-no", action="store_true")
    rt.set_defaults(fn=cmd_returning)

    cl = sub.add_parser("close",
                        help="record what was actually filed, at the end of "
                             "the engagement")
    cl.add_argument("--engagement", required=True)
    cl.add_argument("--store")
    cl.add_argument("--filed", help="answers file, instead of asking")
    cl.set_defaults(fn=cmd_close)

    rc = sub.add_parser("reconcile",
                        help="the end-of-cycle control: what we said against "
                             "what we filed")
    rc.add_argument("--engagement", help="just this one")
    rc.add_argument("--store")
    rc.add_argument("--apply", action="store_true",
                    help="move the record to match what was filed, and log "
                         "every move")
    rc.set_defaults(fn=cmd_reconcile)

    pc = sub.add_parser("procedures",
                        help="write the operating procedures from the software "
                             "that performs them")
    pc.add_argument("--check", action="store_true",
                    help="fail if the committed copy has drifted")
    pc.add_argument("--html", metavar="FILE",
                    help="also write a reading copy in the firm's house "
                         "style: one self-contained file, nothing beside it")
    pc.set_defaults(fn=cmd_procedures)

    wk = sub.add_parser("walkthrough",
                        help="write the guided walkthrough of the browser "
                             "from screens photographed by `capture.py`")
    wk.add_argument("--out", metavar="FILE",
                    default=str(ROOT / "out" / "walkthrough" /
                                "walkthrough.html"),
                    help="where to write it (one self-contained file)")
    wk.add_argument("--check", action="store_true",
                    help="fail if the committed inventory of screens has "
                         "drifted from what the registry answers for")
    wk.set_defaults(fn=cmd_walkthrough)

    evp = sub.add_parser("event",
                         help="a lifecycle event after the opening pack, and "
                              "the document it produces")
    evp.add_argument("--kind", required=True,
                     choices=sorted(lifecycle.load()),
                     help="which event")
    evp.add_argument("--engagement", required=True)
    evp.add_argument("--store")
    evp.add_argument("--out")
    evp.add_argument("--answers", help="answers file, instead of asking")
    evp.add_argument("--again", action="store_true",
                     help="ask again rather than reusing what was recorded")
    evp.add_argument("--no-pdf", action="store_true")
    evp.set_defaults(fn=cmd_event)

    rq = sub.add_parser("requote",
                        help="the work changed: price the engagement again")
    rq.add_argument("--engagement", required=True)
    rq.add_argument("--set", action="append", metavar="QUESTION=VALUE",
                    help="an interview answer that changed; repeatable. "
                         "Omit to list the answers that move money.")
    rq.add_argument("--reason",
                    help="why the price moved, in one sentence. WITHOUT THIS "
                         "NOTHING IS WRITTEN -- the plan prints and stops.")
    rq.add_argument("--store")
    rq.set_defaults(fn=cmd_requote)

    sg = sub.add_parser("sign",
                        help="who has signed what, and record one that is back")
    sg.add_argument("--engagement",
                    help="one engagement. Omit for everything still waiting.")
    sg.add_argument("--sent", metavar="HOW",
                    help="record that the pack went out, and start the clock")
    sg.add_argument("--record", metavar="DOCUMENT/FIELD",
                    help="the signature line that came back. Omit to list.")
    sg.add_argument("--on", help="the day they signed, not the day you heard")
    sg.add_argument("--how", choices=sorted(signing.MEANS),
                    help="how it reached you; the means is the evidence")
    sg.add_argument("--reference",
                    help="the envelope or request id, for a signing service")
    sg.add_argument("--store")
    sg.set_defaults(fn=cmd_sign)

    sp = sub.add_parser("spent",
                        help="what an engagement has taken, beside its budget")
    sp.add_argument("--engagement", required=True)
    sp.add_argument("--add", type=float, metavar="HOURS",
                    help="record work the software could not see, e.g. Drake")
    sp.add_argument("--what", help="what that time was — required with --add")
    sp.add_argument("--store")
    sp.set_defaults(fn=cmd_spent)

    sn = sub.add_parser("season",
                        help="what is due across every engagement, soonest first")
    sn.add_argument("--within", type=int, metavar="DAYS",
                    help="only what falls in the next DAYS. Omit for everything.")
    sn.add_argument("--today", metavar="YYYY-MM-DD",
                    help="pretend it is this day, for looking ahead")
    sn.add_argument("--store")
    sn.set_defaults(fn=cmd_season)

    e = sub.add_parser("engagements", help="list what exists")
    e.add_argument("--store")
    e.set_defaults(fn=cmd_engagements)

    r = sub.add_parser("render", help="record -> client-ready documents")
    r.add_argument("record", nargs="?", help="a record JSON; or use --engagement")
    r.add_argument("--engagement", metavar="REF", help="render a stored engagement")
    r.add_argument("--store", help="engagements directory")
    r.add_argument("--invoice", metavar="NUMBER",
                   help="which invoice to render (default: the latest raised)")
    r.add_argument("--docs", nargs="+", metavar="DOC",
                   help="default: this engagement's own opening package — the "
                        "engagement letter for its return type, the estimate, "
                        "the onboarding letter, and the records release where "
                        "there is a predecessor")
    r.add_argument("--out", default="out")
    r.add_argument("--draft", action="store_true",
                   help="render past open decisions, stamped DRAFT")
    r.add_argument("--no-pdf", action="store_true", help="HTML only")
    r.set_defaults(fn=cmd_render)

    pr = sub.add_parser("price", help="derive the fee schedule from hours x your rate")
    pr.add_argument("--rate", type=float, help="what an hour of your time is worth")
    pr.add_argument("--hours", help="a YAML of hours, keyed by the paths --list prints")
    pr.add_argument("--base-covers", dest="base_covers",
                    choices=["federal_only", "one_included"],
                    help="does the base fee cover the first state and locality?")
    pr.add_argument("--round-to", dest="round_to", type=float, default=0,
                    metavar="N", help="round each fee up to the nearest N (off by default)")
    pr.add_argument("--schedule", help="derive against a schedule other than the firm's")
    pr.add_argument("--write", metavar="PATH", help="write the result; prints to stdout otherwise")
    pr.add_argument("--list", action="store_true", help="the priceable items and what each means")
    pr.set_defaults(fn=cmd_price)

    hr = sub.add_parser("hours", help="what each price buys, in hours, at your rate")
    hr.set_defaults(fn=cmd_hours)

    d = sub.add_parser("demo", help="the whole chain end to end, in one command")
    d.add_argument("--out", default="out/demo")
    d.add_argument("--no-pdf", action="store_true")
    d.set_defaults(fn=cmd_demo)

    hy = sub.add_parser("hourly",
                        help="hourly work on an engagement, so it can be billed")
    hy.add_argument("--engagement", required=True)
    # `--for`, NOT `--on`. This flag first read `--on cleanup`, and `--on`
    # means a DATE on `sign` -- "the day they signed, not the day you heard".
    # One flag with two meanings across two commands is worse than either
    # spelling, and it collided outright the moment this command needed a date
    # of its own.
    hy.add_argument("--for", dest="situation", metavar="SITUATION",
                    help="which of the firm's hourly situations. Omit to list them.")
    hy.add_argument("--hours", type=float,
                    help="how long it took. Omit to see what the software "
                         "measured, which is a floor and not the answer.")
    hy.add_argument("--note", help="what the time was, in one line")
    hy.add_argument("--on", metavar="YYYY-MM-DD",
                    help="the day it was worked, if that is not today")
    hy.add_argument("--store")
    hy.set_defaults(fn=cmd_hourly)

    fm = sub.add_parser("forms",
                        help="do our forms eliminate work, or only claim to?")
    fm.set_defaults(fn=cmd_forms)

    ck = sub.add_parser("check",
                        help="does a rendered package agree with itself?")
    ck.add_argument("record")
    ck.set_defaults(fn=cmd_check)

    sa = sub.add_parser("sample",
                        help="rebuild the demo record from the demo answers")
    sa.set_defaults(fn=cmd_sample)

    return p


def main(argv=None) -> int:
    console.speak_utf8()
    args = build_parser().parse_args(argv)

    # TIME RECORDS ITSELF, IN ONE PLACE. The firm: "automate everything possible
    # about recording time because I am bad at doing so." Anything with a start
    # button is a chore, and a chore that does not get done is a feature that
    # reports nothing. So every command naming an engagement leaves a timestamp
    # here and nowhere else -- put it inside the commands and the next command
    # added forgets, which is the same failure by a slower route.
    #
    # BEFORE the command runs, not after: a command that refuses still took the
    # time it took, and a pack blocked by the pre-send gate is often where the
    # work actually went.
    ref = getattr(args, "engagement", None)
    if ref:
        timelog.record(Path(args.store) if getattr(args, "store", None)
                       else engagements.STORE, ref, args.cmd)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
