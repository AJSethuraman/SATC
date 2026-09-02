"""The operating procedures, generated from the software that performs them.

THE FIRM ASKED FOR THESE: "i will eventually want operating procedures and
stuff so it's integral everything works and can be demonstrated."

They are GENERATED, and that is the whole point. Every step below is read out
of the code that would run it -- the CLI's own subparsers, `packaging.PACKS`,
`presend.gate`, `closeout.questions_for` -- so this document

  * cannot describe a command that does not exist,
  * cannot list a document a return type does not get,
  * cannot claim a check the gate does not perform,
  * and cannot go stale, because `procedures --check` regenerates it and fails
    when the committed copy differs.

The same shape as `website/pricing.spec.py`, and for the same reason: a
procedure written by hand beside software is a procedure that is wrong within
a month, and nobody finds out until somebody follows it.

WHAT IS NOT GENERATED is the judgement -- when to decline work, whether a
divergence means the return changed or the interview was wrong. That belongs
to a person, and the places it does are marked rather than filled in.
"""

from __future__ import annotations

import inspect
import re
from functools import lru_cache
from pathlib import Path

import closeout
import packaging
import presend

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "docs" / "OPERATING-PROCEDURES.md"

# The four kinds of engagement, in the order a practice meets them.
RETURN_TYPES = [
    ("individual", "An individual", "1040"),
    ("partnership", "A partnership", "1065"),
    ("s_corp", "An S corporation", "1120S"),
    ("c_corp", "A C corporation", "1120"),
]


def commands() -> list[str]:
    """Every subcommand the CLI actually offers, read from its own parser.

    ASKED, NOT READ. This used to scrape `add_parser("...")` out of
    `inspect.getsource(cli.main)`, which broke silently the moment the parser
    moved into `build_parser` -- and would have broken the same way for any
    refactor, or for a subcommand added through a helper. Worse, it read the
    file from disk, so editing `cli.py` while the suite ran made every
    procedures test fail for a reason that had nothing to do with them.

    The parser is now handed out, so this asks it.
    """
    import cli
    choices = cli.build_parser()._subparsers._group_actions[0].choices
    return list(choices)


def invocations(text: str) -> list[str]:
    """Every `python cli.py ...` invocation the document prints.

    Continuation lines are joined: the document wraps long commands with a
    trailing backslash, exactly as a person would type them, and checking the
    first half alone would pass a command whose second half is wrong.
    """
    out: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("python cli.py "):
            while line.endswith("\\") and i + 1 < len(lines):
                i += 1
                line = line[:-1].rstrip() + " " + lines[i].strip()
            out.append(line)
        i += 1
    return out


def unrunnable(text: str | None = None) -> list[str]:
    """Every command line in the document that argparse would refuse.

    WHY THIS EXISTS, and it is the whole lesson of this file. `_require`
    below checks that a command NAME exists, and the document's own preamble
    then promises it "cannot name a command that does not exist". True of
    names. Every FLAG, argument and value in every code block was typed by
    hand into `render()` and checked by nothing -- so the first command in the
    first procedure, `from-lead --lead lead.json`, had been wrong since it was
    written: `lead` is a positional and argparse refuses the flag outright. A
    new preparer's first act failed, on the front page, under a guarantee that
    it could not.

    That is this repository's own recurring bug shape, relocated one layer up:
    a claim in one place, the behaviour in another, and nothing comparing them
    (S31). This is the thing that compares them. It parses each line the
    document prints with the real parser, in a mode that raises instead of
    exiting, and reports what would not run.

    Values are replaced with harmless stand-ins before parsing: the point is
    the SHAPE of the invocation -- which flags exist, what takes an argument,
    what is positional -- not whether a file named lead.json is on this disk.
    """
    import argparse
    import shlex
    import cli

    text = text if text is not None else render()
    problems: list[str] = []

    parser = _quiet_parser()
    for line in invocations(text):
        # Placeholders go FIRST, before the shell split: the document writes
        # things like `<LAST YEAR'S REF>`, and an apostrophe inside one makes
        # `shlex` read the rest of the line as a quoted string.
        body = re.sub(r"<[^>]+>", "PLACEHOLDER",
                      line.replace("python cli.py ", "", 1))
        argv = shlex.split(body)
        if "#" in argv:
            argv = argv[:argv.index("#")]
        argv = [a for a in argv if not a.startswith("#")]
        # Optional pieces are written `[--within 21]`; the document means "you
        # may add this", so it is checked as though it were there.
        argv = [a.strip("[]") for a in argv if a.strip("[]")]
        try:
            parser.parse_args(argv)
        except _ParserRefused as exc:
            problems.append(f"{line}\n      -> {exc}")
    return problems


class _ParserRefused(Exception):
    pass


def _stand_in(arg: str) -> str:
    """A placeholder the document prints, replaced with something parseable."""
    if arg.startswith("<") and arg.endswith(">"):
        return "PLACEHOLDER"
    return arg


