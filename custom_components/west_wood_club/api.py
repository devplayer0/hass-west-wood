"""Thin async client for the West Wood Club (PerfectGym) API.

Authentication is a long-lived bearer token supplied by the user (see
``get-token.py`` in the repo root for how to obtain one). Only the
``Authorization`` header is required by the backend.
"""

from __future__ import annotations

import aiohttp

from .const import BASE_URL


class WestWoodApiError(Exception):
    """A request to the API failed."""


class WestWoodAuthError(WestWoodApiError):
    """The token was rejected (expired or revoked)."""


class WestWoodClient:
    """Minimal client wrapping the endpoints the integration needs."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._token = token

    async def _get(self, path: str, **params: str) -> list[dict]:
        """GET a wrapped endpoint and return its ``data`` list."""
        try:
            async with self._session.get(
                f'{BASE_URL}{path}',
                params=params,
                headers={
                    'Authorization': f'bearer {self._token}',
                    'Accept': 'application/json',
                },
            ) as resp:
                if resp.status in (401, 403):
                    raise WestWoodAuthError(f'token rejected (HTTP {resp.status})')
                resp.raise_for_status()
                payload = await resp.json()
        except aiohttp.ClientError as err:
            raise WestWoodApiError(str(err)) from err

        if payload.get('errors'):
            raise WestWoodApiError(str(payload['errors']))
        return payload.get('data') or []

    async def async_get_clubs(self) -> dict[int, str]:
        """Return ``{club_id: name}`` for every club in the tenant."""
        data = await self._get('/v1/Clubs/Clubs', timestamp='0')
        return {club['id']: club['name'] for club in data}

    async def async_get_member_counts(self) -> dict[int, int]:
        """Return ``{club_id: live_member_count}``."""
        data = await self._get('/v1/Clubs/WhoIsInCount')
        return {row['clubId']: row['count'] for row in data}
