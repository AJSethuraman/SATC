"""A workflow file is validated once and completely, and silence answers nothing.

Three guards used to sit on one of two paths each, which is this codebase's
recurring defect shape:

  * the condition grammar was checked in ``services:`` and not in ``tasks:``, so
    the same typo in the same hand-edited file turned a conditional document
    request into one every client gets;
  * ``evaluate_condition`` read a missing answer as a value and compared it, so a
    ``not_equals`` gate was satisfied by silence — a client chased for a document
    because they had NOT said something;
  * the fixed-unit quantity check ran inside the quote's per-rule loop, so a
    broken ``services:`` entry was found by the first client it fired for rather
    than by reading the config.

Each test below is paired with the mutation that proves it: the answered case
that must still fire, the per-form service that must still multiply, the shipped
configs that must still load.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from satc.billing.quote import load_service_map, quote_for
from satc.config import ConfigError
from satc.intake.workflows import (
    build_engagement,
    condition_holds_by_silence,
    evaluate_condition,
    list_workflows,
    load_workflow,
)

CLIENT = "client-workflow-test"
YEAR = 2025
DUE = "2026-04-15"

SHIPPED = ("personal_1040_core", "personal_schedule_c", "personal_rental_schedule_e",
           "business_monthly_bookkeeping", "business_year_end_cleanup",
           "business_scorp_tax", "business_partnership_tax", "new_client_onboarding")


# ---------------------------------------------------------------------------
# Helpers — a one-question workflow the test owns
# ---------------------------------------------------------------------------

def _write(root, *, task_extra: str = "", services: str = "",
           questions: str = "  - id: soldShares\n    label: Did you sell shares?\n"
                            "    type: boolean\n") -> None:
    """Write ``<root>/workflows/tiny.yaml``: one question, one gated task."""
    folder = root / "workflows"
    folder.mkdir(exist_ok=True)
    (folder / "tiny.yaml").write_text(
        "key: tiny\n"
        "name: Tiny workflow\n"
        "engagement_type: tiny\n"
        "questions:\n" + questions +
        "tasks:\n"
        "  - template_id: tiny-always\n"
        "    title: Always do this\n"
        "  - template_id: tiny-ask-for-statements\n"
        "    title: Request brokerage statements\n"
        "    audience: client\n"
        "    doc_type: Brokerage statements\n"
        + task_extra
        + services, encoding="utf-8")


def _templates(job):
    return {t.template_id for t in job.tasks}


# ---------------------------------------------------------------------------
# 1. The condition grammar is checked in BOTH blocks, from BOTH doors
# ---------------------------------------------------------------------------

def test_a_mistyped_operator_in_a_tasks_condition_refuses(tmp_path):
    """The one that shipped. `equal:` is not a word the engine knows, so the
    gate reads as True and a conditional document request goes to every client
    on the practice's books — silently, in a file nobody re-reads."""
    _write(tmp_path, task_extra='    condition: {question_id: soldShares, equal: "yes"}\n')
    with pytest.raises(ConfigError) as refusal:
        load_workflow("tiny", tmp_path)

    words = str(refusal.value)
    assert "tiny.yaml" in words, "principle 10: name the file"
    assert "tiny-ask-for-statements" in words, "principle 10: name the entry"
    assert "tasks:" in words, "and the block it is in"
    assert "equal" in words and "not_equals" in words, "name the fix"
    assert "TRUE for everybody" in words
    assert "EVERY client" in words, "say what it would have done"


def test_the_mistyped_task_operator_would_otherwise_gate_nothing(tmp_path):
    """The mutation for the test above: prove the typo really is a silently
    unconditional task rather than a config that would have failed anyway."""
    assert evaluate_condition({"question_id": "soldShares", "equal": "yes"},
                              {"soldShares": "no"}) is True


def test_a_task_condition_naming_a_question_the_workflow_does_not_ask_refuses(tmp_path):
    """A typo'd question id consults nothing forever, so the leaf is answered by
    silence — which is now never an answer, so the ask can never fire at all."""
    _write(tmp_path, task_extra='    condition: {question_id: soldShare, equals: "yes"}\n')
    with pytest.raises(ConfigError) as refusal:
        load_workflow("tiny", tmp_path)

    words = str(refusal.value)
    assert "soldShare" in words and "tiny.yaml" in words
    assert "soldShares" in words, "say what the workflow does ask"
    assert "tiny-ask-for-statements" in words


