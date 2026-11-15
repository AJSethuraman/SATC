"""The two Windows scripts. They cannot be run here, so these check the things that have broken before: a ")" that ends a
block early (the "(x86)" in the game path), a goto to a label that is not there, and a quote left open."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_installer as bi  # noqa: E402


def scripts():
    return {"install": bi.HEAD.replace("__TARGET__", bi.TARGET), "collect": bi.collect_text()}


def test_neither_script_has_a_parenthesised_block_because_the_game_path_has_a_closing_bracket_in_it():
    for name, text in scripts().items():
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("rem"):
                continue
            assert not re.match(r"\s*(if|for)\b.*\(\s*$", line, re.I), f"{name} line {n} opens a block: {line}"
            assert not re.match(r"\s*\)", line), f"{name} line {n} closes a block: {line}"
            assert not re.match(r"\s*\(\s*$", line), f"{name} line {n} opens a block: {line}"


def test_every_goto_has_its_label():
    for name, text in scripts().items():
        labels = set(re.findall(r"^:(\w+)", text, re.M))
        code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("rem"))
        for g in re.findall(r"goto (\w+)", code):
            assert g in labels or g.lower() == "eof", f"{name}: goto {g} has no label"


def test_the_collector_reads_saved_data_and_the_newest_screenshots_and_writes_one_zip_on_the_desktop():
    t = bi.collect_text()
    assert bi.WOW in t and r"%USERPROFILE%\Desktop\Dread-report.zip" in t
    assert r"WTF\Account\*\SavedVariables\Dread.lua" in t and r"Screenshots" in t
    assert "Select-Object -First 20" in t and "AddDays(-1)" in t and "Compress-Archive" in t
    assert "/reload" in t                                                       # it says what to do when nothing was saved yet
    assert "goto failed" in t and "exit 2" in t                                  # an empty collection is reported, not a silent empty zip


def test_every_powershell_line_has_balanced_quotes_and_ends_with_the_continuation_mark_except_the_last():
    lines = bi.collect_text().splitlines()
    ps = [l for l in lines if l.startswith(' "')]
    assert len(ps) >= 8
    for l in ps:
        body = l.rstrip(" ^").strip()
        assert body.startswith('"') and body.endswith('"'), l
        assert body[1:-1].count('"') == 0, f"an inner double quote would end the string early: {l}"
    assert all(l.endswith("^") for l in ps[:-1]) and not ps[-1].endswith("^")


def test_the_installer_zip_carries_both_scripts(monkeypatch):
    import zipfile
    import os
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(bi, "stamp", lambda: None)                              # do not rewrite Build.lua just for a test
    bi.main()
    with zipfile.ZipFile(ROOT / "dist" / "Install-Dread.zip") as z:
        assert sorted(z.namelist()) == ["Collect-Dread-Report.bat", "Install-Dread.bat"]
        assert b"\r\n" in z.read("Collect-Dread-Report.bat")                     # Windows line endings
