"""Base entity for Assault AirBike."""
from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity import Entity

from .bike import AirBike
from .const import DOMAIN


class AirBikeEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, bike: AirBike, key: str) -> None:
        self.bike = bike
        self._attr_unique_id = f"{bike.address}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, bike.address)},
            connections={(CONNECTION_BLUETOOTH, bike.address)},
            name="AirBike",
            manufacturer="Assault Fitness",
            model="AirBike Elite",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.bike.add_listener(self._on_update))

    def _on_update(self) -> None:
        self.async_write_ha_state()
