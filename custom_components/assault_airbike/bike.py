"""BLE connection and ride tracking for the Assault AirBike."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import timedelta
from functools import partial
from typing import Any

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import (
    CHAR_DATA,
    CHAR_MODE,
    CHAR_STATE,
    EVENT_RIDE_FINISHED,
    MAX_HOLD_SAMPLES,
    NOTIFY_CHARS,
    STATE_NAMES,
)

_LOGGER = logging.getLogger(__name__)
RETRY_SECONDS = 20


def _held_max(values: list[float], n: int = MAX_HOLD_SAMPLES) -> float:
    """Highest value sustained for n consecutive samples (console-style max)."""
    if not values:
        return 0
    if len(values) < n:
        return min(values)
    return max(min(values[i : i + n]) for i in range(len(values) - n + 1))


class AirBike:
    """One bike: keeps a BLE connection while auto-connect is on."""

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        self.hass = hass
        self.address = address.upper()
        self.name = name
        self.client: BleakClientWithServiceCache | None = None
        self.connected = False
        self.auto_connect = True
        self.state = "off"
        self.mode: str | None = None
        self.live: dict[str, Any] = self._zero_live()
        self.last_ride: dict[str, Any] = {}
        self.totals = {"distance_km": 0.0, "kcal": 0}
        self._listeners: set[Callable[[], None]] = set()
        self._lock = asyncio.Lock()
        self._last_attempt = 0.0
        self._unsub: CALLBACK_TYPE | None = None
        self._ride: dict[str, Any] | None = None
        self._prev_dist = 0
        self._prev_kcal = 0
        self._done_elapsed: int | None = None  # bike repeats its final packet after a ride
        self._code = 0

    @staticmethod
    def _zero_live() -> dict[str, Any]:
        return {"speed": 0.0, "cadence": 0.0, "power": 0, "distance": 0,
                "calories": 0, "elapsed": 0}

    # listeners -----------------------------------------------------------
    @callback
    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(cb)
        return lambda: self._listeners.discard(cb)

    @callback
    def _update(self) -> None:
        for cb in list(self._listeners):
            cb()

    # lifecycle -----------------------------------------------------------
    async def async_start(self) -> None:
        self._unsub = bluetooth.async_register_callback(
            self.hass,
            self._on_advert,
            bluetooth.BluetoothCallbackMatcher(address=self.address, connectable=True),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
        if bluetooth.async_address_present(self.hass, self.address, connectable=True):
            self.hass.async_create_background_task(self._connect(), "airbike_connect")

    async def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        await self.async_disconnect()

    async def async_disconnect(self) -> None:
        client = self.client
        if client:
            try:
                await client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self._handle_disconnect()

    async def async_set_auto_connect(self, on: bool) -> None:
        self.auto_connect = on
        if on:
            self._last_attempt = 0
            if bluetooth.async_address_present(self.hass, self.address, connectable=True):
                await self._connect()
        else:
            await self.async_disconnect()
        self._update()

    @callback
    def _on_advert(self, info: bluetooth.BluetoothServiceInfoBleak, change: Any) -> None:
        if (
            self.auto_connect
            and not self.connected
            and not self._lock.locked()
            and time.monotonic() - self._last_attempt > RETRY_SECONDS
        ):
            self.hass.async_create_background_task(self._connect(), "airbike_connect")

    async def _connect(self) -> None:
        async with self._lock:
            if self.connected or not self.auto_connect:
                return
            self._last_attempt = time.monotonic()
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if device is None:
                return
            try:
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    self.name,
                    disconnected_callback=self._on_disconnect,
                    max_attempts=3,
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("AirBike connect failed: %s", err)
                return
            self.client = client
            self.connected = True
            self.state = "connected"
            for uuid in NOTIFY_CHARS:
                try:
                    await client.start_notify(uuid, partial(self._on_notify, uuid))
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning("AirBike notify %s failed: %s", uuid[4:8], err)
            _LOGGER.info("AirBike connected via %s", getattr(device, "details", {}).get("source") if isinstance(getattr(device, "details", None), dict) else device)
            self._update()

    def _on_disconnect(self, _client: Any) -> None:
        self.hass.loop.call_soon_threadsafe(self._handle_disconnect)

    @callback
    def _handle_disconnect(self) -> None:
        if not self.connected and self.client is None:
            return
        self.client = None
        self.connected = False
        self._finish_ride("disconnected")
        self.state = "off"
        self.live = self._zero_live()
        _LOGGER.info("AirBike disconnected")
        self._update()

    # data ----------------------------------------------------------------
    def _on_notify(self, uuid: str, _char: Any, data: bytearray) -> None:
        _LOGGER.debug("notify %s %s", uuid[4:8], bytes(data).hex())
        if uuid == CHAR_STATE and data:
            code = data[0]
            self._code = code
            self.state = STATE_NAMES.get(code, f"0x{code:02x}")
            if code == 0x80:
                self._finish_ride("finished")
            elif code == 0x01 and self._ride and self._ride["elapsed"] > 0:
                self._finish_ride("reset")
        elif uuid == CHAR_MODE and data:
            self.mode = bytes(data).decode("ascii", "ignore").strip("\x00 ") or None
        elif (
            uuid == CHAR_DATA
            and len(data) >= 16
            and (data[0] & 0x7F) == 0x73
            and data[1] == 0x58
            and len(data) >= (18 if data[0] & 0x80 else 16)
        ):
            self._on_data(bytes(data))
        else:
            return
        self._update()

    def _on_data(self, b: bytes) -> None:
        le = lambda s: int.from_bytes(s, "little")  # noqa: E731
        elapsed = le(b[3:5])
        # programmes (e.g. TIME MODE) set bit 7 of byte 0 and insert a 2-byte
        # countdown (seconds remaining) after elapsed time
        o = 2 if b[0] & 0x80 else 0
        live = {
            "elapsed": elapsed,
            "remaining": le(b[5:7]) if o else None,
            "speed": le(b[5 + o : 7 + o]) / 100,
            "cadence": le(b[7 + o : 9 + o]) / 10,
            "distance": le(b[9 + o : 12 + o]),
            "calories": le(b[12 + o : 14 + o]),
            "power": le(b[14 + o : 16 + o]),
        }
        # running totals (counter restarts at 0 each ride)
        d, k = live["distance"], live["calories"]
        # only count increases; a drop means the console counter was reset
        self.totals["distance_km"] += max(d - self._prev_dist, 0) / 1000
        self.totals["kcal"] += max(k - self._prev_kcal, 0)
        self._prev_dist, self._prev_kcal = live["distance"], live["calories"]

        if self._ride and elapsed < self._ride["elapsed"]:
            self._finish_ride("reset")
        if elapsed == 0:
            self._done_elapsed = None
        elif self._ride is None and (self._code == 0x80 or elapsed == self._done_elapsed):
            pass  # finished ride being repeated by the console; not a new ride
        elif elapsed > 0:
            if self._ride is None:
                now = dt_util.now()
                self._ride = {"start": now - timedelta(seconds=elapsed), "elapsed": 0,
                              "speed": [], "cadence": [], "power": []}
            if elapsed != self._ride["elapsed"]:
                for k in ("speed", "cadence", "power"):
                    self._ride[k].append(live[k])
            self._ride.update(elapsed=elapsed, distance=live["distance"],
                              calories=live["calories"])
        self.live = live

    @callback
    def _finish_ride(self, reason: str) -> None:
        ride, self._ride = self._ride, None
        if not ride or ride["elapsed"] <= 0:
            return
        self._done_elapsed = ride["elapsed"]
        avg = lambda v: round(sum(v) / len(v), 1) if v else 0  # noqa: E731
        end = ride["start"] + timedelta(seconds=ride["elapsed"])
        self.last_ride = {
            "start": ride["start"].isoformat(timespec="seconds"),
            "end": end.isoformat(timespec="seconds"),
            "duration_s": ride["elapsed"],
            "duration_min": round(ride["elapsed"] / 60, 1),
            "distance_km": round(ride.get("distance", 0) / 1000, 2),
            "kcal": ride.get("calories", 0),
            "avg_power": avg(ride["power"]),
            "max_power": _held_max(ride["power"]),
            "avg_speed": avg(ride["speed"]),
            "max_speed": _held_max(ride["speed"]),
            "avg_cadence": avg(ride["cadence"]),
            "max_cadence": _held_max(ride["cadence"]),
            "mode": self.mode,
            "reason": reason,
        }
        _LOGGER.info("AirBike ride finished: %s", self.last_ride)
        self.hass.bus.async_fire(EVENT_RIDE_FINISHED, dict(self.last_ride))
