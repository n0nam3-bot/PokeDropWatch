import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONITOR = ROOT / "monitor"
sys.path.insert(0, str(MONITOR))

import source_health_patch
import public_ui_fixes_patch


class SourceHealthPatchTests(unittest.TestCase):
    def test_dashboard_uses_shared_activity_filters_for_saved_products(self):
        source = '''
  const isPokemonItem = (item) => {
    if (item.category === 'news' || item.type === 'news') return true;
    const title = ` ${normalize(item.title)} `;
    return pokemonTerms.some(term => title.includes(` ${term} `));
  };
  function flattenProducts(items = {}) {
    return [];
  }
  function populateRetailerFilter() {
    return;
  }
  function itemMatches(item, includeAlertType = false) {
    return true;
  }
  function productMedia(item) {
    return item;
  }
  function renderEvents() {
    const filtered = sourceItems.filter(item => itemMatches(item, !isTracked));
  }
  function render(data) {
      state.products = flattenProducts(data.items || {});
  }
      const partial = Boolean((source.response_health && source.response_health.partial) || (configured > 0 && succeeded < configured));
      const stateLabel = partial ? 'PARTIAL' : status === 'ok' ? 'MATCHES' : status === 'warning' ? 'NO MATCH' : 'ISSUE';
      const stateClass = partial || status === 'warning' ? 'warn' : status === 'ok' ? 'ok' : 'error';
      if (partial) description = `Partial results · ${Number(source.items_found || 0)} item(s) recognized · ${routeStatus}`;
      else if (status === 'ok') description = `${source.items_found || 0} Pokémon listings · ${routeStatus}`;
      else if (status === 'warning') description = `No recognized items · ${routeStatus}`;
      else description = 'All configured pages failed · inspect scan log';
    state.filter = button.dataset.filter;
    renderEvents();
  $('categoryFilter').addEventListener('change', (event) => { state.category = event.target.value; renderEvents(); });
'''
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            docs.mkdir()
            app = docs / "app.js"
            app.write_text(source, encoding="utf-8")
            source_health_patch._patch_dashboard_js(app)
            patched = app.read_text(encoding="utf-8")
        self.assertIn("POKEDROP_TRACKED_ACTIVITY_FILTERS_V2", patched)
        self.assertIn("item.activity_types", patched)
        self.assertIn("$('alertTypeFilters').hidden = false", patched)
        self.assertIn("flattenProducts(data.items || {}, state.events)", patched)
        self.assertIn("BLOCKED", patched)

    def test_public_ui_patch_preserves_notify_and_admin_iframes(self):
        app_source = '''
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
        '''
        notify = '<iframe id="notifyPortalFrame" src="https://script.google.com/macros/s/test/exec?page=subscribe"></iframe>'
        admin = '<iframe id="adminPortalFrame" src="https://script.google.com/macros/s/test/exec?page=admin"></iframe>'
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            docs.mkdir()
            (docs / "app.js").write_text(app_source, encoding="utf-8")
            (docs / "notify.html").write_text(notify, encoding="utf-8")
            (docs / "admin.html").write_text(admin, encoding="utf-8")
            public_ui_fixes_patch.apply_public_ui_patches(Path(temp))
            app_after = (docs / "app.js").read_text(encoding="utf-8")
            notify_after = (docs / "notify.html").read_text(encoding="utf-8")
            admin_after = (docs / "admin.html").read_text(encoding="utf-8")
        self.assertNotIn("state.view = 'alerts'", app_after)
        self.assertEqual(notify_after, notify)
        self.assertEqual(admin_after, admin)


if __name__ == "__main__":
    unittest.main()