def test_a_task_condition_with_no_comparison_at_all_refuses(tmp_path):
    _write(tmp_path, task_extra="    condition: {question_id: soldShares}\n")
    with pytest.raises(ConfigError, match="no comparison at all"):
        load_workflow("tiny", tmp_path)


def test_a_task_condition_combining_a_branch_and_a_question_test_refuses(tmp_path):
    """The engine reads the branch and ignores everything beside it."""
    _write(tmp_path, task_extra=(
        "    condition:\n"
        "      question_id: soldShares\n"
        "      any:\n"
        '        - {question_id: soldShares, equals: "yes"}\n'))
    with pytest.raises(ConfigError, match="EITHER one"):
        load_workflow("tiny", tmp_path)


def test_an_empty_branch_in_a_task_condition_refuses(tmp_path):
    """`all: []` is vacuously true and `any: []` vacuously false — two opposite
    behaviours from one thing the author plainly meant to fill in."""
    _write(tmp_path, task_extra="    condition:\n      all: []\n")
    with pytest.raises(ConfigError, match="empty 'all'"):
        load_workflow("tiny", tmp_path)


def test_a_task_condition_that_is_not_a_mapping_refuses(tmp_path):
    _write(tmp_path, task_extra="    condition: soldShares\n")
    with pytest.raises(ConfigError, match="not a condition"):
        load_workflow("tiny", tmp_path)


def test_reading_the_services_block_also_validates_the_tasks_block(tmp_path):
    """The point of the move. The billing side reads this file for what the
    answers cost; the only error in it is in tasks:. One read, whole file."""
    _write(tmp_path,
           task_extra='    condition: {question_id: soldShares, equal: "yes"}\n',
           services="services:\n  - service: return_1040\n")
    with pytest.raises(ConfigError) as refusal:
        load_service_map("tiny", tmp_path)
    assert "tiny-ask-for-statements" in str(refusal.value)


def test_loading_the_workflow_also_validates_the_services_block(tmp_path):
    """And the mirror, which is the half that used to work. The intake side
    reads this file for what to ask; the only error in it is in services:."""
    _write(tmp_path, services=("services:\n  - service: schedule_d\n"
                               '    condition: {question_id: soldShares, equal: "yes"}\n'))
    with pytest.raises(ConfigError) as refusal:
        load_workflow("tiny", tmp_path)

    words = str(refusal.value)
    assert "schedule_d" in words and "services:" in words
    assert "every quote" in words, "the services: consequence, not the tasks: one"


def test_the_two_blocks_are_refused_in_their_own_words(tmp_path):
    """LAW AND FIRM POLICY NEVER LOOK ALIKE has a sibling here: a task going
    unconditional chases every client for a document, a service going
    unconditional puts money on every quote. Same typo, different damage, so
    the refusal must not be one generic sentence for both."""
    _write(tmp_path, task_extra='    condition: {question_id: soldShares, equal: "yes"}\n')
    with pytest.raises(ConfigError) as task_refusal:
        load_workflow("tiny", tmp_path)

    _write(tmp_path, services=("services:\n  - service: schedule_d\n"
                               '    condition: {question_id: soldShares, equal: "yes"}\n'))
    with pytest.raises(ConfigError) as service_refusal:
        load_workflow("tiny", tmp_path)

    assert "generated for EVERY client" in str(task_refusal.value)
    assert "generated for EVERY client" not in str(service_refusal.value)
    assert "on every quote" in str(service_refusal.value)


def test_a_good_condition_in_either_block_still_loads(tmp_path):
    """The mutation: the validator refuses TYPOS, not conditions."""
    _write(tmp_path,
           task_extra='    condition: {question_id: soldShares, equals: "yes"}\n',
           services=("services:\n  - service: schedule_d\n"
                     "    condition:\n"
                     "      any:\n"
                     '        - {question_id: soldShares, not_equals: "no"}\n'))
    wf = load_workflow("tiny", tmp_path)
    assert [t.template_id for t in wf.tasks] == ["tiny-always", "tiny-ask-for-statements"]
    assert [r.service_code for r in load_service_map("tiny", tmp_path)] == ["schedule_d"]


