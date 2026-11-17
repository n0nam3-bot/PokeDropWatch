# PokéDrop Watch — Configuration and Change Guide

**Purpose:** This is the project's reference manual for configuring, customizing, testing, and changing PokéDrop Watch. Read it before making a change. It is intended to prevent assumptions, undocumented settings, accidental regressions, and inconsistent updates.

**Current documented release:** 1.1.0  
**Last updated:** 2026-11-16

---

## 1. Rules that every change must follow

1. **Inspect before editing.** Read the current repository files, this guide, the README, the roadmap, the changelog, and the relevant tests before changing anything. The checked-out repository is the source of truth; do not rely on an old ZIP, an old chat message, or memory when the live files are available.
2. **Do not guess.** Do not invent configuration keys, file paths, retailer capabilities, completed features, or test results. Confirm each detail in the code or test it. When a required detail is not known, state the uncertainty and choose the least disruptive safe behavior rather than silently assuming.
3. **Keep changes targeted.** Change only what the request requires. Do not replace working code, redesign the interface, rename files, remove features, or reorganize folders unless the request requires it.
4. **Preserve the product direction.** Keep the project free to run with GitHub Pages, GitHub Actions, and the approved Firebase/Gmail free-tier subscriber architecture. Keep the interface minimal, Pokémon-themed, responsive on phones and desktop, and free of unnecessary decoration. Do not add AI services, paid APIs, or new hosting dependencies unless explicitly requested.
5. **No fake completion.** Do not add a roadmap checkmark until the feature is implemented and verified. Do not claim a retailer works simply because its URL is configured. Report blocked sources and limitations honestly.
6. **Test after every code or configuration change.** Run the relevant tests and the full automated test suite. Add or update tests for changed behavior. Report failures; never hide, delete, or weaken a test just to get a passing result.
7. **Keep documentation synchronized.** Update the README when setup or required configuration changes. Update the roadmap when implementation status changes. Add every released change to the top of the changelog. Update this guide whenever the supported configuration, workflow, folder layout, test process, or patch process changes.
8. **Deliver a small patch ZIP.** Include only changed or newly added files, with paths relative to the repository root. Do not make the user re-upload the whole application for an ordinary update.
9. **Verify the deliverable.** List the ZIP contents, test that the ZIP opens, apply it to a clean copy of the current project using the project's patch installer, and confirm the installed file paths. Do not give a download link until the file exists and has been checked.
10. **Finish with a precise report.** State what changed, list every file changed, what tests were run and their real results, any manual GitHub configuration still required, and the exact ZIP upload location.

## 2. Current project layout

