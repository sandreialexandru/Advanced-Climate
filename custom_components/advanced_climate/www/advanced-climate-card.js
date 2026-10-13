/*
 * Advanced Climate card
 *
 * Shows every room of the Advanced Climate integration (or one room) with the
 * current decision, the reason, today's schedule as a 24h timeline and an
 * editor for the schedule profiles.
 *
 *   type: custom:advanced-climate-card
 *   entity: sensor.living_decision   # optional: one room only
 *   title: Heating                   # optional
 *   show_editor: true                # optional (default true)
 */

const PRESET_COLORS = {
  home: "#ff9800",
  comfort: "#f4511e",
  activity: "#fbc02d",
  sleep: "#5c6bc0",
  eco: "#26a69a",
  away: "#90a4ae",
};

const TEXT = {
  en: {
    rooms: "Heating",
    target: "Target",
    now: "Now",
    next: "Next",
    profile: "Profile",
    edit: "Edit schedule",
    save: "Save",
    cancel: "Cancel",
    add_slot: "Add slot",
    add_profile: "Add profile",
    profile_name: "Profile name",
    remove: "Remove",
    clear_override: "Clear manual change",
    window: "Window open",
    override: "Manual change",
    no_rooms: "No Advanced Climate rooms found.",
    not_editable: "This room uses a schedule helper.",
    saved: "Schedule saved",
  },
  ro: {
    rooms: "Încălzire",
    target: "Țintă",
    now: "Acum",
    next: "Următor",
    profile: "Profil",
    edit: "Editează programul",
    save: "Salvează",
    cancel: "Renunță",
    add_slot: "Adaugă interval",
    add_profile: "Adaugă profil",
    profile_name: "Numele profilului",
    remove: "Șterge",
    clear_override: "Anulează modificarea manuală",
    window: "Fereastră deschisă",
    override: "Modificare manuală",
    no_rooms: "Nu există camere Advanced Climate.",
    not_editable: "Camera folosește un helper de program.",
    saved: "Program salvat",
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

class AdvancedClimateCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._editing = null; // room_id being edited
    this._draft = null; // profiles being edited
    this._lastKey = "";
  }

  setConfig(config) {
    this._config = { show_editor: true, ...config };
    this._lastKey = "";
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._editing) return; // do not redraw while editing
    const key = this._rooms()
      .map((s) => `${s.entity_id}:${s.state}:${s.last_updated}`)
      .join("|");
    if (key !== this._lastKey) {
      this._lastKey = key;
      this._render();
    }
  }

  getCardSize() {
    return 3 + this._rooms().length * 3;
  }

  static getStubConfig() {
    return {};
  }

  _t(key) {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").slice(0, 2);
    return (TEXT[lang] || TEXT.en)[key] || TEXT.en[key] || key;
  }

  _rooms() {
    if (!this._hass) return [];
    const states = Object.values(this._hass.states).filter(
      (s) => s.attributes && s.attributes.room_id && s.attributes.entry_id && s.attributes.schedule
    );
    if (this._config?.entity) {
      return states.filter((s) => s.entity_id === this._config.entity);
    }
    return states.sort((a, b) =>
      String(a.attributes.room_name).localeCompare(String(b.attributes.room_name))
    );
  }

  _stateLabel(stateObj) {
    if (this._hass?.formatEntityState) {
      try {
        return this._hass.formatEntityState(stateObj);
      } catch (e) {
        /* older frontends */
      }
    }
    return stateObj.state;
  }

  _presetName(attrs, preset) {
    return (attrs.preset_names && attrs.preset_names[preset]) || preset;
  }

  _fmtTime(iso) {
    if (!iso) return "–";
    const d = new Date(iso);
    const lang = this._hass?.locale?.language || "en";
    const sameDay = new Date().toDateString() === d.toDateString();
    const opts = sameDay
      ? { hour: "2-digit", minute: "2-digit" }
      : { weekday: "short", hour: "2-digit", minute: "2-digit" };
    return d.toLocaleString(lang, opts);
  }

  _timeline(attrs) {
    const profile = attrs.profile && attrs.schedule[attrs.profile];
    if (!profile || !profile.length) return "";
    const slots = [...profile].sort((a, b) => toMinutes(a.time) - toMinutes(b.time));
    const segments = [];
    const last = slots[slots.length - 1];
    if (toMinutes(slots[0].time) > 0) {
      segments.push({ start: 0, end: toMinutes(slots[0].time), preset: last.preset });
    }
    slots.forEach((slot, i) => {
      const start = toMinutes(slot.time);
      const end = i + 1 < slots.length ? toMinutes(slots[i + 1].time) : 1440;
      segments.push({ start, end, preset: slot.preset });
    });
    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();
    const bars = segments
      .filter((s) => s.end > s.start)
      .map(
        (s) => `<div class="seg" title="${esc(this._presetName(attrs, s.preset))} ${String(
          Math.floor(s.start / 60)
        ).padStart(2, "0")}:${String(s.start % 60).padStart(2, "0")}"
          style="left:${(s.start / 1440) * 100}%;width:${((s.end - s.start) / 1440) * 100}%;
          background:${PRESET_COLORS[s.preset] || "var(--primary-color)"}">
          ${s.end - s.start >= 150 ? esc(this._presetName(attrs, s.preset)) : ""}</div>`
      )
      .join("");
    const ticks = [0, 6, 12, 18, 24]
      .map((h) => `<span style="left:${(h / 24) * 100}%">${String(h).padStart(2, "0")}</span>`)
      .join("");
    return `<div class="timeline">${bars}<div class="now" style="left:${
      (nowMin / 1440) * 100
    }%"></div></div><div class="ticks">${ticks}</div>`;
  }

  _roomHtml(stateObj) {
    const a = stateObj.attributes;
    const temp = (v) => (v === null || v === undefined ? "–" : `${Number(v).toFixed(1)} °C`);
    const badges = [];
    if (a.window_open) badges.push(`<span class="badge warn">${this._t("window")}</span>`);
    if (a.override)
      badges.push(
        `<span class="badge">${this._t("override")}${
          a.override.until ? ` · ${esc(this._fmtTime(a.override.until))}` : ""
        }</span>`
      );
    if (a.heat_demand) badges.push(`<span class="badge heat">🔥</span>`);
    const editing = this._editing === a.room_id;
    const editor = editing ? this._editorHtml(a) : "";
    const editBtn =
      this._config.show_editor && !editing
        ? a.schedule_editable
          ? `<button class="link" data-action="edit" data-room="${esc(a.room_id)}">${this._t(
              "edit"
            )}</button>`
          : `<span class="muted">${this._t("not_editable")}</span>`
        : "";
    const clearBtn = a.override
      ? `<button class="link" data-action="clear" data-room="${esc(a.room_id)}">${this._t(
          "clear_override"
        )}</button>`
      : "";
    return `
      <div class="room">
        <div class="head">
          <div class="name">${esc(a.room_name)}</div>
          <div class="temps"><span class="now-t">${temp(a.current_temperature)}</span>
            <span class="arrow">→</span><span class="target">${temp(a.target_temperature)}</span></div>
        </div>
        <div class="rule"><span class="chip" style="background:${
          PRESET_COLORS[a.preset] || "var(--secondary-background-color)"
        }">${esc(this._stateLabel(stateObj))}</span> ${badges.join(" ")}</div>
        <div class="reason">${esc(a.reason || "")}</div>
        ${this._timeline(a)}
        <div class="meta">
          <span>${this._t("profile")}: <b>${esc(a.profile || "–")}</b></span>
          <span>${this._t("next")}: <b>${esc(this._fmtTime(a.next_change))}</b>
            ${a.next_preset ? esc(this._presetName(a, a.next_preset)) : ""}</span>
        </div>
        <div class="actions">${editBtn} ${clearBtn}</div>
        ${editor}
      </div>`;
  }

  _editorHtml(attrs) {
    const presets = attrs.presets || Object.keys(PRESET_COLORS);
    const profiles = this._draft || {};
    const option = (preset, current) =>
      `<option value="${esc(preset)}" ${preset === current ? "selected" : ""}>${esc(
        this._presetName(attrs, preset)
      )}</option>`;
    const blocks = Object.entries(profiles)
      .map(([name, slots]) => {
        const rows = slots
          .map(
            (slot, i) => `<div class="row">
              <input type="time" data-profile="${esc(name)}" data-index="${i}" data-field="time" value="${esc(
              slot.time
            )}">
              <select data-profile="${esc(name)}" data-index="${i}" data-field="preset">
                ${presets.map((p) => option(p, slot.preset)).join("")}</select>
              <button class="icon" data-action="del-slot" data-profile="${esc(
                name
              )}" data-index="${i}" title="${this._t("remove")}">✕</button></div>`
          )
          .join("");
        return `<div class="profile"><div class="pname">${esc(name)}
            <button class="icon" data-action="del-profile" data-profile="${esc(name)}" title="${this._t(
          "remove"
        )}">✕</button></div>${rows}
            <button class="link" data-action="add-slot" data-profile="${esc(name)}">+ ${this._t(
          "add_slot"
        )}</button></div>`;
      })
      .join("");
    return `<div class="editor">${blocks}
      <div class="row"><input type="text" class="newprofile" placeholder="${this._t(
        "profile_name"
      )}"><button class="link" data-action="add-profile">+ ${this._t("add_profile")}</button></div>
      <div class="error"></div>
      <div class="actions"><button class="primary" data-action="save" data-room="${esc(
        attrs.room_id
      )}">${this._t("save")}</button>
      <button class="link" data-action="cancel">${this._t("cancel")}</button></div></div>`;
  }

  _render() {
    if (!this._config) return;
    const rooms = this._rooms();
    const title = this._config.title ?? this._t("rooms");
    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        .title { font-size: 1.25em; font-weight: 500; margin-bottom: 8px; }
        .room { padding: 12px 0; border-top: 1px solid var(--divider-color); }
        .room:first-of-type { border-top: none; }
        .head { display: flex; justify-content: space-between; align-items: baseline; }
        .name { font-weight: 500; font-size: 1.1em; }
        .temps { font-variant-numeric: tabular-nums; }
        .target { font-weight: 600; }
        .arrow { color: var(--secondary-text-color); margin: 0 4px; }
        .rule { margin-top: 6px; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
        .chip { color: #fff; padding: 2px 10px; border-radius: 12px; font-size: 0.85em; }
        .badge { background: var(--secondary-background-color); padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
        .badge.warn { background: var(--warning-color, #ffa600); color: #fff; }
        .reason { color: var(--secondary-text-color); font-size: 0.9em; margin: 6px 0; }
        .timeline { position: relative; height: 22px; border-radius: 6px; overflow: hidden;
          background: var(--secondary-background-color); margin-top: 6px; }
        .seg { position: absolute; top: 0; bottom: 0; color: #fff; font-size: 0.7em; line-height: 22px;
          text-align: center; overflow: hidden; white-space: nowrap; }
        .now { position: absolute; top: -2px; bottom: -2px; width: 2px; background: var(--primary-text-color); }
        .ticks { position: relative; height: 14px; font-size: 0.7em; color: var(--secondary-text-color); }
        .ticks span { position: absolute; transform: translateX(-50%); }
        .ticks span:first-child { transform: none; }
        .ticks span:last-child { transform: translateX(-100%); }
        .meta { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-size: 0.85em; margin-top: 4px; }
        .actions { margin-top: 6px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
        button.link { background: none; border: none; color: var(--primary-color); cursor: pointer; padding: 0; font: inherit; }
        button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border: none;
          border-radius: 6px; padding: 6px 14px; cursor: pointer; font: inherit; }
        button.icon { background: none; border: none; cursor: pointer; color: var(--secondary-text-color); }
        .muted { color: var(--secondary-text-color); font-size: 0.85em; }
        .editor { margin-top: 10px; padding: 10px; border-radius: 8px; background: var(--secondary-background-color); }
        .profile { margin-bottom: 10px; }
        .pname { font-weight: 500; margin-bottom: 4px; }
        .row { display: flex; gap: 8px; align-items: center; margin: 4px 0; }
        input, select { font: inherit; padding: 4px; border-radius: 4px; border: 1px solid var(--divider-color);
          background: var(--card-background-color); color: var(--primary-text-color); }
        .error { color: var(--error-color, #db4437); font-size: 0.85em; }
      </style>
      <ha-card>
        ${title ? `<div class="title">${esc(title)}</div>` : ""}
        ${rooms.length ? rooms.map((r) => this._roomHtml(r)).join("") : `<div class="muted">${this._t("no_rooms")}</div>`}
      </ha-card>`;
    this.shadowRoot.querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", (ev) => this._onClick(ev))
    );
    this.shadowRoot.querySelectorAll(".editor input[data-field], .editor select").forEach((el) =>
      el.addEventListener("change", (ev) => this._onEdit(ev))
    );
  }

  _onEdit(ev) {
    const el = ev.target;
    const { profile, index, field } = el.dataset;
    if (!this._draft?.[profile]) return;
    this._draft[profile][Number(index)][field] = el.value;
  }

  async _onClick(ev) {
    const el = ev.currentTarget;
    const { action, room, profile, index } = el.dataset;
    if (action === "edit") {
      const stateObj = this._rooms().find((s) => s.attributes.room_id === room);
      this._editing = room;
      this._draft = JSON.parse(JSON.stringify(stateObj.attributes.schedule));
    } else if (action === "cancel") {
      this._editing = null;
      this._draft = null;
    } else if (action === "add-slot") {
      const slots = this._draft[profile];
      const lastTime = slots.length ? toMinutes(slots[slots.length - 1].time) : 0;
      const t = Math.min(lastTime + 60, 23 * 60 + 59);
      slots.push({
        time: `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`,
        preset: "home",
      });
    } else if (action === "del-slot") {
      this._draft[profile].splice(Number(index), 1);
      if (!this._draft[profile].length) delete this._draft[profile];
    } else if (action === "del-profile") {
      delete this._draft[profile];
    } else if (action === "add-profile") {
      const input = this.shadowRoot.querySelector(".newprofile");
      const name = (input?.value || "").trim().toLowerCase().replace(/\s+/g, "_");
      if (name && !this._draft[name]) this._draft[name] = [{ time: "00:00", preset: "home" }];
    } else if (action === "clear") {
      await this._hass.callService("advanced_climate", "clear_override", { room });
      return;
    } else if (action === "save") {
      try {
        await this._hass.callService("advanced_climate", "set_schedule", {
          room,
          profiles: this._draft,
        });
        this._editing = null;
        this._draft = null;
      } catch (err) {
        const box = this.shadowRoot.querySelector(".editor .error");
        if (box) box.textContent = err?.message || String(err);
        return;
      }
    }
    this._lastKey = "";
    this._render();
  }
}

if (!customElements.get("advanced-climate-card")) {
  customElements.define("advanced-climate-card", AdvancedClimateCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "advanced-climate-card",
    name: "Advanced Climate",
    description: "Rooms, decisions and editable schedules of Advanced Climate.",
    preview: true,
  });
}
