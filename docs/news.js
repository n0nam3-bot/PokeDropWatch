(() => {
  'use strict';

  // News stays inside the existing Latest alerts / All tracked products feed.
  // Latest activity is intentionally limited to the last 30 days; the All
  // tracked products view exposes the full saved archive.
  const $ = (id) => document.getElementById(id);
  const list = $('alertList');
  if (!list) return;

  const feedSourceId = 'pokemon-news-google';
  const DAY = 86400000;
  const LATEST_WINDOW_DAYS = 30;
  let latestData = null;
  let renderTimer = 0;

  const normalize = (value) => String(value || '').toLowerCase()
    .replace(/é/g, 'e').replace(/[^a-z0-9]+/g, ' ').trim();

  function safeHttpUrl(value) {
    try {
      const url = new URL(String(value || ''), window.location.href);
      return ['https:', 'http:'].includes(url.protocol) ? url.href : '';
    } catch {
      return '';
    }
  }

  function dateValue(value) {
    if (!value) return 0;
    const parsed = Date.parse(String(value));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function articleTime(article) {
    return dateValue(article.published) || dateValue(article.detected_at) || dateValue(article.first_seen);
  }

  function formatDate(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(undefined, {
      month: 'short', day: 'numeric', year: 'numeric',
    }).format(date);
  }

  function activeActivityFilter() {
    return document.querySelector('#alertTypeFilters .filter-chip.active')?.dataset.filter || 'all';
  }

  function isArchiveView() {
    return Boolean($('productsViewButton')?.classList.contains('active'));
  }

  function shouldShowNews() {
    const type = activeActivityFilter();
    const category = $('categoryFilter')?.value || 'all';
    // Keep the original Latest Activity rule: the News chip always opens news;
    // Item type = News opens it when All activity is selected. The same two
    // controls also work in All tracked products without leaving that view.
    return type === 'news' || (type === 'all' && category === 'news');
  }

  function currentArticles(data) {
    const source = data?.items?.[feedSourceId];
    const articles = Array.isArray(source?.articles) ? source.articles : [];
    const byUrl = new Map();

    for (const item of articles) {
      const url = safeHttpUrl(item?.url);
      if (!url || !item?.title) continue;
      const publisher = item.publisher || item.retailer || 'Pokémon News';
      byUrl.set(url, {
        ...item,
        type: 'news',
        category: 'news',
        retailer_key: 'pokemon-news',
        url,
        publisher,
        retailer: publisher,
      });
    }

    // Older states may contain news events that predate the persistent archive.
    for (const item of (Array.isArray(data?.events) ? data.events : [])) {
      if (item?.type !== 'news') continue;
      const url = safeHttpUrl(item.url);
      if (!url || !item.title || byUrl.has(url)) continue;
      const publisher = item.publisher || item.retailer || item.source_name || 'Pokémon News';
      byUrl.set(url, {
        ...item,
        type: 'news',
        category: 'news',
        retailer_key: 'pokemon-news',
        url,
        publisher,
        retailer: publisher,
      });
    }

    return [...byUrl.values()].sort((a, b) => articleTime(b) - articleTime(a));
  }

  function matchesFilters(article) {
    const type = activeActivityFilter();
    const category = $('categoryFilter')?.value || 'all';
    const retailer = $('retailerFilter')?.value || 'all';
    const query = normalize($('alertSearch')?.value || '');
    const exact = Boolean($('exactMatch')?.checked);
    const title = normalize(article.title);

    if (type !== 'all' && type !== 'news') return false;
    if (category !== 'all' && category !== 'news') return false;
    if (retailer !== 'all' && retailer !== 'pokemon-news') return false;
    if (query && (exact ? title !== query : !title.includes(query))) return false;
    return true;
  }

  function makePlaceholder() {
    const fallback = document.createElement('span');
    fallback.className = 'alert-icon-fallback';
    fallback.setAttribute('aria-hidden', 'true');
    fallback.textContent = '✧';
    return fallback;
  }

  function makeArticleCard(article) {
    const card = document.createElement('article');
    card.className = 'alert-card';

    const media = document.createElement('div');
    media.className = 'alert-media';
    const imageUrl = safeHttpUrl(article.image);
    if (imageUrl) {
      const image = document.createElement('img');
      image.className = 'alert-product-image';
      image.src = imageUrl;
      image.alt = '';
      image.loading = 'lazy';
      image.decoding = 'async';
      image.referrerPolicy = 'no-referrer';
      image.addEventListener('error', () => {
        media.replaceChildren(makePlaceholder());
        media.classList.add('image-missing');
      }, { once: true });
      media.append(image);
    } else {
      media.classList.add('image-missing');
      media.append(makePlaceholder());
    }

    const content = document.createElement('div');
    content.className = 'alert-content';
    const title = document.createElement('div');
    title.className = 'alert-title';
    title.textContent = article.title;
    content.append(title);

    const meta = document.createElement('div');
    meta.className = 'alert-meta';
    const publisher = document.createElement('span');
    publisher.textContent = article.publisher || 'Pokémon News';
    meta.append(publisher);
    const publishedText = formatDate(article.published || article.detected_at || article.first_seen);
    if (publishedText) {
      meta.append(document.createElement('span'));
      meta.lastChild.textContent = '·';
      const published = document.createElement('time');
      published.textContent = publishedText;
      if (article.published) published.dateTime = article.published;
      meta.append(published);
    }
    content.append(meta);

    const actions = document.createElement('div');
    actions.className = 'alert-actions';
    const badge = document.createElement('span');
    badge.className = 'type-badge news';
    badge.textContent = 'POKÉMON NEWS';
    actions.append(badge);
    const link = document.createElement('a');
    link.className = 'view-link';
    link.href = article.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'READ ARTICLE ↗';
    actions.append(link);
    content.append(actions);

    const detail = document.createElement('div');
    detail.className = 'alert-price';
    const label = document.createElement('strong');
    label.textContent = 'NEWS';
    const summary = document.createElement('span');
    summary.textContent = article.summary || publishedText || 'Open the article for details.';
    detail.append(label, summary);

    card.append(media, content, detail);
    return card;
  }

  function renderNews() {
    if (!shouldShowNews() || !latestData) return;
    const archiveView = isArchiveView();
    const cutoff = Date.now() - LATEST_WINDOW_DAYS * DAY;
    let articles = currentArticles(latestData);
    if (!archiveView) {
      articles = articles.filter(article => articleTime(article) >= cutoff);
    }
    articles = articles.filter(matchesFilters);

    list.replaceChildren();
    $('feedHeading').textContent = archiveView ? 'Pokémon News Archive' : 'Pokémon News · Last 30 Days';
    const fragment = document.createDocumentFragment();
    articles.forEach(article => fragment.append(makeArticleCard(article)));
    if (!fragment.childNodes.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-state large-empty';
      const heading = document.createElement('strong');
      heading.textContent = archiveView ? 'No archived Pokémon news articles' : 'No Pokémon news in the last 30 days';
      const note = document.createElement('span');
      note.textContent = archiveView
        ? 'Older articles will remain here as the monitor collects them. Try All retailers or clear the title search.'
        : 'The Latest activity news view only shows articles published or first detected within the last 30 days. Choose All tracked products and Item type = News to browse the full archive.';
      empty.append(heading, note);
      list.append(empty);
    } else {
      list.append(fragment);
    }
  }

  function queueRender() {
    window.clearTimeout(renderTimer);
    renderTimer = window.setTimeout(renderNews, 0);
  }

  function isAccessBlocked(source) {
    const diagnostic = Array.isArray(source?.parser_diagnostics)
      ? source.parser_diagnostics.join(' ')
      : '';
    const message = `${source?.message || ''} ${diagnostic}`.toLowerCase();
    return Boolean(source?.access_blocked) || /access-challenge|pardon our interruption|robot or human|captcha|access denied|verify you are human|request blocked/.test(message);
  }

  function updateSourceCards() {
    const sources = latestData?.source_status;
    const grid = $('sourceGrid');
    if (!Array.isArray(sources) || !grid) return;

    sources.forEach((source, index) => {
      const card = grid.children[index];
      if (!card) return;
      const badge = card.querySelector('.source-state');
      const detail = card.querySelector('.source-bottom span');
      if (!badge || !detail) return;

      if (isAccessBlocked(source)) {
        badge.textContent = 'BLOCKED';
        badge.title = 'The retailer returned an access-protection page. The monitor cannot confirm current inventory.';
        detail.textContent = `Access protection · ${Number(source.last_known_items || source.items_found || 0)} last-known listing(s) · current stock not confirmed`;
        detail.title = source.message || 'Access protection page detected.';
      } else if (source.status === 'error' && Number(source.last_known_items || source.items_found || 0) > 0) {
        detail.textContent = `Last known only · ${Number(source.last_known_items || source.items_found)} saved listing(s) · latest request failed`;
        detail.title = source.message || detail.textContent;
      }
    });
  }

  function updateRunMetadata() {
    const lastChecked = $('lastChecked');
    if (!lastChecked || !latestData?.last_checked) return;
    const checked = new Date(latestData.last_checked);
    if (Number.isNaN(checked.getTime())) return;
    const formatted = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(checked);
    const triggerLabels = {
      schedule: 'scheduled check',
      push: 'ZIP upload',
      workflow_dispatch: 'manual run',
      'manual/local': 'manual/local run',
    };
    const trigger = triggerLabels[latestData.last_trigger] || '';
    const text = `Last checked ${formatted}${trigger ? ` · ${trigger}` : ''}`;
    if (lastChecked.textContent !== text) lastChecked.textContent = text;
  }

  async function refresh() {
    try {
      const response = await fetch(`./data/state.json?t=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`Monitor data returned ${response.status}`);
      latestData = await response.json();
      renderNews();
      updateSourceCards();
      updateRunMetadata();
    } catch (error) {
      console.warn('PokéDrop Watch news/filter extension could not refresh:', error);
    }
  }

  document.addEventListener('click', event => {
    if (event.target.closest('.filter-chip, #alertsViewButton, #productsViewButton, #refreshButton')) {
      window.setTimeout(() => {
        if (event.target.closest('#refreshButton')) refresh();
        else queueRender();
      }, 0);
    }
  });
  document.addEventListener('change', event => {
    if (['categoryFilter', 'retailerFilter', 'exactMatch'].includes(event.target?.id)) queueRender();
  });
  $('alertSearch')?.addEventListener('input', queueRender);

  const lastChecked = $('lastChecked');
  if (lastChecked && 'MutationObserver' in window) {
    new MutationObserver(updateRunMetadata).observe(lastChecked, { childList: true, characterData: true, subtree: true });
  }

  const sourceGrid = $('sourceGrid');
  if (sourceGrid && 'MutationObserver' in window) {
    new MutationObserver(updateSourceCards).observe(sourceGrid, { childList: true });
  }

  refresh();
  window.setInterval(refresh, 5 * 60 * 1000);
})();
