"""satc_system's front doors, driven through Flask's test client, in-process.

Every owner act goes through a route a person could press -- never a store
write. Where no route exists for an act the owner needs (an e-file
acknowledgement, an extension, a disengagement, an 8879 request, withdrawing a
request), there is deliberately no method here: the simulator records the gap
instead (H14 in the brief).

Each call returns a `Call`, which is what a finding quotes as its evidence.
"""

from __future__ import annotations

import html
import re
from contextlib import contextmanager
from dataclasses import dataclass, field

from season_sim import guard

CLIENT_ID = re.compile(r"SATC-\d+")
JOB_ID = re.compile(r"/engagements/(engagement-[0-9a-f]+)")
ACTION_ID = re.compile(r'name="action_id"\s+value="([^"]+)"')
RETURN_KEY = re.compile(r'name="return_key"\s+value="([^"]*)"')
TOTAL_DUE = re.compile(r"(?:Total due|Total — no charge)</b>\s*<span[^>]*><strong>([\d,]+\.\d\d)")
FLAG = re.compile(r'<p class="flag">(.*?)</p>', re.S)
WORK_JOB = re.compile(r'href="/work/(engagement-[0-9a-f]+)"')


@dataclass
class Call:
    door: str            # "http" | "cli" | "function"
    target: str
    args: dict = field(default_factory=dict)
    status: int | str = 0
    excerpt: str = ""

    def brief(self) -> dict:
        return {"door": self.door, "target": self.target, "args": self.args,
                "status": self.status}


@contextmanager
def _no_banned_call(what: str):
    """A route that reached a banned door ends the run, even if Flask turned the
    refusal into a 500 page: the count is taken at the ban (guard.py)."""
    before = len(guard.BANNED_ATTEMPTS)
    yield
    if len(guard.BANNED_ATTEMPTS) > before:
        raise guard.SimRefused(f"{what} tried a banned door: {guard.BANNED_ATTEMPTS[before:]}")


