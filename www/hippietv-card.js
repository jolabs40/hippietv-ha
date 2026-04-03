class HippieTvCard extends HTMLElement {
  // --- Config ---

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please define an entity");
    }
    this._config = {
      name: config.name || "HippieTV",
      show_controls: config.show_controls !== false,
      show_description: config.show_description !== false,
      ...config,
    };
    this._entity = config.entity;
  }

  static getConfigElement() {
    return document.createElement("hippietv-card-editor");
  }

  static getStubConfig() {
    return { entity: "" };
  }

  getCardSize() {
    return 4;
  }

  // --- Hass setter ---

  set hass(hass) {
    this._hass = hass;
    const entity = hass.states[this._entity];
    if (!entity) {
      this._renderError("Entit\u00e9 introuvable : " + this._entity);
      return;
    }
    this._render(entity);
  }

  // --- Rendering ---

  _render(entity) {
    const state = entity.state;
    const attrs = entity.attributes;
    const mediaType = attrs.media_type || "live";

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    if (state === "idle" || state === "unavailable" || state === "unknown" || state === "off") {
      this._renderIdle(attrs);
      return;
    }

    if (mediaType === "live") {
      this._renderLive(entity, attrs);
    } else {
      this._renderVod(entity, attrs);
    }
  }

  // --- Live TV ---

  _renderLive(entity, attrs) {
    const state = entity.state;
    const isPaused = state === "paused";
    const channelName = attrs.media_channel || attrs.friendly_name || "";
    const category = attrs.category_name || "";
    const epgTitle = attrs.epg_title || "";
    const epgDesc = attrs.epg_description || "";
    const epgProgress = attrs.epg_progress || 0;
    const startTime = attrs.epg_start_time
      ? new Date(attrs.epg_start_time).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
      : "";
    const endTime = attrs.epg_end_time
      ? new Date(attrs.epg_end_time).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
      : "";
    const isMuted = attrs.is_volume_muted || false;
    const hasEpg = !!(epgTitle || epgDesc);
    const progressPct = Math.min(Math.round(epgProgress * 100), 100);

    let html = this._getStyles() + `<div class="card">`;

    // Header
    html += `<div class="header">`;
    if (isPaused) {
      html += `<span class="badge paused"><span class="dot orange"></span>EN PAUSE</span>`;
    } else {
      html += `<span class="badge live"><span class="dot green"></span>EN DIRECT</span>`;
    }
    html += `<span class="channel-name">${this._esc(channelName)}</span>`;
    html += `</div>`;

    // Category
    if (category) {
      html += `<div class="category">\uD83D\uDCFA ${this._esc(category)}</div>`;
    }

    // EPG block
    if (hasEpg) {
      html += `<div class="program-title">${this._esc(epgTitle)}</div>`;
      if (this._config.show_description && epgDesc) {
        html += `<div class="program-description">${this._esc(epgDesc)}</div>`;
      }
      // Progress bar
      if (startTime && endTime) {
        html += `<div class="progress-container">`;
        html += `<div class="progress-times"><span>${startTime}</span><span>${endTime}</span></div>`;
        html += `<div class="progress-bar-bg"><div class="progress-bar-fill live" style="width:${progressPct}%"></div></div>`;
        html += `<div class="progress-percent">${progressPct}%</div>`;
        html += `</div>`;
      }
    } else {
      html += `<div class="program-title">${this._esc(channelName)}</div>`;
    }

    // Controls
    if (this._config.show_controls) {
      html += this._renderControls(state, isMuted);
    }

    html += `</div>`;
    this.shadowRoot.innerHTML = html;
    this._bindControls(state, isMuted);
  }

  // --- VOD ---

  _renderVod(entity, attrs) {
    const state = entity.state;
    const mediaType = attrs.media_type || "movie";
    const isMovie = mediaType === "movie";
    const title = attrs.media_title || attrs.friendly_name || "";
    const category = attrs.category_name || "";
    const position = attrs.media_position || 0;
    const duration = attrs.media_duration || 0;
    const progress = duration > 0 ? position / duration : 0;
    const progressPct = Math.min(Math.round(progress * 100), 100);
    const isMuted = attrs.is_volume_muted || false;

    let html = this._getStyles() + `<div class="card">`;

    const seriesName = attrs.series_name || "";
    const seriesSeason = attrs.series_season || 0;
    const seriesEpisode = attrs.series_episode || 0;
    const isSeries = !isMovie;

    // Header
    html += `<div class="header">`;
    if (isMovie) {
      html += `<span class="badge movie">\uD83C\uDFAC FILM</span>`;
    } else {
      html += `<span class="badge series">\uD83D\uDCFA S\u00c9RIE</span>`;
    }
    html += `</div>`;

    // Series name
    if (isSeries && seriesName) {
      html += `<div class="series-name">${this._esc(seriesName)}</div>`;
    }

    // Category
    if (category) {
      html += `<div class="category">\uD83C\uDFAD ${this._esc(category)}</div>`;
    }

    // Season / Episode
    if (isSeries && (seriesSeason || seriesEpisode)) {
      html += `<div class="series-info">Saison ${seriesSeason} \u2022 \u00c9pisode ${seriesEpisode}</div>`;
    }

    // Title
    html += `<div class="program-title">${this._esc(title)}</div>`;

    // Progress bar
    if (duration > 0) {
      html += `<div class="progress-container">`;
      html += `<div class="progress-times"><span>${this._formatTime(position)}</span><span>${this._formatTime(duration)}</span></div>`;
      html += `<div class="progress-bar-bg"><div class="progress-bar-fill vod" style="width:${progressPct}%"></div></div>`;
      html += `<div class="progress-percent">${progressPct}%</div>`;
      html += `</div>`;
    }

    // Controls
    if (this._config.show_controls) {
      html += this._renderControls(state, isMuted);
    }

    html += `</div>`;
    this.shadowRoot.innerHTML = html;
    this._bindControls(state, isMuted);
  }

  // --- Idle ---

  _renderIdle(attrs) {
    const profileName = attrs.profile_name || "";
    const name = this._config.name;

    let html = this._getStyles() + `<div class="card">`;
    html += `<div class="idle-container">`;
    html += `<div class="idle-icon">\uD83C\uDF00</div>`;
    html += `<div class="idle-title">${this._esc(name)}</div>`;
    html += `<div class="idle-subtitle">En attente</div>`;
    if (profileName) {
      html += `<div class="idle-profile">Profil : ${this._esc(profileName)}</div>`;
    }
    html += `</div></div>`;
    this.shadowRoot.innerHTML = html;
  }

  // --- Error ---

  _renderError(msg) {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this.shadowRoot.innerHTML = this._getStyles() +
      `<div class="card"><div class="idle-container"><div class="idle-title">${this._esc(msg)}</div></div></div>`;
  }

  // --- Controls ---

  _renderControls(state, isMuted) {
    const isPaused = state === "paused";
    let html = `<div class="controls">`;
    html += `<button class="control-btn" data-action="playpause" title="${isPaused ? "Lecture" : "Pause"}">${isPaused ? "\u25B6\uFE0F" : "\u23F8\uFE0F"}</button>`;
    html += `<button class="control-btn" data-action="stop" title="Stop">\u23F9\uFE0F</button>`;
    html += `<button class="control-btn" data-action="voldown" title="Volume -">\uD83D\uDD09</button>`;
    html += `<button class="control-btn" data-action="mute" title="${isMuted ? "Son" : "Muet"}">${isMuted ? "\uD83D\uDD07" : "\uD83D\uDD0A"}</button>`;
    html += `<button class="control-btn" data-action="volup" title="Volume +">\uD83D\uDD0A</button>`;
    html += `</div>`;
    return html;
  }

  _bindControls(state, isMuted) {
    if (!this.shadowRoot) return;
    const btns = this.shadowRoot.querySelectorAll(".control-btn");
    btns.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        if (action === "playpause") this._togglePlayPause(state);
        else if (action === "stop") this._handleStop();
        else if (action === "voldown") this._callService("volume_down");
        else if (action === "volup") this._callService("volume_up");
        else if (action === "mute") this._toggleMute(isMuted);
      });
    });
  }

  // --- HA Service calls ---

  _callService(service, data = {}) {
    this._hass.callService("media_player", service, {
      entity_id: this._entity,
      ...data,
    });
  }

  _togglePlayPause(state) {
    if (state === "playing") {
      this._callService("media_pause");
    } else {
      this._callService("media_play");
    }
  }

  _handleStop() {
    this._callService("media_stop");
  }

  _toggleMute(isMuted) {
    this._callService("volume_mute", { is_volume_muted: !isMuted });
  }

  // --- Helpers ---

  _formatTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return h > 0
      ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
      : `${m}:${String(s).padStart(2, "0")}`;
  }

  _esc(str) {
    const el = document.createElement("span");
    el.textContent = str;
    return el.innerHTML;
  }

  // --- Styles ---

  _getStyles() {
    return `<style>
      :host {
        display: block;
      }
      .card {
        background: var(--ha-card-background, var(--card-background-color, white));
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, none);
        padding: 16px;
        color: var(--primary-text-color);
        font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .badge.live { background: rgba(76,175,80,0.15); color: #4CAF50; }
      .badge.paused { background: rgba(255,152,0,0.15); color: #FF9800; }
      .badge.movie { background: rgba(33,150,243,0.15); color: #2196F3; }
      .badge.series { background: rgba(156,39,176,0.15); color: #9C27B0; }
      .dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        display: inline-block;
      }
      .dot.green { background: #4CAF50; }
      .dot.orange { background: #FF9800; }
      .channel-name {
        font-size: 14px;
        font-weight: 600;
        color: var(--secondary-text-color);
      }
      .category {
        font-size: 13px;
        color: var(--secondary-text-color);
        margin-bottom: 8px;
      }
      .series-name {
        font-size: 16px;
        font-weight: 700;
        color: var(--primary-text-color);
        margin-bottom: 4px;
      }
      .series-info {
        font-size: 13px;
        font-weight: 600;
        color: #9C27B0;
        margin-bottom: 6px;
      }
      .program-title {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 4px;
        line-height: 1.3;
      }
      .program-description {
        font-size: 13px;
        color: var(--secondary-text-color);
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-bottom: 12px;
      }
      .progress-container { margin: 16px 0 12px; }
      .progress-bar-bg {
        height: 6px;
        background: var(--divider-color, rgba(0,0,0,0.12));
        border-radius: 3px;
        overflow: hidden;
        margin: 6px 0;
      }
      .progress-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 1s linear;
      }
      .progress-bar-fill.live { background: linear-gradient(90deg, #4CAF50, #66BB6A); }
      .progress-bar-fill.vod { background: linear-gradient(90deg, #2196F3, #42A5F5); }
      .progress-times {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .progress-percent {
        text-align: center;
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      .controls {
        display: flex;
        justify-content: center;
        gap: 16px;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid var(--divider-color, rgba(0,0,0,0.08));
      }
      .control-btn {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 22px;
        padding: 8px;
        border-radius: 50%;
        transition: background 0.2s;
        line-height: 1;
      }
      .control-btn:hover {
        background: var(--divider-color, rgba(0,0,0,0.08));
      }
      .idle-container {
        text-align: center;
        padding: 24px 16px;
      }
      .idle-icon { font-size: 32px; margin-bottom: 12px; }
      .idle-title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
      .idle-subtitle { font-size: 13px; color: var(--secondary-text-color); }
      .idle-profile {
        font-size: 13px;
        color: var(--secondary-text-color);
        margin-top: 12px;
      }
    </style>`;
  }
}

