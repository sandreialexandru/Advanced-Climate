/*
 * Advanced Climate card – every option of the integration in one card.
 *
 *   type: custom:advanced-climate-card
 *   title: Heating               # optional
 *   rooms:                       # optional: decision sensors to show (default: all)
 *     - sensor.living_decision
 *   show_house: true             # house: presence, mode, pause, guests, vacation, stats
 *   show_rooms: true
 *   show_timeline: true          # today's schedule as a temperature profile
 *   show_quick_override: true    # set a level / temperature for a while
 *   show_levels: true            # level temperatures (rooms without Generic Thermostat)
 *   show_details: true           # temperatures, heating rate, runtime, adjustments
 *   show_schedule_editor: true
 *   collapsed: false             # rooms start folded (header only)
 */

const CARD_VERSION = "1.4.1";

const PRESET_COLORS = {
  comfort: "#d9480f",
  home: "#f08c00",
  activity: "#e0a030",
  eco: "#2f9e8f",
  sleep: "#5f6fd1",
  away: "#8a96a3",
};

const WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

const DEFAULTS = {
  show_house: true,
  show_rooms: true,
  show_timeline: true,
  show_quick_override: true,
  show_levels: true,
  show_details: true,
  show_schedule_editor: true,
  collapsed: false,
};

const TEXT = {
  en: {
    title: "Heating",
    now_tag: "Now",
    target_tag: "Target",
    arriving: "On the way home",
    vacation_none: "not planned",
    vacation_hint: "During the vacation every room uses away. Heating starts again a few hours before the end.",
    today: "Today",
    quick_hint: "Keeps a level or a temperature as a manual change. Empty duration = the rule from the options.",
    days_workday: "Monday–Friday, except holidays",
    days_weekend: "Saturday, Sunday and holidays",
    days_weekday: "Every {day}",
    days_custom: "Chosen manually or by a calendar event",
    schedule_help: "Each time starts a level that lasts until the next time; the last one lasts until the first time of the next day. The schedule is used while someone is home; windows, manual changes, vacation, presence (nearby = eco, far = away) and the house mode come first.",
    schedule_active: "The schedule decides right now.",
    schedule_not_active: "Right now {rule} decides; the schedule applies again when that ends.",
    next_day: "next day",
    starts: "From",
    ends: "Until",
    level: "Level",
    remove_profile: "Delete profile",
    presence: "Presence",
    outdoor: "Outdoor",
    season: "Heating season",
    cutoff: "Warm outside",
    demand: "Heat demand",
    runtime: "Heating time",
    mode: "Mode",
    pause: "Pause",
    guests: "Guests",
    vacation: "Vacation",
    from: "From",
    to: "To",
    set_vacation: "Save vacation",
    clear_vacation: "Clear vacation",
    reevaluate: "Reevaluate now",
    clear_all: "Clear all manual changes",
    profile: "Profile",
    child_lock: "Child lock",
    next: "Next",
    quick: "Set for a while",
    for_hours: "for",
    hours: "h",
    apply: "Set",
    clear_override: "Back to automatic",
    override: "Manual change",
    until: "until",
    until_change: "until the next change",
    window: "Window open",
    heating: "Heating",
    details: "Details",
    levels: "Level temperatures",
    schedule: "Schedule",
    edit: "Edit schedule",
    save: "Save schedule",
    cancel: "Cancel",
    add_slot: "Add time",
    add_profile: "Add profile",
    profile_name: "New profile name",
    remove: "Remove",
    room_temp: "Room temperature",
    target: "Target",
    rate: "Heating rate",
    adjustments: "Adjustments",
    none: "none",
    not_editable: "This room follows a Schedule helper; edit the helper instead.",
    no_rooms: "No heating devices yet. Add them in Settings → Devices & services → Advanced Climate → Configure → Heating of the whole house (or add rooms).",
    error: "Could not save",
    persons: "People",
    on: "On",
    off: "Off",
    level_temps_gt: "Preset temperatures (set in Generic Thermostat)",
    from_device: "thermostat",
    device_preset: "Thermostat preset now",
    no_preset: "none (manual temperature)",
    active: "active",
  },
  ro: {
    title: "Încălzire",
    now_tag: "Acum",
    target_tag: "Țintă",
    arriving: "Pe drum spre casă",
    vacation_none: "neplanificată",
    vacation_hint: "În vacanță toate zonele folosesc away. Încălzirea repornește cu câteva ore înainte de sfârșit.",
    today: "Azi",
    quick_hint: "Păstrează un nivel sau o temperatură ca modificare manuală. Durată goală = regula din opțiuni.",
    days_workday: "Luni–vineri, fără sărbători",
    days_weekend: "Sâmbătă, duminică și sărbători",
    days_weekday: "În fiecare {day}",
    days_custom: "Ales manual sau dintr-un eveniment din calendar",
    schedule_help: "Fiecare oră pornește un nivel care ține până la ora următoare; ultimul ține până la prima oră din ziua următoare. Programul se folosește cât timp e cineva acasă; ferestrele, modificările manuale, vacanța, prezența (aproape = eco, departe = away) și modul casei au prioritate.",
    schedule_active: "Acum decide programul.",
    schedule_not_active: "Acum decide {rule}; programul se aplică din nou după ce se termină.",
    next_day: "a doua zi",
    starts: "De la",
    ends: "Până la",
    level: "Nivel",
    remove_profile: "Șterge profilul",
    presence: "Prezență",
    outdoor: "Exterior",
    season: "Sezon de încălzire",
    cutoff: "Cald afară",
    demand: "Cerere de căldură",
    runtime: "Timp de încălzire",
    mode: "Mod",
    pause: "Pauză",
    guests: "Oaspeți",
    vacation: "Vacanță",
    from: "De la",
    to: "Până la",
    set_vacation: "Salvează vacanța",
    clear_vacation: "Șterge vacanța",
    reevaluate: "Reevaluează acum",
    clear_all: "Anulează toate modificările manuale",
    profile: "Profil",
    child_lock: "Blocare modificări",
    next: "Următor",
    quick: "Setează temporar",
    for_hours: "pentru",
    hours: "h",
    apply: "Setează",
    clear_override: "Înapoi la automat",
    override: "Modificare manuală",
    until: "până la",
    until_change: "până la următoarea schimbare",
    window: "Fereastră deschisă",
    heating: "Încălzește",
    details: "Detalii",
    levels: "Temperaturile nivelurilor",
    schedule: "Program",
    edit: "Editează programul",
    save: "Salvează programul",
    cancel: "Renunță",
    add_slot: "Adaugă oră",
    add_profile: "Adaugă profil",
    profile_name: "Numele profilului nou",
    remove: "Șterge",
    room_temp: "Temperatura camerei",
    target: "Țintă",
    rate: "Viteză de încălzire",
    adjustments: "Ajustări",
    none: "niciuna",
    not_editable: "Camera urmează un helper de program; editează helperul.",
    no_rooms: "Încă nu sunt dispozitive de încălzire. Adaugă-le din Setări → Dispozitive și servicii → Advanced Climate → Configurează → Încălzirea întregii case (sau adaugă camere).",
    error: "Nu s-a putut salva",
    persons: "Persoane",
    on: "Pornit",
    off: "Oprit",
    level_temps_gt: "Temperaturile preseturilor (setate în Generic Thermostat)",
    from_device: "din termostat",
    device_preset: "Preset în termostat acum",
    no_preset: "niciunul (temperatură manuală)",
    active: "activ",
  },
};

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