def test_all_eight_shipped_workflows_still_load():
    """The check that makes every refusal above worth having: run the validator
    over the real configs the owner edits, so a typo fails the build."""
    keys = {wf.key for wf in list_workflows()}
    assert len(keys) == 8
    assert keys == set(SHIPPED)
    for key in SHIPPED:
        load_workflow(key)             # tasks: and services: both, on every file


# ---------------------------------------------------------------------------
# 2. An unanswered question is not an answer — on the task path too
# ---------------------------------------------------------------------------

def test_silence_does_not_generate_a_task(tmp_path):
    """Principle 2, on the path that chases people. `not_equals: "no"` was
    satisfied by a question nobody answered, so the task was generated for every
    client who had not got to that question yet."""
    _write(tmp_path, task_extra='    condition: {question_id: soldShares, not_equals: "no"}\n')
    wf = load_workflow("tiny", tmp_path)
    job = build_engagement(wf, client_id=CLIENT, due_date=DUE, answers={})
    assert "tiny-ask-for-statements" not in _templates(job)
    assert "tiny-always" in _templates(job), "an ungated task is still generated"


def test_silence_does_not_mint_a_document_request(tmp_path):
    """The same defect one layer out, because document requests are minted from
    the client-facing tasks. The client would be asked to upload brokerage
    statements on the strength of a question they never answered."""
    _write(tmp_path, task_extra='    condition: {question_id: soldShares, not_equals: "no"}\n')
    wf = load_workflow("tiny", tmp_path)
    job = build_engagement(wf, client_id=CLIENT, due_date=DUE, answers={})
    asks = [t.title for t in job.tasks if t.audience == "client"]
    assert asks == [], "nothing to ask for: the client has not said anything yet"


def test_an_answered_question_still_generates_the_task(tmp_path):
    """The mutation: the rule is about SILENCE, not about `not_equals`. An
    explicit answer through the same gate behaves exactly as before."""
    _write(tmp_path, task_extra='    condition: {question_id: soldShares, not_equals: "no"}\n')
    wf = load_workflow("tiny", tmp_path)

    fires = build_engagement(wf, client_id=CLIENT, due_date=DUE,
                             answers={"soldShares": "yes"})
    assert "tiny-ask-for-statements" in _templates(fires)

    refused = build_engagement(wf, client_id=CLIENT, due_date=DUE,
                               answers={"soldShares": "no"})
    assert "tiny-ask-for-statements" not in _templates(refused)


def test_an_explicit_no_is_not_silence(tmp_path):
    """Principle 2 has two halves and this is the second: an explicit "no" is
    an answer. It must not be swept up with the unanswered ones."""
    cond = {"question_id": "soldShares", "not_equals": "yes"}
    assert evaluate_condition(cond, {"soldShares": "no"}) is True
    assert evaluate_condition(cond, {"soldShares": ""}) is False
    assert evaluate_condition(cond, {}) is False


def test_silence_satisfies_no_operator_in_either_direction():
    """Every leaf, not only `not_equals`. `less_than` was the quiet second one:
    a missing answer numbered zero, so `less_than: 100` fired on silence too."""
    for op, needle in (("equals", "yes"), ("not_equals", "no"),
                       ("includes", "CA"), ("greater_than", -1), ("less_than", 100)):
        cond = {"question_id": "q", op: needle}
        assert evaluate_condition(cond, {}) is False, op
        assert evaluate_condition(cond, {"q": ""}) is False, op
        assert evaluate_condition(cond, {"q": "   "}) is False, op


def test_a_less_than_gate_no_longer_fires_on_a_missing_number(tmp_path):
    """Named on its own because it is the one nobody would have looked for: it
    is not a `not_equals`, and it still turned silence into work."""
    _write(tmp_path, task_extra="    condition: {question_id: soldShares, less_than: 100}\n")
    wf = load_workflow("tiny", tmp_path)
    assert "tiny-ask-for-statements" not in _templates(
        build_engagement(wf, client_id=CLIENT, due_date=DUE, answers={}))
    assert "tiny-ask-for-statements" in _templates(
        build_engagement(wf, client_id=CLIENT, due_date=DUE, answers={"soldShares": "5"}))


