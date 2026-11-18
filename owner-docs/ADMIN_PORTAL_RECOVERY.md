# PokéDrop Watch — embedded administrator portal

The public admin URL remains `https://n0nam3-bot.github.io/PokeDropWatch/admin.html`. The GitHub Pages page embeds the Apps Script admin page in an iframe. Administrator actions still execute inside Apps Script through `google.script.run`, but the browser's top-level address remains on the PokéDrop Watch website.

## 1. Keep the existing Admin.html

Do not delete or rename the existing `Admin.html` file in the Apps Script project. It contains the standalone administrator interface and direct `google.script.run` calls.

## 2. Update doGet in the existing Code.gs project

Open the existing **PokéDrop Watch Backend** Apps Script project. Replace only the `doGet()` function in `Code.gs` with the complete contents of `backend/apps-script/doGet_REPLACEMENT.txt` from this patch. Keep the rest of `Code.gs` unchanged.

The updated handler:

- continues serving `Index.html` at the ordinary `/exec` endpoint for email verification;
- serves `Admin.html` at `/exec?page=admin`;
- applies the existing PKMN RBYGSC font from the public GitHub Pages asset URL;
- sets `XFrameOptionsMode.ALLOWALL` on the Admin output so GitHub Pages can embed it.

## 3. Deploy a new version

Choose **Deploy → Manage deployments → Edit → New version → Deploy**. Keep the existing deployment ID, execute as the Apps Script owner, and retain access for Anyone.

## 4. Open the admin portal

Use `https://n0nam3-bot.github.io/PokeDropWatch/admin.html`. The page shows a PokéDrop Watch header with a **Main website** link and embeds the Apps Script admin UI below it. Signing in and signing out happen inside the embedded frame, so the browser address stays on the GitHub Pages URL. The Google Apps Script URL is only the iframe's internal source.

The admin theme now loads `PKMN-RBYGSC.ttf` from `docs/assets/fonts/PKMN-RBYGSC.ttf`, the same font used by the main site. No new font upload is required.

## 5. Data and security

The admin portal still uses the custom Apps Script password hash and reset-code functions. It does not use Firebase Authentication. Firestore remains private; do not enable public browser read/write rules. If the password is accepted but the subscriber list cannot load, check the service-account JSON, Cloud Datastore User IAM role, and Firestore API independently.
