"""Nothing here may depend on the platform it happens to be running on.

THE CLASS, NAMED BY THE FORGE DESK ON 8 SEPTEMBER 2026 after it ran this suite
on the firm's own Windows machine — the machine that matters, and the one it
had never been run on:

    6 failed, 903 passed, 1 skipped

    "A CONTROL WHOSE OUTCOME IS DECIDED BY THE ENVIRONMENT RATHER THAN BY THE
     CODE. Mutation cannot catch these, and that is precisely why they survive
     — you are mutating the code, and the code is not what is deciding. […]
     THE SUITE PROVES THE CODE WORKS WHERE IT WAS WRITTEN."

Three of the six were one root cause: **paths compared and printed as strings**.
`str(Path)` uses the platform separator, so the holes report — a document a
PERSON reads — printed `desks\\fixed-assets\\unsupported\\forge.md` and a line
reading `runs\\` where its own prose says `runs/`. That is not a test problem;
the test was reporting a real defect in what the reader sees.

A fourth was `UnicodeDecodeError` on byte 0x9d from `cp1252`: a file opened with
no `encoding=`, where the default codec is not UTF-8 and this corpus is full of
`§` and `—`.

WHY THIS IS A TEST AND NOT A FIXED BUG. Both causes are one-line mistakes that
read as correct on the machine they are written on, and neither shows up in CI
here. Greppable, so they are grepped.
"""
import ast
import pathlib

HERE = pathlib.Path(__file__).resolve().parents[1]

#: Everything this plugin ships. `runs/` and `tie-ins` hold recorded output
#: rather than code.
SOURCES = sorted(
    p for p in list(HERE.glob("*.py")) + list((HERE / "tools").glob("*.py"))
    + list((HERE / "tests").glob("*.py"))
    if p.name != pathlib.Path(__file__).name)


def test_there_is_something_to_scan():
    assert len(SOURCES) > 40, f"only {len(SOURCES)} files found; the glob is wrong"


def test_no_file_is_read_without_saying_what_encoding_it_is_in():
    """`Path.read_text()` and `open()` use `locale.getpreferredencoding()`. On
    the firm's Windows machine that is cp1252 and this corpus is full of `§`."""
    bare = []
    for path in SOURCES:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name not in ("read_text", "write_text", "open"):
                continue
            if any(k.arg == "encoding" for k in node.keywords):
                continue
            if name == "open" and len(node.args) > 1:
                continue          # a mode was given; binary reads are fine
            bare.append(f"{path.name}:{node.lineno} {name}()")
    assert not bare, (
        "these read or write text without naming an encoding, so they use "
        "whatever the machine's locale says — cp1252 on Windows, where this "
        "corpus does not decode:\n  " + "\n  ".join(bare))


def test_no_path_becomes_text_through_str():
    """`str(Path)` is the platform separator. Anywhere a path becomes something
    a person reads or a test compares, it must be `.as_posix()`.

    Scoped to `tools/holes.py` because that is where it bit and where paths are
    a documented part of the output; widening it to every module would sweep up
    `str(p)` in exception messages, which is a different question."""
    src = (HERE / "tools" / "holes.py").read_text(encoding="utf-8")
    offences = [ln.strip() for ln in src.splitlines()
                if "str(p" in ln and "as_posix" not in ln
                and not ln.strip().startswith("#")]
    assert not offences, (
        "a path reaches the reader through str(), which prints backslashes on "
        "Windows:\n  " + "\n  ".join(offences))


def test_the_scan_can_actually_fail():
    """THE GUARD ON THE GUARD. Both checks above are absence assertions, which
    is the very family this week's findings are about."""
    tree = ast.parse('p.read_text()\n')
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    assert getattr(call.func, "attr", None) == "read_text"
    assert not any(k.arg == "encoding" for k in call.keywords)
