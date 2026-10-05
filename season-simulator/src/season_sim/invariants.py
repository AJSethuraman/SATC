"""The invariants, each carrying the rule it checks and where that rule is written.

A checker reads ONLY what was recorded through the front doors -- the snapshot
the daily read pass took. The simulator's own ledger is used for one thing:
naming which fake client a hit is about.

Every check returns `(hits, examined)`. `examined` is the denominator (S2,
`docs/SOFTWARE-TENETS.md:72`): a check that looked at nothing did not pass.

KINDS, so nothing is called a failure that is not one:
  failure            the code breaks a rule written in this repository
  cross_store        the two applications disagree where the firm recorded that
                     they must agree (D3, LOG.md:847), usually because a door is
                     missing
  known              already recorded as a known gap; reproduced, not new
  recorded_deferral  the firm deferred the missing piece on purpose (D8)
Observations -- things with no recorded rule -- are NOT here. They live in
`observations.py` and are never called failures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from satc.actions.propose import sort_key as REAL_SORT_KEY   # captured before any mutation

_URG = {"overdue": 0, "urgent": 1, "soon": 2, "routine": 3}


@dataclass
class Hit:
    sim_client: str
    output: str
    expected: str
    subject: str = ""
    call: dict = field(default_factory=dict)


@dataclass
class Invariant:
    code: str
    name: str
    kind: str
    sources: tuple[str, ...]
    rule: str
    fn: Callable
    note: str = ""
    audit_only: bool = False     # filled by the clock-leak audit, never by the daily pass


REGISTRY: dict[str, Invariant] = {}


def invariant(code, name, kind, sources, rule, note="", *, audit_only=False):
    def wrap(fn):
        REGISTRY[code] = Invariant(code, name, kind, tuple(sources), rule, fn, note,
                                   audit_only)
        return fn
    return wrap


def _default(fn, name: str):
    """A threshold read off the real function's own signature, so a changed
    default changes the check with it (and never shows up as a defect)."""
    import inspect
    return inspect.signature(fn).parameters[name].default


class Ctx:
    """What a checker may use besides the snapshot: names, and the season."""

    def __init__(self, firm=None, *, tax_year: int = 2026, billing_door: str = "satc"):
        self.firm = firm
        self.prev_day = ""          # the previous day that was read; door events are new since then
        self.tax_year = tax_year
        self.billing_door = billing_door
        self._by_satc = firm.by_satc() if firm else {}
        self._by_ref = firm.by_ref() if firm else {}
        self._by_job = firm.by_job() if firm else {}

    def refresh(self):
        if self.firm:
            self._by_satc = self.firm.by_satc()
            self._by_ref = self.firm.by_ref()
            self._by_job = self.firm.by_job()

    def sim_for_client(self, cid: str) -> str:
        tr = self._by_satc.get(cid)
        return tr.sim.sim_id if tr else cid

    def sim_for_ref(self, ref: str) -> str:
        tr = self._by_ref.get(ref)
        return tr.sim.sim_id if tr else ref

    def sim_for_job(self, job_id: str) -> str:
        tr = self._by_job.get(job_id)
        return tr.sim.sim_id if tr else job_id

    def ref_to_client(self) -> dict[str, str]:
        """TY-current refs -> satc client id, from the simulator's mapping."""
        out = {}
        for tr in (self.firm.t.values() if self.firm else ()):
            if tr.satc_client and tr.engaged_on:
                out[tr.sim.ref] = tr.satc_client
        return out

    def client_to_ref(self) -> dict[str, str]:
        return {v: k for k, v in self.ref_to_client().items()}


RT = {"1040": "individual_1040", "1065": "partnership_1065", "1120S": "s_corp_1120s",
      "1120": "c_corp_1120"}


def _filing_duty(snap, cid: str):
    """The return duty Today materialised for this client, for the working year."""
    for o in snap.obligations:
        if o.client_id == cid and o.kind == "file" and str(o.period_key) == str(snap.tax_year) \
                and o.form in RT:
            return o
    return None


def _cd_state(snap, ref: str) -> dict:
    events = set(snap.cd_events.get(ref) or [])
    return {"extended": "extension" in events, "disengaged": "disengagement" in events,
            "closed": bool(snap.cd_closed.get(ref)), "delivered": "delivery" in events}


def _q(action) -> str:
    return f"[{action.urgency}] {action.title} -- {action.why}"


# ============================================================================
# A. Calendar
# ============================================================================

@invariant("A1", "due dates land on business days, never early", "failure",
           ["docs/DESIGN-PRINCIPLES.md:49",
            "satc_system/tests/test_obligations_calendar.py:138",
            "satc_system/tests/test_obligations_calendar.py:147"],
           "A computed due date is a business day and never earlier than the statutory date.")
def a1(snap, ctx):
    import deadlines
    from satc.obligations.calendar import is_business_day
    hits, n = [], 0
    for o in snap.obligations:
        n += 1
        if not is_business_day(o.due) or o.due < o.statutory_due:
            hits.append(Hit(ctx.sim_for_client(o.client_id),
                            f"satc duty {o.obligation_key}: statutory {o.statutory_due}, due {o.due}",
                            "due is a business day on or after the statutory date", o.obligation_key))
    for ref, rec in snap.cd_records.items():
        rt = deadlines.return_type_for(rec)
        ty = rec.get("TaxYear")
        if not rt or not deadlines.plausible_year(ty, snap.day):
            continue
        for ext in (False, True):
            n += 1
            got = deadlines.filing_date(rt, int(ty), extended=ext)
            month = deadlines._DUE_MONTH[rt] + (deadlines._EXTENSION_MONTHS if ext else 0)
            statutory = date(int(ty) + 1, month, 15)
            if deadlines.is_closed(got) or got < statutory:
                hits.append(Hit(ctx.sim_for_ref(ref),
                                f"deadlines.filing_date({rt!r}, {ty}, extended={ext}) = {got}",
                                f"a business day on or after {statutory}", ref))
    return hits, n


@invariant("A2", "the two deadline engines agree", "failure",
           ["satc_system/configs/obligations/federal.yaml:61",
            "satc_system/configs/obligations/federal.yaml:74",
            "client-documents/deadlines.py:29-41",
            "docs/SOFTWARE-TENETS.md:150"],
           "For the same return and year, satc_system's duty and client-documents' "
           "filing_date give the same original and extended due dates (both cite "
           "IRC 6072 and 7503; S6: two lists that must agree).")
def a2(snap, ctx):
    import deadlines
    hits, n = [], 0
    for ref, cid in ctx.ref_to_client().items():
        rec = snap.cd_records.get(ref)
        duty = _filing_duty(snap, cid)
        if rec is None or duty is None or str(rec.get("TaxYear")) != str(duty.period_key):
            continue
        rt = deadlines.return_type_for(rec)
        if not rt:
            continue
        n += 1
        ty = int(rec["TaxYear"])
        cd_orig = deadlines.filing_date(rt, ty)
        cd_ext = deadlines.filing_date(rt, ty, extended=True)
        if cd_orig != duty.due or (duty.extended_due and cd_ext != duty.extended_due):
            hits.append(Hit(ctx.sim_for_ref(ref),
                            f"client-documents {rt} {ty}: {cd_orig} / extended {cd_ext}; "
                            f"satc {duty.obligation_key}: {duty.due} / extended {duty.extended_due}",
                            "identical original and extended dates", ref,
                            {"door": "function", "target": "deadlines.filing_date vs "
                             "satc.obligations.profile.materialise"}))
    return hits, n


@invariant("A3", "the materials deadline on the letters is the computed one", "failure",
           ["client-documents/settings.py:83-127", "client-documents/deadlines.py:154"],
           "The MaterialsDeadline a letter prints equals deadlines.materials_deadline "
           "for its return type and season.")
