"""DataUpdateCoordinator für eine Liga."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DartsApiClient, DartsApiError
from .const import (
    CONF_EVENT_ID,
    CONF_PHASE_ID,
    CONF_SCAN_INTERVAL,
    CONF_TEAM_ID,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    MATCHDAY_SCAN_INTERVAL,
    MATCHDAY_WINDOW,
    NO_TEAM,
)
from .models import (
    LeagueData,
    parse_matches,
    parse_players,
    parse_table,
    parse_teams,
)

_LOGGER = logging.getLogger(__name__)

type DartsConfigEntry = ConfigEntry[DartsCoordinator]


class DartsCoordinator(DataUpdateCoordinator[LeagueData]):
    """Lädt Liga, Tabelle, Spiele, Teams und Spielerstatistik."""

    config_entry: DartsConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: DartsConfigEntry, client: DartsApiClient
    ) -> None:
        self._normal_interval = timedelta(
            minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN)
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.data[CONF_EVENT_ID]}",
            update_interval=self._normal_interval,
        )
        self.client = client
        self.event_id: int = entry.data[CONF_EVENT_ID]
        self.phase_id: int = entry.data[CONF_PHASE_ID]
        team = entry.data.get(CONF_TEAM_ID, NO_TEAM)
        self.team_id: int | None = None if team in (None, NO_TEAM) else int(team)

    async def _async_update_data(self) -> LeagueData:
        try:
            event, table, matches, participants = await asyncio.gather(
                self.client.event(self.event_id),
                self.client.table(self.event_id),
                self.client.matches(self.event_id, self.phase_id),
                self.client.participants(self.event_id),
            )
        except DartsApiError as err:
            raise UpdateFailed(f"Fehler beim Abruf der Liga {self.event_id}: {err}") from err

        info = event.get("event") or {}
        players = []
        if info.get("frontendShowPlayerResults", True):
            try:
                players = parse_players(await self.client.player_results(self.event_id))
            except DartsApiError as err:
                # Spielerstatistik ist optional – Liga-Daten trotzdem liefern
                _LOGGER.debug("Spielerstatistik nicht verfügbar: %s", err)

        data = LeagueData(
            event_id=self.event_id,
            event_name=info.get("name", str(self.event_id)),
            season_name=(info.get("saison") or {}).get("name", ""),
            region_name=(info.get("region") or {}).get("name", ""),
            db_id=info.get("dbId"),
            table=parse_table(table, self.phase_id),
            matches=parse_matches(matches),
            teams=parse_teams(participants),
            players=players,
        )
        # Spiellokal fehlt bei manchen Spielen in der Match-Antwort -> aus Teamdaten ergänzen
        for match in data.matches:
            if match.venue is None and (team := data.teams.get(match.home_id)):
                match.venue = team.venue

        self._adjust_interval(data)
        return data

    def _adjust_interval(self, data: LeagueData) -> None:
        """Während eines laufenden Spieltags öfter abfragen."""
        now = dt_util.utcnow()
        live = any(
            not m.finished
            and m.planned is not None
            and m.planned <= now <= m.planned + MATCHDAY_WINDOW
            for m in data.matches_for(self.team_id)
        )
        self.update_interval = (
            min(MATCHDAY_SCAN_INTERVAL, self._normal_interval)
            if live
            else self._normal_interval
        )
