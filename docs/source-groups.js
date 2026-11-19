(() => {
  'use strict';

  const grid = document.getElementById('sourceGrid');
  if (!grid || !window.MutationObserver) return;

  let queued = false;
  let rebuilding = false;

  function splitSourceTitle(title) {
    const parts = String(title || '').split(/\s*·\s*/);
    if (parts.length < 2) return { retailer: String(title || 'Other'), route: 'Catalog' };
    return { retailer: parts.shift().trim(), route: parts.join(' · ').trim() || 'Catalog' };
  }

  function sourceMessage(card) {
    return card.querySelector('.source-bottom span')?.title || '';
  }

  function statusClass(card) {
    const badge = card.querySelector('.source-state');
    const message = sourceMessage(card);
    const label = (badge?.textContent || '').trim().toUpperCase();
    if (/scheduled for a later retailer rotation/i.test(message)) return 'scheduled';
    if (/all available route checks failed|all configured urls failed/i.test(message)) return 'error';
    if (badge?.classList.contains('error') || label === 'ISSUE') return 'error';
    if (/through a fallback route|cooldown/i.test(message) || label === 'PARTIAL') return 'partial';
    if (label === 'NO MATCH') return 'no-match';
    if (badge?.classList.contains('warn')) return 'no-match';
    return 'ok';
  }

  function makeText(className, value) {
    const element = document.createElement('div');
    element.className = className;
    element.textContent = value;
    return element;
  }

  function makeGroup(retailer, cards) {
    const wrapper = document.createElement('article');
    wrapper.className = 'source-retailer-card';

    const states = cards.map(card => statusClass(card));
    const scheduled = states.filter(value => value === 'scheduled').length;
    const activeStates = states.filter(value => value !== 'scheduled');
    const healthy = activeStates.filter(value => value === 'ok').length;
    const noMatches = activeStates.filter(value => value === 'no-match').length;
    const partials = activeStates.filter(value => value === 'partial').length;
    const failures = activeStates.filter(value => value === 'error').length;
    const aggregateClass = !activeStates.length ? 'neutral' : failures === activeStates.length ? 'error'
      : (partials || failures || (healthy && noMatches)) ? 'warn'
        : noMatches === activeStates.length ? 'warn' : 'ok';
    const aggregateLabel = aggregateClass === 'neutral' ? 'SCHEDULED'
      : aggregateClass === 'error' ? 'ISSUE'
        : noMatches === activeStates.length && !partials && !failures ? 'NO MATCH'
          : aggregateClass === 'warn' ? 'PARTIAL' : 'MATCHES';

    const heading = document.createElement('div');
    heading.className = 'source-retailer-heading';
    const identity = document.createElement('div');
    identity.className = 'source-retailer-identity';
    identity.append(
      makeText('source-retailer-name', retailer),
      makeText('source-retailer-kind', cards.length === 1
        ? '1 monitoring route'
        : `${cards.length} category routes`)
    );
    const aggregate = document.createElement('span');
    aggregate.className = `source-state ${aggregateClass}`;
    aggregate.textContent = aggregateLabel;
    aggregate.title = `${healthy} matching · ${noMatches} no-match · ${partials} fallback/partial · ${failures} request error(s) · ${scheduled} scheduled for later intervals`;
    heading.append(identity, aggregate);

    const routes = document.createElement('div');
    routes.className = 'source-retailer-routes';

    cards.forEach(card => {
      const oldName = card.querySelector('.source-name')?.textContent || '';
      const routeInfo = splitSourceTitle(oldName);
      const route = document.createElement('section');
      route.className = 'source-route-row';

      const routeHead = document.createElement('div');
      routeHead.className = 'source-route-heading';
      const routeIdentity = document.createElement('div');
      routeIdentity.className = 'source-route-identity';
      routeIdentity.append(
        makeText('source-route-name', routeInfo.route),
        makeText('source-route-kind', card.querySelector('.source-kind')?.textContent || 'source')
      );
      const oldBadge = card.querySelector('.source-state');
      const oldBottom = card.querySelector('.source-bottom');
      const message = sourceMessage(card);
      if (oldBadge) {
        const routeBadge = oldBadge.cloneNode(true);
        if (statusClass(card) === 'scheduled') {
          routeBadge.className = 'source-state neutral';
          routeBadge.textContent = 'SCHEDULED';
        } else if (statusClass(card) === 'error') {
          routeBadge.className = 'source-state error';
          routeBadge.textContent = 'ISSUE';
        } else if (/skipped this category route during the retailer .* cooldown/i.test(message)) {
          routeBadge.className = 'source-state warn';
          routeBadge.textContent = 'COOLDOWN';
        } else if (/through a fallback route/i.test(message)) {
          routeBadge.className = 'source-state warn';
          routeBadge.textContent = 'FALLBACK';
        } else if (/retailer access protection blocked|access challenge/i.test(message)) {
          routeBadge.className = 'source-state warn';
          routeBadge.textContent = 'BLOCKED';
        }
        routeHead.append(routeIdentity, routeBadge);
      } else routeHead.append(routeIdentity);

      const bottom = document.createElement('div');
      bottom.className = 'source-route-bottom';
      if (oldBottom) {
        const oldDetail = oldBottom.querySelector('span');
        const detail = document.createElement('span');
        const retained = message.match(/Last-known catalog retained:\s*(\d+)|(?:^|\s)(\d+)\s+last-known (?:listing|article)\(s\) retained/i);
        const retainedCount = retained ? (retained[1] || retained[2]) : '';
        const recovered = message.match(/(?:Recovered|Recognized)\s+(\d+)\s+current (listing|article)\(s\) through a fallback route/i);
        const lastScanned = message.match(/Last scanned:\s*([0-9TZ:.+\-]+?)(?=\.\s|\s|$)/i);
        if (statusClass(card) === 'scheduled') {
          detail.textContent = `Scheduled route · no request this interval${lastScanned ? ` · last checked ${lastScanned[1]}` : ' · not scanned yet'}`
            + (retainedCount ? ` · ${retainedCount} last-known record(s) retained` : '');
        } else if (/skipped this category route during the retailer .* cooldown/i.test(message)) {
          detail.textContent = retainedCount
            ? `Retailer cooldown active · no request made · ${retainedCount} last-known record(s) retained`
            : 'Retailer cooldown active · no new request made';
        } else if (recovered) {
          detail.textContent = `Fallback matched ${recovered[1]} current ${recovered[2]}(s); primary route did not provide usable entries`;
        } else if (/retailer access protection blocked|access challenge/i.test(message)) {
          detail.textContent = retainedCount
            ? `Blocked by retailer access protection · ${retainedCount} last-known record(s) retained`
            : 'Blocked by retailer access protection · current entries unconfirmed';
        } else if (retainedCount) {
          detail.textContent = `No current entries confirmed · ${retainedCount} last-known record(s) retained`;
        } else if (/all available route checks failed|all configured urls failed/i.test(message)) {
          detail.textContent = 'Request failed · no current inventory confirmed';
        } else if (/access challenge|access protection|blocked/i.test(message)) {
          detail.textContent = 'Retailer access protection blocked this route · current inventory unconfirmed';
        } else if (oldDetail) {
          detail.textContent = oldDetail.textContent;
        } else {
          detail.textContent = 'Route status unavailable';
        }
        detail.title = message || detail.textContent;
        bottom.append(detail);
        const oldLink = oldBottom.querySelector('a');
        if (oldLink) bottom.append(oldLink.cloneNode(true));
      }
      route.append(routeHead, bottom);
      routes.append(route);
    });

    wrapper.append(heading, routes);
    return wrapper;
  }

  function regroup() {
    queued = false;
    if (rebuilding) return;
    const routeCards = [...grid.children].filter(child => child.classList.contains('source-card'));
    if (!routeCards.length) return;

    rebuilding = true;
    const groups = new Map();
    routeCards.forEach(card => {
      const info = splitSourceTitle(card.querySelector('.source-name')?.textContent || 'Other');
      if (!groups.has(info.retailer)) groups.set(info.retailer, []);
      groups.get(info.retailer).push(card);
    });

    const fragment = document.createDocumentFragment();
    for (const [retailer, cards] of groups) fragment.append(makeGroup(retailer, cards));
    grid.replaceChildren(fragment);

    const matchingRetailers = [...groups.values()].filter(cards => cards.some(card => {
      const message = sourceMessage(card);
      const current = message.match(/(?:Primary route recognized|Recovered|Recognized)\s+(\d+)\s+current (?:listing|article)\(s\)/i);
      return Boolean(current && Number(current[1]) > 0);
    })).length;
    const requestErrorRetailers = [...groups.values()].filter(cards =>
      cards.some(card => statusClass(card) === 'error')
    ).length;
    const warningRetailers = [...groups.values()].filter(cards =>
      cards.some(card => ['partial', 'no-match'].includes(statusClass(card)))
    ).length;

    const count = document.getElementById('sourceCount');
    if (count) {
      count.textContent = `${groups.size} retailers · ${routeCards.length} monitoring routes`;
    }
    const onlineCount = document.getElementById('onlineCount');
    if (onlineCount) onlineCount.textContent = `${matchingRetailers}/${groups.size}`;
    const metricLabel = document.querySelector('#onlineCount')?.parentElement?.querySelector('.metric-label');
    if (metricLabel) metricLabel.textContent = 'RETAILERS WITH MATCHES';
    const metricCaption = document.querySelector('#onlineCount')?.parentElement?.querySelector('.metric-caption');
    if (metricCaption) metricCaption.textContent = 'retailers whose scheduled route returned current product or news matches';
    const overallStatus = document.getElementById('overallStatus');
    if (overallStatus) {
      const scheduledRoutes = [...groups.values()].flat().filter(card => statusClass(card) === 'scheduled').length;
      overallStatus.textContent = `${matchingRetailers} retailer matches · ${warningRetailers} with route warnings · ${requestErrorRetailers} with request errors · ${scheduledRoutes} routes scheduled`;
    }
    const overallLed = document.getElementById('overallLed');
    if (overallLed) {
      overallLed.className = `status-led ${warningRetailers === 0 && requestErrorRetailers === 0 ? 'ok' : 'warn'}`;
    }
    rebuilding = false;
  }

  function scheduleRegroup() {
    if (queued || rebuilding) return;
    queued = true;
    window.requestAnimationFrame(regroup);
  }

  new MutationObserver(scheduleRegroup).observe(grid, { childList: true });
  scheduleRegroup();
})();
