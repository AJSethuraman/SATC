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
import uuid
from datetime import date
from pathlib import Path

from flask import (Flask, abort, jsonify, redirect, request, url_for)

import engagements
import intake
import interview as iv
import settings as firm

DRAFTS = "_drafts"


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
    p = draft_path(store, sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def session_for(draft: dict) -> iv.Interview:
    return iv.Interview(lead=draft.get("lead"), answers=dict(draft["answers"]))


# ── the value a form field carries -> the value the schema expects ────────

def coerce(q: dict, raw) -> object:
    """A browser sends strings. The schema wants ints, lists and option values.

    Deliberately mirrors the CLI's parsing rather than inventing its own: both
    accept the option's `value`, and neither invents one that is not offered --
    an unknown option is passed through so `Interview.answer` rejects it, which
    is the same gate the terminal hits.
    """
    t = q["type"]
    if t in ("multi", "list"):
        values = raw if isinstance(raw, list) else \
            [p.strip() for p in (raw or "").split(",") if p.strip()]
        return values
    if t == "number":
        raw = (raw or "").strip() if isinstance(raw, str) else raw
        if raw in (None, ""):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw
    if isinstance(raw, str):
        raw = raw.strip()
    return raw or None


def create_app(store: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["STORE"] = Path(store) if store else engagements.STORE

    def st() -> Path:
        return app.config["STORE"]

    # ── index ─────────────────────────────────────────────────────────────

    @app.get("/")
    def index():
        rows = engagements.listing(st())
        drafts = sorted(p.stem for p in (st() / DRAFTS).glob("*.json")) \
            if (st() / DRAFTS).exists() else []
        if wants_json():
            return jsonify(engagements=rows, drafts=drafts)
        return page("SAT-C", index_body(rows, drafts))

    # ── start ─────────────────────────────────────────────────────────────

    @app.post("/interview")
    def start():
        lead = None
        if request.is_json:
            lead = (request.get_json(silent=True) or {}).get("lead")
        sid = uuid.uuid4().hex[:12]
        save_draft(st(), sid, {"lead": lead, "answers": {},
                               "started": date.today().isoformat()})
        if wants_json():
            return jsonify(draft=sid, next=url_for("show", sid=sid)), 201
        return redirect(url_for("show", sid=sid))

    # ── the current question ──────────────────────────────────────────────

    @app.get("/interview/<sid>")
    def show(sid):
        draft = load_draft(st(), sid)
        session = session_for(draft)
        nxt = session.next_question()

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
        if wants_json():
            return jsonify(draft=sid, complete=False, section=section["title"],
                           question=q, claim=claim, claim_acceptable=acceptable,
                           answered=len(session.answers))
        return page(q["question"], question_body(sid, section, q, claim,
                                                 acceptable, session))

    # ── answering ─────────────────────────────────────────────────────────

    @app.post("/interview/<sid>")
    def answer(sid):
        draft = load_draft(st(), sid)
        session = session_for(draft)
        nxt = session.next_question()
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
        except iv.InterviewError as exc:
            if wants_json():
                return jsonify(error=str(exc), question=q["id"]), 400
            return page(q["question"],
                        question_body(sid, nxt[0], q,
                                      iv.prefill_for(q, draft.get("lead")),
                                      iv.prefill_is_answerable(
                                          q, iv.prefill_for(q, draft.get("lead"))),
                                      session, error=str(exc))), 400

        draft["answers"] = session.answers
        save_draft(st(), sid, draft)
        if wants_json():
            return jsonify(draft=sid, saved=q["id"], next=url_for("show", sid=sid))
        return redirect(url_for("show", sid=sid))

    # ── finishing: straight through to the core ───────────────────────────

    @app.post("/interview/<sid>/finish")
    def finish(sid):
        draft = load_draft(st(), sid)
        override = bool(request.form.get("override")
                        or (request.get_json(silent=True) or {}).get("override"))

        # The ONLY decision-making call in this module, and it is a delegation.
        outcome = intake.finish(draft["answers"], store=st(),
                                override_hard_no=override)

        if outcome.created:
            draft_path(st(), sid).unlink(missing_ok=True)

        if wants_json():
            return jsonify(status=outcome.status, reason=outcome.reason,
                           blockers=outcome.blockers, ref=outcome.ref,
                           overridden=outcome.overridden), \
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
        return page(ref, engagement_body(ref, record, open_now))

    return app


# ── rendering ─────────────────────────────────────────────────────────────
#
# Deliberately plain: server-rendered HTML, no build step, no framework, in the
# brand's own tokens. It is the same choice `website/` makes, for the same
# reason -- a front door with a toolchain is a front door that stops working.

CSS = """
:root{--navy:#132437;--oxblood:#6A2833;--ink:#242C36;--ink-2:#4A5360;
--mute:#82817C;--hairline:#D8D7D1;--hairline-2:#E6E5E0;--paper:#FCFCFA}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font:15px/1.55 "IBM Plex Sans",-apple-system,Segoe UI,sans-serif}
header{background:var(--navy);color:#fff;padding:14px 28px}
header a{color:#fff;text-decoration:none;letter-spacing:.02em;font-weight:600}
main{max-width:660px;margin:0 auto;padding:34px 28px 80px}
h1{font-size:21px;line-height:1.3;margin:0 0 6px;font-weight:600}
.sec{font:11px/1 "IBM Plex Mono",monospace;letter-spacing:.14em;
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
.bar{height:2px;background:var(--hairline-2);margin:0 0 26px}
.bar i{display:block;height:2px;background:var(--navy)}
table{border-collapse:collapse;width:100%;font-size:14px}
td,th{text-align:left;padding:7px 10px;border-bottom:1px solid var(--hairline-2)}
th{font:11px/1 "IBM Plex Mono",monospace;letter-spacing:.1em;
text-transform:uppercase;color:var(--ink-2)}
.hardno{border:1px solid var(--oxblood);border-left-width:3px;padding:14px 16px;
margin:0 0 20px}
.hardno h2{color:var(--oxblood);font-size:15px;margin:0 0 8px}
.muted{color:var(--ink-2);font-size:14px}
code{font-family:"IBM Plex Mono",monospace;font-size:13px}
"""


def esc(s) -> str:
    from markupsafe import escape
    return str(escape("" if s is None else s))


def page(title: str, body: str) -> str:
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title if title != 'SAT-C' else 'Engagements')}"
            f" · SAT-C</title><style>{CSS}</style></head>"
            f"<body><header><a href='/'>SAT-C</a></header><main>{body}</main>"
            f"</body></html>")


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
        out.append("<h1 style='margin-top:32px'>Unfinished</h1><ul class=muted>")
        for d in drafts:
            out.append(f"<li><a href='/interview/{esc(d)}'>resume {esc(d)}</a></li>")
        out.append("</ul>")
    out.append("<form method=post action='/interview' class=row>"
               "<button>Start an interview</button></form>")
    return "".join(out)


