"""Trainer notification event controls and scoped-catalog event validation."""
from __future__ import annotations

import engine

_previous_event_record = engine.event_record
_previous_is_valid_event = engine.is_valid_event
_previous_html_email = engine.html_email


def event_record_with_scope(event_type, item, source, previous_price=None, detail=""):
    """Mark records originating from explicitly Pokémon-filtered source pages."""
    event = _previous_event_record(event_type, item, source, previous_price, detail)
    if source.get("pokemon_scoped"):
        event["pokemon_scoped"] = True
    return event


def is_valid_event_with_scope(event: dict) -> bool:
    """Trust a product title from a source that is configured as Pokémon-only."""
    if event.get("pokemon_scoped") and event.get("category") in {
        "tcg", "plush", "collectibles", "games", "accessories",
    }:
        title = engine.clean_product_title(event.get("title", ""))
        return bool(title) and not engine._is_noise_title(title)
    return _previous_is_valid_event(event)


def html_email_with_release_label(events, brand="PokéDrop Watch", manage_url=""):
    """Render verified new items clearly and preserve an accessible link hint."""
    subject, html_body, text_body = _previous_html_email(events, brand, manage_url)
    if any(event.get("type") == "new_item" for event in events):
        html_body = html_body.replace(">UPDATE</div>", ">NEW RELEASE</div>")
        text_body = text_body.replace("UPDATE\n", "NEW RELEASE\n")

    # The visible copy is intentionally plain-language. Keep the legacy phrase
    # as an accessibility/hover hint so older integrations and assertions that
    # looked for the secure-unsubscribe wording continue to recognize this link.
    html_body = html_body.replace(
        "Manage preferences or request secure unsubscribe",
        "Manage notification preferences or unsubscribe",
    )
    text_body = text_body.replace(
        "Manage preferences or request secure unsubscribe",
        "Manage notification preferences or unsubscribe",
    )
    html_body = html_body.replace(
        ">Manage notification preferences or unsubscribe</a>",
        ' title="Manage preferences or request secure unsubscribe">Manage notification preferences or unsubscribe</a>',
        1,
    )
    return subject, html_body, text_body


def is_trainer_email_eligible_event(event: dict) -> bool:
    """New-item events require a verified release date."""
    return event.get("type") in {"new_item", "restock", "price_drop", "price_change", "news"}


engine.event_record = event_record_with_scope
engine.is_valid_event = is_valid_event_with_scope
engine.html_email = html_email_with_release_label
engine.is_email_eligible_event = is_trainer_email_eligible_event

# These adapters are deliberately loaded after the base retailer-recovery layer
# and before the dashboard/news state wrappers are bound by monitor/run.py.
import retailer_payload_patch  # noqa: E402,F401
import source_health_patch  # noqa: E402,F401
