/**
 * DSAB Dartliga Card – Lovelace-Card für die Integration dsab_darts.
 *
 * Ansichten: Tabelle (Teams / Spieler), Spieltag (letzter / nächster), Team.
 * Wird von der Integration automatisch registriert, keine Ressource nötig.
 *
 *   type: custom:dsab-darts-card
 *   entity: sensor.<beliebige Entität der Liga>   # optional
 *   default_view: tabelle | spieltag | team       # optional
 *   views: [tabelle, spieltag, team]              # optional, Reihenfolge = Tabs
 *   title: Meine Liga                             # optional
 */

const CARD_VERSION = "1.1.0";
const DOMAIN = "dsab_darts";

const VIEWS = {
  tabelle: { label: "Tabelle", icon: "mdi:format-list-numbered" },
  spieltag: { label: "Spieltag", icon: "mdi:calendar-month" },
  team: { label: "Team", icon: "mdi:account-group" },
};

// translation_key → Rolle; Fallback über die Endungen der Entitäts-IDs (de/en)
const ROLES = {
  leader: ["tabellenfuhrer", "league_leader"],
  next_round: ["nachster_spieltag", "next_match_day"],
  last_round: ["letzter_spieltag", "last_match_day"],
  top_player: ["bester_spieler", "top_player"],
  placement: ["tabellenplatz", "placement"],
  points: ["punkte", "points"],
  next_match: ["nachstes_spiel", "next_match"],
  last_result: ["letztes_ergebnis", "last_result"],
  team_players: ["spielerstatistik", "player_statistics"],
  matches: ["spiele", "matches"],
};

const OUTCOME = {
  sieg: { label: "Sieg", cls: "win" },
  niederlage: { label: "Niederlage", cls: "loss" },
  unentschieden: { label: "Unentschieden", cls: "draw" },
};

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const signed = (n) => (n > 0 ? `+${n}` : `${n ?? "–"}`);

const pct = (won, played) => (played ? `${Math.round((won / played) * 100)} %` : "–");

const mapsUrl = (address) =>
  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;

class DsabDartsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._view = null;
    this._tableMode = "teams";
    this._roundMode = null;
    this._lastStates = null;
  }

  // ---------------------------------------------------------------- config

  setConfig(config) {
    const views = (config.views ?? Object.keys(VIEWS)).filter((v) => v in VIEWS);
    if (!views.length) throw new Error("views muss mindestens eine von tabelle, spieltag, team enthalten");
    if (config.default_view && !(config.default_view in VIEWS)) {
      throw new Error(`Unbekannte Ansicht: ${config.default_view}`);
    }
    this._config = { ...config, views };
    this._view = views.includes(config.default_view) ? config.default_view : views[0];
    this._lastStates = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._resolve();
    const states = Object.values(this._entities).map((id) => hass.states[id]);
    if (this._lastStates && states.length === this._lastStates.length &&
        states.every((s, i) => s === this._lastStates[i])) {
      return;
    }
    this._lastStates = states;
    this._render();
  }

  getCardSize() {
    return 7;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  static getStubConfig(hass) {
    const entry = Object.values(hass.entities ?? {}).find((e) => e.platform === DOMAIN);
    return entry ? { entity: entry.entity_id } : {};
  }

  static getConfigForm() {
    const viewOptions = Object.entries(VIEWS).map(([value, v]) => ({ value, label: v.label }));
    return {
      schema: [
        { name: "entity", selector: { entity: { integration: DOMAIN } } },
        { name: "title", selector: { text: {} } },
        { name: "default_view", selector: { select: { mode: "dropdown", options: viewOptions } } },
        { name: "views", selector: { select: { multiple: true, options: viewOptions } } },
      ],
      computeLabel: (s) =>
        ({
          entity: "Liga (beliebige Entität der Integration)",
          title: "Titel (optional)",
          default_view: "Startansicht",
          views: "Angezeigte Ansichten",
        })[s.name],
    };
  }

  // ------------------------------------------------------------- entities

  _resolve() {
    const all = Object.values(this._hass.entities ?? {}).filter((e) => e.platform === DOMAIN);
    let device = this._config.device_id;
    if (!device && this._config.entity) device = this._hass.entities?.[this._config.entity]?.device_id;
    if (!device && all.length) device = all[0].device_id;
    const mine = all.filter((e) => e.device_id === device);

    const found = {};
    for (const e of mine) {
      const role = e.translation_key in ROLES
        ? e.translation_key
        : Object.keys(ROLES).find((r) => ROLES[r].some((s) => e.entity_id.endsWith(`_${s}`)));
      if (role && !found[role]) found[role] = e.entity_id;
    }
    this._entities = found;
  }

  _state(role) {
    const id = this._entities[role];
    return id ? this._hass.states[id] : undefined;
  }

  _moreInfo(role) {
    const entityId = this._entities[role];
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
  }

  // ------------------------------------------------------------ formatting

  get _tz() {
    return this._hass.locale?.time_zone === "local"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone
      : this._hass.config?.time_zone;
  }

  get _lang() {
    return this._hass.locale?.language ?? this._hass.language ?? "de";
  }

  _fmt(iso, opts) {
    if (!iso) return "–";
    try {
      return new Intl.DateTimeFormat(this._lang, { timeZone: this._tz, ...opts }).format(new Date(iso));
    } catch (_) {
      return new Date(iso).toLocaleString();
    }
  }

  _date(iso) {
    return this._fmt(iso, { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" });
  }

  _time(iso) {
    return this._fmt(iso, { hour: "2-digit", minute: "2-digit" });
  }

  _dayKey(d) {
    const p = new Intl.DateTimeFormat("en-CA", { timeZone: this._tz, year: "numeric", month: "2-digit", day: "2-digit" })
      .format(d);
    return Date.parse(`${p}T00:00:00Z`);
  }

  _relative(iso) {
    if (!iso) return "";
    const days = Math.round((this._dayKey(new Date(iso)) - this._dayKey(new Date())) / 86400000);
    if (days === 0) return "heute";
    if (days === 1) return "morgen";
    if (days === -1) return "gestern";
    return days > 0 ? `in ${days} Tagen` : `vor ${-days} Tagen`;
  }

  // ---------------------------------------------------------------- render

  _render() {
    if (!this._config || !this._hass) return;
    const leader = this._state("leader");
    const a = leader?.attributes ?? {};
    const title = this._config.title ?? (a.liga ? `${a.liga} · ${a.saison ?? ""}` : "DSAB Dartliga");
    const subtitle = this._config.title ? [a.liga, a.saison].filter(Boolean).join(" · ") : a.region ?? "";

    let body;
    if (!Object.keys(this._entities).length) {
      body = this._notice("Keine Entitäten der Integration „DSAB Dartliga“ gefunden.");
    } else if (this._view === "tabelle") {
      body = this._renderTable();
    } else if (this._view === "spieltag") {
      body = this._renderRound();
    } else {
      body = this._renderTeam();
    }

    const tabs = this._config.views.length > 1
      ? `<nav class="tabs" role="tablist">${this._config.views
          .map((v) => `<button role="tab" data-view="${v}" class="tab ${v === this._view ? "active" : ""}"
              aria-selected="${v === this._view}"><ha-icon icon="${VIEWS[v].icon}"></ha-icon><span>${VIEWS[v].label}</span></button>`)
          .join("")}</nav>`
      : "";

    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <ha-card>
        <header>
          <ha-icon class="logo" icon="mdi:bullseye-arrow"></ha-icon>
          <div class="titles">
            <div class="title">${esc(title)}</div>
            ${subtitle ? `<div class="subtitle">${esc(subtitle)}</div>` : ""}
          </div>
        </header>
        ${tabs}
        <section class="body">${body}</section>
      </ha-card>`;

    this.shadowRoot.querySelectorAll("[data-view]").forEach((b) =>
      b.addEventListener("click", () => { this._view = b.dataset.view; this._render(); }));
    this.shadowRoot.querySelectorAll("[data-table]").forEach((b) =>
      b.addEventListener("click", () => { this._tableMode = b.dataset.table; this._render(); }));
    this.shadowRoot.querySelectorAll("[data-round]").forEach((b) =>
      b.addEventListener("click", () => { this._roundMode = b.dataset.round; this._render(); }));
    this.shadowRoot.querySelectorAll("[data-more]").forEach((b) =>
      b.addEventListener("click", () => this._moreInfo(b.dataset.more)));
  }

  _notice(text) {
    return `<div class="notice"><ha-icon icon="mdi:information-outline"></ha-icon><span>${esc(text)}</span></div>`;
  }

  _segment(attr, current, options) {
    return `<div class="segment">${options
      .map(([value, label]) => `<button data-${attr}="${value}" class="${value === current ? "active" : ""}">${esc(label)}</button>`)
      .join("")}</div>`;
  }

  get _ownTeam() {
    return this._state("placement")?.attributes?.team ?? null;
  }

  // ---------------------------------------------------------------- Tabelle

  _renderTable() {
    const own = this._ownTeam;
    const switcher = this._segment("table", this._tableMode, [["teams", "Teams"], ["spieler", "Spieler"]]);

    if (this._tableMode === "spieler") {
      const players = this._state("top_player")?.attributes?.spieler ?? [];
      if (!players.length) return switcher + this._notice("Noch keine Spielerstatistik verfügbar.");
      return `${switcher}
        <table class="grid players">
          <thead><tr><th class="num">#</th><th>Spieler</th><th class="num">Sp</th><th class="num">S:N</th>
            <th class="num hide-s">Legs</th><th class="num">Quote</th></tr></thead>
          <tbody>${players.map((p) => `
            <tr class="${p.team === own ? "own" : ""}">
              <td class="num rank">${p.platz}</td>
              <td><div class="name">${esc(p.spieler)}</div><div class="sub">${esc(p.team)}</div></td>
              <td class="num">${p.spiele}</td>
              <td class="num">${p.siege}:${p.niederlagen}</td>
              <td class="num hide-s">${esc(p.legs)}</td>
              <td class="num strong">${pct(p.siege, p.spiele)}</td>
            </tr>`).join("")}</tbody>
        </table>`;
    }

    const rows = this._state("leader")?.attributes?.tabelle ?? [];
    if (!rows.length) return switcher + this._notice("Noch keine Tabelle verfügbar.");
    return `${switcher}
      <table class="grid standings">
        <thead><tr><th class="num">#</th><th>Team</th><th class="num">Sp</th>
          <th class="num hide-s">S</th><th class="num hide-s">U</th><th class="num hide-s">N</th>
          <th class="num">Sets</th><th class="num hide-m">Legs</th><th class="num">Pkt</th></tr></thead>
        <tbody>${rows.map((r, i) => `
          <tr class="${r.team === own ? "own" : ""} ${i === 0 ? "first" : ""}">
            <td class="num rank">${r.platz}</td>
            <td class="name">${esc(r.team)}</td>
            <td class="num">${r.spiele}</td>
            <td class="num hide-s">${r.siege}</td>
            <td class="num hide-s">${r.unentschieden}</td>
            <td class="num hide-s">${r.niederlagen}</td>
            <td class="num"><span class="hide-s">${esc(r.sets)} </span><span class="diff ${r.sets_diff > 0 ? "pos" : r.sets_diff < 0 ? "neg" : ""}">${signed(r.sets_diff)}</span></td>
            <td class="num hide-m"><span class="diff ${r.legs_diff > 0 ? "pos" : r.legs_diff < 0 ? "neg" : ""}">${signed(r.legs_diff)}</span></td>
            <td class="num strong">${r.punkte}</td>
          </tr>`).join("")}</tbody>
      </table>`;
  }

  // --------------------------------------------------------------- Spieltag

  _renderRound() {
    const next = this._state("next_round");
    const last = this._state("last_round");
    const nextGames = next?.attributes?.spiele ?? [];
    const lastGames = last?.attributes?.spiele ?? [];

    if (!this._roundMode) {
      // Direkt nach einem Spieltag (bis 3 Tage) die Ergebnisse zeigen, sonst den nächsten
      const lastDate = lastGames[0]?.termin;
      const recent = lastDate && Date.now() - Date.parse(lastDate) < 3 * 86400000;
      this._roundMode = !nextGames.length || recent ? "last" : "next";
    }

    const options = [];
    if (lastGames.length) options.push(["last", `Letzter · ${last.attributes.spiele[0].spieltag}`]);
    if (nextGames.length) options.push(["next", `Nächster · ${next.attributes.spieltag}`]);
    if (!options.length) return this._notice("Kein Spieltag geplant.");
    if (!options.some(([v]) => v === this._roundMode)) this._roundMode = options[0][0];

    const games = this._roundMode === "next" ? nextGames : lastGames;
    const own = this._ownTeam;
    const when = games[0]?.termin;

    return `${options.length > 1 ? this._segment("round", this._roundMode, options) : ""}
      <div class="round-head" data-more="${this._roundMode === "next" ? "next_round" : "last_round"}">
        <ha-icon icon="mdi:calendar-clock"></ha-icon>
        <span>${esc(this._date(when))}, ${esc(this._time(when))} Uhr</span>
        <span class="chip">${esc(this._relative(when))}</span>
      </div>
      <div class="matches">${games.map((g) => this._matchRow(g, own)).join("")}</div>`;
  }

  _matchRow(g, own) {
    const [sh, sg] = (g.ergebnis ?? "").split(":").map(Number);
    const done = g.status === "FINISH";
    const live = !done && g.status !== "OPEN" && g.ergebnis;
    const homeWin = done && sh > sg;
    const guestWin = done && sg > sh;
    const isOwn = own && (g.heim === own || g.gast === own);
    const score = g.ergebnis
      ? `<div class="score ${live ? "live" : ""}">${esc(g.ergebnis)}</div>${g.legs ? `<div class="legs">Legs ${esc(g.legs)}</div>` : ""}`
      : `<div class="score pending">${esc(this._time(g.termin))}</div>`;
    return `
      <div class="match ${isOwn ? "own" : ""}">
        <div class="team home ${homeWin ? "winner" : ""} ${g.heim === own ? "me" : ""}">${esc(g.heim)}</div>
        <div class="result">${live ? `<span class="live-dot">LIVE</span>` : ""}${score}</div>
        <div class="team guest ${guestWin ? "winner" : ""} ${g.gast === own ? "me" : ""}">${esc(g.gast)}</div>
        ${g.spiellokal ? `<a class="venue" href="${mapsUrl(g.spiellokal)}" target="_blank" rel="noopener">
          <ha-icon icon="mdi:map-marker-outline"></ha-icon><span>${esc(g.spiellokal)}</span></a>` : ""}
      </div>`;
  }

  // ------------------------------------------------------------------- Team

  _renderTeam() {
    const place = this._state("placement");
    if (!place) {
      return this._notice("Für diese Liga ist kein Team gewählt. Lege die Integration mit einem Team an, um diese Ansicht zu nutzen.");
    }
    const p = place.attributes;
    const next = this._state("next_match");
    const last = this._state("last_result");
    const players = [...(this._state("team_players")?.attributes?.spieler ?? [])]
      .sort((a, b) => b.siege / (b.spiele || 1) - a.siege / (a.spiele || 1) || b.spiele - a.spiele);

    const stats = `
      <div class="team-name">${esc(p.team)}</div>
      <div class="stats">
        <button class="stat" data-more="placement"><div class="value">${p.platz}.</div><div class="label">Platz</div></button>
        <button class="stat" data-more="points"><div class="value">${p.punkte}</div><div class="label">Punkte</div></button>
        <div class="stat"><div class="value">${p.siege}-${p.unentschieden}-${p.niederlagen}</div><div class="label">S-U-N</div></div>
        <div class="stat"><div class="value ${p.sets_diff > 0 ? "pos" : p.sets_diff < 0 ? "neg" : ""}">${signed(p.sets_diff)}</div><div class="label">Sets ${esc(p.sets)}</div></div>
        <div class="stat hide-s"><div class="value ${p.legs_diff > 0 ? "pos" : p.legs_diff < 0 ? "neg" : ""}">${signed(p.legs_diff)}</div><div class="label">Legs ${esc(p.legs)}</div></div>
      </div>`;

    const n = next?.attributes ?? {};
    const nextBox = next && next.state && !["unknown", "unavailable"].includes(next.state)
      ? `<div class="box" data-more="next_match">
          <div class="box-title"><ha-icon icon="mdi:dart"></ha-icon>Nächstes Spiel<span class="chip">${esc(this._relative(next.state))}</span></div>
          <div class="versus">
            <span class="badge ${n.heimspiel ? "home" : "away"}">${n.heimspiel ? "Heim" : "Auswärts"}</span>
            <span class="opp">vs. ${esc(n.gegner)}</span>
            ${n.gegner_platz ? `<span class="muted">(${n.gegner_platz}.)</span>` : ""}
          </div>
          <div class="muted">${esc(n.spieltag ?? "")} · ${esc(this._date(next.state))}, ${esc(this._time(next.state))} Uhr</div>
          ${n.adresse ? `<a class="venue" href="${mapsUrl(n.adresse)}" target="_blank" rel="noopener">
            <ha-icon icon="mdi:map-marker-outline"></ha-icon><span>${esc(n.adresse)}</span></a>` : ""}
        </div>`
      : `<div class="box muted">Kein weiteres Spiel geplant.</div>`;

    const l = last?.attributes ?? {};
    const out = OUTCOME[l.ausgang];
    const lastBox = last && l.gegner
      ? `<div class="box" data-more="last_result">
          <div class="box-title"><ha-icon icon="mdi:scoreboard-outline"></ha-icon>Letztes Ergebnis
            ${out ? `<span class="badge ${out.cls}">${out.label}</span>` : ""}</div>
          <div class="versus"><span class="big-score ${out?.cls ?? ""}">${esc(last.state)}</span>
            <span class="opp">${l.heimspiel ? "vs." : "bei"} ${esc(l.gegner)}</span></div>
          <div class="muted">${esc(l.spieltag ?? "")} · ${esc(this._date(l.termin))}${l.legs ? ` · Legs ${esc(l.legs)}` : ""}</div>
        </div>`
      : "";

    const playerTable = players.length
      ? `<table class="grid players">
          <thead><tr><th>Spieler</th><th class="num">Sp</th><th class="num">S:N</th>
            <th class="num hide-s">Legs</th><th class="num">Quote</th><th class="num hide-s">Liga</th></tr></thead>
          <tbody>${players.map((s) => `
            <tr>
              <td class="name">${esc(s.spieler)}</td>
              <td class="num">${s.spiele}</td>
              <td class="num">${s.siege}:${s.niederlagen}</td>
              <td class="num hide-s">${esc(s.legs)}</td>
              <td class="num strong"><div class="bar"><span style="width:${s.spiele ? Math.round((s.siege / s.spiele) * 100) : 0}%"></span></div>${pct(s.siege, s.spiele)}</td>
              <td class="num hide-s muted">${s.platz}.</td>
            </tr>`).join("")}</tbody>
        </table>`
      : "";

    return `${stats}<div class="boxes">${nextBox}${lastBox}</div>${playerTable}`;
  }
}

const STYLES = `
  :host { --dsab-accent: var(--primary-color); --dsab-win: var(--success-color, #43a047);
          --dsab-loss: var(--error-color, #db4437); --dsab-draw: var(--warning-color, #ffa600); }
  ha-card { overflow: hidden; container-type: inline-size; }
  header { display: flex; align-items: center; gap: 12px; padding: 16px 16px 8px; }
  .logo { color: var(--dsab-accent); --mdc-icon-size: 28px; }
  .title { font-size: 1.15em; font-weight: 500; line-height: 1.3; }
  .subtitle { color: var(--secondary-text-color); font-size: 0.85em; }
  .tabs { display: flex; border-bottom: 1px solid var(--divider-color); padding: 0 8px; }
  .tab { flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 10px 4px;
         background: none; border: 0; border-bottom: 2px solid transparent; color: var(--secondary-text-color);
         font: inherit; font-size: 0.9em; cursor: pointer; }
  .tab ha-icon { --mdc-icon-size: 18px; }
  .tab.active { color: var(--dsab-accent); border-bottom-color: var(--dsab-accent); font-weight: 500; }
  .body { padding: 12px 16px 16px; }
  button { font: inherit; color: inherit; }
  .segment { display: inline-flex; background: var(--secondary-background-color); border-radius: 18px;
             padding: 3px; margin-bottom: 12px; gap: 2px; max-width: 100%; }
  .segment button { border: 0; background: none; padding: 5px 12px; border-radius: 15px; cursor: pointer;
                    color: var(--secondary-text-color); font-size: 0.85em; white-space: nowrap; }
  .segment button.active { background: var(--card-background-color, #fff); color: var(--primary-text-color);
                           box-shadow: 0 1px 3px rgba(0,0,0,.15); font-weight: 500; }
  table.grid { width: 100%; border-collapse: collapse; font-size: 0.9em; }
  .grid th { text-align: left; font-weight: 500; color: var(--secondary-text-color); font-size: 0.8em;
             text-transform: uppercase; letter-spacing: .03em; padding: 4px 6px 6px; border-bottom: 1px solid var(--divider-color); }
  .grid td { padding: 7px 6px; border-bottom: 1px solid var(--divider-color); vertical-align: middle; }
  .grid tr:last-child td { border-bottom: 0; }
  .grid .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .grid .rank { color: var(--secondary-text-color); width: 1.5em; }
  .grid tr.first .rank { color: var(--dsab-accent); font-weight: 600; }
  .grid tr.own td { background: rgba(var(--rgb-primary-color, 3,169,244), .10); }
  .grid tr.own .name, .grid tr.own .rank { font-weight: 600; }
  .grid .name { overflow-wrap: anywhere; }
  .grid .sub { color: var(--secondary-text-color); font-size: 0.85em; }
  .strong { font-weight: 600; }
  .muted { color: var(--secondary-text-color); font-size: 0.9em; }
  .diff { font-size: 0.9em; }
  .pos { color: var(--dsab-win); } .neg { color: var(--dsab-loss); }
  .notice { display: flex; gap: 10px; align-items: center; color: var(--secondary-text-color); padding: 8px 0; }
  .chip { margin-left: auto; font-size: 0.75em; padding: 2px 8px; border-radius: 10px;
          background: var(--secondary-background-color); color: var(--secondary-text-color); white-space: nowrap; }
  .round-head { display: flex; align-items: center; gap: 8px; font-weight: 500; margin-bottom: 8px; cursor: pointer; }
  .round-head ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
  .matches { display: flex; flex-direction: column; gap: 8px; }
  .match { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 4px 10px;
           padding: 10px 12px; border-radius: 10px; background: var(--secondary-background-color); }
  .match.own { box-shadow: inset 3px 0 0 var(--dsab-accent); }
  .match .team { font-size: 0.95em; overflow-wrap: anywhere; }
  .match .home { text-align: right; } .match .guest { text-align: left; }
  .match .winner { font-weight: 600; }
  .match .me { color: var(--dsab-accent); }
  .result { text-align: center; min-width: 64px; }
  .score { font-size: 1.25em; font-weight: 600; font-variant-numeric: tabular-nums; }
  .score.pending { font-size: 0.95em; font-weight: 500; color: var(--secondary-text-color); }
  .score.live { color: var(--dsab-loss); }
  .legs { font-size: 0.75em; color: var(--secondary-text-color); }
  .live-dot { font-size: 0.65em; font-weight: 700; color: var(--dsab-loss); letter-spacing: .05em; }
  .venue { grid-column: 1 / -1; display: flex; align-items: center; justify-content: center; gap: 4px;
           color: var(--secondary-text-color); font-size: 0.8em; text-decoration: none; margin-top: 2px; }
  .venue ha-icon { --mdc-icon-size: 15px; flex: none; }
  .venue:hover { color: var(--dsab-accent); }
  .team-name { font-size: 1.05em; font-weight: 600; margin-bottom: 10px; }
  .stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-bottom: 12px; }
  .stat { background: var(--secondary-background-color); border: 0; border-radius: 10px; padding: 8px 4px;
          text-align: center; }
  button.stat { cursor: pointer; }
  .stat .value { font-size: 1.2em; font-weight: 600; font-variant-numeric: tabular-nums; }
  .stat .label { font-size: 0.72em; color: var(--secondary-text-color); white-space: nowrap; }
  .boxes { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
  .box { border: 1px solid var(--divider-color); border-radius: 10px; padding: 10px 12px; cursor: pointer;
         display: flex; flex-direction: column; gap: 4px; }
  .box .venue { justify-content: flex-start; margin: 0; }
  .box-title { display: flex; align-items: center; gap: 6px; font-size: 0.8em; color: var(--secondary-text-color);
               text-transform: uppercase; letter-spacing: .03em; }
  .box-title ha-icon { --mdc-icon-size: 16px; }
  .box-title .badge { margin-left: auto; }
  .box-title .chip { text-transform: none; letter-spacing: 0; font-size: 0.9em; }
  .versus { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .opp { font-weight: 500; }
  .badge { font-size: 0.72em; font-weight: 600; padding: 2px 8px; border-radius: 10px; text-transform: none;
           letter-spacing: 0; color: #fff; background: var(--secondary-text-color); }
  .badge.home { background: var(--dsab-accent); }
  .badge.away { background: var(--secondary-text-color); }
  .badge.win { background: var(--dsab-win); } .badge.loss { background: var(--dsab-loss); }
  .badge.draw { background: var(--dsab-draw); }
  .big-score { font-size: 1.5em; font-weight: 700; font-variant-numeric: tabular-nums; }
  .big-score.win { color: var(--dsab-win); } .big-score.loss { color: var(--dsab-loss); }
  .big-score.draw { color: var(--dsab-draw); }
  .bar { display: inline-block; width: 36px; height: 5px; border-radius: 3px; margin-right: 6px; vertical-align: middle;
         background: var(--divider-color); overflow: hidden; }
  .bar span { display: block; height: 100%; background: var(--dsab-accent); }
  @container (max-width: 560px) {
    .hide-m { display: none; }
    .boxes { grid-template-columns: 1fr; }
  }
  @container (max-width: 400px) {
    .hide-s { display: none; }
    .stats { grid-template-columns: repeat(4, 1fr); }
    .match { padding: 8px; gap: 4px 6px; }
    .match .team { font-size: 0.85em; }
    .bar { display: none; }
  }
  @container (max-width: 300px) {
    .tab span { display: none; }
    .tab ha-icon { --mdc-icon-size: 22px; }
  }
`;

if (!customElements.get("dsab-darts-card")) {
  customElements.define("dsab-darts-card", DsabDartsCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "dsab-darts-card",
    name: "DSAB Dartliga",
    description: "Tabelle, Spieltag und Team einer DSAB-Liga",
    preview: true,
    documentationURL: "https://github.com/DHansel91/ha-dsab-darts#card",
  });
  console.info(`%c DSAB-DARTS-CARD %c ${CARD_VERSION} `, "color:#fff;background:#d32f2f;font-weight:700", "color:#d32f2f");
}
