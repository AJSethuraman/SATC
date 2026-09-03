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
from datetime import date
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import engagements  # noqa: E402
import deadlines as taxcal  # noqa: E402
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


def test_the_website_answer_reaches_the_interview_at_all():
    """It could not, until 26 August 2026.

    `federal_schedules` used to prefill through a `prefill_map` whose keys had
    drifted from the intake form: it expected `rental`, `self_employed`,
    `sole_prop`, `brokerage` and `itemize`, and the site has never sent any of
    the five. A prospect ticked "Rental property" and the interview offered
    nothing. Only `k1` and `investments` ever matched.

    The fix was to stop translating. `return_features` asks the same question
    the website asks, in the same words, with the same option values -- so
    there is no vocabulary to keep in step and no map to go stale.
    """
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    session = iv.Interview(lead=lead)
    got = iv.prefill_for(session.question("return_features"), lead)
    assert got, "the website's answer reached the interview as nothing"
    assert set(got) <= set(lead["individual_complexity"]), \
        "a value was invented rather than carried"


def test_the_sample_lead_only_says_things_the_website_can_say():
    """It said "rental". The site sends "rentals".

    So the fixture demonstrated the exact bug it was meant to exercise: a
    value the interview could never hear. A sample that cannot happen proves
    nothing about the leads that do.
    """
    import re
    site = (Path(__file__).resolve().parents[2] / "website" / "intake-config.js"
            ).read_text(encoding="utf-8")
    i = site.index("id: 'individual_complexity'")
    sends = set(re.findall(r"value: '([^']+)'", site[i:site.index("/* ── 4", i)]))

    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    stray = [v for v in lead["individual_complexity"] if v not in sends]
    assert not stray, f"the sample lead says things the intake form cannot: {stray}"


def test_a_lead_value_that_means_no_schedule_is_dropped():
    """A plain W-2 is a real thing to tell us and implies no schedule."""
    lead = json.loads((SAMPLES / "website-lead.json").read_text(encoding="utf-8"))
    assert "w2" in lead["individual_complexity"]
    session = iv.Interview(lead=lead)
    assert "w2" not in iv.prefill_for(session.question("return_features"), lead)


def test_the_interview_and_the_website_share_one_vocabulary():
    """The guard that stops the five dead keys coming back.

    Every option `return_features` offers must be an option the intake form
    actually sends, or a prospect can tick something on the site that the
    interview quietly cannot hear.
    """
    import re
    site = (Path(__file__).resolve().parents[2] / "website" / "intake-config.js"
            ).read_text(encoding="utf-8")
    i = site.index("id: 'individual_complexity'")
    block = site[i:site.index("/* ── 4", i)]
    sends = set(re.findall(r"value: '([^']+)'", block))

    q = iv.Interview().question("return_features")
    asks = {o["value"] for o in q["options"]}

    # THE DIRECTION THAT MATTERS is site -> interview. Every value the site can
    # send must be one the interview either offers or deliberately drops; a
    # value it sends that the interview has never heard of is the failure this
    # question was rebuilt to stop.
    #
    # The reverse is NOT a failure. `farm` and `itemizing` are asked on the
    # call and not on the site, because a preparer learns things a prospect was
    # never asked. That gap is recorded in docs/site-open-questions.md for the
    # site rather than forced closed from here.
    unheard = {v for v in sends if v in asks} - asks
    assert not unheard
    assert asks & sends, "the two share no vocabulary at all, so prefill is dead"
    for v in sorted(sends):
        assert v in asks or v not in {"self_employment", "business_owner",
                                      "rentals", "k1", "investments"}, (
            f"the website sends {v!r}, which means a schedule, and the "
            f"interview does not offer it"
        )


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

def test_a_hard_no_label_does_not_repeat_the_badge():
    """Both front doors draw a HARD NO badge from `hard_no: true`.

    Two option labels also ended with "— HARD NO", so the screen read
    "Needs assurance work — HARD NO **HARD NO**". Found 26 August 2026 by
    screenshotting the real page rather than reading the YAML.
    """
    import interview as iv
    for _, q in iv.all_questions(iv.load_schema()):
        for o in q.get("options") or []:
            if o.get("hard_no"):
                assert "HARD NO" not in o["label"].upper(), (
                    f"{q['id']}/{o['value']}: the label repeats the badge"
                )


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


