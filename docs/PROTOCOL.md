# AirBike console Bluetooth protocol (as observed)

Observed on an **Assault AirBike Elite** console (advertised name `Assault AirBike <serial>`). The console uses a private GATT service family rather than the standard Fitness Machine (0x1826), Cycling Power (0x1818) or Cycling Speed and Cadence (0x1816) services.

All characteristic UUIDs follow the pattern `A026xxxx-0A7D-4AB3-97FA-F1500F9FEB8B`.

## Services

| Service | Characteristics |
|---|---|
| `A026EE01` | `E002` (write without response, notify), `E004` (notify) |
| `A026EE03` | `E00A` (write, notify) |
| `A026EE07` (advertised) | `E01F`, `E01E`, `E020`, `E01B`, `E01D`, `E033`, `E016`, `E024`, `E028` |
| `180F` Battery, `180A` Device Information | standard |

No writes are needed: enabling notifications is enough for the console to stream data. The integration subscribes, in order, to `E002`, `E004`, `E00A`, `E01F`, `E01E`, `E020`, `E01B`, `E01D`, `E024`, `E028`.

## `E01E`: state (1 byte)

| Value | Meaning |
|---|---|
| `01` | ready / reset |
| `0A` | riding |
| `80` | finished (results screen) |

## `E01B`: programme name (ASCII)

For example `Manual` or `TIME MODE`.

## `E01D`: live data (once per second)

All multi-byte values are little-endian.

### Manual mode (16 bytes, byte 0 = `0x73`)

| Bytes | Field | Unit |
|---|---|---|
| 0–1 | header `73 58` | |
| 2 | `0x12` | |
| 3–4 | elapsed time | s |
| 5–6 | speed | 0.01 km/h |
| 7–8 | cadence | 0.1 rpm |
| 9–11 | distance | m |
| 12–13 | calories | kcal |
| 14–15 | power | W |

### Programme mode (18 bytes, byte 0 = `0xF3`)

Bit 7 of byte 0 is set and a 2-byte **time remaining** field (seconds) is inserted after elapsed time. Every later field moves 2 bytes along:

| Bytes | Field |
|---|---|
| 3–4 | elapsed time (s) |
| 5–6 | time remaining (s) |
| 7–8 | speed (0.01 km/h) |
| 9–10 | cadence (0.1 rpm) |
| 11–13 | distance (m) |
| 14–15 | calories (kcal) |
| 16–17 | power (W) |

## Behaviour worth knowing

- After a ride ends (state `80`), the console **keeps repeating its final packet** every second. Don't treat these as a new ride.
- The console's "Max Values" match the highest value **held for 4 consecutive seconds**, not the single-second peak.
- Power and speed are stepped values derived from cadence (for example 76 rpm is always shown as 557 W and 46.8 km/h).
- The console accepts **one** Bluetooth connection at a time and stops advertising while connected.
