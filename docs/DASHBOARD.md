# Example dashboard

[`dashboard-view.yaml`](dashboard-view.yaml) is a ready-made **sections** view for the AirBike, designed to be read on a phone mounted on the bike.

**While riding**
- Time remaining (timed programmes) or time elapsed (Manual), and calories, as two large tiles.
- An RPM dial centred on a target cadence (52 rpm in the example): green within ±5 rpm, orange within ±15, red beyond that.
- Power and speed dials side by side, then time (m:ss) and distance (x.x km).
- Power, cadence and speed graphs for the last 30 minutes.

**When the bike isn't connected**
- The live tiles, dials and graphs are hidden, so no "unavailable" warnings are shown.
- A "Bike not connected — press the Bluetooth button" card with a one-line summary of the last ride.
- The Last ride section stays visible.

## Adding it

1. Open the dashboard you want it on → ✏️ **Edit** → ⋮ → **Raw configuration editor**.
2. Paste the contents of `dashboard-view.yaml` as a new item under `views:` (indent it to line up with your other views) and save.

The entity IDs assume the integration's device is named **AirBike** (the default). If you renamed it, search and replace `airbike_` with your prefix.

## Adjusting the cadence target

In the `RPM` gauge, change `min`/`max` and the `segments` `from` values. The example uses a 52 rpm target, so `min: 22`, `max: 82`, and colour bands starting at 22 (red), 37 (orange), 47 (green), 57 (orange) and 67 (red).

## Keeping the phone screen on

iOS and Android apps can't change the phone's auto-lock setting from a dashboard. The simplest option is to set Auto-Lock to Never during workouts. A dashboard card using the browser's Screen Wake Lock API can also work, but only when Home Assistant is opened over **https**.