def a3(snap, ctx):
    import deadlines
    import settings
    hits, n = [], 0
    kinds = {"individual": "individual_1040", "partnership": "partnership_1065",
             "s_corp": "s_corp_1120s", "c_corp": "c_corp_1120"}
    for kind, rt in kinds.items():
        n += 1
        try:
            said = settings.firm_fields(str(ctx.tax_year), kind)["MaterialsDeadline"]
        except (KeyError, ValueError) as exc:
            hits.append(Hit("-", f"settings.firm_fields({ctx.tax_year}, {kind}) refused: {exc}",
                            "a date", kind))
            continue
        want = deadlines.materials_deadline(rt, ctx.tax_year)
        if said != f"{want:%B} {want.day}, {want.year}":
            hits.append(Hit("-", f"{kind}: letter says {said}", f"{want}", kind))
    return hits, n


# ============================================================================
# B. Today (satc_system)
# ============================================================================

@invariant("B1", "one row per thing, one chase per client-year", "failure",
           ["docs/DESIGN-PRINCIPLES.md:235-243", "satc_system/src/satc/actions/__init__.py:124-127",
            "satc_system/tests/test_actions.py:99"],
           "No duplicate action_id, and at most one of chase-documents / 8879-signature "
           "per client-year.")
def b1(snap, ctx):
    hits = []
    seen: dict[str, int] = {}
    chase: dict[str, list] = {}
    for a in snap.queue:
        seen[a.action_id] = seen.get(a.action_id, 0) + 1
        if a.kind in ("chase_documents", "signature_outstanding"):
            chase.setdefault(a.client_id, []).append(a.kind)
    for aid, k in seen.items():
        if k > 1:
            hits.append(Hit(ctx.sim_for_client(aid.split("/")[1] if "/" in aid else aid),
                            f"action_id {aid} appears {k} times", "once", aid))
    for cid, kinds in chase.items():
        if len(kinds) > 1:
            hits.append(Hit(ctx.sim_for_client(cid), f"chase rows: {kinds}", "at most one", cid))
    return hits, len(snap.queue)


@invariant("B2", "every row carries its evidence", "failure",
           ["docs/DESIGN-PRINCIPLES.md:243", "satc_system/tests/test_actions.py:241"],
           "Every Today row has a non-empty `why`.")
def b2(snap, ctx):
    hits = [Hit(ctx.sim_for_client(a.client_id), f"{a.action_id}: why={a.why!r}",
                "a non-empty why", a.action_id) for a in snap.queue if not a.why.strip()]
    return hits, len(snap.queue)


@invariant("B3", "Today is in rule order, and the screen shows the engine's order", "failure",
           ["satc_system/src/satc/actions/propose.py:810", "docs/SOFTWARE-TENETS.md:103",
            "satc_system/src/satc/app/templates/today.html:67"],
           "Rows are sorted by propose.sort_key (urgency, due, client, kind), and the "
           "/today page lists the same action ids in the same order as the queue the "
           "route built.")
def b3(snap, ctx):
    hits = []
    keys = [REAL_SORT_KEY(a) for a in snap.queue]
    for i in range(1, len(keys)):
        if keys[i] < keys[i - 1]:
            a, b = snap.queue[i - 1], snap.queue[i]
            hits.append(Hit(ctx.sim_for_client(b.client_id),
                            f"{b.action_id} {keys[i]} listed after {a.action_id} {keys[i - 1]}",
                            "sorted by sort_key", b.action_id,
                            {"door": "http", "target": "GET /today (the queue the route rendered)"}))
            break
    engine = [a.action_id for a in snap.queue]
    if snap.screen_ids != engine:
        first = next((i for i, (x, y) in enumerate(zip(snap.screen_ids, engine)) if x != y),
                     min(len(snap.screen_ids), len(engine)))
        hits.append(Hit("-", f"GET /today lists {len(snap.screen_ids)} ids; engine "
                             f"{len(engine)}; first difference at position {first}: "
                             f"screen={snap.screen_ids[first:first + 1]} "
                             f"engine={engine[first:first + 1]}",
                        "the same ids in the same order", "/today",
                        {"door": "http", "target": "GET /today"}))
    return hits, len(snap.queue)


@invariant("B4", "the same day gives the same queue", "failure",
           ["docs/DESIGN-PRINCIPLES.md:130-137", "satc_system/tests/test_actions.py:199"],
           "Asking /today twice on the same day gives an identical id list.")
def b4(snap, ctx):
    ids = [a.action_id for a in snap.queue]
    if ids != snap.queue_again:
        return [Hit("-", f"{len(set(ids) ^ set(snap.queue_again))} ids differ between two "
                         f"GET /today on one day", "identical", "build_queue",
                    {"door": "http", "target": "GET /today, twice"})], len(ids)
    return [], len(ids)


@invariant("B5", "reads write nothing", "failure",
           ["docs/DESIGN-PRINCIPLES.md:148-149", "satc_system/tests/test_actions.py:251"],
           "The daily read pass (every screen, every engine) leaves both SQLite files "
           "and the engagements tree byte-identical.")
def b5(snap, ctx):
    if snap.hash_before != snap.hash_after:
        where = [re.sub(r".*[\\/](satc_data|engagements)", r"<\1>", f)
                 for f in snap.changed_files[:4]]
        return [Hit("-", f"{len(snap.changed_files)} file(s) changed during reads: {where}",
                    "no change", "read pass")], 1
    return [], 1


@invariant("B6", "every client waiting on paper gets chased", "failure",
           ["satc_system/src/satc/actions/propose.py:150-177",
            "canon/corpus/the-firms-own-words.md:849"],
           "A client with an open working-year request whose oldest ask is at least "
           "chase_outstanding's own stale_after_days (3) old has a chase-documents or "
           "8879 row. (Firm priority N3: chase documents, not just signatures.)")
def b6(snap, ctx):
    from satc.actions.propose import chase_outstanding
    stale = _default(chase_outstanding, "stale_after_days")
    hits, n = [], 0
    rows = {(a.client_id, a.kind) for a in snap.queue}
    by: dict[str, list] = {}
    for r in snap.requested:
        if r.is_open and r.tax_year == snap.tax_year:
            by.setdefault(r.client_id, []).append(r)
    for cid, items in sorted(by.items()):
        dated = [r.requested_at for r in items if r.requested_at]
        if dated and (snap.day - min(dated)).days < stale:
            continue
        n += 1
        if (cid, "chase_documents") not in rows and (cid, "signature_outstanding") not in rows:
            hits.append(Hit(ctx.sim_for_client(cid),
                            f"{len(items)} open request(s), oldest {min(dated) if dated else 'undated'}; "
                            f"no chase row", "a chase_documents or signature_outstanding row", cid))
    return hits, n


# The one threshold with no parameter to read: `urgency="urgent" if (waiting or
# 0) >= 14` is a literal at propose.py:176. It is transcribed, and the
# transcription is checked by mutation (that literal changed to 21 turned B7 red).
CHASE_URGENT_AFTER_DAYS = 14


def _expected_urgency(a, snap) -> str | None:
    from satc.actions.propose import _urgency_from_days, deadline_pressure
    if a.kind == "chase_documents":
        items = [r for r in snap.requested if r.client_id == a.client_id and r.is_open
                 and r.tax_year == snap.tax_year and r.requested_at]
        if not items:
            return None
        waited = (snap.day - min(r.requested_at for r in items)).days
        return "urgent" if waited >= CHASE_URGENT_AFTER_DAYS else "soon"
    if a.kind == "deadline_approaching" and a.due:
        days = (a.due - snap.day).days
        soon = _default(deadline_pressure, "soon_days")
        urgent = _default(_urgency_from_days, "urgent")
        return ("overdue" if days < 0 else "urgent" if days <= urgent else "soon"
                if days <= soon else "routine")
    return None