| Path | Purpose | Change guidance |
|---|---|---|
| `README.md` | User-facing overview and required setup | Keep concise; document only real features and current setup. Link to this guide for detailed procedures. |
| `.github/workflows/pokedrop-watch.yml` | Scheduled monitor, tests, ZIP installation, commits | This is a permanent GitHub Actions workflow. The ZIP patch installer intentionally blocks changes under `.github/workflows/`; edit this file directly in GitHub when necessary. |
| `config/sources.json` | Monitor settings and retailer/news source list | Normal source and supported setting changes belong here. Preserve valid JSON. |
| `monitor/run.py` | Loads config, runs scans, persists state, sends digest | Keep the command-line entry point and default state path compatible unless a migration is deliberately planned. |
| `monitor/engine.py` | Fetching, parsing, product/news extraction, change detection, email formatting/sending | Add or change parsing logic here only after confirming the actual source format and adding tests. |
| `monitor/requirements.txt` | Python runtime dependencies | Avoid unnecessary dependencies. Document why a dependency is needed and keep version bounds appropriate. |
| `docs/index.html` | Public dashboard and visitor subscription form | Preserve accessibility, responsive layout, and current feature behavior. |
| `docs/styles.css` | Dashboard, subscription, and admin appearance | Keep the visual style minimal and Pokémon-themed. Check phone and desktop layouts after changes. |
| `docs/app.js` | Dashboard state loading, rendering, search, and filters | The dashboard reads `./data/state.json`; keep its data contract synchronized with `monitor/run.py`. |
| `docs/subscriptions.js` | Public application, preference, email-link, and unsubscribe flows | Never grant approval from browser input. Keep owner operations restricted by Firestore rules. |
| `docs/admin.html`, `docs/admin.js` | Static administrator interface and subscriber controls | The page shell is public; subscriber data/actions are protected by Firestore rules. Test with an admin and a non-admin account. |
| `docs/firebase-config.js`, `docs/firebase-client.js` | Public Firebase web-app config and browser SDK setup | Web config is public. Never place service-account credentials here. |
| `firebase/firestore.rules` | Subscriber database security rules | Set the administrator email only in the deployed Firebase Console rules; keep the placeholder in the public repository copy. Test user, admin, and unauthenticated access. |
| `monitor/subscribers.py` | Private subscriber lookup, preference matching, queued email delivery, and retries | Subscriber email addresses must never be written to public dashboard state or Actions logs. |
| `docs/data/state.json` | Generated scan state, source health, and alert history | Treat as runtime data generated by the monitor. Do not hand-edit it as a way to configure sources. Avoid deleting it because it contains the baseline used for change detection. |
| `docs/manifest.webmanifest`, `docs/sw.js` | PWA metadata and network-first service worker | The worker fetches current same-origin files first and uses cache only offline; bump the cache key when changing the app shell and verify refresh behavior. |
| `docs/ROADMAP.md` | Staged feature plan and implementation checkboxes | Check an item only after implementation and verification. Keep future work unchecked. |
| `docs/CHANGELOG.md` | Released changes, newest first | Add a dated version entry at the top for each delivered release. |
| `docs/CONFIGURATION_AND_CHANGE_GUIDE.md` | This operating and change reference | Keep accurate as the project evolves. |
| `scripts/apply_patch.py` | Safe installation of ZIP patches | It blocks unsafe paths, `.git/`, `updates/`, symlinks, and `.github/workflows/`. Test any modification to this script carefully. |
| `tests/` | Automated regression tests | Extend tests with every meaningful behavior change. Do not remove coverage to make a run pass. |

## 3. GitHub setup and required configuration

### 3.1 GitHub Actions permissions

In the repository, open **Settings → Actions → General → Workflow permissions** and select **Read and write permissions**. The workflow needs repository write access to commit scan state, install patches, and save updates. GitHub Actions must also be enabled for the repository.

The workflow file must exist at:

`/.github/workflows/pokedrop-watch.yml`

It supports scheduled execution, manual execution through `workflow_dispatch`, and ZIP-triggered execution. The configured schedule is currently:

```yaml
schedule:
  - cron: '*/15 * * * *'
```

This means a scheduled attempt every 15 minutes. GitHub may delay scheduled jobs. Change the cron expression in the workflow to change the actual interval. **The `check_interval_minutes` value in `config/sources.json` is descriptive only; it does not schedule GitHub Actions.**

### 3.2 GitHub Pages

Open **Settings → Pages** and publish from:

- Branch: `main`
- Folder: `/docs`

The dashboard is the static site in `docs/`. The monitor writes its current status and alert data to `docs/data/state.json`. Do not change the publish folder without also changing the workflow and the dashboard paths.

### 3.3 Firebase subscription system and email notifications

The public subscription feature uses Firebase Authentication email-link sign-in and Cloud Firestore. No Google Sheet, Apps Script deployment, Firebase Cloud Function, or paid application server is part of this implementation.

Follow `docs/FIREBASE_SETUP.html` (mobile-friendly, with clickable direct Console links) or `docs/FIREBASE_SETUP.md` (full text checklist) for the exact click-by-click setup. The guide includes direct Firebase Console URLs, exact GitHub Settings URLs, field-by-field Web App config mapping, required secret and variable names, and troubleshooting. The important configuration points are:

