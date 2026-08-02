"""Client-comms screen (Flask) tests — picking, prefilling, and not sending.

The pure merging rules are guarded in ``tests/test_comms.py``; this file guards
the thin view: that the screen lists the library, prefills a real client from
state, surfaces what it couldn't fill, and never acquires a send path.
"""

from __future__ import annotations

import pytest

from satc.app.server import create_app
from satc.app.state import STATE
from satc.comms import library


@pytest.fixture()
def client():
    return create_app().test_client()


@pytest.fixture(scope="module")
def demo_client_id():
    """A client that actually exists in the store (the seeded sample practice)."""
    choices = STATE.client_choices()
    assert choices, "the seeded store should hold at least one client"
    return choices[0][0]


def test_screen_lists_every_template(client):
    resp = client.get("/comms")
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    for tpl in library().templates:
        assert tpl.name in body, f"{tpl.key} is missing from the screen"


def test_nav_carries_a_comms_entry(client):
    assert b"Client comms" in client.get("/").data


def test_screen_offers_the_practice_clients(client, demo_client_id):
    assert demo_client_id.encode() in client.get("/comms").data


def test_no_draft_until_a_client_and_template_are_chosen(client):
    """Template alone must not render a draft addressed to nobody."""
    resp = client.get("/comms", query_string={"template": "document_request"})
    assert resp.status_code == 200
    assert b"Copy the draft" not in resp.data


def test_drafting_for_a_real_client_prefills_from_state(client, demo_client_id):
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "document_request"})
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "Copy the draft" in body
    assert STATE.name(demo_client_id) in body
    assert "Prefilled from their record" in body


def test_the_interview_invite_now_arrives_finished(client, demo_client_id):
    """It used to hand back three blanks — meeting place, times, and nothing
    else to do. Standing firm wording comes from config and the judgement
    wording is drafted, so the owner edits rather than composes."""
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "interview_invite"})
    body = resp.data.decode("utf-8")
    assert "a phone call or our office" in body      # standing firm wording
    assert "Copy the draft" in body


def test_a_genuine_unknown_fact_is_still_marked(client, demo_client_id):
    """The guarantee that did NOT change: a fact nothing supplies stays
    visibly blank. An invoice number is not something a model may invent."""
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "invoice_cover"})
    body = resp.data.decode("utf-8")
    assert "fill in ]]" in body
    assert "Invoice number" in body


def test_preparer_typed_values_are_merged_in(client, demo_client_id):
    resp = client.post("/comms", data={
        "client": demo_client_id, "template": "interview_invite",
        "fill_proposed_times": "Tuesday 10am or Thursday 2pm",
        "fill_meeting_place": "our office",
    })
    body = resp.data.decode("utf-8")
    assert "Tuesday 10am or Thursday 2pm" in body
    assert "[[ Proposed meeting times: fill in ]]" not in body


def test_a_letter_offers_no_mail_buttons(client, demo_client_id):
    """A printed cover letter isn't an email — don't pretend it is."""
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "cover_letter"})
    body = resp.data.decode("utf-8")
    assert "Copy the draft" in body
    assert "Open in your mail app" not in body


def test_an_unknown_template_does_not_500(client, demo_client_id):
    resp = client.get("/comms", query_string={
        "client": demo_client_id, "template": "no_such_template"})
    assert resp.status_code == 200
    assert b"Copy the draft" not in resp.data


def test_client_shortcut_redirects_into_the_screen(client, demo_client_id):
    resp = client.get(f"/clients/{demo_client_id}/comms")
    assert resp.status_code == 302
    assert "/comms" in resp.headers["Location"]
    assert demo_client_id in resp.headers["Location"]


def test_outlook_route_hands_back_text_it_did_not_send(client, demo_client_id):
    """On a box without Outlook COM this must degrade to copyable text, not fail."""
    resp = client.post("/comms/outlook", data={
        "client": demo_client_id, "template": "document_request"})
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "Open it yourself" in body or "Sent to Outlook" in body


def test_outlook_route_guards_a_missing_selection(client):
    resp = client.post("/comms/outlook", data={"client": "", "template": ""})
    assert resp.status_code == 302


def test_the_comms_area_has_no_send_path():
    """The hard rule: sending stays a human act in the mail client (BACKLOG §6).

    Parsed rather than grepped, so the modules stay free to *say* "no SMTP" in
    their docstrings while this proves they never import or call one.
    """
    import ast
    from pathlib import Path

    import satc.app.comms_views as views
    import satc.comms as comms

    banned_modules = {"smtplib", "ssl"}
    banned_calls = {"sendmail", "send_message", "starttls", "SMTP", "SMTP_SSL"}

    roots = [Path(comms.__file__).parent, Path(views.__file__)]
    files = [p for root in roots
             for p in ([root] if root.is_file() else sorted(root.glob("*.py")))]
    assert files, "expected to find the comms modules on disk"

    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in banned_modules, path.name
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in banned_modules, path.name
            elif isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, "attr", None) or getattr(func, "id", None)
                assert name not in banned_calls, f"{path.name} calls {name}"