def _quiet_parser():
    """The CLI's own parser, made to raise instead of exiting.

    `cli.build_parser()` is the real thing a person meets -- not a description
    of it -- so this cannot drift from what actually runs.
    """
    import cli

    parser = cli.build_parser()

    def refuse(message):
        raise _ParserRefused(message)

    def stop(status=0, message=None):
        if status:
            raise _ParserRefused(message or f"exit {status}")

    for target in [parser] + list(
            parser._subparsers._group_actions[0].choices.values()):
        target.error = refuse
        target.exit = stop
    return parser


def _carry_count() -> int:
    """How many answers can carry from last year, asked of the list itself."""
    import interview
    return len(interview.CARRIES)


def _require(name: str) -> str:
    """Fail loudly if a procedure names a command that has been renamed."""
    if name not in commands():
        raise RuntimeError(
            f"the procedures name `{name}`, which the CLI no longer offers. "
            f"Either the command was renamed or the procedure is wrong; a "
            f"document that tells someone to run a command that does not "
            f"exist is worse than no document.")
    return name


def gate_checks() -> list[str]:
    """What the pre-send gate verifies, from the gate itself."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        # An empty directory: nothing to find, so nothing fails, and what comes
        # back is the list of checks rather than a list of findings.
        result = presend.gate(Path(tmp), {}, rendered=None, skip_render=False)

    # The names are the gate's own, verbatim, so a check renamed in `presend`
    # is renamed here without anybody remembering to. (The gate used to append
    # a count to one of them -- "every document opens and renders (3)" -- and
    # this function stripped the bracket; the count now lives in the gate's
    # REPORT rather than in the check's name, so there is nothing to strip.)
    #
    # A skipped check is named as skipped rather than dropped: a procedure that
    # lists only what ran reads like a procedure where everything ran.
    return list(result.checked) + [
        f"{s} — only when the caller supplies the rendered text"
        for s in result.skipped]


def advisory_checks() -> list[str]:
    """What `--notes` reads, from the advisory register itself.

    Listed separately and said to be advisory, because the difference is the
    whole design: these ten never stop a pack. A procedure that ran them
    together with the blocking eight would teach a preparer that a note is a
    failure, and the next thing that happens is that the eight get ignored too.
    """
    import notes as _notes
    return [f"{a.key} ({a.tenet}) — {a.what}" for a in _notes.ADVISORIES]


# ── every template belongs to a procedure ─────────────────────────────────
#
# THE FIRM'S GENERAL RULE, 2 September 2026:
#
#     "each relevant template is included as an appendix item to the process
#      it belongs to (this is a general rule)"
#
# DERIVED, NEVER TYPED. Which documents a procedure produces is already stated
# by the software -- `packaging.PACKS` for the opening pack, `lifecycle.yaml`
# for the events, the invoice command for the invoice -- so this reads those
# rather than restating them. A typed list beside them would be a second claim
# about the same fact with nothing comparing the two, which is how the pack and
# the renderer disagreed for a fortnight (see cli.opening_package).
#
# AND IT IS CHECKED BOTH WAYS. `template_audit` reports templates that belong
# to no procedure AND procedures that name a template which does not exist. One
# direction alone passes trivially: a document set with no procedures has no
# orphans.

APPENDIX_TITLE = "Appendix"


def templates_by_procedure() -> dict[str, list[str]]:
    """Which document ids each numbered procedure produces, in reading order."""
    import packaging
    import lifecycle

    opening: list[str] = []
    for docs in packaging.PACKS.values():
        for doc in docs:
            if doc not in opening:
                opening.append(doc)
    # Documents that ride along for the clients they apply to -- the records
    # release travels only when there is a predecessor firm. Conditional is
    # still "belongs to this procedure": the appendix says when.
    for doc in packaging.CONDITIONAL:
        if doc not in opening:
            opening.append(doc)

    events = lifecycle.load()
    by_event = {kind: event.document
                for kind, event in events.items() if event.document}

    # `sign` PRODUCES NOTHING. It reads signature blocks out of templates that
    # already exist and writes `signatures.json`. This entry used to be a
    # hardcoded `("delivery-letter",)` -- in the function whose own comment
    # above says DERIVED, NEVER TYPED -- so section 4 carried an appendix for
    # a document it does not produce, and the delivery letter appeared twice
    # in the index: once against a procedure that does not make it, and once
    # against the lifecycle event that does.
    out = {
        "Sending the opening pack": opening,
        # `requote` re-prices and re-writes the estimate; `invoice` writes the
        # invoice. Both read from the command's own `--docs`/render path, so
        # these two are the one place a typed name is unavoidable -- and they
        # are asserted against `document_files()` so a rename cannot pass.
        "When the work changes, and the price with it":
            [d for d in ("fee-estimate",) if d in document_files()],
        "Billing": [d for d in ("invoice",) if d in document_files()],
    }
    for kind, doc in sorted(by_event.items()):
        out[f"When {_event_title(kind)}"] = [doc]
    return {k: v for k, v in out.items() if v}


def _events():
    """The lifecycle events, loaded once."""
    import lifecycle
    return lifecycle.load()


def _event_title(kind: str) -> str:
    """A lifecycle event, named the way a procedure heading names it."""
    return {
        "delivery": "the return is ready to go back",
        "organizer": "you send the organizer",
        "extension": "the return needs an extension",
        "disengagement": "an engagement has to end",
    }.get(kind, kind)


@lru_cache(maxsize=1)
def document_files() -> dict[str, tuple[str, str]]:
    """`{id: (filename, label)}`, read from the CLI's own map.

    LAZY, because `cli` imports this module: reading it at import time made a
    circular import that only bit when a test imported `procedures` first.
    """
    import cli
    return dict(cli.DOCUMENTS)


def template_audit(template_dir: Path | None = None) -> dict:
    """Both directions, each with its denominator (S2).

    `orphans`  templates on disk that no procedure claims.
    `missing`  documents a procedure produces whose template is not there.
    `examined` how many of each was looked at, because "no orphans" across
               zero templates is not the same report as "no orphans" across
               twelve.
    """
    template_dir = Path(template_dir or ROOT.parent / "satc-handoff" / "04-TEMPLATES")
    on_disk = {p.name for p in template_dir.glob("*.html")
               if not p.name.startswith("_")}

    claimed_ids = {d for docs in templates_by_procedure().values() for d in docs}
    claimed_files, missing = set(), []
    for doc in sorted(claimed_ids):
        entry = document_files().get(doc)
        if entry is None:
            missing.append(f"{doc} (no template is registered for it)")
            continue
        filename = entry[0]
        claimed_files.add(filename)
        if filename not in on_disk:
            missing.append(f"{doc} -> {filename} (not in {template_dir.name})")

    return {
        "orphans": sorted(on_disk - claimed_files),
        "missing": missing,
        "templates_examined": len(on_disk),
        "documents_examined": len(claimed_ids),
    }


def _appendix(add, procedure: str) -> None:
    """The templates this procedure produces, as its own appendix item.

    The firm's general rule, 2 September 2026: "each relevant template is
    included as an appendix item to the process it belongs to". A procedure
    that tells somebody to send a document and does not say which document is
    a procedure they have to already know the answer to.
    """
    docs = templates_by_procedure().get(procedure) or []
    if not docs:
        return
    # NAMED WHEN THE SECTION HOLDS MORE THAN ONE. Section 7 carries four
    # events, and four consecutive headings all reading "Appendix — the
    # documents this produces" tell a reader nothing about which is which.
    if procedure.startswith("When ") and procedure not in (
            "When the work changes, and the price with it",):
        add(f"### {APPENDIX_TITLE} — {procedure[0].lower() + procedure[1:]}")
    else:
        add(f"### {APPENDIX_TITLE} — the documents this produces")
    add("")
    for doc in docs:
        entry = document_files().get(doc)
        if entry is None:
            add(f"- `{doc}` — **no template is registered for this.**")
            continue
        filename, label = entry
        when = ""
        if doc in _conditional_docs():
            when = f" — only when `{_conditional_docs()[doc]}` is set on the record"
        add(f"- **{label}** — `satc-handoff/04-TEMPLATES/{filename}`{when}")
    add("")


def _conditional_docs() -> dict[str, str]:
    import packaging
    return dict(packaging.CONDITIONAL)


def render() -> str:
    """The document."""
    lines: list[str] = []
    add = lines.append

    add("# SATC — operating procedures")
    add("")
    add("> **GENERATED. Do not edit this file.**")
    add(">")
    add("> Every step below is read out of the code that performs it — the")
    add("> CLI's own subparsers, `packaging.PACKS`, `presend.gate`,")
    add("> `closeout.questions_for`. It cannot name a command that does not")
    add("> exist, list a document a return type does not get, or claim a check")
    add("> the gate does not perform.")
    add(">")
    add("> Regenerate with `cd client-documents && python cli.py procedures`.")
    add("> `python cli.py procedures --check` fails when the committed copy has")
    add("> drifted, and runs in the suite, so a procedure cannot quietly stop")
    add("> being true.")
    add("")
    add("A procedure written by hand beside software is wrong within a month,")
    add("and nobody finds out until somebody follows it.")
    add("")

    # ── 0 · the season ────────────────────────────────────────────────────
    add("## The screen to open first")
    add("")
    add("```")
    add(f"python cli.py {_require('season')} [--within 21]")
    add("```")
    add("")
    add("What is due across every engagement, soonest first, overdue at the")
    add("top. Everything else in this document acts on ONE engagement; this is")
    add("the only thing that looks at the whole book.")
    add("")
    add("The dates are not typed in anywhere. They are derived from the statute")
    add("— IRC 6072 for the month, IRC 7503 for the shift off a weekend or a")
    add("legal holiday, and DC Emancipation Day, which is why the 2017 and 2022")
    add("individual deadlines were both 18 April. The date a client's papers")
    add("are due is the filing date minus `MATERIALS_LEAD_DAYS`, currently 21.")
    add("")
    add("> **It says what it could not place.** An engagement whose federal")
    add("> form or tax year cannot be read has an UNKNOWN deadline, and it is")
    add("> named at the bottom rather than left off — a board that quietly")
    add("> drops what it could not read says the season is quieter than it is.")
    add("")

    # ── 1 · taking on a client ────────────────────────────────────────────
    add("## 1 · Taking on a new client")
    add("")
    add("```")
    # `lead` is POSITIONAL. This line read `--lead lead.json` from the day it
    # was written and argparse refused it -- the first command in the first
    # procedure, under a preamble promising the document could not name a
    # command that does not exist. `unrunnable()` now parses every line here
    # with the real parser, so a wrong flag cannot ship again.
    add(f"python cli.py {_require('from-lead')} lead.json --out record.json")
    add(f"python cli.py {_require('interview')}")
    add("```")
    add("")
    add("The website lead is a **claim**, not a fact: every prefilled answer is")
    add("still asked. The interview decides whether to take the work, prices it,")
    add("and creates the engagement — all in `intake.finish`, which the web and")
    add("CLI front doors share, so neither can lose a gate the other keeps.")
    add("")
    add("It refuses in three ways, each of them deliberate:")
    add("")
    add("- **work the firm does not take** — the hard-no list in")
    add("  `firm-settings.yaml`, refused before anything is composed;")
    add("- **a decision that is not yes** — nothing is created;")
    add("- **an unfinished interview** — a required question left unanswered")
    add("  stops the engagement, because creating it anyway puts the hole in a")
    add("  document instead, where a client finds it.")
    add("")
    add("> **Judgement, not procedure:** whether to override a hard-no. The")
    add("> option exists and it is recorded on the outcome. Use it when the list")
    add("> is wrong, not because this one feels like an exception.")
    add("")

    # ── 2 · the opening pack ──────────────────────────────────────────────
    add("## 2 · Sending the opening pack")
    add("")
    add("```")
    add(f"python cli.py {_require('doctor')} --engagement <REF>")
    add(f"python cli.py {_require('package')} --engagement <REF> --out packs/<REF>")
    add("```")
    add("")
    add("`doctor` says what is missing before you try. `package` is **atomic**:")
    add("every document is rendered to a temporary directory first, and the")
    add("output folder is only touched once all of them have succeeded. A pack")
    add("with a hole in it is worse than no pack at all — somebody signs what")
    add("arrived and the rest turns up later saying something different.")
    add("")
    add("What each kind of engagement is sent:")
    add("")
    add("| Engagement | Documents in the opening pack |")
    add("|---|---|")
    for key, label, form in RETURN_TYPES:
        docs = packaging.documents_for({"_return_type": key})
        add(f"| {label} ({form}) | {', '.join(f'`{d}`' for d in docs)} |")
    add("")
    conditional = ", ".join(f"`{d}` when `{flag}`"
                            for d, flag in packaging.CONDITIONAL.items())
    add(f"And conditionally: {conditional}.")
    add("")

    # ── 3 · the gate ──────────────────────────────────────────────────────
    _appendix(add, "Sending the opening pack")
    add("## 3 · What the pre-send gate checks")
    add("")
    add("`package` runs these before it writes anything. Nothing has reached the")
    add("output directory yet, so a refusal costs nothing and leaves no half-pack")
    add("behind.")
    add("")
    for check in gate_checks():
        add(f"- {check}")
    add("")
    add("**Blocking, with a logged override.** A gate with no override will one")
    add("day stop a return going out at eleven at night and there will be nothing")
    add("to do about it; a gate that can be waved through silently is not a gate.")
    add("")
    add("```")
    add("python cli.py package --engagement <REF> --out packs/<REF> \\")
    add('    --force --reason "why this is going out as it is"')
    add("```")
    add("")
    add("`--force` needs `--reason`. What failed and why it was overridden are")
    add("appended to the engagement's own `overrides.json` — append-only, because")
    add("a log you can edit is not evidence. If the log cannot be written, the")
    add("pack is not written either.")
    add("")
    add("**Every check above reports how many things it examined.** A check with")
    add("nothing to look at prints `NONE`, never `ok`: on an opening pack there")
    add("is no cited clause to resolve, and for a while that printed as a pass.")
    add("")
    add("### The readings — `package --notes`")
    add("")
    add("Ten more checks that **never block and never change the exit code**.")
    add("They are the tenets a machine can only guess at, and each is promoted")
    add("to blocking only after a full cycle with no false positive.")
    add("")
    for check in advisory_checks():
        add(f"- {check}")
    add("")
    add("Run them on the round where somebody is reading the prose, not on every")
    add("send. An advisory printed beside a real failure every time is an")
    add("advisory people learn to scroll past — and they take the blocking")
    add("checks with them.")
    add("")
    add("Where a document promises something this software does not render —")
    add("an organizer, a payment voucher — declare it:")
    add("")
    add("```")
    add("python cli.py package --engagement <REF> --out packs/<REF> \\")
    for aid in sorted(packaging.ATTACHMENTS):
        add(f"    --attach {aid} \\")
    add("    # (only the ones actually going in the envelope)")
    add("```")
    add("")

    # ── 4 · the signature ─────────────────────────────────────────────────
    add("## 4 · Getting it signed")
    add("")
    add("```")
    add(f"python cli.py {_require('sign')}"
        "                             # everyone still waiting")
    add(f"python cli.py {_require('sign')} --engagement <REF>")
    add(f"python cli.py {_require('sign')} --engagement <REF> --sent encyro")
    add(f"python cli.py {_require('sign')} --engagement <REF> \\")
    add("    --record tax-letter/TaxpayerName \\")
    add("    --on '<the day THEY signed>' --how in-person")
    add("```")
    add("")
    add("**Run with no engagement, it is the morning list** — every client")
    add("still waiting, longest first, with the overdue at the top. That is")
    add("the half worth automating: sending a pack is three minutes of")
    add("clicking, and knowing who has not signed is what nothing supported.")
    add("")
    add("**Record that it went out.** Until you do, \"outstanding\" only means")
    add("nobody has signed yet — which on the morning you built the pack is")
    add("not a chase. `--sent` starts the clock, and re-sending restarts it.")
    add("")
    add("### Getting it to them")
    add("")
    add("```")
    add(f"python cli.py {_require('package')} --engagement <REF> "
        "--out packs/<REF> --ready")
    add("```")
    add("")
    add("`--ready` writes the covering email beside the pack as an ordinary")
    add("`.eml`. Double-click it and it opens in the mail client already")
    add("addressed, already attached, already written; you read it and press")
    add("send. **Nothing is sent by the software** — the send is the one")
    add("irreversible step in the whole pipeline, and it stays attached to a")
    add("person.")
    add("")
    add("The wording is the firm's and lives in `registry/signing.yaml`. Until")
    add("somebody has accepted or rewritten the draft there, this refuses and")
    add("says so — the pack still builds. An agent writing to a client over the")
    add("firm's name, in prose nobody read, is the one failure worth refusing")
    add("a convenience over.")
    add("")
    add("Turning on `secure_keyword` in that registry puts Encyro's")
    add("`[Secure]` keyword in the subject, which their Outlook add-in reads")
    add("on send. That is the only automation hook Encyro appears to offer —")
    add("there is no API, no SMTP relay and no connector. It is off until")
    add("somebody has sent one to themselves and checked the client does not")
    add("read the keyword. See `docs/research-e-signature.md`.")
    add("")

    add("**Nobody types a list of who must sign.** The templates carry the")
    add("signature blocks and the register reads them, so a block that moves or")
    add("gains a signer is followed on its own — and the spouse's line is")
    add("expected only on a joint return, because that is how the letter is")
    add("drawn and what the delivery letter tells the client.")
    add("")
    add("**How it reached you is the record, not a tick.** *In person*,")
    add("*came back signed* and *signed through a service* are three different")
    add("kinds of knowing, and which one it was is the first thing anybody")
    add("asks. A signature taken through a service is refused without the")
    add("reference its audit trail is under.")
    add("")
    add("**The date is the day they signed, not the day you heard.** A letter")
    add("that arrives on Monday was signed on Friday, and the date on the page")
    add("is the one that counts. Both are kept.")
    add("")
    add("**The e-file authorization is tracked, though we never print it.**")
    add("Drake produces Form 8879 — or 8879-CORP, or 8879-PE — and no template")
    add("here will ever be one, so the census that reads our own documents")
    add("cannot see it. `registry/signing.yaml` declares it instead, as a")
    add("signature the **engagement** needs rather than one our paper carries.")
    add("That is why it can be blocked on rather than shrugged at, and why the")
    add("form names live in a registry: the IRS renames them, and 8879-C and")
    add("8879-S became a single 8879-CORP in December 2022.")
    add("")
    add("One thing this deliberately does **not** know, and says so rather")
    add("than assuming:")
    add("")
    add("- **The records release.** Addressed to the previous accountant. It")
    add("  gates nothing here, and waiting on it would stop an engagement over")
    add("  a document somebody else acts on.")
    add("")
    # THIS PARAGRAPH USED TO SAY THE OPPOSITE, for a year after it stopped
    # being true. `signing._unsettled` blocks on an unsettled invoice and has
    # since payments were wired; the sentence here was transcribed from that
    # function's own stale docstring, which still said nothing recorded
    # whether a bill was paid. A preparer read section 4, believed billing
    # could not gate signing, and was then blocked with no explanation.
    add("**And one it does know, which used to be listed above as unknowable.**")
    add("An invoice that has been raised and is not recorded as settled is a")
    add("BLOCKER here, not a silence: every engagement letter says we will not")
    add(f"e-file before the bill is settled. A bill nobody has raised is not an")
    add(f"unpaid bill and blocks nothing. `python cli.py {_require('payments')}`")
    add("asks the processor; a bill paid another way is recorded by hand.")
    add("")
    add("> **Judgement, not procedure:** whether to start work on a signature")
    add("> you have been told about but not yet seen. The register records what")
    add("> was **observed**; it will not infer one, and it is worth nothing the")
    add("> first time somebody records a signature they are assuming.")
    add("")
    add("See `docs/research-e-signature.md` for what the IRS requires of a")
    add("remote 8879 signature, what it does not require of an engagement")
    add("letter, and what the vendors cost — **including the caveat that none")
    add("of those rules has been read from the source document yet.**")
    add("")

    # ── 4 · the work changed ──────────────────────────────────────────────
    _appendix(add, "Getting it signed")
    add("## 5 · When the work changes, and the price with it")
    add("")
    add("```")
    add(f"python cli.py {_require('requote')} --engagement <REF>")
    add(f"python cli.py {_require('requote')} --engagement <REF> \\")
    add("    --set count_rentals=2 --reason '<why, in one sentence>'")
    add("```")
    add("")
    add("A client rings in March: they bought a rental, a K-1 arrived, the")
    add("side business turned out to be a real one. **Nobody types a figure.**")
    add("The answers move and the same schedule that priced the engagement in")
    add("January prices it again — an amount typed onto an invoice by hand is")
    add("a second source for the same money, and the one the client keeps is")
    add("the one that says the larger number.")
    add("")
    add("Run with no `--set`, it lists the answers that move money — read out")
    add("of the fee schedule itself, and narrowed to the ones this client was")
    add("actually asked. In the browser it is **Update the quote** on the")
    add("engagement's own page.")
    add("")
    add("**Nothing is written without `--reason`.** The plan prints — every")
    add("line that moves, the new total, the difference — and the command")
    add("stops. A re-quote that could happen by accident is a price that moved")
    add("and cannot be explained a year later.")
    add("")
    add("Three things it refuses outright:")
    add("")
    add("- **answers that now flag work the firm does not take** — the")
    add("  engagement is already live, so what is needed is the disengagement")
    add("  letter, not a new price;")
    add("- **a re-quote that changes nothing** — a revision log full of no-ops")
    add("  is a log nobody reads, and a second estimate identical to the first")
    add("  confuses a client for no reason;")
    add("- **an incomplete interview** — it reprices the whole engagement, not")
    add("  one line, so it needs what the first price needed.")
    add("")
    add("What it writes: the amended answers, the repriced record, and one")
    add("entry in `revisions.json` beside the engagement — append-only, never")
    add("pruned, showing what was asked, what moved, and why. The same shape")
    add("as a waved-through gate failure, for the same reason.")
    add("")
    add("**Two dates, and only one of them moves.** The estimate gets today's;")
    add("the engagement letter keeps the date the client signed under. Two")
    add("sheets in a drawer showing different totals under the same date is a")
    add("question nobody can answer next February.")
    add("")
    add("> **Judgement, not procedure:** whether the pack goes out again. If")
    add("> the scope lines moved, the signed letter no longer describes the")
    add("> work and the re-quote says so — rebuild it. If only the figure")
    add("> moved, the letter still reads correctly and the estimate can go on")
    add("> its own.")
    add("")

    # ── 4 · billing ───────────────────────────────────────────────────────
    _appendix(add, "When the work changes, and the price with it")
    add("## 6 · Billing")
    add("")
    add("```")
    add(f"python cli.py {_require('invoice')} --engagement <REF> --billed '<period>'")
    add(f"python cli.py {_require('render')} --engagement <REF> --docs invoice --out out")
    add("```")
    add("")
    add("One engagement has many invoices, so each is written to its own file")
    add("rather than over the record. The invoice and the estimate are checked")
    add("against each other for the reference and the figure.")
    add("")
    # THIS SAID "MUST NOT SHARE PeriodLabel" AS THOUGH IT WERE ENFORCED. It is
    # not, and enforcing it would be wrong: a bill covering the whole
    # engagement legitimately reads "2026 tax year", the same as the estimate.
    # What IS enforced is only that `--billed` is given at all. A "must not" in
    # a document that promises it "cannot claim a check the gate does not
    # perform" reads as a guarantee; this one was an intention.
    add("`--billed` is required, and it is a judgement rather than a check:")
    add("`PeriodLabel` means the engagement's period on the estimate and what")
    add("this bill covers on the invoice. Nothing stops you writing the same")
    add("words in both — on a bill for the whole engagement that is right.")
    add("")
    add("### The link, and finding out that it was paid")
    add("")
    add("```")
    add(f"python cli.py {_require('invoice')} --engagement <REF> "
        "--billed '<period>' --sandbox")
    add(f"python cli.py {_require('payments')}")
    add("```")
    add("")
    add("**Raising the bill creates the payment link**, and the link goes on")
    add("the invoice as `<<PaymentUrl>>`. Nothing else gets one — the firm's")
    add("rule: *\"Quotes get no link. Only the invoice.\"* An estimate is what")
    add("the work will cost and is not yet owed, and this engine re-quotes, so")
    add("a link on a quote would collect a figure that had since moved. A test")
    add("holds that line.")
    add("")
    add("**The link is made before the bill is written**, so a processor that")
    add("refuses leaves no invoice claiming a link it never got. If it refuses,")
    add("the bill is still raised and the reason is printed — `--no-link` skips")
    add("it deliberately.")
    add("")
    add("**`payments` asks; it is not told.** A webhook would need a public")
    add("server this firm does not have, so this polls when somebody wants the")
    add("answer, from a laptop, with nothing listening on the internet. **Only")
    add("a settlement is ever written down** — an unpaid order is left alone,")
    add("because a cached \"no\" goes stale the moment somebody pays.")
    add("")
    add("Once a bill is settled, `sign` stops reporting the invoice half of the")
    add("promise as unknowable: every engagement letter says we will not e-file")
    add("before the invoice is settled, and that becomes something the software")
    add("can actually check.")
    add("")
    add("> **Judgement, not procedure:** a bill paid another way. Somebody who")
    add("> sends a cheque or a bank transfer will never show as settled here,")
    add("> and marking it by hand is a decision about money that belongs to a")
    add("> person, not to a poll.")
    add("")
    add("The token lives in an environment variable named by")
    add("`registry/payments.yaml`, never in the repository — a token in the")
    add("repository is a token in every clone, backup and screenshot. The")
    add("`location_id` and the wording a client sees are in that registry and")
    add("carry `[CONFIRM: ]` until the firm fills them in; until then no link")
    add("is created and the reason says so.")
    add("")
    add("There are **two** location ids, because Square gives you two accounts:")
    add("`location_id` for real money and `sandbox_location_id` for `--sandbox`.")
    add("A run needs only the one it is using, so you can test before you have")
    add("a live location — and a live invoice can never carry the test one.")
    add("")

    # ── 5 · closing ───────────────────────────────────────────────────────
    _appendix(add, "Billing")
    # ── the four lifecycle events ─────────────────────────────────────────
    # THESE HAD NO SECTION AT ALL. Four of the eleven client documents are
    # produced by `event`, and the document named them only inside a comma
    # list of every command. Section 5 even told the reader that a live
    # engagement turning into work the firm does not take needs the
    # disengagement letter -- and never said how to produce one.
    add("## 7 · The four things that happen after the pack")
    add("")
    add("Everything above is one engagement being opened, priced and billed.")
    add("These four are what happens to it afterwards, and each writes one")
    add("document. The questions come from `registry/lifecycle.yaml`, so a")
    add("question added there is asked here without anybody editing this.")
    add("")
    add("```")
    # A REAL KIND, NOT A PLACEHOLDER. `--kind` is a choice, so `<KIND>` is
    # not merely unhelpful -- argparse refuses it, and `unrunnable()` says so.
    add(f"python cli.py {_require('event')} --kind {sorted(_events())[0]} "
        f"--engagement <REF>")
    add(f"# the four kinds are {', '.join(sorted(_events()))}")
    add("```")
    add("")
    add("| Kind | When | It writes | It asks |")
    add("| --- | --- | --- | --- |")
    for kind, event in sorted(_events().items()):
        label = document_files().get(event.document,
                                     (event.document, event.document))[1]
        asks = f"{len(event.questions)} question(s)"
        if event.rows:
            asks += f" + {len(event.rows)} list(s)"
        add(f"| `{kind}` | {event.what.rstrip('.')} | {label} | {asks} |")
    add("")
    add("An event reuses what it recorded last time unless you pass `--again`,")
    add("so re-running one after a correction does not re-ask everything.")
    add("")
    for kind in sorted(_events()):
        _appendix(add, f"When {_event_title(kind)}")

    add("## 8 · Closing an engagement, at the end of the cycle")
    add("")
    add("```")
    add(f"python cli.py {_require('close')} --engagement <REF>")
    add("```")
    add("")
    add("Records what was **actually filed**, in-house. Nothing is read out of")
    add("Drake. The questions asked depend on the return:")
    add("")
    for key, label, form in RETURN_TYPES:
        asked = closeout.questions_for(key)
        add(f"**{label} ({form})** — {len(asked)} questions: "
            + ", ".join(f"`{q['id']}`" for q in asked))
        add("")
    add("An unanswered question is reported as unanswered, never as agreement.")
    add("")

    # ── 6 · the control ───────────────────────────────────────────────────
    add("## 9 · The end-of-cycle control")
    add("")
    add("```")
    add(f"python cli.py {_require('reconcile')}")
    add(f"python cli.py {_require('reconcile')} --apply")
    add("```")
    add("")
    add("Sweeps every engagement and reports where the filed return disagrees")
    add("with what the interview recorded months earlier. An engagement nobody")
    add("closed is reported as **NOT CLOSED**, never skipped: a control that only")
    add("examines the work somebody remembered to close is a control over the")
    add("diligent, which is not where the problem is.")
    add("")
    add("> **Judgement, not procedure:** a divergence is not an error. It is one")
    add("> of three things and only a person can tell which — the return changed")
    add("> after the interview, the interview was wrong, or the wrong thing was")
    add("> filed. `--apply` moves the record to match the return and writes every")
    add("> move to an append-only log. Next year's interview is seeded from those")
    add("> answers, which is why it matters that they are right.")
    add("")

    # ── 7 · next year ─────────────────────────────────────────────────────
    add("## 10 · The following year")
    add("")
    add("```")
    add(f"python cli.py {_require('returning')} --engagement <LAST YEAR'S REF>")
    add("```")
    add("")
    add("Last year's answers are shown back to be confirmed, never assumed —")
    # COUNTED, NOT REMEMBERED. This read "Nine carry" and was typed: nine is
    # what happened to carry for one individual sample. `interview.CARRIES`
    # holds more than that, and five of them are entity-only -- so a preparer
    # rolling a partnership forward and counting nine confirmations would
    # conclude six answers had been lost.
    add(f"every carried answer is still asked. Up to {_carry_count()} carry, "
        f"depending on")
    add("what the engagement is; the rest are asked fresh, and the command")
    add("prints why each one does not carry.")
    add("")
    add("A returning client is also asked what changed: a marriage, a divorce, a")
    add("birth, a death, a home bought or sold, a move, a retirement, an")
    add("inheritance. Those are recorded and flagged for you. What any of them")
    add("*means* for the return is a conversation with the client, and nothing")
    add("here turns a tick box into advice.")
    add("")

    # ── 8 · demonstrating it ──────────────────────────────────────────────
    add("## 11 · Demonstrating that all of it works")
    add("")
    add("```")
    add("cd client-documents && python exercise.py")
    add("```")
    add("")
    add("Runs every scenario end to end through the real commands, produces the")
    add("real documents, **opens each one in a browser** to confirm it rendered,")
    add("and cross-checks each pack against itself. Exits non-zero on a surprise.")
    add("")
    add("A `[CONFIRM: ]` in a registry is not a surprise. It is the software")
    add("saying a sentence a client will read has not been written yet, and")
    add("refusing rather than sending the placeholder; the harness reports those")
    add("as **waiting on the firm**.")
    add("")
    add("Every other command this document names:")
    add("")
    add(", ".join(f"`{c}`" for c in commands()))
    add("")
    # ── the index, and what it could not place ────────────────────────────
    audit = template_audit()
    add("## Appendix — every template, and the procedure it belongs to")
    add("")
    add("The firm's general rule: **each relevant template is an appendix item")
    add("to the process it belongs to.** This index is the other direction —")
    add("start from a template and find its procedure.")
    add("")
    add("Nothing here is typed. Which documents a procedure produces is read")
    add("from `packaging.PACKS`, `packaging.CONDITIONAL` and")
    add("`registry/lifecycle.yaml`; the filenames come from `cli.DOCUMENTS`.")
    add("")
    add("| Template | Procedure |")
    add("| --- | --- |")
    for procedure, docs in templates_by_procedure().items():
        for doc in docs:
            entry = document_files().get(doc)
            name = entry[1] if entry else doc
            add(f"| {name} | {procedure} |")
    add("")
    add(f"{audit['templates_examined']} template file(s) examined against "
        f"{audit['documents_examined']} document(s) named by a procedure.")
    add("")
    if audit["missing"]:
        add("**A procedure names a document with no template:**")
        add("")
        for miss in audit["missing"]:
            add(f"- {miss}")
        add("")
    if audit["orphans"]:
        add("**Templates that belong to no procedure yet.** Reported rather")
        add("than hidden: a finished letter with no process behind it is work")
        add("waiting on a decision, and a document nobody can reach is the")
        add("same as one that does not exist.")
        add("")
        for orphan in audit["orphans"]:
            add(f"- `{orphan}`")
        add("")
    if not audit["missing"] and not audit["orphans"]:
        add("Every template belongs to a procedure, and every procedure names")
        add("a template that exists.")
        add("")

    return "\n".join(lines) + "\n"


def write(path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(), encoding="utf-8")
    return path


def is_current(path: Path = OUT) -> bool:
    return path.exists() and path.read_text(encoding="utf-8") == render()
