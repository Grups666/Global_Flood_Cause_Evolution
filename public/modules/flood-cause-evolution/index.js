/**
 * Global Flood Cause Evolution — Tereon module.
 * Two complementary evidence scales: HydroBASINS level 5 and individual catchments.
 */
window.FloodCauseEvolutionModule = class FloodCauseEvolutionModule {
  constructor(app, manifest = {}) {
    this.app = app;
    this.manifest = manifest;
    this.basePath = manifest.basePath || "/";
    this.dataFile = manifest.dataFile || manifest.datasets?.[0]?.file || "./data/flood-cause-explorer.json";
    this.metric = "intensity_050";
    this.basinLayerId = "flood-cause-hydrobasins";
    this.catchmentLayerId = "flood-cause-catchments";
    this.overviewLayerId = "flood-cause-overview";
    this.legendId = "flood-cause-trend-legend";
    this.selected = null;
    this.toolbar = null;
    this.modal = null;
    this.handleFeatureClick = (payload) => {
      if (![this.basinLayerId, this.catchmentLayerId].includes(payload.layer?.id)) return;
      this.selected = payload.feature;
      this.showInspector(payload.feature, payload.layer.id);
      this.app.draw?.();
    };
    this.handleLayerToggle = (payload) => {
      if (payload.layerId !== this.overviewLayerId) return;
      if (payload.visible) this.showOverview();
      else this.closeOverview();
    };
  }

  async onLoad() {
    const response = await fetch(this.resolve(this.dataFile));
    if (!response.ok) throw new Error(`Unable to load flood-cause data (${response.status})`);
    this.data = await response.json();
    this.basins = (this.data.basins || []).map((item) => ({ ...item, _kind: "basin" }));
    this.catchments = (this.data.catchments || []).map((item) => ({ ...item, _kind: "catchment" }));
    this.addLayers();
    this.ensureStyles();
    this.ensureToolbar();
    this.updateLegend();
    Foundation.eventBus.on(Foundation.Events.FEATURE_CLICK, this.handleFeatureClick);
    Foundation.eventBus.on(Foundation.Events.LAYER_TOGGLE, this.handleLayerToggle);
    this.app.draw?.();
  }

  onUnload() {
    [this.basinLayerId, this.catchmentLayerId, this.overviewLayerId].forEach((id) => this.app.layerManager.removeLayer(id));
    this.app.unregisterLegend?.(this.legendId);
    Foundation.eventBus.off(Foundation.Events.FEATURE_CLICK, this.handleFeatureClick);
    Foundation.eventBus.off(Foundation.Events.LAYER_TOGGLE, this.handleLayerToggle);
    this.toolbar?.remove();
    this.modal?.remove();
  }

  getLayerIds() { return [this.basinLayerId, this.catchmentLayerId, this.overviewLayerId]; }

  resolve(path) {
    if (/^https?:\/\//i.test(path) || path.startsWith("/")) return path;
    return this.basePath + path.replace(/^\.\//, "");
  }

  addLayers() {
    this.app.layerManager.addLayer({
      id: this.basinLayerId,
      name: "HydroBASINS L5 regions",
      type: "vector",
      visible: true,
      interactive: true,
      moduleId: this.manifest.id,
      groupPath: ["flood causes"],
      metadata: { removable: false, evidenceScale: "regional fixed effects" },
      renderer: (ctx, _layer, viewport) => this.renderBasins(ctx, viewport),
      hitTest: (lon, lat) => this.hitTestBasins(lon, lat)
    });
    this.app.layerManager.addLayer({
      id: this.catchmentLayerId,
      name: "Individual catchments",
      type: "vector",
      visible: true,
      interactive: true,
      moduleId: this.manifest.id,
      groupPath: ["flood causes"],
      metadata: { removable: false, evidenceScale: "single-catchment descriptive trend" },
      renderer: (ctx, _layer, viewport) => this.renderCatchments(ctx, viewport),
      hitTest: (lon, lat, viewport) => this.hitTestCatchments(lon, lat, viewport)
    });
    this.app.layerManager.addLayer({
      id: this.overviewLayerId,
      name: "Research overview",
      type: "overlay",
      visible: false,
      interactive: false,
      moduleId: this.manifest.id,
      metadata: { removable: false },
      renderer: () => {}
    });
    this.app.updateLayerList?.();
  }

  renderBasins(ctx, viewport) {
    const shifts = this.worldShifts(viewport);
    for (const basin of this.basins) {
      const metric = basin.metrics?.[this.metric];
      if (!metric) continue;
      const hovered = this.app.hoveredLayer?.id === this.basinLayerId && this.app.hoveredFeatureId === basin.id;
      for (const shift of shifts) {
        ctx.save();
        this.traceGeometry(ctx, basin.geometry, viewport, shift);
        ctx.fillStyle = this.colorFor(metric.slope, 7);
        ctx.globalAlpha = metric.highConfidence ? 0.82 : 0.42;
        ctx.fill("evenodd");
        ctx.globalAlpha = 1;
        const active = this.selected?._kind === "basin" && this.selected.id === basin.id;
        ctx.strokeStyle = active ? "#101827" : hovered ? "#ffffff" : metric.highConfidence ? "#172235" : "rgba(30,41,59,.34)";
        ctx.lineWidth = active ? 2.8 : hovered ? 2.6 : metric.highConfidence ? 1.7 : 0.7;
        ctx.setLineDash(metric.highConfidence || hovered ? [] : [2, 1.8]);
        ctx.stroke();
        ctx.restore();
        if (hovered) {
          const center = this.project(basin.center[0] + shift, basin.center[1], viewport);
          if (center.x > -80 && center.x < viewport.width + 80) this.drawHoverLabel(ctx, center.x, center.y, `${basin.code} · ${this.signed(metric.slope)} pp/dec`);
        }
      }
    }
  }

  renderCatchments(ctx, viewport) {
    const base = (viewport.height / 180) * viewport.scale;
    const shifts = this.worldShifts(viewport);
    for (const catchment of this.catchments) {
      const metric = catchment.metrics?.[this.metric];
      if (!metric) continue;
      const color = this.colorFor(metric.slope, 20);
      const hovered = this.app.hoveredLayer?.id === this.catchmentLayerId && this.app.hoveredFeatureId === catchment.id;
      for (const shift of shifts) {
        const x = viewport.width / 2 + (catchment.lon + shift) * base + viewport.offsetX;
        const y = viewport.height / 2 - catchment.lat * base + viewport.offsetY;
        if (x < -8 || x > viewport.width + 8 || y < -8 || y > viewport.height + 8) continue;
        const active = this.selected?._kind === "catchment" && this.selected.id === catchment.id;
        const radius = active ? 5.3 : hovered ? 5.1 : Math.max(1.7, Math.min(3.5, 1.45 + Math.sqrt(viewport.scale) * 0.55));
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.84;
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = active ? "#0f172a" : hovered ? "#ffffff" : metric.fdrSignificant ? "#f8fafc" : "rgba(15,23,42,.32)";
        ctx.lineWidth = active ? 2.1 : hovered ? 2.2 : metric.fdrSignificant ? 1.4 : 0.45;
        ctx.stroke();
        if (hovered) this.drawHoverLabel(ctx, x, y, `GCIN ${catchment.id} · ${this.signed(metric.slope)} pp/dec`);
      }
    }
  }

  drawHoverLabel(ctx, x, y, text) {
    ctx.save();
    ctx.font = "600 11px Inter, system-ui, sans-serif";
    const width = Math.ceil(ctx.measureText(text).width) + 18;
    const height = 27;
    const left = Math.max(7, Math.min(x + 10, ctx.canvas.width - width - 7));
    const top = Math.max(7, Math.min(y - height - 8, ctx.canvas.height - height - 7));
    const radius = 8;
    ctx.beginPath();
    ctx.moveTo(left + radius, top);
    ctx.lineTo(left + width - radius, top);
    ctx.quadraticCurveTo(left + width, top, left + width, top + radius);
    ctx.lineTo(left + width, top + height - radius);
    ctx.quadraticCurveTo(left + width, top + height, left + width - radius, top + height);
    ctx.lineTo(left + radius, top + height);
    ctx.quadraticCurveTo(left, top + height, left, top + height - radius);
    ctx.lineTo(left, top + radius);
    ctx.quadraticCurveTo(left, top, left + radius, top);
    ctx.closePath();
    ctx.fillStyle = "rgba(15,23,42,.94)";
    ctx.fill();
    ctx.fillStyle = "#f8fafc";
    ctx.textBaseline = "middle";
    ctx.fillText(text, left + 9, top + height / 2 + 0.5);
    ctx.restore();
  }

  worldShifts(viewport) {
    const base = (viewport.height / 180) * viewport.scale;
    const left = (-viewport.width / 2 - viewport.offsetX) / base;
    const right = (viewport.width / 2 - viewport.offsetX) / base;
    const shifts = [];
    for (let segment = Math.floor(left / 360) - 1; segment <= Math.ceil(right / 360) + 1; segment++) shifts.push(segment * 360);
    return shifts;
  }

  traceGeometry(ctx, geometry, viewport, shift) {
    ctx.beginPath();
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    for (const polygon of polygons) {
      for (const ring of polygon) {
        ring.forEach(([lon, lat], index) => {
          const point = this.project(lon + shift, lat, viewport);
          if (index === 0) ctx.moveTo(point.x, point.y); else ctx.lineTo(point.x, point.y);
        });
        ctx.closePath();
      }
    }
  }

  project(lon, lat, viewport) {
    const base = (viewport.height / 180) * viewport.scale;
    return {
      x: viewport.width / 2 + lon * base + viewport.offsetX,
      y: viewport.height / 2 - lat * base + viewport.offsetY
    };
  }

  hitTestBasins(lon, lat) {
    const normalized = ((lon + 180) % 360 + 360) % 360 - 180;
    for (let index = this.basins.length - 1; index >= 0; index--) {
      const basin = this.basins[index];
      if (this.geometryContains(basin.geometry, normalized, lat)) return basin;
    }
    return null;
  }

  geometryContains(geometry, lon, lat) {
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    return polygons.some((polygon) => this.ringContains(polygon[0], lon, lat) && !polygon.slice(1).some((ring) => this.ringContains(ring, lon, lat)));
  }

  ringContains(ring, lon, lat) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  hitTestCatchments(lon, lat, viewport) {
    const normalized = ((lon + 180) % 360 + 360) % 360 - 180;
    const threshold = Math.max(0.08, 7 / ((viewport.height / 180) * viewport.scale));
    let best = null;
    let distance = Infinity;
    for (const catchment of this.catchments) {
      if (!catchment.metrics?.[this.metric]) continue;
      const dx = this.lonDistance(normalized, catchment.lon);
      const dy = lat - catchment.lat;
      const current = Math.hypot(dx, dy);
      if (current < threshold && current < distance) { best = catchment; distance = current; }
    }
    return best;
  }

  lonDistance(a, b) {
    let value = a - b;
    while (value > 180) value -= 360;
    while (value < -180) value += 360;
    return value;
  }

  setMetric(metric) {
    if (!this.data.meta.outcomes[metric]) return;
    this.metric = metric;
    this.toolbar?.querySelectorAll("[data-metric]").forEach((button) => button.classList.toggle("active", button.dataset.metric === metric));
    this.updateLegend();
    if (this.selected) {
      const layerId = this.selected._kind === "basin" ? this.basinLayerId : this.catchmentLayerId;
      this.showInspector(this.selected, layerId);
    }
    this.app.draw?.();
  }

  ensureToolbar() {
    this.toolbar = document.createElement("div");
    this.toolbar.className = "fce-toolbar";
    this.toolbar.innerHTML = `
      <div class="fce-toolbar-label">Flood-generating condition</div>
      <div class="fce-segmented">
        <button data-metric="intensity_050" class="active">Intensity</button>
        <button data-metric="wet_1d">Wet antecedent</button>
      </div>
      <button class="fce-overview-button" data-overview>Research overview</button>`;
    document.body.appendChild(this.toolbar);
    this.toolbar.querySelectorAll("[data-metric]").forEach((button) => button.addEventListener("click", () => this.setMetric(button.dataset.metric)));
    this.toolbar.querySelector("[data-overview]").addEventListener("click", () => this.showOverview());
  }

  updateLegend() {
    const outcome = this.data.meta.outcomes[this.metric];
    this.app.unregisterLegend?.(this.legendId);
    this.app.registerLegend?.(this.legendId, {
      title: outcome.short,
      html: `
        <div class="fce-legend-scale-title">HydroBASINS fixed-effect trend</div>
        <div class="fce-legend-bar"></div>
        <div class="fce-legend-axis"><span>−7</span><span>0</span><span>+7</span></div>
        <div class="fce-legend-scale-title catchment">Catchment logistic probability change</div>
        <div class="fce-legend-bar"></div>
        <div class="fce-legend-axis"><span>−20</span><span>0</span><span>+20</span></div>
        <div class="fce-legend-unit">Percentage points per decade · values outside the scale are clipped</div>
        <div class="fce-legend-key"><i class="solid"></i> High-confidence HydroBASINS signal</div>
        <div class="fce-legend-key"><i class="dash"></i> Estimated regional context</div>
        <div class="fce-legend-key"><i class="dot"></i> Individual catchment</div>`
    });
  }

  showInspector(feature, layerId) {
    const metric = feature.metrics?.[this.metric];
    const outcome = this.data.meta.outcomes[this.metric];
    if (layerId === this.basinLayerId) {
      this.app.showInspector?.(`${feature.code} · ${feature.countries}`, `
        <p class="fce-inspector-lead">HydroBASINS level-5 fixed-effect estimate · ${this.escape(outcome.label)}</p>
        ${this.signal(metric)}
        <div class="fce-grid">
          ${this.fact("95% CI", metric ? `${this.num(metric.ci[0])} to ${this.num(metric.ci[1])}` : "—")}
          ${this.fact("Primary q", this.prob(metric?.q))}
          ${this.fact("Catchments", metric?.catchments ?? "—")}
          ${this.fact("Event observations", metric?.observations?.toLocaleString?.() ?? "—")}
          ${this.fact("POT/Q95 slope", this.signed(metric?.potSlope))}
          ${this.fact("Early–late change", this.signed(metric?.pairedChange, " pp"))}
        </div>
        ${this.gates(metric)}
        <p class="fce-note">Solid outlines identify signals that passed the prespecified FDR, alternative-sample, paired-period, scale, definition and leave-one-catchment-out checks. Color alone is not a significance claim.</p>`);
      return;
    }
    this.app.showInspector?.(`GCIN ${feature.id} · ${feature.country}`, `
      <p class="fce-inspector-lead">Single-catchment annual trend · ${this.escape(outcome.label)}</p>
      ${this.signal(metric, "Logistic probability change")}
      <div class="fce-grid">
        ${this.fact("Record years", metric?.years ?? "Insufficient")}
        ${this.fact("Positive years", metric?.positiveYears ?? "—")}
        ${this.fact("Odds ratio / decade", this.num(metric?.oddsRatio, 3))}
        ${this.fact("Modeled probability · 2000", Number.isFinite(Number(metric?.probability2000)) ? `${this.num(metric.probability2000, 1)}%` : "—")}
        ${this.fact("Modeled probability · 2010", Number.isFinite(Number(metric?.probability2010)) ? `${this.num(metric.probability2010, 1)}%` : "—")}
        ${this.fact("Logistic q", this.prob(metric?.q))}
        ${this.fact("HydroBASINS L5", feature.hydrobasinId || "Unmatched")}
        ${this.fact("Local sub-area", feature.subAreaKm2 ? `${this.num(feature.subAreaKm2, 0)} km²` : "—")}
      </div>
      <div class="fce-status ${metric?.fdrSignificant ? "pass" : "neutral"}">${metric?.fdrSignificant ? "Passes 5% FDR" : "Does not pass 5% FDR / insufficient series"}</div>
      <p class="fce-note">The displayed probability change is the fitted logistic-model contrast between 2000 and 2010, using the catchment's actual observation years to recover the model intercept. It avoids the zero-valued Sen slope degeneracy of annual binary series. The supported inference remains primarily the multi-catchment HydroBASINS estimate, not an isolated gauge.</p>`);
  }

  signal(metric, label = "Fixed-effect slope") {
    const value = metric?.slope;
    return `<div class="fce-signal"><span>${label}</span><strong style="color:${this.colorFor(value, 7)}">${this.signed(value)}</strong><small>percentage points / decade</small></div>`;
  }

  gates(metric) {
    if (!metric) return "";
    const gates = [
      ["Primary FDR", Number(metric.q) < 0.05],
      ["POT direction", metric.sameDirectionPot],
      ["Paired periods", metric.sameDirectionPaired],
      ["Scale stability", metric.scaleStable],
      ["Definition stability", metric.definitionStable],
      ["Jackknife stability", metric.jackknifeStable]
    ];
    return `<div class="fce-gates">${gates.map(([name, pass]) => `<span class="${pass ? "pass" : "fail"}">${pass ? "✓" : "·"} ${name}</span>`).join("")}</div>`;
  }

  fact(label, value) { return `<div class="fce-fact"><span>${label}</span><strong>${value}</strong></div>`; }

  showOverview() {
    this.ensureModal();
    const signals = this.basins.flatMap((basin) => Object.entries(basin.metrics).filter(([, metric]) => metric.highConfidence).map(([outcome, metric]) => ({ basin, outcome, metric }))).sort((a, b) => Math.abs(b.metric.slope) - Math.abs(a.metric.slope));
    const outcome = this.data.meta.outcomes[this.metric];
    this.modal.querySelector(".fce-modal-body").innerHTML = `
      <section class="fce-hero">
        <span class="fce-kicker">1982–2019 · rainfall-driven floods</span>
        <h2>Local change, resolved at two hydrological scales</h2>
        <p>Global averages conceal directionally opposed local signals. Explore fixed-effect trends across eligible HydroBASINS level-5 regions, then inspect the individual catchments that supply spatial context.</p>
      </section>
      <div class="fce-kpis">
        ${this.kpi(this.data.meta.eligibleHydrobasins, "eligible L5 regions")}
        ${this.kpi(this.data.meta.highConfidenceSignals, "high-confidence basin–metric signals")}
        ${this.kpi(this.data.meta.primaryCatchments.toLocaleString(), "primary catchments")}
        ${this.kpi(this.data.meta.annualMaximumEvents.toLocaleString(), "annual-maximum events")}
      </div>
      <section><h3>How to read the map</h3><div class="fce-reading">
        <div><b>Hydrological regions</b><span>Area colors estimate within-catchment temporal change, pooled over neighboring catchments with fixed effects.</span></div>
        <div><b>Individual catchments</b><span>Points show fitted logistic probability changes from 2000 to 2010. Their FDR status is visible on click.</span></div>
        <div><b>Evidence boundary</b><span>Outlined regions pass all robustness gates; magnitude and statistical support are kept separate.</span></div>
      </div></section>
      <section><h3>Largest robust local signals</h3><p class="fce-section-note">Ranked by absolute effect size across both primary indicators.</p>
        <div class="fce-ranking">${signals.slice(0, 10).map((item) => `<button data-basin="${item.basin.id}" data-outcome="${item.outcome}"><span>${this.escape(item.basin.code)} · ${this.escape(this.data.meta.outcomes[item.outcome].short)}</span><strong>${this.signed(item.metric.slope)}</strong><i style="width:${Math.min(100, Math.abs(item.metric.slope) / 7 * 100)}%;background:${this.colorFor(item.metric.slope, 7)}"></i></button>`).join("")}</div>
      </section>
      <section><h3>Current metric</h3><p><b>${this.escape(outcome.label)}</b> — ${this.escape(outcome.definition)}. Units are percentage points per decade.</p><p class="fce-note">Source: Event_Typology reconstructed annual maxima and HydroBASINS v1.c. Period coverage is observed 1982–2019; it is not extrapolated to 1970–2020.</p></section>`;
    this.modal.classList.add("visible");
    this.modal.querySelectorAll("[data-basin]").forEach((button) => button.addEventListener("click", () => {
      this.setMetric(button.dataset.outcome);
      const basin = this.basins.find((item) => item.id === button.dataset.basin);
      if (basin) { this.selected = basin; this.closeOverview(); this.showInspector(basin, this.basinLayerId); this.app.draw?.(); }
    }));
  }

  ensureModal() {
    if (this.modal) return;
    this.modal = document.createElement("div");
    this.modal.className = "fce-modal";
    this.modal.innerHTML = `<div class="fce-modal-card"><button class="fce-close" aria-label="Close overview">×</button><div class="fce-modal-body"></div></div>`;
    document.body.appendChild(this.modal);
    this.modal.querySelector(".fce-close").addEventListener("click", () => this.closeOverview());
    this.modal.addEventListener("click", (event) => { if (event.target === this.modal) this.closeOverview(); });
  }

  closeOverview() { this.modal?.classList.remove("visible"); }
  kpi(value, label) { return `<div><strong>${value}</strong><span>${label}</span></div>`; }
  num(value, digits = 2) { return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—"; }
  prob(value) { return Number.isFinite(Number(value)) ? (Number(value) < 0.001 ? "<0.001" : Number(value).toFixed(3)) : "—"; }
  signed(value, suffix = "") { return Number.isFinite(Number(value)) ? `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(2)}${suffix}` : "—"; }
  escape(value) { const div = document.createElement("div"); div.textContent = value == null ? "" : String(value); return div.innerHTML; }

  colorFor(value, maxAbs) {
    if (!Number.isFinite(Number(value))) return "#aeb8c2";
    const t = Math.max(-1, Math.min(1, Number(value) / maxAbs));
    return t < 0 ? this.mix("#275f83", "#ece7d8", t + 1) : this.mix("#ece7d8", "#c75c36", t);
  }
  mix(a, b, t) {
    const parse = (hex) => [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16));
    const aa = parse(a); const bb = parse(b);
    return `rgb(${aa.map((value, index) => Math.round(value + (bb[index] - value) * t)).join(",")})`;
  }

  ensureStyles() {
    if (document.getElementById("fce-styles")) return;
    const style = document.createElement("style");
    style.id = "fce-styles";
    style.textContent = `
      .fce-toolbar{position:fixed;top:14px;left:50%;transform:translateX(-50%);z-index:850;display:flex;align-items:center;gap:10px;padding:8px 9px 8px 13px;border:1px solid rgba(148,163,184,.35);border-radius:14px;background:rgba(255,255,255,.94);box-shadow:0 10px 30px rgba(15,23,42,.12);backdrop-filter:blur(16px);font:12px/1.2 Inter,system-ui,sans-serif;color:#334155}.fce-toolbar-label{font-weight:700;white-space:nowrap}.fce-segmented{display:flex;padding:3px;border-radius:10px;background:#edf1f4}.fce-segmented button,.fce-overview-button{border:0;border-radius:8px;padding:7px 10px;background:transparent;color:#526171;font:600 11px Inter,system-ui;cursor:pointer}.fce-segmented button.active{background:#fff;color:#173d55;box-shadow:0 2px 8px rgba(15,23,42,.1)}.fce-overview-button{background:#173d55;color:#fff}.fce-legend-scale-title{margin:5px 0 4px;font-size:10px;font-weight:700;color:#475569}.fce-legend-scale-title.catchment{margin-top:9px}.fce-legend-bar{height:10px;border-radius:99px;background:linear-gradient(90deg,#275f83,#ece7d8 50%,#c75c36)}.fce-legend-axis{display:flex;justify-content:space-between;margin-top:3px;font:10px/1.2 ui-monospace,monospace;color:#64748b}.fce-legend-unit{margin:7px 0 8px;font-size:10px;color:#64748b}.fce-legend-key{display:flex;align-items:center;gap:7px;margin-top:5px;font-size:10px;color:#475569}.fce-legend-key i{display:inline-block;width:18px;height:9px}.fce-legend-key .solid{border:2px solid #172235;background:#d5c9a8}.fce-legend-key .dash{border:1px dashed #475569;background:#d5c9a8}.fce-legend-key .dot{width:8px;height:8px;border-radius:50%;background:#527b95;border:1px solid #334155}.fce-inspector-lead,.fce-note{font-size:11px;line-height:1.55;color:#64748b}.fce-signal{margin:12px 0;padding:14px;border-radius:12px;background:#f4f6f7}.fce-signal span,.fce-signal small{display:block;color:#64748b;font-size:10px}.fce-signal strong{display:block;margin:5px 0 2px;font-size:28px;letter-spacing:-.04em}.fce-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.fce-fact{padding:10px;border:1px solid #e2e8f0;border-radius:10px}.fce-fact span,.fce-fact strong{display:block}.fce-fact span{font-size:9px;text-transform:uppercase;letter-spacing:.05em;color:#7c8b99}.fce-fact strong{margin-top:4px;font-size:12px;color:#263646}.fce-gates{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}.fce-gates span,.fce-status{padding:5px 8px;border-radius:99px;font:600 9px Inter,system-ui}.fce-gates .pass,.fce-status.pass{background:#e4eee7;color:#315e45}.fce-gates .fail,.fce-status.neutral{background:#eef1f3;color:#788592}.fce-status{display:inline-block;margin-top:12px}.fce-modal{position:fixed;inset:0;z-index:1100;display:none;align-items:center;justify-content:center;padding:28px;background:rgba(15,23,42,.48);backdrop-filter:blur(9px)}.fce-modal.visible{display:flex}.fce-modal-card{position:relative;width:min(900px,94vw);max-height:90vh;overflow:auto;border:1px solid rgba(255,255,255,.5);border-radius:22px;background:#f8fafb;box-shadow:0 32px 90px rgba(15,23,42,.28);color:#223143;font:13px/1.6 Inter,system-ui,sans-serif}.fce-close{position:sticky;float:right;top:14px;margin:14px 14px -50px 0;z-index:2;width:34px;height:34px;border:0;border-radius:50%;background:#e7ecef;color:#415161;font-size:22px;cursor:pointer}.fce-modal-body{padding:40px}.fce-hero{padding:4px 48px 26px 0;border-bottom:1px solid #dce3e8}.fce-kicker{font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#9b6a26}.fce-hero h2{max-width:680px;margin:9px 0 12px;font-size:34px;line-height:1.08;letter-spacing:-.04em;color:#172638}.fce-hero p{max-width:720px;margin:0;color:#5f6f7e}.fce-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:20px 0}.fce-kpis div{padding:15px;border:1px solid #dce3e8;border-radius:13px;background:#fff}.fce-kpis strong,.fce-kpis span{display:block}.fce-kpis strong{font-size:22px;color:#173d55}.fce-kpis span{margin-top:4px;font-size:10px;color:#73818f}.fce-modal section h3{margin:26px 0 8px;font-size:15px;color:#243648}.fce-reading{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.fce-reading div{padding:15px;border-radius:13px;background:#edf2f4}.fce-reading b,.fce-reading span{display:block}.fce-reading span{margin-top:5px;font-size:11px;color:#667684}.fce-section-note{margin-top:-5px;color:#788795;font-size:11px}.fce-ranking{display:grid;grid-template-columns:1fr 1fr;gap:7px}.fce-ranking button{position:relative;overflow:hidden;display:flex;justify-content:space-between;gap:10px;padding:11px 12px;border:1px solid #dce3e8;border-radius:10px;background:#fff;color:#3e4e5d;text-align:left;cursor:pointer}.fce-ranking button span,.fce-ranking button strong{position:relative;z-index:1;font-size:11px}.fce-ranking button i{position:absolute;bottom:0;left:0;height:3px}.fce-ranking button:hover{border-color:#8fa7b5;transform:translateY(-1px)}@media(max-width:760px){.fce-toolbar{top:auto;bottom:12px;max-width:calc(100vw - 24px);flex-wrap:wrap;justify-content:center}.fce-toolbar-label{display:none}.fce-modal{padding:0}.fce-modal-card{width:100%;max-height:100%;height:100%;border-radius:0}.fce-modal-body{padding:24px}.fce-hero h2{font-size:27px}.fce-kpis{grid-template-columns:1fr 1fr}.fce-reading{grid-template-columns:1fr}.fce-ranking{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }
};
