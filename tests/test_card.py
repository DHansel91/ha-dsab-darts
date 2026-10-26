"""Registrierung der Lovelace-Card."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant

from custom_components.dsab_darts.card import CARD_FILE, CARD_URL, async_register_card


async def test_card_file_exists() -> None:
    assert CARD_FILE.is_file()
    assert "customElements.define(\"dsab-darts-card\"" in CARD_FILE.read_text("utf-8")


async def test_card_not_registered_without_frontend(hass: HomeAssistant) -> None:
    await async_register_card(hass)
    assert not hass.data.get("dsab_darts_card_registered")


async def test_card_registered_once(hass: HomeAssistant) -> None:
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL

    hass.config.components.add("frontend")
    urls = MagicMock()
    hass.data[DATA_EXTRA_MODULE_URL] = urls
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    await async_register_card(hass)
    await async_register_card(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    (config,) = hass.http.async_register_static_paths.call_args.args[0]
    assert config.url_path == CARD_URL
    assert config.path == str(CARD_FILE)
    urls.add.assert_called_once()
    assert urls.add.call_args.args[0].startswith(f"{CARD_URL}?v=")
