"""Serve the Smart Heating Control Lovelace card and add it to the dashboards.

1. The file is served by the integration at CARD_URL (no cache headers).
2. It is added as a Lovelace **resource** (storage mode). Resources are loaded
   every time a dashboard loads, so the card is found even after the browser /
   companion app cache expires.
3. Only when that is impossible (YAML-mode dashboards, read-only resources) it
   is registered as an extra frontend module instead.

The ``?v=<version>`` query string makes every client fetch the new file after
an update.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant

from .const import CARD_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILE = Path(__file__).parent / "www" / "advanced-climate-card.js"
MANIFEST = Path(__file__).parent / "manifest.json"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and make every dashboard load it."""
    if hass.data.get(f"{DOMAIN}_card_registered"):
        return
    try:
        from homeassistant.components.http import StaticPathConfig  # noqa: PLC0415

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_FILE), False)]
        )
    except RuntimeError:
        pass  # already registered (integration reloaded)
    except (AttributeError, ImportError):
        _LOGGER.debug("HTTP not available, the card is not registered")
        return
    hass.data[f"{DOMAIN}_card_registered"] = True

    manifest = json.loads(await hass.async_add_executor_job(MANIFEST.read_text, "utf-8"))
    url = f"{CARD_URL}?v={manifest.get('version', '0')}"

    def _extra_module() -> None:
        """Load the card on every page (when it cannot be a dashboard resource)."""
        try:
            from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

            add_extra_js_url(hass, url)
        except (ImportError, KeyError):
            _LOGGER.debug("Frontend not loaded, extra module not added")

    async def _add_resource(_event: Event | None = None) -> None:
        """Add the card as a dashboard resource, or as an extra module if that fails."""
        try:
            if not await async_ensure_lovelace_resource(hass, url):
                _extra_module()
        except Exception as err:  # noqa: BLE001 - never block setup
            _LOGGER.warning("Could not add the Smart Heating Control card as a resource: %s", err)
            _extra_module()

    if hass.state is CoreState.running:
        await _add_resource()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _add_resource)


def lovelace_resources(hass: HomeAssistant) -> Any:
    """Return the storage resource collection, or None (YAML mode / no lovelace)."""
    data = hass.data.get("lovelace")
    if data is None:
        return None
    resources = getattr(data, "resources", None)
    if resources is None and isinstance(data, dict):
        resources = data.get("resources")
    if resources is None or not hasattr(resources, "async_create_item"):
        return None
    return resources


async def async_ensure_lovelace_resource(hass: HomeAssistant, url: str) -> bool:
    """Create or update the card resource. False when resources are read-only."""
    resources = lovelace_resources(hass)
    if resources is None:
        _LOGGER.info(
            "Dashboards are in YAML mode: add %s (type: module) to the resources "
            "if the Smart Heating Control card does not show up",
            url,
        )
        return False
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True
    mine = [
        item
        for item in resources.async_items()
        if str(item.get("url", "")).split("?")[0] == CARD_URL
    ]
    if mine:
        first, *duplicates = mine
        if first.get("url") != url or first.get("type") != "module":
            await resources.async_update_item(first["id"], {"res_type": "module", "url": url})
        for item in duplicates:
            await resources.async_delete_item(item["id"])
        return True
    await resources.async_create_item({"res_type": "module", "url": url})
    _LOGGER.info("Added the Smart Heating Control card to the dashboard resources (%s)", url)
    return True


async def async_remove_lovelace_resource(hass: HomeAssistant) -> None:
    """Remove the card resource (when the last house is deleted)."""
    resources = lovelace_resources(hass)
    if resources is None:
        return
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True
    for item in list(resources.async_items()):
        if str(item.get("url", "")).split("?")[0] == CARD_URL:
            await resources.async_delete_item(item["id"])
