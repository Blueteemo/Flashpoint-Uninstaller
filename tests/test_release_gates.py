"""Keep release-state and cleanup safety gates from regressing."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseCleanupGates(unittest.TestCase):
    def test_draft_is_rejected_before_cleanup(self):
        workflow = (ROOT / '.github/workflows/final-cleanup.yml').read_text(encoding='utf8')
        release_gate = workflow.split('- name: Verify that v2.0.1 is published and PR #2 is merged', 1)[1].split('- name: Delete only safely merged project working branches', 1)[0]
        self.assertIn('.draft', release_gate)
        self.assertIn('.published_at', release_gate)
        self.assertIn('.prerelease', release_gate)
        self.assertIn('.[0] == false', release_gate)
        self.assertIn('.[1] == false', release_gate)
        self.assertIn('.assets[].name', release_gate)
        self.assertIn('Flashpoint-Uninstaller.exe', release_gate)
        self.assertIn('exit 1', release_gate)

    def test_run_history_is_cleaned_only_at_the_end(self):
        workflow = (ROOT / '.github/workflows/final-cleanup.yml').read_text(encoding='utf8')
        self.assertIn('[final-cleanup]', workflow)
        self.assertIn('status=completed', workflow)
        self.assertIn('select(.conclusion == "failure")', workflow)
        self.assertIn('--force-with-lease=refs/heads/$branch:$expected_sha', workflow)
        self.assertIn('safe_to_delete', workflow)

    def test_release_workflow_requires_explicit_approval(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf8')
        self.assertIn("publish_v2_0_1 == true", workflow)
        self.assertIn('[release-v2.0.1]', workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("needs: windows-tests", workflow)
        self.assertIn("--notes-file .github/RELEASE_NOTES_2.0.1.md", workflow)


if __name__ == '__main__':
    unittest.main()
