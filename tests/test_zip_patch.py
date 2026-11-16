import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.apply_patch import apply_patch


class ZipPatchTests(unittest.TestCase):
    def test_installs_repo_relative_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "patch.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("docs/app.js", "console.log('patched');")
            self.assertEqual(apply_patch(archive, root), 1)
            self.assertEqual((root / "docs/app.js").read_text(), "console.log('patched');")

    def test_strips_one_wrapper_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "patch.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("PokeDropWatch_Update/docs/app.js", "patched")
                zf.writestr("PokeDropWatch_Update/config/sources.json", "{}")
            self.assertEqual(apply_patch(archive, root), 2)
            self.assertEqual((root / "docs/app.js").read_text(), "patched")
            self.assertEqual((root / "config/sources.json").read_text(), "{}")
            self.assertFalse((root / "PokeDropWatch_Update").exists())

    def test_rejects_parent_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../outside.txt", "bad")
            with self.assertRaises(SystemExit):
                apply_patch(archive, root)

    def test_rejects_workflow_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "workflow.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(".github/workflows/pokedrop-watch.yml", "bad")
            with self.assertRaises(SystemExit):
                apply_patch(archive, root)


if __name__ == "__main__":
    unittest.main()
