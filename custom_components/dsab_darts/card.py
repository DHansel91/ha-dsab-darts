"""Stellt die Lovelace-Card bereit und registriert sie im Frontend."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILE = Path(__file__).parent / "www" / "dsab-darts-card.js"
CARD_URL = f"/{DOMAIN}/dsab-darts-card.js"
_REGISTERED = f"{DOMAIN}_card_registered"


async def async_register_card(hass: HomeAssistant) -> None:
    """Card-Datei ausliefern und als Frontend-Modul laden lassen (einmalig)."""
    if hass.data.get(_REGISTERED):
        return
    # Ohne Frontend (z. B. in Tests oder bei minimalen Setups) gibt es nichts zu tun.
    if "frontend" not in hass.config.components or hass.http is None:
        return

    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    integration = await async_get_integration(hass, DOMAIN)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_FILE), True)]
    )
    # Version als Query-Parameter, damit Browser nach einem Update neu laden
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")
    hass.data[_REGISTERED] = True
    _LOGGER.debug("Lovelace-Card unter %s registriert", CARD_URL)
