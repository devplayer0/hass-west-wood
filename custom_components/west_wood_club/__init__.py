"""The West Wood Club integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WestWoodClient
from .const import CONF_TOKEN
from .coordinator import WestWoodConfigEntry, WestWoodCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: WestWoodConfigEntry) -> bool:
    """Set up West Wood Club from a config entry."""
    client = WestWoodClient(async_get_clientsession(hass), entry.data[CONF_TOKEN])
    coordinator = WestWoodCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WestWoodConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