def test_a_blank_number_answer_is_blank_to_the_showIf_grammar():
    """`showIf: "count_sorting != ''"` reads as "only ask this if they answered
    the one above", and it never once said no. `coerce` turns a blank number
    into None — a number field cannot hold "" — and `None != ''` is True. So
    "How much for the sorting? ($175 minimum)" was put to the preparer in every
    sitting on every return type, including a one-W-2 client who has sent
    nothing. Measured in all four paths on 2 September 2026.

    Pinned on the grammar rather than on that one question, because the next
    `!= ''` written into the registry would have had the same bug."""
    q = {"id": "x", "showIf": "count_sorting != ''"}
    for blank in ({}, {"count_sorting": None}, {"count_sorting": ""}):
        assert not iv.visible(q, blank), (
            f"a blank answer read as answered: {blank}")
    assert iv.visible(q, {"count_sorting": 1})
    assert iv.visible(q, {"count_sorting": 0}), (
        "a typed 0 is not blank — somebody entered it")

    inverse = {"id": "y", "showIf": "count_sorting == ''"}
    assert iv.visible(inverse, {}), "the == side must agree with the != side"
    assert not iv.visible(inverse, {"count_sorting": 1})


def test_the_sorting_fee_question_is_not_asked_of_every_client():
    """The live path, not the grammar: drive the interview the way both front
    doors drive it — coerce, then answer — and the sorting-fee question must
    not appear for a client who was not said to need sorting."""
    import json
    answers = {"federal_form": "1040", "tax_year": "2026",
               "client_full_name": "Marcus Ellwood", "filing_status": "single",
               "joint_return": "no", "return_basis": "original"}
    session = iv.Interview()
    asked = []
    for _ in range(200):
        nxt = session.next_question()
        if nxt is None:
            break
        _, q = nxt
        asked.append(q["id"])
        raw = answers.get(q["id"], [] if q.get("type") == "multi" else "")
        try:
            session.answer(q["id"], session.coerce(q, raw))
        except Exception:
            session.answers[q["id"]] = iv.coerce(q, raw)
    assert "count_sorting" in asked, "the question this one hangs off was not asked"
    assert "sorting_amount" not in asked, (
        "the sorting FEE was put to a preparer who said nothing needs sorting")


def test_a_translated_prefill_says_what_the_client_actually_asked_about():
    """Both front doors show a prefill as "the website said <value>", and for a
    mapped question that sentence was not true. `services: [tax_planning]` is
    translated to "1040" by `prefill_map`, so a preparer was told the website
    said "1040" — which the client never said.

    The firm on what a lead is for: "we use the lead as a starting point, so we
    would always ask whether we are doing a 1040. we would confirm what they put
    there. they didn't necessarily know what they needed." Confirming what they
    put there requires being shown what they put there."""
    schema = iv.load_schema()
    q = next(q for _, q in iv.all_questions(schema) if q["id"] == "federal_form")

    planning = {"services": ["tax_planning"]}
    assert iv.prefill_for(q, planning) == "1040", "the map itself changed"
    assert iv.prefill_source(q, planning) == "tax planning", (
        "the preparer is told the client said 1040 and not what they did say")

    # Nothing to add when the map did not change the words, and nothing to add
    # for a question with no map at all — the note is for translation only.
    assert iv.prefill_source(q, {"services": ["business_tax"]}) == "", (
        "a dropped prefill has no claim to explain")
    plain = next(q for _, q in iv.all_questions(schema)
                 if q.get("prefill") and not q.get("prefill_map"))
    assert iv.prefill_source(plain, {"services": ["individual_tax"]}) == ""
    assert iv.prefill_source(q, None) == ""


def _drive(answers, tick=None):
    """A whole sitting, the way both front doors run one: coerce, then answer."""
    session = iv.Interview()
    asked = []
    for _ in range(300):
        nxt = session.next_question()
        if nxt is None:
            break
        _, q = nxt
        asked.append(q["id"])
        raw = (tick if tick is not None and q["id"] == "red_flags"
               else answers.get(q["id"], [] if q.get("type") == "multi" else ""))
        try:
            session.answer(q["id"], session.coerce(q, raw))
        except Exception:
            session.answers[q["id"]] = iv.coerce(q, raw)
    return asked, session


_A_1040 = {"federal_form": "1040", "tax_year": "2026", "return_basis": "original",
           "client_full_name": "Marcus Ellwood", "joint_return": "no",
           "filing_status": "single"}


