"""Which nav item is lit, decided from the ROUTE rather than the page title.

D7, from the walk of 5 September 2026: on `/intake`, `/intake/new` and
`/intake/plan`, both **Intake** and **Engagements** carried the active
background and the gold left bar. A person cannot tell from the nav which screen
they are on.

The cause is that the nav decided from the page's `title`:

    class="{{ 'active' if title=='Intake' }}"                       Intake
    class="{{ 'active' if title in ['Engagements','New client','Intake'] }}"

and `title="Intake"` is used by FOUR screens across two nav items -- the
document-reading Intake screen in `server.py`, and `/intake/new`,
`/intake/plan` and `/intake/organizer` in `intake_views.py`. The title is a
heading for a person to read; it was never an identifier, and asking it to be
one produced two answers to a question with one answer.

The same guesswork is visible elsewhere in that nav: `'nvoice' in title`, spelt
without its leading letter so it catches both "Invoices" and "Invoice
2026-0001". That works, and it is a substring search over prose.

A route knows exactly which screen it is. `request.endpoint` is that, and it
cannot be two things at once -- which is the property the old test did not have
and the reason this is a table rather than fifteen independent conditions:
FIRST MATCH WINS, so exactly one item is lit, always, and a screen that belongs
to no item lights none rather than two.

ORDER IS LOAD-BEARING. `clients` sits above `engagements` because several
client screens live on the `intake.` blueprint (`intake.new_client`,
`intake.client_start`) and would otherwise be swallowed by its prefix. Anything
moved above another entry changes which item claims a shared route.

A trailing dot means "this blueprint"; anything else is an exact endpoint. The
prefix form is what keeps a new route in an existing area working without an
edit here -- and a new route in a NEW area lights nothing, which is honest.
"""

from __future__ import annotations

# (nav key, endpoint patterns). First match wins; see ORDER above.
NAV: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("today",          ("today.",)),
    ("intake",         ("intake", "intake_run", "source_file")),
    ("sort",           ("sort", "sort_apply")),
    ("staging",        ("staging", "staging_action", "staging_auto", "staging_post")),
    ("documents",      ("documents", "close_request")),
    ("clients",        ("clients_index", "client", "discard_client", "drake_entry",
                        "delivery_email", "intake.new_client", "intake.quick_add_client",
                        "intake.import_clients", "intake.import_clients_confirm",
                        "intake.client_start")),
    ("engagements",    ("intake.",)),
    ("questionnaires", ("workflows.",)),
    ("comms",          ("comms.",)),
    ("work",           ("work.",)),
    ("invoices",       ("billing.",)),
    ("pricing",        ("pricing.",)),
    ("withholding",    ("withholding.", "api_withholding_estimate",
                        "api_withholding_meta", "api_read_paystub")),
    ("autonomy",       ("autonomy.",)),
    ("setup",          ("setup", "clear_sample", "export")),
    ("dashboard",      ("dashboard",)),
)


def active(endpoint: str | None) -> str:
    """The single nav item this route belongs to, or "" for none.

    "" is a real answer, not a failure: a route nobody has placed lights nothing,
    which tells the truth. Lighting a guess would put us back where D7 started.
    """
    name = endpoint or ""
    for key, patterns in NAV:
        for pattern in patterns:
            if pattern.endswith(".") and name.startswith(pattern):
                return key
            if name == pattern:
                return key
    return ""
