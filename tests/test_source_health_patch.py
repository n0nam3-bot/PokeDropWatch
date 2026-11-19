import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONITOR = ROOT / "monitor"
sys.path.insert(0, str(MONITOR))

import source_health_patch


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

    def test_notify_and_admin_iframes_are_replaced_with_top_level_launchers(self):
        notify = '''<style></style><div class="notify-frame-wrap"><iframe id="notifyPortalFrame" src="https://script.google.com/macros/s/test/exec?page=subscribe"></iframe></div><p class="portal-fallback">Open <a href="https://script.google.com/macros/s/test/exec?page=subscribe">directly</a>.</p><script>document.getElementById('refreshNotifyButton').addEventListener('click', () => window.location.reload());</script>'''
        admin = '''<style></style><iframe id="adminPortalFrame" src="https://script.google.com/macros/s/test/exec?page=admin"></iframe><p class="portal-fallback">Open <a href="https://script.google.com/macros/s/test/exec?page=admin">directly</a>.</p><script>document.getElementById('refreshAdminButton').addEventListener('click', () => window.location.reload());</script>'''
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            docs.mkdir()
            (docs / "app.js").write_text("", encoding="utf-8")
            (docs / "notify.html").write_text(notify, encoding="utf-8")
            (docs / "admin.html").write_text(admin, encoding="utf-8")
            source_health_patch._patch_portal_page(
                docs / "notify.html", "notify", "https://script.google.com/macros/s/test/exec?page=subscribe"
            )
            source_health_patch._patch_portal_page(
                docs / "admin.html", "admin", "https://script.google.com/macros/s/test/exec?page=admin"
            )
            notify_after = (docs / "notify.html").read_text(encoding="utf-8")
            admin_after = (docs / "admin.html").read_text(encoding="utf-8")
        self.assertNotIn("<iframe", notify_after)
        self.assertNotIn("<iframe", admin_after)
        self.assertIn("OPEN NOTIFY IN NEW TAB", notify_after)
        self.assertIn("OPEN ADMIN IN NEW TAB", admin_after)
        self.assertIn("window.location.assign(", notify_after)
        self.assertIn("window.location.assign(", admin_after)


if __name__ == "__main__":
    unittest.main()
