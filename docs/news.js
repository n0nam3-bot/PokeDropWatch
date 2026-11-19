(() => {
  'use strict';
  const list = document.getElementById('pokemonNewsList');
  if (!list) return;

  const feedSourceId = 'pokemon-news-google';
  const safeHttpUrl = (value) => {
    try {
      const url = new URL(String(value || ''), window.location.href);
      return ['https:', 'http:'].includes(url.protocol) ? url.href : '';
    } catch {
      return '';
    }
  };

  function formatDate(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
  }

  function makeCard(article) {
    const href = safeHttpUrl(article.url);
    if (!href || !article.title) return null;
    const card = document.createElement('a');
    card.className = 'pokemon-news-card';
    card.href = href;
    card.target = '_blank';
    card.rel = 'noopener noreferrer';

    const imageUrl = safeHttpUrl(article.image);
    if (imageUrl) {
      const image = document.createElement('img');
      image.className = 'pokemon-news-image';
      image.src = imageUrl;
      image.alt = '';
      image.loading = 'lazy';
      image.referrerPolicy = 'no-referrer';
      image.addEventListener('error', () => image.replaceWith(makePlaceholder()));
      card.append(image);
    } else {
      card.append(makePlaceholder());
    }

    const copy = document.createElement('div');
    copy.className = 'pokemon-news-copy';
    const meta = document.createElement('div');
    meta.className = 'pokemon-news-meta';
    const publisher = document.createElement('span');
    publisher.textContent = article.publisher || article.retailer || 'Pokémon News';
    meta.append(publisher);
    const published = formatDate(article.published);
    if (published) {
      const date = document.createElement('time');
      date.textContent = published;
      date.dateTime = article.published;
      meta.append(date);
    }
    const title = document.createElement('h3');
    title.className = 'pokemon-news-title';
    title.textContent = article.title;
    copy.append(meta, title);
    if (article.summary) {
      const summary = document.createElement('p');
      summary.className = 'pokemon-news-summary';
      summary.textContent = article.summary;
      copy.append(summary);
    }
    card.append(copy);
    return card;
  }

  function makePlaceholder() {
    const placeholder = document.createElement('span');
    placeholder.className = 'pokemon-news-placeholder';
    placeholder.setAttribute('aria-hidden', 'true');
    placeholder.textContent = '◉';
    return placeholder;
  }

  function render(articles) {
    const fragment = document.createDocumentFragment();
    (Array.isArray(articles) ? articles : []).slice(0, 12).forEach(article => {
      const card = makeCard(article || {});
      if (card) fragment.append(card);
    });
    list.replaceChildren();
    if (!fragment.childNodes.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No matching articles are available yet.';
      list.append(empty);
      return;
    }
    list.append(fragment);
  }

  async function refresh() {
    try {
      const response = await fetch(`./data/state.json?t=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`News data returned ${response.status}`);
      const data = await response.json();
      const source = data && data.items && data.items[feedSourceId];
      render(source && source.articles);
    } catch (error) {
      if (!list.dataset.loaded) {
        const empty = document.createElement('div');
        empty.className = 'empty-state';
        empty.textContent = 'News is temporarily unavailable. The article feed will retry automatically.';
        list.replaceChildren(empty);
      }
      console.warn('PokéDrop Watch news could not be refreshed:', error);
    } finally {
      list.dataset.loaded = 'true';
    }
  }

  refresh();
  window.setInterval(refresh, 5 * 60 * 1000);
})();
