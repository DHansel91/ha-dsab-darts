"""Datenmodelle und Parser für die 3K-Darts/DSAB-API.

Bewusst ohne Home-Assistant-Imports, damit die Parser separat testbar sind.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

STATUS_FINISHED = "FINISH"


def parse_datetime(value: str | None) -> datetime | None:
    """Parst Zeitstempel wie '2026-10-24T18:00:00.000+0000'."""
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@dataclass(slots=True)
class Venue:
    name: str
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    boards: int | None = None

    @property
    def address(self) -> str:
        city = " ".join(p for p in (self.postal_code, self.city) if p)
        return ", ".join(p for p in (self.name, self.street, city) if p)

    @classmethod
    def from_api(cls, data: dict[str, Any] | None) -> Venue | None:
        if not data:
            return None
        return cls(
            name=data.get("name", ""),
            street=data.get("locationStreet"),
            postal_code=data.get("locationPostalCode"),
            city=data.get("locationCity"),
            boards=data.get("numberOfBoards"),
        )


@dataclass(slots=True)
class Team:
    participant_id: int
    name: str
    venue: Venue | None = None
    weekday: int | None = None
    throwoff_time: str | None = None

    @classmethod
    def from_participant(cls, data: dict[str, Any]) -> Team:
        team_season = data.get("teamSeason") or {}
        return cls(
            participant_id=data["id"],
            name=data.get("displayName") or team_season.get("name", ""),
            venue=Venue.from_api(team_season.get("playingVenue")),
            weekday=team_season.get("weekdayMatch"),
            throwoff_time=team_season.get("throwoffTime"),
        )


@dataclass(slots=True)
class TableRow:
    placement: int
    participant_id: int
    name: str
    matches: int
    won: int
    tied: int
    lost: int
    points: float
    points_against: float
    sets_won: int
    sets_lost: int
    legs_won: int
    legs_lost: int

    @property
    def sets_diff(self) -> int:
        return self.sets_won - self.sets_lost

    @property
    def legs_diff(self) -> int:
        return self.legs_won - self.legs_lost

    def as_dict(self) -> dict[str, Any]:
        return {
            "platz": self.placement,
            "team": self.name,
            "spiele": self.matches,
            "siege": self.won,
            "unentschieden": self.tied,
            "niederlagen": self.lost,
            "punkte": _num(self.points),
            "gegenpunkte": _num(self.points_against),
            "sets": f"{self.sets_won}:{self.sets_lost}",
            "sets_diff": self.sets_diff,
            "legs": f"{self.legs_won}:{self.legs_lost}",
            "legs_diff": self.legs_diff,
        }

    @classmethod
    def from_api(cls, data: dict[str, Any], fallback_index: int) -> TableRow:
        placement = str(data.get("placement") or "").rstrip(".")
        return cls(
            placement=int(placement) if placement.isdigit() else fallback_index + 1,
            participant_id=data.get("participantId"),
            name=data.get("participantName", ""),
            matches=data.get("matchCount", 0),
            won=data.get("win", 0),
            tied=data.get("tie", 0),
            lost=data.get("lost", 0),
            points=data.get("points1", 0.0),
            points_against=data.get("points2", 0.0),
            sets_won=data.get("sets1", 0),
            sets_lost=data.get("sets2", 0),
            legs_won=data.get("legs1", 0),
            legs_lost=data.get("legs2", 0),
        )


@dataclass(slots=True)
class Match:
    match_id: int
    round_name: str
    planned: datetime | None
    status: str
    home_id: int
    home_name: str
    guest_id: int
    guest_name: str
    sets_home: int | None
    sets_guest: int | None
    legs_home: int | None
    legs_guest: int | None
    venue: Venue | None
    bye: bool = False
    swap_home_away: bool = False

    @property
    def finished(self) -> bool:
        return self.status == STATUS_FINISHED

    @property
    def score(self) -> str | None:
        if self.sets_home is None or self.sets_guest is None:
            return None
        return f"{self.sets_home}:{self.sets_guest}"

    @property
    def title(self) -> str:
        return f"{self.home_name} – {self.guest_name}"

    def involves(self, participant_id: int) -> bool:
        return participant_id in (self.home_id, self.guest_id)

    def is_home(self, participant_id: int) -> bool:
        return self.home_id == participant_id

    def opponent(self, participant_id: int) -> str:
        return self.guest_name if self.is_home(participant_id) else self.home_name

    def outcome(self, participant_id: int) -> str | None:
        """'sieg', 'niederlage' oder 'unentschieden' aus Sicht des Teams."""
        if not self.finished or self.score is None:
            return None
        own, other = (
            (self.sets_home, self.sets_guest)
            if self.is_home(participant_id)
            else (self.sets_guest, self.sets_home)
        )
        if own > other:
            return "sieg"
        if own < other:
            return "niederlage"
        return "unentschieden"

    def as_dict(self) -> dict[str, Any]:
        return {
            "spieltag": self.round_name,
            "termin": self.planned.isoformat() if self.planned else None,
            "heim": self.home_name,
            "gast": self.guest_name,
            "ergebnis": self.score,
            "legs": (
                f"{self.legs_home}:{self.legs_guest}"
                if self.legs_home is not None and self.legs_guest is not None
                else None
            ),
            "status": self.status,
            "spiellokal": self.venue.address if self.venue else None,
        }

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Match:
        home = data.get("participantHome") or {}
        guest = data.get("participantGuest") or {}
        home_season = home.get("teamSeason") or {}
        return cls(
            match_id=data["id"],
            round_name=(data.get("round") or {}).get("name", ""),
            planned=parse_datetime(data.get("datePlanned")),
            status=data.get("statusCd", ""),
            home_id=home.get("id"),
            home_name=home.get("displayName", ""),
            guest_id=guest.get("id"),
            guest_name=guest.get("displayName", ""),
            sets_home=data.get("setsHome"),
            sets_guest=data.get("setsAway"),
            legs_home=data.get("legsHome"),
            legs_guest=data.get("legsAway"),
            venue=Venue.from_api(home_season.get("playingVenue")),
            bye=bool(data.get("byeHome") or data.get("byeAway")),
            swap_home_away=bool(data.get("swapHomeAway")),
        )


@dataclass(slots=True)
class PlayerResult:
    placement: int
    name: str
    team: str
    matches: int
    won: int
    lost: int
    legs_won: int
    legs_lost: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "platz": self.placement,
            "spieler": self.name,
            "team": self.team,
            "spiele": self.matches,
            "siege": self.won,
            "niederlagen": self.lost,
            "legs": f"{self.legs_won}:{self.legs_lost}",
        }

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PlayerResult:
        total = data.get("totalResult") or {}
        return cls(
            placement=data.get("place", 0),
            name=data.get("displayName", ""),
            team=(data.get("team") or {}).get("name", ""),
            matches=total.get("matchCount", 0),
            won=total.get("matchWon", 0),
            lost=total.get("matchLost", 0),
            legs_won=total.get("legs1", 0),
            legs_lost=total.get("legs2", 0),
        )


@dataclass(slots=True)
class LeagueData:
    event_id: int
    event_name: str
    season_name: str
    region_name: str
    db_id: int | None = None
    table: list[TableRow] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)
    teams: dict[int, Team] = field(default_factory=dict)
    players: list[PlayerResult] = field(default_factory=list)

    def matches_for(self, participant_id: int | None) -> list[Match]:
        if participant_id is None:
            return self.matches
        return [m for m in self.matches if m.involves(participant_id)]

    def next_match(self, participant_id: int | None, now: datetime) -> Match | None:
        upcoming = [
            m
            for m in self.matches_for(participant_id)
            if not m.finished and not m.bye and m.planned and m.planned >= now
        ]
        return min(upcoming, key=lambda m: m.planned, default=None)

    def last_match(self, participant_id: int | None) -> Match | None:
        played = [
            m for m in self.matches_for(participant_id) if m.finished and m.planned
        ]
        return max(played, key=lambda m: m.planned, default=None)

    def table_row(self, participant_id: int) -> TableRow | None:
        return next((r for r in self.table if r.participant_id == participant_id), None)

    def team_name(self, participant_id: int) -> str | None:
        team = self.teams.get(participant_id)
        return team.name if team else None


def parse_table(data: dict[str, Any], phase_id: int | None = None) -> list[TableRow]:
    groups = data.get("tableEntries") or []
    group = next(
        (g for g in groups if phase_id is not None and g.get("phaseId") == phase_id),
        groups[0] if groups else None,
    )
    if not group:
        return []
    rows = group.get("tableEntries") or []
    return [TableRow.from_api(row, i) for i, row in enumerate(rows)]


def parse_matches(data: dict[str, Any]) -> list[Match]:
    matches = [Match.from_api(m) for m in data.get("matches") or [] if m.get("active", True)]
    return sorted(matches, key=lambda m: (m.planned is None, m.planned or datetime.min, m.match_id))


def parse_teams(data: list[dict[str, Any]]) -> dict[int, Team]:
    return {
        team.participant_id: team
        for team in (Team.from_participant(p) for p in data or [] if not p.get("retired"))
    }


def parse_players(data: dict[str, Any]) -> list[PlayerResult]:
    return [PlayerResult.from_api(p) for p in data.get("playerResults") or []]


def _num(value: float) -> float | int:
    return int(value) if float(value).is_integer() else value
