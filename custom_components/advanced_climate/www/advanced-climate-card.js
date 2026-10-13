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

const CARD_VERSION = "1.2.1";

const PRESET_COLORS = {
  comfort: "#d9480f",
  home: "#f08c00",
  activity: "#e0a030",
  eco: "#2f9e8f",
  sleep: "#5f6fd1",
  away: "#8a96a3",
};

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
    level_temps_gt: "Set in Generic Thermostat",
  },
  ro: {
    title: "Încălzire",
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
    level_temps_gt: "Setate în Generic Thermostat",
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

  _toggle(entityId, label) {
    const s = this._state(entityId);
    if (!s) return "";
    const on = s.state === "on";
    return `<button class="toggle ${on ? "on" : ""}" role="switch" aria-checked="${on}"
      data-action="toggle" data-entity="${esc(entityId)}"><span class="knob"></span>${esc(
      label
    )}</button>`;
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
        return `<span class="person ${esc(cls || "unknown")}">${esc(name)}</span>`;
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
      ? ` <span class="muted">${this._t("until")} ${esc(this._fmtTime(guest.attributes.until))}</span>`
      : "";

    return `
      <section class="house">
        <div class="house-head">
          <div>
            <div class="house-name">${esc(house.name || "")}</div>
            <div class="presence"><span class="presence-state ${esc(presence?.state)}">${esc(
      this._label(presence)
    )}</span>${presence?.attributes?.arriving ? `<span class="muted">↩</span>` : ""}${personList}</div>
          </div>
          <div class="stats">
            ${stat(this._t("outdoor"), this._temp(outdoor?.state))}
            ${stat(this._t("season"), onOff(season))}
            ${cutoff?.state === "on" ? stat(this._t("cutoff"), this._t("on"), "warn") : ""}
            ${stat(this._t("demand"), onOff(demand), demand?.state === "on" ? "hot" : "")}
            ${runtime ? stat(this._t("runtime"), `${num(runtime.state)?.toFixed(1) ?? "–"} h`) : ""}
          </div>
        </div>
        <div class="row wrap">
          <div class="segmented" role="group" aria-label="${esc(this._t("mode"))}">${modes}</div>
          <div class="toggles">${this._toggle(e.pause, this._t("pause"))}${this._toggle(
      e.guest_mode,
      this._t("guests")
    )}${guestUntil}</div>
        </div>
        <details class="fold" data-fold="vac-${esc(house.id)}" ${this._open[`vac-${house.id}`] ? "open" : ""}>
          <summary>${this._t("vacation")}${
      vStart && num(Date.parse(vStart.state))
        ? ` <span class="muted">${esc(this._fmtTime(vStart.state))} – ${esc(this._fmtTime(vEnd?.state))}</span>`
        : ""
    }</summary>
          <div class="row wrap">
            <label class="field">${this._t("from")}<input type="datetime-local" data-vac="start" data-house="${esc(
      house.id
    )}" value="${esc(toLocalInput(vStart?.state))}"></label>
            <label class="field">${this._t("to")}<input type="datetime-local" data-vac="end" data-house="${esc(
      house.id
    )}" value="${esc(toLocalInput(vEnd?.state))}"></label>
            <button class="primary" data-action="vacation" data-house="${esc(house.id)}">${this._t(
      "set_vacation"
    )}</button>
            ${
              e.clear_vacation
                ? `<button class="link" data-action="press" data-entity="${esc(e.clear_vacation)}">${this._t(
                    "clear_vacation"
                  )}</button>`
                : ""
            }
          </div>
          ${this._error[`vac-${house.id}`] ? `<p class="error">${esc(this._error[`vac-${house.id}`])}</p>` : ""}
        </details>
        <div class="row wrap actions">
          ${
            e.reevaluate
              ? `<button class="link" data-action="press" data-entity="${esc(e.reevaluate)}">${this._t(
                  "reevaluate"
                )}</button>`
              : ""
          }
          ${
            e.clear_overrides
              ? `<button class="link" data-action="press" data-entity="${esc(e.clear_overrides)}">${this._t(
                  "clear_all"
                )}</button>`
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
    if (a.heat_demand) badges.push(`<span class="badge hot">${this._t("heating")}</span>`);
    if (a.window_open) badges.push(`<span class="badge warn">${this._t("window")}</span>`);
    if (a.override) {
      const until = a.override.until
        ? `${this._t("until")} ${this._fmtTime(a.override.until)}`
        : this._t("until_change");
      const prefix = stateObj.state === "manual_override" ? "" : `${this._t("override")} `;
      badges.push(`<span class="badge">${esc(prefix + until)}</span>`);
    }

    const head = `
      <button class="room-head" data-action="fold" data-key="room-${esc(key)}" aria-expanded="${!folded}">
        <span class="room-name">${esc(a.room_name)}</span>
        <span class="temps"><span class="current">${this._temp(a.current_temperature)}</span>
          <span class="target" style="--c:${color}">${this._temp(a.target_temperature)}</span></span>
      </button>
      <div class="decision"><span class="rule" style="--c:${color}">${esc(this._label(stateObj))}</span>${badges.join(
      ""
    )}</div>`;

    if (folded) return `<section class="room">${head}</section>`;

    const parts = [
      `<p class="reason">${esc(a.reason || "")}</p>`,
      cfg.show_timeline ? this._timelineHtml(a) : "",
      this._controlsHtml(a, e),
      cfg.show_quick_override ? this._quickHtml(a) : "",
      cfg.show_levels ? this._levelsHtml(a, e) : "",
      cfg.show_details ? this._detailsHtml(a, e) : "",
      cfg.show_schedule_editor ? this._scheduleHtml(a) : "",
    ];
    return `<section class="room">${head}${parts.join("")}</section>`;
  }

  _timelineHtml(a) {
    const profile = a.profile && a.schedule && a.schedule[a.profile];
    if (!profile || !profile.length) return "";
    const slots = [...profile].sort((x, y) => toMinutes(x.time) - toMinutes(y.time));
    const segments = [];
    const last = slots[slots.length - 1];
    if (toMinutes(slots[0].time) > 0) {
      segments.push({ start: 0, end: toMinutes(slots[0].time), preset: last.preset });
    }
    slots.forEach((slot, i) => {
      const end = i + 1 < slots.length ? toMinutes(slots[i + 1].time) : 1440;
      segments.push({ start: toMinutes(slot.time), end, preset: slot.preset });
    });
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
      .filter((s) => s.end > s.start)
      .map((s) => {
        const h = height(s.preset);
        path += ` L${s.start} ${H - h} L${s.end} ${H - h}`;
        const t = num(levels[s.preset]);
        if (s.end - s.start >= 120) {
          const pct = ((s.start + s.end) / 2 / W) * 100;
          const align = s.start === 0 ? "left:0;transform:none" : s.end >= W ? "right:0;transform:none" : `left:${pct}%`;
          labels.push(
            `<span style="${align};bottom:${((h + 4) / (H + 14)) * 100}%">${esc(
              this._presetName(a, s.preset)
            )}${t !== null ? ` ${t}°` : ""}</span>`
          );
        }
        return `<rect x="${s.start}" y="${H - h}" width="${s.end - s.start}" height="${h}"
          fill="${PRESET_COLORS[s.preset] || "var(--primary-color)"}"><title>${esc(
          this._presetName(a, s.preset)
        )} ${hhmm(s.start)}–${hhmm(s.end % 1440)}</title></rect>`;
      })
      .join("");
    path += ` L${W} ${H}`;
    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();
    const ticks = [0, 6, 12, 18, 24]
      .map((h) => `<span style="left:${(h / 24) * 100}%">${String(h).padStart(2, "0")}</span>`)
      .join("");
    const next = a.next_change
      ? `<span>${this._t("next")}: <b>${esc(this._fmtTime(a.next_change))}</b> ${esc(
          this._presetName(a, a.next_preset)
        )}</span>`
      : "";
    return `
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
      <div class="meta"><span>${this._t("profile")}: <b>${esc(a.profile || "–")}</b></span>${next}</div>`;
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
      ? `<label class="field">${this._t("profile")}<select data-action="select" data-entity="${esc(
          e.profile
        )}">${options}</select></label>`
      : "";
    const clear = a.override
      ? `<button class="link" data-action="clear" data-room="${esc(a.room_id)}">${this._t(
          "clear_override"
        )}</button>`
      : "";
    return `<div class="row wrap controls">${select}${this._toggle(e.child_lock, this._t("child_lock"))}${clear}</div>`;
  }

  _quickHtml(a) {
    const presets = (a.presets || Object.keys(PRESET_COLORS))
      .map(
        (p) => `<button class="preset" style="--c:${PRESET_COLORS[p] || "var(--primary-color)"}"
          data-action="quick-preset" data-room="${esc(a.room_id)}" data-preset="${esc(p)}">${esc(
          this._presetName(a, p)
        )}</button>`
      )
      .join("");
    const target = num(a.target_temperature) ?? 21;
    return `
      <div class="quick">
        <div class="sub">${this._t("quick")}</div>
        <div class="row wrap">${presets}</div>
        <div class="row wrap">
          <label class="field small"><input type="number" step="0.5" min="5" max="30"
            data-quick="temp" data-room="${esc(a.room_id)}" value="${target}">°C</label>
          <label class="field small">${this._t("for_hours")}<input type="number" step="0.5" min="0.5" max="72"
            data-quick="hours" data-room="${esc(a.room_id)}" placeholder="auto">${this._t("hours")}</label>
          <button class="primary" data-action="quick-temp" data-room="${esc(a.room_id)}">${this._t(
      "apply"
    )}</button>
        </div>
      </div>`;
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
        return `<label class="field level"><span class="dot" style="--c:${
          PRESET_COLORS[preset] || "var(--divider-color)"
        }"></span>${esc(name)}<input type="number" step="${s.attributes.step || 0.5}" min="${
          s.attributes.min ?? 5
        }" max="${s.attributes.max ?? 30}" data-action="number" data-entity="${esc(id)}" value="${esc(
          s.state
        )}">°C</label>`;
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
    const levelTemps = Object.entries(a.levels || {})
      .filter(([, t]) => t !== null && t !== undefined)
      .map(
        ([p, t]) =>
          `<span class="lv"><span class="dot" style="--c:${PRESET_COLORS[p]}"></span>${esc(
            this._presetName(a, p)
          )} ${t}°</span>`
      )
      .join("");
    const dl = (k, v) => `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>`;
    const html = `<dl class="details">
        ${dl(this._t("room_temp"), esc(this._temp(a.current_temperature)))}
        ${dl(this._t("target"), esc(this._temp(a.target_temperature)))}
        ${rate ? dl(this._t("rate"), `${esc(num(rate.state)?.toFixed(2) ?? "–")} °C/h`) : ""}
        ${runtime ? dl(this._t("runtime"), `${esc(num(runtime.state)?.toFixed(1) ?? "–")} h`) : ""}
        ${dl(this._t("adjustments"), esc(offsets))}
      </dl>
      ${levelTemps ? `<div class="levels-line">${levelTemps}${a.custom_levels ? "" : ` <span class="muted">${this._t("level_temps_gt")}</span>`}</div>` : ""}
      ${a.schedule_error ? `<p class="error">${esc(a.schedule_error)}</p>` : ""}`;
    return this._fold(`details-${a.room_id}`, this._t("details"), html);
  }

  _scheduleHtml(a) {
    if (!a.schedule_editable) {
      return this._fold(`sched-${a.room_id}`, this._t("schedule"), `<p class="muted">${this._t("not_editable")}</p>`);
    }
    if (this._editing !== a.room_id) {
      const summary = Object.entries(a.schedule || {})
        .map(
          ([name, slots]) =>
            `<div class="sched-line"><b>${esc(name)}</b>${slots
              .map(
                (s) =>
                  `<span class="slot"><span class="dot" style="--c:${PRESET_COLORS[s.preset]}"></span>${esc(
                    s.time
                  )} ${esc(this._presetName(a, s.preset))}</span>`
              )
              .join("")}</div>`
        )
        .join("");
      return this._fold(
        `sched-${a.room_id}`,
        this._t("schedule"),
        `${summary}<button class="link" data-action="edit" data-room="${esc(a.room_id)}">${this._t(
          "edit"
        )}</button>`
      );
    }
    const presets = a.presets || Object.keys(PRESET_COLORS);
    const option = (preset, current) =>
      `<option value="${esc(preset)}" ${preset === current ? "selected" : ""}>${esc(
        this._presetName(a, preset)
      )}</option>`;
    const blocks = Object.entries(this._draft || {})
      .map(([name, slots]) => {
        const rows = slots
          .map(
            (slot, i) => `<div class="row">
              <input type="time" data-profile="${esc(name)}" data-index="${i}" data-field="time" value="${esc(slot.time)}">
              <select data-profile="${esc(name)}" data-index="${i}" data-field="preset">${presets
                .map((p) => option(p, slot.preset))
                .join("")}</select>
              <button class="icon" data-action="del-slot" data-profile="${esc(name)}" data-index="${i}"
                aria-label="${this._t("remove")}">✕</button></div>`
          )
          .join("");
        return `<div class="profile-edit"><div class="row between"><b>${esc(name)}</b>
            <button class="link" data-action="del-profile" data-profile="${esc(name)}">${this._t("remove")}</button></div>
            ${rows}
            <button class="link" data-action="add-slot" data-profile="${esc(name)}">${this._t("add_slot")}</button></div>`;
      })
      .join("");
    return `<div class="editor">
        ${blocks}
        <div class="row"><input type="text" class="newprofile" placeholder="${this._t("profile_name")}">
          <button class="link" data-action="add-profile">${this._t("add_profile")}</button></div>
        ${this._error[`sched-${a.room_id}`] ? `<p class="error">${esc(this._error[`sched-${a.room_id}`])}</p>` : ""}
        <div class="row"><button class="primary" data-action="save" data-room="${esc(a.room_id)}">${this._t("save")}</button>
          <button class="link" data-action="cancel">${this._t("cancel")}</button></div>
      </div>`;
  }

  _fold(key, title, content) {
    return `<details class="fold" data-fold="${esc(key)}" ${this._open[key] ? "open" : ""}>
      <summary>${esc(title)}</summary>${content}</details>`;
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
  :host { --ac-gap: 12px; color: var(--primary-text-color); }
  ha-card { padding: 16px; color: var(--primary-text-color); }
  .title { margin: 0 0 12px; font-size: 1.3em; font-weight: 500; }
  .empty, .muted { color: var(--secondary-text-color); }
  .muted { font-size: 0.85em; }
  section { padding: 12px 0; border-top: 1px solid var(--divider-color); }
  section:first-of-type { border-top: none; padding-top: 0; }
  .row { display: flex; gap: 8px; align-items: center; margin-top: 8px; }
  .row.wrap { flex-wrap: wrap; }
  .row.between { justify-content: space-between; }
  .house-head { display: flex; justify-content: space-between; gap: var(--ac-gap); flex-wrap: wrap; }
  .house-name { font-weight: 500; font-size: 1.1em; }
  .presence { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 4px; }
  .presence-state { font-weight: 500; }
  .presence-state.home { color: #f08c00; }
  .presence-state.nearby { color: #2f9e8f; }
  .presence-state.far { color: #8a96a3; }
  .person { font-size: 0.8em; padding: 1px 8px; border-radius: 10px; border: 1px solid var(--divider-color); }
  .person.home { border-color: #f08c00; }
  .person.nearby { border-color: #2f9e8f; }
  .stats { display: flex; gap: 16px; flex-wrap: wrap; }
  .stat { display: flex; flex-direction: column; }
  .stat .k { font-size: 0.75em; color: var(--secondary-text-color); }
  .stat .v { font-variant-numeric: tabular-nums; font-weight: 500; }
  .stat.hot .v { color: #d9480f; }
  .stat.warn .v { color: var(--warning-color, #e0a030); }
  .segmented { display: inline-flex; border: 1px solid var(--divider-color); border-radius: 8px; overflow: hidden; }
  .seg { background: none; border: none; padding: 6px 12px; font: inherit; color: var(--primary-text-color); cursor: pointer; }
  .seg + .seg { border-left: 1px solid var(--divider-color); }
  .seg.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .toggles { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .toggle { display: inline-flex; align-items: center; gap: 6px; background: none; border: none; font: inherit;
    color: var(--primary-text-color); cursor: pointer; padding: 2px 0; }
  .toggle .knob { width: 30px; height: 16px; border-radius: 8px; background: var(--disabled-color, #bdbdbd); position: relative; }
  .toggle .knob::after { content: ""; position: absolute; top: 2px; left: 2px; width: 12px; height: 12px;
    border-radius: 50%; background: #fff; transition: transform .15s; }
  .toggle.on .knob { background: var(--primary-color); }
  .toggle.on .knob::after { transform: translateX(14px); }
  .room-head { width: 100%; display: flex; justify-content: space-between; align-items: baseline; background: none;
    border: none; padding: 0; font: inherit; color: inherit; cursor: pointer; text-align: left; }
  .room-name { font-size: 1.1em; font-weight: 500; }
  .temps { font-variant-numeric: tabular-nums; display: flex; gap: 10px; align-items: baseline; }
  .current { font-size: 1.6em; font-weight: 300; }
  .target { font-weight: 600; color: var(--c); }
  .decision { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-top: 4px; }
  .rule { padding: 2px 10px; border-radius: 12px; font-size: 0.85em; border: 1.5px solid var(--c); }
  .badge { font-size: 0.8em; padding: 2px 8px; border-radius: 12px; background: var(--secondary-background-color); }
  .badge.hot { background: #d9480f; color: #fff; }
  .badge.warn { background: var(--warning-color, #e0a030); color: #fff; }
  .reason { margin: 6px 0 0; color: var(--secondary-text-color); font-size: 0.9em; }
  .profile-chart { margin-top: 10px; position: relative; }
  .chart-labels { position: absolute; left: 0; right: 0; top: 0; height: 72px; pointer-events: none; }
  .chart-labels span { position: absolute; transform: translateX(-50%); font-size: 0.75em; white-space: nowrap;
    color: var(--primary-text-color); }
  .profile-chart svg { width: 100%; height: 72px; display: block; overflow: visible; }
  .profile-chart rect { opacity: 0.85; }
  .profile-chart .edge { fill: none; stroke: var(--primary-text-color); stroke-width: 3; opacity: 0.35;
    vector-effect: non-scaling-stroke; }
  .profile-chart .now { stroke: var(--primary-text-color); stroke-width: 2; vector-effect: non-scaling-stroke; }
  .ticks { position: relative; height: 14px; font-size: 0.7em; color: var(--secondary-text-color); }
  .ticks span { position: absolute; transform: translateX(-50%); }
  .ticks span:first-child { transform: none; }
  .ticks span:last-child { transform: translateX(-100%); }
  .meta { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; font-size: 0.85em; margin-top: 4px; }
  .field { display: inline-flex; align-items: center; gap: 6px; font-size: 0.9em; }
  .field.level { display: grid; grid-template-columns: 10px 1fr auto auto; gap: 6px; }
  input, select { font: inherit; padding: 4px 6px; border-radius: 6px; border: 1px solid var(--divider-color);
    background: var(--card-background-color); color: var(--primary-text-color); }
  input[type="number"] { width: 4.5em; }
  .quick { margin-top: 10px; }
  .sub { font-size: 0.85em; color: var(--secondary-text-color); }
  .preset { font: inherit; font-size: 0.85em; padding: 4px 10px; border-radius: 14px; cursor: pointer;
    background: none; color: var(--primary-text-color); border: 1.5px solid var(--c); }
  .preset:hover { background: var(--c); color: #fff; }
  button.link { background: none; border: none; color: var(--primary-color); cursor: pointer; padding: 0; font: inherit; }
  button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border: none;
    border-radius: 6px; padding: 6px 14px; cursor: pointer; font: inherit; }
  button.icon { background: none; border: none; cursor: pointer; color: var(--secondary-text-color); }
  button:focus-visible, input:focus-visible, select:focus-visible, summary:focus-visible {
    outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .fold { margin-top: 10px; }
  .fold summary { cursor: pointer; font-size: 0.9em; color: var(--primary-text-color); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 8px 16px; margin-top: 8px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--c); display: inline-block; flex: none; }
  .details { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; margin: 8px 0 0; }
  .details dt { font-size: 0.75em; color: var(--secondary-text-color); }
  .details dd { margin: 0; font-variant-numeric: tabular-nums; }
  .levels-line { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; font-size: 0.85em; align-items: center; }
  .lv, .slot { display: inline-flex; gap: 4px; align-items: center; }
  .sched-line { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 6px 0; font-size: 0.9em; }
  .editor { margin-top: 10px; padding: 10px; border-radius: 8px; background: var(--secondary-background-color); }
  .profile-edit { margin-bottom: 10px; }
  .error { color: var(--error-color, #db4437); font-size: 0.85em; }
  .actions { gap: 16px; }
  @media (prefers-reduced-motion: reduce) { .toggle .knob::after { transition: none; } }
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