def test_one_silent_branch_of_an_all_stops_the_whole_gate(tmp_path):
    """A half-answered `all:` decided nothing, however loud the other half is."""
    _write(tmp_path,
           questions=("  - id: soldShares\n    label: Did you sell shares?\n"
                      "    type: boolean\n"
                      "  - id: soldCrypto\n    label: Did you sell crypto?\n"
                      "    type: boolean\n"),
           task_extra=("    condition:\n"
                       "      all:\n"
                       '        - {question_id: soldShares, equals: "yes"}\n'
                       '        - {question_id: soldCrypto, not_equals: "no"}\n'))
    wf = load_workflow("tiny", tmp_path)
    assert "tiny-ask-for-statements" not in _templates(build_engagement(
        wf, client_id=CLIENT, due_date=DUE, answers={"soldShares": "yes"}))
    assert "tiny-ask-for-statements" in _templates(build_engagement(
        wf, client_id=CLIENT, due_date=DUE,
        answers={"soldShares": "yes", "soldCrypto": "yes"}))


def test_one_answered_branch_of_an_any_still_fires(tmp_path):
    """And the mutation on the other combinator: an `any:` needs one real yes,
    not all of them."""
    _write(tmp_path,
           questions=("  - id: soldShares\n    label: Did you sell shares?\n"
                      "    type: boolean\n"
                      "  - id: soldCrypto\n    label: Did you sell crypto?\n"
                      "    type: boolean\n"),
           task_extra=("    condition:\n"
                       "      any:\n"
                       '        - {question_id: soldShares, equals: "yes"}\n'
                       '        - {question_id: soldCrypto, equals: "yes"}\n'))
    wf = load_workflow("tiny", tmp_path)
    assert "tiny-ask-for-statements" in _templates(build_engagement(
        wf, client_id=CLIENT, due_date=DUE, answers={"soldShares": "yes"}))


def test_what_silence_hides_is_still_nameable(tmp_path):
    """The gate does not fire, and that is not the same as the gate not
    existing. The quote depends on being able to tell the two apart, which is
    what keeps a $145 service VISIBLE instead of silently dropped."""
    cond = {"question_id": "soldShares", "not_equals": "no"}
    assert condition_holds_by_silence(cond, {}) is True
    assert condition_holds_by_silence(cond, {"soldShares": "yes"}) is False
    assert condition_holds_by_silence(cond, {"soldShares": "no"}) is False
    assert condition_holds_by_silence(None, {}) is False


def test_nothing_moves_for_the_eight_shipped_workflows():
    """WHAT THE CHANGE MOVES, stated rather than hoped for.

    Every task condition in every shipped config is `equals: "yes"`, and an
    unanswered question was never equal to "yes" — so no shipped workflow
    generates a different task list than it did before. A blank interview yields
    exactly the ungated tasks, and only those.
    """
    for wf in list_workflows():
        job = build_engagement(wf, client_id=CLIENT, due_date=DUE, answers={},
                               tax_year=YEAR)
        assert _templates(job) == {t.template_id for t in wf.tasks if not t.condition}, (
            f"{wf.key} generates something on a blank interview")


def test_answering_everything_still_generates_every_task():
    """The other end of the same statement, and the pair to the test above: the
    change narrows silence, not answers."""
    for wf in list_workflows():
        job = build_engagement(wf, client_id=CLIENT, due_date=DUE, tax_year=YEAR,
                               answers={q.id: "yes" for q in wf.questions})
        assert len(job.tasks) == len(wf.tasks), wf.key


