/** Interactive catchment-scale explorer for flood-generating process change. */
window.FloodCauseEvolutionModule = class FloodCauseEvolutionModule {
  constructor(app, manifest = {}) {
    this.app = app;
    this.manifest = manifest;
    this.basePath = manifest.basePath || "/";
    this.dataFile = manifest.dataFile || manifest.datasets?.[0]?.file;
    this.layerId = "flood-cause-catchments";
    this.legendId = "flood-cause-legend";
    this.scope = "overall";
    this.outcomeKey = "direct_runoff_volume";
    this.mechanism = "Dry-Intensity";
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
    this.app.resize?.();
    this.redraw();
  }

  onUnload() {
    this.app.layerManager.removeLayer(this.layerId);
    this.app.unregisterLegend?.(this.legendId);
    Foundation.eventBus.off(Foundation.Events.FEATURE_CLICK, this.handleClick);
    document.removeEventListener("pointermove", this.handlePointer);
    document.removeEventListener("keydown", this.handleKey);
    this.toolbar?.remove();
    this.tooltip?.remove();
    this.modal?.remove();
  }

  getLayerIds() { return [this.layerId]; }

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
    if (this.scope === "overall") return item.overall?.[this.outcomeKey];
    return item.processes?.[this.mechanism]?.[this.outcomeKey];
  }

  outcome() { return this.data.meta.outcomes[this.outcomeKey]; }

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
    const process = this.scope === "process" ? `${this.mechanism.replace("-", " + ")} · ` : "";
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
    if (!['overall', 'process'].includes(scope)) return;
    this.scope = scope;
    this.outcomeKey = scope === "overall" ? "direct_runoff_volume" : "mechanism_frequency";
    this.selected = null;
    this.updateToolbar();
    this.updateLegend();
    this.redraw();
  }

  setOutcome(outcome) {
    if (!this.data.meta.outcomes[outcome]) return;
    this.outcomeKey = outcome;
    this.updateToolbar();
    this.updateLegend();
    if (this.selected && this.metric(this.selected)) this.showInspector(this.selected);
    this.redraw();
  }

  setMechanism(mechanism) {
    if (!this.data.meta.mechanisms.some((item) => item.id === mechanism)) return;
    this.mechanism = mechanism;
    this.selected = null;
    this.updateToolbar();
    this.updateLegend();
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
      <div class="fce-primary-row">
        <div class="fce-scope"><button data-scope="overall">All selected floods</button><button data-scope="process">By generating process</button></div>
        <select data-mechanism aria-label="Flood-generating process">${this.data.meta.mechanisms.map((item) => `<option value="${item.id}">${item.label}</option>`).join("")}</select>
        <div class="fce-outcomes" data-outcomes></div>
        <button class="fce-overview" data-overview>Research overview</button>
      </div>
      <div class="fce-secondary-row"><div data-count></div><div class="fce-evidence"><button data-evidence="supported">Supported focus</button><button data-evidence="all">All estimates</button></div></div>`;
    document.body.appendChild(this.toolbar);
    this.toolbar.querySelectorAll("[data-scope]").forEach((button) => button.onclick = () => this.setScope(button.dataset.scope));
    this.toolbar.querySelector("[data-mechanism]").onchange = (event) => this.setMechanism(event.target.value);
    this.toolbar.querySelectorAll("[data-evidence]").forEach((button) => button.onclick = () => this.setEvidence(button.dataset.evidence));
    this.toolbar.querySelector("[data-overview]").onclick = () => this.showOverview();
  }

  updateToolbar() {
    if (!this.toolbar) return;
    const outcomeKeys = this.scope === "overall"
      ? ["direct_runoff_volume", "flood_peak", "exceedance_frequency"]
      : ["mechanism_frequency", "mechanism_share", "rainfall_concentration", "antecedent_wetness", "direct_runoff_volume", "flood_peak"];
    this.toolbar.querySelectorAll("[data-scope]").forEach((button) => button.classList.toggle("active", button.dataset.scope === this.scope));
    const select = this.toolbar.querySelector("[data-mechanism]");
    select.hidden = this.scope !== "process";
    select.value = this.mechanism;
    const outcomes = this.toolbar.querySelector("[data-outcomes]");
    outcomes.innerHTML = outcomeKeys.map((key) => `<button data-outcome="${key}" class="${key === this.outcomeKey ? "active" : ""}">${this.data.meta.outcomes[key].short}</button>`).join("");
    outcomes.querySelectorAll("[data-outcome]").forEach((button) => button.onclick = () => this.setOutcome(button.dataset.outcome));
    this.toolbar.querySelectorAll("[data-evidence]").forEach((button) => button.classList.toggle("active", button.dataset.evidence === this.evidenceView));
    const available = this.catchments.map((item) => this.metric(item)).filter(Boolean);
    const supported = available.filter((metric) => metric.supported);
    this.toolbar.querySelector("[data-count]").innerHTML = `<strong>${supported.length.toLocaleString()}</strong> supported · ${available.length.toLocaleString()} estimable catchments <span>· ${this.scope === "process" ? this.mechanism.replace("-", " + ") : "all Q95 floods"}</span>`;
  }

  showInspector(item) {
    const metric = this.metric(item);
    if (!metric) return;
    const outcome = this.outcome();
    const process = this.scope === "process" ? this.mechanism.replace("-", " + ") : "All selected floods";
    const sampleDetail = this.outcomeKey === "exceedance_frequency"
      ? "same direction for Q90 and Q97.5; annual maximum is not a fixed-threshold frequency test"
      : "same direction for Q90, Q97.5 and annual maximum";
    const checks = [
      { name: "p < 0.05", pass: metric.pPass, detail: `two-sided p = ${this.prob(metric.p)}` },
      { name: "Alternative extreme samples", pass: metric.sampleStable, detail: sampleDetail },
      ...(this.scope === "process" ? [{ name: "Classification threshold", pass: metric.classificationStable, detail: "same direction at concentration cutoffs 0.40 and 0.60" }] : []),
      { name: "Leave-one-year-out", pass: metric.leaveOneYearStable, detail: "removing any one year does not reverse direction" },
    ];
    const passed = checks.filter((check) => check.pass).length;
    this.app.showInspector?.(`GCIN ${item.id} · ${item.country}`, `
      <p class="fce-inspector-lead">${this.escape(process)} · ${this.escape(outcome.label)}</p>
      <div class="fce-result"><span>${this.escape(this.direction(metric.slope))}</span><strong>${this.displayEffect(metric.slope, outcome.digits)}</strong><small>${this.escape(outcome.unit)}</small><p>${this.escape(this.physicalMeaning(metric))}</p></div>
      <div class="fce-grid">
        ${this.fact("Fitted record change", `${this.num(metric.from, outcome.digits)} → ${this.num(metric.to, outcome.digits)}`)}
        ${this.fact("95% interval", `${this.signed(metric.ci?.[0], outcome.digits)} to ${this.signed(metric.ci?.[1], outcome.digits)}`)}
        ${this.fact("p value", this.prob(metric.p))}
        ${this.fact("Observed years", this.integer(metric.years))}
        ${this.fact("Selected events", this.integer(metric.events))}
        ${this.fact("Record", `${metric.firstYear}–${metric.lastYear}`)}
        ${this.outcomeKey === "antecedent_wetness" && Number.isFinite(Number(metric.relative)) ? this.fact("Relative to local mean", `${this.signed(metric.relative, 2)}% per 10 years`) : ""}
      </div>
      <div class="fce-checks"><div><b>Evidence checks</b><span>${passed}/${checks.length} passed</span></div>${checks.map((check, index) => `<p class="${check.pass ? "pass" : "fail"}" title="${this.escape(check.detail)}"><i>${index + 1}</i>${check.pass ? "✓" : "·"} ${this.escape(check.name)}</p>`).join("")}</div>
      <div class="fce-alternatives"><b>Alternative extreme samples</b>${Object.entries(metric.alternatives || {}).filter(([name]) => !(this.outcomeKey === "exceedance_frequency" && name === "Annual maximum")).map(([name, value]) => `<span>${this.escape(name)} <strong>${this.signed(value, outcome.digits)}</strong></span>`).join("")}</div>
      <p class="fce-note">${this.escape(outcome.meaning)} This is a within-catchment temporal estimate. It does not extrapolate to ungauged areas and does not, by itself, prove causal attribution.</p>`);
  }

  physicalMeaning(metric) {
    const from = this.num(metric.from, this.outcome().digits);
    const to = this.num(metric.to, this.outcome().digits);
    const slope = this.signed(metric.slope, this.outcome().digits);
    if (this.outcomeKey === "mechanism_share") return `Among selected large floods, this process changes from about ${from}% to ${to}% across the fitted record (${slope} percentage points per 10 years).`;
    if (this.outcomeKey === "rainfall_concentration") return `For selected large floods generated by this process, rainfall becomes ${Number(metric.slope) >= 0 ? "more concentrated" : "more distributed"}: the percentage of total event rainfall falling on the single rainiest day changes from about ${from}% to ${to}% across the fitted record.`;
    if (this.outcomeKey === "antecedent_wetness") return `The normalized antecedent soil saturation index changes from about ${from} to ${to} across the fitted record.`;
    if (this.outcomeKey === "mechanism_frequency") return `This process changes from about ${from} to ${to} selected large floods per observed year across the fitted record.`;
    if (this.outcomeKey === "exceedance_frequency") return `The fixed-threshold Q95-event frequency changes from about ${from} to ${to} events per observed year across the fitted record.`;
    if (this.outcomeKey === "direct_runoff_volume") return `Mean selected-event direct stormflow volume changes from about ${from} to ${to} mm across the fitted record.`;
    return `Mean maximum daily streamflow within selected events changes from about ${from} to ${to} mm/day across the fitted record.`;
  }

  direction(value) {
    const positive = Number(value) >= 0;
    if (this.outcomeKey === "mechanism_share") return positive ? "larger process share" : "smaller process share";
    if (["mechanism_frequency", "exceedance_frequency"].includes(this.outcomeKey)) return positive ? "more frequent" : "less frequent";
    if (this.outcomeKey === "rainfall_concentration") return positive ? "more concentrated rainfall" : "more distributed rainfall";
    if (this.outcomeKey === "antecedent_wetness") return positive ? "wetter antecedent state" : "drier antecedent state";
    return positive ? "larger flood response" : "smaller flood response";
  }

  updateLegend() {
    const outcome = this.outcome();
    const metrics = this.catchments.map((item) => this.metric(item)).filter(Boolean);
    const supported = metrics.filter((metric) => metric.supported);
    this.app.unregisterLegend?.(this.legendId);
    this.app.registerLegend?.(this.legendId, {
      title: this.scope === "process" ? `${this.mechanism.replace("-", " + ")} · ${outcome.short}` : outcome.short,
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
  num(value, digits = 2) { return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—"; }
  signed(value, digits = 2) { return Number.isFinite(Number(value)) ? `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(digits)}` : "—"; }
  integer(value) { return Number.isFinite(Number(value)) ? Number(value).toLocaleString() : "—"; }
  displayEffect(value, digits = 2) { const base = this.signed(value, digits); return ["mechanism_share", "rainfall_concentration"].includes(this.outcomeKey) && base !== "—" ? `${base} pp` : base; }
  prob(value) { return Number.isFinite(Number(value)) ? (Number(value) < 0.001 ? "<0.001" : Number(value).toFixed(3)) : "—"; }
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
      .fce-toolbar{position:fixed;z-index:10020;top:16px;left:50%;transform:translateX(-50%);width:min(1120px,calc(100vw - 380px));padding:8px 10px;border:1px solid #d9e3e9;border-radius:15px;background:rgba(255,255,255,.97);box-shadow:0 10px 34px rgba(28,43,58,.13);font:13px/1.25 Inter,system-ui;color:#263548}.fce-primary-row,.fce-secondary-row,.fce-scope,.fce-outcomes,.fce-evidence{display:flex;align-items:center;gap:6px}.fce-primary-row{flex-wrap:wrap}.fce-outcomes{flex:1;flex-wrap:wrap}.fce-toolbar button,.fce-toolbar select{border:0;border-radius:9px;background:#eef3f5;color:#526274;padding:9px 11px;font:600 12px Inter,system-ui;cursor:pointer}.fce-toolbar button.active{background:#174b61;color:white}.fce-toolbar select{background:#fff;border:1px solid #d7e1e7;color:#263548}.fce-overview{margin-left:auto!important;background:#173f54!important;color:#fff!important}.fce-secondary-row{justify-content:space-between;margin-top:7px;padding-top:7px;border-top:1px solid #e3eaee;color:#607184}.fce-secondary-row strong{color:#16778a;font-size:15px}.fce-secondary-row span{color:#84919d}.fce-evidence button{padding:6px 9px}.fce-tooltip{display:none;position:fixed;z-index:2147483000;max-width:320px;padding:13px 15px;border-radius:12px;background:#172337;color:white;box-shadow:0 16px 38px rgba(18,28,41,.34);font:13px/1.45 Inter,system-ui;pointer-events:none}.fce-tooltip.visible{display:block}.fce-tooltip strong,.fce-tooltip span,.fce-tooltip b,.fce-tooltip em{display:block}.fce-tooltip strong{font-size:14px}.fce-tooltip span{color:#cbd6df}.fce-tooltip b{margin-top:3px;color:#67e8f9;font-size:18px}.fce-tooltip small{font-size:11px;color:#e5eef3}.fce-tooltip em{font-style:normal;color:#9fe0bd;font-size:11px}.fce-inspector-lead{color:#64778c}.fce-result{padding:16px 18px;border-radius:14px;background:#f1f5f6;border-left:3px solid #22d3ee}.fce-result span,.fce-result strong,.fce-result small{display:block}.fce-result strong{font-size:34px;color:#2f6688}.fce-result small{color:#64778c}.fce-result p{margin:9px 0 0;padding-top:9px;border-top:1px solid #d8e2e7;color:#29475a}.fce-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}.fce-grid>div{padding:10px;border:1px solid #dbe5eb;border-radius:10px}.fce-grid span,.fce-grid strong{display:block}.fce-grid span{font-size:10px;text-transform:uppercase;color:#75869a}.fce-checks,.fce-alternatives{margin-top:13px;padding:12px;border:1px solid #dbe5eb;border-radius:12px}.fce-checks>div{display:flex;justify-content:space-between}.fce-checks p{display:inline-flex;align-items:center;gap:4px;margin:8px 5px 0 0;padding:5px 8px;border-radius:16px;font-size:11px}.fce-checks p.pass{background:#e6f1ea;color:#315f48}.fce-checks p.fail{background:#eef2f4;color:#778594}.fce-checks i{font-style:normal}.fce-alternatives span{display:flex;justify-content:space-between;margin-top:7px}.fce-note{color:#64778c;font-size:12px}.fce-legend-bar{height:10px;border-radius:8px;background:linear-gradient(90deg,#2f6688,#ecebe6,#d96b3f)}.fce-legend-axis{display:flex;justify-content:space-between}.fce-key{display:flex;align-items:center;gap:7px;margin:7px 0}.fce-key i{width:12px;height:12px;border-radius:50%}.fce-key .supported{background:#d96b3f}.fce-key .estimate{background:#e8bca8}.fce-key .hover{background:white;border:2px solid #22d3ee;box-shadow:0 0 8px #22d3ee}.fce-modal{display:none;position:fixed;z-index:100000;inset:0;padding:4vh 5vw;background:rgba(21,32,45,.62);backdrop-filter:blur(7px)}.fce-modal.visible{display:block}.fce-modal-card{position:relative;width:100%;height:100%;border-radius:18px;overflow:hidden;background:white;box-shadow:0 26px 80px rgba(14,23,34,.32)}.fce-modal iframe{width:100%;height:100%;border:0}.fce-modal-close{position:absolute;z-index:4;right:15px;top:14px;width:42px;height:42px;border:0;border-radius:50%;background:#e9eef1;color:#405164;font-size:25px;cursor:pointer}@media(max-width:900px){.fce-toolbar{left:10px;right:10px;transform:none;width:auto}.fce-secondary-row{align-items:flex-start}.fce-modal{padding:0}.fce-modal-card{border-radius:0}}`;
    document.head.appendChild(style);
  }
};
