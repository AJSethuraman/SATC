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
import re
import shutil
import tempfile
import sys
import textwrap
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

import money as m
import engagements
import invoicing
import lifecycle
import packaging
import notes
import presend
import procedures
import fees
import intake
import interview as iv
import closeout
import consistency
import merge
import pricing
import settings as firm

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
    import os, tempfile
    exe = os.environ.get("SATC_CHROMIUM") or "/opt/pw-browsers/chromium"
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
            launch = {"executable_path": exe} if Path(exe).exists() else {}
            browser = p.chromium.launch(**launch)
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


def _stamp_draft(html: str) -> str:
    """Make a draft impossible to mistake for the real document.

    The banner goes in doc-page's `slot="header"`, which the component prints
    inside a repeating <thead> spacer -- so it lands on EVERY page, not just
    the first. That matters: page two of an unstamped draft is byte-identical
    to page two of the real letter, and page two is what gets handed across a
    desk on its own.
    """
    html = html.replace("</head>", _DRAFT_CSS + "</head>", 1)
    # after the opening <doc-page ...> tag, so the component owns it
    html = re.sub(r"(<doc-page\b[^>]*>)", r"\1\n" + _BANNER, html, count=1)
    # highlight every decision nobody has made yet
    return re.sub(r"(\[CONFIRM:[^\]]*\])",
                  r'<span class="satc-open-decision">\1</span>', html)


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
    """The engagement ref of a pack this command wrote here before, or None.

    None means either an empty/absent directory or one we do not recognise --
    the caller tells those apart, because they need different answers.
    """
    book = outdir / "MANIFEST.json"
    if not book.is_file():
        return None
    try:
        return json.loads(book.read_text(encoding="utf-8")).get(
            "EngagementRef") or "an earlier engagement"
    except (OSError, ValueError):
        return "an earlier engagement"


