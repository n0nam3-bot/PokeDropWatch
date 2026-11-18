# PokéDrop Watch — Pixel theme and interface copy updates

## GitHub Pages patch

Upload the ZIP to the repository `updates/` folder and commit it. The existing patch updater installs the files under `PokeDropWatch_Update/` into the repository root. The service-worker cache is bumped to `pokedrop-shell-v14` and now includes the new theme, page enhancement script, and three 8-bit ball sprites.

## Google Apps Script update (required for the embedded Notify form)

The public Notify page embeds the Apps Script `Subscribe` HTML page. In the existing Apps Script project:

1. Replace the HTML file named `Subscribe` with `backend/apps-script/Subscribe.html` from the installed repository.
2. Replace only `doGet(e)` in `Code.gs` with the function in `backend/apps-script/doGet_REPLACEMENT.txt` and add `pokedropEmbeddedOutput_()` below it.
3. Keep every other server-side function and Script Property unchanged.
4. Save, then deploy the existing web app as a **New version**. Keep the existing deployment URL and its execution/access settings.

The updated output helper removes the old Admin login hint, adds the Master Ball cursor inside Admin, and adds the Ultra Ball cursor inside Notify. The updated Subscribe page moves the verification panel directly below the signup button, removes the explanatory side panel and visible honeypot label, and updates the accepted-request copy.

## Visual behavior

- Home and Alerts use the 8-bit Poké Ball cursor and top-bar icon. The top-bar label changes from **PALLET TOWN** to **POKÉDEX** while the Alerts section is active.
- Notify uses the 8-bit Ultra Ball cursor and top-bar icon, with the label **POKÉMON CENTER**.
- Admin uses the 8-bit Master Ball cursor and top-bar icon, with the label **GYM LEADER**.
- First-seen/new-item alert cards receive a small Poké Ball sprite that rocks side-to-side to indicate a newly captured listing. The top-bar ball also animates during that capture cue.
- Price values do not wrap onto a second line. Supporting availability text can still wrap normally.

## Help content

Admin and Notify now have compact, collapsible “How it works” guides. `docs/SOURCE_HEALTH.html` is rewritten as a durable guide to source statuses, the scan pipeline, alert filters, product filters, verification, and subscriber approval. The previous point-in-time scan table has been removed so the page does not present old source counts as current.
