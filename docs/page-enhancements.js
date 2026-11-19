(() => {
  'use strict';
  const body = document.body;
  const isNotify = body.classList.contains('page-notify');
  const isAdmin = body.classList.contains('page-admin');
  const isInfo = body.classList.contains('page-info');
  const sprite = isAdmin ? './assets/icons/masterball-8bit.png'
    : isNotify ? './assets/icons/ultraball-8bit.png'
      : './assets/icons/pokeball-8bit.png';

  // Load the shared sizing, typography and listing layout after legacy styles.
  if (!document.querySelector('link[data-pd-uniform]')) {
    const css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = './site-uniform.css';
    css.dataset.pdUniform = 'true';
    document.head.append(css);
  }

  // Notify and Admin keep a single link to the shared explanation page.
  const guideUrl = './SOURCE_HEALTH.html';
  const guideLink = () => {
    const p = document.createElement('p');
    p.className = 'pd-how-link';
    const a = document.createElement('a');
    a.href = guideUrl;
    a.textContent = 'How it works ↗';
    p.append(a);
    return p;
  };
  document.querySelectorAll('.portal-fallback').forEach(node => {
    node.replaceWith(guideLink());
  });
  document.querySelectorAll('.notify-heading').forEach(node => node.remove());

  // One shared, centered attribution footer on every outer page.
  const footerText = 'Fan-made tracker · Not affiliated with Pokémon or retailers · ';
  const repoUrl = 'https://github.com/n0nam3-bot/PokeDropWatch';
  const existingFooter = document.querySelector('.public-footer-note, .footer');
  if (existingFooter) {
    existingFooter.className = 'pd-site-footer';
    existingFooter.replaceChildren(document.createTextNode(footerText));
    const link = document.createElement('a');
    link.href = repoUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'View the source repository ↗';
    existingFooter.append(link);
  } else {
    const footer = document.createElement('footer');
    footer.className = 'pd-site-footer';
    footer.append(document.createTextNode(footerText));
    const link = document.createElement('a');
    link.href = repoUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'View the source repository ↗';
    footer.append(link);
    document.querySelector('.site-shell')?.append(footer);
  }

  // Keep the guide page's top-right action the same size as the other page actions.
  if (isInfo) {
    const back = document.querySelector('.health-wrap .topbar .text-link');
    if (back) {
      back.className = 'icon-button';
      back.textContent = '⌂';
      back.setAttribute('aria-label', 'Return to Pallet Town');
      back.title = 'Return to Pallet Town';
    }
    document.querySelectorAll('.health-card p, .health-card li').forEach(node => {
      node.innerHTML = node.innerHTML.replace(/\badministrator\b/gi, 'Gym Leader');
    });
  }

  // Add the same bottom navigation to the guide page if it does not already have it.
  if (isInfo && !document.querySelector('.bottom-bar')) {
    const nav = document.createElement('nav');
    nav.className = 'bottom-bar';
    nav.setAttribute('aria-label', 'Quick navigation');
    nav.innerHTML = '<div class="bottom-bar-inner">' +
      '<a href="./#top"><span aria-hidden="true">⌂</span><small>Home</small></a>' +
      '<a href="./#alerts"><span aria-hidden="true">▤</span><small>Alerts</small></a>' +
      '<a href="./notify.html"><span aria-hidden="true">✉</span><small>Notify</small></a>' +
      '<a href="./admin.html"><span aria-hidden="true">⚙</span><small>Admin</small></a>' +
      '<a href="' + repoUrl + '" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">↗</span><small>GitHub</small></a>' +
      '</div>';
    document.body.append(nav);
  }

  // On Home, the page location label changes as the Alerts section enters view.
  const locationLabel = document.getElementById('pageLocation');
  const alertsSection = document.getElementById('alerts');
  if (locationLabel && alertsSection) {
    let queued = false;
    const updateLocation = () => {
      queued = false;
      const topbar = document.querySelector('.topbar');
      const topbarHeight = topbar ? topbar.getBoundingClientRect().height : 78;
      const threshold = alertsSection.getBoundingClientRect().top + window.scrollY - topbarHeight - 24;
      // Use scroll position rather than the URL hash: scrolling back above Alerts
      // must switch the location back to Pallet Town even while #alerts remains.
      locationLabel.textContent = window.scrollY >= threshold ? 'POKÉDEX' : 'PALLET TOWN';
    };
    const schedule = () => {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(updateLocation);
    };
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('hashchange', schedule);
    window.addEventListener('resize', schedule, { passive: true });
    updateLocation();
  }

  // The homepage keeps the original single 8-bit Poké Ball sprite from index.html.

  const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const activeThrows = new Set();
  function throwBall(x, y) {
    if (reducedMotion) return;
    const sx = Math.round(window.innerWidth * .5 - 18);
    const sy = Math.round(window.innerHeight + 18);
    const ball = document.createElement('img');
    ball.className = 'pd-throw-ball';
    ball.src = sprite;
    ball.alt = '';
    ball.setAttribute('aria-hidden', 'true');
    ball.style.left = sx + 'px';
    ball.style.top = sy + 'px';
    ball.style.setProperty('--pd-dx', (Math.round(x) - sx) + 'px');
    ball.style.setProperty('--pd-dy', (Math.round(y) - sy) + 'px');
    body.append(ball);
    activeThrows.add(ball);
    requestAnimationFrame(() => ball.classList.add('is-throwing'));
    const flash = document.createElement('span');
    flash.className = 'pd-capture-flash';
    flash.style.left = Math.round(x) + 'px';
    flash.style.top = Math.round(y) + 'px';
    body.append(flash);
    window.setTimeout(() => {
      ball.remove(); flash.remove(); activeThrows.delete(ball);
    }, 950);
  }
  function randomSpread(x, y) {
    const width = Math.max(1, window.innerWidth);
    const height = Math.max(1, window.innerHeight);
    // Wide fan around the press point, with some throws reaching the page edges.
    const spreadX = (Math.random() - .5) * width * .9;
    const spreadY = (Math.random() - .5) * height * .72;
    return {
      x: Math.max(18, Math.min(width - 18, x + spreadX)),
      y: Math.max(28, Math.min(height - 48, y + spreadY))
    };
  }

  let press = null;
  function stopRapidFire() {
    if (!press) return;
    clearTimeout(press.holdTimer);
    clearInterval(press.repeatTimer);
    press = null;
  }
  document.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (event.target?.closest('input,textarea,select,option,[contenteditable="true"]')) return;
    stopRapidFire();
    press = { x: event.clientX, y: event.clientY, long: false, holdTimer: 0, repeatTimer: 0 };
    const state = press;
    state.holdTimer = window.setTimeout(() => {
      if (press !== state) return;
      state.long = true;
      const first = randomSpread(state.x, state.y);
      throwBall(first.x, first.y);
      state.repeatTimer = window.setInterval(() => {
        if (activeThrows.size >= 16) return;
        const next = randomSpread(state.x, state.y);
        throwBall(next.x, next.y);
      }, 145);
    }, 1000);
  }, { passive: true });
  document.addEventListener('pointermove', event => {
    if (press) { press.x = event.clientX; press.y = event.clientY; }
  }, { passive: true });
  const release = event => {
    if (!press) return;
    const state = press;
    state.x = event.clientX ?? state.x;
    state.y = event.clientY ?? state.y;
    if (!state.long) throwBall(state.x, state.y);
    stopRapidFire();
  };
  document.addEventListener('pointerup', release, { passive: true });
  document.addEventListener('pointercancel', stopRapidFire, { passive: true });
  window.addEventListener('blur', stopRapidFire);

  // Product images are links too: clicking the image opens the same item URL.
  document.addEventListener('click', event => {
    const image = event.target?.closest('.alert-product-image');
    if (!image) return;
    const card = image.closest('.alert-card');
    const link = card?.querySelector('.view-link');
    if (!link?.href) return;
    event.preventDefault();
    window.open(link.href, '_blank', 'noopener,noreferrer');
  });

  // Capture newly appearing listings and animate the page's 8-bit header ball.
  const alertList = document.getElementById('alertList');
  if (alertList) {
    const seen = new Set();
    let initial = false;
    let queued = false;
    const cardKey = card => ((card.querySelector('.alert-meta span')?.textContent || '') + '|' +
      (card.querySelector('.alert-title')?.textContent || '')).toLowerCase();
    const process = () => {
      queued = false;
      alertList.querySelectorAll('.alert-price span').forEach(span => {
        if (/^First observed by PokéDrop Watch/i.test(span.textContent.trim())) span.remove();
      });
      const cards = [...alertList.querySelectorAll('.alert-card')];
      if (!cards.length) return;
      if (!initial) { cards.forEach(card => seen.add(cardKey(card))); initial = true; return; }
      cards.forEach(card => {
        const key = cardKey(card);
        if (seen.has(key)) return;
        seen.add(key);
        const badge = card.querySelector('.type-badge');
        if (!badge || !/FIRST SEEN|NEW ITEM/i.test(badge.textContent || '')) return;
        const media = card.querySelector('.alert-media');
        if (media && !media.querySelector('.capture-ball')) {
          const icon = document.createElement('img');
          icon.className = 'capture-ball';
          icon.src = './assets/icons/pokeball-8bit.png';
          icon.alt = '';
          icon.setAttribute('aria-hidden', 'true');
          media.append(icon);
        }
        const headerBall = document.querySelector('.page-ball');
        if (headerBall) {
          headerBall.classList.remove('capture-wiggle');
          void headerBall.offsetWidth;
          headerBall.classList.add('capture-wiggle');
          headerBall.addEventListener('animationend', () => headerBall.classList.remove('capture-wiggle'), { once: true });
        }
      });
    };
    const queue = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(process);
    };
    new MutationObserver(queue).observe(alertList, { childList: true, subtree: true });
    queue();
  }
})();