def test_a_hard_no_ends_the_sitting_where_it_is_ticked():
    """It used to paint a red HARD NO badge and ask the next question anyway —
    the block was acted on only once the questions ran out. Measured before the
    change: two more questions after the tick.

    The firm does not take assurance work. Continuing to interview somebody about
    their dependents after they have said they need it is not politeness, it is
    the software knowing something the person running the call has to act on and
    saying nothing."""
    asked, session = _drive(_A_1040, tick=["assurance_needed"])
    assert session.hard_no() == ["Needs assurance work"]
    assert asked[-1] == "red_flags", (
        f"the sitting carried on past the refusal: {asked[asked.index('red_flags') + 1:]}")


def test_the_question_that_can_end_it_is_asked_near_the_start():
    """It was question 30 of 32, so a client the firm does not take answered 29
    first. The firm, asked directly, chose to move it. This pins the intent
    rather than the exact index: a later question can be added above it only
    deliberately."""
    asked, _ = _drive(_A_1040)
    assert "red_flags" in asked
    position = asked.index("red_flags") + 1
    assert position <= 6, (
        f"the only refusal gate is question {position}; it was moved to the "
        f"front on purpose and something has pushed it back down")


def test_a_clean_sitting_still_reaches_the_end():
    """The early exit must fire on a HARD NO and on nothing else — an interview
    that ends early for everybody is worse than one that ends late."""
    asked, session = _drive(_A_1040, tick=[])
    assert session.hard_no() == []
    assert "decision" in asked, "a clean sitting stopped before the decision"
    assert len(asked) > 20


# ── does a form eliminate work, or only claim to? ──────────────────────────

def test_no_condition_in_any_form_is_one_that_can_never_say_no():
    """The firm's tenet, 2 September 2026: "a tenet of any checklist or
    interview-like form we make ... should be it directionally eliminates work
    where possible. for instance, if something is not applicable why would you
    want to answer questions around it."

    A `showIf` is a CLAIM that a question can be skipped. This is the thing that
    compares the claim to what happens — `sorting_amount` carried one, read
    correctly, and never once said no."""
    import elimination
    sweeps = elimination.sweep_all()
    dead = [d for s in sweeps.values() for d in s.dead]
    assert not dead, "\n".join(d.line() for d in dead)

    # S2: the denominator is half the report. A sweep that examined nothing
    # would pass the assertion above and mean nothing.
    for name, s in sweeps.items():
        assert not s.examined_nothing, f"{name} examined no questions"
        assert s.conditional > 0, f"{name} eliminates nothing at all"


def test_the_elimination_sweep_would_notice_the_bug_it_exists_for():
    """Check the checker. The first version of this sweep offered "" as a
    candidate answer for every question, found that `count_sorting = ""` hides
    `sorting_amount`, and called the condition alive — while the live bug was
    that a blank number coerces to None and the question was asked of everybody.

    A checker that invents values the system cannot produce proves the code
    agrees with the checker (S32). This drives the sweep against a schema
    carrying exactly that shape of condition."""
    import elimination
    # A number field can never hold the string this condition compares against,
    # so nothing a person can answer makes it False. It reads like a filter and
    # is not one — the exact shape `sorting_amount` had.
    schema = {"sections": [{"id": "s", "title": "S", "questions": [
        {"id": "count_x", "question": "How many?", "type": "number"},
        {"id": "amount_x", "question": "How much?", "type": "number",
         "showIf": "count_x != 'shoebox'"},
        {"id": "real_x", "question": "Which one?", "type": "single",
         "options": [{"value": "a"}, {"value": "b"}],
         "showIf": "count_x == '1'"},
    ]}]}
    sweep = elimination.interview_sweep(schema)
    assert [d.question for d in sweep.dead] == ["amount_x"], (
        f"expected only amount_x to be dead, got {[d.question for d in sweep.dead]}")
    assert sweep.examined == 3 and sweep.conditional == 2, (
        "the denominator is half the report and it is wrong")

    # And it must not fire on the live schema, whose conditions all work.
    assert elimination.interview_sweep().dead == []


# ── an answer the question never offered ───────────────────────────────────
#
# Raised 3 September 2026, driving the real form on the Forge. `coerce`'s
# docstring said `Interview.answer` rejected an unknown option. It did not: the
# only gate was required-ness, so any string at all could be stored against a
# multiple-choice question.


