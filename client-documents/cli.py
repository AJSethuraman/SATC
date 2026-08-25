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
import json
import re
import sys
import textwrap
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

import engagements
import fees
import intake
import interview as iv
import merge
import pricing
import settings as firm

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT.parent / "satc-handoff" / "04-TEMPLATES"

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
}

# The three that go out together. Named because generating them in one call is
# the reason they cannot disagree about the date, the ref or the address.
OPENING_PACKAGE = ["tax-letter", "fee-estimate", "onboarding-letter"]

# When in an engagement's life a document becomes due. Readiness is only
# meaningful against a stage: a disengagement letter that cannot render at
# engagement creation is not blocked, it is not due, and reporting the two the
# same way buries the one that matters.
STAGE = {
    "tax-letter": "opening", "business-letter": "opening",
    "bookkeeping-letter": "opening", "fee-estimate": "opening",
    "onboarding-letter": "opening", "organizer-letter": "opening",
    "extension-notice": "in flight",
    "delivery-letter": "delivery", "invoice": "delivery",
    "disengagement-letter": "ending",
}

# Which opening document an engagement actually uses, by return type. The rest
# belong to a different engagement and are not this one's business.
OPENING_BY_RETURN = {
    "individual": "tax-letter", "s_corp": "business-letter",
    "partnership": "business-letter", "c_corp": "business-letter",
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
    # A temp file rather than set_content, so relative links (satc-doc.css,
    # doc-page.js) resolve exactly as they do when the template is opened.
    with tempfile.NamedTemporaryFile("w", suffix=".html", dir=base,
                                     encoding="utf-8", delete=False) as fh:
        fh.write(html)
        tmp = Path(fh.name)
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
        tmp.unlink(missing_ok=True)


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
    relevant = [d for d in DOCUMENTS
                if STAGE[d] != "opening" or d == letter
                or d in ("fee-estimate", "onboarding-letter", "organizer-letter")]

    ready, blocked = [], {}
    for doc in relevant:
        template = (TEMPLATE_DIR / DOCUMENTS[doc][0]).read_text(encoding="utf-8")
        try:
            merge.render(template, record)
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

    if not decisions and not unpriced:
        print("\n  No open decisions. Real renders will produce documents.")
        return 0
    if not decisions:
        return 1

    print(f"\n  {len(decisions)} open decision(s) block every REAL render.")
    print("  Each is a question only a human can answer. Edit "
          "registry/firm-settings.yaml.\n")
    for path, q in decisions:
        print(f"    {path}\n        {q}\n")
    print("  Until then, use --draft to exercise the pipeline end to end.")
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
        "ClientFullName": todo,
        "ClientLetterName": contact.get("name") or todo,
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
    session = iv.Interview(lead=lead)

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
            value = _ask(section, q, iv.prefill_for(q, lead))
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


def _render_one(doc: str, record: dict, outdir: Path, draft: bool, want_pdf: bool):
    filename, _ = DOCUMENTS[doc]
    template = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
    result = merge.render(template, record, strict=not draft,
                          required_lists=_required_lists().get(doc, ()))

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
    elif args.record:
        raw = json.loads(Path(args.record).read_text(encoding="utf-8"))
    else:
        raise SystemExit("give a record file or --engagement REF")
    record = build_record(raw)

    docs = args.docs or OPENING_PACKAGE
    unknown = [d for d in docs if d not in DOCUMENTS]
    if unknown:
        raise SystemExit(f"unknown document(s): {', '.join(unknown)}\n"
                         f"known: {', '.join(sorted(DOCUMENTS))}")

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

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

    record = str(ROOT / "samples" / "tax-opening-package.json")
    common = dict(record=record, docs=OPENING_PACKAGE, out=str(outdir),
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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="satc-docs", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

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

    e = sub.add_parser("engagements", help="list what exists")
    e.add_argument("--store")
    e.set_defaults(fn=cmd_engagements)

    r = sub.add_parser("render", help="record -> client-ready documents")
    r.add_argument("record", nargs="?", help="a record JSON; or use --engagement")
    r.add_argument("--engagement", metavar="REF", help="render a stored engagement")
    r.add_argument("--store", help="engagements directory")
    r.add_argument("--docs", nargs="+", metavar="DOC",
                   help=f"default: the opening package ({', '.join(OPENING_PACKAGE)})")
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

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
