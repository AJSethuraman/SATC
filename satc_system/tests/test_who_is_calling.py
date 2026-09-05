"""A caller is who launched it, not how the call arrived.

**THE DEFECT.** `acting_actor()` decided whether a caller was a human by asking
whether Flask happened to be handling a request::

    return Actor.owner() if has_request_context() else Actor.system("headless")

Its own docstring, two lines above, promised the opposite — *"Anything else — a
script, a scheduled sweep, an API tool, a model rung — gets a system actor and
is refused by require_human at the gate."* **A script is exactly what it did
not catch**, because `app.test_client()` creates a request context in one line
with no browser and no person. Reproduced 4 September 2026: inside a test
request context `acting_actor()` returned `Actor(kind='human', name='owner')`,
`require_human` passed, and a Python script issued an invoice and recorded a
payment.

The gate read **how the call arrived**, not **who made it**.

**WHAT IS DELIBERATELY NOT FIXED, and must not be quietly "improved" later.** A
local script that declares no role is still the owner. That is the same choice
Occam made and for the same reason: this box has no authentication, the tailnet
is the perimeter, and a restrictive default would only teach everybody to pass
`owner` everywhere — which is worse than being honest about where the boundary
is. What changes is that anything **launched as an agent** now says so, and
cannot talk its way out of it.
"""

from __future__ import annotations

import json

import pytest

from satc import principals as P


# ── the resolver ─────────────────────────────────────────────────────────────

def test_nothing_declared_is_the_owner():
    """The desktop UI and the owner's own scripts. Deliberate — see the module
    docstring before changing it."""
    assert P.resolve(None, None).is_owner
    assert P.resolve("", "").is_owner


def test_an_unrecognised_role_is_read_only_and_never_the_owner():
    """Failing open on a header nobody understands is how this class of bug
    happens a second time."""
    p = P.resolve("bookkeeper-ish", None)
    assert not p.is_owner
    assert p.caps == P.ROLES["observer"]
    assert not p.can(P.CAP_INVOICE_ISSUE)


def test_an_unrecognised_role_says_which_one_it_did_not_recognise():
    """A refusal a person cannot trace is a refusal they route around."""
    assert "bookkeeper-ish" in P.resolve("bookkeeper-ish", None).role


@pytest.mark.parametrize("cap", [
    P.CAP_STAGE_CONFIRM,        # confirming is saying a machine-read value is true
    P.CAP_INVOICE_ISSUE,        # a claim on somebody's bank account
    P.CAP_PAYMENT_RECORD,       # an assertion that money arrived
    P.CAP_PRICING_WRITE,        # a price nobody agreed
    P.CAP_CLIENT_CONTACT,       # cannot be recalled
])
def test_the_agent_does_not_carry_the_dangerous_capabilities(cap):
    assert not P.resolve("ai_staff", None).can(cap), (
        f"ai_staff carries {cap!r}, which is one of the five it must not")


@pytest.mark.parametrize("cap", [
    P.CAP_READ, P.CAP_INTAKE_POST, P.CAP_CLIENT_NEW, P.CAP_ENGAGEMENT_NEW,
])
def test_the_agent_can_still_do_its_actual_job(cap):
    """A role stripped so far that the work cannot be done gets worked around,
    and a worked-around control is worse than none. Preparation is the job."""
    assert P.resolve("ai_staff", None).can(cap)


def test_the_owner_carries_everything():
    assert P.OWNER.caps == P.ALL_CAPS


# ── assignment ───────────────────────────────────────────────────────────────

def test_no_assignment_means_every_client():
    """Right here and wrong in a system with authentication: the common case is
    the owner, who is assigned nothing because everything is theirs."""
    assert P.resolve("ai_staff", None).may_touch("SATC-001000")


def test_an_assignment_keeps_a_caller_out_of_other_books():
    p = P.resolve("ai_staff", "SATC-001000")
    assert p.may_touch("SATC-001000")
    assert not p.may_touch("SATC-002000")


def test_an_assignment_takes_globs_and_a_list():
    p = P.resolve("ai_staff", "SATC-001*, SATC-009000")
    assert p.may_touch("SATC-001000") and p.may_touch("SATC-0019999")
    assert p.may_touch("SATC-009000")
    assert not p.may_touch("SATC-002000")


