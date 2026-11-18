(() => {
  'use strict';
  const body = document.body;
  const isNotify = body.classList.contains('page-notify');
  const isAdmin = body.classList.contains('page-admin');
  const isInfo = body.classList.contains('page-info');
  const sprite = isAdmin ? './assets/icons/masterball-8bit.png'
    : isNotify ? './assets/icons/ultraball-8bit.png'
      : './assets/icons/pokeball-8bit.png';

  // The home document also contains the Alerts view, so its location name follows scroll position.
  const locationLabel = document.getElementById('pageLocation');
  const alertsSection = document.getElementById('alerts');
  if (locationLabel && alertsSection) {
    let scheduled = false;
    const updateLocation = () => {
      scheduled = false;
      const threshold = alertsSection.getBoundingClientRect().top + window.scrollY - 135;
      locationLabel.textContent = (location.hash === '#alerts' || window.scrollY >= threshold)
        ? 'POKÉDEX' : 'PALLET TOWN';
    };
    const scheduleLocationUpdate = () => {
      if (scheduled) return;
      scheduled = true;
      window.requestAnimationFrame(updateLocation);
    };
    window.addEventListener('scroll', scheduleLocationUpdate, { passive: true });
    window.addEventListener('hashchange', scheduleLocationUpdate);
    document.querySelectorAll('.bottom-bar a[href="#alerts"]').forEach(link => link.addEventListener('click', () => {
      locationLabel.textContent = 'POKÉDEX';
    }));
    document.querySelectorAll('.bottom-bar a[href="#top"]').forEach(link => link.addEventListener('click', () => {
      locationLabel.textContent = 'PALLET TOWN';
    }));
    updateLocation();
  }

  // Throw the current page's ball sprite from the bottom of the screen to the pointer/tap.
  const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function throwBall(x, y) {
    if (reducedMotion || !body) return;
    const startX = Math.round(window.innerWidth * 0.5 - 18);
    const startY = Math.round(window.innerHeight + 18);
    const ball = document.createElement('img');
    ball.className = 'pd-throw-ball';
    ball.src = sprite;
    ball.alt = '';
    ball.setAttribute('aria-hidden', 'true');
    ball.style.left = startX + 'px';
    ball.style.top = startY + 'px';
    ball.style.setProperty('--pd-dx', (Math.round(x) - startX) + 'px');
    ball.style.setProperty('--pd-dy', (Math.round(y) - startY) + 'px');
    body.append(ball);
    requestAnimationFrame(() => ball.classList.add('is-throwing'));
    const flash = document.createElement('span');
    flash.className = 'pd-capture-flash';
    flash.style.left = Math.round(x) + 'px';
    flash.style.top = Math.round(y) + 'px';
    body.append(flash);
    window.setTimeout(() => { ball.remove(); flash.remove(); }, 950);
  }
  document.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (event.target && event.target.closest('input,textarea,select,option,[contenteditable="true"]')) return;
    throwBall(event.clientX, event.clientY);
  }, { passive: true });

  // Only animate genuinely new First seen / New item entries after the first dashboard render.
  const alertList = document.getElementById('alertList');
  if (alertList) {
    const seen = new Set();
    let initialSnapshotReady = false;
    let observerQueued = false;
    const keyFor = card => {
      const title = card.querySelector('.alert-title')?.textContent?.trim() || '';
      const retailer = card.querySelector('.alert-meta span')?.textContent?.trim() || '';
      return (retailer + '|' + title).toLowerCase();
    };
    const processAlertCards = () => {
      observerQueued = false;
      alertList.querySelectorAll('.alert-price span').forEach(span => {
        if (/^First observed by PokéDrop Watch/i.test(span.textContent.trim())) span.remove();
      });
      const cards = [...alertList.querySelectorAll('.alert-card')];
      if (!cards.length) return;
      if (!initialSnapshotReady) {
        cards.forEach(card => seen.add(keyFor(card)));
        initialSnapshotReady = true;
        return;
      }
      cards.forEach(card => {
        const key = keyFor(card);
        if (seen.has(key)) return;
        seen.add(key);
        const badge = card.querySelector('.type-badge');
        if (!badge) return;
        const capturedType = badge.classList.contains('first_seen') || badge.classList.contains('new_item')
          || /FIRST SEEN|NEW ITEM/i.test(badge.textContent || '');
        if (!capturedType) return;
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
    const queueProcess = () => {
      if (observerQueued) return;
      observerQueued = true;
      requestAnimationFrame(processAlertCards);
    };
    new MutationObserver(queueProcess).observe(alertList, { childList: true, subtree: true });
    queueProcess();
  }
})();
