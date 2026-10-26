"""Asynchroner Client für die öffentliche 3K-Darts/DSAB-API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import API_BASE, DEFAULT_MANDANT_KEY

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "HomeAssistant-DSAB-Darts (+https://github.com/DHansel91/ha-dsab-darts)",
}


class DartsApiError(Exception):
    """Allgemeiner API-Fehler."""


class DartsApiConnectionError(DartsApiError):
    """Backend nicht erreichbar oder Zeitüberschreitung."""


class DartsApiClient:
    """Dünner Wrapper um die Frontend-Endpunkte des Portals."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        mandant_key: int = DEFAULT_MANDANT_KEY,
        base_url: str = API_BASE,
    ) -> None:
        self._session = session
        self._mandant_key = mandant_key
        self._base = base_url.rstrip("/")

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base}/{path.lstrip('/')}"
        _LOGGER.debug("GET %s %s", url, params)
        try:
            async with self._session.get(
                url, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS
            ) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise DartsApiError(
                        f"HTTP {resp.status} für {resp.url}: {body[:200]!r}"
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise DartsApiConnectionError(
                f"{url}: {type(err).__name__}: {err}"
            ) from err
        try:
            return json.loads(body) if body.strip() else None
        except ValueError as err:
            raise DartsApiError(
                f"Keine gültige JSON-Antwort von {url}: {body[:200]!r}"
            ) from err

    # --- Auswahllisten für den Config-Flow ---------------------------------

    async def regions(self) -> list[dict[str, Any]]:
        data = await self._get("region", {"mandantKey": self._mandant_key})
        return [r for r in data or [] if r.get("frontendShow", True)]

    async def seasons(self, region_id: int) -> list[dict[str, Any]]:
        return await self._get(
            "season", {"mandantKey": self._mandant_key, "regionId": region_id}
        ) or []

    async def events(self, region_id: int, season_id: int) -> list[dict[str, Any]]:
        return await self._get(
            "event",
            {
                "mandantKey": self._mandant_key,
                "regionId": region_id,
                "seasonId": season_id,
            },
        ) or []

    # --- Daten einer Liga ---------------------------------------------------

    async def event(self, event_id: int) -> dict[str, Any]:
        return await self._get(f"event/{event_id}") or {}

    async def participants(self, event_id: int) -> list[dict[str, Any]]:
        return await self._get(f"event/{event_id}/participant") or []

    async def table(self, event_id: int) -> dict[str, Any]:
        return await self._get(f"event/{event_id}/phase/0/round/0/table") or {}

    async def matches(self, event_id: int, phase_id: int) -> dict[str, Any]:
        """round/0 liefert alle Spiele der Phase über alle Spieltage."""
        return await self._get(f"event/{event_id}/phase/{phase_id}/round/0") or {}

    async def player_results(self, event_id: int) -> dict[str, Any]:
        return await self._get(f"event/{event_id}/player/results") or {}
