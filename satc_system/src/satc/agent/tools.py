"""The tool surface a local model is allowed to touch.

Every tool here is READ or PROPOSE. There is no write tool, and that is the
primary control — doctrine rule 7 says permissions are server-side roles, not
tool lists, but the strongest version of both is a surface where the dangerous
operation *does not exist*. If one were ever added, the staging gate and
``require_human`` refuse it anyway.

Three properties every tool holds to, because an 8B model fails at exactly these
points:

* **Small results** (rules 1 and 2). ``today()`` returns six numbers and at most
  eight lines, never 200 obligation rows. The model works categories, not lists.
* **Errors that teach** (rule 3). An unknown client returns the list of real
  ones; a bad template names the ones that exist. A refusal that only says "no"
  ends the run.
* **Nothing invented.** Every figure comes from the engine. The model's job is
  to read, phrase, and ask — never to compute a number that matters.
"""

from __future__ import annotations

from datetime import date
from typing import Any

MAX_ROWS = 8
"""Hard cap on rows any tool returns. A small model loses the thread on long
lists long before it runs out of context — 84 rows killed runs on the sister
project. Anything longer is summarised and the count is stated."""


def _truncate(rows: list, total: int | None = None) -> tuple[list, str]:
    total = len(rows) if total is None else total
    if total <= MAX_ROWS:
        return rows, ""
    return rows[:MAX_ROWS], f"showing {MAX_ROWS} of {total}"


def _client_names(state) -> dict[str, str]:
    return {cid: name for cid, name in state.client_choices()}


def _stem(word: str) -> str:
    """Crude singularisation, enough to match how people actually talk.

    The owner says "the Maplewoods" and "Beacon Hill". Neither is a substring of
    the stored name, so plain containment fails on both — found by putting the
    real question to the real model, not by unit tests.
    """
    w = word.strip().lower().strip(".,'’")
    if w.endswith("'s") or w.endswith("’s"):
        w = w[:-2]
    return w[:-1] if len(w) > 4 and w.endswith("s") else w


def _tokens(text: str) -> set[str]:
    import re

    return {_stem(w) for w in re.split(r"[^a-z0-9]+", (text or "").lower())
            if len(w) >= 3 and w not in {"the", "and", "inc", "llc", "llp", "corp", "ltd"}}


