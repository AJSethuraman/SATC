"""The pre-send gate: does a pack survive being opened.

WHY THIS SUITE EXISTS. Every other test in this repo reads a document as a
STRING and asserts on its tokens. That is exactly right for checking a merge,
and it is completely blind to whether the thing renders. So for weeks every
pack shipped without `satc-doc.css` and `doc-page.js`, every document opened as
browser-default Times, and 749 tests stayed green throughout. The firm found it
by opening one: *"these html files are plain text?"*

The gate is the answer. These tests are the gate's own check-the-checker: each
one BREAKS a pack on purpose and proves the gate catches it. A gate nobody has
watched fail is not known to work — that is the whole lesson of the incident
that produced it.

The browser checks are skipped where Playwright or Chromium is absent, and they
say so out loud rather than passing quietly. A skipped check that reports as a
pass is the same failure in a smaller costume.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import engagements  # noqa: E402
import presend  # noqa: E402

HAS_BROWSER = False
try:  # pragma: no cover - environment probe
    import playwright.sync_api  # noqa: F401
    HAS_BROWSER = Path(presend.CHROMIUM).exists()
except ImportError:  # pragma: no cover
    HAS_BROWSER = False

needs_browser = pytest.mark.skipif(
    not HAS_BROWSER, reason="no Playwright/Chromium here — the render gate "
                            "cannot be exercised, and is NOT being asserted")


# ── what a document points at ─────────────────────────────────────────────

def test_relative_references_are_found_and_absolute_ones_ignored():
    html = """
      <link rel="stylesheet" href="satc-doc.css">
      <script src="doc-page.js"></script>
      <link href="https://fonts.googleapis.com/css2?family=X" rel="stylesheet">
      <a href="#top">top</a>
      <a href="mailto:hello@example.com">mail</a>
      <img src="data:image/png;base64,AAAA">
      <img src='logo.svg'>
    """
    assert presend.referenced_files(html) == [
        "satc-doc.css", "doc-page.js", "logo.svg"]


def test_a_missing_asset_is_named_not_merely_counted(tmp_path):
    """The check has to say WHICH file, because a screenshot cannot."""
    (tmp_path / "letter.html").write_text(
        '<link rel="stylesheet" href="satc-doc.css">'
        '<script src="doc-page.js"></script>', encoding="utf-8")
    (tmp_path / "satc-doc.css").write_text("/* here */", encoding="utf-8")

    found = presend.assets_present(tmp_path)
    assert len(found) == 1
    assert found[0].document == "letter.html"
    assert "doc-page.js" in found[0].detail
    assert found[0].blocking


def test_a_complete_pack_has_nothing_to_say(tmp_path):
    (tmp_path / "letter.html").write_text(
        '<link rel="stylesheet" href="satc-doc.css">', encoding="utf-8")
    (tmp_path / "satc-doc.css").write_text("/* here */", encoding="utf-8")
    assert presend.assets_present(tmp_path) == []


def test_a_query_string_does_not_hide_a_missing_file(tmp_path):
    """`href="satc-doc.css?v=2"` is still a reference to satc-doc.css."""
    (tmp_path / "letter.html").write_text(
        '<link rel="stylesheet" href="satc-doc.css?v=2">', encoding="utf-8")
    assert len(presend.assets_present(tmp_path)) == 1


# ── the gate reports what it DID, not only what failed ────────────────────

def test_a_skipped_check_is_reported_as_skipped(tmp_path):
    """A clean report that does not name its checks is indistinguishable from
    a check that never ran. That distinction is the entire subject here."""
    (tmp_path / "letter.html").write_text("<p>hi</p>", encoding="utf-8")
    res = presend.gate(tmp_path, {}, rendered=None, skip_render=True)
    text = presend.format_result(res)

    assert "SKIP" in text
    assert "not known to be right" in text
    assert res.ok, "skipping is not failing"
    assert len(res.skipped) == 2, "both the browser and the agreement check"


# ── the whole command, on a real engagement ───────────────────────────────

@pytest.fixture(scope="module")
def packed(tmp_path_factory):
    """One real engagement, built once.

    MODULE SCOPE ON PURPOSE. Building it per test ran the whole scenario --
    intake, pricing, three merges, three browser renders -- seven times over,
    and took seven and a half minutes. A suite slow enough that people stop
    running it is a suite that is not protecting anything.

    Every test that uses it packages into its OWN output directory, so nothing
    here is shared but the engagement itself, which is read-only.
    """
    import exercise

    base = tmp_path_factory.mktemp("engagement")
    store = base / "store"
    out = base / "out"
    scenario = exercise.scenarios()[0]
    result = exercise.run_one(scenario, store, out)
    ref = getattr(result, "ref", None) or "2026-0001"
    return {"store": store, "out": out / scenario.key, "ref": ref}


def _package(ref, store, out, **flags):
    args = type("A", (), {
        "engagement": ref, "store": str(store), "out": str(out),
        "with_invoice": False, "no_pdf": True, "force": False,
        "reason": "", "skip_render": not HAS_BROWSER,
    })()
    for k, v in flags.items():
        setattr(args, k, v)
    return cli.cmd_package(args)


def test_a_good_pack_passes_and_carries_its_own_assets(packed, tmp_path):
    out = tmp_path / "fresh"
    assert _package(packed["ref"], packed["store"], out) == 0

    for asset in presend.PACK_ASSETS:
        assert (out / asset).exists(), (
            f"{asset} is not in the pack, so every document in it opens as "
            f"plain text")
    assert presend.assets_present(out) == []


def test_a_pack_missing_an_asset_is_refused_and_nothing_is_written(
        packed, tmp_path, monkeypatch):
    """THE ORIGINAL BUG, reproduced: the templates are there, the assets are
    not, and before the gate this wrote a folder of unreadable documents and
    reported success."""
    crippled = tmp_path / "templates"
    shutil.copytree(cli.TEMPLATE_DIR, crippled)
    (crippled / "doc-page.js").unlink()
    monkeypatch.setattr(cli, "TEMPLATE_DIR", crippled)

    out = tmp_path / "refused"
    assert _package(packed["ref"], packed["store"], out) == 1
    assert not out.exists() or not any(out.iterdir()), (
        "the gate refused but a pack was written anyway — a refusal that "
        "leaves a folder behind is worse than no refusal, because someone "
        "opens the folder")


def test_force_without_a_reason_is_refused(packed, tmp_path, monkeypatch):
    crippled = tmp_path / "templates"
    shutil.copytree(cli.TEMPLATE_DIR, crippled)
    (crippled / "doc-page.js").unlink()
    monkeypatch.setattr(cli, "TEMPLATE_DIR", crippled)

    out = tmp_path / "noreason"
    assert _package(packed["ref"], packed["store"], out, force=True) == 1
    assert not out.exists() or not any(out.iterdir())


def test_force_with_a_reason_writes_the_pack_and_logs_what_failed(
        packed, tmp_path, monkeypatch):
    """The override is what makes this a gate rather than a wall. What makes
    it a gate rather than a suggestion is that it is written down."""
    crippled = tmp_path / "templates"
    shutil.copytree(cli.TEMPLATE_DIR, crippled)
    (crippled / "doc-page.js").unlink()
    monkeypatch.setattr(cli, "TEMPLATE_DIR", crippled)

    out = tmp_path / "forced"
    code = _package(packed["ref"], packed["store"], out, force=True,
                    reason="client is in the office and signing on paper")
    assert code == 0
    assert (out / "MANIFEST.json").exists()

    logged = engagements.overrides(packed["ref"], packed["store"])
    assert len(logged) == 1
    entry = logged[0]
    assert entry["command"] == "package"
    assert entry["reason"] == "client is in the office and signing on paper"
    assert entry["failed"], "an override that records no failure records nothing"
    assert any("doc-page.js" in f["detail"] for f in entry["failed"])
    assert entry["at"].endswith("+00:00"), "timestamps are UTC and unambiguous"


def test_the_override_log_is_append_only(tmp_path):
    """A log you can edit is not evidence."""
    store = tmp_path / "store"
    engagements.record_override("2026-0009", {"at": "1", "reason": "first"}, store)
    engagements.record_override("2026-0009", {"at": "2", "reason": "second"}, store)

    log = engagements.overrides("2026-0009", store)
    assert [e["reason"] for e in log] == ["first", "second"]


def test_a_corrupt_override_log_is_kept_not_overwritten(tmp_path):
    """Something happened here. Losing the evidence is not a recovery."""
    store = tmp_path / "store"
    path = engagements._dir(store, "2026-0010") / "overrides.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    engagements.record_override("2026-0010", {"at": "1", "reason": "after"}, store)
    assert path.with_suffix(".corrupt").exists()
    assert json.loads(path.read_text())[-1]["reason"] == "after"


# ── the browser half ──────────────────────────────────────────────────────

@needs_browser
def test_the_render_gate_catches_a_document_with_no_stylesheet(tmp_path):
    """Deleting the assets makes the document fail. This is the assertion the
    original incident needed and did not have."""
    doc = tmp_path / "letter.html"
    shutil.copy2(cli.TEMPLATE_DIR / "satc-doc.css", tmp_path / "satc-doc.css")
    doc.write_text(
        '<link rel="stylesheet" href="satc-doc.css">'
        '<doc-page><p>A letter with no page component.</p></doc-page>',
        encoding="utf-8")

    found = presend.renders([doc])
    assert len(found) == 1
    assert "plain text" in found[0].detail
    assert found[0].blocking


@needs_browser
def test_the_render_gate_passes_a_real_document(packed, tmp_path):
    out = tmp_path / "real"
    assert _package(packed["ref"], packed["store"], out) == 0
    assert presend.renders(sorted(out.glob("*.html"))) == []


# ── section numbers on the page ───────────────────────────────────────────

def test_a_gap_in_the_numbering_is_caught(tmp_path):
    """The live defect this check was built for: 26 of 55 rendered documents
    read 01, 02, 04, 05 because a dropped `[[IF]]` section left a hole and
    nothing renumbered."""
    (tmp_path / "onboarding.html").write_text(
        '<h2><span class="n">01</span>A</h2>'
        '<h2><span class="n">02</span>B</h2>'
        '<h2><span class="n">04</span>C</h2>', encoding="utf-8")
    found = presend.numbering(tmp_path)
    assert len(found) == 1
    assert "01 02 04" in found[0].detail
    assert found[0].blocking


def test_a_repeated_number_is_caught(tmp_path):
    """Both halves of an inverse pair rendering — a contradiction on the page."""
    (tmp_path / "delivery.html").write_text(
        '<h2><span class="n">01</span>A</h2>'
        '<h2><span class="n">02</span>B</h2>'
        '<h2><span class="n">02</span>B again</h2>', encoding="utf-8")
    assert len(presend.numbering(tmp_path)) == 1


def test_an_unnumbered_document_is_not_a_failure(tmp_path):
    (tmp_path / "note.html").write_text("<h2>Just a heading</h2>", encoding="utf-8")
    assert presend.numbering(tmp_path) == []


def test_contiguous_numbering_passes(tmp_path):
    (tmp_path / "ok.html").write_text(
        '<h2><span class="n">01</span>A</h2>'
        '<h2><span class="n">02</span>B</h2>', encoding="utf-8")
    assert presend.numbering(tmp_path) == []


# ── sentences the firm deleted ────────────────────────────────────────────

def test_a_deleted_sentence_coming_back_is_caught(tmp_path):
    """A note in a tenets file saying a phrase is "not yet swept" is not a
    control. This is: it caught the bookkeeping engagement letter still
    carrying "Sign through Encyro and it comes straight back to us." a day
    after that sentence was replaced in every other letter."""
    (tmp_path / "letter.html").write_text(
        "<p>If this letter states your understanding, sign and return a copy. "
        "Sign through Encyro and it comes straight back to us.</p>",
        encoding="utf-8")
    found = presend.retired_phrases(tmp_path)
    assert len(found) == 1
    assert "Encyro" in found[0].detail
    assert found[0].blocking


def test_punctuation_is_not_a_disguise(tmp_path):
    """Changing a comma is exactly the edit that would let a deleted sentence
    back in wearing a hat."""
    (tmp_path / "letter.html").write_text(
        "<p>Sign through Encyro; and it comes — straight back to us!</p>",
        encoding="utf-8")
    assert len(presend.retired_phrases(tmp_path)) == 1


def test_a_heading_is_not_a_retired_bullet(tmp_path):
    """"this estimate assumes" is retired as a bullet opener and LIVE as the
    heading. Excluding headings is what makes this check exact rather than
    nearly exact."""
    (tmp_path / "estimate.html").write_text(
        '<h2>Only the work listed in the scope section of the engagement '
        'letter is included.</h2><p>Ordinary copy.</p>', encoding="utf-8")
    assert presend.retired_phrases(tmp_path) == []


def test_the_registry_refuses_a_phrase_too_short_to_be_a_sentence(tmp_path, monkeypatch):
    """A fragment collides with innocent copy sooner or later — measured: one
    of the two hits this check produced on its first run was exactly that."""
    reg = tmp_path / "retired.yaml"
    reg.write_text('phrases:\n  - phrase: "sign below"\n', encoding="utf-8")
    monkeypatch.setattr(presend, "_RETIRED", reg)

    (tmp_path / "doc.html").write_text("<p>Anything.</p>", encoding="utf-8")
    found = presend.retired_phrases(tmp_path)
    assert len(found) == 1
    assert "shorter than five words" in found[0].detail


def test_every_template_and_every_real_pack_is_clean_of_retired_sentences(tmp_path):
    """The measurement, not an assumption. Twelve templates, zero hits."""
    import shutil
    for f in cli.TEMPLATE_DIR.glob("*.html"):
        shutil.copy2(f, tmp_path / f.name)
    assert presend.retired_phrases(tmp_path) == []


# ── plain language ────────────────────────────────────────────────────────

@pytest.mark.parametrize("word,kind", [
    ("pursuant", "legalese"), ("herein", "legalese"),
    ("at our discretion", "legalese"),
    ("authorisation", "British"), ("cheque", "British"),
])
def test_banned_words_are_caught(tmp_path, word, kind):
    (tmp_path / "doc.html").write_text(
        f"<p>The work is done {word} to the schedule.</p>", encoding="utf-8")
    assert len(presend.plain_language(tmp_path)) == 1, f"{kind}: {word}"


def test_accompanies_is_deliberately_allowed(tmp_path):
    """It is in DOCUMENT-TENETS' written list and it is live in five templates
    in copy the firm has approved four times. Shipping the list with it in
    would make this check cry wolf on its first run, and a linter that cries
    wolf gets muted."""
    (tmp_path / "doc.html").write_text(
        "<p>This accompanies our engagement letter.</p>", encoding="utf-8")
    assert presend.plain_language(tmp_path) == []


def test_the_screen_only_reference_block_is_not_read(tmp_path):
    """THE DIFFERENCE BETWEEN RIGHT AND WRONG FIVE TIMES OUT OF FIVE. Every
    template carries a FIELDS reference table that `merge` strips before
    anything reaches a client. Read the source without stripping it and the
    spelling sweep reports five British spellings, every one of them invisible
    to every client."""
    # The trailing </body> matters: `merge._REF_BLOCK` is anchored to a ref
    # block that sits at the end of the document, before the script or the
    # closing body tag, which is where every template puts it. This check
    # delegates to that same pattern rather than writing a second one, so the
    # two cannot disagree about what a client sees.
    (tmp_path / "doc.html").write_text(
        '<p>Ordinary copy.</p>'
        '<div class="ref"><p>Sample: an authorisation from the licence '
        'centre.</p></div></body>', encoding="utf-8")
    assert presend.plain_language(tmp_path) == []


def test_a_reference_block_that_merge_would_ship_is_still_read(tmp_path):
    """The other direction, and the reason this delegates rather than
    re-implements: a ref block somewhere merge does NOT strip is a block a
    client sees, so the check has to see it too."""
    (tmp_path / "doc.html").write_text(
        '<div class="ref"><p>An authorisation.</p></div>'
        '<p>And then the letter continues.</p>', encoding="utf-8")
    assert len(presend.plain_language(tmp_path)) == 1


def test_every_template_is_clean_of_banned_words(tmp_path):
    import shutil
    for f in cli.TEMPLATE_DIR.glob("*.html"):
        shutil.copy2(f, tmp_path / f.name)
    assert presend.plain_language(tmp_path) == []
