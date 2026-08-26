"""The interview, and the engagement it creates.

`interview.yaml` described thirty questions and nothing asked them, so a record
was filled by hand and the pipeline went unused. These tests cover the engine
that asks them and the store that keeps what comes out.

Two things get the most attention, because both fail silently:

* **`showIf`.** These conditions decide whether a spouse signs and whether a
  predecessor is contacted. A condition that mis-evaluates produces a document
  that is wrong rather than one that is missing.
* **Composition.** Several answers make one field. `FederalReturns` is the form
  plus its schedules, and an empty list is the literal "None" — with foreign
  reporting in scope, blank and "None" are different statements.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import engagements  # noqa: E402
import interview as iv  # noqa: E402

SAMPLES = ROOT / "samples"


@pytest.fixture(scope="module")
def schema():
    return iv.load_schema()


# ── showIf ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cond,answers,expected", [
    ("joint_return == 'yes'", {"joint_return": "yes"}, True),
    ("joint_return == 'yes'", {"joint_return": "no"}, False),
    ("joint_return == 'yes'", {}, False),
    ("federal_form != '1040'", {"federal_form": "1065"}, True),
    ("'E1' in federal_schedules", {"federal_schedules": ["A", "E1"]}, True),
    ("'E1' in federal_schedules", {"federal_schedules": ["A"]}, False),
    ("'E1' in federal_schedules", {}, False),
])
def test_showif_evaluates(cond, answers, expected):
    assert iv.visible({"showIf": cond}, answers) is expected


def test_an_unparseable_condition_raises_rather_than_guessing():
    """A condition this engine cannot read must not quietly become False.

    False means the question is never asked, which means a spouse never signs.
    """
    with pytest.raises(iv.InterviewError):
        iv.visible({"showIf": "count_k1s > 3"}, {"count_k1s": 5})


def test_every_showif_in_the_real_schema_is_parseable(schema):
    """The grammar must cover the schema as it actually is, today."""
    for _, q in iv.all_questions(schema):
        if q.get("showIf"):
            iv.visible(q, {})       # raises if the grammar cannot read it


# ── the flow ──────────────────────────────────────────────────────────────

def test_a_hidden_question_is_not_asked():
    session = iv.Interview()
    session.answer("joint_return", "no")
    assert "spouse_name" not in {q["id"] for _, q in session.pending()}


def test_changing_an_answer_retracts_what_it_hid():
    """Answer joint, name the spouse, then change to single.

    The spouse name must go. Left behind, it reaches a document that no longer
    has a signature block for it.
    """
    session = iv.Interview()
    session.answer("federal_form", "1040")
    session.answer("joint_return", "yes")
    session.answer("spouse_name", "Maria Reyes")
    assert session.answers["spouse_name"] == "Maria Reyes"
    session.answer("joint_return", "no")
    assert "spouse_name" not in session.answers


def test_changing_the_return_type_retracts_the_whole_individual_half():
    """The case the entity branch exists for.

    Answer as an individual, then discover it is an S corporation. Filing
    status and the spouse must go -- an entity has neither, and a spouse name
    left behind would reach a letter with no signature block for it.
    """
    session = iv.Interview()
    session.answer("federal_form", "1040")
    session.answer("joint_return", "yes")
    session.answer("spouse_name", "Maria Reyes")

    session.answer("federal_form", "1120S")
    for gone in ("joint_return", "spouse_name"):
        assert gone not in session.answers, f"{gone} survived the change to an entity"


def test_changing_back_retracts_the_entity_half():
    """And the mirror, which is the half a one-way fix would miss."""
    session = iv.Interview()
    session.answer("federal_form", "1120S")
    session.answer("entity_structure", "llc")
    session.answer("signer_name", "Daniel Reyes")

    session.answer("federal_form", "1040")
    for gone in ("entity_structure", "signer_name"):
        assert gone not in session.answers, f"{gone} survived the change to a 1040"


def test_a_c_corporation_is_not_asked_about_k1s():
    """It issues none. Asking is asking about something that does not exist."""
    session = iv.Interview()
    session.answer("federal_form", "1120")
    pending = {q["id"] for _, q in session.pending()}
    assert "k1_target" not in pending and "count_owners" not in pending
    assert "signer_name" in pending, "but it still signs through a person"


def test_a_required_question_will_not_take_a_blank():
    session = iv.Interview()
    with pytest.raises(iv.InterviewError):
        session.answer("client_full_name", "")


def test_prefill_offers_the_website_claim_without_answering():
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    session = iv.Interview(lead=lead)
    q = session.question("client_email")
    assert iv.prefill_for(q, lead) == "dreyes@example.com"
    assert "client_email" not in session.answers, (
        "prefill must offer a claim, never answer for you -- the schema is "
        "explicit that every prefilled question is still asked"
    )


def test_prefill_is_silent_when_the_website_did_not_ask():
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    session = iv.Interview(lead=lead)
    assert iv.prefill_for(session.question("client_zip"), lead) is None


def test_one_lead_value_splits_across_two_questions():
    """The form collects "Solon, OH"; the address block needs two lines.

    Both questions used to be offered the whole string, which was invisible
    while every prefill had to be retyped and would have printed
    "Solon, OH, Solon, OH 44139" the moment enter began accepting one.
    """
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    session = iv.Interview(lead=lead)
    assert iv.prefill_for(session.question("client_city"), lead) == "Solon"
    assert iv.prefill_for(session.question("client_state"), lead) == "OH"


def test_a_split_with_nothing_in_that_position_makes_no_claim():
    q = {"prefill": "contact.location", "prefill_index": 1}
    assert iv.prefill_for(q, {"contact": {"location": "Solon"}}) is None


def test_the_websites_vocabulary_is_translated_not_carried_through():
    """"rental" is not a schedule. "E1" is."""
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    session = iv.Interview(lead=lead)
    got = iv.prefill_for(session.question("federal_schedules"), lead)
    assert set(got) == {"E1", "E2"}


def test_a_lead_value_with_no_translation_is_dropped():
    """A plain W-2 is a real thing to tell us and is not a schedule."""
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    assert "w2" in lead["individual_complexity"]
    session = iv.Interview(lead=lead)
    assert "w2" not in iv.prefill_for(session.question("federal_schedules"), lead)


def test_one_lead_answer_can_imply_two_schedules():
    q = {"prefill": "x", "prefill_map": {"sole_prop": ["C", "SE"]}}
    assert iv.prefill_for(q, {"x": ["sole_prop"]}) == ["C", "SE"]


# ── a claim you can accept must be a legal answer ─────────────────────────

def test_a_claim_the_question_would_reject_is_not_acceptable(schema):
    """Enter accepts a prefill, so an invalid one is a keystroke from a
    document. It is still shown -- it is what the client told us -- but it
    cannot be taken as the answer."""
    q = {"options": [{"value": "yes"}, {"value": "partial"}, {"value": "no"}]}
    assert not iv.prefill_is_answerable(q, "unsure")
    assert iv.prefill_is_answerable(q, "yes")


def test_a_free_text_claim_is_always_acceptable():
    assert iv.prefill_is_answerable({}, "anything")


def test_an_empty_claim_is_not_a_claim():
    for empty in (None, "", []):
        assert not iv.prefill_is_answerable({}, empty)


def test_a_multi_claim_is_acceptable_only_if_every_value_is_legal():
    q = {"options": [{"value": "A"}, {"value": "B"}]}
    assert iv.prefill_is_answerable(q, ["A", "B"])
    assert not iv.prefill_is_answerable(q, ["A", "w2"])


def test_every_prefill_in_the_real_schema_is_either_legal_or_flagged(schema):
    """The guard that makes the whole mechanism safe.

    Any prefill the sample lead supplies must either be a legal answer, or be
    reported as unacceptable. Nothing may be silently offered for acceptance
    that the question itself would reject.
    """
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    for section in schema["sections"]:
        for q in section["questions"]:
            if not q.get("prefill"):
                continue
            value = iv.prefill_for(q, lead)
            if iv.prefill_is_answerable(q, value):
                opts = [o["value"] for o in q.get("options", [])]
                if opts:
                    vals = value if isinstance(value, list) else [value]
                    assert all(v in opts for v in vals), (
                        f"{q['id']} offers {value!r} for acceptance, but the "
                        f"question only takes {opts}"
                    )


def test_the_scope_boundary_is_never_prefilled(schema):
    """`states` is what the firm agreed to file. It once prefilled from the
    website's complexity checklist, which would have offered 'w2' as a state."""
    for section in schema["sections"]:
        for q in section["questions"]:
            if q["id"] == "states":
                assert "prefill" not in q, (
                    "the website never asks which states; a wrong claim here "
                    "is worse than no claim"
                )


