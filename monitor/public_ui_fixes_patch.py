"""Apply feed-filter corrections without changing Notify/Admin page layouts."""
from __future__ import annotations

import re
from pathlib import Path

import source_health_patch


def _remove_product_view_news_redirects(source: str) -> str:
    """Allow News filters to work while the All tracked products view is active."""
    patterns = (
        re.compile(
            r"\n\s*if \(state\.view === 'products' && state\.filter === 'news'\) \{"
            r"\s*state\.view = 'alerts';\s*"
            r"\$\('alertsViewButton'\)\.classList\.add\('active'\);\s*"
            r"\$\('productsViewButton'\)\.classList\.remove\('active'\);\s*\}",
            re.S,
        ),
        re.compile(
            r"\n\s*if \(state\.view === 'products' && state\.category === 'news'\) \{"
            r"\s*state\.view = 'alerts';\s*"
            r"\$\('alertsViewButton'\)\.classList\.add\('active'\);\s*"
            r"\$\('productsViewButton'\)\.classList\.remove\('active'\);\s*\}",
            re.S,
        ),
    )
    for pattern in patterns:
        source = pattern.sub("", source)
    # News is also a feed source, so give it an explicit retailer filter value.
    source = source.replace(
        "new Option('GameStop', 'gamestop')\n    );",
        "new Option('GameStop', 'gamestop'),\n      new Option('Pokémon News', 'pokemon-news')\n    );",
        1,
    )
    source = source.replace(
        "['all', 'amazon', 'walmart', 'best-buy', 'target', 'pokemon-center', 'gamestop'].includes(selected)",
        "['all', 'amazon', 'walmart', 'best-buy', 'target', 'pokemon-center', 'gamestop', 'pokemon-news'].includes(selected)",
        1,
    )
    return source


def apply_public_ui_patches(repo_root: Path) -> dict[str, bool]:
    """Patch only the home feed controls; Notify/Admin remain their original pages."""
    docs = Path(repo_root) / "docs"
    outcomes: dict[str, bool] = {}
    app = docs / "app.js"
    if app.is_file():
        original = app.read_text(encoding="utf-8")
        updated = _remove_product_view_news_redirects(original)
        if updated != original:
            app.write_text(updated, encoding="utf-8")
            outcomes["app.js"] = True
        else:
            outcomes["app.js"] = False
    # Intentionally do not patch docs/notify.html or docs/admin.html. Their
    # existing iframe shell, sizing, navigation and fallback links are preserved.
    return outcomes


# source_health_patch invokes this function on the first source scan.
source_health_patch.apply_public_ui_patches = apply_public_ui_patches
