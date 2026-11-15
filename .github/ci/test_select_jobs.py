"""The selector picks what a change needs, and runs everything when unsure.

Standard library only, run by the `changes` job before it selects anything:

    python -m unittest discover -s .github/ci -p "test_*.py"
"""

import pathlib
import re
import unittest

import select_jobs as S

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "test.yml"
EVERY = set(S._all_targets())


def pick(*files):
    return set(S.select(files)[0])


class TheCasesThisWasBuiltFor(unittest.TestCase):

    def test_a_service_inviter_change_runs_service_inviter_alone(self):
        self.assertEqual(pick("service-inviter/ServiceInviter/ServiceInviter.lua",
                              "service-inviter/tests/test_queue.py"),
                         {"service-inviter"})

    def test_the_fee_schedule_runs_the_website_checks_and_its_readers(self):
        self.assertEqual(pick("client-documents/registry/fee-schedule.yaml"),
                         {"client-documents", "satc_system", "pricing"})

    def test_canon_runs_desk_which_depends_on_it(self):
        self.assertEqual(pick("canon/record.py"), {"canon", "desk"})

    def test_a_guide_draft_runs_the_copy_check(self):
        self.assertEqual(pick("docs/guides/entity-choice.md"), {"copy"})

    def test_a_website_page_runs_both_website_checks(self):
        self.assertEqual(pick("website/index.html"), {"pricing", "copy"})

    def test_the_intake_config_also_runs_client_documents(self):
        self.assertIn("client-documents", pick("website/intake-config.js"))

    def test_pocketbook_brings_its_mutation_shards(self):
        self.assertEqual(pick("pocketbook/src/pocketbook/book.py"),
                         {"pocketbook", "mutation-pocketbook"})

    def test_the_arena_is_matched_by_its_full_path(self):
        self.assertEqual(pick("docs/ember-vault-arena/code/arena/cli.py"),
                         {"docs/ember-vault-arena/code"})

    def test_a_monitor_runs_the_suite_that_checks_it(self):
        self.assertEqual(pick("fdic-peer-monitor/keybank_style.py"), {"credit-suite"})

    def test_a_folder_nothing_tests_runs_nothing(self):
        self.assertEqual(pick("stock-helper/README.md"), set())


class WhenInDoubtEverythingRuns(unittest.TestCase):

    def test_the_workflow_itself(self):
        self.assertEqual(pick(".github/workflows/test.yml"), EVERY)

    def test_this_selector(self):
        self.assertEqual(pick(".github/ci/select_jobs.py"), EVERY)

    def test_an_unmapped_root_file(self):
        self.assertEqual(pick(".gitattributes"), EVERY)
        self.assertEqual(pick("some-new-shared-config.toml"), EVERY)

    def test_an_inert_root_file_runs_nothing(self):
        self.assertEqual(pick("LOG.md"), set())

    def test_a_mapped_root_file_runs_its_reader(self):
        self.assertEqual(pick("render.yaml"), {"invoice-generator"})
        self.assertIn("credit-suite", pick("BACKLOG.md"))


class TheTableAgreesWithTheRepository(unittest.TestCase):
    """A name that matches nothing would quietly never run."""

    def test_every_project_is_a_folder_with_tests(self):
        for e in S.PYTEST:
            folder = ROOT / str(e["project"])
            self.assertTrue((folder / "tests").is_dir(), f"{folder} has no tests/")

    def test_every_path_a_project_reads_exists(self):
        prefixes = [p for e in S.PYTEST for p in e["reads"]]
        prefixes += [p for ps in S.OTHER.values() for p in ps]
        for p in prefixes:
            self.assertTrue((ROOT / p).exists(), f"{p} does not exist")

    def test_every_other_job_is_a_job_in_the_workflow(self):
        jobs = set(re.findall(r"^  ([\w-]+):\s*$", WORKFLOW.read_text(encoding="utf-8"), re.M))
        for job in S.OTHER:
            self.assertIn(job, jobs)

    def test_the_inert_root_files_are_really_at_the_root(self):
        for f in S.INERT_ROOT_FILES:
            self.assertTrue((ROOT / f).is_file(), f"{f} is not a root file")


if __name__ == "__main__":
    unittest.main()
