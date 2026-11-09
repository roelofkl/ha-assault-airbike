"""Assault AirBike: live ride data over Bluetooth (via HA Bluetooth / ESPHome proxies)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .bike import AirBike

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    bike = AirBike(hass, entry.data[CONF_ADDRESS], entry.title)
    entry.runtime_data = bike
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # entities (incl. the auto-connect switch) restore first, then connect
    await bike.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.async_stop()
    return ok
