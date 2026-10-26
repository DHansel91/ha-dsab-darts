"""Config-Flow: Region → Saison → Liga → (Phase) → Team."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import DartsApiClient, DartsApiError
from .const import (
    CONF_EVENT_ID,
    CONF_EVENT_NAME,
    CONF_MANDANT_KEY,
    CONF_PHASE_ID,
    CONF_REGION_ID,
    CONF_REGION_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SEASON_ID,
    CONF_SEASON_NAME,
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    DEFAULT_MANDANT_KEY,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    MIN_SCAN_INTERVAL_MIN,
    NO_TEAM,
)

_LOGGER = logging.getLogger(__name__)


def _dropdown(options: list[SelectOptionDict]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN, sort=False)
    )


class DartsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Auswahl der Liga in mehreren Schritten."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {CONF_MANDANT_KEY: DEFAULT_MANDANT_KEY}
        self._regions: dict[str, str] = {}
        self._seasons: dict[str, str] = {}
        self._events: dict[str, dict[str, Any]] = {}
        self._phases: dict[str, str] = {}
        self._teams: dict[str, str] = {}
        self._client: DartsApiClient | None = None

    @property
    def client(self) -> DartsApiClient:
        if self._client is None:
            self._client = DartsApiClient(
                async_get_clientsession(self.hass), self._data[CONF_MANDANT_KEY]
            )
        return self._client

    # 1) Region / Spielgebiet
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            region_id = user_input[CONF_REGION_ID]
            self._data[CONF_REGION_ID] = int(region_id)
            self._data[CONF_REGION_NAME] = self._regions[region_id]
            return await self.async_step_season()

        try:
            regions = await self.client.regions()
        except DartsApiError as err:
            _LOGGER.warning("3K-Darts-Backend nicht erreichbar: %s", err)
            return self.async_abort(reason="cannot_connect")

        regions.sort(key=lambda r: r.get("name", "").casefold())
        self._regions = {str(r["id"]): r["name"] for r in regions}
        if not self._regions:
            return self.async_abort(reason="no_regions")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGION_ID): _dropdown(
                        [SelectOptionDict(value=k, label=v) for k, v in self._regions.items()]
                    )
                }
            ),
        )

    # 2) Saison
    async def async_step_season(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            season_id = user_input[CONF_SEASON_ID]
            self._data[CONF_SEASON_ID] = int(season_id)
            self._data[CONF_SEASON_NAME] = self._seasons[season_id]
            return await self.async_step_event()

        try:
            seasons = await self.client.seasons(self._data[CONF_REGION_ID])
        except DartsApiError as err:
            _LOGGER.warning("3K-Darts-Backend nicht erreichbar: %s", err)
            return self.async_abort(reason="cannot_connect")

        # API liefert die neueste Saison zuerst
        self._seasons = {str(s["id"]): s["name"] for s in seasons}
        if not self._seasons:
            return self.async_abort(reason="no_seasons")

        return self.async_show_form(
            step_id="season",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SEASON_ID, default=next(iter(self._seasons))
                    ): _dropdown(
                        [SelectOptionDict(value=k, label=v) for k, v in self._seasons.items()]
                    )
                }
            ),
            description_placeholders={"region": self._data[CONF_REGION_NAME]},
        )

    # 3) Liga (z. B. "BZ 01", "A 02")
    async def async_step_event(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            event = self._events[user_input[CONF_EVENT_ID]]
            self._data[CONF_EVENT_ID] = event["id"]
            self._data[CONF_EVENT_NAME] = event["name"]
            phases = [p for p in event.get("phases") or [] if p.get("id")]
            self._phases = {
                str(p["id"]): p.get("name") or str(p["id"]) for p in phases
            }
            if len(self._phases) > 1:
                return await self.async_step_phase()
            if self._phases:
                self._data[CONF_PHASE_ID] = int(next(iter(self._phases)))
                return await self.async_step_team()
            errors["base"] = "no_phase"

        try:
            events = await self.client.events(
                self._data[CONF_REGION_ID], self._data[CONF_SEASON_ID]
            )
        except DartsApiError as err:
            _LOGGER.warning("3K-Darts-Backend nicht erreichbar: %s", err)
            return self.async_abort(reason="cannot_connect")

        # Reihenfolge der API beibehalten – sie ist nach Spielklasse sortiert
        # (BZO, BZ, A, B, C …), nicht alphabetisch.
        events = [e for e in events if e.get("eventTypeCd", "LEAGUE") == "LEAGUE"]
        self._events = {str(e["id"]): e for e in events}
        if not self._events:
            return self.async_abort(reason="no_events")

        return self.async_show_form(
            step_id="event",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EVENT_ID): _dropdown(
                        [
                            SelectOptionDict(value=k, label=e["name"])
                            for k, e in self._events.items()
                        ]
                    )
                }
            ),
            errors=errors,
            description_placeholders={
                "region": self._data[CONF_REGION_NAME],
                "season": self._data[CONF_SEASON_NAME],
            },
        )

    # 3b) Phase – nur wenn eine Liga mehrere hat (z. B. Vorrunde/Play-offs)
    async def async_step_phase(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._data[CONF_PHASE_ID] = int(user_input[CONF_PHASE_ID])
            return await self.async_step_team()

        return self.async_show_form(
            step_id="phase",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PHASE_ID): _dropdown(
                        [SelectOptionDict(value=k, label=v) for k, v in self._phases.items()]
                    )
                }
            ),
        )

    # 4) Optional ein eigenes Team
    async def async_step_team(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            team_id = user_input[CONF_TEAM_ID]
            self._data[CONF_TEAM_ID] = team_id
            self._data[CONF_TEAM_NAME] = self._teams.get(team_id)

            await self.async_set_unique_id(
                f"{self._data[CONF_EVENT_ID]}_{self._data[CONF_PHASE_ID]}_{team_id}"
            )
            self._abort_if_unique_id_configured()

            title = f"{self._data[CONF_EVENT_NAME]} ({self._data[CONF_SEASON_NAME]})"
            if team_id != NO_TEAM:
                title = f"{self._teams[team_id]} – {title}"
            return self.async_create_entry(title=title, data=self._data)

        try:
            participants = await self.client.participants(self._data[CONF_EVENT_ID])
        except DartsApiError as err:
            _LOGGER.warning("3K-Darts-Backend nicht erreichbar: %s", err)
            return self.async_abort(reason="cannot_connect")

        teams = sorted(
            (p for p in participants if not p.get("retired")),
            key=lambda p: p.get("displayName", "").casefold(),
        )
        self._teams = {str(p["id"]): p.get("displayName", str(p["id"])) for p in teams}
        options = [SelectOptionDict(value=NO_TEAM, label="— Kein Team (nur Liga) —")]
        options += [SelectOptionDict(value=k, label=v) for k, v in self._teams.items()]

        return self.async_show_form(
            step_id="team",
            data_schema=vol.Schema(
                {vol.Required(CONF_TEAM_ID, default=NO_TEAM): _dropdown(options)}
            ),
            description_placeholders={"league": self._data[CONF_EVENT_NAME]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> DartsOptionsFlow:
        return DartsOptionsFlow()


class DartsOptionsFlow(OptionsFlow):
    """Aktualisierungsintervall."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_MIN,
                            max=1440,
                            step=5,
                            unit_of_measurement="min",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