const toMinutes = (hhmm) => {
  const [h, m] = String(hhmm).split(":").map((x) => parseInt(x, 10));
  return (h || 0) * 60 + (m || 0);
};

const hhmm = (minutes) =>
  `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;

const num = (value) => {
  const n = parseFloat(value);
  return Number.isFinite(n) ? n : null;
};

/** ISO datetime -> value for <input type="datetime-local"> in local time. */
const toLocalInput = (iso) => {
  if (!iso || iso === "unknown" || iso === "unavailable") return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
};

/** <input type="datetime-local"> value -> "YYYY-MM-DD HH:MM:SS" in local time. */
const fromLocalInput = (value) => (value ? `${value.replace("T", " ")}:00` : null);

class AdvancedClimateCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._editing = null;
    this._draft = null;
    this._open = {};
    this._lastKey = "";
    this._error = {};
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("change", (ev) => this._onChange(ev));
    this.shadowRoot.addEventListener("toggle", (ev) => this._onToggle(ev), true);
  }

  static getConfigForm() {
    const lang = (document.querySelector("home-assistant")?.hass?.locale?.language || navigator.language || "en").slice(0, 2);
    const labels = EDITOR_LABELS[lang] || EDITOR_LABELS.en;
    return {
      schema: EDITOR_SCHEMA,
      computeLabel: (schema) => labels[schema.name] || schema.name,
    };
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    if (config === null || typeof config !== "object" || Array.isArray(config)) {
      throw new Error("Invalid configuration");
    }
    if (config.rooms !== undefined && !Array.isArray(config.rooms)) {
      throw new Error("'rooms' must be a list of Decision sensors");
    }
    const merged = { ...DEFAULTS, ...(config || {}) };
    if (config && config.show_editor === false) merged.show_schedule_editor = false;
    if (config && config.entity && !config.rooms) merged.rooms = [config.entity];
    this._config = merged;
    this._lastKey = "";
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this.style.colorScheme = hass?.themes?.darkMode ? "dark" : "light";
    if (this._editing) return;
    const active = this.shadowRoot.activeElement;
    if (active && ["INPUT", "SELECT"].includes(active.tagName)) return;
    const key = this._watched()
      .map((id) => {
        const s = hass.states[id];
        return s ? `${id}:${s.state}:${s.last_updated}` : id;
      })
      .join("|");
    if (key !== this._lastKey) {
      this._lastKey = key;
      this._render();
    }
  }

  getCardSize() {
    return 4 + this._rooms().length * 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  // ------------------------------------------------------------------ data
  _t(key) {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").slice(0, 2);
    return (TEXT[lang] || TEXT.en)[key] ?? TEXT.en[key] ?? key;
  }

  _lang() {
    return this._hass?.locale?.language || "en";
  }

  _rooms() {
    if (!this._hass) return [];
    const all = Object.values(this._hass.states).filter(
      (s) => s.attributes && s.attributes.room_id && s.attributes.entry_id && s.attributes.schedule
    );
    const wanted = this._config?.rooms;
    if (Array.isArray(wanted) && wanted.length) {
      return wanted.map((id) => this._hass.states[id]).filter(Boolean);
    }
    return all.sort((a, b) =>
      String(a.attributes.room_name).localeCompare(String(b.attributes.room_name))
    );
  }

  _houses() {
    const houses = new Map();
    const filtered = Array.isArray(this._config?.rooms) && this._config.rooms.length;
    for (const s of Object.values(this._hass.states)) {
      const a = s.attributes || {};
      if (!a.advanced_climate_house || !a.entry_id) continue;
      houses.set(a.entry_id, {
        id: a.entry_id,
        name: a.house_name,
        entities: a.house_entities || {},
        rooms: [],
        standalone: true,
      });
    }
    for (const room of this._rooms()) {
      const a = room.attributes;
      if (!houses.has(a.entry_id)) {
        houses.set(a.entry_id, {
          id: a.entry_id,
          name: a.house_name,
          entities: a.house_entities || {},
          rooms: [],
        });
      }
      const house = houses.get(a.entry_id);
      house.standalone = false;
      house.rooms.push(room);
    }
    // With an explicit room list, only the houses of those rooms are shown.
    return [...houses.values()].filter((h) => !filtered || h.rooms.length);
  }

  _watched() {
    const ids = [];
    for (const house of this._houses()) {
      ids.push(...Object.values(house.entities));
      for (const room of house.rooms) {
        ids.push(room.entity_id, ...Object.values(room.attributes.entities || {}));
        ids.push(...(room.attributes.climate_entities || []));
      }
    }
    return ids;
  }

  _state(id) {
    return id ? this._hass.states[id] : undefined;
  }

  _label(stateObj, value) {
    if (!stateObj) return value ?? "";
    if (this._hass.formatEntityState) {
      try {
        return this._hass.formatEntityState(stateObj, value);
      } catch (e) {
        /* older frontends */
      }
    }
    return value ?? stateObj.state;
  }

  _presetName(attrs, preset) {
    return (attrs.preset_names && attrs.preset_names[preset]) || preset;
  }

  _fmtTime(iso) {
    if (!iso) return "–";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "–";
    const sameDay = new Date().toDateString() === d.toDateString();
    const opts = sameDay
      ? { hour: "2-digit", minute: "2-digit" }
      : { weekday: "short", hour: "2-digit", minute: "2-digit" };
    return d.toLocaleString(this._lang(), opts);
  }

  _temp(value) {
    const n = num(value);
    return n === null ? "–" : `${n.toFixed(1)}°`;
  }

  // ------------------------------------------------------------------ render
  _render() {
    if (!this._config) return;
    const cfg = this._config;
    const houses = this._hass ? this._houses() : [];
    const title = cfg.title ?? this._t("title");
    let body = "";
    if (!houses.length) {
      body = `<p class="empty">${this._t("no_rooms")}</p>`;
    } else {
      body = houses
        .map(
          (house) =>
            (cfg.show_house ? this._houseHtml(house) : "") +
            (cfg.show_rooms
              ? house.rooms.length
                ? house.rooms.map((r) => this._roomHtml(r)).join("")
                : `<p class="empty">${this._t("no_rooms")}</p>`
              : "")
        )
        .join("");
    }
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card>
        ${title ? `<h2 class="title">${esc(title)}</h2>` : ""}
        ${body}
      </ha-card>`;
  }

  _icon(name) {
    return name ? `<ha-icon icon="mdi:${name}"></ha-icon>` : "";
  }

  _btn(label, attrs, { icon = "", kind = "" } = {}) {
    return `<button class="btn ${kind}" ${attrs}>${this._icon(icon)}<span>${esc(label)}</span></button>`;
  }

  _toggle(entityId, label) {
    const s = this._state(entityId);
    if (!s) return "";
    const on = s.state === "on";
    return `<button class="toggle ${on ? "on" : ""}" role="switch" aria-checked="${on}"
      data-action="toggle" data-entity="${esc(entityId)}"><span class="knob"></span><span>${esc(
      label
    )}</span></button>`;
  }

  _tempPair(current, target, color) {
    return `<div class="temps">
        <div class="tval"><span class="tag">${this._t("now_tag")}</span><span class="tnum">${this._temp(
          current
        )}</span></div>
        <div class="tval target" style="--c:${color}"><span class="tag">${this._t(
          "target_tag"
        )}</span><span class="tnum">${this._temp(target)}</span></div>
      </div>`;
  }

  _houseHtml(house) {
    const e = house.entities;
    const presence = this._state(e.presence);
    const mode = this._state(e.mode);
    const outdoor = this._state(e.outdoor_average);
    const season = this._state(e.heating_season);
    const cutoff = this._state(e.outdoor_cutoff);
    const demand = this._state(e.heat_demand);
    const runtime = this._state(e.heating_runtime);
    const guest = this._state(e.guest_mode);
    const vStart = this._state(e.vacation_start);
    const vEnd = this._state(e.vacation_end);

    const persons = presence?.attributes?.persons || {};
    const personList = Object.entries(persons)
      .map(([id, cls]) => {
        const p = this._hass.states[id];
        const name = p?.attributes?.friendly_name || id.split(".")[1];
        return `<span class="person ${esc(cls || "unknown")}" title="${esc(
          this._label(presence, cls)
        )}">${esc(name)}</span>`;
      })
      .join("");

    const modes = (mode?.attributes?.options || ["auto", "vacation", "off", "summer"])
      .map(
        (opt) => `<button class="seg ${mode?.state === opt ? "active" : ""}" data-action="mode"
          data-entity="${esc(e.mode)}" data-option="${esc(opt)}">${esc(this._label(mode, opt))}</button>`
      )
      .join("");

    const stat = (label, value, extra = "") =>
      `<div class="stat ${extra}"><span class="k">${esc(label)}</span><span class="v">${esc(
        value
      )}</span></div>`;
    const onOff = (s) => (s ? (s.state === "on" ? this._t("on") : this._t("off")) : "–");
    const guestUntil = guest?.attributes?.until
      ? `<span class="muted">${this._t("until")} ${esc(this._fmtTime(guest.attributes.until))}</span>`
      : "";
    const vacationSet = vStart && !Number.isNaN(Date.parse(vStart.state));
    const vacationSummary = vacationSet
      ? `${esc(this._fmtTime(vStart.state))} – ${esc(this._fmtTime(vEnd?.state))}`
      : this._t("vacation_none");

    return `
      <section class="block house">
        <div class="house-head">
          <div>
            <div class="name">${esc(house.name || "")}</div>
            <div class="presence">
              <span class="pill presence-state ${esc(presence?.state)}">${esc(this._label(presence))}</span>
              ${presence?.attributes?.arriving ? `<span class="pill">${this._t("arriving")}</span>` : ""}
              ${personList}
            </div>
          </div>
          <div class="stats">
            ${stat(this._t("outdoor"), this._temp(outdoor?.state))}
            ${stat(this._t("season"), onOff(season))}
            ${cutoff?.state === "on" ? stat(this._t("cutoff"), this._t("on"), "warn") : ""}
            ${stat(this._t("demand"), onOff(demand), demand?.state === "on" ? "hot" : "")}
            ${runtime ? stat(this._t("runtime"), `${num(runtime.state)?.toFixed(1) ?? "–"} h`) : ""}
          </div>
        </div>
        <div class="label">${this._t("mode")}</div>
        <div class="segmented" role="group" aria-label="${esc(this._t("mode"))}">${modes}</div>
        <div class="row wrap">
          ${this._toggle(e.pause, this._t("pause"))}
          ${this._toggle(e.guest_mode, this._t("guests"))}${guestUntil}
        </div>
        <details class="fold" data-fold="vac-${esc(house.id)}" ${this._open[`vac-${house.id}`] ? "open" : ""}>
          <summary><span>${this._t("vacation")}</span><span class="muted">${vacationSummary}</span></summary>
          <div class="fold-body">
            <div class="dates">
              <label class="datefield"><span>${this._t("from")}</span>
                <input type="datetime-local" data-vac="start" data-house="${esc(house.id)}"
                  value="${esc(toLocalInput(vStart?.state))}"></label>
              <label class="datefield"><span>${this._t("to")}</span>
                <input type="datetime-local" data-vac="end" data-house="${esc(house.id)}"
                  value="${esc(toLocalInput(vEnd?.state))}"></label>
            </div>
            <p class="hint">${this._t("vacation_hint")}</p>
            <div class="row wrap">
              ${this._btn(this._t("set_vacation"), `data-action="vacation" data-house="${esc(house.id)}"`, {
                icon: "content-save",
                kind: "primary",
              })}
              ${
                e.clear_vacation && vacationSet
                  ? this._btn(this._t("clear_vacation"), `data-action="press" data-entity="${esc(e.clear_vacation)}"`, {
                      icon: "close",
                    })
                  : ""
              }
            </div>
            ${this._error[`vac-${house.id}`] ? `<p class="error">${esc(this._error[`vac-${house.id}`])}</p>` : ""}
          </div>
        </details>
        <div class="row wrap">
          ${e.reevaluate ? this._btn(this._t("reevaluate"), `data-action="press" data-entity="${esc(e.reevaluate)}"`, { icon: "refresh" }) : ""}
          ${
            e.clear_overrides
              ? this._btn(this._t("clear_all"), `data-action="press" data-entity="${esc(e.clear_overrides)}"`, {
                  icon: "restore",
                })
              : ""
          }
        </div>
      </section>`;
  }

  _roomHtml(stateObj) {
    const cfg = this._config;
    const a = stateObj.attributes;
    const e = a.entities || {};
    const key = a.room_id;
    const folded = this._open[`room-${key}`] === undefined ? cfg.collapsed : !this._open[`room-${key}`];
    const color = PRESET_COLORS[a.preset] || "var(--secondary-text-color)";

    const badges = [];
    if (a.heat_demand) badges.push(`<span class="pill hot">${this._t("heating")}</span>`);
    if (a.window_open) badges.push(`<span class="pill warn">${this._t("window")}</span>`);
    if (a.override) {
      const until = a.override.until
        ? `${this._t("until")} ${this._fmtTime(a.override.until)}`
        : this._t("until_change");
      const prefix = stateObj.state === "manual_override" ? "" : `${this._t("override")} `;
      badges.push(`<span class="pill">${esc(prefix + until)}</span>`);
    }

    const head = `
      <div class="room-head">
        <button class="room-title" data-action="fold" data-key="room-${esc(key)}" aria-expanded="${!folded}">
          <span class="chev ${folded ? "" : "open"}"></span><span class="name">${esc(a.room_name)}</span>
        </button>
        ${this._tempPair(a.current_temperature, a.target_temperature, color)}
      </div>
      <div class="decision"><span class="pill rule" style="--c:${color}">${esc(
        this._label(stateObj)
      )}</span>${badges.join("")}</div>`;

    if (folded) return `<section class="block room">${head}</section>`;

    const parts = [
      `<p class="reason">${esc(a.reason || "")}</p>`,
      cfg.show_timeline ? this._timelineHtml(a) : "",
      this._controlsHtml(a, e),
      cfg.show_quick_override ? this._quickHtml(a) : "",
      cfg.show_levels ? this._levelsHtml(a, e) : "",
      cfg.show_details ? this._detailsHtml(a, e) : "",
      cfg.show_schedule_editor ? this._scheduleHtml(a, stateObj) : "",
    ];
    return `<section class="block room">${head}${parts.join("")}</section>`;
  }

  /** Segments of a profile over one day (the last slot continues past midnight). */
  _segments(slots) {
    const sorted = [...slots].sort((x, y) => toMinutes(x.time) - toMinutes(y.time));
    const segments = [];
    const last = sorted[sorted.length - 1];
    if (toMinutes(sorted[0].time) > 0) {
      segments.push({ start: 0, end: toMinutes(sorted[0].time), preset: last.preset });
    }
    sorted.forEach((slot, i) => {
      const end = i + 1 < sorted.length ? toMinutes(sorted[i + 1].time) : 1440;
      segments.push({ start: toMinutes(slot.time), end, preset: slot.preset });
    });
    return segments.filter((s) => s.end > s.start);
  }

  /** Intervals as people read them: from a slot to the next one; the last one ends at the first slot of the next day. */
  _intervals(slots) {
    const sorted = [...slots].sort((x, y) => toMinutes(x.time) - toMinutes(y.time));
    return sorted.map((slot, i) => {
      if (i + 1 < sorted.length) {
        return { from: slot.time, to: sorted[i + 1].time, preset: slot.preset, nextDay: false };
      }
      const first = sorted[0];
      if (sorted.length > 1 && toMinutes(first.time) === 0) {
        return { from: slot.time, to: "24:00", preset: slot.preset, nextDay: false };
      }
      return { from: slot.time, to: first.time, preset: slot.preset, nextDay: true };
    });
  }

  _timelineHtml(a) {
    const profile = a.profile && a.schedule && a.schedule[a.profile];
    if (!profile || !profile.length) return "";
    const segments = this._segments(profile);
    const levels = a.levels || {};
    const temps = segments.map((s) => num(levels[s.preset])).filter((t) => t !== null);
    const lo = temps.length ? Math.min(...temps) : 0;
    const hi = temps.length ? Math.max(...temps) : 1;
    const W = 1440;
    const H = 56;
    const height = (preset) => {
      const t = num(levels[preset]);
      if (t === null || hi === lo) return H * 0.6;
      return H * (0.25 + (0.7 * (t - lo)) / (hi - lo));
    };
    let path = `M0 ${H}`;
    const labels = [];
    const blocks = segments
      .map((s) => {
        const h = height(s.preset);
        path += ` L${s.start} ${H - h} L${s.end} ${H - h}`;
        const t = num(levels[s.preset]);
        if (s.end - s.start >= 120) {
          const pct = ((s.start + s.end) / 2 / W) * 100;
          const align =
            s.start === 0 ? "left:0;transform:none" : s.end >= W ? "right:0;transform:none" : `left:${pct}%`;
          labels.push(
            `<span style="${align};bottom:${((h + 4) / (H + 14)) * 100}%">${esc(
              this._presetName(a, s.preset)
            )}${t !== null ? ` ${t}°` : ""}</span>`
          );
        }
        return `<rect x="${s.start}" y="${H - h}" width="${s.end - s.start}" height="${h}" rx="0"
          fill="${PRESET_COLORS[s.preset] || "var(--primary-color)"}"><title>${esc(
          this._presetName(a, s.preset)
        )} ${hhmm(s.start)}–${hhmm(s.end % 1440)}</title></rect>`;
      })
      .join("");
    path += ` L${W} ${H}`;
    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();
    const ticks = [0, 6, 12, 18, 24]
      .map((h) => `<span style="left:${(h / 24) * 100}%">${String(h).padStart(2, "0")}:00</span>`)
      .join("");
    const next = a.next_change
      ? `<span>${this._t("next")}: <b>${esc(this._fmtTime(a.next_change))}</b> → ${esc(
          this._presetName(a, a.next_preset)
        )}</span>`
      : "";
    return `
      <div class="chart-card">
        <div class="profile-chart">
          <svg viewBox="0 -14 ${W} ${H + 14}" preserveAspectRatio="none" role="img"
            aria-label="${esc(this._t("schedule"))}">
            ${blocks}
            <path d="${path}" class="edge"></path>
            <line x1="${nowMin}" x2="${nowMin}" y1="-14" y2="${H}" class="now"></line>
          </svg>
          <div class="chart-labels">${labels.join("")}</div>
          <div class="ticks">${ticks}</div>
        </div>
        <div class="meta"><span>${this._t("today")}: <b>${esc(a.profile || "–")}</b></span>${next}</div>
      </div>`;
  }

  _controlsHtml(a, e) {
    const profile = this._state(e.profile);
    const options = (profile?.attributes?.options || [])
      .map(
        (opt) =>
          `<option value="${esc(opt)}" ${profile.state === opt ? "selected" : ""}>${esc(
            this._label(profile, opt)
          )}</option>`
      )
      .join("");
    const select = profile
      ? `<label class="selectfield"><span>${this._t("profile")}</span><select data-action="select" data-entity="${esc(
          e.profile
        )}">${options}</select></label>`
      : "";
    const clear = a.override
      ? this._btn(this._t("clear_override"), `data-action="clear" data-room="${esc(a.room_id)}"`, {
          icon: "autorenew",
          kind: "primary",
        })
      : "";
    return `<div class="row wrap controls">${select}${this._toggle(e.child_lock, this._t("child_lock"))}${clear}</div>`;
  }

  _quickHtml(a) {
    const presets = (a.presets || Object.keys(PRESET_COLORS))
      .map(
        (p) => `<button class="preset" style="--c:${PRESET_COLORS[p] || "var(--primary-color)"}"
          data-action="quick-preset" data-room="${esc(a.room_id)}" data-preset="${esc(p)}"><span class="dot"></span>${esc(
          this._presetName(a, p)
        )}${num(a.levels?.[p]) !== null ? ` <small>${num(a.levels[p])}°</small>` : ""}</button>`
      )
      .join("");
    const target = num(a.target_temperature) ?? 21;
    return this._fold(
      `quick-${a.room_id}`,
      this._t("quick"),
      `<p class="hint">${this._t("quick_hint")}</p>
        <div class="presets">${presets}</div>
        <div class="row wrap">
          <label class="numfield"><span>${this._t("target_tag")}</span><input type="number" step="0.5" min="5" max="30"
            data-quick="temp" data-room="${esc(a.room_id)}" value="${target}"><em>°C</em></label>
          <label class="numfield"><span>${this._t("for_hours")}</span><input type="number" step="0.5" min="0.5" max="72"
            data-quick="hours" data-room="${esc(a.room_id)}" placeholder="auto"><em>${this._t("hours")}</em></label>
          ${this._btn(this._t("apply"), `data-action="quick-temp" data-room="${esc(a.room_id)}"`, {
            icon: "thermometer-check",
            kind: "primary",
          })}
        </div>`
    );
  }

  _levelsHtml(a, e) {
    const numbers = Object.entries(e).filter(([k]) => k.startsWith("level_"));
    if (!numbers.length) return "";
    const rows = numbers
      .map(([k, id]) => {
        const s = this._state(id);
        if (!s) return "";
        const preset = k.replace("level_", "");
        const name = s.attributes.friendly_name?.replace(`${a.room_name} `, "") || this._presetName(a, preset);
        return `<label class="numfield level"><span class="dot" style="--c:${
          PRESET_COLORS[preset] || "var(--divider-color)"
        }"></span><span class="lname">${esc(name)}</span><input type="number" step="${s.attributes.step || 0.5}" min="${
          s.attributes.min ?? 5
        }" max="${s.attributes.max ?? 30}" data-action="number" data-entity="${esc(id)}" value="${esc(
          s.state
        )}"><em>°C</em></label>`;
      })
      .join("");
    return this._fold(`levels-${a.room_id}`, this._t("levels"), `<div class="grid">${rows}</div>`);
  }

  _detailsHtml(a, e) {
    const rate = this._state(e.heating_rate);
    const runtime = this._state(e.heating_runtime);
    const offsets =
      (a.offsets || []).map(([label, delta]) => `${label} ${delta > 0 ? "+" : ""}${delta}°`).join(", ") ||
      this._t("none");
    const active = a.device_level !== undefined ? a.device_level : a.device_preset;
    const fromDevice = a.custom_levels ? a.device_levels || [] : [];
    const levelTemps = Object.entries(a.levels || {})
      .filter(([, t]) => t !== null && t !== undefined)
      .map(
        ([p, t]) =>
          `<span class="lv ${p === active ? "active" : ""}"><span class="dot" style="--c:${PRESET_COLORS[p]}"></span>${esc(
            this._presetName(a, p)
          )} ${t}°${fromDevice.includes(p) ? ` <small>${this._t("from_device")}</small>` : ""}${
            p === active ? ` <small>${this._t("active")}</small>` : ""
          }</span>`
      )
      .join("");
    const rawPreset = a.device_preset;
    const devicePreset =
      a.climate_entities && a.climate_entities.length
        ? !rawPreset || rawPreset === "none"
          ? this._t("no_preset")
          : rawPreset
        : null;
    const dl = (k, v) => `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>`;
    const html = `<dl class="details">
        ${dl(this._t("room_temp"), esc(this._temp(a.current_temperature)))}
        ${dl(this._t("target"), esc(this._temp(a.target_temperature)))}
        ${rate ? dl(this._t("rate"), `${esc(num(rate.state)?.toFixed(2) ?? "–")} °C/h`) : ""}
        ${runtime ? dl(this._t("runtime"), `${esc(num(runtime.state)?.toFixed(1) ?? "–")} h`) : ""}
        ${devicePreset !== null ? dl(this._t("device_preset"), esc(devicePreset)) : ""}
        ${dl(this._t("adjustments"), esc(offsets))}
      </dl>
      ${
        levelTemps
          ? `<div class="label">${a.custom_levels ? this._t("levels") : this._t("level_temps_gt")}</div>
             <div class="levels-line">${levelTemps}</div>`
          : ""
      }
      ${a.schedule_error ? `<p class="error">${esc(a.schedule_error)}</p>` : ""}`;
    return this._fold(`details-${a.room_id}`, this._t("details"), html);
  }

  _profileDays(name) {
    const days = {
      workday: this._t("days_workday"),
      weekend: this._t("days_weekend"),
    };
    if (days[name]) return days[name];
    const weekday = WEEKDAY_KEYS.indexOf(name);
    if (weekday >= 0) return this._t("days_weekday").replace("{day}", this._weekdayName(weekday));
    return this._t("days_custom");
  }

  _weekdayName(index) {
    // 2024-01-01 was a Monday.
    return new Date(2024, 0, 1 + index).toLocaleDateString(this._lang(), { weekday: "long" });
  }

  _scheduleIntro(a, stateObj) {
    const scheduleRules = ["schedule", "optimal_start", "optimal_stop"];
    const now = scheduleRules.includes(stateObj.state)
      ? `<p class="hint ok">${this._t("schedule_active")}</p>`
      : `<p class="hint warn">${this._t("schedule_not_active").replace("{rule}", esc(this._label(stateObj)))}</p>`;
    return `<p class="hint">${this._t("schedule_help")}</p>${now}`;
  }

  _scheduleHtml(a, stateObj) {
    if (!a.schedule_editable) {
      return this._fold(`sched-${a.room_id}`, this._t("schedule"), `<p class="hint">${this._t("not_editable")}</p>`);
    }
    const intro = this._scheduleIntro(a, stateObj);
    if (this._editing !== a.room_id) {
      const profiles = Object.entries(a.schedule || {})
        .map(([name, slots]) => {
          const rows = this._intervals(slots)
            .map(
              (it) => `<li><span class="dot" style="--c:${PRESET_COLORS[it.preset]}"></span>
                <span class="range">${esc(it.from)} – ${esc(it.to)}${
                it.nextDay ? ` <small>${this._t("next_day")}</small>` : ""
              }</span><span class="pname">${esc(this._presetName(a, it.preset))}</span></li>`
            )
            .join("");
          return `<div class="profile ${a.profile === name ? "today" : ""}">
              <div class="phead"><b>${esc(name)}</b>${
            a.profile === name ? `<span class="pill">${this._t("today")}</span>` : ""
          }<span class="muted">${esc(this._profileDays(name))}</span></div>
              <ul class="intervals">${rows}</ul></div>`;
        })
        .join("");
      return this._fold(
        `sched-${a.room_id}`,
        this._t("schedule"),
        `${intro}<div class="profiles">${profiles}</div>
         <div class="row">${this._btn(this._t("edit"), `data-action="edit" data-room="${esc(a.room_id)}"`, {
           icon: "pencil",
           kind: "primary",
         })}</div>`
      );
    }
    const presets = a.presets || Object.keys(PRESET_COLORS);
    const option = (preset, current) =>
      `<option value="${esc(preset)}" ${preset === current ? "selected" : ""}>${esc(
        this._presetName(a, preset)
      )}</option>`;
    const blocks = Object.entries(this._draft || {})
      .map(([name, slots]) => {
        const intervals = this._intervals(slots);
        const sorted = [...slots]
          .map((slot, i) => ({ slot, i }))
          .sort((x, y) => toMinutes(x.slot.time) - toMinutes(y.slot.time));
        const rows = sorted
          .map(({ slot, i }, pos) => {
            const it = intervals[pos];
            return `<div class="slot-row">
              <span class="dot" style="--c:${PRESET_COLORS[slot.preset]}"></span>
              <input type="time" data-profile="${esc(name)}" data-index="${i}" data-field="time" value="${esc(slot.time)}"
                aria-label="${this._t("starts")}">
              <span class="until">→ ${esc(it.to)}${it.nextDay ? ` <small>${this._t("next_day")}</small>` : ""}</span>
              <select data-profile="${esc(name)}" data-index="${i}" data-field="preset">${presets
                .map((p) => option(p, slot.preset))
                .join("")}</select>
              <button class="btn icon-only" data-action="del-slot" data-profile="${esc(name)}" data-index="${i}"
                aria-label="${this._t("remove")}" title="${this._t("remove")}">${this._icon("delete-outline")}<span class="x">✕</span></button>
            </div>`;
          })
          .join("");
        return `<div class="profile edit">
            <div class="phead"><b>${esc(name)}</b><span class="muted">${esc(this._profileDays(name))}</span>
              ${this._btn(this._t("remove_profile"), `data-action="del-profile" data-profile="${esc(name)}"`, {
                icon: "delete-outline",
                kind: "danger",
              })}</div>
            <div class="slot-head"><span></span><span>${this._t("starts")}</span><span>${this._t("ends")}</span><span>${this._t(
              "level"
            )}</span><span></span></div>
            ${rows}
            ${this._btn(this._t("add_slot"), `data-action="add-slot" data-profile="${esc(name)}"`, { icon: "plus" })}
          </div>`;
      })
      .join("");
    return `<div class="editor">
        <div class="ehead"><b>${this._t("schedule")}</b></div>
        ${intro}
        ${blocks}
        <div class="row wrap">
          <label class="textfield"><span>${this._t("profile_name")}</span>
            <input type="text" class="newprofile" placeholder="home_office"></label>
          ${this._btn(this._t("add_profile"), `data-action="add-profile"`, { icon: "plus" })}
        </div>
        ${this._error[`sched-${a.room_id}`] ? `<p class="error">${esc(this._error[`sched-${a.room_id}`])}</p>` : ""}
        <div class="row wrap end">
          ${this._btn(this._t("cancel"), `data-action="cancel"`, {})}
          ${this._btn(this._t("save"), `data-action="save" data-room="${esc(a.room_id)}"`, {
            icon: "content-save",
            kind: "primary",
          })}
        </div>
      </div>`;
  }

  _fold(key, title, content) {
    return `<details class="fold" data-fold="${esc(key)}" ${this._open[key] ? "open" : ""}>
      <summary><span>${esc(title)}</span></summary><div class="fold-body">${content}</div></details>`;
  }

  // ------------------------------------------------------------------ events
  _onToggle(ev) {
    const el = ev.target;
    if (el?.dataset?.fold) this._open[el.dataset.fold] = el.open;
  }

  async _call(domain, service, data, errorKey) {
    try {
      await this._hass.callService(domain, service, data);
      if (errorKey) delete this._error[errorKey];
      return true;
    } catch (err) {
      if (errorKey) this._error[errorKey] = `${this._t("error")}: ${err?.message || err}`;
      this._lastKey = "";
      this._render();
      return false;
    }
  }

  async _onChange(ev) {
    const el = ev.target;
    const d = el.dataset || {};
    if (d.action === "select") {
      await this._call("select", "select_option", { entity_id: d.entity, option: el.value });
    } else if (d.action === "number") {
      const value = num(el.value);
      if (value !== null) await this._call("number", "set_value", { entity_id: d.entity, value });
    } else if (d.field && this._draft?.[d.profile]) {
      this._draft[d.profile][Number(d.index)][d.field] = el.value;
      this._render();
    }
  }

  _quickValues(room) {
    const temp = this.shadowRoot.querySelector(`input[data-quick="temp"][data-room="${CSS.escape(room)}"]`);
    const hours = this.shadowRoot.querySelector(`input[data-quick="hours"][data-room="${CSS.escape(room)}"]`);
    const data = {};
    const h = num(hours?.value);
    if (h !== null) data.duration_hours = h;
    return { temp: num(temp?.value), data };
  }

  async _onClick(ev) {
    const el = ev.target.closest("[data-action]");
    if (!el || el.tagName === "SELECT" || el.tagName === "INPUT") return;
    const { action, room, profile, index, entity, option, key, house } = el.dataset;
    switch (action) {
      case "fold":
        this._open[key] = el.getAttribute("aria-expanded") !== "true";
        break;
      case "toggle":
        await this._call(entity.split(".")[0], "toggle", { entity_id: entity });
        return;
      case "mode":
        await this._call("select", "select_option", { entity_id: entity, option });
        return;
      case "press":
        await this._call("button", "press", { entity_id: entity });
        return;
      case "vacation": {
        const h = this._houses().find((x) => x.id === house);
        if (!h) return;
        const start = this.shadowRoot.querySelector(`input[data-vac="start"][data-house="${CSS.escape(house)}"]`);
        const end = this.shadowRoot.querySelector(`input[data-vac="end"][data-house="${CSS.escape(house)}"]`);
        const data = { config_entry_id: house };
        if (start?.value) data.start = fromLocalInput(start.value);
        if (end?.value) data.end = fromLocalInput(end.value);
        await this._call("advanced_climate", "set_vacation", data, `vac-${house}`);
        break;
      }
      case "clear":
        await this._call("advanced_climate", "clear_override", { room });
        return;
      case "quick-preset": {
        const { data } = this._quickValues(room);
        await this._call("advanced_climate", "set_override", { room, preset: el.dataset.preset, ...data });
        return;
      }
      case "quick-temp": {
        const { temp, data } = this._quickValues(room);
        if (temp === null) return;
        await this._call("advanced_climate", "set_override", { room, temperature: temp, ...data });
        return;
      }
      case "edit": {
        const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
        this._editing = room;
        this._open[`sched-${room}`] = true;
        this._draft = JSON.parse(JSON.stringify(stateObj.attributes.schedule));
        break;
      }
      case "cancel":
        this._editing = null;
        this._draft = null;
        break;
      case "add-slot": {
        const slots = this._draft[profile];
        const lastTime = slots.length ? toMinutes(slots[slots.length - 1].time) : 0;
        slots.push({ time: hhmm(Math.min(lastTime + 60, 23 * 60 + 59)), preset: "home" });
        break;
      }
      case "del-slot":
        this._draft[profile].splice(Number(index), 1);
        if (!this._draft[profile].length) delete this._draft[profile];
        break;
      case "del-profile":
        delete this._draft[profile];
        break;
      case "add-profile": {
        const input = this.shadowRoot.querySelector(".newprofile");
        const name = (input?.value || "").trim().toLowerCase().replace(/\s+/g, "_");
        if (name && !this._draft[name]) this._draft[name] = [{ time: "00:00", preset: "home" }];
        break;
      }
      case "save": {
        const ok = await this._call(
          "advanced_climate",
          "set_schedule",
          { room, profiles: this._draft },
          `sched-${room}`
        );
        if (ok) {
          this._editing = null;
          this._draft = null;
        }
        break;
      }
      default:
        return;
    }
    this._lastKey = "";
    this._render();
  }
}