- `docs/firebase-config.js` contains only public Firebase web-app configuration. It must not contain the administrator email, service-account JSON, SMTP credentials, or other private keys.
- `firebase/firestore.rules` is the security boundary. Replace the administrator email placeholder in the Firebase Console rules editor only, then publish. Keep the placeholder in the public repository copy; do not commit the real admin email. Never leave Firestore in test mode.
- `FIREBASE_SERVICE_ACCOUNT_JSON` is a GitHub Actions secret containing the complete Firebase service-account JSON. It is used only by the monitor on GitHub's runner. Never commit the JSON file or paste it into a public project file.
- `SMTP_USERNAME` and `SMTP_APP_PASSWORD` are GitHub Actions secrets used to send individual alert emails. `ALERT_EMAIL` is optional and receives an extra owner-only copy; it is not required for subscriber fan-out.
- `PUBLIC_SITE_URL` is a GitHub Actions repository variable containing the complete Pages URL, including the repository path. It supplies the preference/unsubscribe link in emails.
- `.github/workflows/pokedrop-watch.yml` must pass `FIREBASE_SERVICE_ACCOUNT_JSON` and `PUBLIC_SITE_URL` into the monitor step. The supplied release workflow includes these values. Workflow files are intentionally excluded from ordinary patch ZIPs and must be updated directly in GitHub when the workflow itself changes.

Subscriber statuses are `pending`, `active`, `rejected`, `suspended`, `unsubscribed`, and `removed`. A visitor can create a `pending` record only after Firebase email-link sign-in verifies the visitor's mailbox. A verified visitor can read only their own record, update their categories/retailers, and mark their own record `unsubscribed`. Only the configured verified administrator can list records or change approval/administrative status.

The administrator email is kept out of public website JavaScript and the public repository. It is configured only in the deployed Firestore rules. The admin page may accept an email address for link delivery, but Firestore rules alone decide whether the verified account has administrator access. Protect that mailbox with a strong login and two-step verification.

The browser applies a one-minute resend cooldown. Firebase Authentication also applies service-side email sending and abuse limits. The cooldown is a usability control, not a complete CAPTCHA or bot-defense system. If the service grows beyond a small community, add stronger abuse controls and a dedicated transactional email provider before increasing volume.

`monitor/subscribers.py` queries only `active` records and matches each alert against the saved category and retailer preferences. Each subscriber receives a separate email; no subscriber addresses are exposed to other recipients. Pending delivery batches and retry status are stored in private Firestore subcollections. No subscriber email, UID, or delivery record may be added to `docs/data/state.json` or printed into public Actions logs.

Firebase Spark, GitHub Actions, and Gmail all have usage limits. The intended deployment is a no-cost, low-volume setup, not a guarantee of unlimited delivery. Check current provider quotas in their respective consoles before inviting a large subscriber group.

### 3.4 GitHub Pages URL versus repository README

The repository Code tab normally displays `README.md`; that is not the public website. Set **Settings → Pages → Deploy from a branch → `main` → `/docs`**. The website entry point is `docs/index.html`, the public site root is the URL GitHub Pages displays, and the administrator page is `/admin.html` under that same repository path. If the Pages URL displays the README, check that `docs/index.html` exists on `main` and that the publish folder is `/docs`, not `/root`.

## 4. Configuring sources and scan behavior

The monitor reads `config/sources.json`. It contains a top-level `settings` object and a `sources` array.

### 4.1 Supported settings

| Setting | Current default | What it controls |
|---|---:|---|
| `check_interval_minutes` | `15` | Informational only. The actual schedule is the cron expression in the GitHub Actions workflow. |
| `request_timeout_seconds` | `25` | HTTP request timeout for a source fetch. |
| `max_items_per_catalog` | `80` | Maximum relevant Pokémon products retained from one catalog page. Product-title relevance filtering is enforced by the parser. |
| `history_limit` | `100` | Maximum recent alert events retained in the state file. |
| `email_digest_subject_prefix` | `PokéDrop Watch` | Prefix used in email subject lines. |
| `user_agent` | `PokeDropWatch/1.0 (+https://github.com; public product availability monitor)` | User-Agent string sent with source requests. |

Only use settings that are implemented in the current code. Adding a new JSON key alone does not make the monitor support it; a feature that uses a new setting must include code, validation/default behavior, tests, and documentation.

### 4.2 Source object fields

Every source in `sources` should have:

