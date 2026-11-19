"""More accurate access-block diagnostics and shared dashboard filters."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

import engine
import engine_recovery_patch as recovery


_BLOCKED_VISIBLE_RE = re.compile(
    r"pardon our interruption|robot or human\??|access denied|verify you are human|just a moment|checking your browser|"
    r"request blocked|unusual traffic|automated requests|enter the characters you see below|temporarily blocked|"
    r"complete the security check|confirm you are not a robot",
    re.I,
)
_PREVIOUS_RESPONSE_DIAGNOSTIC = recovery._response_diagnostic
_PREVIOUS_SCAN_SOURCE = engine.scan_source
_PUBLIC_UI_PATCHES_APPLIED = False


def response_diagnostic_with_visible_block_check(body: str, url: str) -> dict[str, Any]:
    """Detect visible challenges without matching incidental JS bundle strings."""
    diagnostic = _PREVIOUS_RESPONSE_DIAGNOSTIC(body, url)
    soup = BeautifulSoup(body, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    visible_text = engine.clean_text(soup.get_text(" ", strip=True), 18000)
    challenge_text = f"{title} {visible_text}"
    diagnostic["challenge"] = bool(_BLOCKED_VISIBLE_RE.search(challenge_text))
    # Keep the GameStop/product-marker summary added by source_diagnostics_patch.
    diagnostic_title = str(diagnostic.get("title", "") or "")
    marker_suffix = diagnostic_title.split("; product markers=", 1)[1] if "; product markers=" in diagnostic_title else ""
    display_title = f"{title}; product markers={marker_suffix}" if title and marker_suffix else (title or diagnostic_title)
    diagnostic["title"] = engine.clean_text(display_title, 160)
    diagnostic["visible_text_length"] = len(visible_text)
    diagnostic["empty_shell"] = (
        int(diagnostic.get("bytes", 0) or 0) < 5000
        and int(diagnostic.get("product_links", 0) or 0) == 0
        and int(diagnostic.get("json_scripts", 0) or 0) == 0
        and not diagnostic["challenge"]
    )
    return diagnostic


def scan_source_with_health(session, source: dict[str, Any], settings: dict[str, Any], state: dict[str, Any]):
    global _PUBLIC_UI_PATCHES_APPLIED
    if not _PUBLIC_UI_PATCHES_APPLIED:
        repo_root = Path(__file__).resolve().parents[1]
        apply_public_ui_patches(repo_root)
        _PUBLIC_UI_PATCHES_APPLIED = True

    events, result = _PREVIOUS_SCAN_SOURCE(session, source, settings, state)
    status = result.get("status", {}) if isinstance(result, dict) else {}
    if not isinstance(status, dict):
        return events, result

    diagnostics = [entry for entry in recovery._FETCH_DIAGNOSTICS if isinstance(entry, dict) and "error" not in entry]
    blocked = any(entry.get("challenge") for entry in diagnostics)
    current_items = int(status.get("items_found", 0) or 0)
    if blocked and current_items == 0:
        status["access_blocked"] = True
        status["parse_state"] = "access_blocked"
        last_known = int(status.get("last_known_items", 0) or 0)
        note = "BLOCKED: the returned page is an access-protection challenge, so current inventory could not be checked."
        if last_known:
            note += f" {last_known} last-known listing(s) are retained; they are not fresh stock confirmation."
        status["message"] = (note + " " + str(status.get("message", "")))[:1100]
    else:
        status["access_blocked"] = False
        if current_items == 0 and diagnostics and any(entry.get("empty_shell") for entry in diagnostics):
            status["parse_state"] = "small_or_client_rendered_shell"
            marker = "The response was a very small page shell with no product links or JSON payload; this is not evidence of an empty catalog."
            existing = str(status.get("message", ""))
            if marker not in existing:
                status["message"] = (existing + " " + marker).strip()[:1100]
            existing_diagnostics = list(status.get("parser_diagnostics", []))
            if marker not in existing_diagnostics:
                existing_diagnostics.append(marker)
            status["parser_diagnostics"] = existing_diagnostics[:5]
        elif current_items == 0 and status.get("status") == "warning":
            status["parse_state"] = "response_not_recognized"
        elif current_items:
            status["parse_state"] = "products_recognized"

    if status.get("status") == "error" and int(status.get("last_known_items", 0) or 0) > 0:
        status["freshness"] = "last_known_only"
    elif current_items:
        status["freshness"] = "current_scan"
    return events, result


def _replace_function(source: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = source.find(start_marker)
    if start < 0:
        raise ValueError(f"Dashboard patch could not find {start_marker!r}")
    end = source.find(end_marker, start + len(start_marker))
    if end < 0:
        raise ValueError(f"Dashboard patch could not find {end_marker!r}")
    return source[:start] + replacement + source[end:]


def _patch_dashboard_js(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    marker = "POKEDROP_TRACKED_ACTIVITY_FILTERS_V2"
    if marker in source:
        return False

    old_pokemon_filter = """  const isPokemonItem = (item) => {
    if (item.category === 'news' || item.type === 'news') return true;
    const title = ` ${normalize(item.title)} `;
    return pokemonTerms.some(term => title.includes(` ${term} `));
  };"""
    new_pokemon_filter = """  const isPokemonItem = (item) => {
    if (item.category === 'news' || item.type === 'news') return true;
    // Source pages explicitly scoped to Pokémon can omit the franchise name in a product title.
    if (item.pokemon_scoped === true) return true;
    const title = ` ${normalize(item.title)} `;
    return pokemonTerms.some(term => title.includes(` ${term} `));
  };"""
    if old_pokemon_filter not in source:
        raise ValueError("Dashboard patch could not find Pokémon title filter")
    source = source.replace(old_pokemon_filter, new_pokemon_filter, 1)

    flatten = r'''  // POKEDROP_TRACKED_ACTIVITY_FILTERS_V2
  function flattenProducts(items = {}, events = []) {
    const activities = new Map();
    for (const event of events || []) {
      if (!event || event.type === 'news') continue;
      const key = `${retailerKey(event)}|${normalize(event.title)}`;
      if (!key || key.endsWith('|')) continue;
      const rawType = event.type === 'new_drop' ? 'first_seen' : event.type;
      const activityType = ['first_seen', 'new_item'].includes(rawType)
        ? (releaseDateWithinMonth(event.release_date) ? 'new_item' : 'first_seen')
        : rawType;
      if (!['new_item', 'first_seen', 'restock', 'price_drop'].includes(activityType)) continue;
      if (!activities.has(key)) activities.set(key, []);
      activities.get(key).push({ ...event, activity_type: activityType });
    }

    const unique = new Map();
    for (const [sourceId, sourceState] of Object.entries(items || {})) {
      const saved = sourceState && sourceState.products;
      if (!saved || typeof saved !== 'object') continue;
      for (const product of Object.values(saved)) {
        if (!product || !isPokemonItem(product)) continue;
        const item = { ...product, source_id: sourceId, retailer_key: retailerKey(product), is_tracked_product: true };
        const key = `${item.retailer_key}|${normalize(item.title)}`;
        const matching = activities.get(key) || [];
        item.activity_types = [...new Set(matching.map(event => event.activity_type))];
        const newestActivity = [...matching].sort((a, b) => String(b.detected_at || '').localeCompare(String(a.detected_at || '')))[0];
        if (newestActivity) {
          item.last_activity_at = newestActivity.detected_at || '';
          item.last_activity_type = newestActivity.activity_type;
          item.release_date = item.release_date || newestActivity.release_date || '';
        }
        const previous = unique.get(key);
        const score = candidate => (candidate.image ? 4 : 0) + (candidate.price != null ? 3 : 0)
          + (candidate.availability && candidate.availability !== 'unknown' ? 2 : 0)
          + (candidate.release_date ? 1 : 0)
          + Math.min(String(candidate.title || '').length, 240) / 240;
        if (!previous) {
          unique.set(key, item);
        } else {
          previous.activity_types = [...new Set([...(previous.activity_types || []), ...item.activity_types])];
          if (score(item) > score(previous)) {
            item.activity_types = previous.activity_types;
            item.last_activity_at = previous.last_activity_at || item.last_activity_at;
            item.last_activity_type = previous.last_activity_type || item.last_activity_type;
            unique.set(key, item);
          }
        }
      }
    }
    return [...unique.values()].sort((a, b) => String(b.last_seen || '').localeCompare(String(a.last_seen || '')));
  }
'''
    source = _replace_function(
        source,
        "  function flattenProducts(items = {}) {",
        "  function populateRetailerFilter() {",
        flatten,
    )

    item_matches = r'''  function itemMatches(item, includeActivityType = false) {
    const category = inferCategory(item);
    const normalizedType = item.type === 'new_drop' ? 'first_seen' : item.type;
    let typeOk = true;
    if (includeActivityType && state.filter !== 'all') {
      if (item.is_tracked_product) {
        const types = Array.isArray(item.activity_types) ? item.activity_types : [];
        typeOk = types.includes(state.filter);
      } else if (state.filter === 'new_item') {
        typeOk = ['new_item', 'first_seen'].includes(normalizedType) && releaseDateWithinMonth(item.release_date);
      } else if (state.filter === 'first_seen') {
        typeOk = ['first_seen', 'new_item'].includes(normalizedType) && !releaseDateWithinMonth(item.release_date);
      } else {
        typeOk = normalizedType === state.filter;
      }
    }
    const categoryOk = state.category === 'all' || category === state.category;
    const retailerOk = state.retailer === 'all' || retailerKey(item) === state.retailer;
    const title = normalize(item.title);
    const query = normalize(state.query);
    const queryOk = !query || (state.exact ? title === query : title.includes(query));
    return typeOk && categoryOk && retailerOk && queryOk;
  }
'''
    source = _replace_function(
        source,
        "  function itemMatches(item, includeAlertType = false) {",
        "  function productMedia(item) {",
        item_matches,
    )

    render_events = r'''  function renderEvents() {
    const list = $('alertList');
    list.replaceChildren();
    const isTracked = state.view === 'products';
    const sourceItems = isTracked ? state.products : state.events;
    const filtered = sourceItems.filter(item => itemMatches(item, true));
    $('feedHeading').textContent = isTracked ? 'All tracked products' : 'Latest alerts';
    // Keep the same activity, item-type, and retailer controls active in both views.
    $('alertTypeFilters').hidden = false;
    $('feedExplanation').textContent = isTracked
      ? 'Activity filters also work here: New items, First seen, Restocks and Price drops show saved products that have matching events in the alert history. All activity shows every saved product.'
      : 'NEW ITEMS have a published release date within 30 days before or after today. FIRST SEEN means the monitor discovered a listing but its release date is outside that window or unavailable.';
    if (!filtered.length) {
      const empty = node('div', 'empty-state large-empty');
      empty.append(node('span', 'empty-ball', '◉'));
      const heading = isTracked
        ? (state.products.length ? 'No tracked products match these filters' : 'No tracked products yet')
        : (state.events.length ? 'No matching Pokémon alerts' : 'No verified Pokémon alerts yet');
      empty.append(node('strong', '', heading));
      empty.append(node('span', '', state.filter !== 'all' && isTracked
        ? 'A saved product appears in an activity filter only when that product has a matching event in the retained alert history. Choose All activity to see every saved product.'
        : (state.query
          ? 'Check the spelling, clear Exact title match, or choose a different item type or retailer.'
          : 'A retailer may have loaded without exposing product cards. Check the source status above for MATCHES, BLOCKED, NO MATCH, or ISSUE.')));
      list.append(empty);
      return;
    }
    filtered.forEach(item => list.append(productCard(item, isTracked)));
  }
'''
    source = _replace_function(
        source,
        "  function renderEvents() {",
        "  function render(data) {",
        render_events,
    )

    # Attach the event history to saved products so activity chips can filter them.
    old_assignment = "    state.products = flattenProducts(data.items || {});"
    new_assignment = "    state.products = flattenProducts(data.items || {}, state.events);"
    if old_assignment not in source:
        raise ValueError("Dashboard patch could not find saved-product assignment")
    source = source.replace(old_assignment, new_assignment, 1)

    # BLOCKED is distinct from a normal parser miss and takes precedence over PARTIAL.
    old_status = """      const partial = Boolean((source.response_health && source.response_health.partial) || (configured > 0 && succeeded < configured));
      const stateLabel = partial ? 'PARTIAL' : status === 'ok' ? 'MATCHES' : status === 'warning' ? 'NO MATCH' : 'ISSUE';
      const stateClass = partial || status === 'warning' ? 'warn' : status === 'ok' ? 'ok' : 'error';"""
    new_status = """      const partial = Boolean((source.response_health && source.response_health.partial) || (configured > 0 && succeeded > 0 && succeeded < configured));
      const diagnosticText = `${source.message || ''} ${(source.parser_diagnostics || []).join(' ')}`.toLowerCase();
      const blocked = Boolean(source.access_blocked) || /pardon our interruption|robot or human|access denied|verify you are human|captcha challenge|request blocked|unusual traffic|access-challenge/.test(diagnosticText);
      const stateLabel = blocked ? 'BLOCKED' : partial ? 'PARTIAL' : status === 'ok' ? 'MATCHES' : status === 'warning' ? 'NO MATCH' : 'ISSUE';
      const stateClass = blocked || status === 'error' ? 'error' : partial || status === 'warning' ? 'warn' : 'ok';"""
    if old_status not in source:
        raise ValueError("Dashboard patch could not find source status renderer")
    source = source.replace(old_status, new_status, 1)

    old_description = """      if (partial) description = `Partial results · ${Number(source.items_found || 0)} item(s) recognized · ${routeStatus}`;
      else if (status === 'ok') description = `${source.items_found || 0} Pokémon listings · ${routeStatus}`;
      else if (status === 'warning') description = `No recognized items · ${routeStatus}`;
      else description = 'All configured pages failed · inspect scan log';"""
    new_description = """      if (blocked) description = `Access protection · ${Number(source.last_known_items || source.items_found || 0)} last-known listing(s) · current stock not confirmed`;
      else if (partial) description = `Partial results · ${Number(source.items_found || 0)} current item(s) recognized · ${routeStatus}`;
      else if (status === 'ok') description = `${source.items_found || 0} Pokémon listings · ${routeStatus}`;
      else if (status === 'warning') description = source.parse_state === 'small_or_client_rendered_shell' ? `Page shell returned · products not exposed · ${routeStatus}` : `No recognized items · ${routeStatus}`;
      else description = Number(source.last_known_items || source.items_found || 0) > 0 ? `Last known only · ${Number(source.last_known_items || source.items_found)} saved listing(s) · latest request failed` : 'All configured pages failed · inspect scan log';"""
    if old_description not in source:
        raise ValueError("Dashboard patch could not find source description renderer")
    source = source.replace(old_description, new_description, 1)

    # The News view remains the existing feed, but it is not a saved catalog view.
    old_filter_click = """    state.filter = button.dataset.filter;
    renderEvents();"""
    new_filter_click = """    state.filter = button.dataset.filter;
    if (state.view === 'products' && state.filter === 'news') {
      state.view = 'alerts';
      $('alertsViewButton').classList.add('active');
      $('productsViewButton').classList.remove('active');
    }
    renderEvents();"""
    if old_filter_click not in source:
        raise ValueError("Dashboard patch could not find activity chip listener")
    source = source.replace(old_filter_click, new_filter_click, 1)

    old_category_listener = """  $('categoryFilter').addEventListener('change', (event) => { state.category = event.target.value; renderEvents(); });"""
    new_category_listener = """  $('categoryFilter').addEventListener('change', (event) => {
    state.category = event.target.value;
    if (state.view === 'products' && state.category === 'news') {
      state.view = 'alerts';
      $('alertsViewButton').classList.add('active');
      $('productsViewButton').classList.remove('active');
    }
    renderEvents();
  });"""
    if old_category_listener not in source:
        raise ValueError("Dashboard patch could not find item-type listener")
    source = source.replace(old_category_listener, new_category_listener, 1)

    path.write_text(source, encoding="utf-8")
    return True


def _portal_launcher(page: str, url: str) -> str:
    label = "Notify" if page == "notify" else "Admin"
    icon = "✉" if page == "notify" else "⚙"
    title = "Open the notification center" if page == "notify" else "Open subscriber administration"
    description = (
        "Google sign-in and security cookies are more reliable when this portal is opened directly, "
        "rather than inside an embedded frame. Your PokéDrop Watch page will remain available in this tab."
        if page == "notify" else
        "The administrator portal is opened directly so Google can use its normal first-party sign-in and security cookies."
    )
    return f'''<section class="portal-launch-panel" aria-label="{label} portal">
      <div class="portal-launch-icon" aria-hidden="true">{icon}</div>
      <div class="portal-launch-copy">
        <p class="eyebrow">GOOGLE APPS SCRIPT PORTAL</p>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div class="portal-launch-actions">
        <a class="portal-launch-primary" href="{url}" target="_blank" rel="noopener noreferrer">OPEN {label.upper()} IN NEW TAB ↗</a>
        <a class="portal-launch-secondary" href="{url}">Open in this tab</a>
      </div>
    </section>'''


def _patch_portal_page(path: Path, page: str, url: str) -> bool:
    source = path.read_text(encoding="utf-8")
    marker = f"POKEDROP_{page.upper()}_TOP_LEVEL_PORTAL_V2"
    if marker in source:
        return False
    if page == "notify":
        pattern = re.compile(r'<div class="notify-frame-wrap">.*?<p class="portal-fallback">.*?</p>', re.S)
        refresh_old = "document.getElementById('refreshNotifyButton').addEventListener('click', () => window.location.reload());"
        refresh_new = f"// {marker}\ndocument.getElementById('refreshNotifyButton').addEventListener('click', () => window.location.assign('{url}'));"
    else:
        pattern = re.compile(r'<iframe id="adminPortalFrame".*?</iframe>\s*<p class="portal-fallback">.*?</p>', re.S)
        refresh_old = "document.getElementById('refreshAdminButton').addEventListener('click', () => window.location.reload());"
        refresh_new = f"// {marker}\ndocument.getElementById('refreshAdminButton').addEventListener('click', () => window.location.assign('{url}'));"
    replacement = _portal_launcher(page, url)
    source, count = pattern.subn(replacement, source, count=1)
    if count != 1:
        raise ValueError(f"Could not replace the existing {page} iframe block")
    if refresh_old not in source:
        raise ValueError(f"Could not find {page} refresh button handler")
    source = source.replace(refresh_old, refresh_new, 1)
    portal_css = """
    .portal-launch-panel { min-height:360px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:15px; padding:34px 24px; border:1px solid var(--line); border-radius:13px; background:linear-gradient(145deg,#fffdfa,#f7f1ed); box-shadow:var(--shadow); text-align:center; }
    .portal-launch-icon { width:58px; height:58px; display:grid; place-items:center; border-radius:16px; background:#fff0ea; color:var(--red-dark); font-size:25px; }
    .portal-launch-copy { max-width:620px; }
    .portal-launch-copy h2 { margin:4px 0 8px; font:750 clamp(21px,3vw,29px)/1.15 system-ui,sans-serif; letter-spacing:-.7px; }
    .portal-launch-copy p:last-child { margin:0; color:#777970; font-size:13px; line-height:1.65; }
    .portal-launch-actions { display:flex; justify-content:center; align-items:center; flex-wrap:wrap; gap:12px; margin-top:5px; }
    .portal-launch-primary { display:inline-flex; min-height:44px; align-items:center; justify-content:center; padding:0 19px; border-radius:9px; background:var(--red-dark); color:#fff; font-size:11px; font-weight:850; letter-spacing:.5px; text-decoration:none; }
    .portal-launch-secondary { color:var(--red-dark); font-size:12px; font-weight:750; text-decoration:underline; text-underline-offset:3px; }
    @media(max-width:520px) { .portal-launch-panel { min-height:320px; padding:26px 16px; } .portal-launch-actions { width:100%; flex-direction:column; } .portal-launch-primary { width:min(100%,320px); } }
"""
    source = source.replace("</style>", portal_css + "  </style>", 1)
    path.write_text(source, encoding="utf-8")
    return True


def apply_public_ui_patches(repo_root: Path) -> dict[str, bool]:
    """Patch the existing dashboard and replace fragile Apps Script iframes."""
    docs = Path(repo_root) / "docs"
    outcomes = {}
    app = docs / "app.js"
    if app.is_file():
        outcomes["app.js"] = _patch_dashboard_js(app)
    notify_url = "https://script.google.com/macros/s/AKfycbwGfc1E_t1nj-HG5Sf5V1Y-J_cwY_PmwLIUAfbPPBVtl7mbxOhCkz5Q6BNosWmEUmVm/exec?page=subscribe"
    admin_url = "https://script.google.com/macros/s/AKfycbwGfc1E_t1nj-HG5Sf5V1Y-J_cwY_PmwLIUAfbPPBVtl7mbxOhCkz5Q6BNosWmEUmVm/exec?page=admin"
    notify = docs / "notify.html"
    admin = docs / "admin.html"
    if notify.is_file():
        outcomes["notify.html"] = _patch_portal_page(notify, "notify", notify_url)
    if admin.is_file():
        outcomes["admin.html"] = _patch_portal_page(admin, "admin", admin_url)
    return outcomes


# Keep the recovery module's existing diagnostics, but avoid classifying an
# ordinary JavaScript bundle that mentions CAPTCHA as a live access challenge.
recovery._response_diagnostic = response_diagnostic_with_visible_block_check
engine.scan_source = scan_source_with_health
