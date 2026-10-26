"""Konstanten für die DSAB-Dartliga-Integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "dsab_darts"

API_BASE: Final = "https://backend-dsab.3k-darts.com/2k-backend-dsab/api/v1/frontend"
PORTAL_BASE: Final = "https://portal.3k-darts.com/frontend/events"
# Mandant "DSAB" – die Portal-URLs enthalten ihn nicht, die Listen-Endpunkte brauchen ihn.
DEFAULT_MANDANT_KEY: Final = 1758

CONF_MANDANT_KEY: Final = "mandant_key"
CONF_REGION_ID: Final = "region_id"
CONF_REGION_NAME: Final = "region_name"
CONF_SEASON_ID: Final = "season_id"
CONF_SEASON_NAME: Final = "season_name"
CONF_EVENT_ID: Final = "event_id"
CONF_EVENT_NAME: Final = "event_name"
CONF_PHASE_ID: Final = "phase_id"
CONF_TEAM_ID: Final = "team_id"
CONF_TEAM_NAME: Final = "team_name"
CONF_SCAN_INTERVAL: Final = "scan_interval"

NO_TEAM: Final = "none"

DEFAULT_SCAN_INTERVAL_MIN: Final = 30
MIN_SCAN_INTERVAL_MIN: Final = 5
# An Spieltagen (ab Anwurf bis 6 h danach) häufiger aktualisieren
MATCHDAY_SCAN_INTERVAL: Final = timedelta(minutes=5)
MATCHDAY_WINDOW: Final = timedelta(hours=6)

# Dauer eines Ligaspiels für den Kalender
MATCH_DURATION: Final = timedelta(hours=4)

TOP_PLAYERS: Final = 10
