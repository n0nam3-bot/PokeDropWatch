(() => {
  'use strict';
  const grid = document.getElementById('sourceGrid');
  if (!grid || !window.MutationObserver) return;
  let rebuilding = false;
  let queued = false;

  const textNode = (className, text) => {
    const node = document.createElement('div');
    node.className = className;
    node.textContent = text;
    return node;
  };
  const sourceMessage = card => card.querySelector('.source-bottom span')?.title || '';
  const parseName = title => {
    const parts = String(title || '').split(/\s*·\s*/);
    return parts.length > 1
      ? { retailer: parts.shift().trim(), route: parts.join(' · ').trim() }
      : { retailer: String(title || 'Other'), route: 'Catalog' };
  };
  const classify = card => {
    const badge = (card.querySelector('.source-state')?.textContent || '').trim().toUpperCase();
    const message = sourceMessage(card).toLowerCase();
    if (/fallback recognized/.test(message)) return 'FALLBACK';
    if (/access protection blocked|access challenge|captcha|robot or human|pardon our interruption/.test(message)) return 'BLOCKED';
    if (badge === 'ISSUE' || /request failed|all available source routes failed/.test(message)) return 'ISSUE';
    if (badge === 'MATCHES' || badge === 'OK') return 'MATCHES';
    return 'NO MATCH';
  };
  const tone = label => label === 'MATCHES' ? 'ok' : label === 'ISSUE' ? 'error' : 'warn';
  const checkedText = card => {
    const detail = card.querySelector('.source-bottom span')?.textContent || '';
    const match = detail.match(/(\d+)\/(\d+) pages responded/);
    const count = Number((detail.match(/(\d+) Pokémon listings/) || [])[1] || (sourceMessage(card).match(/recognized (\d+) current item/) || [])[1] || 0);
    if (match && Number(match[1]) > 0 && count > 0) return `${count} items found`;
    if (classify(card) === 'BLOCKED') return 'Blocked by retailer';
    if (classify(card) === 'ISSUE') return 'Request failed';
    if (classify(card) === 'FALLBACK') return 'Backup route found items';
    return 'No items found';
  };

  function makeGroup(retailer, cards) {
    const group = document.createElement('article');
    group.className = 'source-retailer-card';
    const labels = cards.map(classify);
    const aggregate = labels.every(x => x === 'ISSUE') ? 'ISSUE'
      : labels.some(x => x === 'MATCHES' || x === 'FALLBACK') ? 'MATCHES'
        : labels.some(x => x === 'BLOCKED') ? 'BLOCKED' : 'NO MATCH';

    const head = document.createElement('div');
    head.className = 'source-retailer-heading';
    const identity = document.createElement('div');
    identity.append(textNode('source-retailer-name', retailer));
    const categoryNames = cards.map(card => parseName(card.querySelector('.source-name')?.textContent).route);
    identity.append(textNode('source-retailer-kind', categoryNames.join(' · ')));
    const badge = document.createElement('span');
    badge.className = `source-state ${tone(aggregate)}`;
    badge.textContent = aggregate;
    head.append(identity, badge);

    const routes = document.createElement('div');
    routes.className = 'source-retailer-routes';
    cards.forEach(card => {
      const info = parseName(card.querySelector('.source-name')?.textContent);
      const oldBottom = card.querySelector('.source-bottom');
      const row = document.createElement('div');
      row.className = 'source-route-row';
      const routeHead = document.createElement('div');
      routeHead.className = 'source-route-heading';
      routeHead.append(textNode('source-route-name', info.route));
      const routeLabel = classify(card);
      const routeBadge = document.createElement('span');
      routeBadge.className = `source-state ${tone(routeLabel)}`;
      routeBadge.textContent = routeLabel;
      routeHead.append(routeBadge);

      const bottom = document.createElement('div');
      bottom.className = 'source-route-bottom';
      const detail = document.createElement('span');
      detail.textContent = checkedText(card);
      detail.title = sourceMessage(card) || detail.textContent;
      bottom.append(detail);
      const link = oldBottom?.querySelector('a');
      if (link) bottom.append(link.cloneNode(true));
      row.append(routeHead, bottom);
      routes.append(row);
    });
    group.append(head, routes);
    return group;
  }

  function regroup() {
    queued = false;
    if (rebuilding) return;
    const cards = [...grid.children].filter(node => node.classList.contains('source-card'));
    if (!cards.length) return;
    rebuilding = true;
    const groups = new Map();
    cards.forEach(card => {
      const info = parseName(card.querySelector('.source-name')?.textContent || 'Other');
      if (!groups.has(info.retailer)) groups.set(info.retailer, []);
      groups.get(info.retailer).push(card);
    });
    const fragment = document.createDocumentFragment();
    for (const [retailer, routes] of groups) fragment.append(makeGroup(retailer, routes));
    grid.replaceChildren(fragment);
    const matched = [...groups.values()].filter(routes => routes.some(card => ['MATCHES', 'FALLBACK'].includes(classify(card)))).length;
    const issue = [...groups.values()].filter(routes => routes.every(card => classify(card) === 'ISSUE')).length;
    const warning = [...groups.values()].filter(routes => routes.some(card => ['BLOCKED', 'NO MATCH'].includes(classify(card)))).length;
    const count = document.getElementById('sourceCount');
    if (count) count.textContent = `${groups.size} source groups`;
    const online = document.getElementById('onlineCount');
    if (online) online.textContent = `${matched}/${groups.size}`;
    const label = document.querySelector('#onlineCount')?.parentElement?.querySelector('.metric-label');
    if (label) label.textContent = 'SOURCES WITH MATCHES';
    const caption = document.querySelector('#onlineCount')?.parentElement?.querySelector('.metric-caption');
    if (caption) caption.textContent = 'sources returning recognized products or news';
    const status = document.getElementById('overallStatus');
    if (status) status.textContent = `${matched} matches · ${warning} warnings · ${issue} request issues`;
    rebuilding = false;
  }
  function schedule() {
    if (queued || rebuilding) return;
    queued = true;
    window.requestAnimationFrame(regroup);
  }
  new MutationObserver(schedule).observe(grid, { childList: true });
  schedule();
})();