# ── composition ───────────────────────────────────────────────────────────

def test_federal_returns_is_the_form_plus_its_schedules():
    out = iv.compose({"federal_form": "1040", "federal_schedules": ["A", "C", "SE"]})
    assert out["FederalReturns"] == "Form 1040 with Schedules A, C, and SE"


def test_schedule_e_is_named_once_even_from_two_answers():
    """E1 (rentals) and E2 (K-1s) are both Schedule E. Naming it twice on a
    client's engagement letter reads as a mistake."""
    out = iv.compose({"federal_form": "1040", "federal_schedules": ["E1", "E2"]})
    assert out["FederalReturns"] == "Form 1040 with Schedule E"


def test_a_form_with_no_schedules_says_just_the_form():
    assert iv.compose({"federal_form": "1065"})["FederalReturns"] == "Form 1065"


def test_an_empty_locality_list_is_the_literal_none():
    """Blank and "None" are different statements, and the field docs say so."""
    out = iv.compose({"localities": [], "additional_forms": []})
    assert out["LocalReturns"] == "None"
    assert out["AdditionalForms"] == "None"


def test_yes_no_answers_become_booleans_for_the_flags():
    out = iv.compose({"joint_return": "yes", "prior_firm": "no"})
    assert out["JointReturn"] is True and out["PriorFirm"] is False