def test_refusing_a_client_names_the_assignment():
    p = P.resolve("ai_staff", "SATC-001000")
    with pytest.raises(P.NotPermitted) as exc:
        p.require_client("SATC-002000", "run intake")
    said = str(exc.value)
    assert "SATC-002000" in said and "SATC-001000" in said


def test_refusing_a_capability_names_the_capability():
    with pytest.raises(P.NotPermitted) as exc:
        P.resolve("ai_staff", None).require(P.CAP_INVOICE_ISSUE, "issue an invoice")
    said = str(exc.value)
    assert P.CAP_INVOICE_ISSUE in said and "ai_staff" in said


def test_a_permitted_act_raises_nothing():
    P.resolve("ai_staff", None).require(P.CAP_READ, "read")
    P.OWNER.require(P.CAP_INVOICE_ISSUE, "issue an invoice")


# ── where the principal comes from ───────────────────────────────────────────

def test_outside_a_request_it_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv(P.ROLE_ENV, "ai_staff")
    monkeypatch.setenv(P.ASSIGNMENT_ENV, "SATC-001000")
    p = P.current()
    assert p.role == "ai_staff" and p.assignment == ("SATC-001000",)


def test_a_request_carrying_a_role_header_is_that_role(monkeypatch):
    monkeypatch.delenv(P.ROLE_ENV, raising=False)
    from satc.app.server import create_app
    app = create_app()
    with app.test_request_context("/", headers={P.ROLE_HEADER: "ai_staff"}):
        assert P.current().role == "ai_staff"


def test_a_request_with_no_header_falls_back_to_the_environment(monkeypatch):
    """THE ONE A NAIVE FIX GETS WRONG.

    An MCP server launched as `ai_staff` that makes an HTTP call to its own app
    sends no role header. If a missing header meant "owner", the agent would
    become the owner in transit — the original bug, rebuilt.
    """
    monkeypatch.setenv(P.ROLE_ENV, "ai_staff")
    from satc.app.server import create_app
    app = create_app()
    with app.test_request_context("/"):
        assert P.current().role == "ai_staff", (
            "a request with no role header washed the agent's role off")


def test_the_desktop_case_still_reaches_the_owner(monkeypatch):
    """The whole product must keep working. No role anywhere, in a request:
    that is a person at the browser, and they are the owner."""
    monkeypatch.delenv(P.ROLE_ENV, raising=False)
    monkeypatch.delenv(P.ASSIGNMENT_ENV, raising=False)
    from satc.app.server import create_app
    app = create_app()
    with app.test_request_context("/"):
        assert P.current().is_owner


# ── roles defined on the box ─────────────────────────────────────────────────

def test_a_typo_in_a_config_capability_is_dropped_not_granted(tmp_path,
                                                              monkeypatch):
    """A misspelt capability must not become access. It ends up an empty role,
    which can do nothing — the safe direction."""
    cfg = tmp_path / "principals.json"
    cfg.write_text(json.dumps({"roles": {"junior": {
        "capabilities": ["read", "invoice.isue"]}}}), encoding="utf-8")
    monkeypatch.setenv("SATC_PRINCIPALS", str(cfg))
    p = P.resolve("junior", None)
    assert p.can(P.CAP_READ)
    assert not p.can(P.CAP_INVOICE_ISSUE)


def test_an_unreadable_config_does_not_crash_the_app(tmp_path, monkeypatch):
    cfg = tmp_path / "principals.json"
    cfg.write_text("{ not json", encoding="utf-8")
    monkeypatch.setenv("SATC_PRINCIPALS", str(cfg))
    assert P.resolve("ai_staff", None).can(P.CAP_READ)


# ── the actual regression, end to end ────────────────────────────────────────