const STYLE = `
  :host {
    --ac-surface: color-mix(in srgb, var(--primary-text-color) 4%, transparent);
    --ac-surface-2: color-mix(in srgb, var(--primary-text-color) 7%, transparent);
    --ac-line: color-mix(in srgb, var(--primary-text-color) 12%, transparent);
    --ac-muted: var(--secondary-text-color);
    --ac-accent: var(--primary-color);
    --ac-hot: #d9480f;
    --ac-warn: #c98a12;
    color: var(--primary-text-color);
  }
  ha-card { padding: 16px; color: var(--primary-text-color); display: flex; flex-direction: column; gap: 12px; }
  .title { margin: 0; font-size: 1.35em; font-weight: 500; letter-spacing: -0.01em; }
  .empty { margin: 0; color: var(--ac-muted); }
  .muted { color: var(--ac-muted); font-size: 0.85em; }
  .block { border: 1px solid var(--ac-line); border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
  .house { background: var(--ac-surface); }
  .name { font-weight: 600; font-size: 1.1em; }
  .label { font-size: 0.8em; color: var(--ac-muted); margin-bottom: -4px; }
  .row { display: flex; gap: 10px; align-items: center; }
  .row.wrap { flex-wrap: wrap; }
  .row.end { justify-content: flex-end; }
  .controls { align-items: flex-end; }
  .controls .toggle { min-height: 36px; }
  .hint { margin: 0; font-size: 0.85em; color: var(--ac-muted); line-height: 1.45; }
  .hint.ok { color: #2f9e8f; }
  .hint.warn { color: var(--ac-warn); }
  .error { margin: 0; color: var(--error-color, #db4437); font-size: 0.85em; }

  /* house */
  .house-head { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .presence { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 6px; }
  .stats { display: grid; grid-auto-flow: column; gap: 18px; align-items: start; }
  .stat { display: flex; flex-direction: column; gap: 2px; }
  .stat .k { font-size: 0.75em; color: var(--ac-muted); }
  .stat .v { font-variant-numeric: tabular-nums; font-weight: 600; }
  .stat.hot .v { color: var(--ac-hot); }
  .stat.warn .v { color: var(--ac-warn); }
  @media (max-width: 520px) { .stats { grid-auto-flow: row; grid-template-columns: 1fr 1fr; } }

  /* pills */
  .pill { display: inline-flex; align-items: center; gap: 4px; font-size: 0.8em; padding: 3px 10px;
    border-radius: 999px; background: var(--ac-surface-2); white-space: nowrap; }
  .pill.rule { background: color-mix(in srgb, var(--c) 18%, transparent); color: var(--primary-text-color);
    box-shadow: inset 0 0 0 1.5px var(--c); font-weight: 500; }
  .pill.hot { background: var(--ac-hot); color: #fff; }
  .pill.warn { background: var(--ac-warn); color: #fff; }
  .presence-state.home { background: color-mix(in srgb, #f08c00 22%, transparent); }
  .presence-state.nearby { background: color-mix(in srgb, #2f9e8f 22%, transparent); }
  .presence-state.far { background: color-mix(in srgb, #8a96a3 25%, transparent); }
  .person { font-size: 0.8em; padding: 2px 9px; border-radius: 999px; box-shadow: inset 0 0 0 1px var(--ac-line); }
  .person.home { box-shadow: inset 0 0 0 1.5px #f08c00; }
  .person.nearby { box-shadow: inset 0 0 0 1.5px #2f9e8f; }

  /* buttons */
  .btn { display: inline-flex; align-items: center; gap: 6px; font: inherit; font-size: 0.9em; font-weight: 500;
    padding: 7px 14px; border-radius: 10px; border: 1px solid var(--ac-line); background: var(--card-background-color);
    color: var(--primary-text-color); cursor: pointer; transition: background .15s, border-color .15s; }
  .btn:hover { background: var(--ac-surface-2); }
  .btn ha-icon { --mdc-icon-size: 18px; }
  .btn.primary { background: var(--ac-accent); border-color: var(--ac-accent); color: var(--text-primary-color, #fff); }
  .btn.primary:hover { filter: brightness(1.08); }
  .btn.danger { color: var(--error-color, #db4437); border-color: color-mix(in srgb, var(--error-color, #db4437) 40%, transparent); }
  .btn.icon-only { padding: 6px; }
  .btn.icon-only .x { display: none; }
  .btn.icon-only ha-icon:not(:defined) + .x { display: inline; }
  .segmented { display: grid; grid-template-columns: repeat(4, 1fr); padding: 3px; gap: 3px; border-radius: 12px;
    background: var(--ac-surface-2); }
  .seg { border: none; background: none; padding: 8px 6px; border-radius: 9px; font: inherit; font-size: 0.9em;
    color: var(--primary-text-color); cursor: pointer; }
  .seg.active { background: var(--card-background-color); box-shadow: 0 1px 2px rgba(0,0,0,.18); font-weight: 600; color: var(--ac-accent); }
  .toggle { display: inline-flex; align-items: center; gap: 8px; background: none; border: none; font: inherit;
    color: var(--primary-text-color); cursor: pointer; padding: 4px 0; }
  .toggle .knob { width: 34px; height: 20px; border-radius: 10px; background: var(--disabled-color, #bdbdbd); position: relative; flex: none; }
  .toggle .knob::after { content: ""; position: absolute; top: 3px; left: 3px; width: 14px; height: 14px;
    border-radius: 50%; background: #fff; transition: transform .15s; }
  .toggle.on .knob { background: var(--ac-accent); }
  .toggle.on .knob::after { transform: translateX(14px); }
  button:focus-visible, input:focus-visible, select:focus-visible, summary:focus-visible {
    outline: 2px solid var(--ac-accent); outline-offset: 2px; }

  /* fields */
  input, select { font: inherit; color: var(--primary-text-color); background: var(--card-background-color);
    border: 1px solid var(--ac-line); border-radius: 10px; padding: 7px 10px; min-height: 36px; box-sizing: border-box; }
  input:hover, select:hover { border-color: color-mix(in srgb, var(--primary-text-color) 30%, transparent); }
  input:focus, select:focus { border-color: var(--ac-accent); outline: none; }
  .dates { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; }
  .datefield, .selectfield, .textfield { display: flex; flex-direction: column; gap: 4px; font-size: 0.8em; color: var(--ac-muted); }
  .datefield input, .selectfield select, .textfield input { font-size: 1.1em; }
  .datefield input { width: 100%; }
  input[type="datetime-local"]::-webkit-calendar-picker-indicator,
  input[type="time"]::-webkit-calendar-picker-indicator { cursor: pointer; opacity: .7; }
  .numfield { display: inline-flex; align-items: center; gap: 6px; font-size: 0.9em; }
  .numfield span { color: var(--ac-muted); font-size: 0.9em; }
  .numfield em { font-style: normal; color: var(--ac-muted); }
  .numfield input { width: 5em; text-align: right; }
  .numfield.level { display: grid; grid-template-columns: 10px 1fr auto auto; padding: 6px 10px; border-radius: 12px; background: var(--ac-surface); }
  .numfield.level .lname { color: var(--primary-text-color); }

  /* rooms */
  .room-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
  .room-title { display: inline-flex; align-items: center; gap: 8px; background: none; border: none; padding: 0;
    font: inherit; color: inherit; cursor: pointer; text-align: left; }
  .chev { width: 8px; height: 8px; border-right: 2px solid var(--ac-muted); border-bottom: 2px solid var(--ac-muted);
    transform: rotate(-45deg); transition: transform .15s; }
  .chev.open { transform: rotate(45deg); }
  .temps { display: flex; gap: 6px; }
  .tval { display: flex; flex-direction: column; align-items: flex-end; padding: 4px 10px; border-radius: 12px; background: var(--ac-surface); min-width: 64px; }
  .tval .tag { font-size: 0.68em; color: var(--ac-muted); }
  .tval .tnum { font-size: 1.45em; font-variant-numeric: tabular-nums; line-height: 1.15; font-weight: 300; }
  .tval.target { background: color-mix(in srgb, var(--c) 16%, transparent); }
  .tval.target .tnum { font-weight: 600; }
  .decision { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .reason { margin: 0; color: var(--ac-muted); font-size: 0.9em; }
  .chart-card { border-radius: 12px; background: var(--ac-surface); padding: 10px 10px 8px; }
  .profile-chart { position: relative; }
  .profile-chart svg { width: 100%; height: 72px; display: block; overflow: visible; }
  .profile-chart rect { opacity: 0.85; }
  .profile-chart .edge { fill: none; stroke: var(--primary-text-color); stroke-width: 2; opacity: 0.3; vector-effect: non-scaling-stroke; }
  .profile-chart .now { stroke: var(--primary-text-color); stroke-width: 2; vector-effect: non-scaling-stroke; }
  .chart-labels { position: absolute; left: 0; right: 0; top: 0; height: 72px; pointer-events: none; }
  .chart-labels span { position: absolute; transform: translateX(-50%); font-size: 0.75em; white-space: nowrap; }
  .ticks { position: relative; height: 16px; font-size: 0.7em; color: var(--ac-muted); margin-top: 2px; }
  .ticks span { position: absolute; transform: translateX(-50%); }
  .ticks span:first-child { transform: none; }
  .ticks span:last-child { transform: translateX(-100%); }
  .meta { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; font-size: 0.85em; margin-top: 4px; }
  .presets { display: flex; flex-wrap: wrap; gap: 8px; }
  .preset { display: inline-flex; align-items: center; gap: 6px; font: inherit; font-size: 0.85em; padding: 6px 12px;
    border-radius: 10px; cursor: pointer; background: color-mix(in srgb, var(--c) 12%, transparent);
    color: var(--primary-text-color); border: 1px solid color-mix(in srgb, var(--c) 45%, transparent); }
  .preset:hover { background: color-mix(in srgb, var(--c) 28%, transparent); }
  .preset small { color: var(--ac-muted); }
  .preset .dot { background: var(--c); }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--c); display: inline-block; flex: none; }

  /* folds */
  .fold { border-top: 1px solid var(--ac-line); padding-top: 8px; }
  .fold summary { cursor: pointer; display: flex; justify-content: space-between; gap: 8px; align-items: center;
    list-style: none; font-weight: 500; padding: 2px 0; }
  .fold summary::-webkit-details-marker { display: none; }
  .fold summary::after { content: ""; width: 7px; height: 7px; border-right: 2px solid var(--ac-muted);
    border-bottom: 2px solid var(--ac-muted); transform: rotate(45deg); margin-right: 4px; transition: transform .15s; flex: none; }
  .fold[open] summary::after { transform: rotate(-135deg); }
  .fold summary .muted { margin-left: auto; font-weight: 400; }
  .fold-body { display: flex; flex-direction: column; gap: 10px; padding-top: 10px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; }
  .details { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; margin: 0; }
  .details div { background: var(--ac-surface); border-radius: 10px; padding: 8px 10px; }
  .details dt { font-size: 0.75em; color: var(--ac-muted); }
  .details dd { margin: 2px 0 0; font-variant-numeric: tabular-nums; font-weight: 500; }
  .levels-line { display: flex; gap: 12px; flex-wrap: wrap; font-size: 0.85em; align-items: center; }
  .lv { display: inline-flex; gap: 5px; align-items: center; padding: 2px 8px; border-radius: 999px; }
  .lv.active { background: var(--ac-surface-2); font-weight: 600; }

  /* schedule */
  .profiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
  .profile { border-radius: 12px; padding: 10px 12px; background: var(--ac-surface); display: flex; flex-direction: column; gap: 6px; }
  .profile.today { box-shadow: inset 0 0 0 1.5px var(--ac-accent); }
  .phead { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .phead .muted { flex: 1 1 100%; }
  .profile.edit .phead .muted { flex: 1; }
  .intervals { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .intervals li { display: grid; grid-template-columns: 10px auto 1fr; gap: 8px; align-items: center; font-size: 0.9em; }
  .intervals .range { font-variant-numeric: tabular-nums; }
  .intervals .pname { text-align: right; color: var(--ac-muted); }
  small { font-size: 0.8em; color: var(--ac-muted); }
  .editor { border-radius: 14px; background: var(--ac-surface); padding: 12px; display: flex; flex-direction: column; gap: 12px; }
  .ehead { font-size: 1em; }
  .slot-head, .slot-row { display: grid; grid-template-columns: 10px minmax(130px, 150px) minmax(90px, auto) 1fr auto; gap: 8px; align-items: center; }
  .slot-head { font-size: 0.75em; color: var(--ac-muted); }
  .slot-row .until { font-variant-numeric: tabular-nums; color: var(--ac-muted); font-size: 0.9em; }
  .profile.edit { background: var(--card-background-color); }
  @media (max-width: 480px) {
    .slot-head { display: none; }
    .slot-row { grid-template-columns: 10px 1fr auto; }
    .slot-row .until { grid-column: 2 / 4; order: 5; }
    .slot-row select { grid-column: 2 / 3; }
  }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
`;

