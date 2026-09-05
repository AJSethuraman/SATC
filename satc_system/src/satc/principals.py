"""Who is calling, and what they are allowed to do.

**THE DEFECT THIS REPLACES.** `satc.app.state.acting_actor` decided whether a
caller was a human by asking whether Flask happened to be handling a request::

    return Actor.owner() if has_request_context() else Actor.system("headless")

Its own docstring, two lines above, promised the opposite — *"Anything else — a
script, a scheduled sweep, an API tool, a model rung — gets a system actor and
is refused by require_human at the gate."* **A script is exactly what it did not
catch**, because `app.test_client()` and `test_request_context()` create a
request context in one line, with no browser and no person. Reproduced on
4 September 2026: inside a test request context, `acting_actor()` returned
`Actor(kind='human', name='owner')` and `require_human` passed, so a Python
script issued an invoice and recorded a payment.

The gate read **how the call arrived**, not **who made it**. That is the same
shape as the other defect found the same evening — `--store` scoped the invoice
file and not the Square account — and it is the shape to watch for: a control
that infers identity from transport.

**THE MODEL, ported from Occam** (`occam_processor/principals.py`), which was
written after an eval run wandered onto a real client's books and deactivated
three live accounts. Two ideas, both borrowed from how a firm actually works:

**Role** — what kind of work a caller may do at all. A staff accountant
prepares and proposes; issuing a bill, taking money and writing to the client
are somebody else's job. Enforced here, not asked for in a prompt. The Forge's
own standing rule says why: *a skill's `tools:` list is not a security
boundary* — that is a convention, and a convention is not a gate.

**Assignment** — *whose* books. A caller assigned one client cannot wander into
another's out of curiosity.

**A caller in a live request that declares nothing is the owner** — the desktop
UI. Deliberate, and unchanged from before this module existed: the box has no
authentication and the tailnet is the perimeter, a decision recorded in
`CLIENT-DATA-ASSESSMENT.md`. Making that default restrictive would only teach
everyone to pass `owner` everywhere, which is worse than being honest about
where the boundary is.

**A caller with no request and no role is HEADLESS, and headless is not the
owner.** A script, a scheduled sweep, an import of `STATE` from somewhere. This
was always the behaviour and it stays: `require_human` refuses it.

**The first version of this module got that wrong, and the existing suite caught
it.** It sent every undeclared caller to the environment, so a headless script
came back as the owner — a caller `acting_actor` had always refused. It closed
the agent hole and opened a wider one. `test_actor_gate.py` failed on precisely
that, which is the whole reason those two tests exist. **Nothing here may make a
previously-refused caller permitted: the point was to refuse more, never less.**

**An unrecognised role is `observer`, never owner.** Failing open on a header
nobody understands is how this class of bug happens a second time.

This module is NOT authentication and does not pretend to be. It is capability
separation between an agent and the people, which is a different problem and the
one that has actually bitten.
"""

from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# ── Capabilities ─────────────────────────────────────────────────────────────
#
# COARSE ON PURPOSE, and named for the KIND OF HARM rather than the endpoint. A
# capability per route drifts out of date the first time somebody adds one, and
# a permission model that is behind the code grants things nobody decided.

CAP_READ = "read"                     # any GET, any query
CAP_STAGE_CONFIRM = "stage.confirm"   # a read value becomes a confirmed one
CAP_INTAKE_POST = "intake.post"       # confirmed intake reaches the workpaper
CAP_CLIENT_NEW = "client.create"      # a client enters the vault
CAP_ENGAGEMENT_NEW = "engagement.create"   # a contract for a year
CAP_PRICING_WRITE = "pricing.write"   # a rate or a discount, in the config
CAP_INVOICE_ISSUE = "invoice.issue"   # a claim on somebody's bank account
CAP_PAYMENT_RECORD = "payment.record"  # money is asserted to have arrived
CAP_CLIENT_CONTACT = "client.contact"  # anything a client can see

ALL_CAPS = frozenset({
    CAP_READ, CAP_STAGE_CONFIRM, CAP_INTAKE_POST, CAP_CLIENT_NEW,
    CAP_ENGAGEMENT_NEW, CAP_PRICING_WRITE, CAP_INVOICE_ISSUE,
    CAP_PAYMENT_RECORD, CAP_CLIENT_CONTACT,
})

