(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const state = { events: [], products: [], filter: 'all', category: 'all', retailer: 'all', query: '', exact: false, view: 'alerts' };
  const labels = { new_drop: 'FIRST SEEN', first_seen: 'FIRST SEEN', new_item: 'NEW ITEM', restock: 'RESTOCK', price_drop: 'PRICE DROP', price_change: 'PRICE UPDATE', news: 'POKÉMON NEWS' };
  const icons = { new_drop: '✦', first_seen: '✦', new_item: '✧', restock: '↻', price_drop: '↓', price_change: '↕', news: '✧' };
  const categoryLabels = {
    tcg: 'Trading cards & TCG', plush: 'Plush', collectibles: 'Collectibles',
    games: 'Video games', accessories: 'Accessories & apparel', news: 'News'
  };
  const pokemonTerms = [
    'pokemon', 'pikachu', 'charizard', 'charmander', 'squirtle', 'bulbasaur', 'eevee',
    'jolteon', 'vaporeon', 'flareon', 'mewtwo', 'mew', 'snorlax', 'gengar', 'lucario',
    'greninja', 'psyduck', 'jigglypuff', 'dragonite', 'gardevoir', 'umbreon', 'espeon',
    'arcanine', 'lapras', 'ditto', 'magikarp', 'gyarados', 'rayquaza', 'mimikyu', 'piplup',
    'turtwig', 'chimchar', 'totodile', 'cyndaquil', 'chikorita', 'treecko', 'torchic', 'mudkip',
    'ho oh', 'lugia', 'celebi', 'kyogre', 'groudon', 'dialga', 'palkia', 'giratina', 'arceus',
    'zekrom', 'reshiram', 'kyurem', 'xerneas', 'yveltal', 'solgaleo', 'lunala', 'zacian',
    'zamazenta', 'koraidon', 'miraidon', 'sylveon', 'glaceon', 'leafeon', 'vulpix', 'ninetales',
    'machamp', 'blastoise', 'venusaur', 'scizor', 'heracross', 'cinderace', 'sprigatito',
    'fuecoco', 'quaxly', 'pawmi', 'team rocket'
  ];
  const normalize = (value) => String(value || '').toLowerCase().replace(/é/g, 'e').replace(/[^a-z0-9]+/g, ' ').trim();
  const isPokemonItem = (item) => {
    if (item.category === 'news' || item.type === 'news') return true;
    const title = ` ${normalize(item.title)} `;
    return pokemonTerms.some(term => title.includes(` ${term} `));
  };
  const inferCategory = (item) => {
    if (item.type === 'news' || item.category === 'news') return 'news';
    const title = normalize(item.title);
    if (/(nintendo switch|switch game|video game software|game cartridge|switch cartridge|nintendo ds game)/.test(title)) return 'games';
    if (/(pokemon tcg|trading card|trading cards|booster|elite trainer|trainer box|card collection|battle deck|theme deck|blister|pokemon cards| tcg |etb|surprise box|destined rivals|journey together|prismatic evolutions)/.test(` ${title} `)) return 'tcg';
    if (item.category && ['tcg', 'plush', 'collectibles', 'games', 'accessories'].includes(item.category)) return item.category;
    if (/(plush|stuffed animal|soft toy|plushie)/.test(title)) return 'plush';
    if (/(binder|deck box|playmat|sleeves|backpack|keychain|key chain|apparel|shirt|hoodie|hat|blanket|wallet|bottle|accessor|lunch box|pin set)/.test(title)) return 'accessories';
    return 'collectibles';
  };
  const money = (value, currency = 'USD') => {
    if (value === null || value === undefined || value === '') return 'Price not listed';
    try { return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'USD' }).format(Number(value)); }
    catch { return `$${Number(value).toFixed(2)}`; }
  };
  const dateText = (value) => {
    if (!value) return 'Not scanned yet';
    const date = /^\d{4}-\d{2}-\d{2}$/.test(String(value))
      ? new Date(`${value}T12:00:00`)
      : new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
  };
  const releaseDateWithinMonth = (value) => {
    if (!value) return false;
    const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!match) return false;
    const releaseDay = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    const now = new Date();
    const todayUtc = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
    return Number.isFinite(releaseDay) && Math.abs(releaseDay - todayUtc) <= 30 * 86400000;
  };
  const safeLink = (value) => {
    try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : '#'; }
    catch { return '#'; }
  };
  const retailerKey = (item) => String(item.retailer_key || normalize(item.retailer || item.source_name || 'other').replace(/\s+/g, '-'));
  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function configureAlertTypeFilters() {
    const row = $('alertTypeFilters');
    const explanation = $('feedExplanation');
    if (explanation) {
      explanation.textContent = 'NEW ITEMS have a published release date within 30 days before or after today. FIRST SEEN means the monitor discovered a listing but its release date is outside that window or unavailable.';
    }
    if (!row) return;

    const newItemButtons = [...row.querySelectorAll('[data-filter="new_item"], [data-filter="first_seen"]')];
    const newItems = newItemButtons[0];
    if (!newItems) return;
    newItems.dataset.filter = 'new_item';
    newItems.textContent = 'New items';
    newItems.title = 'Products with a published release date within 30 days before or after today.';

    // Remove duplicate buttons from older page builds before adding First seen.
    newItemButtons.slice(1).forEach(button => button.remove());
    let firstSeen = row.querySelector('[data-filter="first_seen"]');
    if (!firstSeen) {
      firstSeen = node('button', 'filter-chip', 'First seen');
      firstSeen.type = 'button';
      firstSeen.dataset.filter = 'first_seen';
      const restocks = row.querySelector('[data-filter="restock"]');
      row.insertBefore(firstSeen, restocks || null);
    }
    firstSeen.textContent = 'First seen';
    firstSeen.title = 'Items first discovered by the monitor when the release date is outside the 30-day window or unavailable.';
  }
  function renderSources(sources = []) {
    const grid = $('sourceGrid');
    grid.replaceChildren();
    $('sourceCount').textContent = `${sources.length} configured`;
    if (!sources.length) {
      grid.append(node('div', 'empty-state', 'Source status will appear after the first scheduled scan.'));
      return;
    }
    for (const source of sources) {
      const card = node('article', 'source-card');
      const top = node('div', 'source-top');
      const left = node('div');
      left.append(node('div', 'source-name', source.name || source.id));
      left.append(node('div', 'source-kind', source.type || 'source'));
      const status = source.status || 'error';
      const stateLabel = status === 'ok' ? 'MATCHES' : status === 'warning' ? 'NO MATCH' : 'ISSUE';
      const stateClass = status === 'ok' ? 'ok' : status === 'warning' ? 'warn' : 'error';
      const badge = node('span', `source-state ${stateClass}`, stateLabel);
      badge.title = [source.message || stateLabel, source.notes || ''].filter(Boolean).join(' · ');
      top.append(left, badge);
      const bottom = node('div', 'source-bottom');
      let description;
      const succeeded = Number(source.successful_urls ?? (status === 'error' ? 0 : 1));
      const configured = Number(source.configured_urls ?? 1);
      const routeStatus = `${succeeded}/${configured} pages responded`;
      if (status === 'ok') description = `${source.items_found || 0} Pokémon listings · ${routeStatus}`;
      else if (status === 'warning') description = `No recognized items · ${routeStatus}`;
      else description = 'All configured pages failed · inspect scan log';
      const detail = node('span', '', description);
      detail.title = source.message || description;
      bottom.append(detail);
      const link = node('a', '', 'OPEN ↗');
      link.href = safeLink(source.url);
      link.target = '_blank'; link.rel = 'noopener noreferrer';
      bottom.append(link);
      card.append(top, bottom);
      grid.append(card);
    }
  }
  function flattenProducts(items = {}) {
    const unique = new Map();
    for (const [sourceId, sourceState] of Object.entries(items || {})) {
      const products = sourceState && sourceState.products;
      if (!products || typeof products !== 'object') continue;
      for (const product of Object.values(products)) {
        if (!product || !isPokemonItem(product)) continue;
        const item = { ...product, source_id: sourceId, retailer_key: retailerKey(product) };
        const key = `${item.retailer_key}|${normalize(item.title)}`;
        const previous = unique.get(key);
        const score = candidate => (candidate.image ? 4 : 0) + (candidate.price != null ? 3 : 0)
          + (candidate.availability && candidate.availability !== 'unknown' ? 2 : 0)
          + (candidate.release_date ? 1 : 0)
          + Math.min(String(candidate.title || '').length, 240) / 240;
        if (!previous || score(item) > score(previous)) unique.set(key, item);
      }
    }
    return [...unique.values()].sort((a, b) => String(b.last_seen || '').localeCompare(String(a.last_seen || '')));
  }
  function populateRetailerFilter() {
    const select = $('retailerFilter');
    if (!select) return;
    const selected = state.retailer;
    select.replaceChildren(
      new Option('All retailers', 'all'),
      new Option('Amazon', 'amazon'),
      new Option('Walmart', 'walmart'),
      new Option('Best Buy', 'best-buy'),
      new Option('Target', 'target'),
      new Option('Pokémon Center', 'pokemon-center'),
      new Option('GameStop', 'gamestop')
    );
    select.value = ['all', 'amazon', 'walmart', 'best-buy', 'target', 'pokemon-center', 'gamestop'].includes(selected) ? selected : 'all';
    state.retailer = select.value;
  }
  function itemMatches(item, includeAlertType = false) {
    const category = inferCategory(item);
    const normalizedType = item.type === 'new_drop' ? 'first_seen' : item.type;
    let typeOk = true;
    if (includeAlertType && state.filter !== 'all') {
      if (state.filter === 'new_item') {
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
  function productMedia(item) {
    const media = node('div', 'alert-media');
    const imageUrl = safeLink(item.image);
    if (imageUrl !== '#') {
      const image = node('img', 'alert-product-image');
      image.src = imageUrl;
      image.alt = item.title || 'Pokémon product image';
      image.loading = 'lazy';
      image.decoding = 'async';
      image.addEventListener('error', () => {
        media.replaceChildren(node('span', 'alert-icon-fallback', icons[item.type] || '✦'));
        media.classList.add('image-missing');
      }, { once: true });
      media.append(image);
    } else {
      media.append(node('span', 'alert-icon-fallback', icons[item.type] || '✦'));
      media.classList.add('image-missing');
    }
    return media;
  }
  function productCard(item, isTracked = false) {
    const card = node('article', 'alert-card');
    const content = node('div', 'alert-content');
    content.append(node('div', 'alert-title', item.title || 'Pokémon item update'));
    const meta = node('div', 'alert-meta');
    meta.append(node('span', '', item.retailer || item.source_name || 'Source'));
    meta.append(node('span', '', '·'));
    meta.append(node('span', '', categoryLabels[inferCategory(item)] || 'Collectible'));
    if (item.last_seen || item.detected_at) {
      meta.append(node('span', '', '·'));
      meta.append(node('span', '', dateText(item.last_seen || item.detected_at)));
    }
    content.append(meta);
    const actions = node('div', 'alert-actions');
    const displayType = item.type === 'new_drop' ? 'first_seen' : item.type;
    const displayLabelType = displayType === 'first_seen' && releaseDateWithinMonth(item.release_date)
      ? 'new_item'
      : displayType;
    actions.append(node('span', `type-badge ${isTracked ? 'tracked' : displayLabelType || ''}`, isTracked ? 'TRACKED ITEM' : (labels[displayLabelType] || 'UPDATE')));
    const view = node('a', 'view-link', isTracked ? 'VIEW PRODUCT ↗' : 'VIEW ITEM ↗');
    view.href = safeLink(item.url); view.target = '_blank'; view.rel = 'noopener noreferrer';
    actions.append(view);
    content.append(actions);
    const price = node('div', 'alert-price');
    price.append(node('strong', '', money(item.price, item.currency)));
    let extra = displayLabelType === 'new_item' && item.release_date
      ? `Release date ${dateText(item.release_date)}`
      : displayLabelType === 'first_seen'
        ? 'First observed by PokéDrop Watch · Release date outside the 30-day window or unavailable'
        : (item.availability && item.availability !== 'unknown'
          ? item.availability.replaceAll('_', ' ')
          : 'Check retailer for stock');
    if (!isTracked && item.previous_price !== null && item.previous_price !== undefined) extra += ` · was ${money(item.previous_price, item.currency)}`;
    price.append(node('span', '', extra));
    card.append(productMedia(item), content, price);
    return card;
  }
  function renderEvents() {
    const list = $('alertList');
    list.replaceChildren();
    const isTracked = state.view === 'products';
    const sourceItems = isTracked ? state.products : state.events;
    const filtered = sourceItems.filter(item => itemMatches(item, !isTracked));
    $('feedHeading').textContent = isTracked ? 'All tracked products' : 'Latest alerts';
    $('alertTypeFilters').hidden = isTracked;
    $('feedExplanation').textContent = isTracked
      ? 'Products recognized in the latest successful catalog scans. Prices and availability are only shown when the retailer page exposes them.'
      : 'NEW ITEMS have a published release date within 30 days before or after today. FIRST SEEN means the monitor discovered a listing but its release date is outside that window or unavailable.';
    if (!filtered.length) {
      const empty = node('div', 'empty-state large-empty');
      empty.append(node('span', 'empty-ball', '◉'));
      const heading = isTracked
        ? (state.products.length ? 'No tracked products match' : 'No tracked products yet')
        : (state.events.length ? 'No matching Pokémon alerts' : 'No verified Pokémon alerts yet');
      empty.append(node('strong', '', heading));
      empty.append(node('span', '', state.query
        ? 'Check the spelling, clear Exact title match, or choose a different item type or retailer.'
        : 'A retailer may have loaded without exposing product cards. Check the source status above for MATCHES, NO MATCH, or ISSUE.'));
      list.append(empty);
      return;
    }
    filtered.forEach(item => list.append(productCard(item, isTracked)));
  }
  function render(data) {
    const summary = data.summary || {};
    const sources = data.source_status || [];
    const matches = sources.filter(source => source.status === 'ok').length;
    const warnings = sources.filter(source => source.status === 'warning').length;
    const failures = sources.filter(source => source.status === 'error').length;
    $('onlineCount').textContent = `${matches}/${sources.length || summary.enabled_sources || 0}`;
    $('listingCount').textContent = String(summary.tracked_products ?? '—');
    $('alertCount').textContent = String(summary.new_alerts ?? 0);
    $('overallStatus').textContent = sources.length
      ? `${matches} source matches · ${warnings} parser misses · ${failures} request errors`
      : 'Waiting for first scan';
    $('overallLed').className = `status-led ${sources.length && failures === 0 && warnings === 0 ? 'ok' : sources.length ? 'warn' : ''}`;
    $('lastChecked').textContent = data.last_checked ? `Last checked ${dateText(data.last_checked)}` : 'The first scan runs after setup.';
    renderSources(sources);
    const eventMap = new Map();
    for (const rawEvent of (data.events || [])) {
      if (!isPokemonItem(rawEvent)) continue;
      const event = { ...rawEvent, type: rawEvent.type === 'new_drop' ? 'first_seen' : rawEvent.type };
      const key = `${event.type}|${retailerKey(event)}|${normalize(event.title)}|${['first_seen', 'new_item'].includes(event.type) ? '' : (event.price ?? '')}|${event.previous_price ?? ''}`;
      if (!eventMap.has(key)) eventMap.set(key, event);
    }
    state.events = [...eventMap.values()];
    state.products = flattenProducts(data.items || {});
    populateRetailerFilter();
    renderEvents();
  }
  async function refresh(showToast = false) {
    const button = $('refreshButton');
    button.classList.add('spinning');
    try {
      const response = await fetch(`./data/state.json?v=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
      if (showToast) toast('Status refreshed.');
    } catch (error) {
      $('overallStatus').textContent = 'Could not load monitor data';
      $('lastChecked').textContent = 'Check the GitHub Pages deployment and data file.';
      if (showToast) toast('Could not refresh the status.');
      console.error('PokéDrop status load failed:', error);
    } finally {
      button.classList.remove('spinning');
    }
  }
  let toastTimer;
  function toast(message) {
    const element = $('toast');
    element.textContent = message;
    element.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => element.classList.remove('show'), 2200);
  }
  configureAlertTypeFilters();
  $('refreshButton').addEventListener('click', () => refresh(true));
  $('alertSearch').addEventListener('input', (event) => { state.query = event.target.value; renderEvents(); });
  $('categoryFilter').addEventListener('change', (event) => { state.category = event.target.value; renderEvents(); });
  $('retailerFilter').addEventListener('change', (event) => { state.retailer = event.target.value; renderEvents(); });
  $('exactMatch').addEventListener('change', (event) => { state.exact = event.target.checked; renderEvents(); });
  $('alertsViewButton').addEventListener('click', () => {
    state.view = 'alerts';
    $('alertsViewButton').classList.add('active');
    $('productsViewButton').classList.remove('active');
    renderEvents();
  });
  $('productsViewButton').addEventListener('click', () => {
    state.view = 'products';
    $('productsViewButton').classList.add('active');
    $('alertsViewButton').classList.remove('active');
    renderEvents();
  });
  document.querySelectorAll('.filter-chip').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.filter-chip').forEach(chip => chip.classList.toggle('active', chip === button));
    state.filter = button.dataset.filter;
    renderEvents();
  }));
  refresh();
  setInterval(() => refresh(false), 5 * 60 * 1000);
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
  }
})();
