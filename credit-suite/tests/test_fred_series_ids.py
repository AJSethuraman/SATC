"""The seeded FRED series ids are the ones FRED actually publishes (issue #181).

Eleven of the eighteen metro house-price series were dead on arrival: the seed
derived every id as ``ATNHPIUS<cbsa>Q``, and for the eleven largest metros FHFA
publishes at METROPOLITAN DIVISION level and no CBSA-level series exists. The
whole offline bar was green while a live pull returned 404 eleven times, because
nothing offline can tell a well-formed id from a published one.

These tests do not fix that -- only a live probe can, and one is not going to run
in CI. What they do is **lock in what the live probe found**, so the derivation
that caused the bug cannot come back silently. The table below is not inferred
from anything; each id was fetched from the FRED ``series`` endpoint on
2026-09-04 and confirmed present, quarterly and not discontinued.
"""
from __future__ import annotations

import re

from credit_suite.sources.fred import series_seed as S

#: cbsa -> the area code that actually appears in the published series id.
#: Verified live 2026-09-04. Where the two differ, FHFA publishes the metro as a
#: division; where they match, the CBSA-level series is the published one.
VERIFIED_AREA_FOR_CBSA = {
    "35620": "35614", "31080": "31084", "16980": "16984", "19100": "19124",
    "26420": "26420", "47900": "47894", "33100": "33124", "37980": "37964",
    "12060": "12060", "38060": "38060", "14460": "14454", "41860": "41884",
    "42660": "42644", "33460": "33460", "19820": "19804", "12420": "12420",
    "40140": "40140", "45300": "45300",
}

#: The eleven that 404'd on the live run. Kept explicit so the count is a fact in
#: the test rather than a subtraction the reader has to do.
PUBLISHED_AS_DIVISION = {
    c for c, a in VERIFIED_AREA_FOR_CBSA.items() if c != a
}

METRO_ID = re.compile(r"^ATNHPIUS(\d{5})Q$")


def metro_rows():
    return [r for r in S.all_series() if r["category"] == "hpi_metro"]


def test_the_seed_covers_exactly_the_verified_metros():
    """A metro added without a live check is a metro that 404s in production."""
    assert set(S.CBSAS) == set(VERIFIED_AREA_FOR_CBSA), (
        "the metro set changed; every new entry needs its series id confirmed "
        "against the FRED series endpoint before it ships -- deriving the id "
        "from the CBSA code is what issue #181 was"
    )


def test_every_metro_series_id_uses_the_verified_area_code():
    """The id carries the AREA code, which is not always the CBSA code."""
    for row in metro_rows():
        match = METRO_ID.match(row["series_id"])
        assert match, "%s is not a well-formed FHFA metro id" % row["series_id"]
        cbsa = row["geo_segment"].split(":", 1)[1]
        assert match.group(1) == VERIFIED_AREA_FOR_CBSA[cbsa], (
            "%s: series id says area %s, but FRED publishes this metro as %s"
            % (cbsa, match.group(1), VERIFIED_AREA_FOR_CBSA[cbsa])
        )


def test_eleven_metros_are_published_as_divisions():
    """Guards the count itself. If a future edit quietly re-derives the ids from
    the CBSA table, every one of them matches its CBSA again and this drops to
    zero -- which is precisely the shipped bug, so it gets its own assertion."""
    assert len(PUBLISHED_AS_DIVISION) == 11
    actual = {r["geo_segment"].split(":", 1)[1] for r in metro_rows()
              if METRO_ID.match(r["series_id"]).group(1)
              != r["geo_segment"].split(":", 1)[1]}
    assert actual == PUBLISHED_AS_DIVISION


def test_the_entity_key_stays_the_metro_not_the_division():
    """The division is where the numbers come from; the metro is what is being
    watched. Keying on the division would silently renumber the watchlist."""
    keys = {r["geo_segment"] for r in metro_rows()}
    assert keys == {"cbsa:%s" % c for c in VERIFIED_AREA_FOR_CBSA}


def test_a_division_series_says_so_in_its_notes():
    """A reader looking at 'New York' numbers that are really the New York-Jersey
    City-White Plains division deserves to be told, in the workbook."""
    for row in metro_rows():
        cbsa = row["geo_segment"].split(":", 1)[1]
        if cbsa in PUBLISHED_AS_DIVISION:
            assert "DIVISION" in row["notes"].upper(), (
                "%s draws on a division but its notes do not say so" % cbsa
            )


def test_the_extension_table_offers_the_same_ids_it_would_pull():
    """`cbsa_extension_rows` is what a user copies into _config to add a metro.
    If it hands out CBSA-derived ids, the user pastes in a 404."""
    for entry in S.cbsa_extension_rows():
        expected = "ATNHPIUS%sQ" % VERIFIED_AREA_FOR_CBSA[entry["cbsa"]]
        assert entry["series_id"] == expected