def test_a_script_launched_as_the_agent_cannot_issue_an_invoice(monkeypatch):
    """THE DEFECT, ASSERTED.

    A Python script with `app.test_request_context()` and no human anywhere
    used to be `Actor(kind='human', name='owner')` and passed `require_human`.
    Launched as an agent it must not be.
    """
    monkeypatch.setenv(P.ROLE_ENV, "ai_staff")
    from satc.app.server import create_app
    from satc.app.state import acting_actor
    from satc.models.actor import ActorRefused, require_human

    app = create_app()
    with app.test_request_context("/"):
        actor = acting_actor()
        assert actor.kind != "human", (
            f"a script launched as ai_staff is still {actor!r} — the gate is "
            f"reading the transport again")
        with pytest.raises(ActorRefused):
            require_human(actor, "issue an invoice")


def test_and_the_owner_at_the_browser_still_can(monkeypatch):
    monkeypatch.delenv(P.ROLE_ENV, raising=False)
    from satc.app.server import create_app
    from satc.app.state import acting_actor
    from satc.models.actor import require_human

    app = create_app()
    with app.test_request_context("/"):
        require_human(acting_actor(), "issue an invoice")   # must not raise


# ── the agent surface declares itself ────────────────────────────────────────

class _Stop(Exception):
    """Stops `main()` at the point the role has been set, before it serves."""


@pytest.fixture
def launched_role(monkeypatch):
    """Run `mcp_server.main()` and report the role it launched with.

    **PUTS THE ENVIRONMENT BACK BY HAND, and that is the point.** `main()`
    writes `os.environ` directly via `setdefault`, so `monkeypatch` never
    learns the key was touched and does not undo it. The first version of these
    two tests leaked `SATC_ROLE=ai_staff` into every test that ran afterwards
    and turned 29 of them red -- pricing, staging, delivery, all refusing the
    owner because the owner had quietly become an agent. They passed alone and
    failed in a full run, which is the shape of every order-dependent test
    anybody has ever had to debug.
    """
    import os
    from satc.api import mcp_server

    def run(preset: str | None):
        before = {k: os.environ.get(k) for k in (P.ROLE_ENV, P.ASSIGNMENT_ENV)}
        try:
            for k in (P.ROLE_ENV, P.ASSIGNMENT_ENV):
                os.environ.pop(k, None)
            if preset is not None:
                os.environ[P.ROLE_ENV] = preset
            seen = {}
            monkeypatch.setattr(mcp_server, "_build_server",
                                lambda **kw: (_seen(seen), _raise())[0])
            with pytest.raises(_Stop):
                mcp_server.main()
            return seen["role"]
        finally:
            for k, v in before.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def _seen(seen):
        import os as _os
        seen["role"] = _os.environ.get(P.ROLE_ENV)

    def _raise():
        raise _Stop

    return run


def test_the_mcp_server_launches_as_the_agent(launched_role):
    """The mechanism is only worth having if the agent's own entry point uses
    it. `main()` must set the role BEFORE it builds the server."""
    role = launched_role(None)
    assert role == "ai_staff", (
        f"the MCP server built itself as {role!r} -- an agent surface that "
        f"does not declare a role is the owner")


def test_a_launcher_that_chose_a_role_keeps_it(launched_role):
    """`setdefault`, not set. A briefing launched as `observer` must not be
    promoted to `ai_staff` by the server it is talking to."""
    assert launched_role("observer") == "observer"


def test_the_write_tools_are_still_refused_by_the_engine(monkeypatch):
    """THE POINT OF THE WHOLE CHANGE.

    Registration is a convenience now, not the boundary. So even with writes
    turned fully on, the agent must still be refused the acts its role does not
    carry -- by the engine, not by the tool list.
    """
    monkeypatch.setenv(P.ROLE_ENV, "ai_staff")
    monkeypatch.setenv("SATC_MCP_ALLOW_WRITES", "1")
    from satc.app.state import acting_actor
    from satc.models.actor import ActorRefused, require_human

    actor = acting_actor()
    assert actor.kind != "human"
    for act in ("issue an invoice", "record a payment",
                "confirm a staged value", "change what the practice charges"):
        with pytest.raises(ActorRefused):
            require_human(actor, act)


# ── the invariant this change nearly broke ───────────────────────────────────