@invariant("B7", "urgency follows the rule as written", "failure",
           ["satc_system/src/satc/actions/propose.py:111-120",
            "satc_system/src/satc/actions/propose.py:176",
            "satc_system/src/satc/actions/propose.py:229-251"],
           "Chase rows are urgent at 14+ days of waiting, soon before; deadline rows are "
           "overdue / urgent (<= _urgency_from_days' own urgent, 7) / soon (<= "
           "deadline_pressure's own soon_days, 30) from the row's own due date.")
def b7(snap, ctx):
    hits, n = [], 0
    for a in snap.queue:
        want = _expected_urgency(a, snap)
        if want is None:
            continue
        n += 1
        if a.urgency != want:
            hits.append(Hit(ctx.sim_for_client(a.client_id), _q(a), f"urgency {want}", a.action_id))
    return hits, n


@invariant("B8", "a deadline row is dated at the operative deadline", "failure",
           ["satc_system/src/satc/obligations/due_dates.py:109-110",
            "docs/DESIGN-PRINCIPLES.md:64-74"],
           "'The operative deadline -- extended when an extension is on file.' A client "
           "whose return is extended, filed, or whose engagement has ended must not be "
           "told the original due date has passed (principle 5: a confident wrong "
           "answer). The facts are on file in client-documents; satc_system has no door "
           "to receive them (H14).",
           note="expected to fail (H1): build_queue has no input for filed, extended or "
                "disengaged")
def b8(snap, ctx):
    hits, n = [], 0
    to_ref = ctx.client_to_ref()
    for a in snap.queue:
        if a.kind != "deadline_approaching":
            continue
        ref = to_ref.get(a.client_id)
        if not ref:
            continue
        st = _cd_state(snap, ref)
        n += 1
        if a.urgency == "overdue" and (st["extended"] or st["closed"] or st["disengaged"]):
            why = ("closed out as filed" if st["closed"] else
                   "disengaged" if st["disengaged"] else "extended")
            hits.append(Hit(ctx.sim_for_client(a.client_id), _q(a),
                            f"no 'overdue' against the original date: client-documents "
                            f"records {ref} as {why}", a.action_id,
                            {"door": "http", "target": "GET /today"}))
    return hits, n


@invariant("B9", "a row built on an assumption says so", "failure",
           ["satc_system/src/satc/actions/propose.py:241", "docs/DESIGN-PRINCIPLES.md:27-40"],
           "A deadline row whose duty rests on an assumed fact carries the "
           "'unconfirmed assumption' wording.")
def b9(snap, ctx):
    hits, n = [], 0
    duties = {o.obligation_key: o for o in snap.obligations}
    for a in snap.queue:
        if a.kind != "deadline_approaching" or not a.evidence:
            continue
        duty = duties.get(a.evidence[0])
        if duty is None:
            continue
        n += 1
        if duty.is_assumed and "unconfirmed assumption" not in a.why:
            hits.append(Hit(ctx.sim_for_client(a.client_id), _q(a),
                            "the assumption stated", a.action_id))
    return hits, n


@invariant("B10", "no row claims what nobody recorded", "failure",
           ["satc_system/tests/test_actions.py:173", "satc_system/tests/test_actions.py:365"],
           "An extension row never says the extension is filed or decided; a money row "
           "never claims the return reached the client.")
def b10(snap, ctx):
    hits, n = [], 0
    for a in snap.queue:
        if a.kind == "extension_candidate":
            n += 1
            if re.search(r"\b(has been|was|is) (filed|extended|decided)\b", a.why + a.title, re.I):
                hits.append(Hit(ctx.sim_for_client(a.client_id), _q(a), "a flag, not a decision",
                                a.action_id))
        if a.kind in ("unbilled_work", "invoice_overdue", "invoice_unissued"):
            n += 1
            if re.search(r"\bwas delivered\b|\bconfirmed delivery\b(?<!not confirmed delivery)",
                         a.why) and "not confirmed delivery" not in a.why:
                hits.append(Hit(ctx.sim_for_client(a.client_id), _q(a),
                                "no delivery claim", a.action_id))
    return hits, n


@invariant("B11", "a client with nothing started for the year is invited", "failure",
           ["satc_system/src/satc/actions/propose.py:44",
            "satc_system/src/satc/app/today_views.py:86", "docs/SOFTWARE-TENETS.md:706"],
           "interview_invite means 'a client with no engagement for the year'. A client "
           "with no job, no request and no document for the working year gets one. "
           "(S31: a claim and its behaviour are two things.)",
           note="expected to fail (H8): /today passes every job in ANY year as engaged. "
                "It depends on the whole practice (the working year moves only once some "
                "client has a 2026 request), so its repro replays every client")
def b11(snap, ctx):
    hits, n = [], 0
    invited = {a.client_id for a in snap.queue if a.kind == "interview_invite"}
    for cid in snap.clients:
        has_job = any(j.client_id == cid and j.tax_year == snap.tax_year for j in snap.jobs)
        has_paper = any(r.client_id == cid and r.tax_year == snap.tax_year
                        for r in list(snap.requested) + list(snap.received))
        if has_job or has_paper:
            continue
        n += 1
        if cid not in invited:
            prior = sorted({j.tax_year for j in snap.jobs if j.client_id == cid})
            hits.append(Hit(ctx.sim_for_client(cid),
                            f"no interview_invite; the client has jobs only for {prior}",
                            f"'Nothing started for {snap.tax_year}'", cid,
                            {"door": "http", "target": "GET /today"}))
    return hits, n


@invariant("B12", "the agent sees what the owner sees", "failure",
           ["satc_system/src/satc/agent/tools.py:103-114", "docs/SOFTWARE-TENETS.md:103"],
           "agent.tools.today passes 'THE SAME ARGUMENTS THE /today SCREEN PASSES', so its "
           "rows match the screen's rows, and its counts by kind -- which cover every row, "
           "not only the first few it lists -- match the screen's.")
def b12(snap, ctx):
    rows = snap.agent.get("actions") or []
    screen = [(a.title, a.urgency) for a in snap.queue][:len(rows)]
    got = [(r.get("what"), r.get("urgency")) for r in rows]
    hits = []
    call = {"door": "function", "target": "satc.agent.tools.today vs GET /today"}
    if got != screen:
        first = next((i for i, (x, y) in enumerate(zip(got, screen)) if x != y), 0)
        hits.append(Hit("-", f"agent row {first}: {got[first:first + 1]}; screen: "
                             f"{screen[first:first + 1]}", "identical rows",
                        "agent.tools.today", call))
    # The agent lists at most a few rows but counts every one: a row only the
    # screen has (at the routine end of the list) shows up here and nowhere else.
    counts: dict[str, int] = {}
    for a in snap.queue:
        counts[a.kind] = counts.get(a.kind, 0) + 1
    theirs = dict(snap.agent.get("counts_by_kind") or {})
    if theirs != counts:
        diff = {k: (theirs.get(k, 0), counts.get(k, 0)) for k in sorted(set(theirs) | set(counts))
                if theirs.get(k, 0) != counts.get(k, 0)}
        hits.append(Hit("-", f"agent counts vs screen counts, by kind: {diff}",
                        "the same count of every kind", "agent.tools.today counts", call))
    return hits, len(rows) + len(counts)


@invariant("B13", "the prior-year question does not ask for a new-client-only document", "failure",
           ["satc_system/configs/workflows/personal_1040_core.yaml:170-176",
            "satc_system/src/satc/actions/propose.py:180-200",
            "satc_system/src/satc/rollover/diff.py:111-138",
            "docs/DESIGN-PRINCIPLES.md:235-243"],
           "The 1040 workflow asks for prior-year returns only when newSatcClient is "
           "'yes'. For a returning client that document is not an omission, so a row "
           "asking where it went is noise the owner learns to scroll past (principle 13).")
