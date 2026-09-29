"""The two actors: the clients (the world) and the owner (the firm's policy).

The world says WHAT HAPPENS -- a W-2 arrives on 9 February, a client never
signs. The owner decides WHAT GETS RECORDED, and records it only through a
front door: a satc_system route, or a client-documents command. Nothing here
writes a store directly.

The owner is deliberately simple and every choice is an assumption labelled in
`scenario.yaml`: record arrivals the same business day, prepare the earliest
statutory deadline first at a fixed capacity, extend a week before the original
date anything not ready, bill when the return goes out, transmit only when
client-documents' `may_file` is clear (`close` does not enforce that; this owner
chooses it). What the owner types into a document -- the interview's
first-deliverable date, an extension notice's materials date, what was filed --
comes from `scenario.yaml` `owner:` too, never from a literal in this file.

The simulator keeps the MAPPING (SIM id -> satc client id, job ids, request
ids, refs). The checkers never read this ledger for facts about the practice --
only to name which fake client a finding is about.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from season_sim import clock
from season_sim.world import SATC_ENTITY, SimClient, World

import re

NA_REASON = "The client ended the engagement; nothing further is being prepared."
PUT_IN = re.compile(r"put \$([\d,]+\.\d\d) in as the rate")


@dataclass
class Tracked:
    sim: SimClient
    satc_client: str = ""
    jobs: dict = field(default_factory=dict)          # workflow_key -> job_id
    requests: dict = field(default_factory=dict)      # request_id -> {doc_type, job, due}
    engaged_on: str = ""
    letter_signed_on: str = ""
    letter_recorded: bool = False
    prep_started: str = ""
    delivered_on: str = ""
    invoice: str = ""
    invoiced_on: str = ""
    paid_on: str = ""
    payment_recorded: str = ""          # "", "yes", "refused", "no-door" or "no-door-sim"
    paid2_on: str = ""                  # a part payer's balance
    payment2_recorded: str = ""
    signed_8879_on: str = ""
    spouse_8879_on: str = ""
    recorded_8879: set = field(default_factory=set)
    extended_on: str = ""
    disengaged_on: str = ""
    filed_on: str = ""
    amended_created: str = ""
    amended_letter_recorded: bool = False
    amended_delivered: str = ""
    amended_signed: str = ""
    amended_filed: str = ""
    requoted_on: str = ""
    refusals: list = field(default_factory=list)      # door calls that did not succeed

    @property
    def main_job(self) -> str:
        wf = [w for w in self.sim.satc_workflows if w not in (
            "personal_rental_schedule_e", "new_client_onboarding")]
        return self.jobs.get(wf[0], "") if wf else ""

    @property
    def open_for_work(self) -> bool:
        return bool(self.engaged_on) and not self.disengaged_on


def _no_by_default(workflow_key: str, yes: set[str]) -> dict:
    from satc.intake.workflows import load_workflow
    wf = load_workflow(workflow_key)
    out = {}
    for q in wf.questions:
        if q.id == "newSatcClient":
            continue                                   # set from `mode` by the route
        out[q.id] = "yes" if q.id in yes else "no"
    return out


def satc_answers(c: SimClient, workflow_key: str, *, tax_year: int) -> dict:
    f = c.features
    if workflow_key == "personal_1040_core":
        yes = {"stateReturnNeeded"}
        brokerage = f.get("brokerage") or (tax_year < 2026 and c.prior_gap)
        if brokerage:
            yes.add("brokerageActivity")
        if f.get("k1"):
            yes.add("expectedK1s")
        if f.get("retirement"):
            yes.add("retirementDistributions")
        if f.get("marketplace"):
            yes.add("marketplaceInsurance")
        return _no_by_default(workflow_key, yes)
    if workflow_key == "business_partnership_tax":
        return _no_by_default(workflow_key, {"capitalActivity", "assetActivity"})
    if workflow_key == "business_scorp_tax":
        return _no_by_default(workflow_key, {"shareholderDistributions", "shareholderPayroll"})
    if workflow_key == "personal_rental_schedule_e":
        return _no_by_default(workflow_key, {"majorImprovements"})
    if workflow_key == "new_client_onboarding":
        return _no_by_default(workflow_key, {"hasPriorYearReturns"})
    return _no_by_default(workflow_key, set())


def first_deliverable_target(owner: dict, form: str) -> str:
    """The date promised at the interview -- scenario.yaml owner.interview, labelled
    there as invented (it used to come silently from exercise.py)."""
    from season_sim import clock
    raw = (owner.get("interview") or {}).get("first_deliverable_target", {}).get(form)
    when = raw if isinstance(raw, date) else date.fromisoformat(str(raw))
    return clock.spoken(when)


def cd_answers(c: SimClient, *, tax_year: int, amended: bool = False, owner: dict) -> dict:
    import exercise
    ident = dict(client_full_name=c.name, client_email=c.email,
                 client_address1=f"{c.idx} Simulation Way", client_city="Testville",
                 first_deliverable_target=first_deliverable_target(owner, c.form))
    if c.form == "1040":
        feats, extra = [], {}
        brokerage = c.features.get("brokerage") or (tax_year < 2026 and c.prior_gap)
        if brokerage:
            feats.append("investments")
            extra["count_brokerages"] = 1
        if c.features.get("k1"):
            feats.append("k1")
            extra["count_k1s"] = 1
        if c.features.get("rental"):
            feats.append("rentals")
            extra["count_rentals"] = 1
        if amended:
            feats, extra = [], {}
            extra.update(return_basis="amended", amendment_reason="new_information")
        if c.joint:
            extra.update(joint_return="yes", spouse_name=c.spouse)
        return exercise.individual(return_features=feats, tax_year=str(tax_year),
                                   taxpayer_name=c.name, **ident, **extra)
    over = dict(signer_name=f"Testsigner {c.idx:03d}", tax_year=str(tax_year), **ident)
    if c.form == "1065":
        return exercise.entity("1065", count_owners=2, owner_returns="yes", **over)
    if c.form == "1120S":
        return exercise.entity("1120S", entity_structure="corporation",
                               signer_title="President", owner_returns="no", **over)
    return exercise.entity("1120", entity_structure="corporation",
                           signer_title="President", owner_returns="no", **over)


RETURN_TYPE = {"1040": "individual_1040", "1065": "partnership_1065",
               "1120S": "s_corp_1120s", "1120": "c_corp_1120"}
SATC_LINES = {"1040": ["return_1040", "return_state"], "1065": ["return_1065"],
              "1120S": ["return_1120s"], "1120": []}


class Firm:
    """The owner, acting one business day at a time."""

    def __init__(self, world: World, scenario: dict, satc, cd, state, calls: list):
        self.world = world
        self.sc = scenario
        self.owner = scenario["owner"]
        self.tax_year = int(scenario["season"]["tax_year"])
        self.satc = satc
        self.cd = cd
        self.STATE = state
        self.calls = calls
        self.t: dict[str, Tracked] = {c.sim_id: Tracked(sim=c) for c in world.clients}
        self.prep_queue: list[tuple[str, str]] = []     # (sim_id, done_on)
        self.facts: list[dict] = []                     # world facts with no door
        self.cd_invoice_seq = 0
        self.probes: list[dict] = []                    # door probes (what-ifs through a door)
        self.gate_refusals: list[dict] = []             # documents the pre-send gate refused
        self.unrecordable_payments: list[dict] = []     # money that arrived with no door to record it

    # -- the mapping, for the checkers to NAME things -----------------------
    def by_ref(self) -> dict[str, Tracked]:
        out = {}
        for tr in self.t.values():
            out[tr.sim.ref] = tr
            if tr.sim.prior_ref:
                out[tr.sim.prior_ref] = tr
            if tr.sim.amended_ref:
                out[tr.sim.amended_ref] = tr
        return out

    def by_satc(self) -> dict[str, Tracked]:
        return {tr.satc_client: tr for tr in self.t.values() if tr.satc_client}

    def by_job(self) -> dict[str, Tracked]:
        out = {}
        for tr in self.t.values():
            for j in tr.jobs.values():
                out[j] = tr
        return out

    def _refused(self, tr: Tracked, call, day: date) -> None:
        tr.refusals.append({"day": day.isoformat(), **call.brief(), "excerpt": call.excerpt})

    def _event(self, tr: Tracked, ref: str, kind: str, payload: dict, d: date) -> None:
        """A lifecycle event. If the pre-send gate refuses the document, the
        refusal is kept as evidence and the owner does what it says: sends
        anyway with --force and a reason (the gate logs the override)."""
        call, out = self.cd.event(ref, kind, payload)
        if call.status == 0:
            return
        self._refused(tr, call, d)
        if "REFUSED BY THE PRE-SEND GATE" in out:
            self.gate_refusals.append({"day": d.isoformat(), "sim": tr.sim.sim_id, "ref": ref,
                                       "kind": kind, "call": call.brief(),
                                       "output": out.strip()[-900:]})
            again, _ = self.cd.event(ref, kind, payload, force_reason=(
                "simulated owner: the gate's rule and this document disagree; "
                "sent as the refusal instructs"))
            if again.status != 0:
                self._refused(tr, again, d)

    # -- 2026: last year's cycle for returning clients ----------------------
    def history(self) -> None:
        """TY2025, through the same doors, with the clock frozen at 2026 dates."""
        ph = {k: date.fromisoformat(str(v)) for k, v in self.owner["prior_history"].items()}
        prior = int(self.sc["season"]["prior_year"])
        returning = [tr for tr in self.t.values() if tr.sim.returning]
        with clock.frozen(ph["engaged"]):
            for tr in returning:
                c = tr.sim
                call, cid = self.satc.quick_add(name=c.name, entity_type=SATC_ENTITY[c.form],
                                                email=c.email)
                tr.satc_client = cid
                call, job = self.satc.new_engagement(
                    client_id=cid, workflow_key="personal_1040_core", tax_year=prior,
                    mode="new", answers=satc_answers(c, "personal_1040_core", tax_year=prior))
                if job:
                    self.satc.set_ref(job, c.prior_ref)
                    tr.jobs["prior"] = job
                call, _ = self.cd.interview(c.prior_ref, cd_answers(c, tax_year=prior,
                                                                    owner=self.owner))
                self.cd.sent(c.prior_ref, ph["engaged"].isoformat())
        with clock.frozen(ph["letter_signed"]):
            for tr in returning:
                for line in self._letter_lines(tr.sim.prior_ref):
                    self.cd.record_signature(tr.sim.prior_ref, line,
                                             ph["letter_signed"].isoformat())
        with clock.frozen(ph["docs_in"]):
            for tr in returning:
                for item in list(self.STATE.requested_items()):
                    if item.client_id == tr.satc_client and item.is_open:
                        self.satc.received(item.request_id)
        with clock.frozen(ph["delivered"]):
            for tr in returning:
                if tr.jobs.get("prior"):
                    self.satc.delivered(tr.jobs["prior"], ph["delivered"].isoformat())
                self._event(tr, tr.sim.prior_ref, "delivery", self._delivery_payload(
                    tr, ph["delivered"], year=prior), ph["delivered"])
        with clock.frozen(ph["signed_8879"]):
            for tr in returning:
                for line in self._auth_lines(tr.sim.prior_ref):
                    self.cd.record_signature(tr.sim.prior_ref, line,
                                             ph["signed_8879"].isoformat())
        with clock.frozen(ph["filed"]):
            for tr in returning:
                self.cd.close(tr.sim.prior_ref, self._filed(tr, extended=False, year=prior))

    # -- reading the client-documents census, the way `sign` prints it ------
    def _lines(self, ref: str):
        import cli
        import engagements
        import packaging
        import signing
        from pathlib import Path
        store = Path(self.cd.store)
        record = engagements.load(ref, store)
        docs = packaging.documents_for(record)
        return signing.standing(ref, record, docs, cli.TEMPLATE_DIR, store=store).expected

    def _auth_names(self) -> frozenset:
        import signing
        return signing._authorization_names()

    def _letter_lines(self, ref: str) -> list[str]:
        import signing
        return [f"{ln.document}/{ln.field}" for ln in self._lines(ref)
                if ln.document in signing.GATES_THE_WORK]

    def _auth_lines(self, ref: str, who: str = "") -> list[str]:
        names = self._auth_names()
        out = [f"{ln.document}/{ln.field}" for ln in self._lines(ref) if ln.document in names]
        if who == "taxpayer":
            out = [x for x in out if not x.endswith("/SpouseName")]
        if who == "spouse":
            out = [x for x in out if x.endswith("/SpouseName")]
        return out

    # -- payloads (shapes from client-documents/tests/test_lifecycle.py) -----
    def _delivery_payload(self, tr: Tracked, d: date, *, year: int) -> dict:
        deadline = d + timedelta(days=int(self.owner["signature_deadline_days"]))
        form = tr.sim.form
        est = str((self.owner.get("delivery_letter") or {})["estimated_payments"])
        return {"answers": {"signature_deadline": clock.spoken(deadline), "filing": "efiled",
                            "estimated_payments": est},
                "rows": {"ReturnsDelivered": [{"Return": f"Federal Form {form}",
                                               "Detail": f"Tax year {year}"}],
                         "ActionList": [{"Action": "Sign the e-file authorization",
                                         "Detail": f"By {clock.spoken(deadline)}"}]}}

    def _extension_payload(self, tr: Tracked) -> dict:
        import deadlines
        rt = RETURN_TYPE[tr.sim.form]
        ext = deadlines.filing_date(rt, self.tax_year, extended=True)
        orig = deadlines.filing_date(rt, self.tax_year)
        notice = self.owner["extension_notice"]
        materials = ext - timedelta(days=int(notice["materials_days_before_extended"]))
        return {"answers": {"extended_deadline": clock.spoken(ext),
                            "payment_deadline": clock.spoken(orig),
                            "materials_deadline": clock.spoken(materials),
                            "payment": str(notice["payment_enclosed"])},
                "rows": {"ExtendedReturns": [{"Return": f"Federal Form {tr.sim.form}",
                                              "Detail": f"Extended to {clock.spoken(ext)}"}],
                         "OutstandingItems": [{"Document": "Outstanding documents",
                                               "Detail": "Still expected"}]}}

    def _disengagement_payload(self, tr: Tracked, d: date) -> dict:
        return {"answers": {"effective_date": clock.spoken(d),
                            "records_available_until": clock.spoken(d + timedelta(
                                days=int(self.owner["disengagement_letter"]["records_available_days"]))),
                            "scope_ended": f"the preparation of your {self.tax_year} return",
                            "ended_by": "client", "balance": "no"},
                "rows": {"WorkStatus": [{"Work": f"{self.tax_year} return",
                                         "Status": "Not started"}],
                         "OpenDeadlines": [{"Obligation": f"{self.tax_year} return",
                                            "Detail": "Still due"}]}}

    def _filed(self, tr: Tracked, *, extended: bool, year: int, amended: bool = False) -> dict:
        c = tr.sim
        told = self.owner["close_out"]
        out = {"filed_form": c.form, "filed_basis": "amended" if amended else "original",
               "filed_state_count": int(told["filed_state_count"]),
               "filed_locality_count": int(told["filed_locality_count"]),
               "filed_extended": "yes" if extended else "no", "closeout_note": ""}
        if c.form == "1040":
            out.update(filed_joint="yes" if c.joint else "no", filed_dependents="no",
                       filed_k1s_received=0 if amended else (1 if c.features.get("k1") else 0),
                       filed_rentals=0 if amended else (1 if c.features.get("rental") else 0),
                       filed_businesses=0)
        elif c.form in ("1065", "1120S"):
            out.update(filed_k1s_issued=int(told["k1s_issued"][c.form]))
        return out

    # -- one business day ------------------------------------------------------
    def act(self, d: date) -> None:
        for tr in sorted(self.t.values(), key=lambda x: x.sim.idx):
            self._engage(tr, d)
        for tr in sorted(self.t.values(), key=lambda x: x.sim.idx):
            if not tr.engaged_on:
                continue
            self._letter(tr, d)
            self._arrivals(tr, d)
            self._disengage(tr, d)
            self._amended(tr, d)
            self._requote(tr, d)
        self._extensions(d)
        self._prepare(d)
        for tr in sorted(self.t.values(), key=lambda x: x.sim.idx):
            if tr.delivered_on:
                self._sign_8879(tr, d)
                self._payment(tr, d)
                self._transmit(tr, d)
        self._work_tasks(d)

    def _engage(self, tr: Tracked, d: date) -> None:
        c = tr.sim
        if tr.engaged_on or not c.engage_on or date.fromisoformat(c.engage_on) > d:
            return
        tr.engaged_on = d.isoformat()
        if not tr.satc_client:
            call, cid = self.satc.quick_add(name=c.name, entity_type=SATC_ENTITY[c.form],
                                            email=c.email)
            tr.satc_client = cid
            if not cid:
                self._refused(tr, call, d)
        mode = "returning" if c.returning else "new"
        for wf in c.satc_workflows:
            call, job = self.satc.new_engagement(
                client_id=tr.satc_client, workflow_key=wf, tax_year=self.tax_year,
                mode=mode, answers=satc_answers(c, wf, tax_year=self.tax_year))
            if job:
                tr.jobs[wf] = job
            else:
                self._refused(tr, call, d)
        if tr.main_job:
            call = self.satc.set_ref(tr.main_job, c.ref)
            if call.status != 302:
                self._refused(tr, call, d)
        if not c.satc_workflows:
            self.facts.append({"day": d.isoformat(), "sim": c.sim_id, "kind": "no_satc_workflow",
                               "detail": f"Form {c.form}: satc_system has no workflow to hold "
                                         f"this return (satc/intake/fanout.py:117)"})
        # The plan's dates onto the requests the workflows actually opened.
        mine = sorted((i for i in self.STATE.requested_items()
                       if i.client_id == tr.satc_client and i.tax_year == self.tax_year),
                      key=lambda i: (str(i.doc_type), i.request_id))
        plan = list(c.arrival_plan)
        for n, item in enumerate(mine):
            due = plan[n % len(plan)] if plan else None
            doc = str(item.doc_type)
            if doc == "K-1" and c.partnership:
                due = "k1"
            elif doc == "Engagement letter":
                due = (d + timedelta(days=c.letter_sign_lag or 1)).isoformat()
            elif doc == "Core income documents" and due:
                floor = c.features.get("core_income_not_before")
                if floor and due < floor:
                    due = floor
            tr.requests[item.request_id] = {"doc_type": doc, "due": due}

        # client-documents: the interview, and the pack going out.
        if c.returning:
            answers = cd_answers(c, tax_year=self.tax_year, owner=self.owner)
            answers.pop("returning_client", None)
            call, _ = self.cd.returning(c.prior_ref, c.ref, answers)
        else:
            call, _ = self.cd.interview(c.ref, cd_answers(c, tax_year=self.tax_year,
                                                          owner=self.owner))
        if call.status != 0:
            self._refused(tr, call, d)
            return
        self.cd.sent(c.ref, d.isoformat())
        tr.letter_signed_on = (d + timedelta(days=c.letter_sign_lag or 1)).isoformat()

    def _letter(self, tr: Tracked, d: date) -> None:
        if tr.letter_recorded or not tr.letter_signed_on or tr.letter_signed_on > d.isoformat():
            return
        for line in self._letter_lines(tr.sim.ref):
            call, _ = self.cd.record_signature(tr.sim.ref, line, tr.letter_signed_on)
            if call.status != 0:
                self._refused(tr, call, d)
        tr.letter_recorded = True

    def _arrival_due(self, tr: Tracked, due) -> str | None:
        if due == "k1":
            partner = self.t.get(tr.sim.partnership or "")
            if not partner or not partner.delivered_on:
                return None
            return (date.fromisoformat(partner.delivered_on)
                    + timedelta(days=tr.sim.k1_lag or 0)).isoformat()
        return due

    def _arrivals(self, tr: Tracked, d: date) -> None:
        if tr.disengaged_on:
            return
        open_ids = {i.request_id for i in self.STATE.requested_items() if i.is_open}
        for rid, info in sorted(tr.requests.items()):
            when = self._arrival_due(tr, info["due"])
            if when is None or when > d.isoformat() or rid not in open_ids:
                continue
            call = self.satc.received(rid, channel="email")
            info["recorded"] = d.isoformat()
            if call.status != 302:
                self._refused(tr, call, d)

    def _disengage(self, tr: Tracked, d: date) -> None:
        c = tr.sim
        if tr.disengaged_on or not c.disengage_on or c.disengage_on > d.isoformat():
            return
        tr.disengaged_on = d.isoformat()
        self._event(tr, c.ref, "disengagement", self._disengagement_payload(tr, d), d)
        self.facts.append({"day": d.isoformat(), "sim": c.sim_id, "kind": "no_door",
                           "detail": "disengagement recorded in client-documents; "
                                     "satc_system has no door for it"})
        if self.owner.get("on_disengage_mark_requests_na"):
            for item in list(self.STATE.requested_items()):
                if item.client_id == tr.satc_client and item.is_open:
                    self.satc.not_applicable(item.request_id, NA_REASON)

    def _amended(self, tr: Tracked, d: date) -> None:
        """An amended 2025 return: opened, signed for, delivered, authorised,
        and closed out only when client-documents' own gate is clear."""
        c = tr.sim
        if not c.amended_on or c.amended_on > d.isoformat() or tr.amended_filed:
            return
        ref = c.amended_ref
        if not tr.amended_created:
            call, _ = self.cd.interview(ref, cd_answers(c, tax_year=self.tax_year - 1,
                                                        amended=True, owner=self.owner))
            if call.status != 0:
                self._refused(tr, call, d)
                return
            tr.amended_created = d.isoformat()
            self.cd.sent(ref, d.isoformat())
            return
        created = date.fromisoformat(tr.amended_created)
        if not tr.amended_letter_recorded and d >= created + timedelta(days=c.letter_sign_lag or 1):
            for line in self._letter_lines(ref):
                self.cd.record_signature(ref, line, d.isoformat())
            tr.amended_letter_recorded = True
            return
        lags = self.owner["amended"]
        if tr.amended_letter_recorded and not tr.amended_delivered and \
                d >= created + timedelta(days=int(lags["deliver_after_days"])):
            tr.amended_delivered = d.isoformat()
            self._event(tr, ref, "delivery", self._delivery_payload(tr, d, year=self.tax_year - 1), d)
            return
        if tr.amended_delivered and not tr.amended_signed and \
                d >= date.fromisoformat(tr.amended_delivered) + timedelta(
                    days=int(lags["sign_after_delivery_days"])):
            for line in self._auth_lines(ref):
                self.cd.record_signature(ref, line, d.isoformat())
            tr.amended_signed = d.isoformat()
            return
        if tr.amended_signed and self._may_transmit(ref):
            call, _ = self.cd.close(ref, self._filed(tr, extended=False, year=self.tax_year - 1,
                                                     amended=True))
            tr.amended_filed = d.isoformat()
            if call.status != 0:
                self._refused(tr, call, d)

    def _may_file(self, ref: str) -> bool:
        import cli
        import engagements
        import lifecycle
        import packaging
        import signing
        from pathlib import Path
        store = Path(self.cd.store)
        record = engagements.load(ref, store)
        saved = lifecycle.load_saved(ref, "delivery", store) or {}
        deadline = (saved.get("answers") or {}).get("signature_deadline", "")
        return signing.may_file(ref, record, packaging.documents_for(record), cli.TEMPLATE_DIR,
                                store=store, deadline=deadline).clear

    def _may_transmit(self, ref: str) -> bool:
        """The owner's rule for closing out (scenario owner.transmit_when). `close`
        itself never asks may_file; waiting on it is this owner's choice."""
        rule = self.owner.get("transmit_when", "may_file_clear")
        if rule != "may_file_clear":
            raise ValueError(f"owner.transmit_when {rule!r} is not one the simulator knows")
        return self._may_file(ref)

    def _requote(self, tr: Tracked, d: date) -> None:
        c = tr.sim
        if tr.requoted_on or not c.requote_on or c.requote_on > d.isoformat():
            return
        tr.requoted_on = d.isoformat()
        call, _ = self.cd.requote(c.ref, ["count_brokerages=2"],
                                  "the client opened a second brokerage account")
        if call.status != 0:
            self._refused(tr, call, d)

    def _extensions(self, d: date) -> None:
        import deadlines
        lead = int(self.owner["extension_lead_days"])
        for tr in sorted(self.t.values(), key=lambda x: x.sim.idx):
            if not tr.open_for_work or tr.delivered_on or tr.extended_on:
                continue
            due = deadlines.filing_date(RETURN_TYPE[tr.sim.form], self.tax_year)
            if d < due - timedelta(days=lead):
                continue
            tr.extended_on = d.isoformat()
            self._event(tr, tr.sim.ref, "extension", self._extension_payload(tr), d)
            self.facts.append({"day": d.isoformat(), "sim": tr.sim.sim_id, "kind": "no_door",
                               "detail": "extension recorded in client-documents; "
                                         "satc_system has no door for it"})

    def _everything_in(self, tr: Tracked, d: date) -> bool:
        if tr.satc_client and tr.main_job:
            mine = [i for i in self.STATE.requested_items()
                    if i.client_id == tr.satc_client and i.tax_year == self.tax_year]
            return bool(mine) and all(not i.is_open for i in mine)
        # No satc job (Form 1120): the owner knows from the paper on the desk,
        # which no system records. The world's plan stands in for the desk.
        plan = [p for p in tr.sim.arrival_plan[:4]]
        return all(p is not None and p <= d.isoformat() for p in plan)

    def _prepare(self, d: date) -> None:
        """Earliest statutory deadline first, at a fixed capacity (assumption)."""
        import deadlines
        cap = int(self.owner["prep_capacity_per_day"])
        started = {sid for sid, _ in self.prep_queue}
        # finish what is due today
        for sid, done_on in list(self.prep_queue):
            if done_on <= d.isoformat():
                self.prep_queue.remove((sid, done_on))
                self._deliver(self.t[sid], d)
        ready = []
        for tr in self.t.values():
            if not tr.open_for_work or tr.delivered_on or tr.sim.sim_id in started:
                continue
            if not tr.letter_recorded or not self._everything_in(tr, d):
                continue
            rt = RETURN_TYPE[tr.sim.form]
            due = deadlines.filing_date(rt, self.tax_year, extended=bool(tr.extended_on))
            ready.append((due, tr.sim.ref, tr))
        for due, _ref, tr in sorted(ready, key=lambda r: (r[0], r[1]))[:cap]:
            tr.prep_started = d.isoformat()
            done = clock.add_business_days(d, int(self.owner["prep_days"]))
            self.prep_queue.append((tr.sim.sim_id, done.isoformat()))

    def _deliver(self, tr: Tracked, d: date) -> None:
        c = tr.sim
        tr.delivered_on = d.isoformat()
        for wf, job in tr.jobs.items():
            if wf in ("prior", "new_client_onboarding"):
                continue
            call = self.satc.delivered(job, d.isoformat())
            if call.status != 302:
                self._refused(tr, call, d)
        self._event(tr, c.ref, "delivery", self._delivery_payload(tr, d, year=self.tax_year), d)
        if self.owner.get("bill_at") == "delivery":
            self._bill(tr, d)

    def _bill(self, tr: Tracked, d: date) -> None:
        c = tr.sim
        tr.invoiced_on = d.isoformat()
        if self.world.billing_door == "satc":
            codes = list(SATC_LINES[c.form])
            if c.form == "1040" and c.features.get("brokerage"):
                codes.append("schedule_d")
            if c.features.get("rental"):
                codes.append("schedule_e_rental")
            if not codes or not tr.satc_client:
                self.facts.append({"day": d.isoformat(), "sim": c.sim_id, "kind": "no_door",
                                   "detail": f"no satc_system service code bills a Form {c.form}"})
                return
            # What each line says when added at the catalogue rate.
            said = {}
            calls, _total = self.satc.draft_total(client_id=tr.satc_client, tax_year=self.tax_year,
                                                  lines=[(code, "", "") for code in codes])
            for code, call in zip(codes, calls[1:]):
                m = PUT_IN.search(call.excerpt or "")
                said[code] = m.group(1).replace(",", "") if m else ""
            if not self.probes and len([v for v in said.values() if v]) > 1:
                self._probe_every_instruction(tr, codes, said, d)
            main = codes[0]
            note = (f"the price on engagement {c.ref}'s estimate" if said.get(main) else "")
            calls, number = self.satc.invoice(
                client_id=tr.satc_client, tax_year=self.tax_year,
                lines=[(main, said.get(main, ""), note)], issued_on=d.isoformat())
            tr.invoice = number
            if not number:
                for call in calls:
                    if call.status not in (302,):
                        self._refused(tr, call, d)
        else:
            self.cd_invoice_seq += 1
            number = f"{d.year}-{self.cd_invoice_seq:04d}"
            call, _ = self.cd.invoice(c.ref, number, f"{self.tax_year} tax year")
            tr.invoice = number if call.status == 0 else ""
            if call.status != 0:
                self._refused(tr, call, d)
        if tr.invoice and c.pay_lag is not None:
            tr.paid_on = (d + timedelta(days=c.pay_lag)).isoformat()
            if c.pay_style == "part" and c.pay_lag2 is not None:
                tr.paid2_on = (d + timedelta(days=max(c.pay_lag2, c.pay_lag))).isoformat()

    def _probe_every_instruction(self, tr: Tracked, codes: list, said: dict, d: date) -> None:
        """Do what EVERY line's refusal says, on a draft that is then discarded.
        Nothing is issued. The probe asks: does following the screen's own
        instruction on each line give the one price the client was quoted?"""
        from satc.billing.engagement_price import price_for_ref
        quoted = price_for_ref(tr.sim.ref)
        lines = [(code, said.get(code, ""), f"the price on engagement {tr.sim.ref}'s estimate"
                  if said.get(code) else "") for code in codes]
        calls, total = self.satc.draft_total(client_id=tr.satc_client, tax_year=self.tax_year,
                                             lines=lines)
        self.probes.append({
            "day": d.isoformat(), "sim": tr.sim.sim_id, "ref": tr.sim.ref,
            "estimate": getattr(quoted, "total", ""), "lines": lines, "draft_total": total,
            "refusals": {code: calls[i + 1].excerpt for i, code in enumerate(codes)},
            "call": {"door": "http", "target": "POST /invoices/new (header, add x"
                     f"{len(codes)}, then discard)", "args": {"lines": lines}}})

    def _sign_8879(self, tr: Tracked, d: date) -> None:
        c = tr.sim
        delivered = date.fromisoformat(tr.delivered_on)
        for who, lag in (("taxpayer", c.sign_8879_lag), ("spouse", c.spouse_8879_lag)):
            if lag is None or who in tr.recorded_8879:
                continue
            if who == "spouse" and not c.joint:
                continue
            signed = delivered + timedelta(days=lag)
            if signed > d:
                continue
            for line in self._auth_lines(c.ref, who if c.joint else ""):
                call, _ = self.cd.record_signature(c.ref, line, signed.isoformat())
                if call.status != 0:
                    self._refused(tr, call, d)
            tr.recorded_8879.add(who)
            if who == "taxpayer":
                tr.signed_8879_on = signed.isoformat()
            else:
                tr.spouse_8879_on = signed.isoformat()

    def _payment(self, tr: Tracked, d: date) -> None:
        c = tr.sim
        if tr.paid2_on and tr.payment_recorded and not tr.payment2_recorded \
                and tr.paid2_on <= d.isoformat() and self.world.billing_door == "satc":
            self._satc_payment(tr, d, second=True)
        if not tr.paid_on or tr.payment_recorded or tr.paid_on > d.isoformat():
            return
        if self.world.billing_door == "satc":
            self._satc_payment(tr, d, second=False)
            return
        # client-documents settles a bill only from what Square reports
        # (`cli.py payments`, payments.py:666; record_settlement's only caller is
        # cli.py:900). The two kinds are DIFFERENT gaps and are kept apart:
        #   check -- no command exists that records it. docs/OPERATING-PROCEDURES.md
        #            :382-385 already records this as "judgement, not procedure".
        #   card  -- the door exists (Square), but the simulator issues bills with
        #            --no-link and may not reach Square. A gap in the SIMULATOR.
        if c.pays_by == "check":
            tr.payment_recorded = "no-door"
            detail = (f"client paid invoice {tr.invoice} by check on {tr.paid_on}; "
                      f"no client-documents command records a check (recorded as a "
                      f"judgement for a person, OPERATING-PROCEDURES.md:382-385)")
        else:
            tr.payment_recorded = "no-door-sim"
            detail = (f"client paid invoice {tr.invoice} by card on {tr.paid_on}; "
                      f"card settlement exists only through Square, which the "
                      f"simulator may not reach (a simulator limit, not a product gap)")
        self.facts.append({"day": d.isoformat(), "sim": c.sim_id,
                           "kind": "no_door" if c.pays_by == "check" else "sim_limit",
                           "detail": detail})
        self.unrecordable_payments.append({
            "day": d.isoformat(), "sim": c.sim_id, "ref": c.ref, "invoice": tr.invoice,
            "paid_on": tr.paid_on, "by": c.pays_by})

    def _satc_payment(self, tr: Tracked, d: date, *, second: bool) -> None:
        """Money arriving, recorded on the invoice's own page (/invoices/<id>/paid).
        How much is the world's (scenario.yaml `money:`): the total; for a part
        payer a share now and the balance later; for an overpayer a bit more."""
        from decimal import Decimal
        c = tr.sim
        inv = next((i for i in self.STATE.store.load_invoices()
                    if i.invoice_id == tr.invoice), None)
        if inv is None:
            return
        money = self.sc.get("money") or {}
        total = Decimal(inv.total)
        if c.pay_style == "part":
            first = (total * Decimal(str(money["part_first_fraction"]))).quantize(Decimal("0.01"))
            amount = total - first if second else first
        elif c.pay_style == "over":
            amount = total + Decimal(str(money["overpay_amount"]))
        else:
            amount = total
        on = tr.paid2_on if second else tr.paid_on
        call = self.satc.paid(tr.invoice, amount=f"{amount:.2f}", on=on,
                              method="check" if c.pays_by == "check" else "card")
        status = "yes" if call.status == 302 else "refused"
        if second:
            tr.payment2_recorded = status
        else:
            tr.payment_recorded = status
        if call.status != 302:
            self._refused(tr, call, d)

    def _transmit(self, tr: Tracked, d: date) -> None:
        if tr.filed_on or tr.disengaged_on:
            return
        ref = tr.sim.ref
        if not self._may_transmit(ref):
            return
        tr.filed_on = d.isoformat()
        call, _ = self.cd.close(ref, self._filed(tr, extended=bool(tr.extended_on),
                                                 year=self.tax_year))
        if call.status != 0:
            self._refused(tr, call, d)
        self.facts.append({"day": d.isoformat(), "sim": tr.sim.sim_id, "kind": "no_door",
                           "detail": "return transmitted (Drake) and closed out in "
                                     "client-documents; satc_system has no door to record a "
                                     "Filing (firm decision D8, LOG.md:742)"})

    def _work_tasks(self, d: date) -> None:
        """Take the /work queue in the order GET /work renders it, a few internal
        tasks a day (the board the route handed its template, not a copy)."""
        cap = int(self.owner["task_capacity_per_day"])
        _call, _ids, ctx = self.satc.work()
        b = ctx.get("board")
        if b is None:
            return
        done = 0
        for item in b.workable:
            for task in item.job.tasks:
                if done >= cap:
                    return
                if task.audience == "internal" and task.is_open and not task.blocked_by:
                    self.satc.toggle_task(item.job.job_id, task.task_id)
                    done += 1