def cmd_package(args) -> int:
    """Every document a client signs, in one atomic write.

    ATOMIC is the point and it is why this does not just loop `_render_one`
    into the output directory. An engagement letter without its fee estimate
    asks somebody to sign for work at a price they have not been shown; a pack
    with a hole in it is worse than no pack at all. So everything is rendered
    to a temporary directory first, and the output directory is only touched
    once every document has succeeded.
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
    # WHOSE DIRECTORY IS THIS? Found by testing the refusal path: a run that
    # refuses leaves whatever was already in `--out` untouched, so a complete
    # pack from a DIFFERENT engagement sits there looking current, and the
    # person who reads "No pack written" and then opens the folder finds one.
    # That is the failure this command exists to prevent, arriving by the
    # back door.
    #
    # So the pack owns its directory. A folder we wrote before (it has our
    # MANIFEST) is replaced wholesale. A folder with anything else in it is
    # somebody's, and we do not touch it.
    stale = _previous_pack(outdir)
    if stale is None and outdir.exists() and any(outdir.iterdir()):
        print(f"\n{outdir} already has files in it and no MANIFEST.json, so it "
              f"is not a pack this\ncommand wrote. Refusing to mix a signing "
              f"pack into somebody else's folder —\ngive --out a new directory.\n")
        return 1

    staging = Path(tempfile.mkdtemp(prefix="satc-pack-"))
    written: dict[str, list[Path]] = {}
    refused: list[tuple[str, str]] = []
    try:
        rendered: dict[str, str] = {}
        for doc in docs:
            try:
                result, files = _render_one(doc, record, staging, False, want_pdf)
                written[doc] = files
                rendered[doc] = result.html
            except merge.MergeError as exc:
                refused.append((doc, str(exc)))

        if refused:
            print(f"\nNo pack written. {len(refused)} of {len(docs)} document(s) "
                  f"refused, and a pack with a hole in it is worse than none —\n"
                  f"the client signs what arrived and the rest turns up later "
                  f"saying something different.\n")
            for doc, why in refused:
                print(f"  {DOCUMENTS[doc][1]}")
                for line in textwrap.wrap(why, 74):
                    print(f"      {line}")
                print()
            if stale:
                print(f"  WARNING: {outdir} still holds the pack written for "
                      f"{stale}.\n           It is not this engagement's and it "
                      f"has not been updated. Do not send it.\n")
            return 1

        # THE HTML IS NOT SELF-CONTAINED. Every template links `satc-doc.css`
        # and `doc-page.js` by relative path, so a pack folder holding only
        # HTML opens as UNSTYLED PLAIN TEXT -- the whole document, no masthead,
        # no rules, no layout. With --no-pdf that is the entire deliverable.
        #
        # Found by the firm, opening one: "these html files are plain text?"
        # Nothing caught it because every test reads the HTML as a STRING and
        # asserts on its tokens, which is exactly right for a merge and blind
        # to whether the thing renders.
        #
        # The two assets are copied beside the documents rather than inlined:
        # inlining bloats every file with the same 12 KB and diverges from how
        # the templates are authored. They go into STAGING, before the gate --
        # a gate that inspects a pack the assets have not reached yet would
        # fail every time for the wrong reason.
        for asset in presend.PACK_ASSETS:
            src = TEMPLATE_DIR / asset
            if src.exists():
                shutil.copy2(src, staging / asset)

        # THE MANIFEST GOES IN BEFORE THE GATE, NOT AFTER, and until this line
        # existed two of the eight blocking checks had never examined anything
        # on a real send.
        #
        # A rendered document is named for the client, so nothing about the
        # file on disk says which template it came from. The manifest is the
        # only thing that knows -- so `compliance_floor` (the assurance
        # negation, the "an extension is not more time to pay" warning) and
        # `pointer_test` (the enclosure check the firm asked for by name) both
        # need it and both refuse without it. It used to be written at the very
        # end, from the output directory, which meant every real `package` run
        # gated a folder that had no manifest in it: both checks returned "no
        # MANIFEST.json ... Not a pass", nothing blocked, and the summary line
        # said `ok`. They passed in the tests, on fixtures that wrote their own
        # manifest, and examined ZERO on every pack ever sent.
        #
        # Found by making every check report its denominator (SOFTWARE-TENETS
        # S2) -- which is the whole argument for the denominator.
        book = packaging.manifest(record, docs, written,
                                  getattr(args, "attach", None))
        manifest_json = json.dumps(book, indent=2, ensure_ascii=False) + "\n"
        (staging / "MANIFEST.json").write_text(manifest_json, encoding="utf-8")

        # THE GATE. The firm's choice, 27 August 2026: blocking, with a logged
        # override. Nothing has been written to `outdir` yet, so a refusal here
        # costs nothing and leaves no half-pack behind.
        check = presend.gate(staging, record, rendered=rendered,
                             skip_render=getattr(args, "skip_render", False))
        print(f"\nBefore sending — {len(check.checked)} check(s):")
        print(presend.format_result(check))

        # THE ADVISORY HALF, AND IT IS OPT-IN. The firm's rule: exact tenets
        # block, judgement ones advise. An advisory printed beside a blocking
        # failure every single time is an advisory people learn to scroll past,
        # and they take the eight real gates with them (SOFTWARE-TENETS S4).
        # `--notes` is for the round where somebody is reading the prose.
        if getattr(args, "notes", False):
            read = notes.review(staging)
            print(f"\nReadings — {len(read)} advisory check(s), none of which "
                  f"can stop a pack:")
            print(notes.format_notes(read))

        force = getattr(args, "force", False)
        if check.blocking and not force:
            print(f"\nNo pack written. {len(check.blocking)} check(s) failed, "
                  f"and a pack that does not\nsurvive being opened is not a "
                  f"pack — it is a folder the client cannot read.\n"
                  f"\n  Fix it, or send anyway with --force and a reason:\n"
                  f"      --force --reason \"why this is going out as it is\"\n")
            return 1

        if check.blocking and force:
            reason = (getattr(args, "reason", "") or "").strip()
            if not reason:
                print("\n--force needs --reason. An override with no recorded "
                      "reason is just a\nquieter way to send a pack that did "
                      "not pass.\n")
                return 1
            ref = record.get("EngagementRef") or args.engagement
            entry = {
                "at": _dt.datetime.now(_dt.timezone.utc)
                      .replace(microsecond=0).isoformat(),
                "command": "package",
                "reason": reason,
                "failed": [{"check": f.check, "document": f.document,
                            "detail": f.detail} for f in check.blocking],
            }
            try:
                logged = engagements.record_override(ref, entry, store)
                print(f"\n  Override recorded — {logged}")
            except Exception as exc:                        # noqa: BLE001
                # Refuse rather than send unlogged. The override IS the record;
                # forcing past a gate with no trace is the thing this design
                # exists to prevent.
                print(f"\nCould not record the override ({exc}), so the pack "
                      f"was not written.\nThe log is the only thing that makes "
                      f"--force different from no gate at all.\n")
                return 1

        # Replace, do not merge. An entity pack written over an individual
        # one would leave two engagement letters in the folder, and whoever
        # sends it picks the wrong one.
        if stale is not None and outdir.exists():
            for old_file in outdir.iterdir():
                if old_file.is_file():
                    old_file.unlink()
        outdir.mkdir(parents=True, exist_ok=True)
        moved: dict[str, list[Path]] = {}
        for doc, files in written.items():
            moved[doc] = [Path(shutil.copy2(f, outdir / f.name)) for f in files]
        for asset in presend.PACK_ASSETS:
            staged = staging / asset
            if staged.exists():
                shutil.copy2(staged, outdir / asset)

        # THE HTML IS NOT SELF-CONTAINED, and until 27 August 2026 the pack
        # did not carry what it needs. Every template links `satc-doc.css` and
        # `doc-page.js` by relative path, so a pack folder holding only HTML
        # opens as UNSTYLED PLAIN TEXT -- the whole document, no masthead, no
        # rules, no layout. With --no-pdf that is the entire deliverable.
        #
        # Found by the firm, opening one: "these html files are plain text?"
        # Nothing caught it because every test reads the HTML as a STRING and
        # asserts on its tokens, which is exactly right for a merge and blind
        # to whether the thing renders.
        #
        # The two assets are copied beside the documents rather than inlined:
        # inlining bloats every file with the same 12 KB and diverges from how
        # the templates are authored. A single HTML file mailed on its own
        # still needs its siblings -- which is what the PDF is for, and why it
        # is the default.

        # The SAME manifest the gate read, byte for byte. Rebuilding it here
        # from `moved` would be a second construction of a thing that must
        # agree with the first (S3) -- and the one the client gets would be the
        # one nothing checked.
        (outdir / "MANIFEST.json").write_text(manifest_json, encoding="utf-8")
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    print(f"\nSigning pack for {record.get('EngagementRef') or args.engagement}"
          f" — {record.get('ClientFullName', '')}")
    print(f"    {outdir}\n")
    for doc in docs:
        print(f"  {DOCUMENTS[doc][1]}")
        print(f"      {packaging.PURPOSE.get(doc, '')}")
    print(f"\n  Estimate  {record.get('EstimateTotal', '(none)')}")
    print(f"  Manifest  {outdir / 'MANIFEST.json'}")
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

    try:
        fields = invoicing.build(record, number=number, billed=args.billed,
                                 credits=credits,
                                 variance_note=args.variance_note or "")
    except invoicing.InvoiceError as exc:
        print(f"\n{exc}\n")
        return 1

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
    print(f"\nNext:  python cli.py render --engagement {args.engagement} "
          f"--docs invoice --out out")
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
        "LetterDate": date.today().strftime("%B %-d, %Y"),
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


def _ask(section: dict, q: dict, default) -> object:
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
        hint = (f"website said: {default!r} -- enter to accept, '-' to clear"
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
    session = iv.Interview(lead=lead, carried=carried)

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
                         carried.get(q["id"], iv.prefill_for(q, lead)))
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


def _render_one(doc: str, record: dict, outdir: Path, draft: bool, want_pdf: bool):
    filename, _ = DOCUMENTS[doc]
    template = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
    result = merge.render(template, record, strict=not draft,
                          required_lists=_required_lists().get(doc, ()),
                          inverse_flags=_inverse_flags())

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
        if "invoice" in (args.docs or ()):
            bill = invoicing.find(store, args.engagement,
                                  getattr(args, "invoice", None))
            if bill is None:
                print(f"engagement {args.engagement} has no invoice yet. Raise "
                      f"one first:\n  python cli.py invoice --engagement "
                      f"{args.engagement} --billed 'March 2027'\n")
                return 1
            raw = {**raw, **bill}
            print(f"  invoice {bill.get('InvoiceNumber', '')}\n")
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
            result, written = _render_one(doc, record, outdir, args.draft, want_pdf)
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


def main(argv=None) -> int:
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
    iv = sub.add_parser("invoice", help="a priced engagement -> an invoice")
    iv.add_argument("--engagement", required=True)
    iv.add_argument("--store")
    iv.add_argument("--number", help="default: the next unused one")
    iv.add_argument("--billed", required=True,
                    help="the period this invoice BILLS, e.g. '2026 tax year'")
    iv.add_argument("--credit", action="append", metavar="LABEL=AMOUNT",
                    help="a credit, entered as what it is worth")
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
    pc.set_defaults(fn=cmd_procedures)

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

    ck = sub.add_parser("check",
                        help="does a rendered package agree with itself?")
    ck.add_argument("record")
    ck.set_defaults(fn=cmd_check)

    sa = sub.add_parser("sample",
                        help="rebuild the demo record from the demo answers")
    sa.set_defaults(fn=cmd_sample)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
