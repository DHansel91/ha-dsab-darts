"""DSAB-Dartliga (3K Darts) für Home Assistant."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import DartsApiClient
from .card import async_register_card
from .const import CONF_MANDANT_KEY, DEFAULT_MANDANT_KEY, DOMAIN
from .coordinator import DartsConfigEntry, DartsCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Lovelace-Card bereitstellen, unabhängig von einzelnen Einträgen."""
    await async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DartsConfigEntry) -> bool:
    client = DartsApiClient(
        async_get_clientsession(hass),
        entry.data.get(CONF_MANDANT_KEY, DEFAULT_MANDANT_KEY),
    )
    coordinator = DartsCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DartsConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: DartsConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