def b13(snap, ctx):
    from satc.intake.workflows import load_workflow
    new_only = set()
    for key in ("personal_1040_core",):
        for t in load_workflow(key).tasks:
            cond = getattr(t, "condition", None) or {}
            if isinstance(cond, dict) and cond.get("question_id") == "newSatcClient" \
                    and str(cond.get("equals")) == "yes" and t.doc_type:
                new_only.add(t.doc_type)
    hits, n = [], 0
    for a in snap.queue:
        if a.kind != "prior_year_question":
            continue
        n += 1
        asked = [e for e in a.evidence if e in new_only]
        returning = any(j.client_id == a.client_id and j.tax_year == snap.tax_year
                        and (j.intake_answers or {}).get("newSatcClient") == "no"
                        for j in snap.jobs)
        if asked and returning:
            hits.append(Hit(ctx.sim_for_client(a.client_id), _q(a),
                            f"no question about {asked}: the workflow asks it of new clients only",
                            a.action_id, {"door": "http", "target": "GET /today"}))
    return hits, n


# ============================================================================
# C. Work queue and stage
# ============================================================================

def _board_items(snap):
    b = snap.board
    return list(b.workable), list(b.not_workable)


@invariant("C1", "every job is in exactly one half of the board", "failure",
           ["satc_system/src/satc/app/work_views.py:46-57"],
           "Each job for the working year is workable or not workable, never both, "
           "never neither.")
def c1(snap, ctx):
    work, stuck = _board_items(snap)
    ids = [w.job_id for w in work] + [s.job_id for s in stuck]
    year_jobs = [j for j in snap.jobs if j.tax_year is None or int(j.tax_year) == snap.tax_year]
    hits = []
    for j in year_jobs:
        k = ids.count(j.job_id)
        if k != 1:
            hits.append(Hit(ctx.sim_for_job(j.job_id), f"job {j.job_id} appears {k} times on "
                                                     f"the board", "exactly once", j.job_id))
    return hits, len(year_jobs)


@invariant("C2", "nothing finished is offered as workable", "failure",
           ["satc_system/src/satc/work/stage.py:73-86"],
           "No job at ready_to_deliver, delivered or complete is in the workable half.")
def c2(snap, ctx):
    work, _ = _board_items(snap)
    hits = [Hit(ctx.sim_for_job(w.job_id), f"workable at stage {w.view.stage}",
                "not workable", w.job_id) for w in work
            if w.view.stage in ("ready_to_deliver", "delivered", "complete")]
    return hits, len(work)


@invariant("C3", "delivered and complete need a recorded fact", "failure",
           ["satc_system/src/satc/work/stage.py:17-22", "satc_system/src/satc/work/stage.py:96-119"],
           "A job reads delivered or complete only when a Deliverable or an accepted "
           "Filing is on file.")
def c3(snap, ctx):
    hits, n = [], 0
    for jid, view in snap.page_view.items():
        n += 1
        if view.stage == "delivered" and snap.deliverables.get(jid) is None:
            hits.append(Hit(ctx.sim_for_job(jid), "delivered with no Deliverable", "a record", jid))
        if view.stage == "complete":
            hits.append(Hit(ctx.sim_for_job(jid), "complete, yet no door records a Filing",
                            "an accepted Filing on file", jid))
    return hits, n


@invariant("C4", "a job waiting on a blocking document says so", "failure",
           ["satc_system/src/satc/work/stage.py:126-129", "satc_system/src/satc/work/stage.py:147-153"],
           "With an open blocking request and no recorded delivery, the board shows the "
           "job waiting_on_documents.")
def c4(snap, ctx):
    hits, n = [], 0
    work, stuck = _board_items(snap)
    for item in work + stuck:
        j = item.job
        year = j.tax_year if j.tax_year is not None else snap.tax_year
        blocking = [r for r in snap.requested if r.client_id == j.client_id and r.is_open
                    and r.tax_year == year and r.blocks_prep]
        if not blocking:
            continue
        n += 1
        if item.view.stage != "waiting_on_documents":
            hits.append(Hit(ctx.sim_for_job(j.job_id),
                            f"stage {item.view.stage} with {len(blocking)} blocking request(s) open "
                            f"({blocking[0].doc_type})", "waiting_on_documents", j.job_id))
    return hits, n


@invariant("C5", "the board and the job page agree on a job's stage", "failure",
           ["docs/SOFTWARE-TENETS.md:103", "satc_system/src/satc/work/queue.py:559",
            "satc_system/src/satc/app/work_views.py:280"],
           "S3: two halves of one tool make the same call. The board passes no "
           "delivery (queue.py:559); the job page does (work_views.py:280).",
           note="expected to fail once a delivery is recorded")
def c5(snap, ctx):
    hits, n = [], 0
    work, stuck = _board_items(snap)
    for item in work + stuck:
        page = snap.page_view.get(item.job_id)
        if page is None:
            continue
        n += 1
        shown = snap.page_stage.get(item.job_id, page.stage.replace("_", " "))
        if page.stage != item.view.stage or shown != page.stage.replace("_", " "):
            hits.append(Hit(ctx.sim_for_job(item.job_id),
                            f"GET /work lists it as {item.view.stage}; GET /work/{item.job_id} "
                            f"shows '{shown}'", "one stage", item.job_id,
                            {"door": "http", "target": f"GET /work/{item.job_id}"}))
    return hits, n


@invariant("C6", "the work order is total and repeatable", "failure",
           ["satc_system/src/satc/work/queue.py:567-570",
            "satc_system/tests/test_work_queue.py:245"],
           "Workable jobs are sorted by score, highest first, ties broken on job_id.")
def c6(snap, ctx):
    work, _ = _board_items(snap)
    keys = [(-w.score, w.job_id) for w in work]
    if keys != sorted(keys):
        return [Hit("-", "workable half out of (score, job_id) order", "sorted", "/work")], len(work)
    screen = [j for j in snap.work_screen_ids if j in {w.job_id for w in work}]
    if screen != [w.job_id for w in work]:
        return [Hit("-", f"GET /work lists workable jobs {screen[:3]}...; board "
                         f"{[w.job_id for w in work][:3]}...", "same order", "/work")], len(work)
    return [], len(work)


@invariant("C7", "a job stronger on every factor ranks higher", "failure",
           ["satc_system/src/satc/work/queue.py:139-152", "satc_system/tests/test_work_queue.py:1-8"],
           "Weights are how hard a factor pulls, never which way: if job A is at least as "
           "strong as job B on every factor and stronger on one, A ranks above B.")
def c7(snap, ctx):
    work, _ = _board_items(snap)
    hits, n = [], 0
    for i, a in enumerate(work):
        for b in work[:i]:                      # b ranks above a
            n += 1
            fa = {f.key: f.score for f in a.factors}
            fb = {f.key: f.score for f in b.factors}
            if all(fa[k] >= fb[k] for k in fa) and any(fa[k] > fb[k] for k in fa):
                hits.append(Hit(ctx.sim_for_job(a.job_id),
                                f"{a.job_id} {fa} ranks below {b.job_id} {fb}",
                                "the dominant job first", a.job_id))
    return hits, n


@invariant("C8", "the deadline factor is known exactly when a duty is on file", "failure",
           ["satc_system/src/satc/work/queue.py:37-41", "satc_system/src/satc/work/queue.py:400-409"],
           "Known iff the job's obligation_key matches a materialised duty; the typed "
           "Job.due_date is never used.")
def c8(snap, ctx):
    work, _ = _board_items(snap)
    keys = {o.obligation_key for o in snap.obligations}
    hits = []
    for w in work:
        f = next(f for f in w.factors if f.key == "deadline")
        on_file = bool((w.job.obligation_key or "").strip() in keys and w.job.obligation_key)
        if f.known != on_file:
            hits.append(Hit(ctx.sim_for_job(w.job_id), f"deadline factor known={f.known}, duty on "
                                                     f"file={on_file}", "equal", w.job_id))
    return hits, len(work)


