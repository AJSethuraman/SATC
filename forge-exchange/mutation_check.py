"""Break each guard rule on purpose and confirm a test goes red.

A guard that has never failed is not evidence. For every mutation below this
copies the folder, makes one small change to exchange.py that disables or
weakens one rule, and runs the tests. A mutation the tests do not notice is a
SURVIVOR: either the rule is decoration or its test is too weak. Survivors are
reported and the exit status is non-zero. Run: python mutation_check.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

MUTATIONS = [
    ("SSN shape weakened",
     'r"\\b\\d{3}-\\d{2}-\\d{4}\\b")),  # SSN-MARK',
     'r"\\b\\d{3}-\\d{2}-\\d{5}\\b")),  # SSN-MARK'),
    ("EIN shape weakened",
     'r"\\b\\d{2}-\\d{7}\\b")),  # EIN-MARK',
     'r"\\b\\d{2}-\\d{8}\\b")),  # EIN-MARK'),
    ("long digit runs allowed", "MIN_DIGITS = 9  # DIGITS-MARK",
     "MIN_DIGITS = 99  # DIGITS-MARK"),
    ("email check broken", 'EMAIL = re.compile(r"[\\w.+-]+@[\\w-]+',
     'EMAIL = re.compile(r"[\\w.+-]+@@[\\w-]+'),
    ("phone check broken", '[-. ]\\d{3}[-. ]\\d{4}(?!\\d)")  # PHONE-MARK',
     '[-. ]\\d{3}[-. ]\\d{5}(?!\\d)")  # PHONE-MARK'),
    ("vault key not protected", 're.compile(r"vault\\.key", re.I)),  # PROTECTED-MARK',
     're.compile(r"vault\\.keyz", re.I)),  # PROTECTED-MARK'),
    ("data-file names allowed", '\\.(?:%s)\\b" % ext, cleaned, flags=re.I):  # EXT-MARK',
     '\\.(?:%s)zz" % ext, cleaned, flags=re.I):  # EXT-MARK'),
    ("links with query strings allowed",
     'if p.query or (p.fragment and not line_anchor) or "@" in p.netloc:  # QUERY-MARK',
     'if "@" in p.netloc:  # QUERY-MARK'),
    ("any link allowed", "if not link_allowed(host, path, allow):  # LINK-MARK",
     "if False:  # LINK-MARK"),
    ("a 'run' kind exists", '"agreement", "owner-item", "goal-check")  # KINDS-MARK',
     '"agreement", "owner-item", "goal-check", "run")  # KINDS-MARK'),
    ("message numbers can collide",
     "os.O_CREAT | os.O_EXCL | os.O_WRONLY)  # EXCL-MARK",
     "os.O_CREAT | os.O_WRONLY)  # EXCL-MARK"),
    ("junctions not refused",
     'return bool(getattr(st, "st_file_attributes", 0) & 0x400)  # JUNCTION-MARK',
     'return bool(getattr(st, "st_file_attributes", 0) & 0x0)  # JUNCTION-MARK'),
    ("cursor passes withheld messages", "if not x.ok:  # ACK-MARK",
     "if False:  # ACK-MARK"),
    ("any goal accepted", "    if goal in goals:\n        pass",
     "    if True:\n        pass"),
    ("mode not required", 'if h.get("mode") not in MODES:\n        problems.append("mode must',
     'if h.get("mode", "satc") not in MODES:\n        problems.append("mode must'),
    ("findings need no labelled lines",
     "missing = [l for l in FINDING_LABELS if l not in body]", "missing = []"),
    ("stale proposal accepted", "elif sha8(found.text) != ph:", "elif False:"),
    ("duplicate posts allowed", "if content_key(m.header, m.body) == key:", "if False:"),
    ("reading changes the folder",
     'return "\\n\\n".join(render_message(m) for m in pick)',
     '(root / "touched.txt").write_text("x"); return "\\n\\n".join(render_message(m) for m in pick)'),
    ("runnable text not flagged", "if RUNNABLE.search(m.body):", "if False:"),
    ("stale agreements shown as current", 'stale = prop is None or st["hash"] != {cur}',
     "stale = False"),
    ("an unknown header key is echoed", 'raise ValueError("a header key that is not allowed")  # NOECHO-KEY-MARK',
     'raise ValueError(f"header key {k!r} is not allowed")  # NOECHO-KEY-MARK'),
    ("an odd file name is shown", 'else "unexpected-" + sha8(path.name)  # NOECHO-NAME-MARK',
     'else path.name  # NOECHO-NAME-MARK'),
    ("an odd hidden file name is shown", "if known  # NOECHO-HIDDEN-MARK",
     "if True  # NOECHO-HIDDEN-MARK"),
    ("ack echoes its argument", 'raise Refused([f"that is not one of {OTHER[me]}\'s message ids"])  # NOECHO-ACK-MARK',
     'raise Refused([f"{upto} is not one of {OTHER[me]}\'s message ids"])  # NOECHO-ACK-MARK'),
    ("you can withdraw the other side's message (at posting)",
     'if wd and wd != "none" and not wd.startswith(PREFIX[me] + "-"):  # WITHDRAW-POST-MARK',
     "if False:  # WITHDRAW-POST-MARK"),
    ("a cross-side withdrawal counts (at reading)",
     'if w and w.startswith(PREFIX[m.side] + "-"):  # WITHDRAW-READ-MARK',
     "if w:  # WITHDRAW-READ-MARK"),
    ("local deny-list ignored", 'elif raw.lower().startswith("literal:"):',
     'elif False:'),
]


def run_tests(tree: Path) -> tuple[bool, str]:
    env = dict(os.environ)
    env.pop("EXCHANGE_SRC", None)
    env["EXCHANGE_MUTATION_RUN"] = "1"  # the install-match tests would kill every mutant
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                       cwd=tree / "forge-exchange", capture_output=True, text=True, env=env)
    return r.returncode == 0, (r.stdout + r.stderr)


def main() -> int:
    survivors = []
    rows = []
    with tempfile.TemporaryDirectory(prefix="mut-") as tmp:
        base = Path(tmp)
        for name, old, new in MUTATIONS:
            tree = base / "t"
            if tree.exists():
                shutil.rmtree(tree)
            shutil.copytree(REPO / "forge-exchange", tree / "forge-exchange",
                            ignore=shutil.ignore_patterns("__pycache__"))
            tins = REPO / "client-documents" / "tins.py"
            if tins.is_file():
                (tree / "client-documents").mkdir()
                shutil.copy(tins, tree / "client-documents" / "tins.py")
            src = tree / "forge-exchange" / "exchange.py"
            text = src.read_text(encoding="utf-8")
            if text.count(old) != 1:
                rows.append((name, "BAD MUTATION (anchor not found once)"))
                survivors.append(name)
                continue
            if name == MUTATIONS[0][0]:  # prove the unmutated copy is green first
                ok, out = run_tests(tree)
                if not ok:
                    print("The unmutated copy fails its own tests; fix that first.\n" + out)
                    return 1
            src.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
            ok, out = run_tests(tree)
            if ok:
                rows.append((name, "SURVIVED"))
                survivors.append(name)
            else:
                failed = out.count("\nFAIL:") + out.count("\nERROR:")
                rows.append((name, f"killed ({failed} test(s) failed)"))
    width = max(len(n) for n, _ in rows)
    print(f"{'mutation':<{width}}  result")
    for n, r in rows:
        print(f"{n:<{width}}  {r}")
    print(f"\n{len(MUTATIONS) - len(survivors)} of {len(MUTATIONS)} mutations killed; "
          f"{len(survivors)} survivor(s).")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
