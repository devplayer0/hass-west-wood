"""Live member-count sensors for West Wood Club."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CLUBS, DEVICE_NAME, DOMAIN
from .coordinator import WestWoodConfigEntry, WestWoodCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WestWoodConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one occupancy sensor per selected club."""
    coordinator = entry.runtime_data
    clubs: dict[str, str] = entry.data[CONF_CLUBS]
    async_add_entities(
        WestWoodOccupancySensor(coordinator, entry, int(club_id), name)
        for club_id, name in clubs.items()
    )


class WestWoodOccupancySensor(CoordinatorEntity[WestWoodCoordinator], SensorEntity):
    """Number of members currently checked in at a club."""

    _attr_has_entity_name = True
    _attr_icon = 'mdi:account-group'
    _attr_native_unit_of_measurement = 'members'
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: WestWoodCoordinator,
        entry: WestWoodConfigEntry,
        club_id: int,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._club_id = club_id
        # has_entity_name prepends the device name, so drop the duplicate prefix
        # the API includes (e.g. 'West Wood Club Dun Laoghaire' -> 'Dun Laoghaire').
        self._attr_name = name.removeprefix(f'{DEVICE_NAME} ') or name
        self._attr_unique_id = f'{entry.entry_id}_{club_id}'
        # All club sensors share one device so they group together in the UI.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEVICE_NAME,
            manufacturer='PerfectGym',
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get(self._club_id)

    @property
    def available(self) -> bool:
        return super().available and self._club_id in self.coordinator.data
