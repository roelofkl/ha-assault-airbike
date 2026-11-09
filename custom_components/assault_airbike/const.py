"""Constants for the Assault AirBike integration (Wahoo-style private BLE protocol)."""

DOMAIN = "assault_airbike"
DEFAULT_ADDRESS = "EA:D8:3E:D7:B2:91"
EVENT_RIDE_FINISHED = "assault_airbike_ride_finished"


def _u(short: str) -> str:
    return f"a026{short.lower()}-0a7d-4ab3-97fa-f1500f9feb8b"


CHAR_DATA = _u("e01d")    # 16-byte live data
CHAR_STATE = _u("e01e")   # 1 byte: 01 ready, 0a riding, 80 finished
CHAR_MODE = _u("e01b")    # ASCII programme name, e.g. "Manual"

# Same subscription order nRF Connect used in the working test.
NOTIFY_CHARS = [
    _u("e002"), _u("e004"), _u("e00a"), _u("e01f"), CHAR_STATE,
    _u("e020"), CHAR_MODE, CHAR_DATA, _u("e024"), _u("e028"),
]

STATE_NAMES = {0x01: "ready", 0x0A: "riding", 0x80: "finished"}

# Console "max" values ignore short spikes; a value held for 4 s matches it.
MAX_HOLD_SAMPLES = 4
