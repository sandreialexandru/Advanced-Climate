"""Serve and register the Advanced Climate Lovelace card."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import CARD_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILE = Path(__file__).parent / "www" / "advanced-climate-card.js"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it in the frontend (no manual resource needed)."""
    if hass.data.get(f"{DOMAIN}_card_registered"):
        return
    if getattr(hass, "http", None) is None or "frontend" not in hass.config.components:
        return
    manifest = json.loads(
        await hass.async_add_executor_job(
            (Path(__file__).parent / "manifest.json").read_text, "utf-8"
        )
    )
    version = manifest.get("version", "0")
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_FILE), True)]
        )
    except RuntimeError:
        _LOGGER.debug("Card path already registered")
    add_extra_js_url(hass, f"{CARD_URL}?v={version}")
    hass.data[f"{DOMAIN}_card_registered"] = True