def test_the_quote_still_shows_what_silence_gated(tmp_path):
    """The regression guard for the money side of the same change: the quote
    reads the same engine now, and a gate held open only by silence must still
    surface as work that cannot be priced yet rather than vanishing."""
    _write(tmp_path, services=("services:\n  - service: schedule_d\n"
                               '    condition: {question_id: soldShares, not_equals: "no"}\n'))
    priced = quote_for(load_workflow("tiny", tmp_path), {}, client_id=CLIENT,
                       tax_year=YEAR, config_root=tmp_path)
    assert priced.lines == () and priced.total == Decimal("0.00")
    listed = next(u for u in priced.unpriced if u.service_code == "schedule_d")
    assert "Did you sell shares?" in listed.reason


# ---------------------------------------------------------------------------
# 3. The config is checked when it is READ, not when a client fires it
# ---------------------------------------------------------------------------

def test_a_fixed_price_service_at_a_bad_quantity_refuses_when_the_config_is_read(tmp_path):
    """The guard existed; it was inside the quote's per-rule loop, so it only
    ran for entries a particular client's answers selected. Reading the file is
    now enough to find it."""
    _write(tmp_path, services="services:\n  - service: schedule_d\n    quantity: 2\n")
    with pytest.raises(ConfigError) as refusal:
        load_service_map("tiny", tmp_path)

    words = str(refusal.value)
    assert "tiny.yaml" in words and "configs/billing/services.yaml" in words
    assert "FIXED-price" in words
    assert "per_form" in words, "principle 10: name the way out"


def test_a_gated_bad_entry_is_found_even_for_a_client_it_does_not_fire_for(tmp_path):
    """THE DEFECT ITSELF. The broken entry is gated on an answer this client did
    not give, so the loop skipped it and the quote came out clean — the config
    error waiting for whichever client answered "yes" first, and meeting the
    owner in front of them."""
    _write(tmp_path, services=("services:\n  - service: schedule_d\n"
                               "    quantity: 2\n"
                               '    condition: {question_id: soldShares, equals: "yes"}\n'))
    wf = load_workflow("tiny", tmp_path)
    with pytest.raises(ConfigError, match="FIXED-price"):
        quote_for(wf, {"soldShares": "no"}, client_id=CLIENT, tax_year=YEAR,
                  config_root=tmp_path)


def test_a_fixed_price_service_at_an_unknown_quantity_refuses_at_read(tmp_path):
    """"unknown" is a legitimate answer for a per-form service and a nonsense
    one here: there is exactly one of a fixed charge, always."""
    _write(tmp_path, services="services:\n  - service: schedule_d\n    quantity: unknown\n")
    with pytest.raises(ConfigError, match="FIXED-price"):
        load_service_map("tiny", tmp_path)


def test_a_service_the_catalogue_does_not_have_refuses_at_read(tmp_path):
    """The same move for the same reason: a code that does not exist is a typo
    in the file, findable by reading the file."""
    _write(tmp_path, services=("services:\n  - service: gold_plated_return\n"
                               '    condition: {question_id: soldShares, equals: "yes"}\n'))
    with pytest.raises(ConfigError) as refusal:
        load_service_map("tiny", tmp_path)
    assert "tiny.yaml" in str(refusal.value)
    assert "configs/billing/services.yaml" in str(refusal.value)


def test_a_per_form_service_still_loads_at_a_quantity_of_two(tmp_path):
    """The mutation: the guard is about the UNIT, not about quantities above
    one. Two state returns are 190.00 and always were."""
    _write(tmp_path, services="services:\n  - service: return_state\n    quantity: 2\n")
    rules = load_service_map("tiny", tmp_path)
    assert rules[0].quantity == Decimal("2")
    priced = quote_for(load_workflow("tiny", tmp_path), {}, client_id=CLIENT,
                       tax_year=YEAR, config_root=tmp_path)
    # It used to total 190.00 here. Since 5 September 2026 the ladder prices
    # the return; the QUANTITY is the part this test was protecting, and the
    # engagement needs to know two states as much as this catalogue ever did.
    assert priced.total == Decimal("0.00")
    listed = next(i for i in (*priced.lines, *priced.unpriced)
                  if i.service_code == "return_state")
    assert "does not record how many" not in listed.reason, (
        "the config said 2, so nothing about the count is unknown")


def test_every_shipped_services_block_survives_being_read():
    """And over the real files, where a bad entry would now be found by the
    build rather than by a client."""
    for key in SHIPPED:
        load_service_map(key)