# ── Roles ────────────────────────────────────────────────────────────────────

ROLES: dict[str, frozenset[str]] = {
    # The owner of the box. Everything, including the irreversible things.
    "owner": ALL_CAPS,

    # A human reviewer: everything the agent does, plus the money and the
    # client. Not pricing — what the practice charges is the owner's.
    "reviewer": frozenset({
        CAP_READ, CAP_STAGE_CONFIRM, CAP_INTAKE_POST, CAP_CLIENT_NEW,
        CAP_ENGAGEMENT_NEW, CAP_INVOICE_ISSUE, CAP_PAYMENT_RECORD,
        CAP_CLIENT_CONTACT,
    }),

    # The AI staff accountant: read, prepare, propose, take work in.
    #
    # WHAT IT DOES NOT HAVE, AND WHY EACH ONE IS OUT:
    #
    # `stage.confirm` — confirming is the act of saying a machine-read value is
    #   true. `staging_gate` already refuses a non-human confirm at any
    #   confidence, and this agrees with it rather than arguing.
    # `invoice.issue` / `payment.record` — an invoice is a claim on somebody's
    #   bank account and a recorded payment is an assertion that money arrived.
    #   Both are the firm's word, not a model's.
    # `pricing.write` — a rate changed by an agent is a price nobody agreed.
    # `client.contact` — a question sent to a client cannot be recalled. This
    #   is the same line Occam draws, for the same reason.
    #
    # It KEEPS `intake.post` and `engagement.create`: posting confirmed intake
    # and generating an engagement from answers are preparation, and preparation
    # is the whole job. Both are idempotent and reversible.
    "ai_staff": frozenset({
        CAP_READ, CAP_INTAKE_POST, CAP_CLIENT_NEW, CAP_ENGAGEMENT_NEW,
    }),

    # Read-only: briefings, dashboards, anything that must not write.
    "observer": frozenset({CAP_READ}),
}


class NotPermitted(PermissionError):
    """A caller asked for something their role does not carry.

    A `PermissionError` rather than a bare exception so a caller that means to
    catch it says so, and a caller that does not gets a refusal rather than a
    silently wrong answer.
    """


@dataclass(frozen=True)
class Principal:
    """The caller: what they may do, and whose books they may touch."""

    role: str
    caps: frozenset[str]
    assignment: tuple[str, ...] = field(default=())
    """Client ids this caller is assigned, ``*`` globs allowed. Empty = all.

    Empty meaning *all* is right here and would be wrong in a system with
    authentication: the common case is the owner, who is assigned nothing
    because everything is theirs.
    """

    # -- questions ------------------------------------------------------------

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    def can(self, cap: str) -> bool:
        return cap in self.caps

    def may_touch(self, client_id: str) -> bool:
        if not self.assignment:
            return True
        cid = (client_id or "").strip().lower()
        return any(fnmatch.fnmatch(cid, pat.lower()) for pat in self.assignment)

    def describe_assignment(self) -> str:
        return ", ".join(self.assignment) if self.assignment else "all clients"

    # -- refusals -------------------------------------------------------------

    def require(self, cap: str, what: str) -> None:
        """Refuse unless this caller carries `cap`, and say what would not.

        The message names the role, the act and the capability, because a
        refusal a person cannot act on is a refusal they will route around.
        """
        if self.can(cap):
            return
        raise NotPermitted(
            f"{self.role} may not {what}. That needs the {cap!r} capability, "
            f"which this role does not carry. Whatever launched this process "
            f"decides the role — the caller cannot widen its own.")

    def require_client(self, client_id: str, what: str) -> None:
        """Refuse unless this client is inside the caller's assignment."""
        if self.may_touch(client_id):
            return
        raise NotPermitted(
            f"{self.role} is assigned {self.describe_assignment()} and may not "
            f"{what} for {client_id}. An assignment is set by whatever launched "
            f"this process.")


OWNER = Principal(role="owner", caps=ALL_CAPS)

#: The headers a launcher sets. Named for this system so a proxy that forwards
#: everything cannot collide with somebody else's.
ROLE_HEADER = "X-SATC-Role"
ASSIGNMENT_HEADER = "X-SATC-Assignment"