@invariant("C9", "the work queue ranks against the operative deadline", "failure",
           ["satc_system/src/satc/obligations/due_dates.py:109-110"],
           "Once an extension is on file the deadline factor measures the extended date.",
           note="would fail by construction (no satc door records an extension), but only "
                "on a workable job that is extended. Tax jobs are never workable (no tax "
                "workflow plans an internal task), so C9 has only ever examined onboarding "
                "and rental jobs, none of them extended: it has never been exercised on a "
                "positive case in a season")
def c9(snap, ctx):
    work, _ = _board_items(snap)
    to_ref = ctx.client_to_ref()
    hits, n = [], 0
    for w in work:
        ref = to_ref.get(w.job.client_id)
        if not ref or not w.deadline:
            continue
        n += 1
        if _cd_state(snap, ref)["extended"]:
            f = next(f for f in w.factors if f.key == "deadline")
            hits.append(Hit(ctx.sim_for_job(w.job_id), f"deadline factor: {f.detail}",
                            f"measured from the extended date ({ref} is extended in "
                            f"client-documents)", w.job_id))
    return hits, n


# ============================================================================
# D. Chase lists
# ============================================================================

@invariant("D1", "the documents sweep adds up to the register", "failure",
           ["satc_system/src/satc/intake/chasing.py:113-127",
            "satc_system/src/satc/intake/chasing.py:195-196", "docs/SOFTWARE-TENETS.md:72"],
           "rows + opened_today == open requests, and requests == register rows.")
def d1(snap, ctx):
    sw = snap.sweep
    open_n = sum(1 for r in snap.requested if r.is_open)
    hits = []
    if len(sw.rows) + sw.opened_today != open_n or sw.requests != len(snap.requested):
        hits.append(Hit("-", f"rows {len(sw.rows)} + opened_today {sw.opened_today}; open "
                             f"{open_n}; requests {sw.requests} vs register {len(snap.requested)}",
                        "the sweep adds up", "chasing.waiting"))
    return hits, len(snap.requested)


@invariant("D2", "the sweep is longest-wait first and holds back today's asks", "failure",
           ["satc_system/src/satc/intake/chasing.py:191-199",
            "satc_system/src/satc/intake/chasing.py:202-210"],
           "Undated rows first, then longest wait; nothing asked today is listed.")
def d2(snap, ctx):
    rows = snap.sweep.rows
    hits = []
    waits = [r.waiting_days(snap.day) for r in rows]
    keys = [(w is not None, -(w or 0)) for w in waits]
    if keys != sorted(keys):
        hits.append(Hit("-", f"order {waits[:8]}", "undated, then longest wait", "chasing.waiting"))
    for r, w in zip(rows, waits):
        if w == 0:
            hits.append(Hit(ctx.sim_for_client(r.client_id), f"{r.doc_type} asked today listed",
                            "held back", r.request_id))
    return hits, len(rows)


@invariant("D3", "the signature list holds everyone with a signature out", "failure",
           ["client-documents/signing.py:612-647"],
           "signing.waiting lists every engagement whose standing().missing is "
           "non-empty, overdue first then longest wait.")
def d3(snap, ctx):
    listed = [w.ref for w in snap.cd_waiting]
    want = sorted(ref for ref, st in snap.cd_standing.items() if st.missing)
    hits = []
    for ref in want:
        if ref not in listed:
            hits.append(Hit(ctx.sim_for_ref(ref), f"{ref} missing {len(snap.cd_standing[ref].missing)} "
                                                  f"signature(s), not on signing.waiting",
                            "listed", ref, {"door": "function", "target": "signing.waiting"}))
    keys = [(not w.overdue, -(w.waiting_days(snap.day) or -1)) for w in snap.cd_waiting]
    if keys != sorted(keys):
        hits.append(Hit("-", "signing.waiting out of order", "overdue first, longest wait",
                        "signing.waiting"))
    return hits, len(want)


@invariant("D4", "an ended engagement is not chased for signatures", "failure",
           ["docs/DESIGN-PRINCIPLES.md:235-243", "client-documents/signing.py:612-647"],
           "Principle 13: a queue that becomes noise is worse than no queue. An "
           "engagement that is disengaged or closed out has nothing left to sign for.",
           note="H5. The rule is INFERRED from principle 13; no recorded rule says the "
                "signature list must drop ended engagements (signing.waiting has no such "
                "filter), so whether it should is the firm's call")
def d4(snap, ctx):
    hits, n = [], 0
    for w in snap.cd_waiting:
        st = _cd_state(snap, w.ref)
        n += 1
        if st["disengaged"] or st["closed"]:
            hits.append(Hit(ctx.sim_for_ref(w.ref),
                            f"signing.waiting lists {w.ref} ({'disengaged' if st['disengaged'] else 'closed out'}) "
                            f"missing {[f'{m.document}/{m.field}' for m in w.missing]}",
                            "not listed", w.ref, {"door": "function", "target": "signing.waiting"}))
    return hits, n


# ============================================================================
# E. Season board (client-documents)
# ============================================================================

@invariant("E1", "every engagement is on the board or named unplaced", "failure",
           ["client-documents/deadlines.py:414-422"],
           "Nothing read from the store silently disappears from the season board.")
def e1(snap, ctx):
    due, unplaced = snap.cd_board
    placed = {d.ref for d in due}
    hits = [Hit(ctx.sim_for_ref(ref), f"{ref} neither placed nor unplaced", "one of the two", ref)
            for ref in snap.cd_records if ref not in placed and ref not in unplaced]
    return hits, len(snap.cd_records)


@invariant("E2", "the board is soonest first", "failure",
           ["client-documents/deadlines.py:472"],
           "Sorted by (when, ref, kind).")
def e2(snap, ctx):
    due, _ = snap.cd_board
    keys = [(d.when, d.ref, d.kind) for d in due]
    if keys != sorted(keys):
        return [Hit("-", f"first rows {keys[:2]}", "sorted", "deadlines.board")], len(due)
    return [], len(due)


@invariant("E3", "nothing is placed without a readable form and year", "failure",
           ["client-documents/deadlines.py:399-405"],
           "A placed row has a return type and a plausible tax year.")
def e3(snap, ctx):
    import deadlines
    due, _ = snap.cd_board
    hits = []
    for d in due:
        rec = snap.cd_records.get(d.ref, {})
        if not deadlines.return_type_for(rec) or not deadlines.plausible_year(rec.get("TaxYear"),
                                                                              snap.day):
            hits.append(Hit(ctx.sim_for_ref(d.ref), f"placed {d.what} {d.when}", "unplaced", d.ref))
    return hits, len(due)


@invariant("E4", "`cli season --today` prints the board it computes", "failure",
           ["client-documents/cli.py:2094-2097", "docs/SOFTWARE-TENETS.md:103"],
           "The command's denominator line and row count equal deadlines.board(today=D).")
def e4(snap, ctx):
    due, unplaced = snap.cd_board
    out = snap.cd_season_out
    hits = []
    m = re.search(r"^(\d+) engagement\(s\) read, (\d{4}-\d\d-\d\d)", out, re.M)
    rows = len(re.findall(r"^\S{0,2}\s+\d{4}-\d\d-\d\d\s", out, re.M))
    if not m or int(m.group(1)) != len(snap.cd_refs) or m.group(2) != snap.day.isoformat():
        hits.append(Hit("-", f"season header {m.group(0) if m else out[:60]!r}",
                        f"{len(snap.cd_refs)} engagement(s) read, {snap.day}", "cli season",
                        {"door": "cli", "target": "cli.main(['season', '--today', ...])"}))
    if rows != len(due):
        hits.append(Hit("-", f"cli season printed {rows} dated rows; deadlines.board(today="
                             f"{snap.day}) returns {len(due)} (unplaced {len(unplaced)})",
                        "the same rows", "cli season",
                        {"door": "cli", "target": "cli.main(['season', '--today', ...])"}))
    return hits, 1


