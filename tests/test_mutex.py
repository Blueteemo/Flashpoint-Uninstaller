"""Concurrent removal exclusion, verified on Windows CI."""
import sys
import tempfile
import threading
from pathlib import Path
import unittest

from flashpoint_uninstaller.core import SafetyError, _uninstall_mutex


@unittest.skipUnless(sys.platform == "win32", "Windows mutex test")
class NamedMutexTests(unittest.TestCase):
    def test_other_thread_cannot_claim_same_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Flashpoint"
            entered = threading.Event()
            release = threading.Event()
            failures = []

            def holder():
                try:
                    with _uninstall_mutex(path):
                        entered.set()
                        if not release.wait(timeout=10):
                            raise RuntimeError("test lock timeout")
                except Exception as exc:
                    failures.append(exc)

            worker = threading.Thread(target=holder, daemon=True)
            worker.start()
            try:
                self.assertTrue(entered.wait(timeout=5))
                with self.assertRaises(SafetyError):
                    with _uninstall_mutex(path):
                        self.fail("Cannot acquire a held mutex")
            finally:
                release.set()
                worker.join(timeout=5)
            self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