| Field | Required | Rule |
|---|---|---|
| `id` | Yes | Unique, stable identifier. Use lowercase letters, numbers, and hyphens. Do not casually rename an existing ID: the ID keys its stored baseline and history. |
| `name` | Yes | Human-readable source name shown on the dashboard. |
| `retailer` | Yes for product sources | Retailer or publisher label used in dashboard and alert details. |
| `category` | Recommended | Subscriber preference category: `tcg`, `plush`, `collectibles`, `games`, `accessories`, or `news`. Defaults to `collectibles` for product sources and `news` for RSS. |
| `retailer_key` | Recommended | Subscriber filter key such as `pokemon-center`, `target`, `walmart`, `best-buy`, `gamestop`, `amazon`, or `pokebeach`. Defaults to a normalized retailer label. |
| `type` | Yes | One of the supported types listed below: `catalog`, `product`, or `rss`. |
| `url` | Yes | Public HTTP or HTTPS catalog, product, or feed URL. |
| `enabled` | Recommended | `true` to scan it; `false` to skip it without deleting its configuration. |
| `notes` | Optional | Plain-language notes shown with source health; use this to document known restrictions. |

Supported source types:

- **`catalog`** — a retailer category or search-results page. The parser looks for Pokémon-relevant product structured data and qualifying product cards in returned HTML, extracts image/price/availability data where exposed, and rejects generic rating/offer links. It does not run a full browser or execute the retailer's JavaScript application. A page that responds but yields zero relevant items is shown as `NO MATCH`, not `ONLINE`.
- **`product`** — one product-detail page. The scanner attempts to extract the product title, price, image, and availability exposed by the page's structured data or HTML.
- **`rss`** — an RSS or Atom feed. Feed entries are treated as news/announcement events, not confirmation that a product is in stock.

### 4.3 Safe procedure for adding or changing a source

1. Find the retailer's public category/search page, product page, or RSS/Atom feed. Prefer a stable public page over a temporary campaign URL.
2. Confirm the exact URL opens without signing in. Do not bypass a retailer's access controls, CAPTCHA, queue, or other restrictions.
3. Add or edit one source object in `config/sources.json`. Give it a unique stable `id`; set the correct `type`; set `enabled` to `true`; and add a note about known limitations.
4. Validate the JSON with `python -m json.tool config/sources.json`.
5. Run the tests. Then run a controlled test of the source parser with a saved sample page/feed or a dedicated integration test. Avoid treating one successful HTTP response as proof that the retailer will remain compatible.
6. After deployment, inspect the dashboard's source status and the GitHub Actions log. A source that returns no usable products, is blocked, or errors must not be described as working coverage.

### 4.4 Baseline and alert behavior

The first successful scan creates a baseline from Pokémon-relevant products currently visible on each source. Product names must identify Pokémon or a recognized Pokémon character; generic ratings, review links, "See options" controls, and unrelated products are excluded. Product category is inferred from the title as `tcg`, `plush`, `games`, `accessories`, or `collectibles`. The public dashboard separates the change-event feed from an All tracked products view and offers category, retailer, alert-type, and exact-title filters. Current product cards are read from each source baseline in `docs/data/state.json`; they must not be presented as new drops unless a change event was detected. A fetched page with zero recognized entries is reported as `NO MATCH`, while blocked/failed requests are reported as `ISSUE`. It does not generate a new-item alert for every item already listed. Later scans compare the current result with saved state and can report newly discovered listings, a transition from out of stock to in stock/preorder, and listed price changes when the page exposes the relevant values. RSS/Atom entries are tracked as news announcements.

The state file is `docs/data/state.json`. Keep it between updates so the monitor can compare scans. Removing or resetting it can cause a new baseline and may affect which changes are reported. Do not promise a price, stock count, release date, or availability location that the source page does not provide.

## 5. Dashboard customization rules

- `docs/index.html` controls public page structure; `docs/styles.css` controls visual presentation; `docs/app.js` controls monitor data rendering; `docs/subscriptions.js` controls visitor subscription actions; `docs/admin.html` and `docs/admin.js` provide the private admin interface.
- The dashboard loads `docs/data/state.json` through a relative `./data/state.json` URL. Preserve this relative path so the site works on a GitHub Pages project subpath.
- Keep the dashboard responsive on small mobile screens and larger desktop displays. Test narrow phone widths, tablet widths, and desktop widths after layout changes.
- Preserve the minimal Pokémon-inspired appearance. Avoid unnecessary animation, oversized controls, clutter, popups, or unrelated branding.
- Keep the dashboard truthful: show request failures as issues and pages with zero recognized Pokémon products as `NO MATCH`; do not convert missing/unknown prices or stock states into positive claims.
- Keep product photos optional: show a neutral fallback when the retailer blocks hotlinking or does not expose an image. Never invent or substitute a different product image.
- Keep category inference and the category filters synchronized across `monitor/engine.py`, `docs/app.js`, subscription defaults, and `firebase/firestore.rules`.
- If changing the JSON structure written by `monitor/run.py`, update `docs/app.js` and tests in the same change. Maintain compatibility with previously saved `docs/data/state.json`, or include a safe migration plan.
- If changing offline/PWA assets, inspect `docs/manifest.webmanifest` and `docs/sw.js`; update the service-worker cache key/version when changing the app shell; the worker is network-first so online configuration and code updates are not masked by stale cached files.

