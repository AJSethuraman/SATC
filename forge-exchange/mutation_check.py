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
    ("email check broken", r'''[\w.+-]++@[\w-]+''', r'''[\w.+-]++@@[\w-]+'''),
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
    ("stale agreements shown as current",
     r'''stale = prop is None or any(h != cur for h in st["hashes"].values())  # LATEST-FP-MARK''',
     r'''stale = False  # LATEST-FP-MARK'''),
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
    ("temporary names can collide",
     'tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")  # TMP-UNIQUE-MARK',
     'tmp = path.with_name(f".{path.name}.tmp")  # TMP-UNIQUE-MARK'),
    ("an out-of-date AGREED.md is not reported",
     'current = on_disk == view_agreed(root)  # STALE-AGREED-MARK',
     'current = True  # STALE-AGREED-MARK'),
    ("duplicate key ignores withdrawals and metadata",
     'fields = [h.get(k, "") for k in HEADER_KEYS if k not in ("id", "from")]  # KEY-FIELDS-MARK',
     'fields = [h.get(k, "") for k in ("kind", "re", "about", "proposal")]  # KEY-FIELDS-MARK'),
    ("oversize bodies accepted on read", "if len(body) > MAX_BODY:  # SIZE-BODY-MARK",
     "if False:  # SIZE-BODY-MARK"),
    ("huge files are read on read", "if path.stat().st_size > MAX_FILE_BYTES:  # SIZE-FILE-MARK",
     "if False:  # SIZE-FILE-MARK"),
    ("a withdrawal can point at a later message", "if mt and int(mt.group(2)) < m.n:  # WITHDRAW-ORDER-MARK",
     "if mt:  # WITHDRAW-ORDER-MARK"),
    ("digits grouped by dots and commas pass", 'DIGIT_RUN = re.compile(r"(?<![A-Za-z0-9])\\d{3,}(?:[ .,/_-]\\d{3,})*(?![A-Za-z0-9])")  # PUNCT-MARK',
     'DIGIT_RUN = re.compile(r"(?<![A-Za-z0-9])\\d{3,}(?:[ -]\\d{3,})*(?![A-Za-z0-9])")  # PUNCT-MARK'),
    ("a path ending at engagements passes", 're.compile(r"(?:[\\\\/]engagements\\b|\\bengagements[\\\\/])", re.I)),  # ENGAGE-MARK',
     're.compile(r"engagements[\\\\/]", re.I)),  # ENGAGE-MARK'),
    ("a lone carriage return passes",
     r"""control = bool(CONTROL.search(text) or "\r" in text.replace("\r\n", "\n"))  # CR-MARK""",
     r"""control = bool(CONTROL.search(text))  # CR-MARK"""),
    ("non-http schemes pass", "if p.scheme.lower() not in (\"http\", \"https\"):  # SCHEME-MARK",
     "if False:  # SCHEME-MARK"),
    ("an abandoned reservation leaves a gap",
     "if age > RESERVE_STALE_SECONDS and not final.exists():  # STALE-RESERVE-MARK",
     "if False:  # STALE-RESERVE-MARK"),
    ("an unreadable-size message is written", "if len(text.encode(\"utf-8\")) > MAX_FILE_BYTES:  # POST-BYTES-MARK",
     "if False:  # POST-BYTES-MARK"),
    ("old fingerprints keep an agreement stale",
     "stale = prop is None or any(h != cur for h in st[\"hashes\"].values())  # LATEST-FP-MARK",
     "stale = prop is None or set(st[\"hashes\"].values()) | {\"old\"} != {cur}  # LATEST-FP-MARK"),
    ("ids beyond four digits are created", "if n > MAX_MESSAGE_NUMBER:  # NUMBER-MARK",
     "if False:  # NUMBER-MARK"),
    ("email pattern is quadratic again", r'''(?<![\w.+-])[\w.+-]++@''', r'''[\w.+-]+@'''),
    ("link pattern is quadratic again", r'''(?<![A-Za-z0-9+.-])[A-Za-z][A-Za-z0-9+.-]*+://''', r'''[A-Za-z][A-Za-z0-9+.-]*://'''),
    ("phone-shaped runs pass", r'''if 10 <= digits <= 15 and re.search(r"\D", run):  # PHONE-MARK''',
     r'''if False:  # PHONE-MARK'''),
    ("a parenthesis can hide a query", "depth += 1  # DEPTH-MARK", "pass  # DEPTH-MARK"),
    ("protocol-relative links pass", r'''(?<![:\w/])//(?=[\w-]+\.[A-Za-z]{2,})''', r'''(?<![:\w/])//(?=ZZZ)'''),
    ("unicode and invisible separators are not normalised", "text = normalize_for_guard(text)  # NORM-MARK",
     "pass  # NORM-MARK"),
    ("regrouped nine-digit identifiers pass", r'''re.compile(r"(?<!\d)\d{3}[ ._/-]\d{2}[ ._/-]\d{4}(?!\d)")),  # LOOSE-MARK''',
     r'''re.compile(r"(?<!\d)\d{3}ZZZ\d{2}ZZZ\d{4}(?!\d)")),  # LOOSE-MARK'''),
    ("multiline header values accepted", "str(v)):  # ONELINE-MARK", "str(v)) and False:  # ONELINE-MARK"),
    ("a published number can be overwritten",
     "os.link(tmp, final)  # EXCL-PUBLISH-MARK",
     "(os.replace(tmp, final), open(tmp, 'w').close())  # EXCL-PUBLISH-MARK"),
    ("a reservation is released by anyone", "if reserve.read_text(encoding=\"ascii\", errors=\"replace\") == token:  # TOKEN-MARK",
     "if True:  # TOKEN-MARK"),
    ("stored goals are not checked on read",
     r'''if not (re.fullmatch(r"G\d+", goal) or''',
     r'''if False and not (re.fullmatch(r"G\d+", goal) or'''),
    ("header whitespace defeats duplicate detection",
     'h = {k: str(v).strip() for k, v in h.items() if v not in (None, "")}  # STRIP-MARK',
     'h = {k: v for k, v in h.items() if v not in (None, "")}  # STRIP-MARK'),
    ("a stale snapshot can win", "if compute() == text:  # CONVERGE-MARK", "if True:  # CONVERGE-MARK"),
    ("the duplicate key is ambiguous",
     r'''payload = "".join(f"{len(v)}:{v}" for v in fields + [body.strip()])  # KEY-ENCODE-MARK''',
     r'''payload = "|".join(fields + [body.strip()])  # KEY-ENCODE-MARK'''),
    ("the duplicate key is a short hash",
     r'''return hashlib.sha256(payload.encode("utf-8")).hexdigest()  # a full digest: a short one can collide''',
     r'''return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]  # a full digest: a short one can collide'''),
    ("a withdrawn proposal still shows as mutual", "if pid in withdrawn:  # WITHDRAWN-PROP-MARK",
     "if False:  # WITHDRAWN-PROP-MARK"),
    ("the body is cut at a marker line",
     'f"{flag}\\n\\n{m.body.strip()}\\n"  # BODY-MARK',
     'f"{flag}\\n\\n{m.text.split(MESSAGE_START + chr(10), 1)[-1].strip()}\\n"  # BODY-MARK'),
    ("a cursor can move backwards", "n = max(n, read_cursor(root, side))  # MONOTONIC-MARK",
     "pass  # MONOTONIC-MARK"),
    ("numbers can be reused below the maximum", "n = max(taken | {0}) + 1  # MONOTONIC-NUMBER-MARK",
     "n = next((i for i in range(1, max(taken | {0}) + 2) if i not in taken), 1)  # MONOTONIC-NUMBER-MARK"),
    ("a gap blocks ack forever", "skipped.append(f\"{PREFIX[OTHER[me]]}-{n:04d}\")  # GAP-SKIP-MARK",
     "raise Refused([\"missing\"])  # GAP-SKIP-MARK"),
    ("ack steps over a number still being written", "if age is not None and age <= RESERVE_STALE_SECONDS:  # GAP-INFLIGHT-MARK",
     "if False:  # GAP-INFLIGHT-MARK"),
    ("a withdrawn newest agreement revives an older one", "if m.id in withdrawn:  # LATEST-FIRST-MARK",
     "if False:  # LATEST-FIRST-MARK"),
    ("ack accepts a message that does not exist", "if target not in theirs:  # TARGET-EXISTS-MARK",
     "if False:  # TARGET-EXISTS-MARK"),
    ("a late arrival into a stepped-over gap is hidden", "or m.id in late]  # LATE-SHOWN-MARK",
     "]  # LATE-SHOWN-MARK"),
    ("a late arrival is not shown by read", "or m.id in late]  # LATE-READ-MARK", "]  # LATE-READ-MARK"),
    ("a malformed link crashes the reader", "except ValueError:  # MALFORMED-URL-MARK",
     "except KeyError:  # MALFORMED-URL-MARK"),
    ("GOALS.md is not checked for redirection", 'for name in ("GOALS.md", "guard-local.txt", "AGREED.md")]  # FILES-MARK',
     'for name in ("guard-local.txt", "AGREED.md")]  # FILES-MARK'),
    ("an allowed name hides a longer file name",
     r'''re.escape(n) + r"(?=\s|\Z|[,;)\]}'\"]|[.:!?](?:\s|\Z))",  # NAME-END-MARK''',
     r'''re.escape(n) + r"(?![\w])",  # NAME-END-MARK'''),
    ("a dangling link is not a redirection", "if os.path.lexists(p) and is_reparse(p):  # LEXISTS-MARK",
     "if p.exists() and is_reparse(p):  # LEXISTS-MARK"),
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
