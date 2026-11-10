# Assault AirBike for Home Assistant (unofficial)

Live ride data from an **Assault AirBike** console in Home Assistant, over Bluetooth, with no phone app and no cloud.

> **Unofficial.** This project is not affiliated with, endorsed by or supported by Assault Fitness. "Assault AirBike" is used only to describe compatibility. The protocol was worked out by observing the console's own Bluetooth output.

## What you get

- **Live sensors** (updated every second while you ride): speed, cadence (rpm), power (W), ride distance, ride calories, elapsed time, time remaining (in timed programmes) and console state.
- **Last ride summary** (kept across restarts): end time, duration, distance, calories, average and max power, max speed and average cadence. Max values use a 4-second "held" maximum, which matches what the console shows as Max Values.
- **Lifetime totals** for distance and calories, for daily and weekly statistics charts.
- An **`assault_airbike_ride_finished` event** at the end of every ride, carrying all the summary figures, for your own automations (e.g. log a workout, send a notification).
- An **Auto-connect** switch: turn it off to free the bike for another app. The console accepts only one Bluetooth connection at a time.

## Requirements

- Home Assistant **2026.3** or newer.
- A Bluetooth adapter or **ESPHome Bluetooth proxy** within range of the bike, set up as an *active* (connectable) proxy.
- Tested on the **AirBike Elite** console in Manual and Time programmes. Other Assault consoles and programmes may work; please report your results (see below).

## Installation

### HACS (recommended)

1. In HACS, open the ⋮ menu → **Custom repositories**.
2. Add `https://github.com/roelofkl/ha-assault-airbike` with category **Integration**.
3. Install **Assault AirBike (unofficial)** and restart Home Assistant.

### Manual

Copy `custom_components/assault_airbike` into your Home Assistant `config/custom_components/` folder and restart.

## Setup

1. Press the **Bluetooth/Connect** button on the console so it starts advertising.
2. Home Assistant should discover **Assault AirBike** automatically (Settings → Devices & services). Otherwise add it manually and enter the bike's Bluetooth address.
3. From then on, Home Assistant connects whenever the bike advertises, which is each time you press the console's Bluetooth button.

## Entities

| Entity | Notes |
|---|---|
| Speed, Cadence, Power | Live, every second |
| Ride distance, Ride calories, Ride time | Live counters from the console |
| Time remaining | Only in timed programmes; unknown in Manual mode |
| State | `off`, `connected`, `ready`, `riding`, `finished` |
| Last ride (timestamp) + Last ride duration/distance/calories/average power/max power/max speed/average cadence | Summary of the most recent finished ride |
| Total distance, Total calories | `total_increasing`, for statistics |
| Connected (binary sensor) | Bluetooth connection status |
| Auto-connect (switch) | Off = leave the bike free for other apps |

## Ride-finished event

`assault_airbike_ride_finished` fires once per ride (at the console's "finished" state, a reset, or a disconnect mid-ride) with:
`start`, `end`, `duration_s`, `duration_min`, `distance_km`, `kcal`, `avg_power`, `max_power`, `avg_speed`, `max_speed`, `avg_cadence`, `max_cadence`, `mode`, `reason`.

Example: phone notification after rides of a minute or more:

```yaml
triggers:
  - trigger: event
    event_type: assault_airbike_ride_finished
conditions:
  - "{{ trigger.event.data.duration_s | int(0) >= 60 }}"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: AirBike ride
      message: >-
        {{ (trigger.event.data.duration_s / 60) | round(0) | int }} min,
        {{ trigger.event.data.kcal }} kcal, {{ trigger.event.data.distance_km }} km
```

## Apple Health (optional)

Home Assistant cannot write to Apple Health directly, but an iPhone Shortcut can copy the last ride across:

1. Add three Home Assistant **Render template** actions:
   - `{{ state_attr('sensor.airbike_last_ride','start') }}`
   - `{{ state_attr('sensor.airbike_last_ride','duration_s') }}`
   - `{{ state_attr('sensor.airbike_last_ride','kcal') }}`
2. Add **Log Workout** (type Cycling): Date = 1st result, Duration = 2nd result in **seconds**, Calories = 3rd result (kcal).
3. Set **Distance to 0**: Log Workout fails if it is empty, and it files distance as walking/running distance.

A notification can open the Shortcut with the URL `shortcuts://run-shortcut?name=AirBike%20to%20Health`.

## Notes and limitations

- **One connection at a time.** While Home Assistant is connected, other apps cannot connect, and vice versa.
- The console sends whole metres and whole calories, so figures can differ slightly from the decimals on the display.
- If Home Assistant connects partway through a ride, totals are complete but averages only cover the connected part.
- Protocol details are in [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Reporting other models and programmes

If your console or programme isn't decoded correctly, open an issue with your console model and a debug log captured during a short ride:

```yaml
logger:
  logs:
    custom_components.assault_airbike: debug
```

The debug log shows every Bluetooth message as `notify <characteristic> <hex>`.

## Licence

MIT. See [LICENSE](LICENSE).