def question_body(sid, section, q, claim, acceptable, session, error="") -> str:
    total = len(list(iv.all_questions(session.schema)))
    done = len(session.answers)
    out = [f"<div class=bar><i style='width:{int(100*done/max(total,1))}%'></i></div>",
           f"<p class=sec>{esc(section['title'])}</p>",
           f"<h1>{esc(q['question'])}</h1>"]
    if q.get("help"):
        out.append(f"<p class=help>{esc(q['help'])}</p>")
    if error:
        out.append(f"<p class=err>{esc(error)}</p>")

    if claim not in (None, "", []):
        if acceptable:
            out.append(f"<p class=claim>The website said <b>{esc(claim)}</b>. "
                       f"Accept it, or answer differently.</p>")
        else:
            out.append(f"<p class='claim bad'>The website said "
                       f"<b>{esc(claim)}</b> &mdash; not a valid answer here, "
                       f"so it needs a real one.</p>")

    out.append(f"<form method=post action='/interview/{esc(sid)}'>")
    t = q["type"]
    if t in ("single", "multi"):
        kind = "radio" if t == "single" else "checkbox"
        for o in q.get("options", []):
            mark = " &nbsp;<b style='color:var(--oxblood)'>HARD NO</b>" \
                if o.get("hard_no") else ""
            out.append(f"<label><input type={kind} name=answer "
                       f"value='{esc(o['value'])}'> {esc(o['label'])}{mark}</label>")
    elif t == "textarea":
        out.append("<textarea name=answer rows=4></textarea>")
    elif t == "number":
        out.append("<input type=number name=answer min=0>")
    else:
        hint = " (comma-separated)" if t == "list" else ""
        out.append(f"<input type=text name=answer autofocus "
                   f"placeholder='{esc(hint.strip())}'>")

    out.append("<div class=row><button>Next</button>")
    if claim not in (None, "", []) and acceptable:
        out.append("<button class=ghost name=accept value=1>Accept the claim</button>")
    if not q.get("required"):
        out.append("<span class=muted>&nbsp;or leave blank to skip</span>")
    out.append("</div></form>")
    return "".join(out)