def test_no_caller_became_more_permitted_than_before(monkeypatch):
    """**REFUSE MORE, NEVER LESS.** The whole point of the change.

    The first version of `principals.current()` sent every undeclared caller to
    the environment, so a HEADLESS script -- no request, no role -- came back as
    the owner. `acting_actor` had refused that caller since it was written. The
    change closed the agent hole and opened a wider one, and `test_actor_gate`
    failed on exactly that.

    So the four cases are pinned against what the OLD derivation said, and the
    only permitted difference is in the safe direction.
    """
    from satc.app.server import create_app
    from satc.app.state import acting_actor

    app = create_app()

    def old_answer(in_request: bool) -> bool:
        """`Actor.owner() if has_request_context() else system` -- was it human?"""
        return in_request

    def new_answer(in_request: bool, role: str | None) -> bool:
        if role is None:
            monkeypatch.delenv(P.ROLE_ENV, raising=False)
        else:
            monkeypatch.setenv(P.ROLE_ENV, role)
        if in_request:
            with app.test_request_context("/"):
                return acting_actor().is_human
        return acting_actor().is_human

    loosened = []
    for in_request in (True, False):
        for role in (None, "ai_staff", "observer", "reviewer", "nonsense"):
            was, now = old_answer(in_request), new_answer(in_request, role)
            if now and not was:
                loosened.append(f"in_request={in_request} role={role!r}: "
                                f"was refused, is now the owner")
    assert not loosened, (
        "these callers gained permission they did not have before: "
        + "; ".join(loosened))


def test_a_headless_script_is_still_refused(monkeypatch):
    """Named on its own because it is the one that regressed."""
    monkeypatch.delenv(P.ROLE_ENV, raising=False)
    from satc.app.state import acting_actor
    from satc.models.actor import ActorRefused, require_human

    actor = acting_actor()
    assert not actor.is_human and actor.kind == "system"
    with pytest.raises(ActorRefused):
        require_human(actor, "confirm a staged value")


# ── check the checker ────────────────────────────────────────────────────────

def test_the_old_derivation_reproduces_and_disagrees(monkeypatch):
    """MUTATION. The old rule was `Actor.owner() if has_request_context()`.
    Reintroduce it and it must disagree with the new answer for an agent —
    otherwise the tests above pin nothing.
    """
    monkeypatch.setenv(P.ROLE_ENV, "ai_staff")
    from flask import has_request_context
    from satc.app.server import create_app
    from satc.app.state import acting_actor
    from satc.models.actor import Actor

    app = create_app()
    with app.test_request_context("/"):
        old = Actor.owner() if has_request_context() else Actor.system("headless")
        new = acting_actor()
        assert old.kind == "human", "the old behaviour no longer reproduces"
        assert new.kind != "human"
        assert old != new, "old and new agree — the fix is doing nothing"


def test_nothing_decides_who_is_calling_by_asking_about_the_request():
    """The rule is only worth having while it is the only decision.

    `has_request_context` is a fine thing to ask when you want to know whether
    there is a request. It is not a way to find out who is calling, and that
    confusion was the whole defect — so a function that does both is worth
    failing over.

    **READ AS CODE, NOT AS TEXT.** The first version grepped lines, and its
    first run failed on the old expression QUOTED IN A DOCSTRING explaining the
    defect — a checker that cannot tell code from prose would have made writing
    down what went wrong an error. Parsing removes the question: a docstring is
    not a call node.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "satc"
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "principals.py":
            continue                       # where the decision now lives
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:                # not ours to police
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = node.body[1:] if (node.body and isinstance(node.body[0], ast.Expr)
                                     and isinstance(node.body[0].value, ast.Constant)
                                     ) else node.body      # drop the docstring
            names = {n.id for b in body for n in ast.walk(b)
                     if isinstance(n, ast.Name)}
            attrs = {n.attr for b in body for n in ast.walk(b)
                     if isinstance(n, ast.Attribute)}
            if "has_request_context" in names and (
                    "Actor" in names or "acting_actor" in names
                    or {"owner", "system", "model"} & attrs):
                offenders.append(f"{path.relative_to(root)}:{node.lineno}: "
                                 f"{node.name}()")
    assert not offenders, (
        "these decide an Actor from whether a request exists, which is the "
        "defect this module removed: " + "; ".join(offenders))
