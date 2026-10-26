"""DSAB-Dartliga (3K Darts) für Home Assistant."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DartsApiClient
from .const import CONF_MANDANT_KEY, DEFAULT_MANDANT_KEY
from .coordinator import DartsConfigEntry, DartsCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]


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
