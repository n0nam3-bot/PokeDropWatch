import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "monitor"))
import source_health_patch  # noqa: F401
import public_ui_fixes_patch


class PublicUiFixTests(unittest.TestCase):
    def test_feed_news_filter_does_not_force_switch_away_from_products_view(self):
        source = """
  if (state.view === 'products' && state.filter === 'news') {
    state.view = 'alerts';
    $('alertsViewButton').classList.add('active');
    $('productsViewButton').classList.remove('active');
  }
  if (state.view === 'products' && state.category === 'news') {
    state.view = 'alerts';
    $('alertsViewButton').classList.add('active');
    $('productsViewButton').classList.remove('active');
  }
"""
        patched = public_ui_fixes_patch._remove_product_view_news_redirects(source)
        self.assertNotIn("state.view = 'alerts'", patched)

    def test_public_ui_patch_does_not_modify_notify_or_admin_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "app.js").write_text("const filters = true;", encoding="utf-8")
            notify = '<iframe id="notifyPortalFrame"></iframe>'
            admin = '<iframe id="adminPortalFrame"></iframe>'
            (docs / "notify.html").write_text(notify, encoding="utf-8")
            (docs / "admin.html").write_text(admin, encoding="utf-8")
            public_ui_fixes_patch.apply_public_ui_patches(root)
            self.assertEqual((docs / "notify.html").read_text(encoding="utf-8"), notify)
            self.assertEqual((docs / "admin.html").read_text(encoding="utf-8"), admin)


if __name__ == "__main__":
    unittest.main()
