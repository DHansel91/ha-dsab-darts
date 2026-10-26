"""Parser-Tests gegen echte API-Antworten."""

from __future__ import annotations

from datetime import datetime, timezone

from custom_components.dsab_darts.models import (
    LeagueData,
    parse_datetime,
    parse_matches,
    parse_players,
    parse_table,
    parse_teams,
)

from .conftest import PHASE_ID, TEAM_MEXIKANER, load, matches_payload

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def _league() -> LeagueData:
    return LeagueData(
        event_id=40672,
        event_name="BZ 01",
        season_name="2026 - 2. Halbjahr",
        region_name="Dartliga Nordoberpfalz",
        table=parse_table(load("table"), PHASE_ID),
        matches=parse_matches(matches_payload()),
        teams=parse_teams(load("participants")),
        players=parse_players(load("player_results")),
    )


def test_parse_datetime() -> None:
    dt = parse_datetime("2026-10-24T18:00:00.000+0000")
    assert dt == datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc)
    assert parse_datetime(None) is None
    assert parse_datetime("kaputt") is None


def test_table() -> None:
    table = parse_table(load("table"), PHASE_ID)
    assert [r.name for r in table][:2] == ["DC Mexikaner", "Don Promillo´s IV e.V."]
    first = table[0]
    assert first.placement == 1
    assert (first.won, first.tied, first.lost) == (2, 0, 1)
    assert first.points == 7.0
    assert first.as_dict()["sets"] == "36:25"
    assert first.sets_diff == 11
    assert table[-1].placement == 6


def test_teams_have_venue() -> None:
    teams = parse_teams(load("participants"))
    assert len(teams) == 6
    mex = teams[TEAM_MEXIKANER]
    assert mex.venue.city == "Pfreimd"
    assert mex.throwoff_time == "20:00:00"
    assert "Stadtgraben 15" in mex.venue.address


def test_matches_and_results() -> None:
    league = _league()
    assert len(league.matches) == 6

    last = league.last_match(TEAM_MEXIKANER)
    assert last.round_name == "Spieltag 3"
    assert last.opponent(TEAM_MEXIKANER) == "Putta Boy's"
    assert last.score == "11:9"
    assert last.outcome(TEAM_MEXIKANER) == "sieg"
    assert last.outcome(704331) == "niederlage"


def test_next_match() -> None:
    league = _league()
    nxt = league.next_match(TEAM_MEXIKANER, NOW)
    assert nxt.round_name == "Spieltag 4"
    assert not nxt.is_home(TEAM_MEXIKANER)
    assert nxt.opponent(TEAM_MEXIKANER) == "Don Promillo´s IV e.V."
    assert nxt.score is None
    # nach dem Termin gibt es kein nächstes Spiel mehr
    assert league.next_match(TEAM_MEXIKANER, datetime(2027, 1, 1, tzinfo=timezone.utc)) is None


def test_players() -> None:
    players = parse_players(load("player_results"))
    assert players[0].name == "Patrick Spindler"
    assert players[0].team == "Putta Boy's"
    assert players[0].won == 16
