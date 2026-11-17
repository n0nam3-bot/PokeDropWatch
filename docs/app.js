(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const state = { events: [], products: [], filter: 'all', category: 'all', retailer: 'all', query: '', exact: false, view: 'alerts' };
  const labels = { new_drop: 'NEW DROP', restock: 'RESTOCK', price_drop: 'PRICE DROP', price_change: 'PRICE UPDATE', news: 'POKÉMON NEWS' };
  const icons = { new_drop: '✦', restock: '↻', price_drop: '↓', price_change: '↕', news: '✧' };
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
    if (/(trading card|pokemon tcg|booster|elite trainer|trainer box|card collection|battle deck|theme deck|blister|pokemon cards|trading cards| etb )/.test(` ${title} `)) return 'tcg';
    if (/(plush|stuffed animal|soft toy|plushie)/.test(title)) return 'plush';
    if (/(nintendo switch|switch game|video game|game card|pokemon legends|pokemon scarlet|pokemon violet|pokemon sword|pokemon shield|brilliant diamond|shining pearl|pokemon arceus|pokemon game)/.test(title)) return 'games';
    if (/(binder|deck box|playmat|sleeves|backpack|keychain|key chain|apparel|shirt|hoodie|hat|blanket|wallet|bottle|accessor|lunch box|pin set)/.test(title)) return 'accessories';
    return ['tcg', 'plush', 'collectibles', 'games', 'accessories'].includes(item.category) ? item.category : 'collectibles';
  };
  const money = (value, currency = 'USD') => {
    if (value === null || value === undefined || value === '') return 'Price not listed';
    try { return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'USD' }).format(Number(value)); }
    catch { return `$${Number(value).toFixed(2)}`; }
  };
  const dateText = (value) => {
    if (!value) return 'Not scanned yet';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
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
      badge.title = source.message || stateLabel;
      top.append(left, badge);
      const bottom = node('div', 'source-bottom');
      let description = `${source.items_found || 0} relevant`;
      if (status !== 'ok' && source.message) description = source.message;
      const detail = node('span', '', description.slice(0, 100));
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
    const result = [];
    for (const [sourceId, sourceState] of Object.entries(items || {})) {
      const products = sourceState && sourceState.products;
      if (!products || typeof products !== 'object') continue;
      for (const product of Object.values(products)) {
        if (!product || !isPokemonItem(product)) continue;
        result.push({ ...product, source_id: sourceId, retailer_key: retailerKey(product) });
      }
    }
    result.sort((a, b) => String(b.last_seen || '').localeCompare(String(a.last_seen || '')));
    return result;
  }
  function populateRetailerFilter() {
    const select = $('retailerFilter');
    if (!select) return;
    const selected = state.retailer;
    const items = [...state.events, ...state.products];
    const retailers = [...new Map(items.map(item => [retailerKey(item), String(item.retailer || item.source_name || 'Other')])).entries()]
      .sort((a, b) => a[1].localeCompare(b[1]));
    select.replaceChildren(new Option('All retailers', 'all'));
    retailers.forEach(([key, label]) => select.add(new Option(label, key)));
    select.value = retailers.some(([key]) => key === selected) ? selected : 'all';
    state.retailer = select.value;
  }
  function itemMatches(item, includeAlertType = false) {
    const category = inferCategory(item);
    const typeOk = !includeAlertType || state.filter === 'all' || item.type === state.filter;
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
    actions.append(node('span', `type-badge ${isTracked ? 'tracked' : item.type || ''}`, isTracked ? 'TRACKED ITEM' : (labels[item.type] || 'UPDATE')));
    const view = node('a', 'view-link', isTracked ? 'VIEW PRODUCT ↗' : 'VIEW ITEM ↗');
    view.href = safeLink(item.url); view.target = '_blank'; view.rel = 'noopener noreferrer';
    actions.append(view);
    content.append(actions);
    const price = node('div', 'alert-price');
    price.append(node('strong', '', money(item.price, item.currency)));
    let extra = item.availability && item.availability !== 'unknown'
      ? item.availability.replaceAll('_', ' ')
      : 'Check retailer for stock';
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
      : 'Alerts show changes detected after a source’s first baseline scan. Existing products are tracked separately and do not generate a false new-drop alert.';
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
      ? `${matches} sources with matches · ${warnings} no matches · ${failures} errors`
      : 'Waiting for first scan';
    $('overallLed').className = `status-led ${sources.length && failures === 0 && warnings === 0 ? 'ok' : sources.length ? 'warn' : ''}`;
    $('lastChecked').textContent = data.last_checked ? `Last checked ${dateText(data.last_checked)}` : 'The first scan runs after setup.';
    renderSources(sources);
    state.events = (data.events || []).filter(isPokemonItem);
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
  // Poll only the public status JSON; retailer checks run on the scheduled workflow.
  setInterval(() => refresh(false), 5 * 60 * 1000);
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
  }
})();
