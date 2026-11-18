# PokéDrop Watch — Admin navigation layout update

This patch makes the GitHub Pages admin shell use the same site navigation as the public homepage.

## GitHub installation

Upload this ZIP to the repository's `updates/` folder and commit it. The existing patch workflow installs the files under their repository paths.

## Apps Script update (required)

The embedded administrator page is served from Google Apps Script, so GitHub's ZIP installer cannot update the live Apps Script project.

1. Open the existing **PokéDrop Watch Backend** Apps Script project.
2. Open `Code.gs`.
3. Replace only the existing `doGet(e)` function with the complete function in `backend/apps-script/doGet_REPLACEMENT.txt` from this patch.
4. Leave the existing `Admin.html`, `Index.html`, all server functions, and Script Properties unchanged.
5. Save, then choose **Deploy → Manage deployments → Edit → New version → Deploy**. Keep the existing deployment URL and permissions.

The new handler removes the duplicate branding header and duplicate branded footer from the embedded Admin HTML response. The outer GitHub Pages page supplies the shared PokéDrop WATCH top bar and the Home / Alerts / Notify / Admin / GitHub bottom navigation.

## What stays the same

- The public address remains `https://n0nam3-bot.github.io/PokeDropWatch/admin.html`.
- Sign-in, password reset, subscriber management, and Firestore calls remain in Apps Script.
- The existing PKMN RBYGSC font remains loaded from the public site's font asset.
- The Admin item is highlighted in the shared bottom navigation.