## 6. Email customization rules

Email formatting and SMTP transport live in `monitor/engine.py`; private subscriber filtering and retry queueing live in `monitor/subscribers.py`. The alert message can include event title, retailer/source, listed price, availability, previous price when available, detection time, and a direct source/product link.

When changing email content or behavior:

1. Keep the email readable on both mobile and desktop email clients.
2. Keep the product link direct and clearly labeled. Do not create invented checkout links.
3. Keep unavailable data explicitly unknown or omit it; do not infer a price or stock status.
4. Do not expose SMTP credentials or other secrets in the email body, logs, dashboard, or state file.
5. Add tests for HTML escaping, missing optional data, subscriber preference matching, individual-recipient delivery, and retry behavior.
6. Keep a secure preference/unsubscribe link in subscriber emails. The link must require an email sign-in and a separate confirmation; never add a raw public unsubscribe endpoint that changes a record based only on an email address.
7. Do not log recipient email addresses, SMTP exception text, subscriber UIDs, or service-account content into public Actions logs or `docs/data/state.json`.
8. Update this guide and the README if new secrets or configuration fields are introduced.

## 7. Required testing and validation

Run tests from the repository root. The standard full test command is:

```bash
python -m unittest discover -s tests -v
```

Install runtime dependencies first when needed:

```bash
python -m pip install -r monitor/requirements.txt
```

Validate the source configuration:

```bash
python -m json.tool config/sources.json > /dev/null
```

For every change, do the following as relevant:

- Run the full existing unit test suite, not only the test most closely related to the edit.
- Add a regression test for every fixed bug or newly implemented behavior.
- For source parsing changes, test saved HTML/XML fixtures for the exact page/feed structure being supported.
- For dashboard changes, check phone, tablet, and desktop layouts and browser-console errors.
- For email changes, test message generation without sending real email; use configured test credentials only when an actual delivery test is explicitly intended.
- For workflow or patch-installer changes, test the workflow logic and apply a sample ZIP to a clean temporary copy of the repository.
- Record the exact command and pass/fail result. If a test cannot be run in the available environment, say so explicitly and provide the remaining manual verification step.

Do not run `python monitor/run.py` casually as a unit test: it performs live network requests, updates `docs/data/state.json`, and may send email if secrets are present. Run it intentionally when performing an end-to-end scan.

## 8. How to write a new change request

Use the following template when requesting a new feature, fix, configuration change, or visual adjustment. Fill in what is known; attaching a screenshot or exact GitHub Actions error is better than paraphrasing it.

```text
POKÉDROP WATCH — CHANGE REQUEST

Project baseline:
- Repository/branch:
- Current version (from docs/CHANGELOG.md):
- Device/browser used for the test (phone/tablet/desktop):

Request type:
- [ ] Bug fix
- [ ] New feature
- [ ] Retailer/source addition or change
- [ ] Dashboard/UI change
- [ ] Email/notification change
- [ ] Configuration or deployment change
- [ ] Documentation change

Current behavior:
- What I did:
- What happened:
- Exact error text or Actions log (if any):
- Screenshot or example item/source URL (if relevant):

Exact desired behavior:
- What should happen instead:
- What information must be shown or sent:
- What should happen on mobile:
- What should happen on desktop:

Must preserve / must not change:
- Features, layout, settings, behavior, or files that must remain unchanged:
- Things that must not be added:

Acceptance checks:
- [ ] The change works in the stated scenario.
- [ ] Existing behavior listed above still works.
- [ ] Relevant automated tests pass.
- [ ] README/roadmap/changelog/this guide are updated where applicable.
- [ ] Only changed files are included in the patch ZIP.
```