def test_period_label_is_derived_from_the_tax_year():
    assert iv.compose({"tax_year": "2026"})["PeriodLabel"] == "2026 tax year"


def test_internal_answers_never_become_merge_fields():
    out = iv.compose({"notes": "difficult client", "decision": "yes",
                      "red_flags": ["missing_records"], "unfiled_years": "2023"})
    assert out == {}, f"internal answers leaked into the record: {out}"


def test_billable_counts_are_kept_but_are_not_fields():
    answers = {"count_states": 2, "count_k1s": 3, "count_brokerages": 1}
    assert iv.compose(answers) == {}
    counts = iv.billable_counts(answers)
    assert counts["LineItems"]["count_states"] == 2


# ── the sample interview fills the opening package ────────────────────────

def test_the_sample_answers_supply_every_field_the_interview_owns():
    answers = json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))
    session = iv.Interview()
    for _, q in list(iv.all_questions(session.schema)):
        if q["id"] in answers:
            session.answer(q["id"], answers[q["id"]])
    assert session.missing_required() == [], (
        "the sample interview leaves a required question unanswered"
    )


# ── engagements ───────────────────────────────────────────────────────────

def test_refs_are_allocated_sequentially(tmp_path):
    assert engagements.next_ref(2026, tmp_path) == "2026-0001"
    engagements.create({"ClientFullName": "A"}, year=2026, store=tmp_path)
    assert engagements.next_ref(2026, tmp_path) == "2026-0002"


def test_a_ref_is_never_reused(tmp_path):
    engagements.create({"ClientFullName": "A"}, ref="2026-0001", store=tmp_path)
    with pytest.raises(engagements.EngagementError):
        engagements.create({"ClientFullName": "B"}, ref="2026-0001", store=tmp_path)


def test_a_malformed_ref_is_refused(tmp_path):
    """The ref is byte-compared across every document, so it is validated at
    the door rather than discovered on a client's letter."""
    for bad in ("2026-1", "26-0001", "2026_0001", "../etc"):
        with pytest.raises(engagements.EngagementError):
            engagements.create({}, ref=bad, store=tmp_path)


def test_the_created_record_carries_its_own_ref(tmp_path):
    ref, _ = engagements.create({"ClientFullName": "A"}, year=2026, store=tmp_path)
    assert engagements.load(ref, tmp_path)["EngagementRef"] == ref


def test_years_do_not_collide(tmp_path):
    engagements.create({}, ref="2026-0009", store=tmp_path)
    assert engagements.next_ref(2027, tmp_path) == "2027-0001"


# ── interview -> engagement -> render, the whole chain ────────────────────

def _run_interview(tmp_path, answers_file="interview-answers.json", extra=()):
    return cli.main(["interview", "--answers", str(SAMPLES / answers_file),
                     "--lead", str(SAMPLES / "website-lead.json"),
                     "--store", str(tmp_path), *extra])


def test_the_interview_creates_a_renderable_engagement(tmp_path):
    assert _run_interview(tmp_path) == 0
    rows = engagements.listing(tmp_path)
    assert len(rows) == 1
    record = engagements.load(rows[0]["ref"], tmp_path)

    assert record["EngagementRef"] == rows[0]["ref"]
    assert record["FederalReturns"].startswith("Form 1040 with Schedules")
    assert record["_return_type"] == "individual"
    assert record["_season"] == "2026"

    # the internal answers are kept beside it, not merged into it
    assert "notes" not in record and "red_flags" not in record
    kept = json.loads((tmp_path / rows[0]["ref"] / "interview.json").read_text())
    assert kept["decision"] == "yes" and "notes" in kept


