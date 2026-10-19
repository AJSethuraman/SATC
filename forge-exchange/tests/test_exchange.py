"""Tests for exchange.py. Standard library only: `python -m unittest` runs them.

Every guard rule has a test that can fail for the reason its name gives, and
mutation_check.py breaks each rule on purpose to prove it. Identifier-shaped
strings are assembled at run time so this file holds none (a repo-wide scan for
them should stay quiet).
"""

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SRC = Path(os.environ.get("EXCHANGE_SRC", HERE.parent / "exchange.py"))
spec = importlib.util.spec_from_file_location("exchange", SRC)
ex = importlib.util.module_from_spec(spec)
sys.modules["exchange"] = ex
spec.loader.exec_module(ex)

SSN = "123" + "-" + "45" + "-" + "6789"
EIN = "12" + "-" + "3456789"
LONG = "1234" + "56789" + "012"
MAIL = "someone" + "@" + "example" + ".com"
PHONE = "216" + "-" + "555" + "-" + "0142"


def run(root, argv, stdin=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ex.main(["--root", str(root)] + list(argv), stdin=stdin)
    return code, out.getvalue(), err.getvalue()


def post(root, me, body, kind="note", goal="G2", mode="satc", about="test", **kw):
    argv = ["post", "--as", me, "--kind", kind, "--goal", goal, "--mode", mode,
            "--about", about]
    for k, v in kw.items():
        argv += ["--" + k.replace("_", "-"), v]
    return run(root, argv, stdin=body)


FINDING = ("Source evidence: the file read\nReproduction evidence: the printed "
           "result\nExpected: A\nActual: B\nUntested boundary: none\n"
           "Owning project: example\n")
WORK_EXTRA = ("Source version: abc1234\nInputs: a safe fixture\nEnvironment: "
              "python 3.12\nMethod: the named command\nLimitations: synthetic\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="exch-")
        self.root = Path(self.tmp) / "exchange"
        code, out, err = run(self.root, ["init"])
        self.assertEqual(code, 0, err)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def snapshot(self):
        snap = {}
        for p in sorted(self.root.rglob("*")):
            if p.is_file():
                st = p.stat()
                snap[str(p.relative_to(self.root))] = (st.st_size, st.st_mtime_ns)
        return snap


class TestGuardShapes(Base):
    def refused(self, text):
        return ex.guard(text, root=self.root, label="t")

    def test_ssn_shape_is_refused(self):
        self.assertTrue(self.refused("see " + SSN))

    def test_ein_shape_is_refused(self):
        self.assertTrue(self.refused("see " + EIN))

    def test_long_digit_run_is_refused(self):
        self.assertTrue(self.refused("acct " + LONG))

    def test_grouped_digits_are_refused(self):
        self.assertTrue(self.refused("acct 1234 5678 9012"))

    def test_email_is_refused(self):
        self.assertTrue(self.refused("write to " + MAIL))

    def test_phone_is_refused(self):
        self.assertTrue(self.refused("call " + PHONE))

    def test_phone_forms_with_a_tight_bracket_are_caught(self):
        # Codex: "(ddd)ddd-dddd" and country-prefixed forms slipped through,
        # because the closing bracket broke the digit-run rule and the phone
        # rule demanded a separator after it.
        # (dotted "216.555.0142" is the form only the plain phone rule catches:
        # the digit-run rule joins groups with spaces and dashes, not dots.)
        for text in ("call (216)555" + "-" + "0142", "call +1 (216)555" + "-" + "0142",
                     "call (216)555" + "0142", "call 1(216)555" + "-" + "0142",
                     "call 216" + "." + "555" + "." + "0142"):
            found = self.refused(text)
            self.assertTrue(any("phone" in f.what for f in found), text)
        # and ordinary things in brackets are not phone numbers
        for text in ("(see section 4.9) and (A)", "version (3.12) of (112) checks"):
            self.assertEqual(self.refused(text), [], text)

    def test_a_bracketed_phone_is_caught_by_the_phone_rule_itself(self):
        # "(216) 555-0142" is too short for the digit-run rule, so only the
        # phone rule can refuse it. Without this case that rule was decoration.
        found = self.refused("call (216) 555" + "-" + "0142")
        self.assertTrue(any("phone" in f.what for f in found))

    def test_protected_places_are_refused(self):
        # Check the REASON, not only the refusal: the file-extension rule would
        # refuse some of these anyway, which hid the protected-places rule.
        cases = (("vault" + ".key", "the vault key"),
                 ("leads" + ".xlsx", "the leads workbook"),
                 ("C:\\x\\engagements\\2026", "the engagements folder"),
                 ("C:\\a\\build\\data\\x", "the live data folders"),
                 ("C:\\a\\satc_vault.db", "a path to a database file"))
        for text, reason in cases:
            reasons = " | ".join(f.what for f in self.refused(text))
            self.assertIn(reason, reasons, text)

    def test_data_file_name_is_refused_unless_listed(self):
        self.assertTrue(self.refused("the file Smith_2024.pdf"))
        self.assertTrue(self.refused("the file report.xlsx"))
        self.assertFalse(self.refused("the file satc_vault.db holds the vault"))
        self.assertFalse(self.refused("the file satc_mart.db"))

    def test_bare_extension_and_code_names_pass(self):
        self.assertFalse(self.refused("the .xlsx files, exchange.py and GOALS.md"))

    def test_links(self):
        self.assertFalse(self.refused("see https://github.com/AJSethuraman/SATC/pull/456"))
        self.assertFalse(self.refused("see https://satcllp.com/"))
        self.assertTrue(self.refused("see https://example.org/page"))
        self.assertTrue(self.refused("see https://satcllp.com/?name=x"))
        self.assertFalse(self.refused("see https://github.com/AJSethuraman/SATC/blob/main/CLAUDE.md#L953"))
        self.assertTrue(self.refused("see https://github.com/AJSethuraman/SATC/blob/main/CLAUDE.md#some-text"))
        self.assertTrue(self.refused("see https://github.com/other/repo"))

    def test_local_deny_list_applies(self):
        self.assertTrue(self.refused("see the real-sample-proof folder"))

    def test_control_characters_are_refused(self):
        self.assertTrue(self.refused("a\x00b"))

    def test_a_refusal_never_repeats_the_value(self):
        code, out, err = run(self.root, ["check"], stdin="note " + SSN + " " + MAIL + " " + LONG)
        self.assertEqual(code, 2)
        for secret in (SSN, MAIL, LONG):
            self.assertNotIn(secret, err + out)
        self.assertIn("line 1", err)

    def test_benign_text_is_not_a_false_alarm(self):
        benign = [
            "2026-10-18 and 2026-10-17 12", "commit 0571de44f1b2af24909289c390b24648eb34e0f1",
            "B-0007 and R-0004", "PR 456, 112 synthetic checks, 1,434 passed",
            "17/17, 11/11 and 20/20 checks", "version 3.12.10 of Python",
            "docs/PLAN-bassy-and-rev-on-the-forge.md section 4.3",
        ]
        for text in benign:
            self.assertEqual(self.refused(text), [], text)

    def test_shapes_match_the_repo_tins_module(self):
        tins = HERE.parent.parent / "client-documents" / "tins.py"
        if not tins.is_file():
            self.skipTest("client-documents/tins.py not checked out here; "
                          "the parity check was NOT run")
        s = importlib.util.spec_from_file_location("tins", tins)
        m = importlib.util.module_from_spec(s)
        sys.modules["tins"] = m
        s.loader.exec_module(m)
        self.assertEqual([(k, r.pattern) for k, r in m.SHAPES],
                         [(k, r.pattern) for k, r in ex.SHAPES])


class TestPostRules(Base):
    def test_a_good_note_posts_and_is_numbered(self):
        code, out, err = post(self.root, "bassy", "Hello there.")
        self.assertEqual((code, out.strip()), (0, "posted B-0001"), err)
        self.assertEqual(post(self.root, "bassy", "A second note.")[1].strip(), "posted B-0002")

    def test_missing_goal_or_mode_is_refused(self):
        code, _, err = run(self.root, ["post", "--as", "bassy", "--kind", "note",
                                       "--mode", "satc", "--about", "t"], stdin="x")
        self.assertEqual(code, 2)
        self.assertIn("goal", err)
        code, _, err = run(self.root, ["post", "--as", "bassy", "--kind", "note",
                                       "--goal", "G1", "--about", "t"], stdin="x")
        self.assertEqual(code, 2)
        self.assertIn("mode", err)

    def test_unknown_goal_is_refused_but_supporting_with_reason_passes(self):
        self.assertEqual(post(self.root, "bassy", "x", goal="G9")[0], 2)
        self.assertEqual(post(self.root, "bassy", "x", goal="supporting:")[0], 2)
        self.assertEqual(post(self.root, "bassy", "x",
                              goal="supporting: fixing the terminal route")[0], 0)

    def test_there_is_no_kind_for_a_request_to_run(self):
        code, _, err = post(self.root, "rev", "please run this", kind="run")
        self.assertEqual(code, 2)
        self.assertIn("no kind for a request to run", err)

    def test_finding_needs_evidence_and_the_labelled_lines(self):
        self.assertEqual(post(self.root, "rev", "just a claim", kind="finding")[0], 2)
        self.assertEqual(post(self.root, "rev", FINDING, kind="finding")[0], 2)  # no evidence
        code, _, err = post(self.root, "rev", "A claim with no labelled lines.",
                            kind="finding", evidence="a file and a result")
        self.assertEqual(code, 2)  # evidence given, labelled lines missing
        self.assertIn("labelled lines", err)
        self.assertEqual(post(self.root, "rev", FINDING, kind="finding",
                              evidence="a file and a result")[0], 0)

    def test_work_mode_finding_needs_the_proof_statement(self):
        self.assertEqual(post(self.root, "rev", FINDING, kind="finding", mode="work",
                              evidence="x")[0], 2)
        self.assertEqual(post(self.root, "rev", FINDING + WORK_EXTRA, kind="finding",
                              mode="work", evidence="x")[0], 0)

    def test_disagreement_needs_a_conviction_line(self):
        self.assertEqual(post(self.root, "rev", "I differ", kind="disagreement")[0], 2)
        self.assertEqual(post(self.root, "rev", "I differ", kind="disagreement",
                              convictions="none")[0], 0)

    def test_reply_must_name_a_real_message(self):
        self.assertEqual(post(self.root, "bassy", "re", re="R-0099")[0], 2)

    def test_identical_post_is_not_posted_twice(self):
        post(self.root, "bassy", "Same words.")
        code, out, _ = post(self.root, "bassy", "Same words.")
        self.assertEqual(code, 0)
        self.assertIn("not posted: identical to B-0001", out)
        self.assertEqual(len(list((self.root / "from-bassy").glob("B-*.md"))), 1)

    def test_a_taken_number_is_skipped_not_overwritten(self):
        post(self.root, "bassy", "one")
        (self.root / "from-bassy" / ".B-0002.reserve").write_text("", encoding="utf-8")
        self.assertEqual(post(self.root, "bassy", "two")[1].strip(), "posted B-0003")

    def test_body_with_identifiers_is_refused_and_nothing_is_written(self):
        code, _, err = post(self.root, "rev", "number " + SSN)
        self.assertEqual(code, 2)
        self.assertEqual(list((self.root / "from-rev").glob("R-*.md")), [])
        self.assertNotIn(SSN, err)

    def test_a_client_name_is_allowed_in_the_exchange(self):
        self.assertEqual(post(self.root, "rev", "Mr Example Person's return is late.")[0], 0)

    def test_posted_file_carries_the_goals_banner(self):
        post(self.root, "bassy", "Body text.")
        text = (self.root / "from-bassy" / "B-0001.md").read_text(encoding="utf-8")
        self.assertIn("G2. Creating and connecting processes", text)
        self.assertIn("READ:", text)

    def test_post_refreshes_resume_file(self):
        post(self.root, "bassy", "Body text.")
        self.assertTrue((self.root / "from-bassy" / "RESUME.md").is_file())


class TestCodexFindingsOnPR458(Base):
    def test_a_repeat_with_a_withdrawal_is_not_swallowed_as_a_duplicate(self):
        post(self.root, "bassy", "Need a decision.", kind="owner-item")
        post(self.root, "bassy", "Same words.", kind="note")
        code, out, _ = post(self.root, "bassy", "Same words.", kind="note", withdraws="B-0001")
        self.assertEqual(code, 0)
        self.assertIn("posted B-0003", out)
        self.assertIn("Owner items open: 0", run(self.root, ["owner-items"])[1])

    def test_a_metadata_only_difference_is_not_a_duplicate(self):
        post(self.root, "bassy", "Same words.", goal="G1")
        code, out, _ = post(self.root, "bassy", "Same words.", goal="G2")
        self.assertIn("posted B-0002", out)

    def test_a_multiline_header_value_is_refused_and_nothing_is_written(self):
        code, _, err = post(self.root, "bassy", "x", about="topic\ngoal: G9")
        self.assertEqual(code, 2)
        self.assertIn("one line", err)
        self.assertEqual(list((self.root / "from-bassy").glob("B-*.md")), [])

    def test_an_oversize_hand_saved_body_is_withheld(self):
        body = "word " * 1500  # 7,500 characters
        (self.root / "from-rev" / "R-0001.md").write_text(
            "id: R-0001\nfrom: rev\nkind: note\nabout: x\ngoal: G1\nmode: satc\n\n" + body,
            encoding="utf-8")
        shown = run(self.root, ["read", "--as", "bassy"])[1]
        self.assertIn("WITHHELD R-0001", shown)
        self.assertIn("size limit", shown)

    def test_a_huge_file_is_withheld_without_being_read(self):
        (self.root / "from-rev" / "R-0001.md").write_text("x" * 200000, encoding="utf-8")
        called = []
        real = Path.read_bytes
        with mock.patch.object(Path, "read_bytes",
                               lambda p: (called.append(p) or real(p))):
            shown = run(self.root, ["read", "--as", "bassy"])[1]
        self.assertIn("not read", shown)
        self.assertEqual([c for c in called if c.name == "R-0001.md"], [])


class TestCodexSecondPassOnPR458(Base):
    def test_a_withdrawal_cannot_point_at_a_later_message(self):
        # Codex: a hand-saved B-0001 withdrawing B-0002 would silently hide the
        # owner item that B-0002 later becomes.
        (self.root / "from-bassy" / "B-0001.md").write_text(
            "id: B-0001\nfrom: bassy\nkind: note\nabout: x\ngoal: G1\nmode: satc\n"
            "withdraws: B-0002\n\nhand saved\n", encoding="utf-8")
        # B-0002 is hand-saved too, so the allocator (which now refuses to reuse a
        # number a stored message names) is not what protects it: only the read-side
        # ordering rule is.
        (self.root / "from-bassy" / "B-0002.md").write_text(
            "id: B-0002\nfrom: bassy\nkind: owner-item\nabout: x\ngoal: G1\nmode: satc\n"
            "\nNeed a decision.\n", encoding="utf-8")
        self.assertIn("Owner items open: 1", run(self.root, ["owner-items"])[1])

    def test_a_withdrawal_of_an_earlier_own_message_still_works(self):
        post(self.root, "bassy", "Need a decision.", kind="owner-item")
        post(self.root, "bassy", "Answered; closing.", withdraws="B-0001")
        self.assertIn("Owner items open: 0", run(self.root, ["owner-items"])[1])

    def test_grouped_digits_joined_by_any_punctuation_are_refused(self):
        for text in ("1234.5678.9012.3456", "123,456" + ",789", "1234/5678/9012",
                     "1234_5678_9012"):
            self.assertTrue(ex.guard("acct " + text, label="t"), text)

    def test_ordinary_dotted_and_comma_numbers_are_not_false_alarms(self):
        for text in ("version 3.12.10", "1,434 passed", "2026.10.18", "17/17 checks",
                     "about 112,000 characters", "PR 456 and 458"):
            self.assertEqual(ex.guard(text, label="t"), [], text)

    def test_a_path_that_ends_at_the_engagements_folder_is_refused(self):
        for text in ("C:\\Clients\\engagements", "/srv/engagements",
                     "C:\\Clients\\engagements\\2026"):
            reasons = " | ".join(f.what for f in ex.guard(text, label="t"))
            self.assertIn("the engagements folder", reasons, text)
        # naming the folder in prose is fine (the public docs do)
        self.assertEqual(ex.guard("the engagements folder holds real clients", label="t"), [])

    def test_a_lone_carriage_return_is_refused_but_crlf_is_not(self):
        self.assertTrue(ex.guard("safe text\roverwrite", label="t"))
        self.assertEqual(ex.guard("line one\r\nline two", label="t"), [])


class TestCodexThirdPassOnPR458(Base):
    def test_international_phone_numbers_are_refused(self):
        for text in ("call +44 20 7946 0958", "call +61 2 9374 4000", "call +33 1 23 45 67 89"):
            found = ex.guard(text, label="t")
            self.assertTrue(any("phone" in f.what for f in found), text)

    def test_plus_signs_in_ordinary_text_are_not_phone_numbers(self):
        for text in ("17+ tests and C++ 20", "+3 more tests", "the +1 vote", "a +12 point change"):
            self.assertEqual(ex.guard(text, label="t"), [], text)

    def test_protocol_relative_and_other_scheme_links_go_through_the_allow_list(self):
        refused = ["[record](//evil.example/path?client=Jane)",
                   "[record](//evil.example/path)",
                   "see ftp://github.com/AJSethuraman/SATC",
                   "see HTTPS://evil.example/x"]
        for text in refused:
            self.assertTrue(ex.guard(text, label="t"), text)
        self.assertEqual(ex.guard("[ok](//github.com/AJSethuraman/SATC/pull/1)", label="t"), [])
        # an ordinary code comment is not a link
        self.assertEqual(ex.guard("x = 1  // a comment, not a link", label="t"), [])

    def test_a_dead_posters_reservation_does_not_leave_a_permanent_gap(self):
        post(self.root, "bassy", "one")
        stale = self.root / "from-bassy" / ".B-0002.reserve"
        stale.write_text("", encoding="utf-8")
        old = time.time() - 3600
        os.utime(stale, (old, old))
        self.assertEqual(post(self.root, "bassy", "two")[1].strip(), "posted B-0002")
        self.assertFalse(stale.exists())
        run(self.root, ["ack", "--as", "rev", "B-0002"])  # no gap, so the cursor can pass

    def test_a_live_posters_fresh_reservation_is_still_respected(self):
        post(self.root, "bassy", "one")
        (self.root / "from-bassy" / ".B-0002.reserve").write_text("", encoding="utf-8")
        self.assertEqual(post(self.root, "bassy", "two")[1].strip(), "posted B-0003")


class TestCodexFourthPassOnPR458(Base):
    def test_a_link_with_balanced_parentheses_cannot_hide_a_query(self):
        hidden = "[x](https://github.com/AJSethuraman/SATC/foo(bar)?client=Jane)"
        found = ex.guard(hidden, label="t")
        self.assertTrue(any("query string" in f.what for f in found))
        # a parenthesis in an allowed path, with no query, is fine
        self.assertEqual(ex.guard("see https://github.com/AJSethuraman/SATC/foo(bar)", label="t"), [])
        self.assertEqual(ex.guard("(see https://github.com/AJSethuraman/SATC/pull/1)", label="t"), [])

    def test_the_guard_is_linear_on_long_unbroken_text(self):
        # Found while fixing this pass: the email and link patterns rescanned a long
        # unbroken run from every character, so 30,000 characters took about 8
        # seconds per guard pass and a hand-saved 39 KB file could stall status/read.
        for label, text in (("x", "x" * 39000), ("a1-", "a1-" * 13000),
                            ("dots", "a." * 19500), ("scheme-ish", "ab+" * 13000)):
            t0 = time.time()
            ex.guard(text, label="t")
            self.assertLess(time.time() - t0, 1.5, label)

    def test_detection_survives_the_speed_fix(self):
        for text in ("a@b.co", "write to someone.else@example.org now",
                     "see https://evil.example/x", "see www.evil.example", "//evil.example/p"):
            self.assertTrue(ex.guard(text, label="t"), text)

    def test_a_message_the_reader_would_refuse_is_never_written(self):
        code, _, err = post(self.root, "bassy", "\u65e5" * 6000, about="x" * 30000)
        self.assertEqual(code, 2)
        self.assertIn("bytes", err)
        self.assertEqual(list((self.root / "from-bassy").glob("B-*.md")), [])
        self.assertEqual(list((self.root / "from-bassy").glob(".B-*")), [])  # reservation released

    def test_a_reagreement_after_an_edit_restores_the_mutual_position(self):
        post(self.root, "bassy", "Proposal: one writer per file.", kind="suggestion")
        prop = self.root / "from-bassy" / "B-0001.md"
        fp1 = ex.sha8(prop.read_text(encoding="utf-8"))
        post(self.root, "rev", "I agree.", kind="agreement", proposal="B-0001#" + fp1)
        post(self.root, "bassy", "I agree.", kind="agreement", proposal="B-0001#" + fp1)
        prop.write_text(prop.read_text(encoding="utf-8") + "Edited.\n", encoding="utf-8")
        self.assertIn("STALE", ex.view_agreed(self.root))
        fp2 = ex.sha8(prop.read_text(encoding="utf-8"))
        post(self.root, "rev", "I agree to the edited one.", kind="agreement", proposal="B-0001#" + fp2)
        post(self.root, "bassy", "I agree to the edited one.", kind="agreement", proposal="B-0001#" + fp2)
        out = ex.view_agreed(self.root)
        self.assertNotIn("STALE", out)
        self.assertIn("mutual", out)

    def test_numbering_stops_before_an_id_the_reader_cannot_parse(self):
        # The real limit is 9999 (the reader accepts four digits). Use a small limit so
        # the test can fill every slot; with gaps filled from the lowest free number,
        # a lone high id no longer means the numbers are used up.
        with mock.patch.object(ex, "MAX_MESSAGE_NUMBER", 3):
            for n in (1, 2, 3):
                (self.root / "from-bassy" / f"B-000{n}.md").write_text("x", encoding="utf-8")
            code, _, err = post(self.root, "bassy", "one more")
        self.assertEqual(code, 2)
        self.assertIn("used up", err)
        self.assertEqual(sorted(p.name for p in (self.root / "from-bassy").glob("B-*")),
                         ["B-0001.md", "B-0002.md", "B-0003.md"])


class TestCodexFifthPassOnPR458(Base):
    def test_national_and_international_phone_formats_are_all_one_rule(self):
        cases = ("call (020) 7946 0958", "call 020 7946 0958", "call +44 20 7946 0958",
                 "call +61 2 9374 4000", "call +33 1 23 45 67 89",
                 "call (216)555" + "-" + "0142", "call 216" + "." + "555" + "." + "0142",
                 "call +1 (216)555" + "-" + "0142")
        for text in cases:
            found = ex.guard(text, label="t")
            self.assertTrue(any("phone" in f.what for f in found), text)

    def test_ordinary_numbers_are_not_phone_numbers(self):
        for text in ("2026-10-18 12:00 and 3.12.10", "(see section 4.9) and (A)", "1,434 passed of 1,436",
                     "17+ tests and C++ 20", "+3 more tests", "PR 456, 112 checks", "84 tests, 50 mutations"):
            self.assertEqual(ex.guard(text, label="t"), [], text)

    def test_nested_parentheses_cannot_hide_a_query(self):
        for text in ("[x](https://github.com/AJSethuraman/SATC/foo((bar))?client=Jane)",
                     "[x](https://github.com/AJSethuraman/SATC/a(b(c(d)))?client=Jane)",
                     "[x](https://github.com/AJSethuraman/SATC/foo(bar)?client=Jane)"):
            found = ex.guard(text, label="t")
            self.assertTrue(any("query string" in f.what for f in found), text)
        self.assertEqual(ex.guard("see https://github.com/AJSethuraman/SATC/a(b(c))", label="t"), [])

    def test_a_gap_left_by_a_dead_poster_is_not_back_filled(self):
        # Numbers are chronology (withdrawal order and "latest agreement" rely on it),
        # so a lower number is never handed out after a higher one exists.
        for n in (1, 3):
            (self.root / "from-bassy" / f"B-000{n}.md").write_text("x", encoding="utf-8")
        self.assertEqual(post(self.root, "bassy", "after the gap")[1].strip(), "posted B-0004")

    def test_a_live_reservation_in_the_gap_is_respected(self):
        for n in (1, 3):
            (self.root / "from-bassy" / f"B-000{n}.md").write_text("x", encoding="utf-8")
        (self.root / "from-bassy" / ".B-0002.reserve").write_text("", encoding="utf-8")
        self.assertEqual(post(self.root, "bassy", "next free")[1].strip(), "posted B-0004")

    def test_duplicate_detection_is_not_fooled_by_the_delimiter(self):
        self.assertIn("posted B-0001", post(self.root, "bassy", "Same words.", about="a", evidence="|")[1])
        code, out, _ = post(self.root, "bassy", "Same words.", about="a|")
        self.assertIn("posted B-0002", out)


class TestCodexSixthPassOnPR458(Base):
    def test_unicode_spaces_cannot_hide_a_phone_number(self):
        for text in ("call +44\u00a020\u00a07946\u00a00958", "call (020)\u00a07946\u00a00958",
                     "call +44\u200b20\u200b7946\u200b0958", "call +44\u202f20\u202f7946\u202f0958",
                     "call \uff10\uff12\uff10 \uff17\uff19\uff14\uff16 \uff10\uff19\uff15\uff18"):
            found = ex.guard(text, label="t")
            self.assertTrue(any("phone" in f.what for f in found), repr(text))

    def test_regrouped_nine_digit_identifiers_are_refused(self):
        for text in ("id 123 45 6789", "id 123.45.6789", "id 12 3456789", "id 12.3456789",
                     "id 123/45/6789", "id 123_45_6789"):
            self.assertTrue(ex.guard(text, label="t"), text)

    def test_ordinary_numbers_survive_the_normalising_rules(self):
        for text in ("2026-10-18 12:00 and 3.12.10", "version 3.12.10", "1,434 passed", "PR 456 and 458",
                     "112 synthetic checks, 84 tests, 50 mutations", "10/18/2026"):
            self.assertEqual(ex.guard(text, label="t"), [], text)

    def test_unicode_line_separators_in_a_header_are_refused_and_nothing_is_written(self):
        for sep in ("\x85", "\u2028", "\u2029", "\x0b", "\x0c"):
            code, _, err = post(self.root, "bassy", "x", about="ok" + sep + "kind: finding")
            self.assertEqual(code, 2, repr(sep))
        self.assertEqual(list((self.root / "from-bassy").glob("B-*.md")), [])

    def test_a_body_with_a_unicode_line_separator_is_refused(self):
        self.assertEqual(post(self.root, "bassy", "line one\u2028line two")[0], 2)

    def test_a_number_that_a_stored_message_points_at_is_not_reused(self):
        (self.root / "from-bassy" / "B-0001.md").write_text("x", encoding="utf-8")
        (self.root / "from-bassy" / "B-0003.md").write_text(
            "id: B-0003\nfrom: bassy\nkind: note\nabout: x\ngoal: G1\nmode: satc\n"
            "withdraws: B-0002\n\nhand saved\n", encoding="utf-8")
        # B-0002 is missing but already named by B-0003, so it must not be handed out
        self.assertEqual(post(self.root, "bassy", "next")[1].strip(), "posted B-0004")


class TestCodexSeventhPassOnPR458(Base):
    def test_a_writer_that_lost_the_number_overwrites_nothing(self):
        # Another poster publishes B-0001 between our temporary write and our publish.
        real_link = os.link
        state = {"done": False}

        def thief(src, dst):
            if not state["done"]:
                state["done"] = True
                Path(dst).write_text("THIEFS-MESSAGE", encoding="utf-8")
            return real_link(src, dst)

        with mock.patch.object(ex.os, "link", thief):
            out = post(self.root, "bassy", "mine")[1]
        self.assertIn("posted B-0002", out)
        self.assertEqual((self.root / "from-bassy" / "B-0001.md").read_text(encoding="utf-8"),
                         "THIEFS-MESSAGE")
        self.assertIn("mine", (self.root / "from-bassy" / "B-0002.md").read_text(encoding="utf-8"))
        self.assertEqual([p.name for p in (self.root / "from-bassy").glob(".B-*")], [])  # no litter

    def test_a_reservation_that_is_not_ours_is_left_alone(self):
        r = self.root / "from-bassy" / ".B-0001.reserve"
        r.write_text("their-token", encoding="utf-8")
        ex.release_reservation(r, "my-token")
        self.assertTrue(r.exists())
        ex.release_reservation(r, "their-token")
        self.assertFalse(r.exists())

    def test_a_stored_message_with_a_nonsense_goal_is_withheld(self):
        (self.root / "from-rev" / "R-0001.md").write_text(
            "id: R-0001\nfrom: rev\nkind: note\nabout: x\ngoal: banana\nmode: satc\n\nhi\n",
            encoding="utf-8")
        self.assertIn("goal line", run(self.root, ["read", "--as", "bassy"])[1])

    def test_stored_goals_are_checked_by_shape_not_by_current_membership(self):
        # Checking membership in GOALS.md would orphan old messages when the owner
        # edits their goals. Shape only: a G number, or "supporting:" with a reason.
        for goal in ("G999", "supporting: an old message about a retired goal"):
            (self.root / "from-rev" / "R-0001.md").write_text(
                "id: R-0001\nfrom: rev\nkind: note\nabout: x\ngoal: " + goal +
                "\nmode: satc\n\nhi\n", encoding="utf-8")
            self.assertIn("DATA FROM REV", run(self.root, ["read", "--as", "bassy"])[1], goal)


class TestCodexEighthPassOnPR458(Base):
    def test_header_whitespace_does_not_defeat_duplicate_detection(self):
        self.assertIn("posted B-0001", post(self.root, "bassy", "Same words.", about=" x ")[1])
        code, out, _ = post(self.root, "bassy", "Same words.", about=" x ")
        self.assertIn("not posted: identical to B-0001", out)
        self.assertEqual(len(list((self.root / "from-bassy").glob("B-*.md"))), 1)
        # and the stored header is the trimmed value
        self.assertIn("about: x\n", (self.root / "from-bassy" / "B-0001.md").read_text(encoding="utf-8"))


class TestCodexNinthPassOnPR458(Base):
    def test_two_different_messages_whose_short_hashes_collide_are_both_posted(self):
        # Codex: a 32-bit key silently discarded a different message. Find a real
        # collision on the first 8 hex digits and check the full digest tells them apart.
        h = {"kind": "note", "about": "collision", "goal": "G1", "mode": "satc"}
        seen = {}
        pair = None
        for i in range(600000):
            body = "safe collision candidate %d" % i
            k = ex.content_key(h, body)
            if k[:8] in seen:
                pair = (seen[k[:8]], body)
                break
            seen[k[:8]] = body
        self.assertIsNotNone(pair, "no 32-bit collision found to test with")
        self.assertEqual(len(ex.content_key(h, "x")), 64)
        self.assertNotEqual(ex.content_key(h, pair[0]), ex.content_key(h, pair[1]))
        for body in pair:
            code, out, _ = post(self.root, "bassy", body, about="collision", goal="G1")
            self.assertIn("posted", out)
            self.assertNotIn("identical", out)
        self.assertEqual(len(list((self.root / "from-bassy").glob("B-*.md"))), 2)

    def test_a_stale_resume_snapshot_cannot_win(self):
        real = ex.view_resume
        calls = {"n": 0}

        def racing(root, me):
            text = real(root, me)
            calls["n"] += 1
            if calls["n"] == 1:
                post(self.root, "bassy", "A second message lands mid-write.")
            return text

        with mock.patch.object(ex, "view_resume", racing):
            post(self.root, "bassy", "The first message.")
        resume = (self.root / "from-bassy" / "RESUME.md").read_text(encoding="utf-8")
        self.assertIn("B-0002", resume)


class TestCodexTenthPassOnPR458(Base):
    def test_a_withdrawn_proposal_is_not_shown_as_a_mutual_position(self):
        post(self.root, "bassy", "Proposal: one writer per file.", kind="suggestion")
        fp = ex.sha8((self.root / "from-bassy" / "B-0001.md").read_text(encoding="utf-8"))
        post(self.root, "rev", "I agree.", kind="agreement", proposal="B-0001#" + fp)
        post(self.root, "bassy", "I agree.", kind="agreement", proposal="B-0001#" + fp)
        self.assertIn("mutual", ex.view_agreed(self.root))
        post(self.root, "bassy", "I withdraw that proposal.", withdraws="B-0001")
        out = ex.view_agreed(self.root)
        self.assertIn("WITHDRAWN", out)
        self.assertNotIn("mutual;", out)

    def test_a_body_containing_the_marker_line_is_shown_whole(self):
        (self.root / "from-rev" / "R-0001.md").write_text(
            "id: R-0001\nfrom: rev\nkind: note\nabout: x\ngoal: G1\nmode: satc\n\n"
            "FIRST-PART\n---message---\nSECOND-PART\n", encoding="utf-8")
        shown = run(self.root, ["read", "--as", "bassy"])[1]
        self.assertIn("FIRST-PART", shown)
        self.assertIn("SECOND-PART", shown)

    def test_a_cursor_never_moves_backwards(self):
        ex.write_cursor(self.root, "bassy", 5)
        ex.write_cursor(self.root, "bassy", 2)  # an older acknowledgement finishing last
        self.assertEqual(ex.read_cursor(self.root, "bassy"), 5)


class TestCodexEleventhPassOnPR458(Base):
    def test_withdrawing_the_newest_agreement_does_not_revive_the_older_one(self):
        post(self.root, "bassy", "Proposal: one writer per file.", kind="suggestion")
        fp = ex.sha8((self.root / "from-bassy" / "B-0001.md").read_text(encoding="utf-8"))
        post(self.root, "bassy", "I agree.", kind="agreement", proposal="B-0001#" + fp)
        post(self.root, "rev", "I agree.", kind="agreement", proposal="B-0001#" + fp)
        post(self.root, "rev", "I agree again, more firmly.", kind="agreement", proposal="B-0001#" + fp)
        self.assertIn("mutual", ex.view_agreed(self.root))
        post(self.root, "rev", "I withdraw my latest agreement.", withdraws="R-0002")
        out = ex.view_agreed(self.root)
        self.assertIn("one side only (bassy)", out)  # rev's older agreement must not come back
        self.assertNotIn("mutual;", out)


class TestCodexTwelfthPassOnPR458(Base):
    def _msg(self, side, n, body="a message"):
        pre = "R" if side == "rev" else "B"
        folder = "from-rev" if side == "rev" else "from-bassy"
        (self.root / folder / f"{pre}-{n:04d}.md").write_text(
            f"id: {pre}-{n:04d}\nfrom: {side}\nkind: note\nabout: x\ngoal: G1\nmode: satc\n\n{body}\n",
            encoding="utf-8")

    def test_ack_refuses_a_target_that_does_not_exist(self):
        self._msg("rev", 1)
        code, _, err = run(self.root, ["ack", "--as", "bassy", "R-9999"])
        self.assertEqual(code, 2)
        self.assertIn("not a message that exists", err)
        self.assertEqual(ex.read_cursor(self.root, "bassy"), 0)  # unchanged

    def test_a_message_published_into_a_stepped_over_gap_is_not_lost(self):
        self._msg("rev", 1)
        self._msg("rev", 3)
        stale = self.root / "from-rev" / ".R-0002.reserve"
        stale.write_text("", encoding="utf-8")
        old = time.time() - 3600
        os.utime(stale, (old, old))
        code, out, _ = run(self.root, ["ack", "--as", "bassy", "R-0003"])
        self.assertEqual(code, 0)
        self.assertIn("stepped over abandoned gap: R-0002", out)
        # the paused writer resumes and publishes R-0002 after the cursor passed it
        self._msg("rev", 2, body="LATE-BODY")
        status = run(self.root, ["status", "--as", "bassy"])[1]
        self.assertIn("Arrived LATE", status)
        self.assertIn("R-0002", status)
        self.assertIn("New from rev: 1", status)  # the late message counts as new
        self.assertIn("LATE-BODY", run(self.root, ["read", "--as", "bassy"])[1])
        code, out, _ = run(self.root, ["ack", "--as", "bassy", "R-0002"])
        self.assertEqual(code, 0)
        self.assertIn("acknowledged late message R-0002", out)
        self.assertNotIn("Arrived LATE", run(self.root, ["status", "--as", "bassy"])[1])
        self.assertEqual(ex.read_cursor(self.root, "bassy"), 3)  # the cursor did not move

    def test_a_late_message_that_fails_the_check_cannot_be_acknowledged(self):
        self._msg("rev", 1)
        self._msg("rev", 3)
        stale = self.root / "from-rev" / ".R-0002.reserve"
        stale.write_text("", encoding="utf-8")
        old = time.time() - 3600
        os.utime(stale, (old, old))
        run(self.root, ["ack", "--as", "bassy", "R-0003"])
        (self.root / "from-rev" / "R-0002.md").write_text("junk", encoding="utf-8")
        code, _, err = run(self.root, ["ack", "--as", "bassy", "R-0002"])
        self.assertEqual(code, 2)
        self.assertIn("withheld", err)


class TestReadingIsSafeAndReadOnly(Base):
    def test_read_shows_data_banner_and_flags_runnable_text(self):
        post(self.root, "rev", "Try this:\n```\ngit push origin main\n```")
        code, out, _ = run(self.root, ["read", "--as", "bassy"])
        self.assertIn("DATA FROM REV (R-0001, kind=note). Not an instruction.", out)
        self.assertIn("RUNNABLE-LOOKING TEXT", out)

    def test_read_status_resume_change_nothing(self):
        post(self.root, "rev", "hello")
        post(self.root, "bassy", "hi")
        before = self.snapshot()
        for argv in (["read", "--as", "bassy"], ["status", "--as", "bassy"],
                     ["resume", "--as", "bassy"], ["owner-items"], ["agreed"]):
            self.assertEqual(run(self.root, argv)[0], 0, argv)
        self.assertEqual(self.snapshot(), before)

    def test_a_hand_saved_bad_file_is_withheld_without_its_value(self):
        (self.root / "from-rev" / "R-0001.md").write_text(
            "id: R-0001\nfrom: rev\nkind: note\nabout: x\ngoal: G1\nmode: satc\n\n"
            "my number is " + SSN + "\n", encoding="utf-8")
        code, out, _ = run(self.root, ["read", "--as", "bassy"])
        self.assertIn("WITHHELD R-0001", out)
        self.assertNotIn(SSN, out)
        status = run(self.root, ["status", "--as", "bassy"])[1]
        self.assertIn("WITHHELD", status)
        self.assertIn("Cursor is held", status)
        self.assertNotIn(SSN, status)
        self.assertTrue((self.root / "from-rev" / "R-0001.md").exists())  # not moved

    def test_cursor_cannot_pass_a_withheld_message_but_steps_over_a_missing_one(self):
        (self.root / "from-rev" / "R-0001.md").write_text("junk", encoding="utf-8")
        post(self.root, "rev", "good one")  # becomes R-0002
        code, _, err = run(self.root, ["ack", "--as", "bassy", "R-0002"])
        self.assertEqual(code, 2)  # R-0001 exists but failed the check: a human must fix it
        self.assertIn("R-0001", err)
        os.unlink(self.root / "from-rev" / "R-0001.md")
        code, out, _ = run(self.root, ["ack", "--as", "bassy", "R-0002"])
        self.assertEqual(code, 0)  # R-0001 is now simply missing, and nobody is writing it
        self.assertIn("stepped over abandoned gap: R-0001", out)

    def test_ack_waits_for_a_number_that_is_still_being_written(self):
        post(self.root, "rev", "one")
        (self.root / "from-rev" / "R-0003.md").write_text("x", encoding="utf-8")
        (self.root / "from-rev" / ".R-0002.reserve").write_text("", encoding="utf-8")  # fresh
        code, _, err = run(self.root, ["ack", "--as", "bassy", "R-0003"])
        self.assertEqual(code, 2)
        self.assertIn("still being written", err)

    def test_ack_steps_over_a_gap_whose_reservation_went_stale(self):
        post(self.root, "rev", "one")
        # R-0003 must be a valid message for ack to pass it
        post(self.root, "rev", "two")
        os.rename(self.root / "from-rev" / "R-0002.md", self.root / "from-rev" / "R-0003.md")
        text = (self.root / "from-rev" / "R-0003.md").read_text(encoding="utf-8").replace("R-0002", "R-0003")
        (self.root / "from-rev" / "R-0003.md").write_text(text, encoding="utf-8")
        stale = self.root / "from-rev" / ".R-0002.reserve"
        stale.write_text("", encoding="utf-8")
        old = time.time() - 3600
        os.utime(stale, (old, old))
        code, out, _ = run(self.root, ["ack", "--as", "bassy", "R-0003"])
        self.assertEqual(code, 0)
        self.assertIn("stepped over abandoned gap: R-0002", out)

    def test_ack_moves_the_cursor_after_good_messages(self):
        post(self.root, "rev", "one")
        post(self.root, "rev", "two")
        self.assertEqual(run(self.root, ["ack", "--as", "bassy", "R-0002"])[0], 0)
        self.assertEqual(ex.read_cursor(self.root, "bassy"), 2)
        self.assertIn("Nothing new", run(self.root, ["read", "--as", "bassy"])[1])

    def test_unexpected_files_are_reported_not_trusted(self):
        (self.root / "from-rev" / "notes.txt").write_text("x", encoding="utf-8")
        self.assertIn("WITHHELD", run(self.root, ["status", "--as", "bassy"])[1])

    def test_leftover_files_show_in_status(self):
        (self.root / "from-bassy" / ".B-0005.tmp").write_text("x", encoding="utf-8")
        self.assertIn(".B-0005.tmp", run(self.root, ["status", "--as", "bassy"])[1])

    def test_the_goals_come_first_in_status_and_resume(self):
        for cmd in ("status", "resume"):
            out = run(self.root, [cmd, "--as", "bassy"])[1]
            self.assertTrue(out.startswith("GOALS (version"), cmd)


class TestNothingIsEchoed(Base):
    """Rev's source-review findings: an odd header key, an odd file name and an
    odd hidden file name were all printed back. None may be."""

    def everything_shown(self):
        return (run(self.root, ["status", "--as", "bassy"])[1] +
                run(self.root, ["read", "--as", "bassy", "--all"])[1] +
                run(self.root, ["resume", "--as", "bassy"])[1])

    def test_an_unknown_header_key_is_not_echoed(self):
        (self.root / "from-rev" / "R-0001.md").write_text(
            "id: R-0001\nfrom: rev\nkind: note\njane_doe_account: 1\n"
            "goal: G1\nmode: satc\n\nx\n", encoding="utf-8")
        shown = self.everything_shown()
        self.assertIn("WITHHELD", shown)
        self.assertNotIn("jane_doe_account", shown)

    def test_an_odd_file_name_is_not_echoed(self):
        (self.root / "from-rev" / "Jane_Doe_return.txt").write_text("x", encoding="utf-8")
        shown = self.everything_shown()
        self.assertIn("WITHHELD unexpected-", shown)
        self.assertNotIn("Jane_Doe", shown)

    def test_an_odd_hidden_file_name_is_not_echoed(self):
        (self.root / "from-rev" / ".Jane_Doe.tmp").write_text("x", encoding="utf-8")
        shown = self.everything_shown()
        self.assertIn("an unrecognised hidden file", shown)
        self.assertNotIn("Jane_Doe", shown)

    def test_the_scripts_own_leftovers_are_still_named(self):
        (self.root / "from-bassy" / ".B-0005.tmp").write_text("x", encoding="utf-8")
        self.assertIn(".B-0005.tmp", self.everything_shown())

    def test_ack_does_not_echo_a_strange_argument(self):
        code, out, err = run(self.root, ["ack", "--as", "bassy", "Jane_Doe_return"])
        self.assertEqual(code, 2)
        self.assertNotIn("Jane_Doe", out + err)


class TestWithdrawalsBelongToTheirAuthor(Base):
    def test_you_cannot_withdraw_the_other_sides_message(self):
        post(self.root, "bassy", "Need the owner to decide.", kind="owner-item")
        code, _, err = post(self.root, "rev", "closing your item", withdraws="B-0001")
        self.assertEqual(code, 2)
        self.assertIn("only withdraw your own", err)
        self.assertIn("Owner items open: 1", run(self.root, ["owner-items"])[1])

    def test_a_hand_saved_cross_withdrawal_counts_for_nothing(self):
        post(self.root, "bassy", "Need the owner to decide.", kind="owner-item")
        post(self.root, "rev", "A first note, so the next number is later than the target.")
        # R-0002 is numbered AFTER B-0001, so only the side rule can stop it
        (self.root / "from-rev" / "R-0002.md").write_text(
            "id: R-0002\nfrom: rev\nkind: note\nabout: x\ngoal: G1\nmode: satc\n"
            "withdraws: B-0001\n\nclosing your item\n", encoding="utf-8")
        self.assertIn("Owner items open: 1", run(self.root, ["owner-items"])[1])

    def test_a_hand_saved_cross_withdrawal_cannot_cancel_the_other_sides_assent(self):
        post(self.root, "bassy", "Proposal.", kind="suggestion")
        fp = ex.sha8((self.root / "from-bassy" / "B-0001.md").read_text(encoding="utf-8"))
        post(self.root, "bassy", "I agree.", kind="agreement", proposal="B-0001#" + fp)
        post(self.root, "rev", "First note.")
        post(self.root, "rev", "Second note, so the hand-saved one is numbered after B-0002.")
        (self.root / "from-rev" / "R-0003.md").write_text(
            "id: R-0003\nfrom: rev\nkind: note\nabout: x\ngoal: G1\nmode: satc\n"
            "withdraws: B-0002\n\nwithdrawing bassy's assent\n", encoding="utf-8")
        self.assertIn("one side only (bassy)", ex.view_agreed(self.root))


class TestThreadsGoalChecksAndOwnerItems(Base):
    def test_goal_check_is_listed_until_answered(self):
        post(self.root, "rev", "Has this drifted from G2?", kind="goal-check")
        out = run(self.root, ["status", "--as", "bassy"])[1]
        self.assertIn("Unanswered goal-checks come first: R-0001", out)
        post(self.root, "bassy", "No; here is the checkpoint.", re="R-0001")
        out = run(self.root, ["status", "--as", "bassy"])[1]
        self.assertNotIn("Unanswered goal-checks", out)

    def test_owner_items_stay_open_until_withdrawn(self):
        post(self.root, "bassy", "Need the owner to decide X.", kind="owner-item")
        self.assertIn("Owner items open: 1", run(self.root, ["owner-items"])[1])
        post(self.root, "bassy", "Owner answered; closing.", withdraws="B-0001")
        self.assertIn("Owner items open: 0", run(self.root, ["owner-items"])[1])


class TestMutualPositions(Base):
    def setUp(self):
        super().setUp()
        post(self.root, "bassy", "Proposal: use one writer per file.", kind="suggestion")
        self.fp = ex.sha8((self.root / "from-bassy" / "B-0001.md").read_text(encoding="utf-8"))

    def agree(self, me):
        return post(self.root, me, "I agree to that.", kind="agreement",
                    proposal="B-0001#" + self.fp)

    def test_one_side_only_then_mutual(self):
        self.assertEqual(self.agree("rev")[0], 0)
        self.assertIn("one side only (rev)", ex.view_agreed(self.root))
        self.assertEqual(self.agree("bassy")[0], 0)
        out = ex.view_agreed(self.root)
        self.assertIn("mutual", out)
        self.assertIn("Mutual positions, not approvals", out)

    def test_a_wrong_fingerprint_is_refused(self):
        code, _, err = post(self.root, "rev", "I agree.", kind="agreement",
                            proposal="B-0001#deadbeef")
        self.assertEqual(code, 2)
        self.assertIn("changed", err)

    def test_an_edited_proposal_makes_the_agreement_stale(self):
        self.agree("rev")
        self.agree("bassy")
        p = self.root / "from-bassy" / "B-0001.md"
        p.write_text(p.read_text(encoding="utf-8") + "Edited afterwards.\n", encoding="utf-8")
        self.assertIn("STALE", ex.view_agreed(self.root))

    def test_withdrawing_removes_that_sides_assent(self):
        self.agree("rev")
        self.agree("bassy")
        post(self.root, "rev", "I withdraw my agreement.", withdraws="R-0001")
        self.assertIn("one side only (bassy)", ex.view_agreed(self.root))

    def test_having_read_a_message_is_not_assent(self):
        run(self.root, ["ack", "--as", "rev", "B-0001"])
        self.assertIn("No agreements yet", ex.view_agreed(self.root))

    def test_regenerating_gives_the_same_file(self):
        self.agree("rev")
        run(self.root, ["agreed", "--write"])
        first = (self.root / "AGREED.md").read_bytes()
        run(self.root, ["agreed", "--write"])
        self.assertEqual(first, (self.root / "AGREED.md").read_bytes())


class TestConcurrentRegeneration(Base):
    """Rev's and Codex's finding: a writer that scanned earlier must not be able
    to finish later and replace a newer AGREED.md with its older snapshot."""

    def setUp(self):
        super().setUp()
        post(self.root, "bassy", "Proposal: use one writer per file.", kind="suggestion")
        self.fp = ex.sha8((self.root / "from-bassy" / "B-0001.md").read_text(encoding="utf-8"))

    def agree(self, me):
        return post(self.root, me, "I agree to that.", kind="agreement",
                    proposal="B-0001#" + self.fp)

    def test_a_stale_snapshot_cannot_win(self):
        self.agree("rev")
        real = ex.view_agreed
        calls = {"n": 0}

        def racing(root):
            text = real(root)
            calls["n"] += 1
            if calls["n"] == 1:
                self.agree("bassy")  # a newer assent lands after this snapshot
            return text

        with mock.patch.object(ex, "view_agreed", racing):
            ex.write_agreed(self.root)
        final = (self.root / "AGREED.md").read_text(encoding="utf-8")
        self.assertIn("mutual", final)
        self.assertNotIn("one side only", final)

    def test_two_writers_do_not_share_a_temporary_name(self):
        seen = []
        real = os.replace

        def spy(src, dst):
            seen.append(Path(src).name)
            return real(src, dst)

        with mock.patch.object(ex.os, "replace", spy):
            ex.atomic_write(self.root / "X.md", "a")
            ex.atomic_write(self.root / "X.md", "b")
        self.assertEqual(len(seen), 2)
        self.assertEqual(len(set(seen)), 2)

    def test_status_reports_an_out_of_date_agreed_file(self):
        self.agree("rev")
        run(self.root, ["agreed", "--write"])
        self.assertNotIn("out of date", run(self.root, ["status", "--as", "bassy"])[1])
        self.agree("bassy")  # a newer assent; the file on disk is now behind
        self.assertIn("AGREED.md is out of date",
                      run(self.root, ["status", "--as", "bassy"])[1])
        run(self.root, ["agreed", "--write"])
        self.assertNotIn("out of date", run(self.root, ["status", "--as", "bassy"])[1])

    def test_the_command_uses_the_converging_writer(self):
        self.agree("rev")
        self.assertEqual(run(self.root, ["agreed", "--write"])[0], 0)
        self.assertIn("one side only (rev)", (self.root / "AGREED.md").read_text(encoding="utf-8"))


class TestRedirection(Base):
    @unittest.skipUnless(os.name == "nt", "junctions are tested on Windows only")
    def test_a_junction_in_the_path_is_refused(self):
        target = Path(self.tmp) / "elsewhere"
        target.mkdir()
        link = Path(self.tmp) / "link"
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest("could not create a junction here; the check was NOT run")
        code, _, err = run(link / "exchange", ["status", "--as", "bassy"])
        self.assertEqual(code, 2)
        self.assertIn("shortcut or junction", err)


class TestInstalledSkill(unittest.TestCase):
    def test_installed_copy_matches_the_repo_copy(self):
        if os.environ.get("EXCHANGE_MUTATION_RUN"):
            self.skipTest("environment check, skipped during the mutation run")
        installed = Path.home() / ".claude" / "skills" / "rev-exchange" / "SKILL.md"
        repo = HERE.parent / "skill" / "SKILL.md"
        if not installed.is_file():
            self.skipTest("the skill is not installed on this machine; the "
                          "match check was NOT run")
        self.assertEqual(installed.read_text(encoding="utf-8").replace("\r\n", "\n"),
                         repo.read_text(encoding="utf-8").replace("\r\n", "\n"))


class TestInstalledBin(unittest.TestCase):
    FILES = ("exchange.py", "allowed_names.txt", "allowed_links.txt",
             "GOALS.template.md", "guard-local.template.txt")

    def test_bin_copy_matches_the_repo_copy(self):
        if os.environ.get("EXCHANGE_MUTATION_RUN"):
            self.skipTest("environment check, skipped during the mutation run so "
                          "that every kill comes from a rule test")
        bin_dir = Path.home() / "Documents" / "Main" / "Reverie" / "exchange" / "bin"
        if not bin_dir.is_dir():
            self.skipTest("no bin folder on this machine; the match check was NOT run")
        for name in self.FILES:
            a = (bin_dir / name).read_text(encoding="utf-8").replace("\r\n", "\n")
            b = (HERE.parent / name).read_text(encoding="utf-8").replace("\r\n", "\n")
            self.assertEqual(a, b, "bin copy of " + name + " differs from the repository copy")


if __name__ == "__main__":
    unittest.main()
