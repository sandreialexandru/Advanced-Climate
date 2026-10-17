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
- **Optimal start / stop** with a learned heating rate and a learned cooling per
  room (see *Heating rate learning* and *Cooling learning and optimal stop*).
  Once an optimal start begins it continues until the scheduled time, even if
  the room is warm early; the rules above the schedule can still override it.
- **Windows**: open/close delays, frost protection or off, detection from a
  sudden temperature drop, windows of neighbouring rooms, alerts.
- **Weather**: outdoor cutoff with averaging and hysteresis, heating season
  (dates or automatic), outdoor compensation, forecast, solar gain per room (needs the weather
  entity of the house; the setting is shown only when one is set).
- **Manual changes**: detected automatically and kept for a fixed time or until
  the next reevaluation (schedule, presence, window or mode change). A device
  that only reports, later, the values the integration sent it (e.g. a sleepy
  Zigbee TRV) is not a manual change. Child lock, pause and per-room / global
  clear buttons.
- **Global modes**: Auto, Vacation (with dates, preheating before the return and
  automatic vacation), Off (frost protection) and Summer. During the preheating
  hours before the end of a vacation the schedule applies even while everyone
  is still far away. Only an end date: the vacation starts now.
- **Energy**: dynamic tariff, PV surplus, boiler control from the heat demand
  of the rooms, runtime statistics.
- **Safety**: frost protection always (once it starts heating it continues
  until the device stops asking for heat), maximum temperature, command
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

1. **Create the house**: first the **temperature unit** (°C or °F), then the name, people, nearby zones and the home rule, then the
   **heating of the whole house** (e.g. your Generic Thermostat). That is enough
   for a house heated by one thermostat: it becomes the zone *Whole house*
   and uses every option. It can be changed later in *Configure → Heating of the
   whole house*.
2. Optionally **add rooms** with *Add room* on the integration page, for rooms
   with their own valves or thermostats. Each room has its own devices,
   sensors, windows and schedule. The zone *Whole house* is changed the same
   way (*⋮ → Reconfigure* on the integration page).
3. Everything else is in the integration **options** (presence, workdays and
   calendar, weather and season, energy, boiler, manual changes and vacation,
   alerts).

### Temperature unit

Each house has one temperature unit, °C or °F, for all its rooms. Every
temperature of the house is entered and shown in it: the settings, the level
temperatures, the sensors, the card and the `set_override` service. It is
chosen first when the house is created and changed with **Reconfigure** on the
integration page; the values are converted, nothing has to be entered again.
The integration keeps its values in °C and converts the readings and commands
of the thermostats and sensors from their own unit, so the unit of the house
does not have to match the one of Home Assistant.

Every form shows only what applies. The choices come first; a second form
then asks only for the values they need, and is skipped when nothing applies:

- **Heating**: the source, then its devices (and the command for other
  thermostats), then the command settings: hysteresis and minimum times for
  relays and on / off control (relays also need a room temperature sensor),
  the thermostat tolerance for temperature / preset commands, nothing for
  Generic Thermostat.
- **Rooms**: TRV calibration and valve exercise only for TRVs; the fixed
  *nearby* temperature only with that choice; aggregation only with several
  temperature sensors; occupancy time only with occupancy sensors; window
  delays only with window sensors or the temperature-drop detection; the
  Schedule helper fields only for a helper; optimal start / stop limits only
  when turned on.
- **Options**: preheat distances only with a Proximity / travel time sensor,
  cutoff / forecast / season / compensation values only for what is turned
  on, price and PV thresholds only with their sensors, boiler times only with
  a boiler, the fixed duration only for that kind of manual change.

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


## Entities

House: *Mode* (select), *Presence* (home / nearby / far), *Pause* and *Guest
mode* (switches), *Vacation start / end* (datetime), *Heating season*, *Outdoor
cutoff* and *Heat demand* (binary sensors), *Outdoor average*, *Heating runtime*,
buttons to clear manual changes, clear the vacation and reevaluate.

Room: *Decision* (enum with the reason in the attributes), *Target temperature*,
*Room temperature*, *Next change*, *Heating rate*, *Cooling rate*, *Heating runtime*, *Heat
demand*, *Window open*, *Manual change*, *Profile* (select), *Child lock*
(switch), *Clear manual change* (button) and, for rooms without Generic
Thermostat, the level temperatures (numbers).

## Heating rate learning

Each room learns how fast it heats up, in °C per hour, from its own heating
episodes.

