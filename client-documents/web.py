"""The web front door: the same interview, in a browser.

**One handler serves both.** Every route here answers a browser with HTML and a
script with JSON, decided by the `Accept` header, and the two share every line
of code up to the point of rendering. That is not a convenience -- it is the
guarantee. A human and an automation cannot drift apart when there is only one
code path, and neither can skip a gate that lives below them both in
`intake.finish`.

What this module is NOT allowed to contain: any rule about whether an
engagement may be created. HARD NO, the decision question, pricing, the record's
shape -- all of it lives in `intake`, and `tests/test_web.py` reads this file's
source and fails if a decision reappears here. If it did, the browser would
enforce something the CLI does not, or the reverse, and the whole arrangement
would be a lie.

Drafts persist. A half-finished sitting is written to `_drafts/` after every
answer, so closing the laptop mid-call does not lose the consultation -- which
the terminal interview could not survive.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date
from functools import lru_cache
from pathlib import Path

from flask import (Flask, abort, jsonify, redirect, request, url_for)

import cli
import editor
import registry_editor
import engagements
import intake
import leads
import lifecycle
import invoicing
import packaging
import payments
import presend
import previewing
import sending
import schedules as sched
import interview as iv
import requote
import signing
import settings as firm
import tins

DRAFTS = "_drafts"
ROOT = Path(__file__).resolve().parent


def wants_json() -> bool:
    """A script asks for JSON; a browser does not.

    Checked this way round on purpose: browsers send `Accept: text/html,...`
    and `*/*` is what a bare client sends, so anything that does not explicitly
    prefer HTML gets data.
    """
    if request.args.get("format") == "json":
        return True
    best = request.accept_mimetypes.best_match(["text/html", "application/json"])
    return best == "application/json"


# ── draft storage ─────────────────────────────────────────────────────────

def draft_path(store: Path, sid: str) -> Path:
    if not sid.isalnum() or len(sid) > 40:
        abort(400, "bad draft id")
    return store / DRAFTS / f"{sid}.json"


def load_draft(store: Path, sid: str) -> dict:
    p = draft_path(store, sid)
    if not p.exists():
        abort(404, f"no draft {sid}")
    return json.loads(p.read_text(encoding="utf-8"))


def save_draft(store: Path, sid: str, data: dict) -> None:
    """Write an unfinished sitting -- refusing a TIN before it reaches disk.

    THE GUARD WAS AT THE FINISH LINE AND THE WRITE HAPPENS EVERY STEP.
    `engagements.save_answers` refuses a full SSN or EIN in the answers, and
    that is the only place it was checked -- but a sitting is written to
    `_drafts/<id>.json` after EVERY question, long before anyone finishes.
    Measured 1 Sep 2026 by driving the browser: thirteen free-text answers each
    carrying `123-45-6789` were accepted, and the number was on disk in
    cleartext in the draft. `notes` is a free textarea, which is exactly where
    a preparer types "prior return showed 123-45-6789".

    The store is the folder the firm syncs. A number written there is in
    OneDrive, in every backup of it, and in every machine that folder reaches.

    The check belongs HERE rather than in the route, so a second caller cannot
    be added without it -- `back` already exists and a third will follow.
    """
    tins.refuse(data, "this sitting")
    p = draft_path(store, sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def draft_card(store: Path, sid: str) -> dict:
    """An unfinished sitting, described the way a person would describe it.

    The home page listed these as `resume 56509a234d60`. That is the session
    id, which tells a preparer nothing at all -- not whose it is, not when it
    started, not whether it is nearly done. Everything needed is already in
    the draft file; nothing new is stored to say it.
    """
    who, started, answered = "", "", 0
    try:
        d = json.loads(draft_path(store, sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # A draft that will not parse is still a draft: it is named, and it
        # is not silently dropped off the page.
        return {"id": sid, "who": "", "started": "", "answered": 0}
    answers = d.get("answers") or {}
    answered = len(answers)
    lead = (d.get("lead") or {}).get("contact") or {}
    who = answers.get("client_full_name") or lead.get("name") or lead.get("email") or ""
    started = str(d.get("started") or "")
    return {"id": sid, "who": who, "started": started, "answered": answered}


def session_for(draft: dict) -> iv.Interview:
    return iv.Interview(lead=draft.get("lead"), answers=dict(draft["answers"]),
                        # "The hard-no list is wrong, carry on." Set on the
                        # draft by the override button, because a sitting now
                        # ENDS where a HARD NO is ticked -- so without this the
                        # override would create an engagement from the four
                        # questions asked before it. See the finish handler.
                        override_hard_no=bool(draft.get("override_hard_no")))


# ── the value a form field carries -> the value the schema expects ────────

def revising(session: iv.Interview, draft: dict):
    """The question a preparer stepped back to, if it still stands.

    A sitting is normally wherever `next_question` says it is. Stepping back
    puts a cursor on the draft instead -- and a cursor goes stale in one
    keystroke: change `joint_return` to "no" and the spouse's name is pruned
    out from under it. So it is checked against the live schema every time
    rather than trusted, and a stale one quietly hands the sitting back to
    `next_question`.
    """
    qid = draft.get("at")
    if not qid:
        return None
    for section, q in iv.all_questions(session.schema):
        if q["id"] != qid:
            continue
        if q.get("derived") or qid not in session.answers:
            return None
        return (section, q) if iv.visible(q, session.answers) else None
    return None


def step_back_to(session: iv.Interview, draft: dict) -> str:
    """One step behind wherever the sitting is now, or "" at the start."""
    order = session.asked()
    at = draft.get("at")
    if at in order:
        i = order.index(at)
        return order[i - 1] if i else ""
    return order[-1] if order else ""


def coerce(q: dict, raw) -> object:
    """One converter, in `interview`, beside the schema it converts to.

    It lived here until the re-quote became the second front door onto
    changing an answer. See `interview.coerce`.
    """
    return iv.coerce(q, raw)


def create_app(store: Path | None = None, leads_workbook: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["STORE"] = Path(store) if store else engagements.STORE
    app.config["LEADS"] = Path(leads_workbook) if leads_workbook else None

    def st() -> Path:
        return app.config["STORE"]

    # ── index ─────────────────────────────────────────────────────────────

    @app.get("/")
    def index():
        rows = engagements.listing(st())
        drafts = sorted(p.stem for p in (st() / DRAFTS).glob("*.json")) \
            if (st() / DRAFTS).exists() else []
        if wants_json():
            # The JSON stays a list of ids. It is what scripts and the tests
            # already read, and a half-finished sitting is identified by its
            # id however it is described on screen.
            return jsonify(engagements=rows, drafts=drafts)
        return page("SAT-C", index_body(rows, [draft_card(st(), d) for d in drafts]))

    # ── start ─────────────────────────────────────────────────────────────

    @app.get("/leads")
    def lead_list():
        """Who has come in, and a way to start a sitting from any of them."""
        path = Path(app.config.get("LEADS") or (ROOT / "leads.xlsx"))
        rows, problem = [], ""
        if path.exists():
            try:
                rows = leads.from_workbook(path)
            except leads.LeadError as exc:
                problem = str(exc)
        if wants_json():
            return jsonify(leads=rows, workbook=str(path), error=problem)
        return page("Leads", leads_body(rows, path,
                                        problem or request.args.get("error", "")))

    @app.post("/interview")
    def start():
        lead = None
        if request.is_json:
            lead = (request.get_json(silent=True) or {}).get("lead")
        elif request.form.get("lead_index") not in (None, ""):
            # A row from the workbook. Read again rather than held in a
            # session: the file on disk is the record, and a sitting started
            # from a stale copy would carry answers the firm has since fixed.
            path = Path(app.config.get("LEADS") or (ROOT / "leads.xlsx"))
            try:
                found = leads.from_workbook(path)
                lead = found[int(request.form["lead_index"])]
            except (leads.LeadError, IndexError, ValueError):
                lead = None
        elif request.form.get("by_hand"):
            # THE MANUAL DOOR. "it is possible that a lead has to be input
            # manually though, they may just give us contact info."
            try:
                lead = leads.by_hand(**{k: request.form.get(k, "")
                                        for k in ("name", "email", "phone",
                                                  "location", "notes")})
            except leads.LeadError as exc:
                # An empty manual form used to fall through and start a blank
                # sitting, which looks like it worked. A lead with nothing in
                # it is nobody.
                if wants_json():
                    return jsonify(error=str(exc)), 400
                return redirect(url_for("lead_list", error=str(exc)))
        sid = uuid.uuid4().hex[:12]
        save_draft(st(), sid, {"lead": lead, "answers": {},
                               "started": date.today().isoformat()})
        if wants_json():
            return jsonify(draft=sid, next=url_for("show", sid=sid)), 201
        return redirect(url_for("show", sid=sid))

    # ── the wording ───────────────────────────────────────────────────────
    #
    # "i want it to be very straightforward and simple. like i can just click
    # a template, open a section, edit it" -- the firm, 26 August 2026. Every
    # rule about what an edit may do lives in `editor`, not here, for the same
    # reason no decision lives here: a browser must not be able to save
    # something a script could not.

    # ── the prices ────────────────────────────────────────────────────────
    #
    # The firm, 26 August 2026: "i want this to be GUI-based like i think you
    # made the changing of templates." Same shape as the section editor above,
    # and the same division of labour: every rule about what an edit may do
    # lives in `registry_editor`, not here, so a browser cannot save something
    # a script could not.
    #
    # A price change is shown BEFORE it is written -- what it was, what it
    # becomes, whether it reaches satcllp.com, and what it does to the demo
    # engagement's quote. That preview is the reason this beats editing YAML:
    # the file cannot show you what a number moves.

    @app.get("/prices")
    def prices():
        return page("Prices", prices_body(registry_editor.prices()))

    @app.get("/prices/<path:path>")
    def price(path):
        try:
            wanted = next(p for p in registry_editor.prices() if p.path == path)
        except StopIteration:
            abort(404, f"no price at {path}")
        return page(wanted.label, price_body(wanted))

    @app.post("/prices/<path:path>")
    def set_price(path):
        raw = (request.form.get("amount") or "").strip()
        preview = request.form.get("preview")
        try:
            amount = int(raw)
        except ValueError:
            return _price_error(path, f"{raw!r} is not a whole number of dollars")
        try:
            report = (registry_editor.effect(path, amount) if preview
                      else registry_editor.save(path, amount))
        except registry_editor.RegistryError as exc:
            return _price_error(path, str(exc))
        if wants_json():
            return jsonify({**report, "saved": not preview})
        wanted = next(p for p in registry_editor.prices() if p.path == path)
        return page(wanted.label, price_body(wanted, report=report, saved=not preview))

    def _price_error(path, message):
        wanted = next((p for p in registry_editor.prices() if p.path == path), None)
        if wanted is None:
            abort(404, f"no price at {path}")
        if wants_json():
            return jsonify(error=message, path=path), 400
        return page(wanted.label, price_body(wanted, error=message)), 400

    @app.get("/templates")
    def templates():
        rows = []
        for name in sorted(editor.TEMPLATE_DIR.glob("SATC*.html")):
            secs = editor.sections(name.read_text(encoding="utf-8"))
            blocks = [b for s in secs for b in s.blocks]
            rows.append({"file": name.name,
                         "title": name.stem.replace("SATC ", ""),
                         "sections": len(secs),
                         "editable": sum(1 for b in blocks if b.editable),
                         "blocks": len(blocks)})
        if wants_json():
            return jsonify(templates=rows)
        return page("Wording", templates_body(rows))

    @app.get("/templates/<path:name>")
    def template(name):
        path = editor.TEMPLATE_DIR / name
        if path.parent != editor.TEMPLATE_DIR or not path.exists():
            abort(404)
        secs = editor.sections(path.read_text(encoding="utf-8"))
        if wants_json():
            return jsonify(template=name, sections=[
                {"id": s.id, "number": s.number, "title": s.title,
                 "blocks": [{"id": b.id, "text": b.text, "editable": b.editable,
                             "reason": b.reason, "fields": list(b.fields)}
                            for b in s.blocks]} for s in secs])
        return page(name, template_body(name, secs,
                                        request.args.get("saved"),
                                        request.args.get("error"),
                                        request.args.get("open")))

    @app.post("/templates/<path:name>/sections")
    def sections(name):
        """Add or take out a whole section. Wording is the route above."""
        form = request.get_json(silent=True) or request.form
        registry = {f: n for n, (f, _) in cli.DOCUMENTS.items()}.get(name)
        if registry is None:
            abort(404)
        try:
            said = editor.save_section(
                name, registry,
                remove=form.get("remove", ""), title=form.get("title", ""),
                text=form.get("text", ""), after=form.get("after", ""))
        except editor.EditError as exc:
            if wants_json():
                return jsonify(error=str(exc)), 400
            return redirect(url_for("template", name=name, error=str(exc)))
        if wants_json():
            return jsonify(done=said)
        return redirect(url_for("template", name=name, saved=said))

    @app.post("/templates/<path:name>")
    def edit(name):
        payload = request.get_json(silent=True)
        if payload is not None:
            edits = payload.get("edits") or {}
            section = payload.get("section", "")
        else:
            edits = {k[2:]: v for k, v in request.form.items() if k.startswith("t:")}
            section = request.form.get("section", "")
        try:
            changed = editor.save(name, edits)
        except editor.EditError as exc:
            if wants_json():
                return jsonify(error=str(exc)), 400
            return redirect(url_for("template", name=name, error=str(exc),
                                    open=section))
        if wants_json():
            return jsonify(changed=changed)
        return redirect(url_for("template", name=name, open=section,
                                saved=",".join(changed) if changed else "none"))

    # ── the current question ──────────────────────────────────────────────

    @app.get("/interview/<sid>")
    def show(sid):
        draft = load_draft(st(), sid)
        session = session_for(draft)
        back = revising(session, draft)
        nxt = back or session.next_question()

        if nxt is None:
            blockers = iv.hard_no(session.answers)
            if wants_json():
                return jsonify(draft=sid, complete=True, answers=session.answers,
                               hard_no=blockers,
                               decision=session.answers.get("decision"))
            return page("Review", review_body(sid, session, blockers))

        section, q = nxt
        claim = iv.prefill_for(q, draft.get("lead"))
        acceptable = iv.prefill_is_answerable(q, claim)
        # What they actually ticked, when a map turned it into something else.
        # See interview.prefill_source: "The website said 1040" was shown to a
        # preparer whose client had asked about tax planning.
        said = iv.prefill_source(q, draft.get("lead"))
        if wants_json():
            return jsonify(draft=sid, complete=False, section=section["title"],
                           question=q, claim=claim, claim_acceptable=acceptable,
                           claim_source=said,
                           answered=len(session.answers),
                           revising=bool(back))
        return page(q["question"],
                    question_body(sid, section, q, claim, acceptable, session,
                                  current=session.answers.get(q["id"])
                                  if back else None,
                                  back=step_back_to(session, draft),
                                  said=said))

    # ── answering ─────────────────────────────────────────────────────────

    @app.post("/interview/<sid>")
    def answer(sid):
        draft = load_draft(st(), sid)
        session = session_for(draft)
        back = revising(session, draft)
        nxt = back or session.next_question()
        if nxt is None:
            abort(409, "the interview has no more questions")
        _, q = nxt

        body = request.get_json(silent=True) if request.is_json else None
        if body is not None:
            raw = body.get("answer")
        elif q["type"] in ("multi",):
            raw = request.form.getlist("answer")
        else:
            raw = request.form.get("answer")

        # "accept the claim" is the browser's enter key. Same semantics.
        if request.form.get("accept") or (body or {}).get("accept"):
            raw = iv.prefill_for(q, draft.get("lead"))

        try:
            session.answer(q["id"], coerce(q, raw))
            draft["answers"] = session.answers
            # The correction is made; the sitting goes back to where it was.
            draft.pop("at", None)
            # INSIDE the try: `save_draft` refuses a TIN, and a refusal there
            # must reach the preparer as the same kind of "fix this answer"
            # message an interview error does -- not a 500, and not a write.
            save_draft(st(), sid, draft)
        except (iv.InterviewError, tins.TinRefused) as exc:
            if wants_json():
                return jsonify(error=str(exc), question=q["id"]), 400
            return page(q["question"],
                        question_body(sid, nxt[0], q,
                                      iv.prefill_for(q, draft.get("lead")),
                                      iv.prefill_is_answerable(
                                          q, iv.prefill_for(q, draft.get("lead"))),
                                      session, error=str(exc),
                                      current=session.answers.get(q["id"])
                                      if back else None,
                                      back=step_back_to(session, draft))), 400

        if wants_json():
            return jsonify(draft=sid, saved=q["id"], next=url_for("show", sid=sid))
        return redirect(url_for("show", sid=sid))

    # ── going back ────────────────────────────────────────────────────────

    @app.post("/interview/<sid>/back")
    def back(sid):
        """A client corrects themselves, and there was no route for it.

        Nothing is deleted here. The cursor moves, the old answer is shown
        as it stands, and re-answering runs the same `Interview.answer` the
        forward path runs -- so a changed answer prunes whatever it hides,
        exactly as it would have if it had been given that way first time.
        """
        draft = load_draft(st(), sid)
        session = session_for(draft)
        body = request.get_json(silent=True) if request.is_json else None
        want = (body or {}).get("to") or request.form.get("to") or ""
        # A preparer who steps back and decides nothing was wrong needs a way
        # out that is not "press Back until something happens".
        if (body or {}).get("resume") or request.form.get("resume"):
            want, qid = "", ""
        else:
            qid = want if want in session.asked() else step_back_to(session,
                                                                   draft)
        if qid:
            draft["at"] = qid
        else:
            draft.pop("at", None)
        save_draft(st(), sid, draft)
        if wants_json():
            return jsonify(draft=sid, at=qid, next=url_for("show", sid=sid))
        return redirect(url_for("show", sid=sid))

    # ── finishing: straight through to the core ───────────────────────────

    @app.post("/interview/<sid>/finish")
    def finish(sid):
        draft = load_draft(st(), sid)
        override = bool(request.form.get("override")
                        or (request.get_json(silent=True) or {}).get("override"))

        # AN OVERRIDE ON AN UNFINISHED SITTING RESUMES IT, it does not finish
        # it. A HARD NO now ends the sitting where it is ticked, so the review
        # screen an override is pressed from may be showing four answers out of
        # thirty. Creating from those would refuse anyway ("the interview is not
        # finished"), and the preparer would be told the wrong thing about why.
        # Overriding means the list is wrong, so the questions resume.
        if override and not draft.get("override_hard_no"):
            draft["override_hard_no"] = True
            save_draft(st(), sid, draft)
            if session_for(draft).next_question() is not None:
                if wants_json():
                    return jsonify(draft=sid, resumed=True,
                                   next=url_for("show", sid=sid)), 200
                return redirect(url_for("show", sid=sid))

        # The ONLY decision-making call in this module, and it is a delegation.
        outcome = intake.finish(draft["answers"], store=st(),
                                override_hard_no=override)

        if outcome.created:
            draft_path(st(), sid).unlink(missing_ok=True)

        if wants_json():
            return jsonify(status=outcome.status, reason=outcome.reason,
                           blockers=outcome.blockers, ref=outcome.ref,
                           overridden=outcome.overridden,
                           flags=outcome.flags), \
                (201 if outcome.created else 200)
        return page("Outcome", outcome_body(sid, outcome))

    # ── what exists ───────────────────────────────────────────────────────

    @app.get("/engagement/<ref>")
    def engagement(ref):
        try:
            record = engagements.load(ref, st())
        except (FileNotFoundError, ValueError):
            abort(404, f"no engagement {ref}")
        open_now = firm.open_decisions() if hasattr(firm, "open_decisions") else []
        if wants_json():
            return jsonify(ref=ref, record=record, open_decisions=open_now)
        return page(ref, engagement_body(ref, record, open_now,
                                         requote.revisions(ref, st())))

    # ── packaging: the same gate, without a terminal ──────────────────────
    #
    # "every process is doable by a human and replicable by automation, under
    # the same controls." Packaging was the half of that sentence that was not
    # true: a preparer could interview, price and edit the wording in a
    # browser, and then had to type a command to get the pack the client
    # actually signs -- which is the one step with a BLOCKING gate on it.
    #
    # Nothing about that gate is re-decided here. `sending.build` is the same
    # function `cli.cmd_package` calls, with the same arguments, and this route
    # reports what it returned.

    def _pack_ready(ref):
        """(record, documents, note) or a rendered refusal."""
        raw = engagements.load(ref, st())
        record = cli.build_record(raw)
        return record

    @app.get("/engagement/<ref>/package")
    def package(ref):
        try:
            record = _pack_ready(ref)
        except (FileNotFoundError, ValueError, engagements.EngagementError):
            abort(404, f"no engagement {ref}")
        invoice = request.args.get("invoice") == "1"
        try:
            docs = packaging.documents_for(record, with_invoice=invoice)
        except packaging.PackageError as exc:
            if wants_json():
                return jsonify(ref=ref, error=str(exc)), 400
            return page("Package", package_body(ref, record, [], problem=str(exc)))
        if wants_json():
            return jsonify(ref=ref, documents=docs, with_invoice=invoice)
        return page("Package", package_body(ref, record, docs,
                                            with_invoice=invoice))

    @app.post("/engagement/<ref>/package")
    def build_package(ref):
        try:
            record = _pack_ready(ref)
        except (FileNotFoundError, ValueError, engagements.EngagementError):
            abort(404, f"no engagement {ref}")

        body = request.get_json(silent=True) if request.is_json else None
        form = body if body is not None else request.form
        invoice = bool(form.get("invoice"))
        reason = (form.get("reason") or "").strip()
        force = bool(form.get("force"))

        try:
            docs = packaging.documents_for(record, with_invoice=invoice)
            packaging.check_attachments(None)
            # THE BILL LIVES IN ITS OWN FILE. Ticking "put the invoice in too"
            # used to refuse the WHOLE pack -- no letter, no estimate, no
            # onboarding letter -- because this door never went and got it.
            # The terminal did. One function now, so a third door cannot
            # forget it a third way.
            record = invoicing.fold_in(record, docs, st(), ref)
        except (packaging.PackageError, invoicing.InvoiceError) as exc:
            if wants_json():
                return jsonify(ref=ref, status="error", detail=str(exc)), 400
            return page("Package", package_body(ref, record, [],
                                                problem=str(exc))), 400

        # The same downgrade the terminal makes, for the same reason: a machine
        # with no PDF engine should still get the documents, not an error.
        want_pdf = True
        pdf_note = ""
        try:
            cli.pdf_engine()
        except cli.NoPdfEngine as exc:
            want_pdf, pdf_note = False, str(exc)

        pack = sending.build(
            record, st() / ref / "pack", render=cli.render_one,
            ref=record.get("EngagementRef") or ref, store=st(),
            template_dir=cli.TEMPLATE_DIR, documents=docs, want_pdf=want_pdf,
            readings=bool(form.get("notes")), force=force, reason=reason)

        if wants_json():
            return jsonify(
                ref=ref, status=pack.status,
                documents=pack.documents,
                written=sorted(f.name for fs in pack.written.values()
                               for f in fs),
                refused=[{"document": d, "detail": w} for d, w in pack.refused],
                blocking=[{"check": f.check, "document": f.document,
                           "detail": f.detail}
                          for f in (pack.check.blocking if pack.check else [])],
                override=pack.override, detail=pack.detail,
                pdf=want_pdf), (200 if pack.ok else 409)

        return page("Package", packed_body(ref, record, pack, invoice,
                                           pdf_note))

    # ── the work changed, so the price does ──────────────────────────────
    #
    # THE ANSWERS MOVE AND THE ENGINE PRICES THEM. Nowhere on these two screens
    # can a preparer type a figure, and that is not a styling choice: `pricing`
    # exists so that no human arithmetic reaches a client, and a box for an
    # amount would be a second way onto the money with none of the schedule's
    # rules behind it.
    #
    # NOTHING IS WRITTEN UNTIL THE SECOND SCREEN. The first shows what would
    # happen; the second takes a reason and records it. The plan is computed
    # again from the answers on the way in rather than carried across as a
    # decided thing -- a price that arrived on a form is a price a form could
    # have changed.

    def _changes_from(form, answers):
        """What the form is asking to change, in the schema's own types.

        Only the questions this client is actually asked, and only the ones
        whose value MOVED. Posting back every field unchanged would otherwise
        record a revision naming fourteen answers, none of which are news.

        WHICH QUESTIONS WERE ON THE PAGE IS ITS OWN FIELD, and it has to be.
        Reading "was this question present?" off the answer field cannot see an
        emptied multi-select: unticking every box sends nothing at all, which
        is indistinguishable from the question not being there -- so clearing
        one silently did nothing, on a screen that had just shown the boxes
        being unticked. `_asked` is posted once per question and says what the
        preparer was actually looking at.
        """
        asked = {q["id"]: q for q in requote.questions(answers)}
        on_page = (form.getlist("_asked") if hasattr(form, "getlist")
                   else (form.get("_asked") or []))
        out = {}
        for qid in on_page:
            q = asked.get(qid)
            if q is None:
                continue
            if hasattr(form, "getlist"):
                raw = form.getlist(f"{qid}[]") or form.getlist(qid)
            else:
                raw = form.get(qid)
            if isinstance(raw, list) and q["type"] not in ("multi", "list"):
                raw = raw[0] if raw else ""
            value = iv.coerce(q, raw)
            # A REORDERED SET OF TICKED BOXES IS NOT A CHANGE, and the old
            # order is kept rather than the new one: the schedules print on
            # the engagement letter in the order they are stored, so writing
            # the browser's reading order back would move a scope line on a
            # signed letter to say the same thing differently.
            if not iv.same_answer(q, answers.get(qid), value):
                out[qid] = value
        return out

    @app.get("/engagement/<ref>/requote")
    def requote_form(ref):
        try:
            record = engagements.load(ref, st())
            answers = requote._answers(ref, st())
        except (engagements.EngagementError, requote.RequoteError) as exc:
            abort(404, str(exc))
        if wants_json():
            return jsonify(ref=ref,
                           questions=[q["id"] for q in requote.questions(answers)],
                           answers={q["id"]: answers.get(q["id"])
                                    for q in requote.questions(answers)})
        return page("Update the quote",
                    requote_body(ref, record, requote.questions(answers),
                                 answers))

    @app.post("/engagement/<ref>/requote")
    def requote_preview(ref):
        try:
            record = engagements.load(ref, st())
            answers = requote._answers(ref, st())
        except (engagements.EngagementError, requote.RequoteError) as exc:
            abort(404, str(exc))

        body = request.get_json(silent=True) if request.is_json else None
        form = body if body is not None else request.form
        if body is not None:
            changes = {k: v for k, v in (body.get("changes") or {}).items()}
        else:
            changes = _changes_from(form, answers)

        if not changes:
            return page("Update the quote",
                        requote_body(ref, record, requote.questions(answers),
                                     answers,
                                     problem="Nothing on this page is "
                                             "different from what is already "
                                             "on file, so there is nothing to "
                                             "re-quote.")), 400
        try:
            quote = requote.plan(ref, changes, store=st())
        except requote.RequoteError as exc:
            return page("Update the quote",
                        requote_body(ref, record, requote.questions(answers),
                                     answers, problem=str(exc))), 400

        # RECORD IT, OR JUST LOOK? The browser posts here to LOOK. A caller
        # that means it sends a reason, and then this is the same two-step the
        # screens are: plan, then write.
        reason = (form.get("reason") or "").strip()
        if reason:
            try:
                requote.apply(quote, reason, store=st())
            except (requote.RequoteError, tins.TinRefused) as exc:
                if wants_json():
                    return jsonify(ref=ref, status="refused",
                                   detail=str(exc)), 400
                return page("Update the quote",
                            requoted_body(ref, record, quote, changes,
                                          problem=str(exc))), 400
            if wants_json():
                return jsonify(ref=ref, status="recorded",
                               was=quote.before_total, now=quote.after_total,
                               difference=quote.difference)
            return page("Update the quote",
                        requoted_body(ref, record, quote, changes, done=True))

        if wants_json():
            return jsonify(
                ref=ref, status="planned" if quote.ok else "blocked",
                was=quote.before_total, now=quote.after_total,
                difference=quote.difference,
                blockers=quote.blockers, notes=quote.notes,
                changed=[{"question": c.question, "from": _plain(c.before),
                          "to": _plain(c.after)} for c in quote.changed],
                moved=[{"service": mv.service, "was": mv.before,
                        "now": mv.after} for mv in quote.moved],
                scope=[{"field": c.question, "from": _plain(c.before),
                        "to": _plain(c.after)} for c in quote.scope_moved])
        return page("Update the quote",
                    requoted_body(ref, record, quote, changes))

    # ── signatures ────────────────────────────────────────────────────────
    # ── the shelf: pieces of this, one at a time ─────────────────────────
    #
    # The firm, 2 September 2026: "we have a lot of, what i would consider to
    # be, smaller functions. i would want to be able to re-print stuff, so
    # obviously i dont want to have to do an interview every time i make an
    # engagement letter. the GUI needs to have a way to use pieces of this
    # stuff ad hoc."
    #
    # And, on being told every one of those pieces would have to pass the
    # blocking gate first: "what we need to be able to also like print it or
    # something to screen - or a preview. something like it doesn't make sense
    # to forcibly have one output".
    #
    # TWO ACTS, TWO ANSWERS, and the split lives in `previewing` and `sending`
    # rather than here. Looking at a document is nobody's copy but yours, so it
    # is never blocked and always stamped. Sending one is the artefact a client
    # gets, so it goes through the same `sending.build` the pack goes through,
    # with the same gate, the same written reason and the same log.

    def _shelf_record(ref, doc=None):
        """This engagement, plus whatever the named document needs beside it."""
        record = cli.build_record(engagements.load(ref, st()))
        if doc is None:
            return record
        return invoicing.fold_in(record, [doc], st(), ref,
                                 request.args.get("invoice") or None)

    def _look(ref, doc):
        record = _shelf_record(ref, doc)
        return record, previewing.look(
            record, doc, merge_one=cli.merge_one, stamp=cli.stamp_preview,
            template_dir=cli.TEMPLATE_DIR,
            filename=cli.output_name(doc, record, False),
            tokens=cli.tokens_for(doc), labels=_field_labels())

    @app.get("/engagement/<ref>/documents")
    def shelf(ref):
        try:
            record = _shelf_record(ref)
        except (FileNotFoundError, ValueError, engagements.EngagementError):
            abort(404, f"no engagement {ref}")
        rows = []
        for doc in previewing.shelf(record):
            try:
                one = _shelf_record(ref, doc)
            except invoicing.InvoiceError:
                # No bill raised yet. The document is still on the shelf and
                # still worth looking at; it just has nothing to say yet.
                one = record
            look = previewing.look(
                one, doc, merge_one=cli.merge_one, stamp=cli.stamp_preview,
                template_dir=cli.TEMPLATE_DIR,
                filename=cli.output_name(doc, one, False),
                tokens=cli.tokens_for(doc), labels=_field_labels())
            rows.append((doc, look))
        if wants_json():
            return jsonify(ref=ref, documents=[
                {"document": d, "label": cli.DOCUMENTS[d][1], "ready": lk.ready,
                 "alone": lk.alone, "wanting": lk.wanting,
                 "blocking": len(lk.blocking)} for d, lk in rows])
        return page("Documents", shelf_body(ref, record, rows))

    @app.get("/engagement/<ref>/documents/<doc>")
    def one_document(ref, doc):
        if doc not in cli.DOCUMENTS:
            abort(404, "no such document")
        try:
            record, look = _look(ref, doc)
        except (FileNotFoundError, ValueError, engagements.EngagementError):
            abort(404, f"no engagement {ref}")
        except invoicing.InvoiceError as exc:
            if wants_json():
                return jsonify(ref=ref, document=doc, error=str(exc)), 409
            return page(cli.DOCUMENTS[doc][1],
                        document_body(ref, doc, None, None, problem=str(exc)))
        if wants_json():
            return jsonify(
                ref=ref, document=doc, ready=look.ready, alone=look.alone,
                why_not_alone=look.why_not_alone, wanting=look.wanting,
                blocking=[{"check": f.check, "document": f.document,
                           "detail": f.detail} for f in look.blocking])
        return page(cli.DOCUMENTS[doc][1],
                    document_body(ref, doc, record, look))

    # THE TRAILING SLASH IS LOAD-BEARING. Every template links `satc-doc.css`
    # and `doc-page.js` by relative path, so the address the document is served
    # at decides where the browser looks for them -- and at `.../page` it looks
    # one level too high and finds nothing. A document served without its
    # stylesheet is the "these html files are plain text?" bug, arriving by a
    # new door.
    @app.get("/engagement/<ref>/documents/<doc>/page/")
    def one_document_page(ref, doc):
        """The document itself, so a browser can open it, read it and print it.

        Served as the page rather than described on one: the whole point of
        looking at something is looking at it.
        """
        if doc not in cli.DOCUMENTS:
            abort(404, "no such document")
        try:
            _, look = _look(ref, doc)
        except (FileNotFoundError, ValueError, engagements.EngagementError):
            abort(404, f"no engagement {ref}")
        except invoicing.InvoiceError as exc:
            abort(409, str(exc))
        return look.html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @app.get("/engagement/<ref>/documents/<doc>/page/<asset>")
    def one_document_asset(ref, doc, asset):
        """The two files every document links. Which two is not decided here."""
        found = previewing.asset(cli.TEMPLATE_DIR, asset)
        if found is None:
            abort(404, "no such file")
        kind = ("text/css" if found.suffix == ".css"
                else "application/javascript")
        return found.read_text(encoding="utf-8"), 200, \
            {"Content-Type": f"{kind}; charset=utf-8"}

    @app.post("/engagement/<ref>/documents/<doc>")
    def send_one_document(ref, doc):
        """SENDING, which is the other act entirely. Same gate as the pack."""
        if doc not in cli.DOCUMENTS:
            abort(404, "no such document")
        try:
            record = _shelf_record(ref, doc)
        except (FileNotFoundError, ValueError, engagements.EngagementError):
            abort(404, f"no engagement {ref}")
        except invoicing.InvoiceError as exc:
            if wants_json():
                return jsonify(ref=ref, document=doc, status="error",
                               detail=str(exc)), 409
            return page(cli.DOCUMENTS[doc][1],
                        document_body(ref, doc, None, None,
                                      problem=str(exc))), 409

        allowed, why = previewing.alone_ok(record, doc)
        if not allowed:
            if wants_json():
                return jsonify(ref=ref, document=doc, status="with-the-pack",
                               detail=why), 409
            return page(cli.DOCUMENTS[doc][1],
                        sent_body(ref, doc, record, None, refused=why)), 409

        body = request.get_json(silent=True) if request.is_json else None
        form = body if body is not None else request.form
        want_pdf = True
        try:
            cli.pdf_engine()
        except cli.NoPdfEngine:
            want_pdf = False

        pack = sending.build(
            record, st() / ref / "documents" / doc, render=cli.render_one,
            ref=record.get("EngagementRef") or ref, store=st(),
            template_dir=cli.TEMPLATE_DIR, documents=[doc], want_pdf=want_pdf,
            force=bool(form.get("force")),
            reason=(form.get("reason") or "").strip())

        if wants_json():
            return jsonify(
                ref=ref, document=doc, status=pack.status,
                written=sorted(f.name for fs in pack.written.values()
                               for f in fs),
                blocking=[{"check": f.check, "document": f.document,
                           "detail": f.detail}
                          for f in (pack.check.blocking if pack.check else [])],
                override=pack.override,
                detail=pack.detail), (200 if pack.ok else 409)
        return page(cli.DOCUMENTS[doc][1], sent_body(ref, doc, record, pack))

    #
    # THE HALF THAT PAYS. Sending a pack is three minutes of clicking in
    # whatever portal the letters name; knowing which clients have not signed,
    # and which are past the date they were given, is what nothing supported.
    # So the sweep is a screen of its own and the home page links it.

    @app.get("/signatures")
    def signatures_waiting():
        rows = signing.waiting(st(), template_dir=cli.TEMPLATE_DIR)
        if wants_json():
            return jsonify(waiting=[
                {"ref": w.ref, "client": w.client, "sent": w.sent,
                 "days": w.waiting_days(), "overdue": w.overdue,
                 "outstanding": [str(l) for l in w.missing],
                 "examined": w.examined} for w in rows])
        return page("Signatures", waiting_body(rows))

    def _sig_state(ref):
        record = engagements.load(ref, st())
        docs = packaging.documents_for(record)
        saved = lifecycle.load_saved(ref, "delivery", st()) or {}
        deadline = (saved.get("answers") or {}).get("signature_deadline", "")
        return record, docs, signing.standing(
            ref, record, docs, cli.TEMPLATE_DIR, store=st(), deadline=deadline)

    @app.get("/engagement/<ref>/signatures")
    def signatures_for(ref):
        try:
            record, docs, where = _sig_state(ref)
        except (engagements.EngagementError, FileNotFoundError):
            abort(404, f"no engagement {ref}")
        gate = signing.may_file(ref, record, docs, cli.TEMPLATE_DIR,
                               store=st(), deadline=where.deadline)
        if wants_json():
            return jsonify(
                ref=ref, sent=where.sent, days=where.waiting_days(),
                overdue=where.overdue, examined=where.examined,
                outstanding=[str(l) for l in where.missing],
                signed=[s.line() for s in where.have],
                blockers=gate.blockers, unknown=gate.unknown)
        return page("Signatures", signatures_body(ref, record, where, gate))

    @app.post("/engagement/<ref>/signatures")
    def record_signature_for(ref):
        try:
            record, docs, where = _sig_state(ref)
        except (engagements.EngagementError, FileNotFoundError):
            abort(404, f"no engagement {ref}")
        body = request.get_json(silent=True) if request.is_json else None
        form = body if body is not None else request.form

        problem = ""
        try:
            if form.get("sent"):
                signing.mark_sent(ref, form.get("sent"),
                                  when=(form.get("on") or "").strip(),
                                  store=st())
            else:
                want = form.get("line") or ""
                line = next((ln for ln in where.expected
                             if ln.key() == want), None)
                if line is None:
                    problem = ("that signature line is not one this engagement "
                               "is waiting for.")
                else:
                    signing.record_signature(
                        ref, line, when=(form.get("on") or "").strip(),
                        how=form.get("how") or "",
                        reference=(form.get("reference") or "").strip(),
                        store=st())
        except signing.SigningError as exc:
            problem = str(exc)

        if problem and wants_json():
            return jsonify(ref=ref, status="refused", detail=problem), 400
        record, docs, where = _sig_state(ref)
        gate = signing.may_file(ref, record, docs, cli.TEMPLATE_DIR,
                               store=st(), deadline=where.deadline)
        if wants_json():
            return jsonify(ref=ref, status="recorded",
                           outstanding=[str(l) for l in where.missing])
        return page("Signatures",
                    signatures_body(ref, record, where, gate,
                                    problem=problem)), (400 if problem else 200)

    # ── the money out ─────────────────────────────────────────────────────
    #
    # READ-ONLY, DELIBERATELY. Asking the processor whether a bill was paid is
    # a network call and belongs to `cli.py payments`, which a person runs when
    # they want the answer. This screen shows what was written down last time
    # it ran -- so a browser with no internet still tells you where you stand,
    # and nothing here can hang waiting on Square.

    @app.get("/payments")
    def money_out():
        rows = []
        for folder in sorted(st().glob("*/invoices")):
            ref = folder.parent.name
            for bill in invoicing.issued_for(st(), ref):
                rows.append({
                    "ref": ref,
                    "invoice": bill.get("InvoiceNumber", ""),
                    "amount": bill.get("AmountDue", ""),
                    "date": bill.get("InvoiceDate", ""),
                    "settled": bill.get("SettledOn", ""),
                    "url": bill.get("PaymentUrl", ""),
                    # A SHORT PAYMENT LOOKS EXACTLY LIKE AN UNPAID BILL unless
                    # this page says otherwise: both are unsettled. Money did
                    # arrive, and somebody needs to chase the difference rather
                    # than wait for a client who thinks they have paid.
                    "short": (bill.get("_payment") or {}).get("short_by") or 0,
                })
        rows.sort(key=lambda r: (bool(r["settled"]), r["invoice"]))
        if wants_json():
            return jsonify(bills=rows)
        return page("Payments", payments_body(rows))

    return app


# ── rendering ─────────────────────────────────────────────────────────────
#
# Deliberately plain: server-rendered HTML, no build step, no framework, in the
# brand's own tokens. It is the same choice `website/` makes, for the same
# reason -- a front door with a toolchain is a front door that stops working.

CSS = """
/* `--await` is the third colour, and it means one thing: the software is
   declining to invent a sentence and waiting on the firm. Navy is the firm
   acting, oxblood is a refusal, and `[CONFIRM: ...]` is neither -- it had been
   wearing the refusal's colour, which taught whoever read the page that a
   decision waiting on them was a thing that had gone wrong.
   From `satc-handoff/06-APP/satc-app.css`. Measured against the brand's own
   greyscale test: navy and oxblood are 1.47:1 in black and white, and this is
   2.06:1 from oxblood -- better, still not enough on its own, which is why
   every use of it is paired with a shape as well (a filled chip, a left rule).
   THE MONO STACK IS THE SYSTEM'S. "IBM Plex Mono" was named here and no
   webfont was ever loaded, so every screen has always rendered in whatever the
   machine had; saying so is the difference between a design that works offline
   and one that happens to. The documents a CLIENT opens are a different
   surface and keep Plex -- `presend` opens each one and fails it if the type
   is not the firm's. */
