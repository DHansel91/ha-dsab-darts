"""Kalender mit allen Spielen (bzw. nur denen des eigenen Teams)."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import MATCH_DURATION
from .coordinator import DartsConfigEntry, DartsCoordinator
from .entity import DartsEntity
from .models import Match


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DartsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([DartsCalendar(entry.runtime_data)])


class DartsCalendar(DartsEntity, CalendarEntity):
    _attr_translation_key = "matches"
    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator: DartsCoordinator) -> None:
        super().__init__(coordinator, "kalender")

    def _events(self) -> list[CalendarEvent]:
        return [
            _to_event(m)
            for m in self.coordinator.data.matches_for(self.team_id)
            if m.planned and not m.bye
        ]

    @property
    def event(self) -> CalendarEvent | None:
        """Laufendes oder nächstes Spiel."""
        now = dt_util.utcnow()
        upcoming = [e for e in self._events() if e.end > now]
        return min(upcoming, key=lambda e: e.start, default=None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [e for e in self._events() if e.start < end_date and e.end > start_date]


def _to_event(match: Match) -> CalendarEvent:
    start = dt_util.as_utc(match.planned)
    summary = match.title
    if match.score:
        summary = f"{summary} ({match.score})"
    description = match.round_name
    if match.finished and match.legs_home is not None:
        description += f"\nSets {match.score}, Legs {match.legs_home}:{match.legs_guest}"
    return CalendarEvent(
        start=start,
        end=start + MATCH_DURATION,
        summary=summary,
        description=description,
        location=match.venue.address if match.venue else None,
        uid=f"dsab-{match.match_id}",
    )