class SatcDoors:
    def __init__(self, app, log: list):
        self.app = app
        self.c = app.test_client()
        self.log = log

    def _post(self, url: str, data: dict) -> tuple[Call, object]:
        with _no_banned_call(f"POST {url}"):
            r = self.c.post(url, data=data)
        said = r.headers.get("Location") or ""
        if r.status_code != 302:
            # A refusal is rendered on the page it happened on (class="flag").
            flags = FLAG.findall(r.get_data(as_text=True))
            said = " | ".join(html.unescape(re.sub(r"<[^>]+>", "", f)).strip()
                              for f in flags) or f"(no flag on a {r.status_code} page)"
        call = Call("http", f"POST {url}", dict(data), r.status_code, said[:400])
        self.log.append(call)
        return call, r

    def get(self, url: str) -> tuple[Call, str]:
        with _no_banned_call(f"GET {url}"):
            r = self.c.get(url)
        call = Call("http", f"GET {url}", {}, r.status_code)
        body = r.get_data(as_text=True)
        return call, body

    def rendered(self, url: str) -> tuple[Call, str, dict]:
        """GET a page and keep what the ROUTE handed its template.

        The checks read this, not a copy of the route's arguments: if the route
        changes what it passes to the engine, the check sees the change. Flask's
        `template_rendered` signal carries the exact context `render_template`
        was called with (the queue object /today built, the board /work built,
        the StageView a job page derived)."""
        from flask import template_rendered
        seen: list[dict] = []

        def keep(_app, template, context, **_extra):
            seen.append(dict(context))
        template_rendered.connect(keep, self.app)
        try:
            call, body = self.get(url)
        finally:
            template_rendered.disconnect(keep, self.app)
        return call, body, (seen[0] if seen else {})

    # -- owner acts -------------------------------------------------------
    def quick_add(self, *, name: str, entity_type: str, email: str,
                  state: str = "MA") -> tuple[Call, str]:
        """No TIN: blank is honest (intake/service.py:59-86)."""
        call, r = self._post("/clients/quick-add", dict(
            name=name, entity_type=entity_type, email=email, state=state))
        found = CLIENT_ID.search(r.headers.get("Location") or "")
        return call, found.group(0) if found else ""

    def new_engagement(self, *, client_id: str, workflow_key: str, tax_year: int,
                       mode: str, answers: dict) -> tuple[Call, str]:
        data = dict(client=client_id, workflow_key=workflow_key,
                    tax_year=str(tax_year), mode=mode)
        data.update({f"q_{k}": v for k, v in answers.items()})
        call, r = self._post("/intake/new", data)
        found = JOB_ID.search(r.headers.get("Location") or "")
        return call, found.group(1) if found else ""

    def set_ref(self, job_id: str, ref: str) -> Call:
        call, _ = self._post(f"/engagements/{job_id}/ref", {"engagement_ref": ref})
        return call

    def received(self, request_id: str, channel: str = "email") -> Call:
        call, _ = self._post(f"/documents/{request_id}/close",
                             {"how": "received", "channel": channel})
        return call

    def not_applicable(self, request_id: str, reason: str) -> Call:
        call, _ = self._post(f"/documents/{request_id}/close",
                             {"how": "not_applicable", "reason": reason})
        return call

    def toggle_task(self, job_id: str, task_id: str) -> Call:
        call, _ = self._post(f"/engagements/{job_id}/tasks/{task_id}", {})
        return call

    def delivered(self, job_id: str, on: str, kind: str = "return_for_review",
                  channel: str = "portal") -> Call:
        """Pressed as the page draws it: the owner keeps the pre-filled
        'Which return' value (job.html:171-172) rather than retyping it."""
        _c, page = self.get(f"/work/{job_id}")
        m = RETURN_KEY.search(page)
        key = html.unescape(m.group(1)) if m else ""
        call, _ = self._post(f"/work/{job_id}/delivered", dict(
            delivered_on=on, kind=kind, channel=channel, return_key=key))
        return call

    def invoice(self, *, client_id: str, tax_year: int, lines: list,
                issued_on: str) -> tuple[list[Call], str]:
        """The sequence `scripts/demo_arc.py:121-160` walks, through the test client."""
        calls, page = self._draft(client_id, tax_year, lines)
        m = re.search(r"Issue invoice (20\d\d-\d{4})", page)
        number = m.group(1) if m else ""
        if not number:
            said = [c.excerpt for c in calls if c.excerpt and not c.excerpt.startswith("(no flag")]
            said += [html.unescape(re.sub(r"<[^>]+>", "", f)).strip() for f in FLAG.findall(page)]
            miss = Call("http", "GET /invoices/new", {}, 200,
                        ("no 'Issue invoice' button on the build screen. " + " | ".join(said))[:400])
            self.log.append(miss)
            calls.append(miss)
            self._post("/invoices/new", dict(action="discard"))
            return calls, ""
        c3, r = self._post(f"/invoices/{number}/issue",
                           dict(issued_on=issued_on, due_in_days="30"))
        calls.append(c3)
        got = re.search(r"/invoices/(20\d\d-\d{4})", r.headers.get("Location") or "")
        return calls, got.group(1) if got else ""

    def _draft(self, client_id: str, tax_year: int, lines: list) -> tuple[list[Call], str]:
        calls = []
        c1, _ = self._post("/invoices/new", dict(action="header", client_id=client_id,
                                                 tax_year=str(tax_year),
                                                 plan_key="standard", plan_basis=""))
        calls.append(c1)
        for line in lines:
            code, rate, note = (line, "", "") if isinstance(line, str) else line
            c2, _ = self._post("/invoices/new", dict(action="add", service_code=code,
                                                     quantity="1", rate_override=rate,
                                                     note=note))
            calls.append(c2)
        _, page = self.get("/invoices/new")
        return calls, page

    def draft_total(self, *, client_id: str, tax_year: int, lines: list) -> tuple[list[Call], str]:
        """Build a draft, read its Total due off the build screen, then DISCARD it.
        Nothing is issued or stored: a discarded draft was never written down."""
        calls, page = self._draft(client_id, tax_year, lines)
        m = TOTAL_DUE.search(page)
        total = m.group(1) if m else ""
        c3, _ = self._post("/invoices/new", dict(action="discard"))
        calls.append(c3)
        return calls, total

    def paid(self, invoice_id: str, *, amount: str, on: str, method: str) -> Call:
        call, _ = self._post(f"/invoices/{invoice_id}/paid", dict(
            amount=amount, received_on=on, method=method, reference="simulated"))
        return call

    # -- screens ----------------------------------------------------------
    def today(self) -> tuple[Call, list[str], dict]:
        """/today: the action ids in page order, and what the route rendered."""
        call, body, ctx = self.rendered("/today")
        return call, ACTION_ID.findall(body), ctx

    def work(self) -> tuple[Call, list[str], dict]:
        """/work: the job ids in page order, and what the route rendered."""
        call, body, ctx = self.rendered("/work")
        seen: list[str] = []
        for j in WORK_JOB.findall(body):
            if j not in seen:
                seen.append(j)
        return call, seen, ctx
