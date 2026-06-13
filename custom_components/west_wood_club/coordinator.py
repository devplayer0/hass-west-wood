"""Data update coordinator for West Wood Club occupancy."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WestWoodApiError, WestWoodAuthError, WestWoodClient
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type WestWoodConfigEntry = ConfigEntry[WestWoodCoordinator]


class WestWoodCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Polls live member counts for all clubs in one request."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: WestWoodConfigEntry,
        client: WestWoodClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, int]:
        try:
            return await self.client.async_get_member_counts()
        except WestWoodAuthError as err:
            # Triggers Home Assistant's reauth flow to paste a fresh token.
            raise ConfigEntryAuthFailed(str(err)) from err
        except WestWoodApiError as err:
            raise UpdateFailed(str(err)) from err