If an item is not relevant, write `N/A` instead of leaving room for interpretation. For visual work, describe the exact element, location, sizing, alignment, colors, and behavior; include a screenshot where possible. For source work, provide the precise URL and the product/feed example that should be detected.

## 9. Standard procedure for implementing each change

1. **Read the request and current project.** Check the current repository tree, this guide, relevant implementation, current configuration, roadmap, changelog, and tests.
2. **Translate the request into acceptance checks.** Identify the exact observed problem, desired behavior, must-preserve constraints, affected devices, and affected files. Do not expand the scope without a reason.
3. **Inspect before deciding.** Follow the current data flow and find the actual cause. Do not guess based on filenames or screenshots alone when logs or code can confirm it.
4. **Implement the smallest complete fix.** Avoid placeholders, mock functionality, fake source data, unnecessary dependencies, and unrelated refactoring.
5. **Test the actual behavior.** Add regression coverage, run the full test suite, validate JSON, and perform appropriate mobile/desktop, workflow, or source fixture checks.
6. **Update documentation.** Update the README for user-facing setup/configuration changes, the roadmap for verified feature status, the changelog for the release, and this guide for changed procedures or supported settings.
7. **Create a patch release.** Increment the version according to the versioning rules below. Put the newest changelog entry first and use the actual release date (`YYYY-MM-DD`).
8. **Build a minimal patch ZIP.** Include only files changed for the release. ZIP paths must be repository-relative, for example `docs/app.js` and `docs/CHANGELOG.md`. Do not include a top-level `updates/` folder inside the ZIP. An optional single wrapper folder is supported by the patch script, but repository-relative paths are preferred.
9. **Verify the patch.** Open/list the ZIP, apply it to a clean copy using `python scripts/apply_patch.py <patch.zip>`, verify installed paths/content, and rerun tests as appropriate.
10. **Deliver the result.** Provide one clear patch ZIP link, the exact upload location `updates/` in the GitHub repository, the files changed, real test results, and any manual setup the user must perform.

## 10. ZIP patch and GitHub update rules

For ordinary application or documentation updates:

- Create a ZIP containing only changed/new project files.
- Store paths relative to the repository root. Example:

```text
PokeDropWatch_Update_vX.Y.Z.zip
├── docs/
│   ├── app.js
│   └── CHANGELOG.md
└── README.md
```

- Upload the ZIP to the repository's `updates/` folder (create that folder if needed) or to the repository root. The existing workflow searches the repository for ZIP files and applies the patch.
- GitHub Actions should run from the ZIP upload. Check the Actions run and confirm the patch step reports the expected installed paths before assuming it succeeded.
- The patch installer blocks archive paths under `.git/` and `updates/`, rejects symlinks and unsafe paths, and refuses workflow edits under `.github/workflows/`. This protects the repository and means permanent workflow changes must be edited directly in GitHub.
- Do not put credentials, local cache folders, Python `__pycache__` folders, temporary test output, or another ZIP inside an ordinary patch ZIP.
- Do not include deletions as empty files. A deletion requires an explicitly designed and tested deletion mechanism; do not assume the current patch installer supports it.
- Do not tell the user an update is installed until the Actions run completed successfully and the expected paths are visible in the repository.

## 11. Version, roadmap, and changelog conventions

### Version numbers

Use `MAJOR.MINOR.PATCH` in `docs/CHANGELOG.md`:

- **PATCH** — documentation-only updates, small bug fixes, or safe corrections that do not add a major capability or break existing configuration.
- **MINOR** — new backward-compatible features or newly supported configuration/source behavior.
- **MAJOR** — intentionally breaking configuration, saved-state, workflow, or user-facing changes that require migration or new setup.

Do not claim semantic-version compatibility as an external guarantee; this is the project's internal release convention.

### Roadmap

- Use `- [x]` only for a capability present in the current code and verified by tests or a documented end-to-end check.
- Use `- [ ]` for planned, partial, unverified, or blocked work.
- A configured retailer URL is not proof of a working retailer adapter.
- When a feature is partly complete, split the task into a completed, precise statement and a remaining unchecked statement rather than marking the broad task complete.
- Keep stage status labels consistent with the checkboxes.

