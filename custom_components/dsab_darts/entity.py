"""Gemeinsame Basisklasse."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_EVENT_ID, CONF_PHASE_ID, DOMAIN, PORTAL_BASE
from .coordinator import DartsCoordinator


class DartsEntity(CoordinatorEntity[DartsCoordinator]):
    _attr_has_entity_name = True
    _attr_attribution = "Daten: DSAB / 3K Darts"

    def __init__(self, coordinator: DartsCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        data = coordinator.data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="DSAB / 3K Darts",
            model=f"{data.region_name} · {data.season_name}".strip(" ·"),
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=(
                f"{PORTAL_BASE}/{data.db_id}/event/{entry.data[CONF_EVENT_ID]}"
                f"/phase/{entry.data[CONF_PHASE_ID]}/group/0"
                if data.db_id is not None
                else None
            ),
        )

    @property
    def team_id(self) -> int | None:
        return self.coordinator.team_id
