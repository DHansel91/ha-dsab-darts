"""Config-Flow und Entities mit gemockter API."""

from __future__ import annotations

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.dsab_darts.const import (
    API_BASE,
    CONF_EVENT_ID,
    CONF_EVENT_NAME,
    CONF_MANDANT_KEY,
    CONF_PHASE_ID,
    CONF_REGION_ID,
    CONF_REGION_NAME,
    CONF_SEASON_ID,
    CONF_SEASON_NAME,
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    DOMAIN,
    NO_TEAM,
)

from .conftest import (
    EVENT_ID,
    PHASE_ID,
    REGION_ID,
    SEASON_ID,
    TEAM_MEXIKANER,
    load,
    matches_payload,
)


def mock_api(aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{API_BASE}/region", params={"mandantKey": 1758}, json=load("regions"))
    aioclient_mock.get(
        f"{API_BASE}/season",
        params={"mandantKey": 1758, "regionId": REGION_ID},
        json=load("seasons"),
    )
    aioclient_mock.get(
        f"{API_BASE}/event",
        params={"mandantKey": 1758, "regionId": REGION_ID, "seasonId": SEASON_ID},
        json=load("events"),
    )
    aioclient_mock.get(f"{API_BASE}/event/{EVENT_ID}", json=load("event"))
    aioclient_mock.get(f"{API_BASE}/event/{EVENT_ID}/participant", json=load("participants"))
    aioclient_mock.get(
        f"{API_BASE}/event/{EVENT_ID}/phase/0/round/0/table", json=load("table")
    )
    aioclient_mock.get(
        f"{API_BASE}/event/{EVENT_ID}/phase/{PHASE_ID}/round/0", json=matches_payload()
    )
    aioclient_mock.get(
        f"{API_BASE}/event/{EVENT_ID}/player/results", json=load("player_results")
    )


async def test_config_flow(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    mock_api(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REGION_ID: str(REGION_ID)}
    )
    assert result["step_id"] == "season"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SEASON_ID: str(SEASON_ID)}
    )
    assert result["step_id"] == "event"

    # nur eine Phase -> Phasen-Schritt wird übersprungen
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EVENT_ID: str(EVENT_ID)}
    )
    assert result["step_id"] == "team"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TEAM_ID: str(TEAM_MEXIKANER)}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "DC Mexikaner – BZ 01 (2026 - 2. Halbjahr)"
    assert result["data"][CONF_PHASE_ID] == PHASE_ID
    assert result["data"][CONF_REGION_NAME] == "Dartliga Nordoberpfalz"


def _entry(team: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="DC Mexikaner – BZ 01",
        unique_id=f"{EVENT_ID}_{PHASE_ID}_{team}",
        data={
            CONF_MANDANT_KEY: 1758,
            CONF_REGION_ID: REGION_ID,
            CONF_REGION_NAME: "Dartliga Nordoberpfalz",
            CONF_SEASON_ID: SEASON_ID,
            CONF_SEASON_NAME: "2026 - 2. Halbjahr",
            CONF_EVENT_ID: EVENT_ID,
            CONF_EVENT_NAME: "BZ 01",
            CONF_PHASE_ID: PHASE_ID,
            CONF_TEAM_ID: team,
            CONF_TEAM_NAME: None,
        },
    )


@pytest.mark.freeze_time("2026-10-26 12:00:00+00:00")
async def test_team_entities(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    mock_api(aioclient_mock)
    entry = _entry(str(TEAM_MEXIKANER))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Entity-IDs entstehen aus den (im Test englischen) Übersetzungen
    states = {s.entity_id: s for s in hass.states.async_all()}
    by_suffix = lambda suffix: next(s for eid, s in states.items() if eid.endswith(suffix))

    placement = by_suffix("_placement")
    assert placement.state == "1"
    assert placement.attributes["punkte"] == 7

    nxt = by_suffix("_next_match")
    assert nxt.state == "2026-11-07T19:00:00+00:00"
    assert nxt.attributes["gegner"] == "Don Promillo´s IV e.V."
    assert nxt.attributes["heimspiel"] is False
    # Spiellokal aus Teamdaten ergänzt (Heimteam Don Promillo´s)
    assert "Rothenstadt" in nxt.attributes["spiellokal"]

    last = by_suffix("_last_result")
    assert last.state == "11:9"
    assert last.attributes["ausgang"] == "sieg"

    leader = by_suffix("_league_leader")
    assert leader.state == "DC Mexikaner"
    assert len(leader.attributes["tabelle"]) == 6

    calendar = by_suffix("_matches")
    assert calendar.state == "off"
    assert calendar.attributes["message"].startswith("Don Promillo´s IV e.V. – DC Mexikaner")

    players = by_suffix("_player_statistics")
    assert int(players.state) > 0


async def test_league_only_has_no_team_sensors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    mock_api(aioclient_mock)
    entry = _entry(NO_TEAM)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ids = [s.entity_id for s in hass.states.async_all()]
    assert not any(i.endswith("_placement") for i in ids)
    assert any(i.endswith("_league_leader") for i in ids)