@invariant("E5", "an amended return is not placed at the original return's dates", "failure",
           ["client-documents/deadlines.py:348-356", "docs/DESIGN-PRINCIPLES.md:64-74"],
           "An amended return is a refund claim with its own clock (IRC 6511(a), "
           "deadlines.py). Placing it at the original return's filing dates, already "
           "past, is principle 5: a confident wrong answer.",
           note="H6; plausible rather than certain")
def e5(snap, ctx):
    due, _ = snap.cd_board
    hits, n = [], 0
    for d in due:
        rec = snap.cd_records.get(d.ref, {})
        basis = str(rec.get("_return_basis") or rec.get("ReturnBasis") or "")
        interview_amended = "amended" in basis.lower() or "amend" in str(rec.get("PeriodLabel", "")).lower()
        if not interview_amended:
            import json
            from pathlib import Path
            p = Path(ctx.firm.cd.store) / d.ref / "interview.json" if ctx.firm else None
            try:
                interview_amended = bool(p and json.loads(p.read_text("utf-8")).get(
                    "return_basis") == "amended")
            except (OSError, ValueError):
                interview_amended = False
        if not interview_amended:
            continue
        n += 1
        if d.overdue:
            hits.append(Hit(ctx.sim_for_ref(d.ref),
                            f"{d.ref}: {d.what} {d.when} OVERDUE ({d.days} days)",
                            "no original-return deadline on an amended return", d.ref,
                            {"door": "cli", "target": "cli.main(['season', ...])"}))
    return hits, n


@invariant("E6", "an ended engagement is not shown as due", "failure",
           ["docs/DESIGN-PRINCIPLES.md:64-74", "docs/DESIGN-PRINCIPLES.md:235-243",
            "client-documents/deadlines.py:414"],
           "A disengaged or closed-out engagement has nothing due; showing it OVERDUE on "
           "the season board is a confident wrong answer and noise (principles 5, 13).",
           note="H4. The rule is INFERRED from principles 5 and 13; no recorded rule says "
                "the season board must drop ended engagements (deadlines.board has no such "
                "filter), so whether it should is the firm's call")
def e6(snap, ctx):
    due, _ = snap.cd_board
    hits, n = [], 0
    for d in due:
        st = _cd_state(snap, d.ref)
        if not (st["disengaged"] or st["closed"]):
            continue
        n += 1
        if d.overdue:
            hits.append(Hit(ctx.sim_for_ref(d.ref),
                            f"{d.ref}: {d.what} {d.when} OVERDUE "
                            f"({'disengaged' if st['disengaged'] else 'closed out'})",
                            "off the board", d.ref,
                            {"door": "cli", "target": "cli.main(['season', ...])"}))
    return hits, n


@invariant("E7", "an extended engagement is shown at its extended date", "known",
           ["client-documents/deadlines.py:197-202",
            "canon/corpus/decisions-in-their-words.md:123-125"],
           "board() emits materials and filing milestones only, never extended; the firm "
           "chose 'Date only for now'. Reproduced, not new.")
def e7(snap, ctx):
    due, _ = snap.cd_board
    hits, n = [], 0
    for d in due:
        st = _cd_state(snap, d.ref)
        if not st["extended"] or st["closed"] or st["disengaged"]:
            continue
        n += 1
        if d.overdue:
            hits.append(Hit(ctx.sim_for_ref(d.ref), f"{d.ref}: {d.what} {d.when} OVERDUE (extended)",
                            "the extended date", d.ref))
    return hits, n


# ============================================================================
# F. Gates and stages (client-documents)
# ============================================================================

@invariant("F1", "the transmit gate blocks on every missing promise", "failure",
           ["client-documents/signing.py:486-570",
            "satc-handoff/04-TEMPLATES/SATC Tax Return Delivery Letter.html:91",
            "satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:95"],
           "'We cannot transmit anything until the signed authorization is back' and 'We "
           "will not e-file a return before the invoice for it is settled': may_file "
           "lists a blocker whenever the 8879 or letter signature is missing or a raised "
           "invoice is unsettled.")
def f1(snap, ctx):
    import signing
    hits, n = [], 0
    auth = signing._authorization_names()
    for ref, gate in snap.cd_may_file.items():
        st = snap.cd_standing.get(ref)
        if st is None:
            continue
        n += 1
        must = [m for m in st.missing if m.document in auth or m.document in signing.GATES_THE_WORK]
        unsettled = [b for b in snap.cd_invoices.get(ref, []) if not b.get("SettledOn")]
        if (must or unsettled) and gate.clear:
            hits.append(Hit(ctx.sim_for_ref(ref), f"may_file clear with {len(must)} signature(s) "
                                                  f"and {len(unsettled)} unsettled bill(s)",
                            "blocked", ref))
    return hits, n


@invariant("F2", "the stages bar never runs ahead of itself", "failure",
           ["client-documents/stages.py:29-34", "client-documents/stages.py:108-119"],
           "paid implies billed.")
def f2(snap, ctx):
    hits = []
    for ref, steps in snap.cd_stages.items():
        by = {s.key: s.reached for s in steps}
        if by.get("paid") and not by.get("billed"):
            hits.append(Hit(ctx.sim_for_ref(ref), "paid without billed", "billed first", ref))
    return hits, len(snap.cd_stages)


@invariant("F3", "the close-out control examines every engagement", "failure",
           ["client-documents/closeout.py:278-305"],
           "closeout.sweep reviews as many engagements as carry interview.json.")
def f3(snap, ctx):
    want = len(snap.cd_interviews)
    if snap.cd_sweep_count != want:
        return [Hit("-", f"sweep reviewed {snap.cd_sweep_count}; {want} have interview.json",
                    "equal", "closeout.sweep")], want
    return [], want


# ============================================================================
# G. Across the two stores
# ============================================================================

@invariant("G1", "each ref names exactly one satc engagement", "cross_store",
           ["LOG.md:847", "satc_system/src/satc/persistence/store.py:701-721",
            "satc_system/tests/test_the_join_has_a_writer.py"],
           "D3: 'client-documents owns the engagement; satc_system holds the return.' Each "
           "engaged ref has one satc Engagement carrying it, and client_for_ref resolves "
           "to the paired client.")
def g1(snap, ctx):
    hits, n = [], 0
    for tr in (ctx.firm.t.values() if ctx.firm else ()):
        if not tr.engaged_on or tr.sim.ref not in snap.cd_records:
            continue
        n += 1
        owners = snap.engagement_refs.get(tr.sim.ref, [])
        if owners != [tr.satc_client] or not tr.satc_client:
            why = ("satc_system has no workflow for this return, so there is no job to "
                   "carry the ref" if not tr.sim.satc_workflows else "")
            hits.append(Hit(tr.sim.sim_id, f"{tr.sim.ref}: satc engagements carrying it: "
                                           f"{owners or 'none'} {why}".strip(),
                            f"exactly [{tr.satc_client or 'a satc client'}]", tr.sim.ref,
                            {"door": "function", "target": "SATCStore.client_for_ref"}))
    return hits, n


@invariant("G2", "the price shown through the ref is the estimate", "cross_store",
           ["LOG.md:744", "LOG.md:848", "satc_system/src/satc/billing/engagement_price.py:98-161"],
           "D10: 'Show the engagement price via the ref'; D4: the fee schedule is the "
           "price. price_for_ref(ref).total equals the record's EstimateTotal.")