:root{--navy:#132437;--oxblood:#6A2833;--await:#A8571C;--ink:#242C36;
--ink-2:#4A5360;
--mute:#82817C;--hairline:#D8D7D1;--hairline-2:#E6E5E0;--paper:#FCFCFA;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font:15px/1.55 var(--sans)}
/* VISIBLE FOCUS, IN THE COLOUR THAT MEANS "WAITING ON YOU". Only inputs had
   one; a button or a link reached by keyboard showed whatever the browser
   chose, which on a navy button is nearly nothing. This is a tool driven from
   a keyboard with a client in the chair. */
:focus-visible{outline:2px solid var(--await);outline-offset:2px}
header{background:var(--navy);color:#fff;padding:14px 28px}
header a{color:#fff;text-decoration:none;letter-spacing:.02em;font-weight:600}
main{max-width:660px;margin:0 auto;padding:34px 28px 80px}
h1{font-size:21px;line-height:1.3;margin:0 0 6px;font-weight:600}
.sec{font:11px/1 var(--mono);letter-spacing:.14em;
text-transform:uppercase;color:var(--ink-2);margin:0 0 18px}
.help{color:var(--ink-2);margin:0 0 20px;font-size:14px}
label{display:block;padding:9px 12px;border:1px solid var(--hairline);
border-radius:2px;margin-bottom:7px;cursor:pointer;background:#fff}
label:hover{border-color:var(--navy)}
input[type=text],input[type=number],textarea{width:100%;padding:10px 12px;
border:1px solid var(--hairline);border-radius:2px;font:inherit;background:#fff}
input:focus,textarea:focus{outline:2px solid var(--navy);outline-offset:-1px}
button{font:inherit;padding:9px 18px;border-radius:2px;border:1px solid var(--navy);
background:var(--navy);color:#fff;cursor:pointer}
button.ghost{background:#fff;color:var(--navy)}
.claim{background:var(--hairline-2);border-left:2px solid var(--navy);
padding:9px 12px;margin:0 0 14px;font-size:14px}
.claim.bad{border-left-color:var(--oxblood)}
.err{color:var(--oxblood);margin:0 0 14px;font-size:14px}
.row{display:flex;gap:9px;align-items:center;margin-top:20px}
/* A button never wraps its own label — a flex row will squeeze one
   into two lines the moment a sentence sits beside it. */
.row button{flex:none;white-space:nowrap}
.bar{height:3px;background:var(--hairline-2);margin:0 0 14px;border-radius:2px}
.bar i{display:block;height:3px;background:var(--navy);border-radius:2px;
transition:width .18s ease}
.crumb{display:flex;justify-content:space-between;align-items:baseline;
gap:14px;margin:0 0 18px}
.crumb .sec{margin:0}
.crumb .count{font:11px/1 var(--mono);letter-spacing:.08em;
color:var(--mute);flex:none}
.crumb form{margin:0;flex:none}
.crumb .sec{flex:1}
/* A control that changes nothing on its own reads as text, not as a slab of
   navy competing with the answer the question is actually asking for. */
button.link{background:none;border:0;padding:0;color:var(--ink-2);font:inherit;
font-size:12.5px;cursor:pointer;text-decoration:underline;
text-underline-offset:3px}
button.link:hover{color:var(--navy)}
td.fix{width:1%;white-space:nowrap;text-align:right}
.quitrow{margin-top:14px}
/* The gate's own report, verbatim. It is a fixed-width table of check names
   and denominators, and reflowing it as prose would lose the alignment that
   makes a SKIP or a NONE findable at a glance. */
/* The gate's report as a table, not a transcript: a mark you can find, the
   check's own words, and the count it examined to say it. */
table.checks th{font:inherit;font-size:14px;text-transform:none;
letter-spacing:0;color:var(--ink);font-weight:400;width:auto}
/* The mark is now an object of its own (`.mk`), so the cell only has to
   hold it. Four colour rules lived here and each one had to be kept in step
   with the vocabulary by hand -- S6, on a small scale. */
table.checks td.mkc{width:1%;white-space:nowrap;vertical-align:top;
padding-top:7px}
table.checks td.den{width:1%;white-space:nowrap;text-align:right;
font-size:13px;color:var(--ink-2)}
@media (max-width:560px){table.checks td.den{white-space:normal}}
.hardno li{margin-bottom:9px;font-size:14px;color:var(--ink-2)}
.hardno li b{color:var(--oxblood);font-weight:600}
table{border-collapse:collapse;width:100%;font-size:14px}
td,th{text-align:left;padding:7px 10px;border-bottom:1px solid var(--hairline-2)}
th{font:11px/1 var(--mono);letter-spacing:.1em;
text-transform:uppercase;color:var(--ink-2)}
iframe.doc{width:min(96vw,980px);height:820px;border:1px solid #d9d4cc;
  background:#fff;margin:8px 0 22px;display:block;
  margin-left:calc(50% - min(48vw,490px))}
td.act{white-space:nowrap}
.hardno{border:1px solid var(--oxblood);border-left-width:3px;padding:14px 16px;
margin:0 0 20px}
.hardno h2{color:var(--oxblood);font-size:15px;margin:0 0 8px}
/* A review note is not a refusal. It gets the navy rule, not the oxblood
   one, because dressing "have a look at this" like "we do not take this
   work" teaches whoever reads the page to dismiss both. */
.note{border:1px solid var(--navy);border-left-width:3px;padding:14px 16px;
margin:0 0 20px}
.note h2{color:var(--navy);font-size:15px;margin:0 0 8px}
.note li{font-size:14px;color:var(--ink-2)}
.muted{color:var(--ink-2);font-size:14px}
code{font-family:var(--mono);font-size:13px}
/* IN A CELL AS WELL AS A HEADER. It was styled under `th` alone, so the same
   span inside a `td` rendered inline and unstyled -- the payments screen read
   "2026-00012026-0001", the invoice number and the engagement ref run
   together. Found by looking at the screenshot. */
th .fname,td .fname{display:block;font:10px/1.4 var(--mono);
letter-spacing:.06em;color:var(--mute);text-transform:none;margin-top:2px}
table.plain th{text-transform:none;font-family:inherit;font-size:14px;
letter-spacing:0;color:var(--ink);font-weight:500;width:52%}
.lead{display:flex;gap:16px;align-items:center;justify-content:space-between;
padding:15px 0 13px}
.lead .who{min-width:0}
.lead .who b{display:block;font-size:16px;color:var(--navy);font-weight:600}
.lead .gist{display:block;font-size:13.5px;color:var(--ink-2);margin-top:2px}
.lead .count{display:block;font:10.5px/1.6 var(--mono);
letter-spacing:.08em;color:var(--mute)}
.lead form{flex:none;margin:0}
@media (max-width:520px){.lead{display:block}.lead form{margin-top:11px}}
/* The "what they told us" panel is secondary to the row above it, and says
   so: a smaller, quieter summary that plainly opens. */
details.blk.quiet summary{padding:7px 2px 13px;font-size:11px}
details.blk.quiet summary .count::before{content:"+ "}
details.blk.quiet[open] summary .count::before{content:"\2212 "}
details.blk{border-bottom:1px solid var(--hairline-2)}
details.blk summary{cursor:pointer;list-style:none;padding:13px 2px;
display:flex;justify-content:space-between;align-items:baseline;gap:14px;
font:12px/1.3 var(--mono);letter-spacing:.1em;
text-transform:uppercase;color:var(--ink-2)}
details.blk summary::-webkit-details-marker{display:none}
details.blk summary:hover{color:var(--navy)}
details.blk summary b{color:var(--oxblood);font-weight:500}
details.blk[open] summary{color:var(--navy)}
details.blk .count{color:var(--mute);letter-spacing:.06em;flex:none}
details.blk .st{flex:1}
details.blk form{padding:4px 0 20px}
/* The manual door is a row, not a section header: it carries a real title,
   a line saying when you would want it, and something that looks pressable. */
details.blk.door summary{padding:15px 2px 13px;font:inherit;letter-spacing:0;
text-transform:none;color:var(--ink);align-items:center}
details.blk.door summary .st b{display:block;font-size:16px;color:var(--navy);
font-weight:600}
details.blk.door summary .st span{display:block;font-size:13.5px;
color:var(--ink-2);margin-top:2px}
.asbtn{flex:none;padding:9px 18px;border:1px solid var(--navy);border-radius:2px;
background:#fff;color:var(--navy);font-size:15px;line-height:1.55}
details.blk.door[open] summary .asbtn{background:var(--hairline-2)}
@media (max-width:520px){details.blk.door summary{display:block}
.asbtn{display:inline-block;margin-top:11px}}
/* A caption a field keeps. Placeholders read as labels until you type. */
.f{margin:0 0 12px}
label.fl{display:block;padding:0;margin:0 0 4px;border:0;background:none;
cursor:default;font:11px/1.4 var(--mono);letter-spacing:.08em;
text-transform:uppercase;color:var(--mute)}
details.blk textarea{font-size:14px;line-height:1.55;margin-bottom:4px}
.fieldrow{margin:0 0 14px;color:var(--mute)}
b.late{color:var(--oxblood);font-weight:600}
.locked{border-left:2px solid var(--hairline);padding:2px 0 2px 12px;
margin:0 0 16px;font-size:14px;color:var(--ink-2)}
/* ── every number says what it counted ─────────────────────────────
   The engine has refused since August to let a check that examined nothing
   look like a check that passed (S2). On screen that rule was bare prose. The
   count and what it counted are one element, so a bare number cannot be
   written with this class -- and `.tally.empty` is the case worth having: it
   says so in words and never shows a zero. */
.tally{font:400 12.5px/1.5 var(--mono);color:var(--ink-2);letter-spacing:.01em}
.tally b{color:var(--navy);font-weight:500}
.tally.empty,.tally.empty b{color:var(--mute)}
/* A COUNT INSIDE A HEADING IS STILL A HEADING. "Not sent. 1 check stopped it"
   read with two of its five words in small grey monospace -- the object is
   right and its own type was fighting the sentence it sits in. Found by
   photographing the blocked gate and looking at it. */
h1 .tally,h2 .tally,h1 .tally b,h2 .tally b{font:inherit;color:inherit;
letter-spacing:inherit}
/* And in the check table the chip carries the longest word in the vocabulary
   ("nothing to look at"), which at full size squeezed every check name into
   three lines in a 660px column. */
table.checks .mk{font-size:9.5px;padding:4px 6px 3px;letter-spacing:.07em}
/* ── five things a line can be, and they do not look alike ─────────
   Blocked, waiting-on-you, fine, examined-nothing and not-built were three
   shades of one grey. FILLED MEANS IT NEEDS A PERSON: oxblood for a refusal,
   the third colour for a decision. Outlines are facts. The difference between
   `stop` and `notyet` is carried by the border, not the colour, so it survives
   being read from three feet away and survives being read in greyscale. */
.mk{display:inline-block;font:500 10.5px/1 var(--mono);letter-spacing:.09em;
text-transform:uppercase;padding:5px 8px 4px;border:1px solid;border-radius:2px;
white-space:nowrap}
.mk.pass{color:var(--ink-2);border-color:var(--hairline);
background:var(--hairline-2)}
.mk.stop{color:#fff;border-color:var(--oxblood);background:var(--oxblood)}
.mk.wait{color:#fff;border-color:var(--await);background:var(--await)}
.mk.none{color:var(--mute);border-color:var(--hairline);background:none}
.mk.notyet{color:var(--ink-2);border-color:var(--hairline);
border-style:dashed;background:none}
.mk.done{color:var(--navy);border-color:var(--navy);background:none}
/* ── what the software refused to invent ───────────────────────────
   `[CONFIRM: ...]` is not an error and must stop looking like one. The
   placeholder is quoted exactly as it will print, because that is the string
   somebody has to go and replace. */
.ask{border:1px solid var(--await);border-left-width:3px;border-radius:2px;
background:#FDF6F0;padding:15px 18px;margin:0 0 20px}
.ask h2{color:var(--await);margin:0 0 5px;font-size:15px}
.ask p{margin:0;font-size:14px;color:var(--ink-2)}
.ask .said{font:400 13.5px/1.6 var(--mono);color:var(--ink);background:#fff;
border:1px solid #EBD9CA;padding:9px 12px;margin-top:10px;border-radius:2px;
display:block}
.said{color:var(--await);font-family:var(--mono);font-size:13px}
/* An option the firm does not take is the only row on the question with a
   coloured edge, and the consequence is beside it rather than under it.
   `HARD NO` in bold red inside an ordinary box read as emphasis; this reads
   as a different kind of thing. */
label.no{border-color:var(--oxblood);border-left-width:3px}
label.no .tag{font:500 10px/1 var(--mono);letter-spacing:.09em;
text-transform:uppercase;color:var(--oxblood);float:right;white-space:nowrap}
"""


def esc(s) -> str:
    from markupsafe import escape
    return str(escape("" if s is None else s))


def tally(n: int, one: str, many: str = "", *, nothing: str = "") -> str:
    """A number and what it counted, as one element.

    S2, ON A SCREEN. The engine has refused since August to let a check that
    examined nothing look like a check that passed; the pages said so in prose,
    which is a sentence somebody has to remember to write beside every number.
    Here the count and the noun it counted are the SAME element, so a bare
    number cannot be rendered through this and a caller that forgets the noun
    does not compile.

    `nothing` is what to say when there was nothing to count, and it is the
    case worth having: "0 checks" and "we did not look" are the same words for
    two different worlds, so a zero is never printed as a zero.

    THE BRACKET-S GOES. `11 check(s)` is a machine talking to a person -- the
    plural is one line of Python and it is the difference between software
    written for you and software generated at you.
    """
    if not n and nothing:
        return f"<span class='tally empty'>{esc(nothing)}</span>"
    word = one if n == 1 else (many or one + "s")
    return f"<span class=tally><b>{n:,}</b> {esc(word)}</span>"


# What a check's `document` field says, and what a preparer would call it.
# `presend` names the thing it looked at, which for a rendered document is the
# FILE -- "SAT-C Engagement Letter - Reyes - 2026.html". That is a filename on
# a screen, and the file it names is the one thing on the page nobody can do
# anything about (S35). The sentinels are the software's own words for a scope.
_WHOLE_PACK = {"(all)": "every document in the pack",
               "(pack)": "the pack as a whole",
               "(templates)": "the letter wording",
               "(registry)": ""}


def _document_named(raw: str, files: dict | None = None) -> str:
    """The document a finding is about, as somebody would go and open it.

    `files` maps a rendered file's name to the document's own label. Anything
    that still looks like a file after that is dropped rather than shown: the
    detail beside it already says what happened, and a filename says nothing a
    person can act on. Dropping it is visible -- the row simply names no
    document -- which is the failure mode to prefer over printing one nobody
    asked for.
    """
    raw = str(raw or "")
    if not raw:
        return ""
    if raw in _WHOLE_PACK:
        return _WHOLE_PACK[raw]
    named = (files or {}).get(raw)
    if named:
        return named
    return "" if ("." in raw or "/" in raw) else raw


def _check_labels(check) -> dict:
    """`{a finding's own check key: the name the check is listed under}`.

    ONE CHECK, TWO NAMES, ON ONE PAGE. The table calls it "no banned legalese
    and no British spelling"; the failure above it called it **plain**, which
    is the key `presend` tags its findings with and is not a sentence. So the
    thing that stopped the pack and the row explaining it did not look like
    the same check -- S3, on a screen, and the only place a preparer meets it
    is the morning something is blocked.

    Derived from `Result.counts` rather than kept as a second list here,
    because a second list is what would go stale (S6).
    """
    out = {}
    for what, got in (getattr(check, "counts", None) or []):
        for finding in got.findings:
            out.setdefault(finding.check, what)
    return out


def _written_labels(pack) -> dict:
    """`{rendered file name: the document's label}` for one pack.

    `sending.build` fills `written` BEFORE the gate runs, so this is populated
    on a refusal as well as on a success -- which is the case that matters,
    because a refusal is the screen that names a failing document.
    """
    out = {}
    for doc, paths in (getattr(pack, "written", None) or {}).items():
        label = cli.DOCUMENTS.get(doc, ("", doc))[1]
        for path in paths:
            out[Path(path).name] = label
    return out


def page(title: str, body: str) -> str:
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title if title != 'SAT-C' else 'Engagements')}"
            f" · SAT-C</title><style>{CSS}</style></head>"
            f"<body><header><a href='/'>SAT-C</a></header><main>{body}</main>"
            f"</body></html>")


def prices_body(prices) -> str:
    """Every price the engine charges, grouped as the schedule groups them.

    `published` is shown because it is the difference between changing a
    number and changing something a stranger can read on satcllp.com, and
    that difference should be visible before the click, not after.
    """
    out = ["<h1>What the firm charges</h1>",
           # "read from fee-schedule.yaml" told a preparer the name of a
           # file they are on this screen precisely so they never have to
           # open. What matters is the consequence, which the second
           # sentence already says.
           "<p class=muted>Every figure the firm charges. Changing one here "
           "changes the estimate, the letters and the website together.</p>"]
    where = None
    for pr in prices:
        if pr.where != where:
            where = pr.where
            out.append(f"<h2>{esc(where)}</h2><table>"
                       "<tr><th>What</th><th>Now</th><th>On the site?</th></tr>")
        out.append(
            f"<tr><td><a href='/prices/{esc(pr.path)}'>{esc(pr.label)}</a>"
            f"<br><code class=muted>{esc(pr.path)}</code></td>"
            f"<td><b>${pr.amount}</b></td>"
            f"<td>{'Published' if pr.published else '<span class=muted>Withheld</span>'}</td></tr>")
        if pr is prices[-1] or prices[prices.index(pr) + 1].where != where:
            out.append("</table>")
    return "".join(out)


def price_body(price, *, report=None, saved=False, error="") -> str:
    """One price, with what changing it would do said out loud."""
    # The path is kept -- it is how a person finds this figure again among a
    # hundred -- but it is labelled as what it is rather than as a filename
    # and a line number, which is a developer's way of pointing at a thing.
    out = [f"<h1>{esc(price.label)}</h1>",
           f"<p class=muted>In the fee schedule at "
           f"<code>{esc(price.path)}</code></p>"]
    if price.published:
        out.append("<p class=claim><b>This figure is on satcllp.com.</b> "
                   "Changing it changes what a stranger reads.</p>")
    if error:
        # `.claim.bad` is this app's existing shape for a refusal -- an
        # invented class name renders as an unstyled paragraph, which is how a
        # refusal ends up looking like a note.
        out.append(f"<p class='claim bad'>{esc(error)}</p>")
    if report:
        out.append("<p class=claim>"
                   + ("<b>Saved.</b> " if saved else "<b>Not saved yet.</b> ")
                   + f"${report['from']} &rarr; <b>${report['to']}</b>")
        if "sample_total_before" in report:
            out.append(f"<br>The demo engagement&rsquo;s quote: "
                       f"{esc(report['sample_total_before'])} &rarr; "
                       f"<b>{esc(report['sample_total_after'])}</b>")
        out.append("</p>")
    out.append(
        f"<form method=post action='/prices/{esc(price.path)}'>"
        f"<label>Amount in dollars<br>"
        f"<input name=amount value='{price.amount}' inputmode=numeric autofocus></label>"
        f"<p><button name=preview value=1 class=ghost>Show me what changes</button> "
        f"<button>Save</button></p></form>"
        f"<p><a href='/prices'>All prices</a></p>")
    return "".join(out)


def index_body(rows, drafts) -> str:
    out = ["<h1>Engagements</h1>"]
    if rows:
        out.append("<table><tr><th>Ref</th><th>Client</th><th>Period</th></tr>")
        for r in rows:
            out.append(f"<tr><td><a href='/engagement/{esc(r['ref'])}'>"
                       f"<code>{esc(r['ref'])}</code></a></td>"
                       f"<td>{esc(r['client'])}</td>"
                       f"<td>{esc(r.get('period',''))}</td></tr>")
        out.append("</table>")
    else:
        out.append("<p class=muted>None yet.</p>")
    if drafts:
        out.append("<h1 style='margin-top:32px'>Unfinished sittings</h1>")
        for d in drafts:
            who = d["who"] or "Nobody named yet"
            bits = [f"{d['answered']} answered"]
            if d["started"]:
                bits.append(f"started {esc(d['started'])}")
            out.append(
                f"<div class=lead><div class=who><b>{esc(who)}</b>"
                f"<span class=gist>{' &middot; '.join(bits)}</span></div>"
                f"<a href='/interview/{esc(d['id'])}'>"
                f"<button type=button class=ghost>Pick it back up</button></a>"
                f"</div>")
    out.append("<form method=post action='/interview' class=row>"
               "<button>Start an interview</button>"
               "<a href='/leads' style='margin-left:4px'>"
               "<button type=button class=ghost>Leads</button></a>"
               "<a href='/signatures' style='margin-left:4px'>"
               "<button type=button class=ghost>Waiting to sign</button></a>"
               "<a href='/payments' style='margin-left:4px'>"
               "<button type=button class=ghost>Payments</button></a>"
               "<a href='/templates' style='margin-left:4px'>"
               "<button type=button class=ghost>Letter wording</button></a>"
               "</form>")
    return "".join(out)



def leads_body(rows, path, problem="") -> str:
    out = ["<h1>Leads</h1>",
           "<p class=help>Everything a prospect told us, before the sitting "
           "starts &mdash; so nobody discovers halfway down that there is a "
           "rental. Start an interview from one, or take a lead by phone.</p>"]
    if problem:
        out.append(f"<p class=err>{esc(problem)}</p>")
    if not rows:
        out.append(f"<p class=muted>No workbook at <code>{esc(str(path))}</code>. "
                   f"Drop the export there, or take one by phone below.</p>")
    for i, lead in enumerate(rows):
        c = lead.get("contact") or {}
        who = c.get("name") or c.get("email") or "(no name)"
        num = lead.get("_lead_number") or ""
        # WHAT THEY WANT, ON THE ROW. A name alone gives a preparer nothing to
        # choose between when four people are waiting.
        gist = next((v for label, v in leads.summary(lead)
                     if label.lower().startswith(("service", "what"))), "")
        where = c.get("location") or ""
        sub = " &middot; ".join(esc(x) for x in (gist, where) if x)

        # THE ACTION IS ON THE ROW, NOT INSIDE IT. These were collapsed
        # disclosures with no chevron and no hint: the names read as static
        # text, the "start" button lived inside, and the only way to discover
        # it was to click something that did not look clickable. A browser
        # automation could not find it either.
        out.append(
            f"<div class=lead>"
            f"<div class=who><b>{esc(who)}</b>"
            + (f"<span class=gist>{sub}</span>" if sub else "")
            + (f"<span class=count>{esc(num)}</span>" if num else "")
            + f"</div>"
            f"<form method=post action='/interview'>"
            f"<input type=hidden name=lead_index value='{i}'>"
            f"<button>Start the interview</button></form>"
            f"</div>"
            f"<details class='blk quiet'><summary>"
            f"<span class=st>What {esc(who)} told us</span>"
            f"<span class=count>show</span></summary><table class=plain>")
        for label, value in leads.summary(lead):
            out.append(f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>")
        out.append("</table></details>")

    # THE MANUAL DOOR, IN THE SAME VOICE AS THE ROWS ABOVE IT. It used to be
    # a mono-caps "TAKE ONE BY PHONE / MANUAL" bar sitting under names set in
    # 16px — the one row a preparer needs when the phone is actually ringing,
    # and the only one on the page that looked like plumbing. Same row shape,
    # same size, and the fields carry captions instead of placeholders, which
    # disappear the moment you start typing.
    out.append(
        "<details class='blk door'><summary><span class=st>"
        "<b>Nobody on this list — they called</b>"
        "<span>Type in what they gave you on the phone and start from "
        "there.</span></span>"
        "<span class=asbtn>Take it by phone</span></summary>"
        "<form method=post action='/interview'>"
        "<input type=hidden name=by_hand value=1>"
        "<div class=f><label class=fl for=ph-name>Name they gave</label>"
        "<input type=text id=ph-name name=name></div>"
        "<div class=f><label class=fl for=ph-email>Email</label>"
        "<input type=text id=ph-email name=email></div>"
        "<div class=f><label class=fl for=ph-phone>Phone</label>"
        "<input type=text id=ph-phone name=phone></div>"
        "<div class=f><label class=fl for=ph-loc>Where they are</label>"
        "<input type=text id=ph-loc name=location placeholder='Solon, OH'></div>"
        "<div class=f><label class=fl for=ph-notes>What they said</label>"
        "<textarea id=ph-notes name=notes rows=2></textarea></div>"
        "<div class=row><button>Start an interview</button>"
        "<span class=muted>A name, an email or a phone number is enough. "
        "The interview asks the rest.</span></div></form></details>")
    return "".join(out)


def templates_body(rows) -> str:
    out = ["<h1>Wording</h1>",
           "<p class=help>Open a template, open a section, change a sentence. "
           "Everything else about the document &mdash; the layout, which blocks "
           "appear, what the fields are &mdash; stays where it is.</p>",
           "<table><tr><th>Template</th><th>Sections</th><th>Editable</th></tr>"]
    for r in rows:
        out.append(f"<tr><td><a href='/templates/{esc(r['file'])}'>"
                   f"{esc(r['title'])}</a></td>"
                   f"<td>{r['sections']}</td>"
                   f"<td>{r['editable']} of {r['blocks']}</td></tr>")
    out.append("</table>")
    return "".join(out)


def template_body(name, secs, saved="", error="", open_id="") -> str:
    out = [f"<h1>{esc(name.replace('SATC ', '').replace('.html', ''))}</h1>",
           # "the registry's business" told a preparer that something they
           # cannot see has jurisdiction over what they are editing. Say what
           # the thing IS instead: a blank the client's own details drop into.
           "<p class=help>Click a section to open it. "
           "<code>**bold**</code> makes a phrase bold. "
           "<code>&lt;&lt;LikeThis&gt;&gt;</code> is a blank that fills in "
           "with the client's own details when the letter is written &mdash; "
           "you can move the words around it, but leave it in place. Adding a "
           "new one is a change to what the letter asks for, not to how it "
           "reads.</p>"]
    if error:
        out.append(f"<p class=err>{esc(error)}</p>"
                   "<p class=muted>Nothing was saved. A section saves whole or "
                   "not at all, so the rest of it is as you left it.</p>")
    elif saved == "none":
        out.append("<p class=claim>Nothing to save &mdash; the wording was "
                   "already what is on the page.</p>")
    elif saved:
        said = (f"Saved {len(saved.split(','))} change"
                f"{'s' if len(saved.split(',')) != 1 else ''}."
                if re.fullmatch(r"[\w.,]+", saved) else saved)
        out.append(f"<p class=claim>{esc(said)} "
                   f"<a href='/templates'>Back to the templates</a>, or render "
                   f"an engagement to see it on a document.</p>")

    for s in secs:
        head = (f"<span class=st><b>{esc(s.number)}</b>&nbsp;&nbsp;{esc(s.title)}</span>"
                if s.number else f"<span class=st>{esc(s.title)}</span>")
        n = sum(1 for b in s.blocks if b.editable)
        is_open = " open" if s.id == open_id else ""
        out.append(f"<details class=blk id='{esc(s.id)}'{is_open}>"
                   f"<summary>{head}<span class=count>{n} "
                   f"sentence{'s' if n != 1 else ''}</span></summary>"
                   f"<form method=post action='/templates/{esc(name)}'>"
                   f"<input type=hidden name=section value='{esc(s.id)}'>")
        for b in s.blocks:
            if not b.editable:
                out.append(f"<div class=locked><p>{esc(b.text[:200])}</p>"
                           f"<p class=muted>Read-only &mdash; {esc(b.reason)}</p></div>")
                continue
            rows = max(2, min(10, len(b.text) // 78 + 1))
            fields = " ".join(f"<code>&lt;&lt;{esc(f)}&gt;&gt;</code>" for f in b.fields)
            out.append(f"<textarea name='t:{esc(b.id)}' rows={rows}>{esc(b.text)}</textarea>")
            if fields:
                out.append(f"<p class=fieldrow>{fields}</p>")
        out.append("<div class=row><button>Save this section</button>")
        if s.number:
            out.append(f"<span class=muted style='flex:1'></span>")
        out.append("</div></form>")
        if s.number:
            out.append(
                f"<form method=post action='/templates/{esc(name)}/sections' "
                f"class=cut><input type=hidden name=remove value='{esc(s.number)}'>"
                f"<button class=ghost>Take this section out</button>"
                f"<span class=muted>The rest renumber. A client should never "
                f"see 03 followed by 05.</span></form>")
        out.append("</details>")

    numbered = [s for s in secs if s.number]
    if numbered:
        opts = "".join(f"<option value='{esc(s.number)}'>after {esc(s.number)} "
                       f"&middot; {esc(s.title)}</option>" for s in numbered)
        out.append(
            f"<details class='blk add'><summary><span class=st>"
            f"Add a section</span><span class=count>new</span></summary>"
            f"<form method=post action='/templates/{esc(name)}/sections'>"
            f"<div class=f><label class=fl for=new-title>Heading &mdash; what "
            f"a client points at</label>"
            f"<input type=text id=new-title name=title required></div>"
            f"<div class=f><label class=fl for=new-text>What it says</label>"
            f"<textarea id=new-text name=text rows=3 placeholder='"
            f"**bold** works here. A &lt;&lt;Blank&gt;&gt; does not — a new "
            f"section cannot ask the client for something new.' "
            f"required></textarea></div>"
            f"<div class=f><label class=fl for=new-after>Where it goes</label>"
            f"<select id=new-after name=after>{opts}"
            f"<option value=''>at the end</option></select></div>"
            f"<div class=row><button>Add it</button></div></form></details>")
    return "".join(out)


def question_body(sid, section, q, claim, acceptable, session, error="", said="",
                  current=None, back="") -> str:
    total = len(list(iv.all_questions(session.schema)))
    done = len(session.answers)
    # SAY THE NUMBER. A 2px rule tells a preparer sitting with a client
    # roughly nothing; "6 of 24" tells them whether to offer more coffee.
    # `total` is the whole schema, so it can only shrink as branches are
    # ruled out -- which is why it reads "of about", not "of".
    # WHERE THE SITTING IS. When a preparer stepped back, the count is the
    # position of the question being fixed, not the end of the pile -- and it
    # says so, because "38 of about 52" on a screen you reached by pressing
    # Back reads as if the sitting lost its place.
    order = session.asked()
    place = order.index(q["id"]) + 1 if q["id"] in order else done + 1
    out = [f"<div class=bar><i style='width:{int(100*done/max(total,1))}%'></i></div>",
           "<div class=crumb>"]
    if back:
        out.append(f"<form method=post action='/interview/{esc(sid)}/back'>"
                   f"<button class=link>&larr; Back</button></form>")
    out.append(f"<span class=sec>{esc(section['title'])}</span>"
               f"<span class=count>"
               + (f"changing {place} of {len(order)}" if current is not None
                  else f"{place} of about {total}")
               + "</span></div>")
    out.append(f"<h1>{esc(q['question'])}</h1>")
    if q.get("help"):
        out.append(f"<p class=help>{esc(q['help'])}</p>")
    if error:
        out.append(f"<p class=err>{esc(error)}</p>")

    if claim not in (None, "", []):
        if acceptable:
            whence = (f" when they asked about {esc(said)}" if said else "")
            out.append(f"<p class=claim>The website said <b>{esc(claim)}</b>"
                       f"{whence}. Accept it, or answer differently.</p>")
        else:
            out.append(f"<p class='claim bad'>The website said "
                       f"<b>{esc(claim)}</b> &mdash; not a valid answer here, "
                       f"so it needs a real one.</p>")

    out.append(f"<form method=post action='/interview/{esc(sid)}'>")
    t = q["type"]
    # AN ANSWER YOU CAME BACK TO IS SHOWN AS IT STANDS. Stepping back to a
    # blank form asks a preparer to remember what they typed, in front of the
    # client who said it -- and a mistyped digit is invisible until it is on
    # the page beside the corrected one.
    held = [] if current is None else (
        [str(x) for x in current] if isinstance(current, list) else [str(current)])
    shown_value = "" if current is None else (
        ", ".join(held) if isinstance(current, list) else str(current))
    if t in ("single", "multi"):
        kind = "radio" if t == "single" else "checkbox"
        for o in q.get("options", []):
            # THE CONSEQUENCE, NOT AN EMPHASIS. `HARD NO` in bold red inside
            # an ordinary box reads as the same kind of thing as every other
            # option, shouted. These are the only rows on the page with a
            # coloured edge, and what happens if you tick one is written
            # beside the tick rather than found out after it.
            no = bool(o.get("hard_no"))
            mark = "<span class=tag>the firm says no</span>" if no else ""
            on = " checked" if str(o["value"]) in held else ""
            out.append(f"<label{' class=no' if no else ''}>"
                       f"<input type={kind} name=answer "
                       f"value='{esc(o['value'])}'{on}> "
                       f"{esc(o['label'])}{mark}</label>")
    elif t == "textarea":
        out.append(f"<textarea name=answer rows=4>{esc(shown_value)}</textarea>")
    elif t == "number":
        out.append(f"<input type=number name=answer min=0 "
                   f"value='{esc(shown_value)}'>")
    else:
        hint = " (comma-separated)" if t == "list" else ""
        out.append(f"<input type=text name=answer autofocus "
                   f"value='{esc(shown_value)}' "
                   f"placeholder='{esc(hint.strip())}'>")

    out.append("<div class=row><button>"
               + ("Save the change" if current is not None else "Next")
               + "</button>")
    if claim not in (None, "", []) and acceptable:
        # THE BUTTON SAYS THE ANSWER IT WILL GIVE. "Accept the claim" is our
        # word for it, not a preparer's -- the firm's own example of a control
        # somebody would look at and ask why they would ever use it. Showing
        # the value turns it into the obvious thing to press when the website
        # got it right.
        shown = ", ".join(claim) if isinstance(claim, list) else str(claim)
        if len(shown) > 28:
            shown = shown[:27].rstrip() + "\u2026"
        out.append(f"<button class=ghost name=accept value=1>"
                   f"Use &ldquo;{esc(shown)}&rdquo;</button>")
    if not q.get("required"):
        out.append("<span class=muted>&nbsp;or leave blank to skip</span>")
    out.append("</div></form>")
    # ITS OWN FORM, AFTER THE ANSWER'S. Forms do not nest, and a stray
    # `accept=1` posted at the back route would step a sitting somewhere
    # nobody asked for.
    if current is not None:
        out.append(f"<form method=post action='/interview/{esc(sid)}/back' "
                   f"class=quitrow>"
                   f"<input type=hidden name=resume value=1>"
                   f"<button class=link>Never mind &mdash; nothing to "
                   f"change</button></form>")
    return "".join(out)


def review_body(sid, session, blockers) -> str:
    out = ["<h1>Review</h1>"]
    if blockers:
        out.append("<div class=hardno><h2>HARD NO flagged</h2><ul>")
        for b in blockers:
            out.append(f"<li>{esc(b)}</li>")
        out.append("</ul><p class=muted>This is work the firm does not take. "
                   "Creating anyway needs a deliberate override.</p></div>")
    # The QUESTION, not its id. This table used to read `federal_form | 1040`,
    # which is the software's name for the thing rather than the thing. The
    # question text is already plain English and already written, so nothing
    # new has to be maintained alongside it.
    # WHAT THE ANSWERS COME TO, before what the answers were. The sitting no
    # longer asks which schedules a return needs -- it asks about the client's
    # year and works them out -- so the derivation is the thing a preparer has
    # to look at, and it is shown with the fact behind each line rather than
    # as a list to take on trust.
    derived = sched.derive(session.answers, session.schema)
    if derived.schedules:
        out.append('<div class="note"><h2>What that comes to</h2><table class=plain>')
        for s, why in derived.because:
            out.append(f"<tr><th>{esc(sched.LABELS.get(s, s))}</th>"
                       f"<td>{esc(why)}</td></tr>")
        out.append("</table><p class=muted>Worked out from the answers below. "
                   "Change an answer and this changes with it.</p></div>")

    asked = {q["id"]: q["question"] for _, q in iv.all_questions(session.schema)}
    # THE LABEL A PREPARER TICKED, NOT THE KEY UNDERNEATH IT. This table read
    # `missing_records` and `self_employment, rentals, k1` -- the software's
    # names for the options, on the last screen anybody checks before a client
    # is billed. The labels are already written in the schema.
    labels = {q["id"]: {str(o["value"]): o["label"] for o in q.get("options", [])}
              for _, q in iv.all_questions(session.schema)}
    # EVERY ROW IS A WAY BACK TO IT. The review was the one page that showed a
    # preparer a wrong answer and gave them nothing to do about it but start
    # the sitting again.
    editable = set(session.asked())
    out.append("<table class=plain>")
    for k, v in session.answers.items():
        seen = labels.get(k, {})
        if isinstance(v, list):
            shown = ", ".join(seen.get(str(x), str(x)) for x in v)
        else:
            shown = seen.get(str(v), "" if v is None else str(v))
        # A blank cell reads as "nobody answered this". These were answered --
        # with nothing, which is a different fact and has to say so.
        blank = not str(shown).strip()
        fix = ""
        if k in editable:
            fix = (f"<form method=post action='/interview/{esc(sid)}/back'>"
                   f"<input type=hidden name=to value='{esc(k)}'>"
                   f"<button class=link>Change</button></form>")
        cell = "<span class=muted>left blank</span>" if blank else esc(shown)
        out.append(f"<tr><th>{esc(asked.get(k, k))}</th>"
                   f"<td>{cell}</td><td class=fix>{fix}</td></tr>")
    out.append("</table>")
    out.append(f"<form method=post action='/interview/{esc(sid)}/finish' class=row>"
               "<button>Create the engagement</button>")
    if blockers:
        out.append("<button class=ghost name=override value=1>"
                   "Override the HARD NO</button>")
    out.append("</form>")
    return "".join(out)


def _flag_block(outcome) -> str:
    """Preparer-facing, on whichever page the outcome lands on.

    Not styled as a blocker: nothing here stops anything, and dressing a
    review note as a refusal teaches whoever reads it to dismiss both.
    """
    if not outcome.flags:
        return ""
    out = ["<div class=note><h2>Worth a look before this is quoted</h2><ul>"]
    for f in outcome.flags:
        out.append(f"<li>{esc(f)}</li>")
    out.append("</ul></div>")
    return "".join(out)


def outcome_body(sid, outcome) -> str:
    if outcome.created:
        return (f"<h1>Engagement {esc(outcome.ref)} created</h1>"
                f"<p class=muted>The interview is saved alongside the record, "
                f"so a year from now you can see why each document says what it "
                f"says.</p>"
                + ("<p class=muted>A HARD NO was overridden.</p>"
                   if outcome.overridden else "")
                + _flag_block(outcome)
                + f"<form method=get action='/engagement/{esc(outcome.ref)}"
                  f"/package' class=row>"
                  f"<button>Build the signing pack</button>"
                  f"<a href='/engagement/{esc(outcome.ref)}'>"
                  f"<button type=button class=ghost>Open the engagement"
                  f"</button></a>"
                  f"<a href='/'><button type=button class=ghost>Home</button>"
                  f"</a></form>")
    heading = {"refused": "Not taken on", "declined": "No engagement created",
               "error": "Could not price it"}.get(outcome.status, "Stopped")
    out = [f"<h1>{esc(heading)}</h1>"]
    if outcome.blockers:
        out.append("<div class=hardno><h2>HARD NO flagged</h2><ul>")
        for b in outcome.blockers:
            out.append(f"<li>{esc(b)}</li>")
        out.append("</ul></div>")
    out.append(_flag_block(outcome))
    out.append(f"<p class=help>{esc(outcome.reason)}</p>")
    # SAY WHAT "nothing" MEANS. A bare "Nothing was written" leaves a
    # preparer wondering what might have been half-done.
    out.append(f"<p class=muted>Nothing was written &mdash; no engagement, "
               f"no price, no documents.</p>"
               f"<p><a href='/interview/{esc(sid)}'>Back to the interview</a> "
               f"&middot; <a href='/'>Home</a></p>")
    return "".join(out)


@lru_cache(maxsize=1)
def _field_labels() -> dict:
    """Merge field -> what it is, in plain English. From the registry, so the
    label sits beside the field it names rather than in a table over here."""
    import yaml
    path = ROOT / "registry" / "fields.yaml"
    reg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = {}
    # Flags and lists reach a record the same way fields do, and read the same
    # way on the page. `SCorpElection` and `ReturnScope` were sitting under the
    # labelled fields with nothing but their own token.
    for kind, key in (("fields", "field"), ("flags", "flag"), ("lists", "list")):
        for e in reg.get(kind, []):
            out[e[key]] = e.get("label") or e[key]
    return out


def engagement_body(ref, record, open_now, revisions=()) -> str:
    out = [f"<h1>{esc(record.get('ClientFullName', ref))}</h1>",
           f"<p class=sec>{esc(ref)} &middot; "
           f"{esc(record.get('PeriodLabel',''))}</p>"]
    rows = ["<table class=plain>"]
    labels = _field_labels()
    waiting = []
    for k, v in record.items():
        if k.startswith("_") or isinstance(v, (list, dict)):
            continue
        # The label leads and the merge-field name follows it, small. A person
        # reading the record wants to know what the value IS; a person wiring
        # a template wants the token. Both are on the page, in that order.
        #
        # AND A `[CONFIRM: ...]` IS NOT AN ERROR. It is the software declining
        # to write a sentence that is the firm's to write, and it had been
        # sitting in the same ink as twenty-five settled facts -- so the one
        # row on the page that needs a person looked exactly like the rest.
        # It gets the third colour, which means that and nothing else.
        held = str(v)
        if "[CONFIRM:" in held:
            # THE LABEL ONLY IF THERE IS ONE. `labels.get(k, k)` falls back to
            # the merge field's own name, and putting that in the panel would
            # be a code identifier on a screen -- the exact thing this panel
            # is here to stop looking normal (S35). The placeholder's own
            # question is already the plain-English half.
            waiting.append((labels.get(k, ""), held))
            cell = f"<span class=said>{esc(held)}</span>"
        else:
            cell = esc(v)
        rows.append(f"<tr><th>{esc(labels.get(k, k))}"
                    f"<span class=fname>{esc(k)}</span></th>"
                    f"<td>{cell}</td></tr>")
    rows.append("</table>")
    # ABOVE THE RECORD, BECAUSE IT IS THE ONLY PART OF IT THAT NEEDS ANYBODY.
    # Twenty-six settled facts and one unwritten sentence read as twenty-seven
    # facts; the placeholder is quoted exactly as it will print, because that
    # is the string somebody has to go and replace.
    # AND THE ONES THAT ARE NOT ON THIS RECORD AT ALL. A `[CONFIRM: ...]` in
    # the firm's own settings is what actually stops most letters, and it
    # reaches a document at render time rather than sitting on the record --
    # so a panel that only read the record would have been a panel nothing
    # could ever fill (S14). `open_decisions` is the same list `doctor` reads;
    # `blocks_render` is the half of it that would refuse a document, and the
    # other half is policy that stops nothing and does not belong on a client's
    # page (S4).
    try:
        waiting += [(q, f"[CONFIRM: {q}]")
                    for path, q in firm.open_decisions()
                    if firm.blocks_render(path)]
    except Exception:                                          # noqa: BLE001
        # An unreadable settings file is `doctor`'s news to break, not this
        # page's. A client's record still has to be readable when it does.
        pass
    if waiting:
        one = len(waiting) == 1
        out.append("<div class=ask><h2>Waiting on you</h2>"
                   f"<p>{tally(len(waiting), 'sentence')} on this file "
                   + ("is yours to write" if one else "are yours to write")
                   + ", and the software will not invent "
                   + ("it" if one else "them")
                   + ". The letter can be built until then but not sent, and "
                     "it prints with "
                   + ("this" if one else "these")
                   + " in place of the words:</p>")
        for label, held in waiting:
            said = f"{esc(label)} &mdash; {esc(held)}" if label else esc(held)
            out.append(f"<p class=said>{said}</p>")
        out.append("</div>")
    out += rows
    # THE NEXT THING, ON THE PAGE THAT KNOWS IT. A door nothing links to is a
    # door nobody finds -- packaging was reachable only by typing a command,
    # and this is the screen a preparer is on when the pack is what is next.
    out.append(f"<form method=get action='/engagement/{esc(ref)}/package' "
               f"class=row><button>Build the signing pack</button>"
               f"<span class=muted>Every document this client signs, checked "
               f"before any of it goes out.</span></form>")
    # THE OTHER THING THAT HAPPENS TO A LIVE ENGAGEMENT, on the same screen.
    # A door nothing links to is a door nobody finds: packaging was reachable
    # only by typing a command until this page linked it, and re-quoting was
    # not reachable at all.
    out.append(f"<form method=get action='/engagement/{esc(ref)}/signatures' "
               f"class=row><button class=ghost>Signatures</button>"
               f"<span class=muted>Who still has to sign, and recording one "
               f"that has come back.</span></form>")
    out.append(f"<form method=get action='/engagement/{esc(ref)}/documents' "
               f"class=row><button class=ghost>Documents</button>"
               f"<span class=muted>Every document this file can produce, one "
               f"at a time &mdash; to read, to print, or to send. No "
               f"interview.</span></form>")
    out.append(f"<form method=get action='/engagement/{esc(ref)}/requote' "
               f"class=row><button class=ghost>Update the quote</button>"
               f"<span class=muted>The work changed &mdash; a second rental, "
               f"another K-1. See every line that moves before anything is "
               f"recorded.</span></form>")
    if record.get("LineItems"):
        out.append("<h1 style='margin-top:30px'>Fee estimate</h1><table>"
                   "<tr><th>Service</th><th>Amount</th></tr>")
        for i in record["LineItems"]:
            out.append(f"<tr><td>{esc(i['Service'])}</td>"
                       f"<td><code>{esc(i['Amount'])}</code></td></tr>")
        out.append(f"<tr><th>Total</th><td><code>"
                   f"{esc(record.get('EstimateTotal'))}</code></td></tr></table>")
    if revisions:
        # THE LOG, ON THE PAGE. `revisions.json` is append-only and nobody
        # would have found it. A price that moved and can only be explained by
        # opening a file in the store is a price nobody can defend on the
        # phone.
        out.append("<h1 style='margin-top:30px'>This quote has moved</h1>"
                   "<table><tr><th>When</th><th>Why</th><th>Was</th>"
                   "<th>Now</th></tr>")
        for entry in revisions:
            out.append(f"<tr><td>{esc(entry.get('when',''))}</td>"
                       f"<td>{esc(entry.get('reason',''))}</td>"
                       f"<td><code>{esc(entry.get('was',''))}</code></td>"
                       f"<td><code>{esc(entry.get('now',''))}</code></td></tr>")
        out.append("</table>")
    return "".join(out)


def _plain(value) -> str:
    """A value as a person reads it. One function, so the page and the JSON
    say the same thing about the same answer."""
    if value in (None, "", []):
        return "(nothing)"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(x) for x in value)
    return str(value)


def _answer_control(q, held) -> str:
    """One question, showing what is on file, ready to be changed.

    The interview's own control for that type, and the answer already given is
    ALREADY SELECTED -- this screen is a correction, not a fresh sitting, and a
    blank form would ask a preparer to retype thirteen answers to change one.
    """
    t = q["type"]
    qid = esc(q["id"])
    marks = [] if held in (None, "", []) else (
        [str(x) for x in held] if isinstance(held, list) else [str(held)])
    shown = ", ".join(marks)
    out = []
    if t in ("single", "multi"):
        kind = "radio" if t == "single" else "checkbox"
        name = f"{qid}[]" if t == "multi" else qid
        for o in q.get("options", []):
            on = " checked" if str(o["value"]) in marks else ""
            out.append(f"<label><input type={kind} name='{name}' "
                       f"value='{esc(o['value'])}'{on}> {esc(o['label'])}</label>")
        if t == "single" and not q.get("required"):
            out.append(f"<label><input type=radio name='{qid}' value=''"
                       + ("" if marks else " checked")
                       + "> <span class=muted>not answered</span></label>")
    elif t == "number":
        out.append(f"<input type=number name='{qid}' min=0 "
                   f"value='{esc(shown)}'>")
    elif t == "textarea":
        out.append(f"<textarea name='{qid}' rows=3>{esc(shown)}</textarea>")
    else:
        out.append(f"<input type=text name='{qid}' value='{esc(shown)}'>")
    return "".join(out)


def requote_body(ref, record, questions, answers, problem="") -> str:
    """What can change, showing what it says today. Nothing is written here."""
    out = [f"<h1>Update the quote</h1>",
           f"<p class=sec>{esc(ref)} &middot; "
           f"{esc(record.get('ClientFullName',''))}</p>"]
    if problem:
        out.append(f"<p class=err>{esc(problem)}</p>")
    out.append("<p class=help>The work changed, so the price does. Change what "
               "is different and you will see every line that moves before "
               "anything is recorded. Nobody types a figure &mdash; the same "
               "schedule that priced this engagement prices it again.</p>")
    out.append(f"<p class=help><b>{esc(record.get('EstimateTotal',''))}</b> "
               f"is the figure on file, from "
               f"{esc(record.get('EstimateDate') or record.get('LetterDate',''))}"
               f".</p>")
    out.append(f"<form method=post action='/engagement/{esc(ref)}/requote'>")
    for q in questions:
        out.append(f"<input type=hidden name=_asked value='{esc(q['id'])}'>")
        out.append("<details class=blk "
                   "data-caption='the answer to one question'><summary>"
                   f"<b>{esc(q['question'])}</b>"
                   f"<span class=fname>{esc(_plain(answers.get(q['id'])))}"
                   f"</span></summary>")
        if q.get("help"):
            out.append(f"<p class=help>{esc(q['help'])}</p>")
        out.append(_answer_control(q, answers.get(q["id"])))
        out.append("</details>")
    out.append("<div class=row><button>See what changes</button>"
               "<span class=muted>Nothing is written yet.</span></div></form>")
    return "".join(out)


def requoted_body(ref, record, quote, changes, *, done=False,
                  problem="") -> str:
    """The plan, and the one box that writes it."""
    out = [f"<h1>{'The new quote is recorded' if done else 'What this changes'}"
           f"</h1>",
           f"<p class=sec>{esc(ref)} &middot; "
           f"{esc(record.get('ClientFullName',''))}</p>"]
    if problem:
        out.append(f"<p class=err>{esc(problem)}</p>")
    if quote.blockers:
        for line in quote.blockers:
            out.append(f"<p class=err>{esc(line)}</p>")
        out.append(f"<p><a href='/engagement/{esc(ref)}/requote'>"
                   f"Back to the answers</a></p>")
        return "".join(out)

    # THE QUESTION, NOT ITS NAME IN THE SOFTWARE. This read `COUNT_K1S` and
    # `ADDITIONAL_FORMS` down the left-hand side until somebody looked at the
    # screenshot. A preparer confirming a change with a client on the phone
    # reads out what was asked, and `pricing.spec.py` enforces the same rule
    # over the price page: nothing built out of our own vocabulary.
    out.append("<h2 class=sec>What changed in the interview</h2><table>")
    for change in quote.changed:
        out.append(f"<tr><th>{esc(requote._question_text(change.question))}"
                   f"<span class=fname>{esc(change.question)}</span></th>"
                   f"<td>{esc(_plain(change.before))} &rarr; "
                   f"<b>{esc(_plain(change.after))}</b></td></tr>")
    out.append("</table>")

    out.append("<h2 class=sec>The estimate</h2><table>"
               "<tr><th>Line</th><th>Was</th><th>Now</th></tr>")
    for mv in quote.moved:
        out.append(f"<tr><td>{esc(mv.service)}</td>"
                   f"<td><code>{esc(mv.before or '—')}</code></td>"
                   f"<td><code>{esc(mv.after or '— (gone)')}</code></td></tr>")
    if not quote.moved:
        out.append("<tr><td colspan=3 class=muted>no line moves</td></tr>")
    out.append(f"<tr><th>Total</th><td><code>{esc(quote.before_total)}</code>"
               f"</td><td><code>{esc(quote.after_total)}</code></td></tr>"
               f"</table>")
    out.append(f"<p class=help><b>{esc(quote.difference)}.</b></p>")

    if quote.scope_moved:
        # SAID SEPARATELY. The price is the headline; the scope is the thing
        # that gets missed, and it is on a letter the client has signed.
        out.append("<h2 class=sec>The engagement letter says something else "
                   "now</h2><table>")
        labels = _field_labels()
        for change in quote.scope_moved:
            out.append(f"<tr><th>"
                       f"{esc(labels.get(change.question, change.question))}"
                       f"<span class=fname>{esc(change.question)}</span></th>"
                       f"<td>{esc(_plain(change.before))} &rarr; "
                       f"<b>{esc(_plain(change.after))}</b></td></tr>")
        out.append("</table>")
    for note in quote.notes:
        out.append(f"<p class=help>{esc(note)}</p>")

    if done:
        out.append(f"<div class=row>"
                   f"<form method=get action='/engagement/{esc(ref)}/package'>"
                   f"<button>Build the pack again</button></form>"
                   f"<form method=get action='/engagement/{esc(ref)}'>"
                   f"<button class=ghost>Open the engagement</button></form>"
                   f"</div>")
        return "".join(out)

    out.append(f"<form method=post action='/engagement/{esc(ref)}/requote'>")
    for qid, value in changes.items():
        out.append(f"<input type=hidden name=_asked value='{esc(qid)}'>")
        for one in (value if isinstance(value, list) else [value]):
            name = f"{esc(qid)}[]" if isinstance(value, list) else esc(qid)
            out.append(f"<input type=hidden name='{name}' "
                       f"value='{esc('' if one is None else one)}'>")
    if any(isinstance(v, list) and not v for v in changes.values()):
        # An emptied multi-select carries no value field at all, so the hidden
        # block above draws nothing for it. `_asked` above is what survives,
        # and `iv.coerce` reads the absence back as the empty list.
        pass
    out.append("<div class=f><label class=fl for=why>Why did the price "
               "move?</label>"
               "<p class=help>One sentence, for whoever reads this engagement "
               "next year. A reason names the thing: &ldquo;bought a second "
               "rental in April&rdquo;. &ldquo;Updated&rdquo; is not a "
               "reason.</p>"
               "<textarea id=why name=reason rows=2 required></textarea>"
               "</div>"
               "<div class=row><button>Record the new quote</button>"
               f"<a class=muted href='/engagement/{esc(ref)}/requote'>"
               f"or go back and change something else</a></div></form>")
    return "".join(out)


def waiting_body(rows) -> str:
    """Who to chase, longest wait first. The morning screen."""
    out = ["<h1>Waiting on a signature</h1>"]
    if not rows:
        out.append("<p class=help>Nothing outstanding. Every engagement has "
                   "everything it is waiting for.</p>")
        return "".join(out)
    out.append(f"<p class=help>{tally(len(rows), 'engagement')}, longest "
               f"wait first. A row marked <b>overdue</b> is past the date that "
               f"client was given in writing.</p>")
    out.append("<table><tr><th>Engagement</th><th>Waiting</th>"
               "<th>Outstanding</th></tr>")
    for w in rows:
        days = w.waiting_days()
        # ALREADY MARKUP, SO IT IS NOT ESCAPED BELOW. The first cut of this
        # passed `tally()` through `esc()` and the column printed its own HTML
        # as words -- caught by photographing the screen, which is the only
        # thing that could have (S16). `not sent` is the only literal here and
        # carries nothing to escape.
        waited = tally(days, "day") if days is not None else "not sent"
        # A colour typed into markup is a colour no palette can move, and it
        # was already `var(--oxblood)` here rather than a hex only by luck --
        # the payments list beside it had a green declared nowhere.
        flag = " <b class=late>overdue</b>" if w.overdue else ""
        out.append(
            # THE LINK IS THE REF, THE NAME IS BESIDE IT -- the same pattern
            # the home page uses, and for a reason that is not cosmetic: the
            # walkthrough keys its notes on a control's label, and a label that
            # is a client's name is a different key on every capture. A ref is
            # recognised as an identifier and folded.
            f"<tr><td><a href='/engagement/{esc(w.ref)}/signatures'>"
            f"{esc(w.ref)}</a> <b>{esc(w.client)}</b></td>"
            f"<td>{waited}{flag}</td>"
            f"<td>{len(w.missing)} of {w.examined}<span class=fname>"
            + esc("; ".join(str(l) for l in w.missing[:3]))
            + ("…" if len(w.missing) > 3 else "") + "</span></td></tr>")
    out.append("</table>")
    return "".join(out)


def signatures_body(ref, record, where, gate, problem="") -> str:
    """One engagement: what is out, what is in, and the box that records one."""
    out = [f"<h1>Signatures</h1>",
           f"<p class=sec>{esc(ref)} &middot; "
           f"{esc(record.get('ClientFullName',''))}</p>"]
    if problem:
        out.append(f"<p class=err>{esc(problem)}</p>")

    days = where.waiting_days()
    if where.sent:
        out.append(f"<p class=help>Sent {esc(where.sent)}"
                   + (f", {tally(days, 'day')} ago" if days is not None else "")
                   + (f". Due {esc(where.deadline)}" if where.deadline else "")
                   + (" &mdash; <b>past that date</b>." if where.overdue else ".")
                   + "</p>")
    else:
        out.append("<p class=help>Not recorded as gone out. Until it is, "
                   "&ldquo;outstanding&rdquo; only means nobody has signed "
                   "yet &mdash; which on the morning you built the pack is not "
                   "a chase.</p>")
        out.append(f"<form method=post action='/engagement/{esc(ref)}/signatures'"
                   f" class=row>")
        out.append("<select name=sent>")
        for key, what in signing.SENT_BY().items():
            out.append(f"<option value='{esc(key)}'>{esc(what)}</option>")
        out.append("</select><button>It has gone out</button></form>")

    out.append("<h2 class=sec>Still to come back</h2>")
    if not where.missing:
        out.append("<p class=help>Everything this engagement is waiting for "
                   "has been signed.</p>")
    for line in where.missing:
        out.append(f"<details class=blk data-caption='one signature'>"
                   f"<summary><b>{esc(line.document)}</b>"
                   f"<span class=fname>{esc(line.who)}</span></summary>"
                   f"<form method=post "
                   f"action='/engagement/{esc(ref)}/signatures'>"
                   f"<input type=hidden name=line value='{esc(line.key())}'>"
                   f"<div class=f><label class=fl for='d{esc(line.key())}'>"
                   f"The day THEY signed</label>"
                   f"<input id='d{esc(line.key())}' type=text name=on "
                   f"placeholder='February 9, 2027'></div>"
                   f"<div class=f><label class=fl>How it reached you</label>")
        for key, what in signing.MEANS.items():
            out.append(f"<label><input type=radio name=how "
                       f"value='{esc(key)}'> {esc(what)}</label>")
        out.append(f"</div><div class=f><label class=fl "
                   f"for='r{esc(line.key())}'>Reference, for a signing "
                   f"service</label>"
                   f"<input id='r{esc(line.key())}' type=text "
                   f"name=reference placeholder='the envelope id'></div>"
                   f"<div class=row><button>Record it</button></div>"
                   f"</form></details>")

    if where.have:
        out.append("<h2 class=sec>Signed</h2><table>")
        for got in where.have:
            out.append(f"<tr><td>{esc(got.document)}</td>"
                       f"<td>{esc(got.when)}</td>"
                       f"<td>{esc(signing.MEANS.get(got.how, got.how))}</td>"
                       f"</tr>")
        out.append("</table>")

    if gate.blockers or gate.unknown:
        out.append("<h2 class=sec>Before this return is transmitted</h2>")
        for line in gate.blockers:
            out.append(f"<p class=err>{esc(line)}</p>")
        for line in gate.unknown:
            out.append(f"<p class=help><b>Not known here.</b> {esc(line)}</p>")
    return "".join(out)


def payments_body(rows) -> str:
    """Every bill, and whether the money has arrived."""
    out = ["<h1>Payments</h1>"]
    if not rows:
        out.append("<p class=help>No invoice has been raised yet.</p>")
        return "".join(out)
    owing = [r for r in rows if not r["settled"]]
    # THE POINT SURVIVES, THE COMMAND NAME DOES NOT. What a person needs to
    # know is that this page shows the last answer rather than a live one --
    # so a payment made an hour ago may not be here yet. Which command last
    # asked is the software's own business.
    out.append(f"<p class=help>{len(owing)} of {tally(len(rows), 'bill')} "
               f"unpaid, as of the last time the "
               f"card processor was asked. This page shows what was written "
               f"down then rather than asking now, so it never hangs waiting "
               f"on them &mdash; a payment made in the last few minutes may "
               f"not be here yet.</p>")
    out.append("<table><tr><th>Invoice</th><th>Amount</th><th>Raised</th>"
               "<th>Status</th></tr>")
    for r in rows:
        # FOUR THINGS CAN BE TRUE OF A BILL AND THREE OF THEM LOOKED ALIKE.
        # They now use the app's one vocabulary of marks, and the green that
        # used to mean "paid" is gone -- it was a fourth colour, declared
        # nowhere, meaning what an outline already means.
        #
        # PART PAID IS THE ONE THAT NEEDS A PERSON, and it is not a refusal:
        # money arrived and the arithmetic does not close, and only the firm
        # decides whether that is a short payment to chase, a fee agreed down,
        # or somebody paying in two halves. So it takes the third colour.
        # NO LINK is a fact about the bill, not a failure, so it is quiet.
        if r["settled"]:
            state = (f"<span class='mk done'>paid</span> "
                     f"<span class=muted>{esc(r['settled'])}</span>")
        elif r.get("short"):
            state = (f"<span class='mk wait'>your call</span> "
                     f"<span class=muted>${r['short'] / 100:,.2f} short</span>")
        elif r["url"]:
            state = (f"<span class='mk pass'>link sent</span> "
                     f"<a href='{esc(r['url'])}'>open it</a>")
        else:
            state = "<span class='mk none'>no link</span>"
        out.append(f"<tr><td><a href='/engagement/{esc(r['ref'])}'>"
                   f"{esc(r['invoice'])}</a>"
                   f"<span class=fname>{esc(r['ref'])}</span></td>"
                   f"<td><code>{esc(r['amount'])}</code></td>"
                   f"<td>{esc(r['date'])}</td><td>{state}</td></tr>")
    out.append("</table>")
    return "".join(out)


def package_body(ref, record, docs, *, with_invoice=False, problem="") -> str:
    """What is about to be built, before anything is."""
    out = [f"<h1>The signing pack</h1>",
           f"<p class=sec>{esc(ref)} &middot; "
           f"{esc(record.get('ClientFullName',''))}</p>"]
    if problem:
        out.append(f"<p class=err>{esc(problem)}</p>")
        return "".join(out)
    out.append("<p class=help>Everything this client signs, built in one go. "
               "Nothing is written until every document has rendered and every "
               "check has passed &mdash; so if something is wrong, you get "
               "nothing rather than half a pack. One of those checks opens "
               "every document in a browser to prove it is readable, so this "
               "takes about a minute.</p>")
    out.append("<div class=note><h2>What goes in it</h2><table class=plain>")
    for doc in docs:
        out.append(f"<tr><th>{esc(cli.DOCUMENTS[doc][1])}</th>"
                   f"<td>{esc(packaging.PURPOSE.get(doc, ''))}</td></tr>")
    out.append("</table></div>")
    out.append(f"<form method=post action='/engagement/{esc(ref)}/package'>"
               f"<label><input type=checkbox name=invoice value=1"
               + (" checked" if with_invoice else "") +
               "> Put the invoice in too</label>"
               "<label><input type=checkbox name=notes value=1> "
               "Also read the prose and tell me what it notices "
               "(nothing here can stop a pack)</label>"
               "<div class=row><button>Build the pack</button>"
               "<span class=muted>Then you get to look at every check before "
               "anything goes to anyone.</span></div></form>"
               # A MINUTE OF NOTHING READS AS A BROKEN BUTTON, and the second
               # click posts the form again. The page carries no other script;
               # this one only changes a label, and without it the form still
               # submits exactly as before.
               "<script>document.currentScript.previousElementSibling"
               ".addEventListener('submit',function(e){var b="
               "e.target.querySelector('button');b.textContent="
               "'Building \u2014 about a minute';});<\/script>")
    return "".join(out)


def packed_body(ref, record, pack, with_invoice, pdf_note="") -> str:
    """What the gate said, and what to do about it.

    THE FAILURES COME FIRST AND THEY NAME THEMSELVES. The terminal prints a
    check list and then the refusal underneath it; on a page that ordering
    puts the thing you have to act on below a wall of green.
    """
    out = ["<h1>The signing pack</h1>",
           f"<p class=sec>{esc(ref)} &middot; "
           f"{esc(record.get('ClientFullName',''))}</p>"]

    if pack.status == "not-ours":
        out.append(f"<div class=hardno><h2>That folder is somebody's</h2>"
                   f"<p>{esc(str(pack.outdir))} already has files in it that "
                   f"this did not write, so nothing was touched.</p></div>")
        return "".join(out)

    if pack.status == "refused-merge":
        out.append(f"<div class=hardno><h2>No pack written &mdash; "
                   f"{tally(len(pack.refused), 'document')} of "
                   f"{len(pack.documents)} would not build</h2>"
                   f"<p>A pack with a hole in it is worse than none: the "
                   f"client signs what arrived, and the rest turns up later "
                   f"saying something different.</p><ul>")
        for doc, why in pack.refused:
            out.append(f"<li><b>{esc(cli.DOCUMENTS[doc][1])}</b> &mdash; "
                       f"{esc(why)}</li>")
        out.append("</ul>")
        if pack.stale:
            out.append(f"<p><b>The folder still holds the pack written for "
                       f"{esc(pack.stale)}.</b> It is not this one and it has "
                       f"not been updated. Do not send it.</p>")
        out.append("</div>")
        return "".join(out)

    check = pack.check
    if pack.status in ("refused-gate", "no-reason", "not-logged"):
        named = _written_labels(pack)
        called = _check_labels(check)
        out.append(f"<div class=hardno><h2>Not sent. "
                   f"{tally(len(check.blocking), 'check')} stopped it</h2>"
                   f"<p>A pack that does not survive being opened is not a "
                   f"pack &mdash; it is a folder the client cannot read.</p>"
                   f"<ul>")
        for f in check.blocking:
            in_what = _document_named(f.document, named)
            where = f" &mdash; {esc(in_what)}" if in_what else ""
            out.append(f"<li><b>{esc(called.get(f.check, f.check))}</b>"
                       f"{where}<br>{esc(f.detail)}</li>")
        out.append("</ul></div>")
        if pack.status == "no-reason":
            out.append("<p class=err>Sending it anyway needs a reason written "
                       "down. An override nobody wrote a reason for is just a "
                       "quieter way to send a pack that did not pass.</p>")
        if pack.status == "not-logged":
            out.append(f"<p class=err>The override could not be recorded "
                       f"({esc(pack.detail)}), so the pack was not written. "
                       f"The record is the only thing that makes an override "
                       f"different from having no check at all.</p>")
        # THE OVERRIDE IS ON THE PAGE, AND IT COSTS A SENTENCE. The firm chose
        # blocking-with-a-logged-override; a gate a browser cannot override is
        # a gate a preparer works around by opening a terminal, which is the
        # one place nobody is watching.
        out.append(f"<form method=post action='/engagement/{esc(ref)}/package'>"
                   f"<input type=hidden name=force value=1>"
                   + (f"<input type=hidden name=invoice value=1>"
                      if with_invoice else "") +
                   "<div class=f><label class=fl for=why>Why is this going "
                   "out as it is?</label>"
                   "<textarea id=why name=reason rows=2></textarea></div>"
                   "<div class=row><button class=ghost>Send it past these "
                   "checks</button><span class=muted>Goes in this "
                   "engagement's record, with the checks it failed.</span>"
                   "</div></form>")
        out.append(_checks_block(check))
        return "".join(out)

    out.append(f"<p class=help>{tally(len(pack.written), 'document')}, "
               f"built and checked. Nothing has been sent.</p>"
               # THE FOLDER STAYS UNTIL THERE IS A SEND BUTTON. A path on a
               # screen is normally the software talking about itself (S35) --
               # but nothing in the browser sends a pack, so this is the only
               # thing on the page that tells a preparer where the files they
               # have to attach actually are. It moves out of the headline and
               # says what it is for; it does not disappear.
               f"<p class=muted>They are waiting in "
               f"<code>{esc(str(pack.outdir))}</code> for you to attach "
               f"them.</p>")
    if pdf_note:
        out.append(f"<p class=muted>No PDF engine here ({esc(pdf_note)}), so "
                   f"this is the HTML only.</p>")
    if pack.override:
        out.append(f"<div class=note><h2>Sent past a failed check</h2>"
                   f"<p>Recorded in this engagement's record: "
                   f"<code>{esc(pack.override)}</code></p></div>")
    out.append("<table class=plain>")
    for doc in pack.documents:
        files = ", ".join(f.name for f in pack.written.get(doc, []))
        out.append(f"<tr><th>{esc(cli.DOCUMENTS[doc][1])}</th>"
                   f"<td>{esc(files)}</td></tr>")
    out.append("</table>")
    out.append(_checks_block(check))
    if pack.readings:
        out.append(f"<h1 style='margin-top:30px'>What the prose reads like</h1>"
                   f"<p class=help>Judgement calls, not rules. None of these "
                   f"can stop a pack.</p><ul>")
        for f in pack.readings:
            where = f" &mdash; {esc(f.document)}" if f.document else ""
            out.append(f"<li><b>{esc(f.check)}</b>{where}<br>"
                       f"{esc(f.detail)}</li>")
        out.append("</ul>")
    return "".join(out)


def shelf_body(ref, record, rows) -> str:
    """Every document this client's file can produce, and what each still needs.

    THE FIRM'S WORDS FOR IT: "the GUI needs to have a way to use pieces of this
    stuff ad hoc." This is the shelf. Nothing on it asks for an interview --
    everything here is built from answers that are already on file.
    """
    out = [f"<h1>Documents</h1>",
           f"<p class=sec>{esc(ref)} &middot; "
           f"{esc(record.get('ClientFullName',''))}</p>",
           "<p class=help>Everything this client's file can produce, without "
           "sitting down for another interview. Look at any of them. The ones "
           "that go out on their own can be sent from here; the rest travel "
           "with the signing pack.</p>",
           "<table><tr><th>Document</th><th>Where it stands</th>"
           "<th></th></tr>"]
    for doc, look in rows:
        if look.ready:
            state = "Ready"
            if not look.alone:
                state += " &mdash; goes out with the pack"
        elif look.wanting:
            state = "Still needs " + esc("; ".join(look.wanting).lower())
        else:
            state = "Not ready yet"
        out.append(f"<tr><td>{esc(cli.DOCUMENTS[doc][1])}</td>"
                   f"<td>{state}</td>"
                   f"<td class=act><a href='/engagement/{esc(ref)}"
                   f"/documents/{esc(doc)}'>Look at it</a></td></tr>")
    out.append("</table>")
    out.append(f"<form method=get action='/engagement/{esc(ref)}/package' "
               f"class=row><button class=ghost>Build the signing pack</button>"
               f"<span class=muted>Everything this client signs, in one go "
               f"&mdash; the way to get a fresh copy of the engagement "
               f"letter.</span></form>")
    return "".join(out)


def document_body(ref, doc, record, look, problem="") -> str:
    """One document, on screen, with everything known about it beside it.

    THE ORDER IS THE ORDER SOMEBODY READS IN. What is wrong comes first,
    because acting on it is the reason to be here; then the document itself,
    because that is what was asked for; then the checks, which are the detail
    behind the first part.
    """
    label = cli.DOCUMENTS[doc][1]
    out = [f"<h1>{esc(label)}</h1>",
           f"<p class=sec>{esc(ref)}</p>"]
    if problem:
        out.append(f"<div class=hardno><h2>Nothing to show yet</h2>"
                   f"<p>{esc(problem)}</p></div>")
        return "".join(out)

    out.append(f"<p class=sec>{esc(record.get('ClientFullName',''))}</p>")

    if not look.ready:
        out.append("<div class=hardno><h2>This one is not finished</h2>"
                   "<p>You can read it below, and every blank is marked. It "
                   "cannot go to the client until these are answered:</p><ul>")
        for line in look.wanting:
            out.append(f"<li>{esc(line)}</li>")
        out.append("</ul><p>There is no way to answer them here yet.</p>"
                   "</div>")

    if not look.alone:
        out.append(f"<div class=note><h2>This one goes out with the "
                   f"others</h2><p>{esc(look.why_not_alone)}</p></div>")

    out.append("<p class=help>This is a copy to read, not the copy that goes "
               "out &mdash; it says so on every page, so a sheet of it left on "
               "a desk cannot be mistaken for the real one. Open it on its own "
               "to print it.</p>")
    out.append(f"<p><a href='/engagement/{esc(ref)}/documents/{esc(doc)}"
               f"/page/' target=_blank>Open it on its own</a></p>")
    out.append(f"<iframe class=doc title='{esc(label)}' "
               f"src='/engagement/{esc(ref)}/documents/{esc(doc)}/page/'>"
               f"</iframe>")

    # WHAT FAILED IS NAMED WHEREVER IT FAILED. This block used to sit inside
    # the "can this be sent" branch, so a document that was not finished
    # showed FAIL in the table underneath and nothing at all above it --
    # which is the exact disagreement the packaging screen already has a test
    # against, arriving one screen over.
    if look.blocking:
        called = _check_labels(look.check)
        out.append(f"<div class=hardno><h2>{tally(len(look.blocking), 'check')}"
                   f" would stop this going out</h2><ul>")
        for f in look.blocking:
            out.append(f"<li><b>{esc(called.get(f.check, f.check))}</b><br>"
                       f"{esc(f.detail)}</li>")
        out.append("</ul></div>")

    if look.alone and not look.ready:
        out.append("<p class=muted>There is nothing to send yet. The blanks "
                   "listed at the top have to be answered first.</p>")
    if look.alone and look.ready:
        out.append(f"<form method=post action='/engagement/{esc(ref)}"
                   f"/documents/{esc(doc)}'>"
                   f"<div class=row><button>Send this one</button>"
                   f"<span class=muted>Checked first, the same way the pack "
                   f"is. Nothing is written unless it passes.</span></div>"
                   f"</form>")

    if look.check is not None:
        out.append(_checks_block(look.check))
        out.append("<p class=muted>Checked as though this were the only thing "
                   "in the envelope, which is why one of them can complain "
                   "about a letter that normally travels with others.</p>")
    return "".join(out)


def sent_body(ref, doc, record, pack, refused="") -> str:
    """What happened when somebody sent one document on its own."""
    label = cli.DOCUMENTS[doc][1]
    out = [f"<h1>{esc(label)}</h1>",
           f"<p class=sec>{esc(ref)} &middot; "
           f"{esc(record.get('ClientFullName','') if record else '')}</p>"]
    if refused:
        out.append(f"<div class=hardno><h2>Nothing was sent</h2>"
                   f"<p>{esc(refused)}</p></div>")
        return "".join(out)

    if pack.status == "not-ours":
        out.append(f"<div class=hardno><h2>That folder is somebody's</h2>"
                   f"<p>{esc(str(pack.outdir))} already has files in it that "
                   f"this did not write, so nothing was touched.</p></div>")
        return "".join(out)

    if pack.status == "refused-merge":
        out.append("<div class=hardno><h2>Nothing was written</h2>"
                   "<p>This document will not build as it stands.</p><ul>")
        for _, why in pack.refused:
            out.append(f"<li>{esc(why)}</li>")
        out.append("</ul></div>")
        return "".join(out)

    check = pack.check
    if pack.status in ("refused-gate", "no-reason", "not-logged"):
        named = _written_labels(pack)
        called = _check_labels(check)
        out.append(f"<div class=hardno><h2>Not sent. "
                   f"{tally(len(check.blocking), 'check')} stopped it</h2><ul>")
        for f in check.blocking:
            in_what = _document_named(f.document, named)
            where = f" &mdash; {esc(in_what)}" if in_what else ""
            out.append(f"<li><b>{esc(called.get(f.check, f.check))}</b>"
                       f"{where}<br>{esc(f.detail)}</li>")
        out.append("</ul></div>")
        if pack.status == "no-reason":
            out.append("<p class=err>Sending it anyway needs a reason written "
                       "down. An override nobody wrote a reason for is just a "
                       "quieter way to send something that did not pass.</p>")
        if pack.status == "not-logged":
            out.append(f"<p class=err>The override could not be recorded "
                       f"({esc(pack.detail)}), so nothing was sent. The record "
                       f"is the only thing that makes an override different "
                       f"from having no check at all.</p>")
        out.append(f"<form method=post action='/engagement/{esc(ref)}"
                   f"/documents/{esc(doc)}'>"
                   f"<input type=hidden name=force value=1>"
                   "<div class=f><label class=fl for=why>Why is this going "
                   "out as it is?</label>"
                   "<textarea id=why name=reason rows=2></textarea></div>"
                   "<div class=row><button class=ghost>Send it past these "
                   "checks</button><span class=muted>Goes in this "
                   "engagement's record, with the checks it failed.</span>"
                   "</div></form>")
        out.append(_checks_block(check))
        return "".join(out)

    out.append(f"<p class=help>Built and checked. It is in "
               f"<code>{esc(str(pack.outdir))}</code>.</p>")
    if pack.override:
        out.append(f"<div class=note><h2>Sent past a failed check</h2>"
                   f"<p>Recorded in this engagement's record: "
                   f"<code>{esc(pack.override)}</code></p></div>")
    out.append("<table class=plain>")
    for files in pack.written.values():
        for f in files:
            out.append(f"<tr><th>{esc(f.name)}</th><td></td></tr>")
    out.append("</table>")
    out.append(_checks_block(check))
    out.append(f"<p><a href='/engagement/{esc(ref)}/documents'>"
               f"Back to the documents</a></p>")
    return "".join(out)


def _checks_block(check, files: dict | None = None) -> str:
    """Every check, what it read, and what happens to you if it failed.

    A green line from a check that looked at nothing is worse than a red one,
    so the denominator comes with it -- it is what caught two blocking checks
    that had never examined anything on a real send.

    Read off `Result` rather than reusing the terminal's `format_result`: the
    facts are the same facts, but 90 columns of fixed-width text in a 660px
    page is a transcript you scroll sideways, and the mark you need to find is
    the one that fell off the right edge.

    THE MARKS SAY WHAT HAPPENS, NOT WHAT THE CHECK DID. `FAIL` describes the
    check; `stops it` describes the consequence to the person reading, which is
    the half they need. `ok` and `NONE` were two shades of the same grey and
    are the two that must never be confused -- one looked and was satisfied,
    the other examined nothing and knows nothing.
    """
    # WHICH CHECKS FAILED IS READ OFF `blocking`, NOT OFF EACH CHECK'S OWN
    # BUCKET. A finding that reached the result any other way would otherwise
    # be named at the top of the page as a failure and marked as fine in the
    # table underneath it -- caught by rendering this page and looking at it.
    failed = {f.check for f in check.blocking}
    out = [f"<h1 style='margin-top:30px'>Before sending</h1>",
           f"<p class=help>{tally(len(check.checked), 'check')}. "
           f"What each one read is on the right.</p>",
           "<table class='plain checks'>"]
    for what, got in check.counts:
        broke = what in failed or any(f.blocking for f in got.findings)
        if broke:
            mark, label, why = "stop", "stops it", f"{got.counted()} read"
        elif not got.examined:
            mark, label, why = "none", "nothing to look at", "nothing to read"
        else:
            mark, label, why = "pass", "fine", f"{got.counted()} read"
        out.append(f"<tr><td class=mkc><span class='mk {mark}'>{label}</span>"
                   f"</td><th>{esc(what)}</th>"
                   f"<td class=den>{esc(why)}</td></tr>")
    for what in check.skipped:
        out.append(f"<tr><td class=mkc><span class='mk notyet'>did not run"
                   f"</span></td><th>{esc(what)}</th>"
                   f"<td class=den>nothing is known about it</td></tr>")
    out.append("</table>")
    nothing = check.examined_nothing
    if nothing:
        out.append(f"<p class=muted>{tally(len(nothing), 'check')} had nothing "
                   f"to look at. Nothing is wrong with them. Nothing is known "
                   f"about them either.</p>")
    if check.skipped:
        out.append(f"<p class=muted>{tally(len(check.skipped), 'check')} did "
                   f"not run at all.</p>")
    return "".join(out)


if __name__ == "__main__":
    create_app().run(port=5051, debug=True)
