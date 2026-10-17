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
 *   compact: false               # one row per room (and the house); tap a row to open it
 *   runtime_period: day          # heating time shown for: day | week | month (tap to change)
 */

const CARD_VERSION = "1.8.3";

const PRESET_COLORS = {
  comfort: "#d9480f",
  home: "#f08c00",
  activity: "#e0a030",
  eco: "#2f9e8f",
  sleep: "#5f6fd1",
  away: "#8a96a3",
};

const MIN_ZOOM_SPAN = 20 * 60 * 1000; // closest zoom: 20 minutes

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
  compact: false,
  runtime_period: "day",
};

const RUNTIME_PERIODS = ["day", "week", "month"];

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
    until_reeval: "until the next reevaluation",
    at_latest: "at the latest",
    reeval_help: "Ends when the schedule moves to another level, presence or the house mode changes, a window opens, the profile changes or the outdoor cutoff / heating season changes. The periodic check does not end it.",
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
    chart_label: "Last 24 hours and the next 12",
    legend_temp: "Temperature",
    legend_target: "Target / plan",
    legend_heat: "Heating",
    planned: "Planned",
    loading: "loading history…",
    drag_hint: "Drag the handles on the bar to move a start time in 5-minute steps (arrow keys: 5 min, Shift: 1 h). Levels are chosen in the list.",
    copy_to: "Copy over…",
    new_profile: "new",
    period_day: "today",
    period_week: "this week",
    period_month: "this month",
    period_hint: "Tap to change the period (today, this week, this month).",
    eta_learning: "learning…",
    eta_help: "Time until the target at the heating rate learned for the current outdoor temperature.",
    zoom_in: "Zoom in",
    zoom_out: "Zoom out",
    zoom_reset: "Whole period",
    zoom_1h: "Last hour",
    zoom_6h: "Last 6 hours",
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
    until_reeval: "până la următoarea reevaluare",
    at_latest: "cel târziu",
    reeval_help: "Se termină când programul trece la alt nivel, se schimbă prezența sau modul casei, se deschide o fereastră, se schimbă profilul ori pragul exterior / sezonul. Verificarea periodică nu o încheie.",
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
    chart_label: "Ultimele 24 de ore și următoarele 12",
    legend_temp: "Temperatură",
    legend_target: "Țintă / program",
    legend_heat: "Încălzire",
    planned: "Programat",
    loading: "se încarcă istoricul…",
    drag_hint: "Trage de mânerele de pe bară ca să muți o oră de început din 5 în 5 minute (săgeți: 5 min, Shift: 1 h). Nivelurile se aleg în listă.",
    copy_to: "Copiază peste…",
    new_profile: "nou",
    period_day: "azi",
    period_week: "săptămâna aceasta",
    period_month: "luna aceasta",
    period_hint: "Apasă ca să schimbi perioada (azi, săptămâna aceasta, luna aceasta).",
    eta_learning: "se învață…",
    eta_help: "Timpul până la țintă, după viteza de încălzire învățată pentru temperatura de afară de acum.",
    zoom_in: "Mărește",
    zoom_out: "Micșorează",
    zoom_reset: "Toată perioada",
    zoom_1h: "Ultima oră",
    zoom_6h: "Ultimele 6 ore",
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
    this.shadowRoot.addEventListener("pointerdown", (ev) => this._pointerDown(ev));
    this.shadowRoot.addEventListener("pointermove", (ev) => this._pointerMove(ev));
    this.shadowRoot.addEventListener("pointerup", (ev) => this._pointerUp(ev));
    this.shadowRoot.addEventListener("pointercancel", (ev) => this._pointerUp(ev));
    this.shadowRoot.addEventListener("wheel", (ev) => this._chartWheel(ev), { passive: false });
    this.shadowRoot.addEventListener("dblclick", (ev) => this._chartDblClick(ev));
    this.shadowRoot.addEventListener("pointerleave", (ev) => this._chartHover(ev), true);
    this.shadowRoot.addEventListener("keydown", (ev) => this._keyDown(ev));
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
    this._runtimePeriod = null;
    this._lastKey = "";
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this.style.colorScheme = hass?.themes?.darkMode ? "dark" : "light";
    if (this._editing || this._pan) return;
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
    if (this._config?.compact) return 2 + this._rooms().length;
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
                ? cfg.compact
                  ? `<div class="rooms-list">${house.rooms.map((r) => this._roomHtml(r)).join("")}</div>`
                  : house.rooms.map((r) => this._roomHtml(r)).join("")
                : `<p class="empty">${this._t("no_rooms")}</p>`
              : "")
        )
        .join("");
    }
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card class="${cfg.compact ? "compact" : ""}">
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

  /** "~35 min" until the target, from the learned heating rate. */
  _eta(a) {
    const current = num(a.current_temperature);
    const target = num(a.target_temperature);
    if (current === null || target === null || target - current <= 0.1) return "";
    if (a.time_to_target === null || a.time_to_target === undefined) return "";
    if (!a.rate_learned) return this._t("eta_learning");
    const m = Math.round(a.time_to_target);
    if (m < 60) return `~${m} min`;
    const h = Math.floor(m / 60);
    const r = Math.round((m % 60) / 5) * 5;
    return r ? `~${h} h ${r} min` : `~${h} h`;
  }

  _tempPair(current, target, color, eta = "") {
    return `<div class="temps">
        <div class="tval"><span class="tag">${this._t("now_tag")}</span><span class="tnum">${this._temp(
          current
        )}</span></div>
        <div class="tval target" style="--c:${color}"><span class="tag">${this._t(
          "target_tag"
        )}</span><span class="tnum">${this._temp(target)}</span>${
          eta ? `<span class="eta" title="${esc(this._t("eta_help"))}">${esc(eta)}</span>` : ""
        }</div>
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

    const houseKey = `house-${house.id}`;
    if (this._config.compact && !this._open[houseKey]) {
      return `<button class="crow house-row" data-action="fold" data-key="${esc(houseKey)}" aria-expanded="false">
          ${this._icon("home-thermometer-outline")}
          <span class="cname">${esc(house.name || "")}</span>
          <span class="pill presence-state ${esc(presence?.state)}">${esc(this._label(presence))}</span>
          <span class="pill">${esc(this._label(mode))}</span>
          ${demand?.state === "on" ? `<span class="cicon hot" title="${esc(this._t("heating"))}">${this._icon("fire")}</span>` : ""}
          <span class="ctemp muted">${this._t("outdoor")} ${esc(this._temp(outdoor?.state))}</span>
          <span class="chev"></span>
        </button>`;
    }
    const foldBack = this._config.compact
      ? `<button class="room-title" data-action="fold" data-key="${esc(houseKey)}" aria-expanded="true"><span class="chev open"></span></button>`
      : "";
    return `
      <section class="block house">
        <div class="house-head">
          <div>
            <div class="name">${foldBack}${esc(house.name || "")}</div>
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
            ${runtime ? this._runtimeStat(e.heating_runtime) : ""}
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
    const folded =
      this._open[`room-${key}`] === undefined ? cfg.collapsed || cfg.compact : !this._open[`room-${key}`];
    const color = PRESET_COLORS[a.preset] || "var(--secondary-text-color)";
    if (cfg.compact && folded) return this._compactRow(stateObj, color);

    const badges = [];
    if (a.heat_demand) badges.push(`<span class="pill hot">${this._t("heating")}</span>`);
    if (a.window_open) badges.push(`<span class="pill warn">${this._t("window")}</span>`);
    if (a.override) {
      const until = this._overrideUntil(a);
      const prefix = stateObj.state === "manual_override" ? "" : `${this._t("override")} `;
      badges.push(`<span class="pill" title="${esc(a.override.until ? "" : this._t("reeval_help"))}">${esc(
        prefix + until
      )}</span>`);
    }

    const head = `
      <div class="room-head">
        <button class="room-title" data-action="fold" data-key="room-${esc(key)}" aria-expanded="${!folded}">
          <span class="chev ${folded ? "" : "open"}"></span><span class="name">${esc(a.room_name)}</span>
        </button>
        ${this._tempPair(a.current_temperature, a.target_temperature, color, this._eta(a))}
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

  /** When a manual change ends, in words. */
  _overrideUntil(a) {
    if (!a.override) return "";
    if (a.override.until) return `${this._t("until")} ${this._fmtTime(a.override.until)}`;
    const latest = a.next_change
      ? ` (${this._t("at_latest")} ${this._fmtTime(a.next_change)}${
          a.next_preset ? `, ${this._presetName(a, a.next_preset)}` : ""
        })`
      : "";
    return `${this._t("until_reeval")}${latest}`;
  }

  /** One line per room: name, rule, now and target; a tap opens the room. */
  _compactRow(stateObj, color) {
    const a = stateObj.attributes;
    const icons = [];
    if (a.heat_demand) icons.push(`<span class="cicon hot" title="${esc(this._t("heating"))}">${this._icon("fire")}</span>`);
    if (a.window_open) icons.push(`<span class="cicon warn" title="${esc(this._t("window"))}">${this._icon("window-open-variant")}</span>`);
    if (a.override) icons.push(`<span class="cicon" title="${esc(`${this._t("override")} ${this._overrideUntil(a)}`)}">${this._icon("hand-back-right-outline")}</span>`);
    return `<button class="crow" data-action="fold" data-key="room-${esc(a.room_id)}" aria-expanded="false" style="--c:${color}">
        <span class="cbar"></span>
        <span class="ctext"><span class="cname">${esc(a.room_name)}</span>
          <span class="crule">${this._eta(a) ? `${esc(this._eta(a))} · ` : ""}${esc(this._label(stateObj))}</span></span>
        ${icons.join("")}
        <span class="ctemp"><span class="cnow">${this._temp(a.current_temperature)}</span><span class="carrow">→</span><b>${this._temp(
          a.target_temperature
        )}</b></span>
        <span class="chev"></span>
      </button>`;
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

  // ------------------------------------------------------------------ history chart
  /** Cached history of the room (fetched in the background, refreshed every 5 minutes). */
  _history(a) {
    const key = a.room_id;
    this._hist = this._hist || {};
    const cached = this._hist[key];
    if (!cached || (!cached.loading && Date.now() - cached.at > 5 * 60 * 1000)) {
      this._fetchHistory(a);
    }
    return cached && cached.temp ? cached : null;
  }

  async _fetchHistory(a) {
    const key = a.room_id;
    const e = a.entities || {};
    const ids = [e.room_temperature, e.target_temperature, e.heat_demand].filter(Boolean);
    const previous = this._hist[key];
    if (!ids.length || !this._hass?.callWS) {
      this._hist[key] = { at: Date.now(), loading: false, temp: [], target: [], heat: [] };
      return;
    }
    this._hist[key] = { ...(previous || {}), at: Date.now(), loading: true };
    const end = new Date();
    const start = new Date(end.getTime() - 24 * 3600 * 1000);
    try {
      const res = await this._hass.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: ids,
        minimal_response: false,
        no_attributes: false,
        significant_changes_only: false,
      });
      const rows = (id) =>
        ((id && res[id]) || [])
          .map((p) => ({ t: (p.lu ?? p.lc) * 1000, s: p.s, a: p.a || {} }))
          .filter((p) => Number.isFinite(p.t));
      this._hist[key] = {
        at: Date.now(),
        loading: false,
        temp: rows(e.room_temperature)
          .map((p) => [p.t, num(p.s)])
          .filter((p) => p[1] !== null),
        target: rows(e.target_temperature).map((p) => ({ t: p.t, v: num(p.s), preset: p.a.preset })),
        heat: rows(e.heat_demand).map((p) => [p.t, p.s === "on"]),
      };
    } catch (err) {
      this._hist[key] = { at: Date.now(), loading: false, temp: [], target: [], heat: [], failed: true };
    }
    const active = this.shadowRoot.activeElement;
    if (this._editing || this._drag || (active && ["INPUT", "SELECT"].includes(active.tagName))) return;
    this._lastKey = "";
    this._render();
  }

  /** Everything drawn by the chart, in time order. */
  _chartData(a) {
    const HOUR = 3600 * 1000;
    const now = Date.now();
    const t0 = now - 24 * HOUR;
    const t1 = now + 12 * HOUR;
    const hist = this._history(a);
    const levels = a.levels || {};

    // Target: history for the past, the plan for the future.
    const segs = [];
    if (hist && hist.target.length) {
      const points = hist.target.filter((p) => p.v !== null);
      points.forEach((p, i) => {
        const s = Math.max(t0, p.t);
        const e = i + 1 < points.length ? Math.min(points[i + 1].t, now) : now;
        if (e > s) segs.push({ s, e, v: p.v, preset: p.preset, future: false });
      });
    }
    const plan = (a.plan || [])
      .map((p) => ({ t: Date.parse(p.at), preset: p.preset }))
      .filter((p) => Number.isFinite(p.t))
      .sort((x, y) => x.t - y.t);
    const upcoming = plan.filter((p) => p.t > now && p.t < t1);
    let cursor = now;
    let preset = a.preset;
    let value = num(a.target_temperature);
    for (const change of upcoming) {
      if (value !== null) segs.push({ s: cursor, e: change.t, v: value, preset, future: true });
      cursor = change.t;
      preset = change.preset;
      value = num(levels[preset]);
    }
    if (value !== null) segs.push({ s: cursor, e: t1, v: value, preset, future: true });
    // Neighbours with the same level form one segment.
    const merged = [];
    for (const sg of segs) {
      const prev = merged[merged.length - 1];
      if (prev && prev.v === sg.v && prev.preset === sg.preset && prev.future === sg.future && prev.e >= sg.s - 1000) {
        prev.e = sg.e;
      } else {
        merged.push({ ...sg });
      }
    }
    segs.length = 0;
    segs.push(...merged);

    const temp = hist ? hist.temp.filter((p) => p[0] >= t0 - HOUR) : [];
    const current = num(a.current_temperature);
    if (current !== null) temp.push([now, current]);

    const heat = [];
    if (hist) {
      let on = null;
      for (const [t, state] of hist.heat) {
        if (state && on === null) on = Math.max(t, t0);
        if (!state && on !== null) {
          heat.push([on, t]);
          on = null;
        }
      }
      if (on !== null) heat.push([on, now]);
    } else if (a.heat_demand) {
      heat.push([now - 5 * 60 * 1000, now]);
    }

    const values = [...segs.map((x) => x.v), ...temp.map((p) => p[1])].filter((v) => v !== null);
    let lo = values.length ? Math.floor(Math.min(...values) - 0.5) : 15;
    let hi = values.length ? Math.ceil(Math.max(...values) + 0.5) : 23;
    if (hi - lo < 4) {
      const mid = (hi + lo) / 2;
      lo = Math.floor(mid - 2);
      hi = lo + 4;
    }
    return { t0, t1, now, segs, temp, heat, lo, hi, loading: !hist };
  }

  /** Visible time window of a chart (zoom); the whole range when not zoomed. */
  _viewOf(room, d) {
    const v = this._view?.[room];
    if (!v) return { v0: d.t0, v1: d.t1, zoomed: false };
    const span = Math.min(d.t1 - d.t0, Math.max(MIN_ZOOM_SPAN, v.v1 - v.v0));
    const v0 = Math.min(d.t1 - span, Math.max(d.t0, v.v0));
    return { v0, v1: v0 + span, zoomed: span < d.t1 - d.t0 - 1000 };
  }

  _setView(room, v0, v1) {
    const d = this._charts?.[room];
    if (!d) return;
    this._view = this._view || {};
    const span = Math.min(d.t1 - d.t0, Math.max(MIN_ZOOM_SPAN, v1 - v0));
    if (span >= d.t1 - d.t0 - 1000) {
      delete this._view[room];
    } else {
      const start = Math.min(d.t1 - span, Math.max(d.t0, v0));
      this._view[room] = { v0: start, v1: start + span };
    }
    this._redrawChart(room);
  }

  /** Zoom by ``factor`` (< 1 = closer) keeping ``center`` in place. */
  _zoom(room, factor, center) {
    const d = this._charts?.[room];
    if (!d) return;
    const { v0, v1 } = this._viewOf(room, d);
    const c = center ?? (Math.min(Math.max(d.now, v0), v1) === d.now ? d.now : (v0 + v1) / 2);
    this._setView(room, c - (c - v0) * factor, c + (v1 - c) * factor);
  }

  _redrawChart(room) {
    const card = this.shadowRoot.querySelector(`[data-chartcard="${CSS.escape(room)}"]`);
    const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
    if (!card || !stateObj) return;
    card.innerHTML = this._timelineHtml(stateObj.attributes, true);
  }

  _timelineHtml(a, innerOnly = false) {
    const d = this._chartData(a);
    if (!d.segs.length && !d.temp.length) return "";
    this._charts = this._charts || {};
    this._charts[a.room_id] = d;
    const view = this._viewOf(a.room_id, d);
    d.v0 = view.v0;
    d.v1 = view.v1;
    if (view.zoomed) {
      // Zoomed in: the temperature scale follows what is visible, for detail.
      const vis = [
        ...d.temp.filter(([t]) => t >= view.v0 - 3600000 && t <= view.v1 + 3600000).map((p) => p[1]),
        ...d.segs.filter((sg) => sg.e >= view.v0 && sg.s <= view.v1).map((sg) => sg.v),
      ].filter((v) => v !== null);
      if (vis.length) {
        let lo = Math.floor((Math.min(...vis) - 0.3) * 2) / 2;
        let hi = Math.ceil((Math.max(...vis) + 0.3) * 2) / 2;
        if (hi - lo < 1) hi = lo + 1;
        d.lo = lo;
        d.hi = hi;
      }
    }
    const W = 1000;
    const H = 100;
    const TOP = 8;
    const BOTTOM = H - 6;
    const x = (t) => ((t - view.v0) / (view.v1 - view.v0)) * W;
    const y = (v) => BOTTOM - ((v - d.lo) / (d.hi - d.lo)) * (BOTTOM - TOP);
    const pct = (t) => (x(t) / W) * 100;
    const gid = `g-${String(a.room_id).replace(/[^a-z0-9]/gi, "")}`;
    const nowX = x(d.now);

    const grid = [d.lo, (d.lo + d.hi) / 2, d.hi]
      .map((v) => `<line x1="0" x2="${W}" y1="${y(v)}" y2="${y(v)}" class="grid"></line>`)
      .join("");
    const heat = d.heat
      .map(
        ([s, e]) => `<rect x="${x(s)}" y="0" width="${Math.max(1.5, x(e) - x(s))}" height="${H}" class="heatband"></rect>
          <rect x="${x(s)}" y="${H - 3}" width="${Math.max(1.5, x(e) - x(s))}" height="3" class="heatbar"></rect>`
      )
      .join("");
    const segs = d.segs
      .map((sg) => {
        const c = PRESET_COLORS[sg.preset] || "var(--ac-accent)";
        const x0 = x(sg.s);
        const x1 = x(sg.e);
        const yy = y(sg.v);
        return `<rect x="${x0}" y="${yy}" width="${Math.max(0, x1 - x0)}" height="${H - yy}" fill="${c}"
            class="tarea ${sg.future ? "future" : ""}"></rect>
          <line x1="${x0}" x2="${x1}" y1="${yy}" y2="${yy}" stroke="${c}" class="tline ${sg.future ? "future" : ""}"></line>`;
      })
      .join("");
    const steps = d.segs
      .slice(1)
      .map((sg, i) => {
        const prev = d.segs[i];
        return `<line x1="${x(sg.s)}" x2="${x(sg.s)}" y1="${y(prev.v)}" y2="${y(sg.v)}" class="tstep"></line>`;
      })
      .join("");
    let tempPath = "";
    let tempArea = "";
    if (d.temp.length > 1) {
      const pts = d.temp.map(([t, v]) => `${x(Math.max(t, d.t0)).toFixed(1)} ${y(v).toFixed(1)}`);
      tempPath = `M${pts.join(" L")}`;
      tempArea = `${tempPath} L${x(d.temp[d.temp.length - 1][0]).toFixed(1)} ${H} L${x(
        Math.max(d.temp[0][0], d.t0)
      ).toFixed(1)} ${H} Z`;
    }
    const last = d.temp.length ? d.temp[d.temp.length - 1] : null;

    // Labels of the levels (HTML, so the text is not stretched).
    const visible = (sg) => [Math.max(0, x(sg.s)), Math.min(W, x(sg.e))];
    const labels = d.segs
      .filter((sg) => {
        const [xs, xe] = visible(sg);
        return xe - xs >= 85;
      })
      .map((sg) => {
        const [xs, xe] = visible(sg);
        const mid = Math.min(0.92, Math.max(0.08, (xs + xe) / 2 / W));
        return `<span class="lvl ${sg.future ? "future" : ""}" style="left:${mid * 100}%;top:${
          (y(sg.v) / H) * 100
        }%">${esc(this._presetName(a, sg.preset) || "")} ${sg.v}°</span>`;
      })
      .join("");
    const yLabels = [d.lo, d.hi]
      .map((v) => `<span style="top:${(y(v) / H) * 100}%">${v}°</span>`)
      .join("");

    // Ticks adapt to the zoom: from every 6 hours down to every 5 minutes.
    const span = view.v1 - view.v0;
    const stepMin = [5, 10, 15, 30, 60, 120, 180, 360].find((m) => span / (m * 60000) <= 7) || 360;
    const ticks = [];
    const first = new Date(view.v0);
    first.setSeconds(0, 0);
    first.setMinutes(Math.ceil(first.getMinutes() / Math.min(stepMin, 60)) * Math.min(stepMin, 60));
    for (let t = first.getTime(); t <= view.v1; t += 60000 * Math.min(stepMin, 60)) {
      const dt = new Date(t);
      const minutes = dt.getHours() * 60 + dt.getMinutes();
      if (minutes % stepMin !== 0) continue;
      const label =
        minutes === 0
          ? dt.toLocaleDateString(this._lang(), { weekday: "short" })
          : dt.toLocaleTimeString(this._lang(), { hour: "2-digit", minute: "2-digit" });
      ticks.push(`<span style="left:${pct(t)}%">${esc(label)}</span>`);
    }
    const fmt = (t) => new Date(t).toLocaleTimeString(this._lang(), { hour: "2-digit", minute: "2-digit" });
    const zoomBtn = (zoom, label, title, active = false) =>
      `<button class="zbtn ${active ? "active" : ""}" data-action="zoom" data-zoom="${zoom}" data-room="${esc(
        a.room_id
      )}" title="${esc(title)}" aria-label="${esc(title)}">${label}</button>`;
    const spanH = Math.round(span / 3600000);
    const zoombar = `<div class="zoombar">
        <span class="zrange">${view.zoomed ? `${esc(fmt(view.v0))} – ${esc(fmt(view.v1))}` : esc(this._t("chart_label"))}</span>
        <span class="zbtns">
          ${zoomBtn("1h", "1h", this._t("zoom_1h"), view.zoomed && spanH === 1)}
          ${zoomBtn("6h", "6h", this._t("zoom_6h"), view.zoomed && spanH === 6)}
          ${zoomBtn("out", "−", this._t("zoom_out"))}
          ${zoomBtn("in", "+", this._t("zoom_in"))}
          ${view.zoomed ? zoomBtn("reset", "⤢", this._t("zoom_reset")) : ""}
        </span>
      </div>`;

    const next = a.next_change
      ? `<span>${this._t("next")}: <b>${esc(this._fmtTime(a.next_change))}</b> → ${esc(
          this._presetName(a, a.next_preset)
        )}</span>`
      : "";
    const nowIn = d.now >= view.v0 && d.now <= view.v1;
    const inner = `
        ${zoombar}
        <div class="hchart ${view.zoomed ? "zoomed" : ""}" data-chart="${esc(a.room_id)}">
          <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(this._t("chart_label"))}">
            <defs><linearGradient id="${gid}" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stop-color="var(--ac-accent)" stop-opacity="0.22"></stop>
              <stop offset="1" stop-color="var(--ac-accent)" stop-opacity="0"></stop>
            </linearGradient></defs>
            <rect x="${Math.min(W, Math.max(0, nowX))}" y="0" width="${W - Math.min(W, Math.max(0, nowX))}" height="${H}" class="futurebg"></rect>
            ${grid}${heat}${segs}${steps}
            ${tempArea ? `<path d="${tempArea}" fill="url(#${gid})" class="tempfill"></path>` : ""}
            ${tempPath ? `<path d="${tempPath}" class="templine"></path>` : ""}
            <line x1="${nowX}" x2="${nowX}" y1="0" y2="${H}" class="now"></line>
          </svg>
          <div class="overlay">
            ${labels}
            <div class="ylabels">${yLabels}</div>
            ${nowIn ? `<span class="nowlabel" style="left:${pct(d.now)}%">${this._t("now_tag")}</span>` : ""}
            ${
              last && last[0] >= view.v0 && last[0] <= view.v1
                ? `<span class="nowdot" style="left:${pct(last[0])}%;top:${(y(last[1]) / H) * 100}%"></span>`
                : ""
            }
            <div class="cross" hidden></div>
            <div class="tip" hidden></div>
          </div>
        </div>
        <div class="ticks">${ticks.join("")}</div>
        <div class="readout">
          <span class="lg"><i class="lg-temp"></i>${this._t("legend_temp")}</span>
          <span class="lg"><i class="lg-target"></i>${this._t("legend_target")}</span>
          <span class="lg"><i class="lg-heat"></i>${this._t("legend_heat")}</span>
          ${d.loading ? `<span class="muted">${this._t("loading")}</span>` : ""}
        </div>
        <div class="meta"><span>${this._t("today")}: <b>${esc(a.profile || "–")}</b></span>${next}</div>`;
    if (innerOnly) return inner;
    return `<div class="chart-card" data-chartcard="${esc(a.room_id)}">${inner}</div>`;
  }

  /** Crosshair and values under the pointer (the legend stays visible). */
  _chartHover(ev) {
    const chart = ev.target.closest?.(".hchart");
    if (!chart) return;
    const room = chart.dataset.chart;
    const d = this._charts?.[room];
    const cross = chart.querySelector(".cross");
    const tip = chart.querySelector(".tip");
    if (!d || !cross || !tip) return;
    if (ev.type === "pointerleave" && ev.target !== chart) return;
    if (ev.type === "pointerleave") {
      cross.hidden = true;
      tip.hidden = true;
      return;
    }
    const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
    const a = stateObj?.attributes || {};
    const rect = chart.getBoundingClientRect();
    const f = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
    const t = d.v0 + f * (d.v1 - d.v0);
    let temp = null;
    for (const [pt, v] of d.temp) {
      if (pt <= t) temp = v;
      else break;
    }
    const seg = d.segs.find((sg) => sg.s <= t && t < sg.e);
    const heating = d.heat.some(([s, e]) => s <= t && t <= e);
    const time = new Date(t).toLocaleString(this._lang(), { weekday: "short", hour: "2-digit", minute: "2-digit" });
    const rows = [`<b>${esc(time)}</b>`];
    if (t <= d.now && temp !== null) rows.push(`<span><i class="lg-temp"></i>${temp.toFixed(1)}°</span>`);
    if (seg) {
      rows.push(
        `<span><i style="background:${PRESET_COLORS[seg.preset] || "var(--ac-accent)"}"></i>${
          seg.future ? this._t("planned") : this._t("target_tag")
        } ${seg.v}° · ${esc(this._presetName(a, seg.preset) || "")}</span>`
      );
    }
    if (heating) rows.push(`<span class="hotword"><i class="lg-heat"></i>${this._t("heating")}</span>`);
    cross.hidden = false;
    cross.style.left = `${f * 100}%`;
    tip.hidden = false;
    tip.innerHTML = rows.join("");
    tip.style.left = `${f * 100}%`;
    tip.style.transform = f > 0.6 ? "translateX(calc(-100% - 10px))" : "translateX(10px)";
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
        ${runtime ? `<div>${this._runtimeButton(e.heating_runtime, "dt")}</div>` : ""}
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
              <div class="sbar ro">${this._barInner(a, name, slots, false)}</div>
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
              <input type="time" step="300" data-profile="${esc(name)}" data-index="${i}" data-field="time" value="${esc(slot.time)}"
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
              ${this._copySelect(name)}
              ${this._btn(this._t("remove_profile"), `data-action="del-profile" data-profile="${esc(name)}"`, {
                icon: "delete-outline",
                kind: "danger",
              })}</div>
            <div class="sbar" data-bar="${esc(name)}">${this._barInner(a, name, slots, true)}</div>
            <div class="bar-ticks"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></div>
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
        <p class="hint">${this._t("drag_hint")}</p>
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

  /** Day bar of a profile; in the editor every start time has a handle that can be dragged. */
  _barInner(a, name, slots, editable) {
    if (!slots || !slots.length) return "";
    const segs = this._segments(slots)
      .map((sg) => {
        const w = ((sg.end - sg.start) / 1440) * 100;
        const label = w >= 14 ? esc(this._presetName(a, sg.preset)) : "";
        return `<div class="sseg" style="left:${(sg.start / 1440) * 100}%;width:${w}%;--c:${
          PRESET_COLORS[sg.preset] || "var(--ac-accent)"
        }" title="${esc(this._presetName(a, sg.preset))} ${hhmm(sg.start)}–${hhmm(sg.end % 1440)}"><span>${label}</span></div>`;
      })
      .join("");
    if (!editable) return segs;
    const handles = slots
      .map((slot, i) => {
        const m = toMinutes(slot.time);
        const dragging = this._drag && this._drag.profile === name && this._drag.index === i;
        return `<div class="handle ${dragging ? "dragging" : ""}" style="left:${(m / 1440) * 100}%" tabindex="0" role="slider"
            aria-label="${esc(this._t("starts"))} ${esc(this._presetName(a, slot.preset))}" aria-valuemin="0" aria-valuemax="1439"
            aria-valuenow="${m}" aria-valuetext="${esc(slot.time)}" data-handle="1" data-profile="${esc(name)}" data-index="${i}">
            <span class="htime">${esc(slot.time)}</span></div>`;
      })
      .join("");
    return segs + handles;
  }

  /** "Copy over…" select of the schedule editor. */
  _copySelect(name) {
    const existing = Object.keys(this._draft || {});
    const targets = [...existing, ...["workday", "weekend", ...WEEKDAY_KEYS].filter((p) => !existing.includes(p))]
      .filter((p) => p !== name);
    const label = (p) => {
      const day = WEEKDAY_KEYS.indexOf(p);
      const suffix = day >= 0 ? ` (${this._weekdayName(day)})` : "";
      return `${p}${suffix}${existing.includes(p) ? "" : ` – ${this._t("new_profile")}`}`;
    };
    return `<select class="copysel" data-copy="${esc(name)}" aria-label="${esc(this._t("copy_to"))}">
        <option value="">${esc(this._t("copy_to"))}</option>
        ${targets.map((p) => `<option value="${esc(p)}">${esc(label(p))}</option>`).join("")}
      </select>`;
  }

  /** Limits of a handle: it stays between its neighbours (5 minutes apart). */
  _handleLimits(slots, index) {
    const order = slots
      .map((slot, i) => ({ i, m: toMinutes(slot.time) }))
      .sort((x, y) => x.m - y.m);
    const pos = order.findIndex((o) => o.i === index);
    const min = pos > 0 ? order[pos - 1].m + 5 : 0;
    const max = pos + 1 < order.length ? order[pos + 1].m - 5 : 1435;
    return [min, max];
  }

  _moveHandle(profile, index, minutes) {
    const slots = this._draft?.[profile];
    if (!slots || !slots[index]) return false;
    const [min, max] = this._handleLimits(slots, index);
    const value = Math.min(max, Math.max(min, minutes));
    if (hhmm(value) === slots[index].time) return false;
    slots[index].time = hhmm(value);
    return true;
  }

  _chartPointerDown(ev) {
    const chart = ev.target.closest?.(".hchart");
    if (!chart) return false;
    const room = chart.dataset.chart;
    this._ptrs = this._ptrs || new Map();
    this._ptrs.set(ev.pointerId, ev.clientX);
    const d = this._charts?.[room];
    if (!d) return true;
    const card = chart.closest(".chart-card");
    try {
      card.setPointerCapture(ev.pointerId);
    } catch (err) {
      /* ignore */
    }
    const xs = [...this._ptrs.values()];
    this._pan = {
      room,
      card,
      startX: xs.length > 1 ? (xs[0] + xs[1]) / 2 : ev.clientX,
      dist: xs.length > 1 ? Math.abs(xs[0] - xs[1]) : 0,
      v0: d.v0,
      v1: d.v1,
      moved: false,
    };
    return true;
  }

  _chartPointerMove(ev) {
    const p = this._pan;
    if (!p || !this._ptrs?.has(ev.pointerId)) return false;
    this._ptrs.set(ev.pointerId, ev.clientX);
    const d = this._charts?.[p.room];
    const chart = p.card.querySelector(".hchart");
    if (!d || !chart) return true;
    const rect = chart.getBoundingClientRect();
    const span = p.v1 - p.v0;
    const xs = [...this._ptrs.values()];
    if (xs.length > 1 && p.dist > 10) {
      // Pinch: zoom around the middle of the two fingers.
      const dist = Math.abs(xs[0] - xs[1]);
      const factor = p.dist / Math.max(dist, 10);
      const center = p.v0 + ((p.startX - rect.left) / rect.width) * span;
      p.moved = true;
      this._setView(p.room, center - (center - p.v0) * factor, center + (p.v1 - center) * factor);
      return true;
    }
    const dx = ev.clientX - p.startX;
    if (Math.abs(dx) > 4) p.moved = true;
    if (p.moved && this._view?.[p.room]) {
      const shift = (-dx / rect.width) * span;
      this._setView(p.room, p.v0 + shift, p.v1 + shift);
      return true;
    }
    return false;
  }

  _chartPointerUp(ev) {
    if (!this._ptrs) return;
    this._ptrs.delete(ev.pointerId);
    const p = this._pan;
    if (!this._ptrs.size) this._pan = null;
    else if (p) {
      // One finger left after a pinch: start a new pan from here.
      const d = this._charts?.[p.room];
      const [x] = [...this._ptrs.values()];
      this._pan = { ...p, startX: x, dist: 0, v0: d?.v0 ?? p.v0, v1: d?.v1 ?? p.v1 };
    }
    const chart = p?.card?.querySelector(".hchart");
    if (p && !p.moved && chart) this._chartHover({ type: "pointermove", clientX: ev.clientX, target: chart });
  }

  _chartWheel(ev) {
    const chart = ev.target.closest?.(".hchart");
    // Only pinch on a touchpad or Ctrl + wheel zoom, so the page still scrolls normally.
    if (!chart || !(ev.ctrlKey || ev.metaKey)) return;
    ev.preventDefault();
    const d = this._charts?.[chart.dataset.chart];
    if (!d) return;
    const rect = chart.getBoundingClientRect();
    const center = d.v0 + ((ev.clientX - rect.left) / rect.width) * (d.v1 - d.v0);
    this._zoom(chart.dataset.chart, ev.deltaY > 0 ? 1.25 : 0.8, center);
  }

  _chartDblClick(ev) {
    // With the pointer captured by the chart card the event target is the card itself.
    const chart = ev.target.closest?.(".hchart") || ev.target.closest?.(".chart-card")?.querySelector(".hchart");
    if (ev.target.closest?.(".zoombar")) return;
    if (!chart) return;
    const d = this._charts?.[chart.dataset.chart];
    if (!d) return;
    const rect = chart.getBoundingClientRect();
    const center = d.v0 + ((ev.clientX - rect.left) / rect.width) * (d.v1 - d.v0);
    this._zoom(chart.dataset.chart, 0.4, center);
  }

  _pointerDown(ev) {
    if (this._chartPointerDown(ev)) return;
    const handle = ev.target.closest?.("[data-handle]");
    if (!handle || !this._draft) return;
    ev.preventDefault();
    const bar = handle.closest(".sbar");
    this._drag = { profile: handle.dataset.profile, index: Number(handle.dataset.index), bar };
    try {
      bar.setPointerCapture(ev.pointerId);
    } catch (err) {
      /* ignore */
    }
    handle.classList.add("dragging");
  }

  _pointerMove(ev) {
    if (!this._drag) {
      if (this._chartPointerMove(ev)) {
        const tip = this._pan?.card?.querySelector(".tip");
        if (tip) tip.hidden = true;
        return;
      }
      const chart = ev.target.closest?.(".hchart") || this._pan?.card?.querySelector(".hchart");
      if (chart) this._chartHover({ type: ev.type, clientX: ev.clientX, target: chart });
      return;
    }
    const { profile, index, bar } = this._drag;
    const rect = bar.getBoundingClientRect();
    const f = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
    const minutes = Math.round((f * 1440) / 5) * 5;
    if (this._moveHandle(profile, index, minutes)) {
      const stateObj = this._rooms().find((s) => s.attributes.room_id === this._editing);
      bar.innerHTML = this._barInner(stateObj?.attributes || {}, profile, this._draft[profile], true);
    }
  }

  _pointerUp(ev) {
    if (ev) this._chartPointerUp(ev);
    if (!this._drag) return;
    this._drag = null;
    this._render();
  }

  _keyDown(ev) {
    const handle = ev.target.closest?.("[data-handle]");
    if (!handle || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(ev.key)) return;
    ev.preventDefault();
    const { profile } = handle.dataset;
    const index = Number(handle.dataset.index);
    const step = (ev.shiftKey ? 60 : 5) * (["ArrowLeft", "ArrowDown"].includes(ev.key) ? -1 : 1);
    const current = toMinutes(this._draft[profile][index].time);
    if (this._moveHandle(profile, index, current + step)) {
      this._render();
      this.shadowRoot
        .querySelector(`[data-handle][data-profile="${CSS.escape(profile)}"][data-index="${index}"]`)
        ?.focus();
    }
  }

  // ------------------------------------------------------------------ heating time per period
  _period() {
    const p = this._runtimePeriod || this._config.runtime_period || "day";
    return RUNTIME_PERIODS.includes(p) ? p : "day";
  }

  /** Hours of heating in the current day / week / month, from the long-term statistics. */
  _runtimeValue(entityId) {
    const period = this._period();
    const key = `${entityId}|${period}`;
    this._runtime = this._runtime || {};
    const cached = this._runtime[key];
    if (!cached || (!cached.loading && Date.now() - cached.at > 5 * 60 * 1000)) {
      this._fetchRuntime(entityId, period, key);
    }
    return cached && !cached.failed ? cached.value : null;
  }

  async _fetchRuntime(entityId, period, key) {
    this._runtime[key] = { ...(this._runtime[key] || {}), at: Date.now(), loading: true };
    if (!this._hass?.callWS) return;
    let value = null;
    let failed = false;
    try {
      const res = await this._hass.callWS({
        type: "recorder/statistic_during_period",
        statistic_id: entityId,
        calendar: { period },
        types: ["change"],
      });
      value = num(res?.change) ?? 0;
    } catch (err) {
      failed = true;
    }
    this._runtime[key] = { at: Date.now(), loading: false, value, failed };
    const active = this.shadowRoot.activeElement;
    if (this._editing || this._drag || this._pan || (active && ["INPUT", "SELECT"].includes(active.tagName))) return;
    this._lastKey = "";
    this._render();
  }

  _runtimeText(entityId) {
    const value = this._runtimeValue(entityId);
    if (value === null) return "–";
    const h = Math.floor(value);
    const m = Math.round((value - h) * 60);
    return h ? `${h} h ${String(m).padStart(2, "0")} min` : `${m} min`;
  }

  /** "Heating time · today" that changes the period when tapped. */
  _runtimeButton(entityId, kind) {
    const label = `${this._t("runtime")} · ${this._t(`period_${this._period()}`)}`;
    const value = esc(this._runtimeText(entityId));
    const title = esc(this._t("period_hint"));
    if (kind === "dt") {
      return `<button class="period" data-action="period" title="${title}"><dt>${esc(label)}</dt><dd>${value}</dd></button>`;
    }
    return `<button class="stat period" data-action="period" title="${title}"><span class="k">${esc(
      label
    )}</span><span class="v">${value}</span></button>`;
  }

  _runtimeStat(entityId) {
    return this._runtimeButton(entityId, "stat");
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
    } else if (d.copy !== undefined && this._draft?.[d.copy]) {
      if (el.value) this._draft[el.value] = JSON.parse(JSON.stringify(this._draft[d.copy]));
      this._render();
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
      case "period": {
        const next = RUNTIME_PERIODS[(RUNTIME_PERIODS.indexOf(this._period()) + 1) % RUNTIME_PERIODS.length];
        this._runtimePeriod = next;
        break;
      }
      case "zoom": {
        const d = this._charts?.[room];
        if (!d) return;
        const z = el.dataset.zoom;
        if (z === "in") this._zoom(room, 0.5);
        else if (z === "out") this._zoom(room, 2);
        else if (z === "reset") this._setView(room, d.t0, d.t1);
        else {
          const span = (z === "1h" ? 1 : 6) * 3600000;
          const end = Math.min(d.t1, Math.max(d.now + span * 0.15, d.t0 + span));
          this._setView(room, end - span, end);
        }
        return;
      }
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
  button.period { font: inherit; color: inherit; text-align: left; cursor: pointer; border: none; background: none; padding: 0; }
  .details button.period { width: 100%; }
  .details button.period dt { font-size: 0.75em; color: var(--ac-muted); }
  .details button.period dd { margin: 2px 0 0; font-variant-numeric: tabular-nums; font-weight: 500; }
  button.period:hover .k, button.period:hover dt { text-decoration: underline dotted; }
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
  .tval .eta { font-size: 0.68em; color: var(--ac-muted); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .decision { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .reason { margin: 0; color: var(--ac-muted); font-size: 0.9em; }
  .chart-card { border-radius: 14px; background: var(--ac-surface); padding: 12px 12px 10px;
    box-shadow: inset 0 0 0 1px var(--ac-line); display: flex; flex-direction: column; gap: 4px; }
  .hchart { position: relative; height: 150px; touch-action: pan-y; cursor: crosshair; user-select: none; }
  .hchart svg { width: 100%; height: 100%; display: block; overflow: hidden; }
  .hchart.zoomed { cursor: grab; }
  .hchart.zoomed:active { cursor: grabbing; }
  .zoombar { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin: -2px 0 10px; }
  .zrange { font-size: 0.78em; color: var(--ac-muted); font-variant-numeric: tabular-nums; }
  .zbtns { display: inline-flex; gap: 2px; padding: 2px; border-radius: 9px; background: var(--ac-surface-2); }
  .zbtn { font: inherit; font-size: 0.78em; min-width: 30px; height: 26px; padding: 0 8px; border: none; border-radius: 7px;
    background: none; color: var(--primary-text-color); cursor: pointer; font-variant-numeric: tabular-nums; }
  .zbtn:hover { background: var(--card-background-color); }
  .zbtn.active { background: var(--card-background-color); color: var(--ac-accent); font-weight: 600;
    box-shadow: 0 1px 2px rgba(0,0,0,.15); }
  .hchart .grid { stroke: var(--ac-line); stroke-width: 1; stroke-dasharray: 2 4; vector-effect: non-scaling-stroke; }
  .hchart .futurebg { fill: var(--primary-text-color); opacity: 0.035; }
  .hchart .heatband { fill: var(--ac-hot); opacity: 0.09; }
  .hchart .heatbar { fill: var(--ac-hot); opacity: 0.85; }
  .hchart .tarea { opacity: 0.11; }
  .hchart .tarea.future { opacity: 0.06; }
  .hchart .tline { stroke-width: 2.5; vector-effect: non-scaling-stroke; stroke-linecap: round; }
  .hchart .tline.future { stroke-dasharray: 5 4; opacity: 0.8; }
  .hchart .tstep { stroke: var(--primary-text-color); opacity: 0.18; stroke-width: 1; vector-effect: non-scaling-stroke; }
  .hchart .templine { fill: none; stroke: var(--ac-accent); stroke-width: 2.25; vector-effect: non-scaling-stroke;
    stroke-linejoin: round; stroke-linecap: round; }
  .hchart .now { stroke: var(--primary-text-color); stroke-width: 1.25; opacity: 0.55; stroke-dasharray: 3 3; vector-effect: non-scaling-stroke; }
  .overlay { position: absolute; inset: 0; pointer-events: none; }
  .overlay .lvl { position: absolute; transform: translate(-50%, calc(-100% - 3px)); font-size: 0.72em; white-space: nowrap;
    padding: 1px 6px; border-radius: 6px; background: color-mix(in srgb, var(--card-background-color) 75%, transparent);
    color: var(--primary-text-color); }
  .overlay .lvl.future { color: var(--ac-muted); }
  .ylabels span { position: absolute; right: 0; transform: translateY(-50%); font-size: 0.68em; color: var(--ac-muted);
    font-variant-numeric: tabular-nums; background: color-mix(in srgb, var(--card-background-color) 70%, transparent);
    padding: 0 3px; border-radius: 4px; }
  .nowlabel { position: absolute; top: -2px; transform: translate(-50%, -100%); font-size: 0.65em; color: var(--ac-muted);
    text-transform: uppercase; letter-spacing: 0.06em; }
  .nowdot { position: absolute; width: 9px; height: 9px; border-radius: 50%; background: var(--ac-accent);
    transform: translate(-50%, -50%); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ac-accent) 25%, transparent); }
  .cross { position: absolute; top: 0; bottom: 0; width: 0; border-left: 1px solid var(--primary-text-color); opacity: 0.45; }
  .ticks { position: relative; height: 14px; font-size: 0.68em; color: var(--ac-muted); }
  .ticks span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
  .readout { display: flex; gap: 14px; flex-wrap: wrap; align-items: center; font-size: 0.78em; color: var(--ac-muted);
    min-height: 20px; font-variant-numeric: tabular-nums; }
  .tip { position: absolute; top: 4px; display: flex; flex-direction: column; gap: 2px; padding: 6px 9px; border-radius: 10px;
    font-size: 0.75em; white-space: nowrap; font-variant-numeric: tabular-nums; color: var(--primary-text-color);
    background: color-mix(in srgb, var(--card-background-color) 92%, transparent); box-shadow: 0 2px 10px rgba(0,0,0,.18);
    border: 1px solid var(--ac-line); z-index: 3; }
  .tip span { display: inline-flex; align-items: center; gap: 6px; }
  .tip i { display: inline-block; width: 10px; height: 3px; border-radius: 2px; }
  .tip .hotword { color: var(--ac-hot); font-weight: 600; }
  .lg { display: inline-flex; align-items: center; gap: 6px; }
  .lg i { display: inline-block; width: 14px; height: 3px; border-radius: 2px; }
  .lg-temp { background: var(--ac-accent); }
  .lg-target { background: linear-gradient(90deg, #f08c00, #5f6fd1); }
  .lg-heat { background: var(--ac-hot); height: 8px !important; opacity: 0.8; }
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
  /* schedule bars */
  .sbar { position: relative; height: 26px; border-radius: 8px; background: var(--ac-surface-2); overflow: visible; touch-action: none; }
  .sbar.ro { height: 10px; border-radius: 5px; overflow: hidden; }
  .sseg { position: absolute; top: 0; bottom: 0; background: color-mix(in srgb, var(--c) 70%, transparent);
    display: flex; align-items: center; justify-content: center; overflow: hidden; }
  .sseg:first-child { border-radius: 8px 0 0 8px; }
  .sseg span { font-size: 0.7em; color: #fff; text-shadow: 0 1px 1px rgba(0,0,0,.35); white-space: nowrap; }
  .handle { position: absolute; top: -5px; bottom: -5px; width: 22px; transform: translateX(-50%); cursor: ew-resize;
    display: flex; justify-content: center; z-index: 2; outline: none; }
  .handle::before { content: ""; width: 6px; border-radius: 3px; background: var(--card-background-color);
    box-shadow: 0 0 0 1.5px var(--primary-text-color), 0 1px 4px rgba(0,0,0,.3); }
  .handle .htime { position: absolute; bottom: calc(100% + 4px); font-size: 0.72em; padding: 2px 6px; border-radius: 6px;
    background: var(--primary-text-color); color: var(--card-background-color); white-space: nowrap; opacity: 0;
    transition: opacity .12s; pointer-events: none; font-variant-numeric: tabular-nums; }
  .handle:hover .htime, .handle:focus-visible .htime, .handle.dragging .htime { opacity: 1; }
  .handle:focus-visible::before, .handle.dragging::before { box-shadow: 0 0 0 2px var(--ac-accent), 0 1px 6px rgba(0,0,0,.35); }
  .bar-ticks { display: flex; justify-content: space-between; font-size: 0.66em; color: var(--ac-muted); margin-top: -2px; }
  .copysel { font-size: 0.85em; min-height: 32px; padding: 4px 8px; }

  /* compact */
  ha-card.compact { gap: 8px; }
  .rooms-list { display: flex; flex-direction: column; gap: 6px; }
  .crow { display: flex; align-items: center; gap: 10px; width: 100%; font: inherit; color: var(--primary-text-color);
    background: var(--ac-surface); border: none; border-radius: 12px; padding: 10px 12px; cursor: pointer; text-align: left;
    transition: background .15s; min-height: 48px; box-sizing: border-box; }
  .crow:hover { background: var(--ac-surface-2); }
  .crow ha-icon { --mdc-icon-size: 20px; color: var(--ac-muted); }
  .crow .cbar { width: 4px; align-self: stretch; border-radius: 2px; background: var(--c); flex: none; }
  .crow .ctext { display: flex; flex-direction: column; min-width: 0; flex: 1 1 auto; }
  .crow .cname { font-weight: 600; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .house-row .cname { flex: 0 1 auto; }
  .crow .crule { font-size: 0.78em; color: var(--ac-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .crow .ctemp { margin-left: auto; display: inline-flex; align-items: baseline; gap: 5px; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .crow .cnow { font-size: 1.15em; font-weight: 300; }
  .crow .carrow { color: var(--ac-muted); font-size: 0.85em; }
  .crow .chev { margin-left: 2px; }
  .cicon ha-icon { --mdc-icon-size: 18px; }
  .cicon.hot ha-icon { color: var(--ac-hot); }
  .cicon.warn ha-icon { color: var(--ac-warn); }
  .house-row .pill { flex: none; }
  .house-row .ctemp { font-size: 0.85em; }
  .compact .block.room { border-color: color-mix(in srgb, var(--ac-accent) 35%, var(--ac-line)); }
  @media (max-width: 420px) { .house-row .pill + .pill { display: none; } }

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
      { name: "compact", selector: { boolean: {} } },
    ],
  },
  {
    name: "runtime_period",
    selector: {
      select: {
        mode: "dropdown",
        options: [
          { value: "day", label: "Day / Zi" },
          { value: "week", label: "Week / Săptămână" },
          { value: "month", label: "Month / Lună" },
        ],
      },
    },
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
    compact: "Compact: one row per room, tap to open",
    runtime_period: "Heating time shown for (tap the value in the card to change it)",
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
    compact: "Compact: un rând pe cameră, se deschide la atingere",
    runtime_period: "Timpul de încălzire afișat pentru (se schimbă și apăsând valoarea în card)",
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