def review_body(sid, session, blockers) -> str:
    out = ["<h1>Review</h1>"]
    if blockers:
        out.append("<div class=hardno><h2>HARD NO flagged</h2><ul>")
        for b in blockers:
            out.append(f"<li>{esc(b)}</li>")
        out.append("</ul><p class=muted>This is work the firm does not take. "
                   "Creating anyway needs a deliberate override.</p></div>")
    out.append("<table>")
    for k, v in session.answers.items():
        shown = ", ".join(str(x) for x in v) if isinstance(v, list) else v
        out.append(f"<tr><th>{esc(k)}</th><td>{esc(shown)}</td></tr>")
    out.append("</table>")
    out.append(f"<form method=post action='/interview/{esc(sid)}/finish' class=row>"
               "<button>Create the engagement</button>")
    if blockers:
        out.append("<button class=ghost name=override value=1>"
                   "Override the HARD NO</button>")
    out.append("</form>")
    return "".join(out)


def outcome_body(sid, outcome) -> str:
    if outcome.created:
        return (f"<h1>Engagement {esc(outcome.ref)} created</h1>"
                f"<p class=muted>The interview is saved alongside the record, "
                f"so a year from now you can see why each document says what it "
                f"says.</p>"
                + ("<p class=muted>A HARD NO was overridden.</p>"
                   if outcome.overridden else "")
                + f"<p><a href='/engagement/{esc(outcome.ref)}'>Open it</a> "
                  f"&middot; <a href='/'>Back</a></p>")
    heading = {"refused": "Not taken on", "declined": "No engagement created",
               "error": "Could not price it"}.get(outcome.status, "Stopped")
    out = [f"<h1>{esc(heading)}</h1>"]
    if outcome.blockers:
        out.append("<div class=hardno><h2>HARD NO flagged</h2><ul>")
        for b in outcome.blockers:
            out.append(f"<li>{esc(b)}</li>")
        out.append("</ul></div>")
    out.append(f"<p class=help>{esc(outcome.reason)}</p>")
    out.append(f"<p class=muted>Nothing was written.</p>"
               f"<p><a href='/interview/{esc(sid)}'>Back to the interview</a> "
               f"&middot; <a href='/'>Home</a></p>")
    return "".join(out)


def engagement_body(ref, record, open_now) -> str:
    out = [f"<h1>{esc(record.get('ClientFullName', ref))}</h1>",
           f"<p class=sec>{esc(ref)} &middot; {esc(record.get('PeriodLabel',''))}</p>",
           "<table>"]
    for k, v in record.items():
        if k.startswith("_") or isinstance(v, (list, dict)):
            continue
        out.append(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>")
    out.append("</table>")
    if record.get("LineItems"):
        out.append("<h1 style='margin-top:30px'>Fee estimate</h1><table>"
                   "<tr><th>Service</th><th>Amount</th></tr>")
        for i in record["LineItems"]:
            out.append(f"<tr><td>{esc(i['Service'])}</td>"
                       f"<td><code>{esc(i['Amount'])}</code></td></tr>")
        out.append(f"<tr><th>Total</th><td><code>"
                   f"{esc(record.get('EstimateTotal'))}</code></td></tr></table>")
    return "".join(out)


if __name__ == "__main__":
    create_app().run(port=5051, debug=True)
