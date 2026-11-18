(() => {
  'use strict';

  // The homepage doubles as the Alerts view; update its Pallet Town / Pokédex label.
  const locationLabel = document.getElementById('pageLocation');
  const alertsSection = document.getElementById('alerts');
  if (locationLabel && alertsSection) {
    let scheduled = false;
    const updateLocation = () => {
      scheduled = false;
      const threshold = alertsSection.getBoundingClientRect().top + window.scrollY - 135;
      locationLabel.textContent = (location.hash === '#alerts' || window.scrollY >= threshold)
        ? 'POKÉDEX'
        : 'PALLET TOWN';
    };
    const scheduleLocationUpdate = () => {
      if (scheduled) return;
      scheduled = true;
      window.requestAnimationFrame(updateLocation);
    };
    window.addEventListener('scroll', scheduleLocationUpdate, { passive: true });
    window.addEventListener('hashchange', scheduleLocationUpdate);
    document.querySelectorAll('.bottom-bar a[href="#alerts"]').forEach(link => {
      link.addEventListener('click', () => { locationLabel.textContent = 'POKÉDEX'; });
    });
    document.querySelectorAll('.bottom-bar a[href="#top"]').forEach(link => {
      link.addEventListener('click', () => { locationLabel.textContent = 'PALLET TOWN'; });
    });
    updateLocation();
  }

  // A new/first-seen listing gets a small 8-bit Poké Ball that rocks side to side.
  const alertList = document.getElementById('alertList');
  if (alertList) {
    const addCaptureSprites = () => {
      alertList.querySelectorAll('.alert-card').forEach(card => {
        const badge = card.querySelector('.type-badge');
        if (!badge) return;
        const isCapture = badge.classList.contains('first_seen')
          || badge.classList.contains('new_item')
          || /FIRST SEEN|NEW ITEM/i.test(badge.textContent || '');
        const media = card.querySelector('.alert-media');
        if (!isCapture || !media || media.querySelector('.capture-ball')) return;
        const sprite = document.createElement('img');
        sprite.className = 'capture-ball';
        sprite.src = './assets/icons/pokeball-8bit.svg';
        sprite.alt = '';
        sprite.setAttribute('aria-hidden', 'true');
        media.append(sprite);
        const headerBall = document.querySelector('.page-ball');
        if (headerBall) {
          headerBall.classList.remove('capture-wiggle');
          void headerBall.offsetWidth;
          headerBall.classList.add('capture-wiggle');
        }
      });
      // The status was useful internally, but the first-seen card no longer needs this long sentence.
      alertList.querySelectorAll('.alert-price span').forEach(span => {
        if (/^First observed by PokéDrop Watch/i.test(span.textContent.trim())) span.remove();
      });
    };
    new MutationObserver(addCaptureSprites).observe(alertList, { childList: true, subtree: true });
    addCaptureSprites();
  }
})();
