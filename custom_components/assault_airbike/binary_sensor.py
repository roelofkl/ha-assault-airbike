"""Connection sensor for Assault AirBike."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .entity import AirBikeEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities([Connected(entry.runtime_data, "connected")])


class Connected(AirBikeEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool:
        return self.bike.connected