#: The same two, for an entry point with no HTTP in it — the MCP server, a
#: scheduled sweep. Read once per call rather than cached, so a test can set
#: them and a long-lived process cannot hold a stale role.
ROLE_ENV = "SATC_ROLE"
ASSIGNMENT_ENV = "SATC_ASSIGNMENT"


def _extra_roles() -> dict[str, frozenset[str]]:
    """Roles defined on this box, if any.

    An unknown capability name is DROPPED rather than granted — a typo in a
    config file must not become access. A role that ends up empty is still a
    role, and it can do nothing, which is the safe direction.
    """
    raw_path = os.environ.get("SATC_PRINCIPALS")
    if not raw_path:
        return {}
    path = Path(raw_path)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, frozenset[str]] = {}
    for name, spec in (raw.get("roles") or {}).items():
        caps = {c for c in (spec.get("capabilities") or []) if c in ALL_CAPS}
        out[str(name).strip().lower()] = frozenset(caps)
    return out


def resolve(role: str | None, assignment: str | None) -> Principal:
    """Build a principal from a role name and an assignment list.

    Nothing given is the OWNER — the desktop UI, and the owner's own scripts.
    An unrecognised role is OBSERVER, never owner.
    """
    if not role or not role.strip():
        return OWNER

    name = role.strip().lower()
    caps = {**ROLES, **_extra_roles()}.get(name)
    if caps is None:
        # Say which role was not recognised, in the role's own name, so the
        # refusal a caller reads later explains itself without a log dive.
        return Principal(role=f"observer (unrecognised role {role.strip()!r})",
                         caps=ROLES["observer"])

    parts: tuple[str, ...] = ()
    if assignment and assignment.strip():
        parts = tuple(s.strip() for s in assignment.split(",") if s.strip())
    return Principal(role=name, caps=frozenset(caps), assignment=parts)


def from_environment() -> Principal:
    """The principal for a process with no request in it."""
    return resolve(os.environ.get(ROLE_ENV), os.environ.get(ASSIGNMENT_ENV))


#: What a process with no request and no declared role is. NOT the owner --
#: see `current()`.
HEADLESS = Principal(role="headless", caps=ROLES["observer"])


def current() -> Principal:
    """The principal for whatever is calling right now.

    Three cases, and the ordering is the whole design:

    1. **A role was declared** — by a header on this request, or by the
       environment the process was launched with. That role, whatever the
       transport. This is what closes the hole: an agent stays an agent inside
       a request context.
    2. **No role, but a live request** — the desktop UI. The owner. This is the
       pre-existing accepted position on a box with no authentication, and it
       is unchanged: the tailnet is the perimeter, and a restrictive default
       here would only teach everyone to pass ``owner`` everywhere.
    3. **No role and no request** — headless. A script, a scheduled sweep, an
       import of ``STATE`` from somewhere. **Not the owner**, exactly as before.

    **CASE 3 IS HERE BECAUSE THE FIRST VERSION GOT IT WRONG AND THE SUITE
    CAUGHT IT.** That version sent every undeclared caller to the environment,
    so a headless script with no role came back as the owner — a caller that
    `acting_actor` had always refused. It closed the agent hole and opened a
    wider one, and `test_actor_gate.py` failed on exactly that. Nothing about
    this change may make a previously-refused caller permitted; the point was
    to refuse MORE, never less.
    """
    declared = os.environ.get(ROLE_ENV)
    try:
        from flask import has_request_context, request
    except ImportError:                      # app extras not installed
        return resolve(declared, os.environ.get(ASSIGNMENT_ENV)) if declared             else HEADLESS

    in_request = has_request_context()
    if in_request:
        header = request.headers.get(ROLE_HEADER)
        if header:
            return resolve(header, request.headers.get(ASSIGNMENT_HEADER))
    if declared:
        # An MCP server launched as `ai_staff` that makes an HTTP call to its
        # own app sends no role header. If a missing header meant "owner", the
        # agent would become the owner in transit -- the original bug, rebuilt.
        return resolve(declared, os.environ.get(ASSIGNMENT_ENV))
    return OWNER if in_request else HEADLESS