def _resolve_client(state, client: str) -> tuple[str, str] | dict:
    """A client id or name -> (id, name), or an error that lists the real ones."""
    names = _client_names(state)
    needle = (client or "").strip().lower()
    if not needle:
        return {"error": "no client given",
                "next_step": "call this tool again with one of these clients",
                "clients": sorted(names.values())[:MAX_ROWS]}
    for cid, name in names.items():
        if needle == cid.lower() or needle == name.lower():
            return cid, name

    # Token overlap, singularised. "the Maplewoods" -> {maplewood} matches
    # "Jordan & Avery Maplewood" -> {jordan, avery, maplewood}.
    wanted = _tokens(needle)
    if wanted:
        matches = [(cid, name) for cid, name in names.items()
                   if wanted & _tokens(name)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return {"error": f"{client!r} matches more than one client",
                    "next_step": "name one of these exactly",
                    "clients": sorted(n for _, n in matches)}
    return {"error": f"no client matching {client!r}",
            "next_step": "use one of these exact names",
            "clients": sorted(names.values())[:MAX_ROWS]}


# --- the tools ----------------------------------------------------------------


def today(state, *, tax_year: int | None = None) -> dict[str, Any]:
    """What needs the owner right now — aggregated, never a row dump."""
    from satc.actions import build_queue
    from satc.app.today_views import _obligations, working_tax_year

    as_of = date.today()
    requested = state.requested_items()
    received = state.received_documents()
    year = tax_year or working_tax_year(list(received) + list(requested), as_of)
    jobs = state.jobs()
    queue = build_queue(
        clients=[cid for cid, _ in state.client_choices()],
        requested=requested, received=received, obligations=_obligations(year),
        engaged_clients=[j.client_id for j in jobs],
        # THE SAME ARGUMENTS THE /today SCREEN PASSES, and they are not optional.
        # Every one of these defaults to empty, so leaving them out builds a
        # queue that is silently missing every money row: a model asked "what
        # needs doing?" answered with the paper chase alone and never mentioned
        # the unbilled year, the unissued draft, the overdue invoice or the
        # client sitting on a credit — while the owner's screen, two feet away,
        # listed all four. Principle 6 puts the model on the proposing side of
        # the engine; that only means anything if it is proposing against what
        # the owner is actually looking at.
        jobs=jobs, invoices=state.store.load_invoices(),
        payments=state.store.load_payments(),
        tax_year=year, today=as_of)

    names = _client_names(state)
    rows, note = _truncate([
        {"client": names.get(a.client_id, a.client_id), "what": a.title,
         "why": a.why, "urgency": a.urgency,
         "draft_ready": a.has_draft}
        for a in queue.actions])

    return {"summary": queue.summary_line(), "tax_year": year,
            "counts_by_kind": queue.counts(), "actions": rows,
            **({"note": note} if note else {})}


def client_brief(state, *, client: str) -> dict[str, Any]:
    """One client's situation, small enough to reason about."""
    resolved = _resolve_client(state, client)
    if isinstance(resolved, dict):
        return resolved
    client_id, name = resolved

    outstanding = [r.doc_type for r in state.requested_items()
                   if r.client_id == client_id and r.is_open]
    received = [d.doc_type for d in state.received_documents()
                if d.client_id == client_id]
    returns = [r for r in state.returns() if r.client_id == client_id]
    pc = state.public_client(client_id)

    out_rows, out_note = _truncate(outstanding)
    rec_rows, rec_note = _truncate(received)
    return {
        "client": name, "client_id": client_id,
        "entity_type": getattr(pc, "entity_type", "") if pc else "",
        "filing_status": getattr(pc, "filing_status", "") if pc else "",
        "outstanding": out_rows, "outstanding_count": len(outstanding),
        "received": rec_rows, "received_count": len(received),
        "returns": [f"{r.tax_year} {r.return_type} ({r.jurisdiction}) — "
                    f"{state.return_status(r.return_key)}"
                    for r in returns][:MAX_ROWS],
        **({"note": " · ".join(n for n in (out_note, rec_note) if n)}
           if (out_note or rec_note) else {}),
    }


def prior_year_check(state, *, client: str, tax_year: int | None = None) -> dict[str, Any]:
    """Documents in hand last year with no counterpart this year."""
    from satc.rollover import as_questions, omission_diff

    resolved = _resolve_client(state, client)
    if isinstance(resolved, dict):
        return resolved
    client_id, name = resolved

    from satc.app.today_views import working_tax_year
    received = state.received_documents()
    requested = state.requested_items()
    year = tax_year or working_tax_year(list(received) + list(requested), date.today())
    report = omission_diff(received, requested, client_id=client_id,
                           prior_year=year - 1, current_year=year)
    return {"client": name, "tax_year": year, "prior_year": year - 1,
            "summary": report.summary_line(),
            "questions": as_questions(report)[:MAX_ROWS],
            "still_outstanding": [k.doc_type for k in report.outstanding][:MAX_ROWS]}


def list_templates(state) -> dict[str, Any]:
    """Which communications can be drafted."""
    from satc.comms import library

    return {"templates": [{"key": t.key, "name": t.name, "for": t.description}
                          for t in library().templates]}


def draft(state, *, client: str, template: str) -> dict[str, Any]:
    """Render a draft for a client. PROPOSES text — it does not send anything.

    Returns the draft plus the slots that could not be filled, so the model can
    report honestly rather than papering over a gap.
    """
    from satc.app.comms_views import _context
    from satc.comms import library
    from satc.comms import render as render_draft

    lib = library()
    if template not in lib.keys():
        return {"error": f"no template named {template!r}",
                "next_step": "use one of these template keys",
                "templates": lib.keys()}
    resolved = _resolve_client(state, client)
    if isinstance(resolved, dict):
        return resolved
    client_id, name = resolved

    # template_key is NOT optional here. Without it the "letter that states
    # terms" branch never fires, and the engagement letter — the one a client
    # SIGNS — takes its agreed fee from an ISSUED INVOICE TOTAL. That is the
    # exact substitution the browser door guards against, and this door was
    # walking straight past it because it omitted one argument.
    notes: list[str] = []
    values = _context(client_id, None, template_key=template, notes=notes)
    rendered = render_draft(lib.template(template), values, library=lib)
    return {
        "client": name, "template": template, "subject": rendered.subject,
        "body": rendered.body,
        "unfilled": [lib.placeholder(n).label if lib.placeholder(n) else n
                     for n in rendered.unfilled],
        # Whatever the browser screen would have shown the owner, the model is
        # told too — a year mismatch or a refusal to derive the terms changes
        # what this draft is, and a model reporting "ready" over it would be
        # reporting something it was not shown.
        "notes": notes,
        "ready_to_send": rendered.is_complete,
        "reminder": ("This is a DRAFT. SATC never sends mail — the owner reads "
                     "it and sends it from their own mail client."),
    }


# --- the registry the model sees ---------------------------------------------

TOOLS: dict[str, Any] = {
    "satc_today": today,
    "satc_client_brief": client_brief,
    "satc_prior_year_check": prior_year_check,
    "satc_list_templates": list_templates,
    "satc_draft": draft,
}

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "satc_today",
        "description": ("What needs the owner's attention right now across the whole "
                        "practice: outstanding documents, unsigned e-file authorisations, "
                        "approaching deadlines, documents missing since last year, and "
                        "the money — work finished but never billed, drafts never issued, "
                        "invoices overdue, and clients who have overpaid."),
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "satc_client_brief",
        "description": ("One client's situation: what is outstanding, what has been "
                        "received, and their returns on file."),
        "parameters": {"type": "object", "properties": {
            "client": {"type": "string", "description": "Client name or id"}},
            "required": ["client"]}}},
    {"type": "function", "function": {
        "name": "satc_prior_year_check",
        "description": ("Documents this client sent last year that have not arrived "
                        "this year. Use this when asked what might be missing."),
        "parameters": {"type": "object", "properties": {
            "client": {"type": "string", "description": "Client name or id"}},
            "required": ["client"]}}},
    {"type": "function", "function": {
        "name": "satc_list_templates",
        "description": "The communication templates available to draft.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "satc_draft",
        "description": ("Render a draft email or letter for a client. This only "
                        "PREPARES text for the owner to review — it never sends."),
        "parameters": {"type": "object", "properties": {
            "client": {"type": "string", "description": "Client name or id"},
            "template": {"type": "string",
                         "description": "Template key, e.g. missing_items"}},
            "required": ["client", "template"]}}},
]


def dispatch(name: str, arguments: dict, *, state) -> dict[str, Any]:
    """Run a tool by name. An unknown name returns the real ones (rule 3)."""
    fn = TOOLS.get(name)
    if fn is None:
        return {"error": f"no tool named {name!r}",
                "next_step": "call one of these instead",
                "tools": sorted(TOOLS)}
    try:
        return fn(state, **(arguments or {}))
    except TypeError as exc:
        return {"error": f"wrong arguments for {name}: {exc}",
                "next_step": "check the tool's parameters and call it again"}
