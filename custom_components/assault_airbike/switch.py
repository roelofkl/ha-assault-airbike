"""Auto-connect switch: turn off to free the bike for Run Fit (one connection at a time)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import AirBikeEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities([AutoConnect(entry.runtime_data, "auto_connect")])


class AutoConnect(AirBikeEntity, SwitchEntity, RestoreEntity):
    _attr_icon = "mdi:bluetooth-connect"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state == STATE_OFF:
            self.bike.auto_connect = False

    @property
    def is_on(self) -> bool:
        return self.bike.auto_connect

    async def async_turn_on(self, **kwargs) -> None:
        await self.bike.async_set_auto_connect(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.bike.async_set_auto_connect(False)