def g2(snap, ctx):
    from satc.billing.engagement_price import price_for_ref
    hits, n = [], 0
    for ref, cid in ctx.ref_to_client().items():
        rec = snap.cd_records.get(ref)
        if rec is None:
            continue
        n += 1
        got = price_for_ref(ref)
        total = getattr(got, "total", None)
        if total != rec.get("EstimateTotal"):
            hits.append(Hit(ctx.sim_for_ref(ref), f"price_for_ref={total or got.reason!r}",
                            f"{rec.get('EstimateTotal')}", ref))
    return hits, n


@invariant("G4", "the papers-due date matches what the client was told", "cross_store",
           ["LOG.md:847",
            "satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:79",
            "client-documents/registry/firm-settings.yaml:114",
            "satc_system/configs/firm_policy.yaml:34-39"],
           "The letter tells the client 'we need your complete information by "
           "<<MaterialsDeadline>>' (client-documents, set 26 Aug 2026). satc_system's "
           "cutoff drives its extension flag. Where they differ the owner is flagged to "
           "extend a client who is still inside the date they were given. Whether the "
           "cutoff is an engagement term is the firm's call.")
def g4(snap, ctx):
    import settings
    hits, n = [], 0
    kind = {"1040": "individual", "1065": "partnership", "1120S": "s_corp", "1120": "c_corp"}
    to_ref = ctx.client_to_ref()
    for cid, ref in sorted(to_ref.items()):
        duty = _filing_duty(snap, cid)
        tr = ctx._by_ref.get(ref)
        if duty is None or tr is None or str(duty.period_key) != str(ctx.tax_year):
            continue
        n += 1
        told = settings.firm_fields(str(ctx.tax_year), kind[tr.sim.form])["MaterialsDeadline"]
        mine = duty.documents_due
        if mine and f"{mine:%B} {mine.day}, {mine.year}" != told:
            hits.append(Hit(tr.sim.sim_id, f"satc documents_due {mine} (firm_policy cutoff); "
                                           f"client told {told}", "the same date", ref))
    return hits, n


@invariant("G8", "no extension flag while the client is inside the date they were told",
           "cross_store",
           ["LOG.md:847",
            "satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:79",
            "satc_system/src/satc/actions/propose.py:254-280",
            "satc_system/configs/firm_policy.yaml:34-39"],
           "The client was told 'we need your complete information by "
           "<<MaterialsDeadline>>'. Today proposes a likely extension from the day after "
           "satc's own cutoff. Before the told date, that row is about a client who is "
           "not late (H2).")
def g8(snap, ctx):
    import settings
    kind = {"1040": "individual", "1065": "partnership", "1120S": "s_corp", "1120": "c_corp"}
    hits, n = [], 0
    for a in snap.queue:
        if a.kind != "extension_candidate":
            continue
        tr = ctx._by_satc.get(a.client_id)
        if tr is None:
            continue
        n += 1
        told = settings.firm_fields(str(ctx.tax_year), kind[tr.sim.form])["MaterialsDeadline"]
        from datetime import datetime
        told_d = datetime.strptime(told, "%B %d, %Y").date()
        if snap.day <= told_d:
            hits.append(Hit(tr.sim.sim_id, _q(a) + f" (client told {told})",
                            f"no extension flag before {told}", a.action_id,
                            {"door": "http", "target": "GET /today"}))
    return hits, n


@invariant("G5", "what client-documents records, satc_system reflects", "cross_store",
           ["LOG.md:847", "satc_system/src/satc/actions/__init__.py:96-98"],
           "D3 splits the engagement from the return. An extension, disengagement or "
           "close-out recorded in client-documents should stop satc_system asking for "
           "the same client's documents or proposing an extension. There is no door "
           "that carries the fact across (H14).")
def g5(snap, ctx):
    hits, n = [], 0
    to_ref = ctx.client_to_ref()
    for a in snap.queue:
        if a.kind not in ("chase_documents", "extension_candidate", "signature_outstanding",
                          "prior_year_question"):
            continue
        ref = to_ref.get(a.client_id)
        if not ref:
            continue
        st = _cd_state(snap, ref)
        n += 1
        if st["closed"] or st["disengaged"] or (st["extended"] and a.kind == "extension_candidate"):
            why = ("closed out" if st["closed"] else "disengaged" if st["disengaged"]
                   else "already extended")
            hits.append(Hit(ctx.sim_for_client(a.client_id), _q(a),
                            f"no {a.kind} row: {ref} is {why} in client-documents", a.action_id,
                            {"door": "http", "target": "GET /today"}))
    return hits, n


@invariant("G6", "both systems know whether the bill is paid", "cross_store",
           ["LOG.md:847-854",
            "satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:95",
            "client-documents/signing.py:541-572",
            "satc_system/src/satc/app/today_views.py:81-96"],
           "D3 settles invoice numbering in client-documents. 'We will not e-file a "
           "return before the invoice for it is settled' is gated by client-documents "
           "alone; Today's money rows read satc_system's invoices alone. Whichever door "
           "bills, the other system cannot see it.")
def g6(snap, ctx):
    hits, n = [], 0
    for tr in (ctx.firm.t.values() if ctx.firm else ()):
        if not tr.invoice:
            continue
        ref = tr.sim.ref
        n += 1
        if ctx.billing_door == "satc":
            inv = next((i for i in snap.invoices if i.invoice_id == tr.invoice), None)
            from satc.actions.propose import balance_owed
            owed = balance_owed(inv, snap.payments) if inv else 0
            if snap.cd_closed.get(ref) and owed and not snap.cd_invoices.get(ref):
                hits.append(Hit(tr.sim.sim_id, f"{ref} closed out as filed while satc invoice "
                                               f"{tr.invoice} still has {owed} owed; "
                                               f"client-documents' gate saw no invoice",
                                "the filing gate sees the unpaid bill", ref))
        else:
            mine = [i for i in snap.invoices if i.client_id == tr.satc_client
                    and i.tax_year == ctx.tax_year]
            if snap.cd_invoices.get(ref) and not mine and tr.satc_client:
                hits.append(Hit(tr.sim.sim_id, f"{ref} billed as {tr.invoice} in "
                                               f"client-documents; satc_system holds no "
                                               f"invoice for {ctx.tax_year}",
                                "Today's money rows know the bill exists", ref))
    return hits, n


# ============================================================================
# L. What the doors themselves answered
# ============================================================================

def _gate_hits(snap, ctx, prefix: str):
    hits, n = [], 0
    for g in (ctx.firm.gate_refusals if ctx.firm else ()):
        if not (ctx.prev_day < g["day"] <= snap.day.isoformat()):
            continue
        reasons = [ln.strip() for ln in g["output"].splitlines() if ln.strip().startswith(prefix)]
        n += 1
        if reasons:
            hits.append(Hit(g["sim"], f"cli event --kind {g['kind']} on {g['day']}: REFUSED BY THE "
                                      f"PRE-SEND GATE -- " + " || ".join(reasons)[:600],
                            f"the {g['kind']} document passes the gate", g["ref"], g["call"]))
    return hits, n


@invariant("L1", "a document the process calls for can pass its own gate", "failure",
           ["satc-handoff/04-TEMPLATES/FIELDS - Extension Notice.md:54",
            "satc-handoff/04-TEMPLATES/FIELDS - Extension Notice.md:68",
            "satc-handoff/04-TEMPLATES/SATC Extension Notice.html:75-81",
            "client-documents/registry/required.yaml:60-66", "docs/SOFTWARE-TENETS.md:150"],
           "The pre-send gate refuses documents that are wrong. A lifecycle document "
           "built from a valid payload -- here the extension notice, whose template "
           "defines a no-payment branch ('the exact inverse of PaymentEnclosed') -- "
           "passes it. S6: the template's conditions and the gate's floors are two "
           "lists that must agree.")
