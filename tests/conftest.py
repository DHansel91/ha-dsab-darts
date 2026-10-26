"""Gemeinsame Fixtures: echte API-Antworten aus einer HAR-Aufzeichnung."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

EVENT_ID = 40672
PHASE_ID = 4375
REGION_ID = 119
SEASON_ID = 73
TEAM_MEXIKANER = 704330


def load(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def matches_payload() -> dict[str, Any]:
    """Spieltag 3 (beendet) aus der Aufzeichnung + künstlicher offener Spieltag 4."""
    data = load("matches")
    finished = data["matches"]
    upcoming = []
    pairings = [(704328, "Sportfreunde Eslarn V", 704329, "DC Nabburg"),
                (704332, "DC Lucky Punch", 704331, "Putta Boy's"),
                (704327, "Don Promillo´s IV e.V.", TEAM_MEXIKANER, "DC Mexikaner")]
    for i, (hid, hname, gid, gname) in enumerate(pairings):
        m = copy.deepcopy(finished[0])
        m["id"] = 6686203 + i
        m["round"] = {**m["round"], "id": 86937, "name": "Spieltag 4", "index": 3}
        m["statusCd"] = "OPEN"
        m["datePlanned"] = "2026-11-07T19:00:00.000+0000"
        for key in ("setsHome", "setsAway", "legsHome", "legsAway", "endDate", "approveStatusCd"):
            m.pop(key, None)
        m["participantHome"] = {"id": hid, "displayName": hname, "rankingPos": 1}
        m["participantGuest"] = {"id": gid, "displayName": gname, "rankingPos": 2}
        upcoming.append(m)
    return {"matches": finished + upcoming}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
