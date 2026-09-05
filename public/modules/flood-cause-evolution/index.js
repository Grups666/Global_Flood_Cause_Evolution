/** Interactive catchment-scale explorer for flood-generating process change. */
window.FloodCauseEvolutionModule = class FloodCauseEvolutionModule {
  constructor(app, manifest = {}) {
    this.app = app;
    this.manifest = manifest;
    this.basePath = manifest.basePath || "/";
    this.dataFile = manifest.dataFile || manifest.datasets?.[0]?.file;
    this.layerId = "flood-cause-catchments";
    this.legendId = "flood-cause-legend";
    this.scope = "conditions";
    this.outcomeKey = "rainfall_concentration";
    this.mechanism = "All-All";
    this.evidenceView = "all";
    this.selected = null;
    this.viewport = null;
    this.pointer = { x: innerWidth / 2, y: innerHeight / 2 };
    this.handlePointer = (event) => { this.pointer = { x: event.clientX, y: event.clientY }; };
    this.handleClick = (payload) => {
      if (payload.layer?.id !== this.layerId) return;
      this.selected = this.catchments.find((item) => String(item.id) === String(payload.feature?.id)) || payload.feature;
      this.showInspector(this.selected);
      this.redraw();
    };
    this.handleKey = (event) => { if (event.key === "Escape") this.closeOverview(); };
    this.handleLayout = () => this.positionToolbar();
  }

  async onLoad() {
    const response = await fetch(this.resolve(this.dataFile));
    if (!response.ok) throw new Error(`Unable to load flood-process data (${response.status})`);
    this.data = await response.json();
    this.catchments = this.data.catchments || [];
    this.ensureStyles();
    this.addLayer();
    this.ensureToolbar();
    this.updateToolbar();
    this.updateLegend();
    Foundation.eventBus.on(Foundation.Events.FEATURE_CLICK, this.handleClick);
    document.addEventListener("pointermove", this.handlePointer, { passive: true });
    document.addEventListener("keydown", this.handleKey);
    window.addEventListener("resize", this.handleLayout);
    this.leftPanel = document.getElementById("leftPanel");
    this.leftPanel?.addEventListener("transitionend", this.handleLayout);
    this.positionToolbar();
    this.app.resize?.();
    this.redraw();
  }

  onUnload() {
    this.app.layerManager.removeLayer(this.layerId);
    this.app.unregisterLegend?.(this.legendId);
    Foundation.eventBus.off(Foundation.Events.FEATURE_CLICK, this.handleClick);
    document.removeEventListener("pointermove", this.handlePointer);
    document.removeEventListener("keydown", this.handleKey);
    window.removeEventListener("resize", this.handleLayout);
    this.leftPanel?.removeEventListener("transitionend", this.handleLayout);
    this.toolbar?.remove();
    this.tooltip?.remove();
    this.modal?.remove();
  }

  getLayerIds() { return [this.layerId]; }

  get population() { return this.mechanism === "All-All" ? "all" : "process"; }

  resolve(path) {
    if (/^https?:\/\//i.test(path) || path.startsWith("/")) return path;
    return this.basePath + path.replace(/^\.\//, "");
  }

  addLayer() {
    this.app.layerManager.addLayer({
      id: this.layerId,
      name: "Observed catchment process trends",
      type: "vector",
      visible: true,
      interactive: true,
      moduleId: this.manifest.id,
      groupPath: ["flood-generating processes"],
      metadata: { removable: false, evidenceScale: "gauged catchment" },
      renderer: (ctx, _layer, viewport) => this.render(ctx, viewport),
      hitTest: (lon, lat, viewport) => this.hitTest(lon, lat, viewport),
    });
    this.app.updateLayerList?.();
  }

  metric(item) {
    if (this.population === "process") return item.processes?.[this.mechanism]?.[this.outcomeKey];
    if (this.scope === "overall") return item.overall?.[this.outcomeKey];
    return item.conditions?.[this.outcomeKey];
  }

  availableOutcomes() {
    if (this.scope === "overall") return ["direct_runoff_volume", "flood_peak", this.population === "process" ? "mechanism_frequency" : "exceedance_frequency"];
    return this.population === "process"
      ? ["rainfall_concentration", "antecedent_wetness", "mechanism_share"]
      : ["rainfall_concentration", "antecedent_wetness"];
  }

  metricShort(key) {
    return key === "mechanism_frequency" ? "Q95 frequency" : this.data.meta.outcomes[key].short;
  }

  outcome() {
    const outcome = { ...this.data.meta.outcomes[this.outcomeKey], short: this.metricShort(this.outcomeKey) };
    return this.scope === "conditions" && this.population === "all"
      ? { ...outcome, limit: this.data.meta.conditionLimits[this.outcomeKey] }
      : outcome;
  }

  processLabel() {
    const [wetness, forcing] = this.mechanism.split("-");
    const soil = wetness === "All" ? "all antecedent wetness" : `${wetness.toLowerCase()} antecedent soil`;
    const rain = forcing === "All" ? "all rainfall forcing" : `${forcing.toLowerCase()}-led`;
    return `${soil} · ${rain}`;
  }

  redraw() {
    this.app.draw?.();
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => this.app.draw?.());
    });
  }

  render(ctx, viewport) {
    this.viewport = viewport;
    const limit = Number(this.outcome().limit) || 1;
    const shifts = this.worldShifts(viewport);
    for (const supportedPass of [false, true]) {
      for (const item of this.catchments) {
        const metric = this.metric(item);
        if (!metric || Boolean(metric.supported) !== supportedPass) continue;
        const contextual = !metric.supported && this.evidenceView === "supported";
        const radius = this.pointRadius(viewport, metric.supported);
        for (const shift of shifts) {
          const point = this.project(item.lon + shift, item.lat, viewport);
          ctx.save();
          ctx.beginPath();
          ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
          ctx.fillStyle = contextual ? "#aeb8bf" : this.color(metric.slope, limit, metric.supported);
          ctx.globalAlpha = metric.supported ? 0.98 : (contextual ? 0.30 : 0.88);
          ctx.fill();
          ctx.restore();
        }
      }
    }
    const hovered = this.app.hoveredLayer?.id === this.layerId
      ? this.catchments.find((item) => String(item.id) === String(this.app.hoveredFeatureId)) : null;
    if (this.selected && this.metric(this.selected) && String(this.selected.id) !== String(hovered?.id)) {
      this.highlight(ctx, this.selected, viewport, false);
    }
    if (hovered && this.metric(hovered)) this.highlight(ctx, hovered, viewport, true);
    this.updateTooltip(hovered);
  }

  highlight(ctx, item, viewport, hovered) {
    const radius = this.pointRadius(viewport, true) + (hovered ? 4.2 : 3.3);
    for (const shift of this.worldShifts(viewport)) {
      const point = this.project(item.lon + shift, item.lat, viewport);
      ctx.save();
      ctx.beginPath();
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.strokeStyle = "#22d3ee";
      ctx.lineWidth = hovered ? 1.8 : 1.55;
      ctx.shadowColor = "rgba(34,211,238,.98)";
      ctx.shadowBlur = hovered ? 24 : 18;
      ctx.stroke();
      ctx.restore();
    }
  }

  pointRadius(viewport, supported = false) {
    const zoom = Math.max(0, Math.log2(Math.max(1, Number(viewport.scale) || 1)));
    return Math.min(9.2, 3.4 + zoom * 0.85 + (supported ? 1.0 : 0));
  }

  hitTest(lon, lat, viewport) {
    const normalized = ((lon + 180) % 360 + 360) % 360 - 180;
    const pixelsPerDegree = (viewport.height / 180) * viewport.scale;
    const threshold = Math.max(0.09, (this.pointRadius(viewport, true) + 5) / pixelsPerDegree);
    let best = null;
    let bestDistance = Infinity;
    for (const item of this.catchments) {
      if (!this.metric(item)) continue;
      const distance = Math.hypot(this.lonDistance(normalized, item.lon), lat - item.lat);
      if (distance < threshold && distance < bestDistance) { best = item; bestDistance = distance; }
    }
    return best;
  }

  updateTooltip(item) {
    if (!item || !this.metric(item)) { this.tooltip?.classList.remove("visible"); return; }
    if (!this.tooltip) {
      this.tooltip = document.createElement("div");
      this.tooltip.className = "fce-tooltip";
      document.body.appendChild(this.tooltip);
    }
    const metric = this.metric(item);
    const outcome = this.outcome();
    const process = this.population === "process" ? `${this.processLabel()} · ` : "";
    this.tooltip.innerHTML = `<strong>GCIN ${this.escape(item.id)} · ${this.escape(item.country)}</strong><span>${this.escape(process + outcome.short)}</span><b>${this.signed(metric.slope, outcome.digits)} <small>${this.escape(outcome.unit)}</small></b><em>${metric.supported ? "passes complete evidence screen" : "estimable direction"}</em>`;
    this.tooltip.classList.add("visible");
    const width = this.tooltip.offsetWidth;
    const height = this.tooltip.offsetHeight;
    let left = this.pointer.x + 16;
    let top = this.pointer.y + 16;
    if (left + width > innerWidth - 10) left = this.pointer.x - width - 16;
    if (top + height > innerHeight - 10) top = this.pointer.y - height - 16;
    this.tooltip.style.left = `${Math.max(10, left)}px`;
    this.tooltip.style.top = `${Math.max(10, top)}px`;
  }

  setScope(scope) {
    if (!['overall', 'conditions'].includes(scope)) return;
    this.scope = scope;
    this.outcomeKey = scope === "overall" ? "direct_runoff_volume" : "rainfall_concentration";
    this.updateToolbar();
    this.updateLegend();
    if (this.selected) this.showInspector(this.selected);
    this.redraw();
  }

  setMechanism(mechanism) {
    if (!this.data.meta.filterGroups.includes(mechanism)) return;
    this.mechanism = mechanism;
    if (this.scope === "overall" && ["exceedance_frequency", "mechanism_frequency"].includes(this.outcomeKey)) {
      this.outcomeKey = this.population === "process" ? "mechanism_frequency" : "exceedance_frequency";
    }
    if (!this.availableOutcomes().includes(this.outcomeKey)) this.outcomeKey = this.availableOutcomes()[0];
    this.updateToolbar();
    this.updateLegend();
    if (this.selected) this.showInspector(this.selected);
    this.redraw();
  }

  setOutcome(outcome) {
    if (!this.availableOutcomes().includes(outcome)) return;
    this.outcomeKey = outcome;
    this.updateToolbar();
    this.updateLegend();
    if (this.selected) this.showInspector(this.selected);
    this.redraw();
  }

  setEvidence(view) {
    this.evidenceView = view;
    this.updateToolbar();
    this.redraw();
  }

  ensureToolbar() {
    this.toolbar = document.createElement("div");
    this.toolbar.className = "fce-toolbar";
    this.toolbar.innerHTML = `
      <div class="fce-toolbar-main">
        <label class="fce-field fce-scope-field">
          <span>Object</span>
          <select data-scope-select aria-label="Study object">
            <option value="overall">Flood characteristics</option>
            <option value="conditions">Flood-generating conditions</option>
          </select>
        </label>
        <label class="fce-field fce-outcome-field">
          <span>Metric</span>
          <select data-outcome-select aria-label="Displayed metric"></select>
        </label>
        <label class="fce-field fce-wetness-field">
          <span>Antecedent wetness</span>
          <select data-wetness aria-label="Antecedent wetness class" aria-describedby="fce-wetness-definition">
            <option value="All">All</option>
            <option value="Dry">Dry</option>
            <option value="Moderate">Moderate</option>
            <option value="Wet">Wet</option>
          </select>
        </label>
        <label class="fce-field fce-forcing-field">
          <span>Rainfall forcing</span>
          <select data-forcing aria-label="Rainfall forcing class" aria-describedby="fce-forcing-definition">
            <option value="All">All</option>
            <option value="Intensity">Intensity-led</option>
            <option value="Volume">Volume-led</option>
          </select>
        </label>
        <button class="fce-help" data-definitions-toggle aria-label="Explain condition metrics and event groups" aria-expanded="false" aria-controls="fce-class-definitions" title="Metrics and optional event groups">?</button>
        <div class="fce-summary" data-count aria-live="polite"></div>
        <label class="fce-field fce-evidence-field">
          <span>Map display</span>
          <select data-evidence-select aria-label="Map display">
            <option value="all">All estimates</option>
            <option value="supported">Supported focus</option>
          </select>
        </label>
        <button class="fce-overview" data-overview title="Open the complete research overview">Overview</button>
      </div>
      <div class="fce-definitions" id="fce-class-definitions" hidden>
        <div class="fce-definitions-header"><strong>Continuous conditions and optional groups</strong><button data-definitions-close aria-label="Close classification explanation">×</button></div>
        <p><b>Object chooses what is measured.</b> Flood characteristics contains flood volume, flood peak and Q95 frequency. Flood-generating conditions contains rainfall concentration and antecedent SSI, plus Process share when a group is selected.</p>
        <p><b>All leaves a filter unrestricted.</b> All + All uses all selected Q95 floods. Wet + All includes both rainfall types over wet soil; All + Intensity-led includes all wetness states with intensity-led rainfall. Matching events are pooled before fitting each trend.</p>
        <p><b>All selected floods.</b> Rainfall concentration is 100 × Pmax / Pevent (%). Antecedent wetness is the source catalogue's pre-event soil saturation index (SSI, 0–1). Their full-sample trends use every valid selected event, regardless of its class. A trend describes generating conditions, not proof of a causal mechanism.</p>
        <p id="fce-wetness-definition"><b>Antecedent wetness.</b> Dry, Moderate and Wet follow the source catalogue's global SSI terciles, with approximate boundaries of 0.3994 and 0.5640. These are relative wetness groups, not universal soil-saturation thresholds.</p>
        <p id="fce-forcing-definition"><b>Rainfall forcing.</b> Intensity-led requires both Pmax / Pevent &gt; 0.50 and daily rainfall CV &gt; 1. Volume-led contains the remaining events; the label alone does not establish a large rainfall total or a particular runoff mechanism.</p>
        <p><b>A catchment's event mix can change.</b> Each event is classified separately. Process share uses all selected Q95 floods as its denominator; concentration and wetness use only matching events. Select All in both filters for the whole-sample continuous trend.</p>
        <a href="https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2019WR026951" target="_blank" rel="noopener noreferrer">Rainfall rule: Tarasova et al. (2020)</a>
      </div>`;
    document.body.appendChild(this.toolbar);
    this.toolbar.querySelector("[data-scope-select]").onchange = (event) => this.setScope(event.target.value);
    const selectConditions = () => this.setMechanism(`${this.toolbar.querySelector("[data-wetness]").value}-${this.toolbar.querySelector("[data-forcing]").value}`);
    this.toolbar.querySelector("[data-wetness]").onchange = selectConditions;
    this.toolbar.querySelector("[data-forcing]").onchange = selectConditions;
    this.toolbar.querySelector("[data-outcome-select]").onchange = (event) => this.setOutcome(event.target.value);
    this.toolbar.querySelector("[data-evidence-select]").onchange = (event) => this.setEvidence(event.target.value);
    this.toolbar.querySelector("[data-overview]").onclick = () => this.showOverview();
    const explanation = this.toolbar.querySelector("[data-definitions-toggle]");
    const closeExplanation = () => { this.toolbar.querySelector(".fce-definitions").hidden = true; explanation.setAttribute("aria-expanded", "false"); };
    explanation.onclick = () => {
      const panel = this.toolbar.querySelector(".fce-definitions");
      panel.hidden = !panel.hidden;
      explanation.setAttribute("aria-expanded", String(!panel.hidden));
    };
    this.toolbar.querySelector("[data-definitions-close]").onclick = closeExplanation;
    this.toolbar.addEventListener("keydown", (event) => { if (event.key === "Escape") closeExplanation(); });
  }

  updateToolbar() {
    if (!this.toolbar) return;
    const outcomeKeys = this.availableOutcomes();
    this.toolbar.querySelector("[data-scope-select]").value = this.scope;
    const [wetness, forcing] = this.mechanism.split("-");
    this.toolbar.querySelector("[data-wetness]").value = wetness;
    this.toolbar.querySelector("[data-forcing]").value = forcing;
    this.toolbar.querySelector(".fce-definitions").hidden = true;
    this.toolbar.querySelector("[data-definitions-toggle]").setAttribute("aria-expanded", "false");
    const outcomeSelect = this.toolbar.querySelector("[data-outcome-select]");
    outcomeSelect.innerHTML = outcomeKeys.map((key) => `<option value="${key}">${this.metricShort(key)}</option>`).join("");
    outcomeSelect.value = this.outcomeKey;
    this.toolbar.querySelector("[data-evidence-select]").value = this.evidenceView;
    const available = this.catchments.map((item) => this.metric(item)).filter(Boolean);
    const supported = available.filter((metric) => metric.supported);
    const context = this.population === "process" ? this.processLabel() : "all Q95 floods";
    const count = this.toolbar.querySelector("[data-count]");
    count.innerHTML = `<strong>${supported.length.toLocaleString()}</strong><span>supported</span><small>of ${available.length.toLocaleString()}</small>`;
    count.title = `${supported.length.toLocaleString()} supported of ${available.length.toLocaleString()} estimable catchments · ${context}`;
    this.positionToolbar();
  }

  positionToolbar() {
    if (!this.toolbar) return;
    const panel = document.getElementById("leftPanel");
    const panelRight = panel && getComputedStyle(panel).display !== "none" ? Math.max(0, panel.getBoundingClientRect().right) : 0;
    const left = innerWidth > 900 ? Math.max(14, panelRight + 10) : 10;
    const right = innerWidth - 54;
    this.toolbar.style.left = innerWidth > 900 ? `${(left + right) / 2}px` : `${left}px`;
    this.toolbar.style.maxWidth = `${right - left}px`;
    this.toolbar.classList.toggle("compact", right - left < 1100);
  }

  showInspector(item) {
    const metric = this.metric(item);
    if (!metric) {
      this.app.showInspector?.(`GCIN ${item.id} · ${item.country}`, '<p class="fce-note">No estimable trend for this metric and event sample. Choose another metric or All selected floods.</p>');
      return;
    }
    const outcome = this.outcome();
    const process = this.population === "process" ? this.processLabel() : "All selected Q95 floods";
    const sampleDetail = this.outcomeKey === "exceedance_frequency"
      ? "same direction for Q90 and Q97.5; annual maximum is not a fixed-threshold frequency test"
      : "same direction for Q90, Q97.5 and annual maximum";
    const checks = [
      { name: "p < 0.05", pass: metric.pPass, detail: `two-sided p = ${this.prob(metric.p)}` },
      { name: "Alternative extreme samples", pass: metric.sampleStable, detail: sampleDetail },
      ...(this.population === "process" && !this.mechanism.endsWith("-All") ? [{ name: "Classification threshold", pass: metric.classificationStable, detail: "same direction at concentration cutoffs 0.40 and 0.60" }] : []),
      { name: "Leave-one-year-out", pass: metric.leaveOneYearStable, detail: "removing any one year does not reverse direction" },
    ];
    const passed = checks.filter((check) => check.pass).length;
    this.app.showInspector?.(`GCIN ${item.id} · ${item.country}`, `
      <p class="fce-inspector-lead">${this.escape(process)} · ${this.escape(outcome.label)}</p>
      ${this.population === "process" && ["rainfall_concentration", "antecedent_wetness"].includes(this.outcomeKey) ? '<p class="fce-note">Within the selected event group. Group membership can change over time; use Process share to inspect shifts between types.</p>' : ""}
      <div class="fce-result"><span>${this.escape(this.direction(metric.slope))}</span><strong style="color:${Number(metric.slope) >= 0 ? '#d96b3f' : '#2f6688'}">${this.displayEffect(metric.slope, outcome.digits)}</strong><small>${this.escape(outcome.unit)}</small><p>${this.escape(this.physicalMeaning(metric))}</p></div>
      ${this.annualChart(metric)}
      <div class="fce-grid">
        ${this.fact(`Fitted level · ${metric.firstYear} → ${metric.lastYear}`, `${this.level(metric.from)} → ${this.level(metric.to)}`)}
        ${this.fact("95% slope interval", `${this.signed(metric.ci?.[0], outcome.digits)} to ${this.signed(metric.ci?.[1], outcome.digits)}<small>${this.escape(outcome.unit)}</small>`)}
        ${this.fact("p value", this.prob(metric.p))}
        ${this.fact("Observed years", this.integer(metric.years))}
        ${this.fact("Selected events", this.integer(metric.events))}
        ${this.fact("Record", `${metric.firstYear}–${metric.lastYear}`)}
        ${this.outcomeKey === "antecedent_wetness" && Number.isFinite(Number(metric.relative)) ? this.fact("Relative to local mean", `${this.signed(metric.relative, 2)}% per 10 years`) : ""}
      </div>
      ${metric.fitOutsideBounds ? '<p class="fce-note">The straight-line fit reaches beyond the metric’s physical range. These fitted endpoints are model values, not observed physical states.</p>' : ""}
      <div class="fce-checks"><div><b>Evidence checks</b><span>${passed}/${checks.length} passed</span></div>${checks.map((check, index) => `<p class="${check.pass ? "pass" : "fail"}" title="${this.escape(check.detail)}"><i>${index + 1}</i>${check.pass ? "✓" : "·"} ${this.escape(check.name)}</p>`).join("")}</div>
      <div class="fce-alternatives"><b>Alternative extreme samples</b>${Object.entries(metric.alternatives || {}).filter(([name]) => !(this.outcomeKey === "exceedance_frequency" && name === "Annual maximum")).map(([name, value]) => `<span>${this.escape(name)} <strong>${this.signed(value, outcome.digits)}</strong></span>`).join("")}</div>
      <p class="fce-note">${this.escape(outcome.meaning)} This is a within-catchment temporal estimate. It does not extrapolate to ungauged areas and does not, by itself, prove causal attribution.</p>`);
  }

  physicalMeaning(metric) {
    const from = this.num(metric.from, this.outcome().digits);
    const to = this.num(metric.to, this.outcome().digits);
    const slope = this.signed(metric.slope, this.outcome().digits);
    if (this.outcomeKey === "mechanism_share") return `Among selected large floods, this process changes from about ${from}% to ${to}% across the fitted record (${slope} percentage points per 10 years).`;
    if (this.outcomeKey === "rainfall_concentration") return `For ${this.population === "process" ? "floods in this event group" : "all selected floods"}, the fitted rainfall-concentration trend is ${slope} percentage points per 10 years: the share of event rainfall falling on its rainiest day ${Number(metric.slope) >= 0 ? "increases" : "decreases"}.`;
    if (this.outcomeKey === "antecedent_wetness") return `Before ${this.population === "process" ? "floods in this event group" : "all selected floods"}, the fitted soil saturation index ${Number(metric.slope) >= 0 ? "increases" : "decreases"} by ${this.num(Math.abs(metric.slope), 3)} SSI units per 10 years.`;
    if (this.outcomeKey === "mechanism_frequency") return `This process changes from about ${from} to ${to} selected large floods per observed year across the fitted record.`;
    if (this.outcomeKey === "exceedance_frequency") return `The fixed-threshold Q95-event frequency changes from about ${from} to ${to} events per observed year across the fitted record.`;
    if (this.outcomeKey === "direct_runoff_volume") return `Mean selected-event direct stormflow volume changes from about ${from} to ${to} mm across the fitted record.`;
    return `Mean maximum daily streamflow within selected events changes from about ${from} to ${to} mm/day across the fitted record.`;
  }

  level(value) {
    const unit = {rainfall_concentration: "%", mechanism_share: "%", antecedent_wetness: " SSI", direct_runoff_volume: " mm", flood_peak: " mm/day", mechanism_frequency: " events/year", exceedance_frequency: " events/year"}[this.outcomeKey] || "";
    return `${this.num(value, this.outcome().digits)}${unit}`;
  }

  annualChart(metric) {
    // Trend contract: annual event means (one dot/year, >=10 valid years),
    // calendar-year x-axis, physical units on y, and the exact Theil–Sen fit.
    // Grey observations / blue fit distinguish evidence from the summary.
    const rows = metric.annual;
    if (!rows?.length) return "";
    const width = 340, height = 210, left = 48, right = 15, top = 30, bottom = 34;
    const first = rows[0][0], last = rows[rows.length - 1][0];
    const values = rows.map((row) => row[1]).concat([metric.from, metric.to]);
    const min = Math.min(...values), max = Math.max(...values);
    const pad = Math.max((max - min) * 0.14, this.outcomeKey === "rainfall_concentration" ? 1 : .01);
    const lower = Math.max(0, min - pad), upper = Math.min(this.outcomeKey === "rainfall_concentration" ? 100 : 1, max + pad);
    const x = (year) => left + (year - first) / Math.max(1, last - first) * (width - left - right);
    const y = (value) => top + (upper - value) / Math.max(1e-9, upper - lower) * (height - top - bottom);
    const ticks = [lower, (lower + upper) / 2, upper];
    const tickDigits = this.outcomeKey === "rainfall_concentration" ? 1 : 3;
    const grid = ticks.map(value => `<line x1="${left}" x2="${width - right}" y1="${y(value)}" y2="${y(value)}" stroke="#e1e7eb"/><text x="${left - 7}" y="${y(value) + 4}" text-anchor="end">${value.toFixed(tickDigits)}</text>`).join("");
    const dots = rows.map(([year, value, count]) => `<circle cx="${x(year)}" cy="${y(value)}" r="3.4" fill="#758592"><title>${year}: ${this.level(value)} · ${count} selected events</title></circle>`).join("");
    return `<section class="fce-trajectory"><b>Annual observations and fitted trend</b><p>${this.escape(this.outcome().short)} · ${first}–${last} · all selected floods</p>
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Annual ${this.escape(this.outcome().short)} observations and Theil–Sen trend from ${first} to ${last}">
        <text x="${left}" y="15">${this.outcomeKey === "rainfall_concentration" ? "Rainfall concentration (%)" : "Soil saturation index (SSI)"}</text>
        ${grid}<line x1="${left}" x2="${left}" y1="${top}" y2="${height - bottom}" stroke="#bbc7ce"/>
        <defs><clipPath id="fce-annual-plot"><rect x="${left}" y="${top}" width="${width - left - right}" height="${height - top - bottom}"/></clipPath></defs>
        <g clip-path="url(#fce-annual-plot)"><line x1="${x(first)}" x2="${x(last)}" y1="${y(metric.from)}" y2="${y(metric.to)}" stroke="#2f6688" stroke-width="2"/></g>${dots}
        ${[first, Math.round((first + last) / 2), last].map(year => `<text x="${x(year)}" y="${height - 12}" text-anchor="middle">${year}</text>`).join("")}
      </svg><p class="fce-chart-key"><span>● Annual event mean</span><span>━ Theil–Sen fit</span></p>
      <small>One point per observed event-year; years without selected events are not filled with zeros. The vertical scale follows the observed range. The line is a fitted trend, not the year-to-year observations.</small></section>`;
  }

  direction(value) {
    const positive = Number(value) >= 0;
    if (this.outcomeKey === "mechanism_share") return positive ? "larger process share" : "smaller process share";
    if (["mechanism_frequency", "exceedance_frequency"].includes(this.outcomeKey)) return positive ? "more frequent" : "less frequent";
    if (this.outcomeKey === "rainfall_concentration") return positive ? "more concentrated rainfall" : "less concentrated rainfall";
    if (this.outcomeKey === "antecedent_wetness") return positive ? "wetter antecedent state" : "drier antecedent state";
    return positive ? "larger flood response" : "smaller flood response";
  }

  updateLegend() {
    const outcome = this.outcome();
    const metrics = this.catchments.map((item) => this.metric(item)).filter(Boolean);
    const supported = metrics.filter((metric) => metric.supported);
    this.app.unregisterLegend?.(this.legendId);
    this.app.registerLegend?.(this.legendId, {
      title: this.population === "process" ? `${this.processLabel()} · ${outcome.short}` : outcome.short,
      html: `<div class="fce-legend-bar"></div><div class="fce-legend-axis"><span>${this.axis(-outcome.limit)}</span><span>0</span><span>+${this.axis(outcome.limit)}</span></div><p>${this.escape(outcome.unit)} · values outside the scale are clipped.</p><div class="fce-key"><i class="supported"></i>Passes complete screen (${supported.length})</div><div class="fce-key"><i class="estimate"></i>Other estimable direction (${metrics.length - supported.length})</div><div class="fce-key"><i class="hover"></i>Hover / selected</div><small>All estimates retains pale directional colour. Supported points are drawn last. Points enlarge as the map is zoomed.</small>`,
    });
  }

  showOverview() {
    if (!this.modal) {
      this.modal = document.createElement("div");
      this.modal.className = "fce-modal";
      this.modal.innerHTML = `<div class="fce-modal-card"><button class="fce-modal-close" aria-label="Close">×</button><iframe title="Research overview"></iframe></div>`;
      document.body.appendChild(this.modal);
      this.modal.querySelector("button").onclick = () => this.closeOverview();
      this.modal.onclick = (event) => { if (event.target === this.modal) this.closeOverview(); };
    }
    this.modal.querySelector("iframe").src = this.resolve(this.data.meta.report);
    this.modal.classList.add("visible");
  }

  closeOverview() { this.modal?.classList.remove("visible"); }

  fact(label, value) { return `<div><span>${this.escape(label)}</span><strong>${value}</strong></div>`; }
  num(value, digits = 2) { return value != null && Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—"; }
  signed(value, digits = 2) { return value != null && Number.isFinite(Number(value)) ? `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(digits)}` : "—"; }
  integer(value) { return value != null && Number.isFinite(Number(value)) ? Number(value).toLocaleString() : "—"; }
  displayEffect(value, digits = 2) { const base = this.signed(value, digits); return ["mechanism_share", "rainfall_concentration"].includes(this.outcomeKey) && base !== "—" ? `${base} pp` : base; }
  prob(value) { return value != null && Number.isFinite(Number(value)) ? (Number(value) < 0.001 ? "<0.001" : Number(value).toFixed(3)) : "—"; }
  axis(value) { const a = Math.abs(Number(value)); return a >= 10 ? Number(value).toFixed(0) : a >= 1 ? Number(value).toFixed(1) : Number(value).toFixed(3); }
  escape(value) { return String(value ?? "").replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c])); }

  color(value, limit, supported) {
    const t = Math.max(-1, Math.min(1, Number(value) / limit));
    if (Math.abs(t) < 1e-12) return "#d9dfe2";
    const strength = supported ? Math.abs(t) : 0.20 + 0.80 * Math.abs(t);
    const neutral = supported ? "#ecebe6" : "#f2f1ee";
    return t < 0
      ? this.mix(neutral, "#2f6688", strength)
      : this.mix(neutral, "#d96b3f", strength);
  }
  mix(a, b, t) {
    const parse = (hex) => [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16));
    const x = parse(a), y = parse(b);
    return `rgb(${x.map((value, index) => Math.round(value + (y[index] - value) * t)).join(",")})`;
  }
  project(lon, lat, viewport) { const base = (viewport.height / 180) * viewport.scale; return { x: viewport.width / 2 + lon * base + viewport.offsetX, y: viewport.height / 2 - lat * base + viewport.offsetY }; }
  lonDistance(a, b) { let value = a - b; while (value > 180) value -= 360; while (value < -180) value += 360; return value; }
  worldShifts(viewport) { const base = (viewport.height / 180) * viewport.scale; const left = (-viewport.width / 2 - viewport.offsetX) / base; const right = (viewport.width / 2 - viewport.offsetX) / base; const shifts = []; for (let i = Math.floor(left / 360) - 1; i <= Math.ceil(right / 360) + 1; i += 1) shifts.push(i * 360); return shifts; }

  ensureStyles() {
    if (document.getElementById("fce-styles")) return;
    const style = document.createElement("style");
    style.id = "fce-styles";
    style.textContent = `
.fce-toolbar{position:fixed;z-index:10020;top:14px;left:50%;transform:translateX(-50%);width:max-content;max-width:calc(100vw - 80px);box-sizing:border-box;padding:7px;border:1px solid #d8e3e8;border-radius:14px;background:#fff;box-shadow:0 10px 30px rgba(28,43,58,.13);font:13px/1.2 Inter,system-ui;color:#263548}
      .fce-toolbar-main{display:flex;align-items:stretch;gap:7px;overflow-x:auto;scrollbar-width:thin}
      .fce-toolbar [hidden]{display:none!important}
      .fce-field{display:grid;flex:0 0 auto;gap:1px;min-width:0;padding:4px 8px 5px;border:1px solid #dce6eb;border-radius:10px;background:#f7fafb}
      .fce-field>span{font-size:10px;font-weight:650;letter-spacing:.035em;color:#607184}
      .fce-field select{height:22px;box-sizing:border-box;padding:0 18px 0 0;border:0;background:transparent;color:#293a4d;font:650 12px Inter,system-ui;cursor:pointer}
      .fce-scope-field select{width:222px}.fce-wetness-field select{width:115px}.fce-forcing-field select{width:125px}.fce-outcome-field select{width:188px}.fce-evidence-field select{width:125px}
      .fce-grid small{display:block;font-size:11px;color:#64778c;font-weight:400;margin-top:3px}
      .fce-trajectory{margin:16px 0;color:#334c5e}.fce-trajectory>p{margin:5px 0;color:#64778c;font-size:12px}.fce-trajectory svg{display:block;width:100%;height:auto;font:11px Inter,system-ui;fill:#526679}.fce-trajectory small{display:block;font-size:11px;line-height:1.5;color:#64778c}.fce-trajectory .fce-chart-key{display:flex;justify-content:space-between;font-size:11px}.fce-chart-key span:first-child{color:#758592}.fce-chart-key span:last-child{color:#2f6688}
      .fce-summary{display:flex;flex:0 0 auto;align-items:baseline;gap:4px;align-self:center;white-space:nowrap;padding:0 3px;color:#607184}
      .fce-summary strong{color:#14778a;font-size:18px}.fce-summary span{font-weight:650}.fce-summary small{color:#718191;font-size:11px}
      .fce-toolbar.compact .fce-summary{display:none}
      .fce-toolbar button{flex:0 0 auto;border:0;border-radius:10px;padding:0 13px;background:#173f54;color:#fff;font:700 12px Inter,system-ui;cursor:pointer}
      .fce-toolbar button:hover{background:#205870}.fce-toolbar :is(button,select):focus-visible{outline:2px solid #0891b2;outline-offset:2px}
      .fce-toolbar .fce-help{align-self:center;border-radius:50%;width:23px;height:23px;padding:0;background:#e8f2f5;color:#17576a}
      .fce-toolbar .fce-help:hover{background:#d5eaf0;color:#123f50}
      .fce-definitions{position:absolute;top:calc(100% + 8px);left:0;width:min(460px,calc(100vw - 40px));box-sizing:border-box;padding:16px;border:1px solid #d8e3e8;border-radius:12px;background:#fff;box-shadow:0 12px 32px #24314224;font:13px/1.55 Inter,system-ui;color:#44596d}
      .fce-definitions-header{display:flex;align-items:center;justify-content:space-between;gap:10px;color:#173f54}.fce-toolbar .fce-definitions-header button{background:#edf3f5;color:#44596d;font-size:20px;padding:0 8px}
      .fce-definitions p{margin:10px 0}.fce-definitions a{color:#126b83}
      .fce-tooltip{display:none;position:fixed;z-index:2147483000;max-width:320px;padding:13px 15px;border-radius:12px;background:#172337;color:white;box-shadow:0 16px 38px rgba(18,28,41,.34);font:13px/1.45 Inter,system-ui;pointer-events:none}.fce-tooltip.visible{display:block}.fce-tooltip strong,.fce-tooltip span,.fce-tooltip b,.fce-tooltip em{display:block}.fce-tooltip strong{font-size:14px}.fce-tooltip span{color:#cbd6df}.fce-tooltip b{margin-top:3px;color:#67e8f9;font-size:18px}.fce-tooltip small{font-size:11px;color:#e5eef3}.fce-tooltip em{font-style:normal;color:#9fe0bd;font-size:11px}.fce-inspector-lead{color:#64778c}.fce-result{padding:16px 18px;border-radius:14px;background:#f1f5f6;border-left:3px solid #22d3ee}.fce-result span,.fce-result strong,.fce-result small{display:block}.fce-result strong{font-size:34px;color:#2f6688}.fce-result small{color:#64778c}.fce-result p{margin:9px 0 0;padding-top:9px;border-top:1px solid #d8e2e7;color:#29475a}.fce-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}.fce-grid>div{padding:10px;border:1px solid #dbe5eb;border-radius:10px}.fce-grid span,.fce-grid strong{display:block}.fce-grid span{font-size:10px;text-transform:uppercase;color:#75869a}.fce-checks,.fce-alternatives{margin-top:13px;padding:12px;border:1px solid #dbe5eb;border-radius:12px}.fce-checks>div{display:flex;justify-content:space-between}.fce-checks p{display:inline-flex;align-items:center;gap:4px;margin:8px 5px 0 0;padding:5px 8px;border-radius:16px;font-size:11px}.fce-checks p.pass{background:#e6f1ea;color:#315f48}.fce-checks p.fail{background:#eef2f4;color:#778594}.fce-checks i{font-style:normal}.fce-alternatives span{display:flex;justify-content:space-between;margin-top:7px}.fce-note{color:#64778c;font-size:12px}.fce-legend-bar{height:10px;border-radius:8px;background:linear-gradient(90deg,#2f6688,#ecebe6,#d96b3f)}.fce-legend-axis{display:flex;justify-content:space-between}.fce-key{display:flex;align-items:center;gap:7px;margin:7px 0}.fce-key i{width:12px;height:12px;border-radius:50%}.fce-key .supported{background:#d96b3f}.fce-key .estimate{background:#e8bca8}.fce-key .hover{background:white;border:2px solid #22d3ee;box-shadow:0 0 8px #22d3ee}.fce-modal{display:none;position:fixed;z-index:100000;inset:0;padding:4vh 5vw;background:rgba(21,32,45,.62);backdrop-filter:blur(7px)}.fce-modal.visible{display:block}.fce-modal-card{position:relative;width:100%;height:100%;border-radius:18px;overflow:hidden;background:white;box-shadow:0 26px 80px rgba(14,23,34,.32)}.fce-modal iframe{width:100%;height:100%;border:0}.fce-modal-close{position:absolute;z-index:4;right:15px;top:14px;width:42px;height:42px;border:0;border-radius:50%;background:#e9eef1;color:#405164;font-size:25px;cursor:pointer}
      @media(max-width:900px){.fce-toolbar{left:10px;right:54px;transform:none;width:auto;max-width:none}.fce-toolbar-main{scrollbar-width:thin}.fce-summary{margin:0}.fce-modal{padding:0}.fce-modal-card{border-radius:0}}
      `;
    document.head.appendChild(style);
  }
};
