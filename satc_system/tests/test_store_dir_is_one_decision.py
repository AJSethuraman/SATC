"""Where the store lives is decided once, and `SATC_DATA_DIR` is obeyed.

FOUND BY RUNNING IT, 4 September 2026. With `SATC_DATA_DIR` pointed at an empty
temp directory, `satc chase` printed the clients out of the real `build/data`
store and wrote nothing to the temp one. `_default_dir`'s own docstring had
promised the opposite for as long as it existed -- "``SATC_DATA_DIR`` (handled
by the caller) always wins over this default" -- and it was handled by two
callers out of eight.

**The one that matters is `reset`, because `reset` deletes the vault.** Under
`SATC_DATA_DIR=/tmp/scratch` it resolved `DEFAULT_DIR` and would have destroyed
the live store while the operator believed the run was scoped to a scratch
directory. It does print the path it is about to delete, so a reader of the
prompt would have caught it -- but `--yes` skips the prompt, which is the form
any script or test would use.

The brief for this machine says: *point tests at a temp store*. That instruction
was not enforceable through the CLI until this landed.

NOTHING HERE TOUCHES THE REAL STORE. `DEFAULT_DIR` is monkeypatched to a second
temp directory that stands in for it, so the delete-the-right-one test can
assert the real store survives without a real store being involved.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from satc.persistence import store as store_mod
from satc.persistence.store import SATCStore, resolve_dir


@pytest.fixture
def two_stores(tmp_path, monkeypatch):
    """A scratch dir the operator asked for, and a stand-in for the real one."""
    scratch = tmp_path / "scratch"
    pretend_real = tmp_path / "pretend_build_data"
    scratch.mkdir()
    pretend_real.mkdir()
    monkeypatch.setattr(store_mod, "DEFAULT_DIR", pretend_real)
    monkeypatch.delenv("SATC_DATA_DIR", raising=False)
    return scratch, pretend_real


# ── the resolver itself ──────────────────────────────────────────────────────

def test_the_environment_beats_the_default(two_stores, monkeypatch):
    scratch, pretend_real = two_stores
    monkeypatch.setenv("SATC_DATA_DIR", str(scratch))
    assert resolve_dir() == scratch, (
        "SATC_DATA_DIR was set and the default won anyway — this is the bug")


def test_an_explicit_argument_beats_the_environment(two_stores, monkeypatch):
    """A path typed on this command line is more specific than a variable that
    may have been exported hours ago."""
    scratch, _ = two_stores
    elsewhere = scratch.parent / "elsewhere"
    monkeypatch.setenv("SATC_DATA_DIR", str(scratch))
    assert resolve_dir(elsewhere) == elsewhere


def test_the_default_is_used_when_nothing_says_otherwise(two_stores):
    _, pretend_real = two_stores
    assert resolve_dir() == pretend_real


def test_an_empty_environment_variable_is_not_a_path(two_stores, monkeypatch):
    """`SATC_DATA_DIR=` exports an empty string. Treating that as a directory
    resolves the store to the process's working directory, which is a different
    store on every invocation."""
    _, pretend_real = two_stores
    monkeypatch.setenv("SATC_DATA_DIR", "")
    assert resolve_dir() == pretend_real


# ── every caller, not just the two that used to handle it ────────────────────

def test_the_store_itself_obeys_the_environment(two_stores, monkeypatch):
    scratch, pretend_real = two_stores
    monkeypatch.setenv("SATC_DATA_DIR", str(scratch))
    store = SATCStore()
    assert store.dir == scratch
    assert (scratch / "satc_mart.db").exists()
    assert not (pretend_real / "satc_mart.db").exists(), (
        "the store wrote into the default directory despite SATC_DATA_DIR")


def test_a_cli_command_reads_the_store_the_environment_names(two_stores, monkeypatch):
    """`chase` is the one that was caught doing this. It takes `--dir`, and with
    `--dir` absent it built `SATCStore(None)` — which meant `DEFAULT_DIR`."""
    scratch, pretend_real = two_stores
    monkeypatch.setenv("SATC_DATA_DIR", str(scratch))
    assert SATCStore(None).dir == scratch


# ── the destructive one ──────────────────────────────────────────────────────

def test_reset_deletes_the_store_it_was_pointed_at_and_not_the_real_one(
        two_stores, monkeypatch, capsys):
    """THE REASON THIS FILE EXISTS.

    Both directories get databases. `reset --yes` runs under SATC_DATA_DIR
    naming the scratch one. The scratch databases must be gone and the stand-in
    for the real store must be untouched.
    """
    scratch, pretend_real = two_stores
    monkeypatch.setenv("SATC_DATA_DIR", str(scratch))
    for d in (scratch, pretend_real):
        for name in ("satc_vault.db", "satc_mart.db"):
            (d / name).write_bytes(b"not really a database")

    from satc.cli import main
    rc = main(["reset", "--yes"])

    assert rc == 0, capsys.readouterr().out
    assert not (scratch / "satc_vault.db").exists(), (
        "reset did not delete the store it was pointed at")
    assert (pretend_real / "satc_vault.db").exists(), (
        "RESET DELETED THE REAL STORE while scoped to a scratch directory — "
        "this is the data-loss path the resolver exists to close")
    assert (pretend_real / "satc_mart.db").exists()


def test_reset_names_the_directory_it_is_about_to_delete(two_stores, monkeypatch,
                                                        capsys):
    """The mitigating half of the old bug, kept deliberately: the prompt printed
    the real path, so a person reading it would have seen `build\\data` and
    stopped. That is worth keeping now that the path is also correct."""
    scratch, _ = two_stores
    monkeypatch.setenv("SATC_DATA_DIR", str(scratch))
    monkeypatch.setattr("builtins.input", lambda *_: "no")
    from satc.cli import main
    rc = main(["reset"])
    out = capsys.readouterr().out
    assert rc == 1 and "Aborted" in out
    assert str(scratch) in out, (
        f"the confirmation prompt did not say which directory it would "
        f"delete; it said: {out!r}")


# ── check the checker ────────────────────────────────────────────────────────

def test_these_tests_would_have_failed_against_the_old_resolver(two_stores,
                                                                monkeypatch):
    """MUTATION. The old line was `Path(directory) if directory else DEFAULT_DIR`
    — the environment never consulted. Reintroduce exactly that and the
    environment test above must fail.

    A regression test that passes against the bug it names is decoration. This
    is the check that the check works.
    """
    scratch, pretend_real = two_stores
    monkeypatch.setenv("SATC_DATA_DIR", str(scratch))

    def old_resolver(directory=None):
        return Path(directory) if directory else store_mod.DEFAULT_DIR

    assert old_resolver() == pretend_real, (
        "the old behaviour no longer reproduces, so the test above is not "
        "pinning what it claims to pin")
    assert resolve_dir() == scratch
    assert old_resolver() != resolve_dir(), (
        "old and new resolvers agree — the fix is not doing anything")


def test_no_caller_resolves_the_directory_for_itself_any_more(two_stores):
    """The bug was eight callers each deciding. `resolve_dir` is only the fix
    while it stays the only decision, so the source is read for the pattern that
    caused it.

    `store.py` is excluded: it is where the decision now lives.
    """
    root = Path(__file__).resolve().parents[1] / "src" / "satc"
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "store.py":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if "DEFAULT_DIR" in line and "import" not in line and not line.strip().startswith("#"):
                offenders.append(f"{path.relative_to(root)}:{i}: {line.strip()}")
    assert not offenders, (
        "these read DEFAULT_DIR directly instead of calling resolve_dir(), "
        "which is how SATC_DATA_DIR came to be honoured by two callers out of "
        "eight:\n  " + "\n  ".join(offenders))


def test_the_documented_promise_and_the_code_agree(two_stores, monkeypatch):
    """`_default_dir`'s docstring promised SATC_DATA_DIR always wins. For most
    of the app's life that sentence was false. Assert the sentence."""
    scratch, _ = two_stores
    monkeypatch.setenv("SATC_DATA_DIR", str(scratch))
    doc = store_mod._default_dir.__doc__ or ""
    assert "SATC_DATA_DIR" in doc and "always wins" in doc
    assert resolve_dir() == scratch, (
        "the docstring says SATC_DATA_DIR always wins and it does not")