def test_the_engagement_renders_in_draft(tmp_path):
    """Real mode is still gated on the firm's open decisions; draft proves the
    chain from a question asked to a document produced."""
    _run_interview(tmp_path)
    ref = engagements.listing(tmp_path)[0]["ref"]
    rc = cli.main(["render", "--engagement", ref, "--store", str(tmp_path),
                   "--docs", "tax-letter", "onboarding-letter", "--draft",
                   "--out", str(tmp_path / "out"), "--no-pdf"])
    assert rc == 0
    written = {p.name: p.read_text(encoding="utf-8")
               for p in (tmp_path / "out").glob("*.html")}
    assert len(written) == 2

    # Each document is checked for what IT carries. PriorFirmName is registered
    # to the onboarding letter alone, so asserting it against the engagement
    # letter tests the test, not the pipeline.
    letter = next(v for k, v in written.items() if "Engagement Letter" in k)
    onboarding = next(v for k, v in written.items() if "Onboarding" in k)

    assert "Mr. and Mrs. Daniel Reyes" in letter
    assert "Form 1040 with Schedules" in letter, "the composed scope is missing"
    assert "Halloran &amp; Reeve CPAs" in onboarding, (
        "the prior-firm answer did not reach the letter that asks for it"
    )
    assert "Maria Reyes" in letter, "the joint-return branch did not survive"


def test_a_hard_no_refuses_to_create_an_engagement(tmp_path):
    """The schema marks two options HARD NO. Flagging one and creating the
    engagement anyway makes the flag decorative."""
    answers = json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))
    answers["red_flags"] = ["assurance_needed"]
    path = tmp_path / "answers.json"
    path.write_text(json.dumps(answers), encoding="utf-8")

    rc = cli.main(["interview", "--answers", str(path), "--store", str(tmp_path)])
    assert rc == 1
    assert engagements.listing(tmp_path) == [], "a HARD NO still created an engagement"


def test_a_hard_no_can_be_overridden_deliberately(tmp_path):
    answers = json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))
    answers["red_flags"] = ["assurance_needed"]
    path = tmp_path / "answers.json"
    path.write_text(json.dumps(answers), encoding="utf-8")

    rc = cli.main(["interview", "--answers", str(path), "--store", str(tmp_path),
                   "--override-hard-no"])
    assert rc == 0 and len(engagements.listing(tmp_path)) == 1


def test_declining_creates_nothing(tmp_path):
    answers = json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))
    answers["decision"] = "no"
    path = tmp_path / "answers.json"
    path.write_text(json.dumps(answers), encoding="utf-8")

    assert cli.main(["interview", "--answers", str(path), "--store", str(tmp_path)]) == 0
    assert engagements.listing(tmp_path) == []


def test_a_missing_required_answer_stops_the_replay(tmp_path):
    answers = json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))
    del answers["client_full_name"]
    path = tmp_path / "answers.json"
    path.write_text(json.dumps(answers), encoding="utf-8")

    with pytest.raises(SystemExit):
        cli.main(["interview", "--answers", str(path), "--store", str(tmp_path)])


def test_the_interview_asks_whether_a_1040_is_an_amendment():
    """The half of the amended-return decision that `pricing.line_items` does
    NOT do, on purpose.

    `line_items` defaults an absent `return_basis` to `original`, because
    refusing would break every engagement recorded before the question
    existed. That default is only safe because a real engagement cannot get
    past the interview without answering — a defaulted answer would quote the
    $200 package for a job the firm prices at $250, silently, on the one
    question nobody would think to check.

    Every form since 26 August 2026 (T-20): the amendment became a $50 adder
    on top of whatever the return is, so an amended 1120-S prices itself.
    """
    schema = yaml.safe_load(
        (ROOT / "registry" / "interview.yaml").read_text(encoding="utf-8"))
    questions = [q for sec in schema["sections"] for q in sec["questions"]]
    basis = [q for q in questions if q["id"] == "return_basis"]
    assert basis, "nothing asks whether this is an original return or an amendment"
    q = basis[0]
    assert q.get("required") is True, "an unanswered basis prices as an original"
    assert not q.get("showIf"), \
        "every form can be amended now, so the question is not 1040-only"
    values = {o["value"] for o in q["options"]}
    assert {"original", "amended"} <= values
