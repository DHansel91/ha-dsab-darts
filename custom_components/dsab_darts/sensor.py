"""Sensoren für Liga und (optional) eigenes Team."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import TOP_PLAYERS
from .coordinator import DartsConfigEntry, DartsCoordinator
from .entity import DartsEntity
from .models import LeagueData, Match

# Große Listen nicht in die Recorder-Datenbank schreiben
BIG_ATTRS = frozenset({"tabelle", "spiele", "spieler"})


@dataclass(frozen=True, kw_only=True)
class DartsSensorDescription(SensorEntityDescription):
    value_fn: Callable[[LeagueData, int | None], Any]
    attr_fn: Callable[[LeagueData, int | None], dict[str, Any]] = lambda d, t: {}
    team_only: bool = False


# --- Hilfsfunktionen ----------------------------------------------------------


def _next_round(data: LeagueData) -> list[Match]:
    nxt = data.next_match(None, dt_util.utcnow())
    if nxt is None:
        return []
    return [m for m in data.matches if m.round_name == nxt.round_name]


def _last_round(data: LeagueData) -> list[Match]:
    last = data.last_match(None)
    if last is None:
        return []
    return [m for m in data.matches if m.round_name == last.round_name]


def _first_planned(matches: list[Match]) -> datetime | None:
    return min((m.planned for m in matches if m.planned), default=None)


def _match_attrs(match: Match | None, team_id: int, data: LeagueData) -> dict[str, Any]:
    if match is None:
        return {}
    return {
        "gegner": match.opponent(team_id),
        "heimspiel": match.is_home(team_id),
        "spieltag": match.round_name,
        "termin": match.planned.isoformat() if match.planned else None,
        "ergebnis": match.score,
        "legs": match.as_dict()["legs"],
        "ausgang": match.outcome(team_id),
        "spiellokal": match.venue.name if match.venue else None,
        "adresse": match.venue.address if match.venue else None,
        "gegner_platz": next(
            (
                r.placement
                for r in data.table
                if r.participant_id
                == (match.guest_id if match.is_home(team_id) else match.home_id)
            ),
            None,
        ),
    }


def _last_result_value(data: LeagueData, team_id: int | None) -> str | None:
    match = data.last_match(team_id)
    if match is None or match.score is None:
        return None
    # Ergebnis aus eigener Sicht (eigene Sets zuerst)
    if match.is_home(team_id):
        return f"{match.sets_home}:{match.sets_guest}"
    return f"{match.sets_guest}:{match.sets_home}"


def _row_attr(data: LeagueData, team_id: int | None) -> dict[str, Any]:
    row = data.table_row(team_id) if team_id is not None else None
    return row.as_dict() if row else {}


def _team_players(data: LeagueData, team_id: int | None) -> list[dict[str, Any]]:
    name = data.team_name(team_id) if team_id is not None else None
    return [p.as_dict() for p in data.players if name and p.team == name]


# --- Beschreibungen -------------------------------------------------------------

LEAGUE_SENSORS: tuple[DartsSensorDescription, ...] = (
    DartsSensorDescription(
        key="tabellenfuehrer",
        translation_key="leader",
        icon="mdi:trophy",
        value_fn=lambda d, t: d.table[0].name if d.table else None,
        attr_fn=lambda d, t: {
            "liga": d.event_name,
            "saison": d.season_name,
            "region": d.region_name,
            "tabelle": [r.as_dict() for r in d.table],
        },
    ),
    DartsSensorDescription(
        key="naechster_spieltag",
        translation_key="next_round",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-clock",
        value_fn=lambda d, t: _first_planned(_next_round(d)),
        attr_fn=lambda d, t: {
            "spieltag": (r[0].round_name if (r := _next_round(d)) else None),
            "spiele": [m.as_dict() for m in _next_round(d)],
        },
    ),
    DartsSensorDescription(
        key="letzter_spieltag",
        translation_key="last_round",
        icon="mdi:scoreboard",
        value_fn=lambda d, t: (r[0].round_name if (r := _last_round(d)) else None),
        attr_fn=lambda d, t: {"spiele": [m.as_dict() for m in _last_round(d)]},
    ),
    DartsSensorDescription(
        key="spielerrangliste",
        translation_key="top_player",
        icon="mdi:account-star",
        value_fn=lambda d, t: d.players[0].name if d.players else None,
        attr_fn=lambda d, t: {
            "spieler": [p.as_dict() for p in d.players[:TOP_PLAYERS]]
        },
    ),
)

TEAM_SENSORS: tuple[DartsSensorDescription, ...] = (
    DartsSensorDescription(
        key="tabellenplatz",
        translation_key="placement",
        icon="mdi:podium",
        state_class=SensorStateClass.MEASUREMENT,
        team_only=True,
        value_fn=lambda d, t: (r.placement if (r := d.table_row(t)) else None),
        attr_fn=_row_attr,
    ),
    DartsSensorDescription(
        key="punkte",
        translation_key="points",
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
        team_only=True,
        value_fn=lambda d, t: (r.points if (r := d.table_row(t)) else None),
    ),
    DartsSensorDescription(
        key="naechstes_spiel",
        translation_key="next_match",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:dart",
        team_only=True,
        value_fn=lambda d, t: (
            m.planned if (m := d.next_match(t, dt_util.utcnow())) else None
        ),
        attr_fn=lambda d, t: _match_attrs(d.next_match(t, dt_util.utcnow()), t, d),
    ),
    DartsSensorDescription(
        key="letztes_ergebnis",
        translation_key="last_result",
        icon="mdi:scoreboard-outline",
        team_only=True,
        value_fn=_last_result_value,
        attr_fn=lambda d, t: _match_attrs(d.last_match(t), t, d),
    ),
    DartsSensorDescription(
        key="spielerstatistik",
        translation_key="team_players",
        icon="mdi:account-group",
        team_only=True,
        value_fn=lambda d, t: len(_team_players(d, t)),
        attr_fn=lambda d, t: {"spieler": _team_players(d, t)},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DartsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    descriptions = list(LEAGUE_SENSORS)
    if coordinator.team_id is not None:
        descriptions += TEAM_SENSORS
    async_add_entities(DartsSensor(coordinator, d) for d in descriptions)


class DartsSensor(DartsEntity, SensorEntity):
    entity_description: DartsSensorDescription
    _unrecorded_attributes = BIG_ATTRS

    def __init__(
        self, coordinator: DartsCoordinator, description: DartsSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data, self.team_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attr_fn(self.coordinator.data, self.team_id)