- An **episode** starts when the room asks for heat at least the *tolerance*
  of its thermostat below the target, so the cycles that only keep the
  temperature are learned too. The tolerance is the *cold tolerance* of
  Generic Thermostat, the *hysteresis* for relays and on / off control, and the
  *Thermostat tolerance* room setting for other thermostats (default 0).
  The episode ends when the target is reached or the heating stops; it is used
  when the heat demand lasted at least 10 minutes and the temperature rose,
  however little: a slow rise is learned too (it may show a problem, but it is
  real).
- Episodes during which a **window or door sensor** of the room (or a linked
  one from another room) was open are not used. Rooms without window sensors
  use every episode.
- The last 30 episodes are kept with the average **outdoor temperature** of
  each. The rate is a straight line of the outdoor temperature, so every
  episode helps at every outdoor temperature and a temperature not seen yet is
  estimated from the trend. The learning is free: no minimum or maximum rate
  and no limit on how the rate changes with the outdoor temperature. Only
  where the line would reach zero the average of the episodes is used. With
  fewer than 3 episodes, or outdoor temperatures less than 3 °C apart, the
  average of the episodes is used.
- Until the first episode the rate is 1 °C/h.

The *Heating rate* sensor shows the rate for the current outdoor temperature;
its attributes show the estimate at −10 / 0 / 10 / 20 °C, the number of
episodes, the change per degree outdoors, how far below the target an episode
starts and the last episodes. Optimal start uses the same rate.

While a room is below its target the card shows the **time to the target**
(e.g. *~35 min*) under the target temperature, from the learned rate for the
current outdoor temperature; until the first episode it shows *learning…*.
The *Decision* sensor has it as the `time_to_target` attribute (minutes).

Version 1.7 discards the learning data of older versions, which also learned
the small thermostat cycles.

## Cooling learning and optimal stop

The cooling is learned the opposite way of the heating, per room:

- An **episode** starts when the heat demand stops (no window or door sensor
  open) and ends when the heat demand starts again. It is used when it lasted
  at least 10 minutes and the temperature fell, however little. Episodes with
  an open window sensor are not used.
- A room cools in proportion to the **difference between inside and
  outside**, so one coefficient per room is learned (the mean of the last 30
  episodes). Walls, radiators and insulation are not modelled: whatever they
  do is in the measured coefficient of that house.

**Optimal stop** lowers the level before the next colder one as early as the
room can cool and still stay in the comfort of the current level at the
scheduled time. The comfort is the *tolerance*: the *cold tolerance* of Generic
Thermostat, the *hysteresis* for relays and on / off control, and the
*Optimal stop tolerance* room setting for other thermostats (default 0).
Example: home 22 °C until 22:00, tolerance 0.5 °C, 7 °C outside: if the room
falls from 22 to 21.5 °C in 40 minutes, sleep starts at 21:20.

- The *Maximum early stop* room setting is the limit; until the first cooling
  episode the lower level starts that early.
- Once an optimal stop begins it continues until the scheduled time; the rules
  above the schedule can still override it. If the room falls below the
  comfort of the current level before that time (it cooled faster than
  learned), the optimal stop is cancelled: the current level stays until the
  scheduled time and the stop does not start again for that change. If this
  happens often, lower the *Maximum early stop*.
- The card shows the expected temperature at the change (e.g. *~21.5° at
  22:00*); the *Decision* sensor has it as the `stop_forecast` attribute.
- The *Cooling rate* sensor shows how fast the room falls now without heating;
  its attributes show the coefficient, the episodes and the tolerance.

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
| `show_timeline` | `true` | Chart of the last 24 hours and the next 12: room temperature, target (colored by level), planned levels and the periods when the room heated. Hover or touch to read the values. Zoom with the buttons (1h, 6h, −, +), double-click, pinch or Ctrl + wheel down to 20 minutes; drag to move in time |
| `show_quick_override` | `true` | Set a level or a temperature for a number of hours (empty = the configured rule) |
| `show_levels` | `true` | Level temperatures (rooms without Generic Thermostat, fixed *nearby* temperature) |
| `show_details` | `true` | Room and target temperature, heating rate, heating time, active adjustments, level temperatures |
| `show_schedule_editor` | `true` | Schedule profiles with an editor: drag the start times on the day bar (5-minute steps), copy a profile over another day |
| `collapsed` | `false` | Rooms start folded; tap the room name to open it |
| `compact` | `false` | One row per room (name, rule, now → target) and one for the house; tap a row to open it |
| `runtime_period` | `day` | Heating time shown for `day`, `week` or `month` (calendar periods, from the long-term statistics; tap the value in the card to change it). The *Heating runtime* sensors stay cumulative totals |

Every room also shows its decision, the reason, heating / window / manual change
badges, the *Profile* select, the *Child lock* switch and *Back to automatic*.


## Translations

English and Romanian.

## License

MIT
