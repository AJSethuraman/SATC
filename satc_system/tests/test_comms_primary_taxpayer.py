"""The invoice email names the primary taxpayer from the record, not by hand.

The firm, 13 Oct 2026, on the PDF-password line: "everything here needs to be
made via the compilation of our data - so [the client]'s name must be the
primary tax payer's".
"""
import re

from satc.comms import load_library
from satc.comms.context import build_context


class _Person:
    entity_type = "INDIVIDUAL"


class _Business:
    entity_type = "SCORP"


def test_the_first_person_on_the_return_is_named():
    values = build_context(client_name="Pat Example Doe", public_client=_Person())
    assert values["primary_first_name"] == "Pat"


def test_a_business_is_given_no_first_name():
    values = build_context(client_name="Acme Widgets LLC", public_client=_Business())
    assert "primary_first_name" not in values


def test_the_invoice_email_uses_it_and_types_no_name():
    lib = load_library()
    body = lib.body("invoice_cover") if hasattr(lib, "body") else open(
        "configs/comms/invoice_cover.txt", encoding="utf-8").read()
    assert "{primary_first_name}'s last name" in body
    line = next(l for l in body.splitlines() if "last name" in l)
    assert re.search(r"[A-Z][a-z]+'s last name", line) is None   # no name typed in
