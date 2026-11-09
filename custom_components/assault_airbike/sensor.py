"""Sensors for Assault AirBike."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.util import dt as dt_util

from .bike import AirBike
from .entity import AirBikeEntity

M = SensorStateClass.MEASUREMENT


@dataclass(frozen=True, kw_only=True)
class BikeSensor(SensorEntityDescription):
    value: Callable[[AirBike], Any]


LIVE = [
    BikeSensor(key="speed", native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
               device_class=SensorDeviceClass.SPEED, state_class=M, suggested_display_precision=1,
               value=lambda b: b.live["speed"]),
    BikeSensor(key="cadence", native_unit_of_measurement="rpm", state_class=M,
               icon="mdi:rotate-right", suggested_display_precision=0,
               value=lambda b: b.live["cadence"]),
    BikeSensor(key="power", native_unit_of_measurement=UnitOfPower.WATT,
               device_class=SensorDeviceClass.POWER, state_class=M,
               value=lambda b: b.live["power"]),
    BikeSensor(key="ride_distance", native_unit_of_measurement=UnitOfLength.METERS,
               device_class=SensorDeviceClass.DISTANCE, value=lambda b: b.live["distance"]),
    BikeSensor(key="ride_calories", native_unit_of_measurement="kcal", icon="mdi:fire",
               value=lambda b: b.live["calories"]),
    BikeSensor(key="ride_time", native_unit_of_measurement=UnitOfTime.SECONDS,
               device_class=SensorDeviceClass.DURATION, value=lambda b: b.live["elapsed"]),
    BikeSensor(key="time_remaining", native_unit_of_measurement=UnitOfTime.SECONDS,
               device_class=SensorDeviceClass.DURATION, icon="mdi:timer-sand",
               value=lambda b: b.live.get("remaining")),
    BikeSensor(key="bike_state", icon="mdi:bike", value=lambda b: b.state),
]

LAST = [
    ("last_ride_end", dict(device_class=SensorDeviceClass.TIMESTAMP), "end"),
    ("last_ride_duration", dict(native_unit_of_measurement=UnitOfTime.MINUTES,
                                device_class=SensorDeviceClass.DURATION), "duration_min"),
    ("last_ride_distance", dict(native_unit_of_measurement=UnitOfLength.KILOMETERS,
                                device_class=SensorDeviceClass.DISTANCE,
                                suggested_display_precision=2), "distance_km"),
    ("last_ride_calories", dict(native_unit_of_measurement="kcal", icon="mdi:fire"), "kcal"),
    ("last_ride_avg_power", dict(native_unit_of_measurement=UnitOfPower.WATT,
                                 device_class=SensorDeviceClass.POWER), "avg_power"),
    ("last_ride_max_power", dict(native_unit_of_measurement=UnitOfPower.WATT,
                                 device_class=SensorDeviceClass.POWER), "max_power"),
    ("last_ride_max_speed", dict(native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
                                 device_class=SensorDeviceClass.SPEED), "max_speed"),
    ("last_ride_avg_cadence", dict(native_unit_of_measurement="rpm",
                                   icon="mdi:rotate-right"), "avg_cadence"),
]


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    bike: AirBike = entry.runtime_data
    ents: list[SensorEntity] = [LiveSensor(bike, d) for d in LIVE]
    ents += [LastRideSensor(bike, k, SensorEntityDescription(key=k, **kw), field)
             for k, kw, field in LAST]
    ents += [TotalSensor(bike, "total_distance", "distance_km", UnitOfLength.KILOMETERS,
                         SensorDeviceClass.DISTANCE),
             TotalSensor(bike, "total_calories", "kcal", "kcal", None)]
    async_add_entities(ents)


class LiveSensor(AirBikeEntity, SensorEntity):
    entity_description: BikeSensor

    def __init__(self, bike: AirBike, desc: BikeSensor) -> None:
        super().__init__(bike, desc.key)
        self.entity_description = desc

    @property
    def available(self) -> bool:
        return self.bike.connected or self.entity_description.key == "bike_state"

    @property
    def native_value(self):
        return self.entity_description.value(self.bike)


class LastRideSensor(AirBikeEntity, RestoreSensor):
    """Summary of the last finished ride; kept across restarts."""

    def __init__(self, bike: AirBike, key: str, desc: SensorEntityDescription, field: str):
        super().__init__(bike, key)
        self.entity_description = desc
        self._field = field
        self._value: Any = None
        self._ride_end: str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._value = last.native_value
        if (st := await self.async_get_last_state()) is not None:
            self._attr_extra_state_attributes = dict(st.attributes)

    def _on_update(self) -> None:
        r = self.bike.last_ride
        if not r or r.get("end") == self._ride_end:
            return
        self._ride_end = r.get("end")
        v = r.get(self._field)
        if self._field == "end" and v:
            v = dt_util.parse_datetime(v)
        self._value = v
        if self._field == "end":
            self._attr_extra_state_attributes = {k: v2 for k, v2 in r.items() if k != "end"}
        self.async_write_ha_state()

    @property
    def native_value(self):
        if self._field == "end" and isinstance(self._value, str):
            return dt_util.parse_datetime(self._value)
        return self._value


class TotalSensor(AirBikeEntity, RestoreSensor):
    """Lifetime totals (total_increasing) for daily/weekly statistics."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, bike, key, field, unit, device_class):
        super().__init__(bike, key)
        self._field = field
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_suggested_display_precision = 2 if field == "distance_km" else 0
        if field == "kcal":
            self._attr_icon = "mdi:fire"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None and last.native_value is not None:
            try:
                self.bike.totals[self._field] = max(
                    self.bike.totals[self._field], float(last.native_value)
                )
            except (TypeError, ValueError):
                pass

    @property
    def native_value(self):
        v = self.bike.totals[self._field]
        return round(v, 3) if self._field == "distance_km" else int(v)
