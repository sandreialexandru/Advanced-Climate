<img src="custom_components/advanced_climate/brand/icon@2x.png" alt="Advanced Climate" width="128" align="right">

# Advanced Climate

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/sandreialexandru/Advanced-Climate/actions/workflows/validate.yml/badge.svg)](https://github.com/sandreialexandru/Advanced-Climate/actions/workflows/validate.yml)
[![Tests](https://github.com/sandreialexandru/Advanced-Climate/actions/workflows/tests.yml/badge.svg)](https://github.com/sandreialexandru/Advanced-Climate/actions/workflows/tests.yml)

Heating schedules for Home Assistant that follow **presence, zones, windows,
weather and manual changes** – with one clear decision per room and the reason
for it.

Advanced Climate is built around **Generic Thermostat**: it uses the same preset
names (`home`, `sleep`, `eco`, `away`, `comfort`, `activity`) and only selects
the right one; your thermostat keeps working exactly as before. Rooms with TRVs,
other thermostats or plain relays are supported as well.

## Features

- **Presence in three states**: *home*, *nearby* (e.g. somewhere in your city)
  and *far*. Nearby zones are evaluated from coordinates too, so a zone such as
  "Office" inside the city counts as nearby and stale `not_home` states are
  corrected.
- **Schedules** with `workday` / `weekend` / weekday / custom profiles, holidays
  from the Workday integration, profiles chosen from a calendar, a day boundary
  for night shifts, or an existing Schedule helper.
- **Optimal start / stop** with a learned heating rate per room.
- **Windows**: open/close delays, frost protection or off, detection from a
  sudden temperature drop, windows of neighbouring rooms, alerts.
- **Weather**: outdoor cutoff with averaging and hysteresis, heating season
  (dates or automatic), outdoor compensation, forecast, solar gain per room.
- **Manual changes**: detected automatically and kept for a fixed time or until
  the next reevaluation (schedule, presence, window or mode change). Child lock,
  pause and per-room / global clear buttons.
- **Global modes**: Auto, Vacation (with dates, preheating before the return and
  automatic vacation), Off (frost protection) and Summer.
- **Energy**: dynamic tariff, PV surplus, boiler control from the heat demand
  of the rooms, runtime statistics.
- **Safety**: frost protection always, maximum temperature, command
  verification with retry, alerts for unavailable devices, failed sensors, low
  batteries and open windows, valve exercise for TRVs.
- **Visibility**: a *Decision* sensor per room with the winning rule and the
  reason, an event on every change, diagnostics with the last 100 decisions and
  a Lovelace card with an editable schedule.

The full specification is in [docs/SPEC.md](docs/SPEC.md).

## Installation

### HACS

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/sandreialexandru/Advanced-Climate` as **Integration**.
2. Install **Advanced Climate** and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Advanced Climate**.

### Manual

Copy `custom_components/advanced_climate` into your `config/custom_components`
folder and restart Home Assistant.

Requires Home Assistant **2025.7** or newer.

## Configuration

1. **Create the house**: name, people, nearby zones and the home rule, then the
   **heating of the whole house** (e.g. your Generic Thermostat). That is enough
   for a house heated by one thermostat: it becomes the zone *Whole house*
   and uses every option. It can be changed later in *Configure → Heating of the
   whole house*.
2. Optionally **add rooms** with *Add room* on the integration page, for rooms
   with their own valves or thermostats. Each room has its own devices,
   sensors, windows and schedule.
3. Everything else is in the integration **options** (presence, workdays and
   calendar, weather and season, energy, boiler, manual changes and vacation,
   alerts).

### Schedule format

One profile per line, each slot is `HH:MM preset`:

```
workday: 00:00 sleep, 06:00 home, 22:00 sleep
weekend: 00:00 sleep, 08:00 home, 23:00 sleep
```

Profiles are chosen in this order: the room *Profile* select (if not `auto`) →
a calendar event titled with a profile name → a weekday profile (`mon` … `sun`)
→ `workday` or `weekend` (holidays count as weekend). The schedule can also be
edited in the Lovelace card.

### How a room decides

Rules are evaluated from the top; the first one that applies wins:

1. Safety (frost protection, maximum temperature) – always applied
2. Mode Off / Pause / Summer / outside the heating season
3. Window open
4. Manual change
5. Vacation
6. Presence: far → `away`, nearby → `eco` (or a fixed temperature)
7. Schedule (optimal start / stop, room occupancy)

Then the adjustments (outdoor cutoff, compensation, tariff, PV, solar gain) and
the safety limits.

### Example: replacing four Scheduler schedules

| Before (Scheduler component) | Advanced Climate |
| --- | --- |
| *Someone home* (workdays) | Profile `workday` |
| *Weekend someone home* | Profile `weekend` |
| *No person home (in Bucharest)* | Presence *nearby* → `eco` (nearby zone *Bucharest*) |
| *Out of Bucharest (workday)* / *Weekend no person home* | Presence *far* → `away` |

Disable the old schedules (or the automations that set the same thermostat)
before enabling a room, otherwise both will change the thermostat; Advanced
Climate would see those changes as manual changes.

## Entities

House: *Mode* (select), *Presence* (home / nearby / far), *Pause* and *Guest
mode* (switches), *Vacation start / end* (datetime), *Heating season*, *Outdoor
cutoff* and *Heat demand* (binary sensors), *Outdoor average*, *Heating runtime*,
buttons to clear manual changes, clear the vacation and reevaluate.

Room: *Decision* (enum with the reason in the attributes), *Target temperature*,
*Room temperature*, *Next change*, *Heating rate*, *Heating runtime*, *Heat
demand*, *Window open*, *Manual change*, *Profile* (select), *Child lock*
(switch), *Clear manual change* (button) and, for rooms without Generic
Thermostat, the level temperatures (numbers).

## Services

| Service | Description |
| --- | --- |
| `advanced_climate.set_override` | Set a preset or a temperature as a manual change (optional duration) |
| `advanced_climate.clear_override` | Clear manual changes (one room or all) |
| `advanced_climate.set_vacation` | Set or clear the vacation period |
| `advanced_climate.reevaluate` | Evaluate everything now |
| `advanced_climate.set_schedule` | Replace the schedule of a room (text or profiles) |

Rooms are addressed by `room` (name or id) or by any of their entities.

The event `advanced_climate_decision_changed` is fired whenever a room changes
its decision (`room`, `old_rule`, `rule`, `old_target`, `target`, `reason`).

## Lovelace card

The integration adds the card to the dashboard resources automatically
(`/advanced_climate/advanced-climate-card.js?v=<version>`, updated on every
release, so browsers and the companion app load the new version). With
YAML-mode dashboards add that URL as a `module` resource yourself. The card has
a visual editor. With no options it shows every house and room with every control:

```yaml
type: custom:advanced-climate-card
```

| Option | Default | Shows |
| --- | --- | --- |
| `title` | Heating | Card title (empty string hides it) |
| `rooms` | all | List of room *Decision* sensors to show |
| `show_house` | `true` | Presence and people, outdoor temperature, season, heat demand, heating time, mode (Auto / Vacation / Off / Summer), Pause, Guests, vacation dates, reevaluate and clear all manual changes |
| `show_rooms` | `true` | The rooms |
| `show_timeline` | `true` | Chart of the last 24 hours and the next 12: room temperature, target (colored by level), planned levels and the periods when the room heated. Hover or touch to read the values |
| `show_quick_override` | `true` | Set a level or a temperature for a number of hours (empty = the configured rule) |
| `show_levels` | `true` | Level temperatures (rooms without Generic Thermostat, fixed *nearby* temperature) |
| `show_details` | `true` | Room and target temperature, heating rate, heating time, active adjustments, level temperatures |
| `show_schedule_editor` | `true` | Schedule profiles with an editor: drag the start times on the day bar (5-minute steps), copy a profile over another day |
| `collapsed` | `false` | Rooms start folded; tap the room name to open it |
| `compact` | `false` | One row per room (name, rule, now → target) and one for the house; tap a row to open it |

Every room also shows its decision, the reason, heating / window / manual change
badges, the *Profile* select, the *Child lock* switch and *Back to automatic*.


## Translations

English and Romanian.

## License

MIT