### Changelog

Add new entries immediately below the title and introductory sentence, before older versions. Use this format:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- Describe the user-visible capability that was added.

### Changed
- Describe changed behavior or configuration.

### Fixed
- Describe the issue that was corrected.

### Tests
- State the actual test suite/validation result.
```

Only include headings that apply. Describe outcomes, not vague statements such as "made improvements." Use the actual date of the delivered patch, not an estimated or future date.

---

## 12. Subscriber privacy and security checks

For every subscription-system change, verify all of the following:

- An application cannot be created until Firebase email-link sign-in completes and the Firebase Auth token reports a verified email.
- A visitor can read only their own subscriber document. A normal verified account cannot list all subscribers or modify another user's record.
- A visitor cannot set their own status to `active`, `rejected`, `suspended`, or `removed`.
- An unsubscribe operation requires a fresh sign-in link and a separate confirmation action; merely entering another person's email must never alter that person's record.
- The configured administrator can list and manage records only when signed in with the exact verified admin email configured privately in Firestore rules, and non-admin accounts are denied by Firestore rules even if they manually call the SDK.
- Product alert email delivery sends one message per recipient. No To/CC/BCC list containing multiple subscribers is allowed.
- Delivery-retry documents are in private Firestore subcollections and are not copied to the public status JSON.
- Secrets remain in GitHub Actions Secrets. Firebase web configuration values are public identifiers and must never contain a private key.
- Update `firebase/firestore.rules`, `docs/firebase-config.js`, `docs/FIREBASE_SETUP.md`, and tests together when changing roles, collection paths, status names, or preferences.

## 13. Definition of done


A change is complete only when all applicable statements are true:

- [ ] The exact requested behavior is implemented, not merely represented by a mockup or placeholder.
- [ ] Existing user requirements and working behavior are preserved.
- [ ] Configuration, defaults, and secrets are documented and match the code.
- [ ] Automated tests and relevant manual checks have been run and their results are reported honestly.
- [ ] The roadmap reflects verified implementation status.
- [ ] The changelog has a newest-first dated version entry.
- [ ] This guide and README are synchronized when their information changed.
- [ ] The ZIP contains only the intended changed files and installs to the correct repository paths in a clean-copy test.
- [ ] The final delivery identifies all changed files and gives a working patch download.

**Do not mark the change complete while any required item is unchecked.** If a step cannot be completed in the available environment, identify it as outstanding rather than implying it passed.

## Manual Firebase Rules deployment

Firestore Rules are not deployed by GitHub Pages or the ZIP patch installer. Whenever a release changes `firebase/firestore.rules`, the owner must copy the updated file into Firebase Console → Firestore Database → Rules, re-enter the private administrator email, preserve intended project-specific changes, and click Publish.


## Firebase browser API-key referrer restrictions

Firebase email-link authentication opens its action handler on the configured `<PROJECT_ID>.firebaseapp.com` auth domain before returning to GitHub Pages. When a Firebase Web API key is restricted to HTTP referrers, allow both the public site and the Firebase auth handler. For the current PokéDrop Watch deployment, the allowed patterns are:

```text
https://n0nam3-bot.github.io/*
https://project-4868291462124176670.firebaseapp.com/*
```

Edit the matching Firebase browser API key in [Google Cloud API Credentials](https://console.cloud.google.com/apis/credentials?project=project-4868291462124176670). This resolves `403 API_KEY_HTTP_REFERRER_BLOCKED` errors caused by the missing Firebase auth domain. Do not paste service-account JSON or Gmail credentials into the browser config. See `docs/FIREBASE_SETUP.md` → Step 4B for the mobile click-by-click procedure.

## Source health interpretation

- `MATCHES`: current fetch succeeded and the parser recognized Pokémon listings or feed entries.
- `NO MATCH`: fetch succeeded but the parser recognized no usable entries; this does not mean the retailer has no inventory.
- `ISSUE`: the request failed before parsing.

Record real scan evidence and preserve the distinction between a parser miss and a network failure. Do not claim retailer coverage until a source-specific fixture and scan test both pass. See `docs/SOURCE_HEALTH.md`.
