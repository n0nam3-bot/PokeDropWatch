(() => {
  'use strict';
  const stateUrl = `./data/state.json?v=${Date.now()}`;
  const $ = (id) => document.getElementById(id);
  const state = { events: [], filter: 'all', query: '' };
  const labels = { new_drop: 'NEW DROP', restock: 'RESTOCK', price_drop: 'PRICE DROP', price_change: 'PRICE UPDATE', news: 'POKÉMON NEWS' };
  const icons = { new_drop: '✦', restock: '↻', price_drop: '↓', price_change: '↕', news: '✧' };
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
  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function renderSources(sources = []) {
    const grid = $('sourceGrid');
    grid.replaceChildren();
    $('sourceCount').textContent = `${sources.length || 8} configured`;
    if (!sources.length) {
      grid.append(node('div', 'empty-state', 'Source status will appear after the first scan.'));
      return;
    }
    for (const source of sources) {
      const card = node('article', 'source-card');
      const top = node('div', 'source-top');
      const left = node('div');
      left.append(node('div', 'source-name', source.name || source.id));
      left.append(node('div', 'source-kind', source.type || 'source'));
      top.append(left, node('span', `source-state ${source.status === 'ok' ? 'ok' : 'error'}`, source.status === 'ok' ? 'ONLINE' : 'ISSUE'));
      const bottom = node('div', 'source-bottom');
      bottom.append(node('span', source.status === 'ok' ? `${source.items_found || 0} found` : (source.message || 'Scan unavailable').slice(0, 44)));
      const link = node('a', '', 'OPEN ↗');
      link.href = safeLink(source.url);
      link.target = '_blank'; link.rel = 'noopener noreferrer';
      bottom.append(link);
      card.append(top, bottom);
      grid.append(card);
    }
  }
  function renderEvents() {
    const list = $('alertList');
    list.replaceChildren();
    const filtered = state.events.filter((event) => {
      const typeOk = state.filter === 'all' || event.type === state.filter;
      const phrase = `${event.title || ''} ${event.retailer || ''} ${event.summary || ''}`.toLowerCase();
      return typeOk && phrase.includes(state.query);
    });
    if (!filtered.length) {
      const empty = node('div', 'empty-state large-empty');
      empty.append(node('span', 'empty-ball', '◉'));
      empty.append(node('strong', '', state.events.length ? 'No matching alerts' : 'No alerts yet'));
      empty.append(node('span', '', state.events.length ? 'Try another filter or search term.' : 'Once the monitor completes its first scan, new drops and changes will show here.'));
      list.append(empty);
      return;
    }
    for (const event of filtered) {
      const card = node('article', 'alert-card');
      const iconClass = event.type === 'restock' ? 'alert-icon restock' : event.type === 'news' ? 'alert-icon news' : 'alert-icon';
      card.append(node('div', iconClass, icons[event.type] || '•'));
      const content = node('div');
      content.append(node('div', 'alert-title', event.title || 'Pokémon item update'));
      const meta = node('div', 'alert-meta');
      meta.append(node('span', '', event.retailer || event.source_name || 'Source'));
      meta.append(node('span', '', '·'));
      meta.append(node('span', '', dateText(event.detected_at)));
      content.append(meta);
      const actions = node('div', 'alert-actions');
      actions.append(node('span', `type-badge ${event.type || ''}`, labels[event.type] || 'UPDATE'));
      const view = node('a', 'view-link', 'VIEW ITEM ↗');
      view.href = safeLink(event.url); view.target = '_blank'; view.rel = 'noopener noreferrer';
      actions.append(view);
      content.append(actions);
      const price = node('div', 'alert-price');
      price.append(node('strong', '', money(event.price, event.currency)));
      let extra = event.availability && event.availability !== 'unknown' ? event.availability.replaceAll('_', ' ') : 'Check retailer for stock';
      if (event.previous_price !== null && event.previous_price !== undefined) extra += ` · was ${money(event.previous_price, event.currency)}`;
      price.append(node('span', '', extra));
      card.append(content, price);
      list.append(card);
    }
  }
  function render(data) {
    const summary = data.summary || {};
    const sources = data.source_status || [];
    const ok = sources.filter(s => s.status === 'ok').length;
    $('onlineCount').textContent = `${ok}/${sources.length || summary.enabled_sources || 8}`;
    $('listingCount').textContent = String(summary.tracked_products ?? '—');
    $('alertCount').textContent = String(summary.new_alerts ?? 0);
    $('overallStatus').textContent = sources.length ? (ok === sources.length ? 'All configured sources scanned' : `${ok} of ${sources.length} sources scanned`) : 'Waiting for first scan';
    $('overallLed').className = `status-led ${sources.length && ok === sources.length ? 'ok' : sources.length ? 'warn' : ''}`;
    $('lastChecked').textContent = data.last_checked ? `Last checked ${dateText(data.last_checked)}` : 'The first scan runs after setup.';
    $('sourceCount').textContent = `${summary.enabled_sources || sources.length || 8} configured`;
    renderSources(sources);
    state.events = data.events || [];
    renderEvents();
    if (data.email_status) $('lastChecked').title = `Email: ${data.email_status}`;
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
  $('alertSearch').addEventListener('input', (event) => { state.query = event.target.value.trim().toLowerCase(); renderEvents(); });
  document.querySelectorAll('.filter-chip').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.filter-chip').forEach(chip => chip.classList.toggle('active', chip === button));
    state.filter = button.dataset.filter;
    renderEvents();
  }));
  refresh();
  // Poll only the small public status JSON; the actual retailer checks run in GitHub Actions.
  setInterval(() => refresh(false), 5 * 60 * 1000);
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
  }
})();