def l1(snap, ctx):
    return _gate_hits(snap, ctx, "compliance")


@invariant("L3", "an extension notice can restate what the extension changed", "failure",
           ["client-documents/consistency.py:313-345",
            "satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:83",
            "client-documents/registry/lifecycle.yaml"],
           "The package check refuses a first-deliverable target that is a DATE earlier "
           "than the materials deadline (a target written as a phrase is skipped, "
           "consistency.py:328-331). An extension moves the materials deadline past a "
           "dated target promised at the interview, and the extension event carries no "
           "field to restate the target -- so an extension notice for such a client is "
           "refused. The letter commits the firm to filing extensions where needed.",
           note="Every simulated client's target is a date (scenario.yaml owner.interview) "
                "and every extension notice's materials date is the extended date minus "
                "owner.extension_notice.materials_days_before_extended -- both invented")
def l3(snap, ctx):
    return _gate_hits(snap, ctx, "agrees")


@invariant("L2", "following the billing screen's instruction gives the quoted price", "failure",
           ["satc_system/src/satc/billing/invoice.py:217-257", "LOG.md:848"],
           "'One price, and it is the one on the client's estimate' (invoice.py). Each "
           "engagement-priced line refuses and tells the owner to 'put <estimate total> "
           "in as the rate'. Doing what every line says must bill the estimate once, not "
           "once per line. D4: the fee schedule is the price.")
def l2(snap, ctx):
    hits, n = [], 0
    for pr in (ctx.firm.probes if ctx.firm else ()):
        if not (ctx.prev_day < pr["day"] <= snap.day.isoformat()):
            continue
        n += 1
        est = str(pr["estimate"]).replace("$", "").replace(",", "")
        got = str(pr["draft_total"]).replace(",", "")
        if not got or est != got:
            told = [f"{code}: put {rate}" for code, rate, _ in pr["lines"] if rate]
            hits.append(Hit(pr["sim"], f"{pr['ref']} estimate {pr['estimate']}; each refusal said "
                                       f"{told}; the draft built that way totals {pr['draft_total']} "
                                       f"(discarded, never issued)",
                            f"a draft totalling {pr['estimate']}", pr["ref"], pr["call"]))
    return hits, n


# ============================================================================
# M. Money on Today (satc_system)
# ============================================================================

def _ledger_owed(inv, payments):
    """What is still owed and what was overpaid, summed straight off the payment
    records -- not through propose.balance_owed, which is the code under test.
    The fallback to the invoice's own paid flag when no payment names it is
    the rule as written (propose.py:406-426)."""
    from decimal import Decimal
    mine = [p for p in payments if p.invoice_id == inv.invoice_id]
    if not mine:
        return (Decimal("0.00") if inv.is_paid else inv.total), Decimal("0.00")
    paid = sum((p.amount for p in mine), Decimal(0))
    return max(inv.total - paid, Decimal("0.00")), max(paid - inv.total, Decimal("0.00"))


@invariant("M1", "an issued bill past due with money owed is chased, for the balance", "failure",
           ["satc_system/src/satc/actions/propose.py:599-617",
            "satc_system/src/satc/actions/propose.py:406-426"],
           "'Issued, still owed, and past its due date -- one row per invoice.' What is "
           "owed comes from the payment ledger: a settled invoice is not chased, and a "
           "part-paid one is chased for the BALANCE. Urgency: soon, then urgent from "
           "invoice_overdue's own chase_after_days (14) past due, overdue from its "
           "serious_after_days (45).")
def m1(snap, ctx):
    from satc.actions.propose import invoice_overdue
    chase = _default(invoice_overdue, "chase_after_days")
    serious = _default(invoice_overdue, "serious_after_days")
    hits, n = [], 0
    for inv in snap.invoices:
        if not inv.is_issued or inv.due_on is None or inv.due_on >= snap.day:
            continue
        n += 1
        owed, _over = _ledger_owed(inv, snap.payments)
        rows = [a for a in snap.queue if a.kind == "invoice_overdue"
                and str(inv.invoice_id) in a.evidence]
        late = (snap.day - inv.due_on).days
        who = ctx.sim_for_client(inv.client_id)
        call = {"door": "http", "target": "GET /today"}
        if owed > 0 and not rows:
            hits.append(Hit(who, f"invoice {inv.invoice_id} ({inv.total}) due {inv.due_on}, "
                                 f"{owed} still owed on the ledger, {late} days late: no "
                                 f"invoice_overdue row", "an invoice_overdue row", str(inv.invoice_id),
                            call))
        elif owed <= 0 and rows:
            hits.append(Hit(who, _q(rows[0]) + f" (the ledger has invoice {inv.invoice_id} settled)",
                            "no row for a settled invoice", str(inv.invoice_id), call))
        elif rows:
            row = rows[0]
            want = "overdue" if late >= serious else "urgent" if late >= chase else "soon"
            said = f"{owed:,.2f}" in row.title + row.why
            if row.urgency != want or not said:
                hits.append(Hit(who, _q(row) + f" (ledger: {owed} owed, {late} days late)",
                                f"urgency {want}, naming the balance ${owed:,.2f}",
                                str(inv.invoice_id), call))
    return hits, n


@invariant("M2", "money beyond the bill is surfaced", "failure",
           ["satc_system/src/satc/actions/propose.py:661-680"],
           "'More money arrived against an invoice than the invoice asked for' gets a "
           "credit_on_account row naming the excess; an invoice that was not overpaid "
           "gets none.")
def m2(snap, ctx):
    hits, n = [], 0
    for inv in snap.invoices:
        if not any(p.invoice_id == inv.invoice_id for p in snap.payments):
            continue
        n += 1
        _owed, over = _ledger_owed(inv, snap.payments)
        rows = [a for a in snap.queue if a.kind == "credit_on_account"
                and str(inv.invoice_id) in a.evidence]
        who = ctx.sim_for_client(inv.client_id)
        call = {"door": "http", "target": "GET /today"}
        if over > 0 and not (rows and f"{over:,.2f}" in rows[0].title + rows[0].why):
            hits.append(Hit(who, (_q(rows[0]) if rows else "no credit_on_account row")
                            + f" (ledger: {over} paid beyond invoice {inv.invoice_id})",
                            f"a credit_on_account row naming ${over:,.2f}", str(inv.invoice_id),
                            call))
        if over <= 0 and rows:
            hits.append(Hit(who, _q(rows[0]), "no credit row: nothing was overpaid",
                            str(inv.invoice_id), call))
    return hits, n


# ============================================================================
# K. The clock
# ============================================================================

@invariant("K1", "an explicit --today governs the whole read", "failure",
           ["client-documents/cli.py:3082", "client-documents/deadlines.py:414-434",
            "client-documents/deadlines.py:395"],
           "`cli season --today D` answers for D. Run under a wrong machine clock with "
           "an explicit --today, it must print what it prints under the right one.",
           note="checked by the clock-leak audit on sample days (H11), under two wrong "
                "clocks: 2031-06-15, and the day plus one year. The board changes only when "
                "the machine clock is far enough from --today that deadlines.plausible_year "
                "(deadlines.py:395) answers differently; the audit line says which clock did",
           audit_only=True)
def k1(snap, ctx):
    return [], 0      # filled by the audit, which needs a second clock


from season_sim.decisions import DECISION, decision_for  # noqa: E402,F401


def run_all(snap, ctx, *, only: set[str] | None = None) -> dict[str, tuple[list, int]]:
    out = {}
    for code, inv in REGISTRY.items():
        if only and code not in only:
            continue
        if inv.audit_only:
            continue
        try:
            out[code] = inv.fn(snap, ctx)
        except Exception as exc:                       # noqa: BLE001
            out[code] = ([Hit("-", f"CHECKER CRASHED: {type(exc).__name__}: {exc}",
                              "the checker runs", code)], 0)
    return out