// ---------------------------------------------------------------------- editor
const EDITOR_SCHEMA = [
  { name: "title", selector: { text: {} } },
  {
    name: "rooms",
    selector: { entity: { multiple: true, filter: { integration: "advanced_climate", domain: "sensor" } } },
  },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "show_house", selector: { boolean: {} } },
      { name: "show_rooms", selector: { boolean: {} } },
      { name: "show_timeline", selector: { boolean: {} } },
      { name: "show_quick_override", selector: { boolean: {} } },
      { name: "show_levels", selector: { boolean: {} } },
      { name: "show_details", selector: { boolean: {} } },
      { name: "show_schedule_editor", selector: { boolean: {} } },
      { name: "collapsed", selector: { boolean: {} } },
    ],
  },
];

const EDITOR_LABELS = {
  en: {
    title: "Title",
    rooms: "Rooms (Decision sensors; empty = all)",
    show_house: "House: presence, mode, pause, guests, vacation",
    show_rooms: "Rooms",
    show_timeline: "Today's schedule",
    show_quick_override: "Set a level for a while",
    show_levels: "Level temperatures",
    show_details: "Details",
    show_schedule_editor: "Schedule editor",
    collapsed: "Rooms start folded",
  },
  ro: {
    title: "Titlu",
    rooms: "Camere (senzorii Decision; gol = toate)",
    show_house: "Casa: prezență, mod, pauză, oaspeți, vacanță",
    show_rooms: "Camere",
    show_timeline: "Programul de azi",
    show_quick_override: "Setare temporară a unui nivel",
    show_levels: "Temperaturile nivelurilor",
    show_details: "Detalii",
    show_schedule_editor: "Editor de program",
    collapsed: "Camerele pornesc pliate",
  },
};

