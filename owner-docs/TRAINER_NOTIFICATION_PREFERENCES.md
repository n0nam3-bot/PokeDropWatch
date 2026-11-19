# Trainer notification preferences and source recovery

## What changed

- Retailer product parsing now checks nested hydration objects, retailer data attributes, more title/name fields, and product-card elements that do not expose their names as headings. Items extracted from explicitly Pokémon-filtered category pages retain that source-scope marker, so a card title such as “Elite Trainer Box” is not discarded merely because the card omits the word Pokémon. Target TCIN and Amazon ASIN routes can be derived only from their explicit identifiers.
- A source with one successful page out of three is marked **PARTIAL** (warning), not fully healthy. Recognized items from the responding pages are retained and shown; prior catalogue totals are not discarded during partial responses. Failed-page counts and compact response diagnostics are attached to the source status.
- Verified **New releases**, **Restocks**, **Price drops**, and **Pokémon news** can be selected individually. News is controlled by the notification-type selector and does not depend on which product categories a Trainer chooses. Verified new-release alerts are labeled **NEW RELEASE** in email and are also retained for owner-email retry if an SMTP send fails. `new_item` is only emitted for a listing with a published release date inside the monitor's current release window; `first_seen` is still not marketed as a new release.
- Trainers can list up to 20 product phrases (80 characters per phrase). Separate names with commas, semicolons, or new lines. A match against any phrase is enough. A blank list means all products that match their selected category/retailer choices.
- Existing Firestore subscribers without the new fields receive the four new preference types by default; their previous category/retailer preferences are preserved. Generic `price_change` emails are not one of the selectable Trainer event types.

## Trainer vs. Gym Leader permissions

Trainers **can manage their own notification preferences**: enter the same verified email address on Notify, change product categories/retailers/event types/item phrases, request the one-time code, and verify it. The Apps Script backend preserves an existing `active` or `suspended` status while updating the preference fields. New applications remain `pending` until approved.

Gym Leaders continue to control account moderation: approve, reject, suspend, reactivate, or remove a subscriber. The current Admin endpoint does not edit a Trainer's category/event/item watchlist settings; the Trainer edits those directly after proving mailbox ownership. Subscriber emails now link directly to the GitHub Pages Notify portal for these changes.

## Install

1. Upload this ZIP to the repository's `updates/` folder and commit it. Do not manually unzip it into the repository. The current patch installer applies files from the ZIP.
2. **Separately update Apps Script** (a GitHub ZIP does not update the Google-hosted deployment): open the existing PokéDrop Watch Apps Script project, replace the entire `Code.gs` with `backend/apps-script/Code.gs` from this patch, save, then choose **Deploy → Manage deployments → Edit → New version → Deploy**. Keep the existing `/exec` URL and Script Properties. No `Subscribe.html` replacement is required; `Code.gs` injects the Trainer controls into the current hosted Notify page.
3. Open GitHub Actions and confirm the tests pass and the scan runs. Check the source list for PARTIAL warnings and re-check the parser counts on a later scan.

## Interpreting recovery results

- **MATCHES / OK**: all configured pages responded and at least one product/news record was recognized.
- **PARTIAL**: at least one configured page responded, but one or more primary/alternate pages failed. Any recognized listings are still useful, but the source is not marked fully healthy.
- **NO MATCH / warning**: pages responded, but the supported page content did not expose recognizable product/news records. This is not evidence that the retailer has no stock. Response diagnostics help distinguish an empty client-rendered shell, a challenge page, and selector coverage gaps.
- **ISSUE / error**: no configured page responded successfully.

The monitor does not execute retailer JavaScript, solve CAPTCHAs/queues, or bypass anti-bot systems. A source cannot be declared fixed until a hosted scan confirms item counts against a real response.