def test_an_option_the_question_never_offered_is_refused():
    """`federal_form="1041"` reached the engagement letter's scope line.

    Worse than a bad string in a record: `intake.RETURN_TYPE.get(..., "individual")`
    falls back to individual, so an unoffered entity code was silently filed as
    a personal return and got the 1040 letter.
    """
    session = iv.Interview()
    with pytest.raises(iv.InterviewError) as raised:
        session.answer("federal_form", "1041")
    assert "federal_form" not in session.answers, "nothing may be stored"
    # AND THE REFUSAL DOES NOT REPEAT IT. The first version of this message
    # quoted the rejected value, and `test_tins.py` caught it: somebody types an
    # SSN into question one and the error carries it into the log and the JSON.
    assert "1041" not in str(raised.value), "a refusal must not echo what was sent"


def test_the_message_says_what_the_question_does_offer():
    """A refusal that does not say what would work is a puzzle, not an error."""
    session = iv.Interview()
    with pytest.raises(iv.InterviewError) as raised:
        session.answer("federal_form", "banana")
    for offered in ("1040", "1120S", "1065", "1120"):
        assert offered in str(raised.value)


def test_a_free_text_question_still_takes_anything():
    """No `options` means the question offers nothing and constrains nothing.

    The guard must not turn every name, note and address into a closed list.
    """
    session = iv.Interview()
    session.answer("federal_form", "1040")
    session.answer("return_basis", "original")
    session.answer("tax_year", "2025")
    assert session.answers["tax_year"] == 2025, "a year coerces to a number"
    free_text = next(q for _, q in iv.all_questions(session.schema)
                     if not q.get("options") and q.get("type") == "text")
    session.answer(free_text["id"], "anything at all")
    assert session.answers[free_text["id"]] == "anything at all"


def test_an_optional_choice_may_be_left_blank():
    """A blank is the absence of an option, not an illegal one.

    Guarding this because the obvious implementation -- check every value
    against the offered list -- refuses `None` on every optional question and
    breaks the prune path, which stores exactly that.
    """
    session = iv.Interview()
    optional = next(
        (q for _, q in iv.all_questions(session.schema)
         if q.get("options") and not q.get("required")), None)
    if optional is None:
        pytest.skip("every question with options is required in this schema")
    session.answer(optional["id"], None)
    # `coerce` normalises a blank to the question's own empty shape -- `[]` for
    # a multi, `None` for a single -- so assert "blank", not one spelling of it.
    assert session.answers[optional["id"]] in (None, "", [])


def test_a_second_post_of_the_same_value_cannot_land_on_the_next_question():
    """F1, defanged by F2.

    `POST /interview/<sid>` carries no question id, so a double-click applies
    the value to whatever question is current by the time it arrives. That is
    fixed separately -- but it could only ever write a WRONG answer because
    nothing checked the value against the question it landed on. Proven before
    the fix: posting "1040" twice set `federal_form` AND `return_basis`.
    """
    session = iv.Interview()
    session.answer("federal_form", "1040")
    _, landed_on = session.next_question()
    assert landed_on["id"] == "return_basis", "the schema moved; retarget this test"
    with pytest.raises(iv.InterviewError):
        session.answer(landed_on["id"], "1040")
    assert "return_basis" not in session.answers


# ── the tax year ───────────────────────────────────────────────────────────
#
# F3, raised 3 September 2026. `tax_year` was `type: text`, so the form accepted
# `x`, `-5`, `99999` and `2025; DROP TABLE`. The range is a TYPO guard, not the
# three-year refund window: IRC 6511(a) limits a refund claim to three years,
# but an unfiled return has no statute of limitations and the firm prepares
# those, so a hard three-year floor would refuse real work.


def _at_tax_year():
    session = iv.Interview()
    session.answer("federal_form", "1040")
    session.answer("return_basis", "original")
    return session


@pytest.mark.parametrize("bad", ["x", "-5", "99999", "0", "2025; DROP TABLE"])
def test_a_tax_year_that_is_not_a_year_is_refused(bad):
    session = _at_tax_year()
    q = session.question("tax_year")
    with pytest.raises(iv.InterviewError):
        session.answer("tax_year", iv.coerce(q, bad))
    assert "tax_year" not in session.answers