// ---------------------------------------------------------------- register
// Some Home Assistant setups replace window.customElements after page load
// (scoped custom element registry). Anything defined before the swap is not
// visible to the new registry and Lovelace reports that the card does not
// exist, so the card is defined again for a few seconds if needed.
const CARD_TAG = "advanced-climate-card";
const registerCard = () => {
  try {
    if (!window.customElements.get(CARD_TAG)) {
      window.customElements.define(CARD_TAG, AdvancedClimateCard);
      return true;
    }
  } catch (err) {
    if (!window.customElements.get(CARD_TAG)) {
      try {
        window.customElements.define(CARD_TAG, class extends AdvancedClimateCard {});
        return true;
      } catch (err2) {
        console.warn("advanced-climate-card: could not register on the current registry", err2);
      }
    }
  }
  return false;
};

if (!window.__advancedClimateCardLoaded) {
  window.__advancedClimateCardLoaded = CARD_VERSION;
  registerCard();
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === CARD_TAG)) {
    window.customCards.push({
      type: CARD_TAG,
      name: "Advanced Climate",
      description: "House and rooms of Advanced Climate with every control and an editable schedule.",
      preview: true,
      documentationURL: "https://github.com/sandreialexandru/Advanced-Climate#lovelace-card",
    });
  }
  console.info(`%c ADVANCED-CLIMATE-CARD %c ${CARD_VERSION} `, "color:#fff;background:#f08c00", "");
  let checks = 0;
  const watch = setInterval(() => {
    registerCard();
    if (++checks >= 60) clearInterval(watch); // 30 s
  }, 500);
  window.addEventListener("location-changed", registerCard);
} else {
  registerCard();
}