// --- Card Editor ---

class HippieTvCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  _render() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this.shadowRoot.innerHTML = `
      <style>
        .editor { padding: 8px; }
        .row { margin-bottom: 12px; }
        label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; }
        input[type="text"] {
          width: 100%; padding: 8px; box-sizing: border-box;
          border: 1px solid var(--divider-color, #ccc); border-radius: 4px;
          font-size: 14px; background: var(--card-background-color, white);
          color: var(--primary-text-color, #333);
        }
        .checkbox-row { display: flex; align-items: center; gap: 8px; }
        .checkbox-row label { margin: 0; }
      </style>
      <div class="editor">
        <div class="row">
          <label for="entity">Entity</label>
          <input type="text" id="entity" value="${this._config.entity || ""}" placeholder="media_player.hippietv_...">
        </div>
        <div class="row">
          <label for="name">Nom (optionnel)</label>
          <input type="text" id="name" value="${this._config.name || ""}" placeholder="HippieTV">
        </div>
        <div class="row checkbox-row">
          <input type="checkbox" id="show_controls" ${this._config.show_controls !== false ? "checked" : ""}>
          <label for="show_controls">Afficher les boutons</label>
        </div>
        <div class="row checkbox-row">
          <input type="checkbox" id="show_description" ${this._config.show_description !== false ? "checked" : ""}>
          <label for="show_description">Afficher la description EPG</label>
        </div>
      </div>
    `;

    this.shadowRoot.getElementById("entity").addEventListener("change", (e) => this._update("entity", e.target.value));
    this.shadowRoot.getElementById("name").addEventListener("change", (e) => this._update("name", e.target.value));
    this.shadowRoot.getElementById("show_controls").addEventListener("change", (e) => this._update("show_controls", e.target.checked));
    this.shadowRoot.getElementById("show_description").addEventListener("change", (e) => this._update("show_description", e.target.checked));
  }

  _update(key, value) {
    this._config = { ...this._config, [key]: value };
    const event = new CustomEvent("config-changed", { detail: { config: this._config } });
    this.dispatchEvent(event);
  }
}

// --- Register ---

customElements.define("hippietv-card", HippieTvCard);
customElements.define("hippietv-card-editor", HippieTvCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "hippietv-card",
  name: "HippieTV",
  description: "Media player card for HippieTV IPTV",
  preview: true,
});