def test_the_refusal_names_the_range_and_not_the_answer():
    """Same TIN rule as every other refusal: say what would work, not what came in."""
    session = _at_tax_year()
    q = session.question("tax_year")
    with pytest.raises(iv.InterviewError) as raised:
        session.answer("tax_year", iv.coerce(q, "99999"))
    assert "99999" not in str(raised.value)
    assert str(date.today().year) in str(raised.value) or "20" in str(raised.value)


def test_an_ordinary_year_and_the_edges_of_the_window_are_accepted():
    now = date.today().year
    for good in (now, now - taxcal.YEARS_BACK, now + taxcal.YEARS_FORWARD):
        session = _at_tax_year()
        q = session.question("tax_year")
        session.answer("tax_year", iv.coerce(q, str(good)))
        assert session.answers["tax_year"] == good


def test_an_unfiled_year_older_than_the_refund_window_is_still_workable():
    """THE POINT OF NOT USING THREE.

    IRC 6511(a) caps a refund claim at three years. It does not cap FILING: the
    assessment clock starts when a return is filed, so for a year the client
    never filed it never started. The interview asks "Any unfiled years?"
    because the firm does that work, and refusing year four here would refuse
    the engagement.
    """
    assert taxcal.YEARS_BACK > taxcal.REFUND_YEARS
    session = _at_tax_year()
    q = session.question("tax_year")
    older_than_a_refund = date.today().year - taxcal.REFUND_YEARS - 1
    session.answer("tax_year", iv.coerce(q, str(older_than_a_refund)))
    assert session.answers["tax_year"] == older_than_a_refund


# ── counts ─────────────────────────────────────────────────────────────────
#
# F5 and F13, raised 3 September 2026.


def _entity():
    session = iv.Interview()
    session.answer("federal_form", "1120S")
    session.answer("return_basis", "original")
    return session


@pytest.mark.parametrize("bad", ["abc", "2.7", "1e5", " "])
def test_a_count_that_is_not_a_whole_number_is_refused(bad):
    """F5. `coerce` hands back the raw string when `int()` fails, and
    `pricing._count` reads any unparseable string as ABSENCE -- zero.

    So `count_rentals` of "abc" or "2.7" priced identically to a correct answer
    of 1, because `form_when` bumps a sub-1 count to 1. Silent under-billing
    with no error and no review flag. `_count`'s own comment assumed this
    function rejected them; it did not, until now.
    """
    session = _entity()
    q = session.question("count_owners")
    with pytest.raises(iv.InterviewError):
        session.answer("count_owners", iv.coerce(q, bad))
    assert "count_owners" not in session.answers


def test_a_count_refusal_does_not_repeat_the_answer():
    session = _entity()
    q = session.question("count_owners")
    with pytest.raises(iv.InterviewError) as raised:
        session.answer("count_owners", iv.coerce(q, "not-a-number"))
    assert "not-a-number" not in str(raised.value)


def test_an_entity_cannot_be_scoped_for_zero_owners():
    """F13. `required` rejects only blank, and 0 is not blank -- so a zero
    satisfied the question and printed as `OwnerCount` on the business letter.
    """
    session = _entity()
    q = session.question("count_owners")
    with pytest.raises(iv.InterviewError) as raised:
        session.answer("count_owners", iv.coerce(q, "0"))
    assert "1" in str(raised.value), "say what the minimum is"
    assert "count_owners" not in session.answers


def test_the_minimum_is_declared_by_the_question_not_hardcoded():
    """The next count that cannot be zero should say so itself, in the schema.

    Guarded because the tempting fix was `if qid == "count_owners"`, which
    fixes one field and leaves the same hole on every other count.
    """
    schema = iv.load_schema()
    owners = next(q for _, q in iv.all_questions(schema)
                  if q["id"] == "count_owners")
    assert owners.get("min") == 1


def test_a_count_with_no_declared_minimum_still_takes_zero():
    """Zero is a real answer to most counts -- no rentals, no localities.

    The minimum is opt-in, so this guards against the guard over-reaching into
    every count in the schema.
    """
    session = iv.Interview()
    session.answer("federal_form", "1040")
    session.answer("return_basis", "original")
    countless = next(
        (q for _, q in iv.all_questions(session.schema)
         if q.get("type") == "number" and q.get("min") is None), None)
    if countless is None:
        pytest.skip("every number question declares a minimum")
    assert iv.coerce(countless, "0") == 0
