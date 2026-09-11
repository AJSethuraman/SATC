"""`dec-lookjoin`, 11 September 2026 — the firm: **"Run it by me — build it."**

WHAT WAS MISSING WAS THE JOIN, NOT THE SEARCHER. `searching.py` has worked since
8 September. Nothing on the answering path imported it — the only caller was
`tools/search_run.py`, which a person runs by hand against a JSON file. So a
question asked during a close reached a parked hole and stopped, while the firm
had been told three times that the desk goes and looks.

Checked on 11 September before building: nothing in the answering path imported
`searching`. `test_the_answering_path_actually_reaches_the_searcher` is what
stops that being true again.

THE FIRM'S RULE, IN THEIR EARLIER WORDS: *"if it is not directly authoritative
it would run the opinion by me."* So a find is PARKED and the firm is told what
it is, where it was read, and how binding it is. Nothing found by searching is
served — not the non-binding find they ruled on, and not the binding one either,
because `STORE` has always meant *may be added by pull request* and never *may
be answered from now*.

EVERY TEST HERE RUNS WITHOUT A NETWORK. `conftest.py` replaces the socket layer,
so a search engine and a transport that quietly reached out would fail rather
than pass slowly.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                   # noqa: E402
import engine                                                # noqa: E402
import looking                                               # noqa: E402
import record                                                # noqa: E402
import searching                                             # noqa: E402
import unsupported                                           # noqa: E402
from conftest import CORPUS                                  # noqa: E402

#: A QUESTION THE RECORD GENUINELY HOLDS NOTHING ON, found rather than invented:
#: `test_a_question_the_record_has_no_words_for` measures that this reaches zero
#: passages, and that is the only door `consult_or_file` opens onto the search.
NOTHING_ON_FILE = "what do i do with it? we bought a forklift"

#: A REAL PARAGRAPH FROM THE RECORD, used as the page a publisher serves back.
#: Quoting the corpus rather than writing prose means `searching.check`'s
#: uniqueness rule is exercised against text that actually exists.
@pytest.fixture(scope="module")
def desk():
    return record.load(CORPUS)


@pytest.fixture(scope="module")
def held(desk):
    """A passage the corpus already holds, and the source that covers it."""
    passage = next(p for p in desk.passages
                   if p.citation.startswith("26 CFR 1.263(a)-1(f)(1)(i)(D)"))
    return passage


class _Engine:
    """A search engine that returns what it was given and records the queries."""

    def __init__(self, *urls):
        self.urls = urls
        self.asked = []

    def __call__(self, query):
        self.asked.append(query)
        return [{"url": u, "title": "t", "snippet": "s"} for u in self.urls]


def _page(text):
    def transport(url, *a, **k):
        return text
    return transport


# ── the join exists, and it is on the answering path ────────────────────────

def test_the_answering_path_actually_reaches_the_searcher():
    """THE DEFECT, MECHANISED. Before this, `searching` was imported by exactly
    one module and it was a tool run by hand. An import graph is the only thing
    that keeps "it is wired in" from being a claim in a docstring."""
    tree = ast.parse((HERE / "looking.py").read_text(encoding="utf-8"))
    named = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    named |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
              for a in n.names}
    assert "searching" in named, "the join does not reach the searcher"

    front = (HERE / "ask.py").read_text(encoding="utf-8")
    assert "import looking" in front, (
        "`ask` does not reach the join, so a question asked during a close "
        "still stops at the parked hole — which is the whole defect")


def test_the_join_can_never_answer():
    """`searching` may not import `engine` or `ask`; the JOIN may, and does. So
    the property has to be held somewhere else: `looking` hands back a queue
    entry and characters to send, and constructs no `Served` at all."""
    tree = ast.parse((HERE / "looking.py").read_text(encoding="utf-8"))
    built = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "Served" not in built, "the join builds an answer"
    assert "serve" not in built and "answer" not in built, (
        "the join calls the engine's answering path")
    assert "Looked" in str(looking.run.__annotations__.get("return", ""))


def test_the_searcher_is_still_forbidden_what_the_join_is_allowed():
    """NARROWING. Adding a module that may import both must not be read as
    relaxing the rule on the one that may import neither."""
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); import searching; "
         "print(','.join(sorted({'engine','ask'} & set(sys.modules))))" % str(HERE)],
        capture_output=True, text=True, check=True)
    assert out.stdout.strip() == ""


# ── what happens to a find, which is the firm's decision ────────────────────

def test_a_find_that_ties_out_is_parked_and_the_firm_is_told(tmp_path, desk, held):
    """THE FIRM'S RULE. It tied out against a source they have already admitted
    — `searching.dispose` calls that STORE — and it is STILL parked. STORE has
    always meant *may be added by pull request*; a find that skipped the merge
    would be a model writing the record it then reads."""
    queue = tmp_path / "asked.md"
    source = desk.source(held.source_id)
    found_at = "https://some-blog.example/a-post-quoting-the-reg"

    looked = looking.run(
        NOTHING_ON_FILE, corpus=CORPUS, queue=queue,
        queries=("de minimis safe harbor invoice",),
        proposals=[{"citation": held.citation, "quoted": held.text,
                    "found_at": found_at, "kind": held.kind}],
        engine_=_Engine(found_at), transport=_page(held.text))

    # it was READ somewhere and VERIFIED somewhere else, and both are kept
    finding = looked.search.findings[0]
    assert finding.candidate.found_at == found_at
    assert finding.candidate.fetched_from == source.url, (
        "a quote of the regulation found on a blog was verified against the "
        "blog rather than against the publisher the firm admitted")

    # HELD, because the corpus already carries this citation -- and the point
    # stands either way: nothing came back that could be answered from.
    assert finding.disposition in (searching.STORE, searching.HELD)
    assert isinstance(looked.entry, unsupported.Unsupported)
    assert unsupported.parse(queue.read_text(encoding="utf-8"))


def test_a_find_nobody_has_graded_says_so_rather_than_guessing(tmp_path, desk):
    """`domains.tier_for` grades a PUBLISHER and irs.gov publishes the
    regulations and its own guides alike. A candidate is a document nobody has
    read, so the honest answer is that nobody has graded it — and saying that IS
    the decision being put to the firm."""
    queue = tmp_path / "asked.md"
    url = "https://accounting-answers.example/forklifts"
    words = "A forklift purchased for the trade is a unit of property."

    looked = looking.run(
        NOTHING_ON_FILE, corpus=CORPUS, queue=queue, queries=("forklift",),
        proposals=[{"citation": "Some Guide, chapter 4", "quoted": words,
                    "found_at": url, "kind": "rule"}],
        engine_=_Engine(url), transport=_page(words))

    working = looked.entry.working
    assert "NOT graded" in working or "does not settle" in working, (
        f"the queue row does not say how binding the find is:\n{working}")
    assert url in working, "the firm is not told where it was read"


def test_a_search_that_finds_nothing_is_still_filed(tmp_path):
    """A gap somebody has searched and a gap nobody has searched are the same
    hole in the record and call for opposite next steps."""
    queue = tmp_path / "asked.md"
    looked = looking.run(
        NOTHING_ON_FILE, corpus=CORPUS, queue=queue, queries=("forklift",),
        proposals=[], engine_=_Engine(), transport=_page(""))

    assert not looked.worth_the_firms_time
    assert "Searched." in looked.entry.working
    assert "found empty" in looked.entry.working
    assert unsupported.parse(queue.read_text(encoding="utf-8"))


def test_the_queue_row_carries_no_passage_text(tmp_path, desk, held):
    """THIS FILE LANDS IN THE REPOSITORY. The citation, the publisher and the
    verdict are what a decision is made from; the words are at the url, where
    the firm reads them with the paragraph around them."""
    queue = tmp_path / "asked.md"
    looked = looking.run(
        NOTHING_ON_FILE, corpus=CORPUS, queue=queue, queries=("q",),
        proposals=[{"citation": held.citation, "quoted": held.text,
                    "found_at": "https://x.example/p", "kind": held.kind}],
        engine_=_Engine("https://x.example/p"), transport=_page(held.text))
    assert held.text[:60] not in looked.entry.working
    assert held.citation in looked.entry.working


# ── and the doer is told, without being given permission ────────────────────

def test_the_page_says_the_desk_looked_and_that_the_find_is_not_theirs(
        tmp_path, desk, held):
    queue = tmp_path / "asked.md"
    page, entry = ask.consult_or_file(
        NOTHING_ON_FILE, queue=queue, corpus=CORPUS,
        search=_Engine("https://x.example/p"), transport=_page(held.text),
        queries=("de minimis",),
        proposals=[{"citation": held.citation, "quoted": held.text,
                    "found_at": "https://x.example/p", "kind": held.kind}])

    assert entry is not None
    assert "The desk went and looked" in page
    assert "This is not permission." in page, (
        "going and looking must not quietly replace the refusal to be read as a "
        "yes -- that is `dec-coverage` and it still holds")


def test_the_record_already_holding_it_is_a_third_outcome_and_says_so(
        tmp_path, desk, held):
    """FOUND BY PRINTING THE PAGE, NOT BY READING THE CODE.

    `worth_the_firms_time` counts STORE and PROPOSE, so a find that came back
    HELD -- the record already carries this citation -- rendered as "Nothing
    tied out". Something tied out. What it found is that the authority was here
    all along and the question could not reach it, which is a defect in
    RETRIEVAL rather than a gap in the record, and it is the most actionable
    thing a search comes back with. The firm reading "Desk found" would have
    gone looking for a source to admit that they admitted months ago.
    """
    queue = tmp_path / "asked.md"
    page, entry = ask.consult_or_file(
        NOTHING_ON_FILE, queue=queue, corpus=CORPUS,
        search=_Engine("https://x.example/p"), transport=_page(held.text),
        queries=("de minimis",),
        proposals=[{"citation": held.citation, "quoted": held.text,
                    "found_at": "https://x.example/p", "kind": held.kind}])

    assert "Nothing tied out" not in page, (
        "something tied out and the page says otherwise")
    assert "already holds what the search found" in page
    assert "the way to it is" in page
    assert held.citation in page
    assert "does not make it yours to cite" in page, (
        "a doer told the record holds a paragraph, without being told they may "
        "not reach for it, will reach for it")


def test_the_firm_is_told_it_could_not_reach_rather_than_that_it_found(
        tmp_path, desk, held):
    """The first three words are the loudest thing the firm reads."""
    queue = tmp_path / "asked.md"
    looked = looking.run(
        NOTHING_ON_FILE, corpus=CORPUS, queue=queue, queries=("q",),
        proposals=[{"citation": held.citation, "quoted": held.text,
                    "found_at": "https://x.example/p", "kind": held.kind}],
        engine_=_Engine("https://x.example/p"), transport=_page(held.text))
    assert looked.told.startswith("Desk could not reach"), looked.told
    assert held.citation in looked.told


def test_a_caller_with_no_search_engine_behaves_exactly_as_before(tmp_path):
    """A close run somewhere with no browser gets the page it got on
    10 September rather than failing in a new way."""
    queue = tmp_path / "asked.md"
    page, entry = ask.consult_or_file(
        NOTHING_ON_FILE, queue=queue, corpus=CORPUS)
    assert entry is not None
    assert "The desk went and looked" not in page
    assert "The words that missed" in page


def test_a_question_the_record_answers_never_reaches_the_search(tmp_path):
    """The searcher repairs a hole; it is not a second way to answer. A question
    the corpus reaches must not touch the engine at all."""
    queue = tmp_path / "asked.md"
    engine_ = _Engine("https://x.example/p")
    out, filed = ask.consult_or_file(
        "what records are required for a purchase?", queue=queue,
        corpus=CORPUS, search=engine_, transport=_page(""))
    assert filed is None, "a question the record answers was filed"
    assert engine_.asked == [], "it searched for something already on file"
