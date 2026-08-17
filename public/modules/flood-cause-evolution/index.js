/**
 * Global Flood Cause Evolution — interactive Tereon module.
 * Continuous flood-generating-condition trends at HydroBASINS L5 and catchment scales.
 */
window.FloodCauseEvolutionModule = class FloodCauseEvolutionModule {
  constructor(app, manifest = {}) {
    this.app = app;
    this.manifest = manifest;
    this.basePath = manifest.basePath || "/";
    this.dataFile = manifest.dataFile || manifest.datasets?.[0]?.file || "./data/flood-cause-explorer.json";
    this.metric = "intensity_fraction";
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
    this.ensureStyles();
    this.addLayers();
    this.ensureToolbar();
    this.updateLegend();
    Foundation.eventBus.on(Foundation.Events.FEATURE_CLICK, this.handleFeatureClick);
    Foundation.eventBus.on(Foundation.Events.LAYER_TOGGLE, this.handleLayerToggle);
    this.app.draw?.();
  }

  onUnload() {
    [this.basinLayerId, this.catchmentLayerId, this.overviewLayerId]
      .forEach((id) => this.app.layerManager.removeLayer(id));
    this.app.unregisterLegend?.(this.legendId);
    Foundation.eventBus.off(Foundation.Events.FEATURE_CLICK, this.handleFeatureClick);
    Foundation.eventBus.off(Foundation.Events.LAYER_TOGGLE, this.handleLayerToggle);
    this.toolbar?.remove();
    this.modal?.remove();
  }

  getLayerIds() {
    return [this.basinLayerId, this.catchmentLayerId, this.overviewLayerId];
  }

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
      groupPath: ["flood-generating conditions"],
      metadata: { removable: false, evidenceScale: "multi-catchment region" },
      renderer: (ctx, _layer, viewport) => this.renderBasins(ctx, viewport),
      hitTest: (lon, lat) => this.hitTestBasins(lon, lat)
    });
    this.app.layerManager.addLayer({
      id: this.catchmentLayerId,
      name: "Eligible individual catchments",
      type: "vector",
      visible: true,
      interactive: true,
      moduleId: this.manifest.id,
      groupPath: ["flood-generating conditions"],
      metadata: { removable: false, evidenceScale: "single catchment" },
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
    const limit = this.outcome().limit;
    for (const basin of this.basins) {
      const metric = basin.metrics?.[this.metric];
      if (!metric) continue;
      const hovered = this.app.hoveredLayer?.id === this.basinLayerId && this.app.hoveredFeatureId === basin.id;
      const active = this.selected?._kind === "basin" && this.selected.id === basin.id;
      for (const shift of shifts) {
        ctx.save();
        this.traceGeometry(ctx, basin.geometry, viewport, shift);
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
        ctx.miterLimit = 1.4;
        ctx.fillStyle = this.colorFor(metric.slope, limit);
        ctx.globalAlpha = metric.strong ? 0.82 : metric.limited ? 0.46 : 0.63;
        ctx.fill("evenodd");
        ctx.globalAlpha = 1;
        ctx.setLineDash([]);

        if (hovered || active) {
          ctx.save();
          ctx.shadowColor = hovered ? "rgba(34, 211, 238, .98)" : "rgba(6, 182, 212, .94)";
          ctx.shadowBlur = hovered ? 28 : 22;
          ctx.strokeStyle = hovered ? "rgba(103, 232, 249, .98)" : "rgba(34, 211, 238, .98)";
          ctx.lineWidth = hovered ? 1.2 : 1.15;
          ctx.stroke();
          ctx.restore();
        } else {
          ctx.strokeStyle = "rgba(15, 23, 42, .72)";
          ctx.lineWidth = 0.72;
          ctx.stroke();
        }
        ctx.restore();

        if (hovered) {
          const center = this.project(basin.center[0] + shift, basin.center[1], viewport);
          if (center.x > -120 && center.x < viewport.width + 120) {
            this.drawHoverLabel(ctx, center.x, center.y,
              `${basin.code} · ${this.direction(metric.slope)} · ${this.signed(metric.slope, this.outcome().digits)}`);
          }
        }
      }
    }
  }

  renderCatchments(ctx, viewport) {
    const base = (viewport.height / 180) * viewport.scale;
    const shifts = this.worldShifts(viewport);
    const limit = this.catchmentLimit();
    for (const catchment of this.catchments) {
      const metric = catchment.metrics?.[this.metric];
      if (!metric) continue;
      const hovered = this.app.hoveredLayer?.id === this.catchmentLayerId && this.app.hoveredFeatureId === catchment.id;
      const active = this.selected?._kind === "catchment" && this.selected.id === catchment.id;
      for (const shift of shifts) {
        const x = viewport.width / 2 + (catchment.lon + shift) * base + viewport.offsetX;
        const y = viewport.height / 2 - catchment.lat * base + viewport.offsetY;
        if (x < -9 || x > viewport.width + 9 || y < -9 || y > viewport.height + 9) continue;
        const radius = active ? 4.7 : Math.max(1.8, Math.min(3.35, 1.5 + Math.sqrt(viewport.scale) * 0.5));
        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = this.colorFor(metric.slope, limit);
        ctx.globalAlpha = 0.82;
        ctx.fill();
        ctx.globalAlpha = 1;
        if (hovered || active) {
          ctx.shadowColor = hovered ? "rgba(34, 211, 238, .98)" : "rgba(6, 182, 212, .94)";
          ctx.shadowBlur = hovered ? 22 : 17;
          ctx.strokeStyle = "rgba(103, 232, 249, .98)";
          ctx.lineWidth = 1.15;
        } else {
          ctx.strokeStyle = metric.fdrSupported ? "rgba(15, 23, 42, .9)" : "rgba(15, 23, 42, .42)";
          ctx.lineWidth = metric.fdrSupported ? 1.05 : 0.5;
        }
        ctx.stroke();
        ctx.restore();
        if (hovered) {
          this.drawHoverLabel(ctx, x, y,
            `GCIN ${catchment.id} · ${this.direction(metric.slope)} · ${this.signed(metric.slope, this.outcome().digits)}`);
        }
      }
    }
  }

  drawHoverLabel(ctx, x, y, text) {
    ctx.save();
    ctx.font = "650 13px Inter, system-ui, sans-serif";
    const width = Math.ceil(ctx.measureText(text).width) + 22;
    const height = 32;
    const left = Math.max(8, Math.min(x + 11, ctx.canvas.width - width - 8));
    const top = Math.max(8, Math.min(y - height - 9, ctx.canvas.height - height - 8));
    this.roundRect(ctx, left, top, width, height, 9);
    ctx.fillStyle = "rgba(15, 23, 42, .94)";
    ctx.fill();
    ctx.fillStyle = "#f8fafc";
    ctx.textBaseline = "middle";
    ctx.fillText(text, left + 11, top + height / 2 + 0.5);
    ctx.restore();
  }

  roundRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r);
    ctx.closePath();
  }

  worldShifts(viewport) {
    const base = (viewport.height / 180) * viewport.scale;
    const left = (-viewport.width / 2 - viewport.offsetX) / base;
    const right = (viewport.width / 2 - viewport.offsetX) / base;
    const shifts = [];
    for (let segment = Math.floor(left / 360) - 1; segment <= Math.ceil(right / 360) + 1; segment += 1) {
      shifts.push(segment * 360);
    }
    return shifts;
  }

  traceGeometry(ctx, geometry, viewport, shift) {
    ctx.beginPath();
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    for (const polygon of polygons) {
      for (const ring of polygon) {
        ring.forEach(([lon, lat], index) => {
          const point = this.project(lon + shift, lat, viewport);
          if (index === 0) ctx.moveTo(point.x, point.y);
          else ctx.lineTo(point.x, point.y);
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
    for (let index = this.basins.length - 1; index >= 0; index -= 1) {
      const basin = this.basins[index];
      if (basin.metrics?.[this.metric] && this.geometryContains(basin.geometry, normalized, lat)) return basin;
    }
    return null;
  }

  geometryContains(geometry, lon, lat) {
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    return polygons.some((polygon) => this.ringContains(polygon[0], lon, lat)
      && !polygon.slice(1).some((ring) => this.ringContains(ring, lon, lat)));
  }

  ringContains(ring, lon, lat) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  hitTestCatchments(lon, lat, viewport) {
    const normalized = ((lon + 180) % 360 + 360) % 360 - 180;
    const threshold = Math.max(0.08, 8 / ((viewport.height / 180) * viewport.scale));
    let best = null;
    let distance = Infinity;
    for (const catchment of this.catchments) {
      if (!catchment.metrics?.[this.metric]) continue;
      const current = Math.hypot(this.lonDistance(normalized, catchment.lon), lat - catchment.lat);
      if (current < threshold && current < distance) {
        best = catchment;
        distance = current;
      }
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
    this.toolbar?.querySelectorAll("[data-metric]")
      .forEach((button) => button.classList.toggle("active", button.dataset.metric === metric));
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
      <div class="fce-segmented" aria-label="Metric selector">
        <button data-metric="intensity_fraction" class="active">Rainfall concentration</button>
        <button data-metric="intensity_050">Intensity-type share</button>
        <button data-metric="ssi_1d">SSI 1d</button>
        <button data-metric="ssi_3d">3d</button>
        <button data-metric="ssi_7d">7d</button>
        <button data-metric="ssi_30d">30d</button>
      </div>
      <button class="fce-overview-button" data-overview>Research overview</button>`;
    document.body.appendChild(this.toolbar);
    this.toolbar.querySelectorAll("[data-metric]")
      .forEach((button) => button.addEventListener("click", () => this.setMetric(button.dataset.metric)));
    this.toolbar.querySelector("[data-overview]").addEventListener("click", () => this.showOverview());
  }

  updateLegend() {
    const outcome = this.outcome();
    const limit = outcome.limit;
    this.app.unregisterLegend?.(this.legendId);
    this.app.registerLegend?.(this.legendId, {
      title: outcome.short,
      html: `
        <div class="fce-legend-scale-title">HydroBASINS L5 trend</div>
        <div class="fce-legend-bar"></div>
        <div class="fce-legend-axis"><span>${this.axisValue(-limit)}</span><span>0</span><span>+${this.axisValue(limit)}</span></div>
        <div class="fce-legend-directions"><span>${this.escape(outcome.low)}</span><span>${this.escape(outcome.high)}</span></div>
        <div class="fce-legend-unit">${this.escape(outcome.unit)}. Values beyond the color scale are clipped.</div>
        <div class="fce-legend-key"><i class="boundary"></i> Eligible L5 region (thin black boundary)</div>
        <div class="fce-legend-key"><i class="limited"></i> Limited sample: 5–19 catchments</div>
        <div class="fce-legend-key"><i class="glow"></i> Hover / selected feature</div>
        <div class="fce-legend-key"><i class="dot"></i> Eligible individual catchment</div>
        <div class="fce-legend-note">Strong evidence is identified in the inspector; color alone is not a significance claim.</div>`
    });
  }

  showInspector(feature, layerId) {
    const metric = feature.metrics?.[this.metric];
    const outcome = this.outcome();
    if (!metric) return;
    if (layerId === this.basinLayerId) {
      const status = metric.strong
        ? "Strong regional evidence"
        : metric.limited
          ? "Regional estimate · limited sample"
          : "Regional estimate";
      const statusClass = metric.strong ? "pass" : metric.limited ? "limited" : "neutral";
      const interpretation = this.interpretation(metric.slope);
      this.app.showInspector?.(`${feature.code} · ${feature.countries}`, `
        <p class="fce-inspector-lead">HydroBASINS level-5 multi-catchment estimate · ${this.escape(outcome.label)}</p>
        <div class="fce-status ${statusClass}">${status}</div>
        <div class="fce-plain-result">${this.escape(interpretation)}</div>
        ${this.signal(metric, "Change per decade")}
        <div class="fce-grid">
          ${this.fact("95% CI", `${this.signed(metric.ci?.[0], outcome.digits)} to ${this.signed(metric.ci?.[1], outcome.digits)}`)}
          ${this.fact("Complete-family q", this.prob(metric.q))}
          ${this.fact("Catchments", this.integer(metric.catchments))}
          ${this.fact("Event observations", this.integer(metric.observations))}
          ${this.fact("Mean condition", this.num(metric.mean, outcome.digits))}
          ${this.fact("HydroBASINS L5", feature.code)}
        </div>
        ${this.trajectory(metric, outcome)}
        ${this.sensitivity(metric, outcome)}
        ${this.drivers(feature)}
        ${this.gates(metric)}
        <p class="fce-note">${this.escape(outcome.definition)} ${metric.limited
          ? `This region clears the display floor of ${this.data.meta.minimumCatchments} catchments and ${this.data.meta.minimumObservations} observations, but has fewer than ${this.data.meta.strongMinimumCatchments} catchments and cannot receive the strongest evidence grade.`
          : "The estimate pools repeated observations within neighboring catchments while controlling stable differences among them."}</p>`);
      return;
    }

    this.app.showInspector?.(`GCIN ${feature.id} · ${feature.country}`, `
      <p class="fce-inspector-lead">Eligible single-catchment Theil–Sen trend · ${this.escape(outcome.label)}</p>
      <div class="fce-plain-result">${this.escape(this.interpretation(metric.slope, true))}</div>
      ${this.signal(metric, "Catchment change per decade")}
      <div class="fce-grid">
        ${this.fact("95% CI", `${this.signed(metric.ci?.[0], outcome.digits)} to ${this.signed(metric.ci?.[1], outcome.digits)}`)}
        ${this.fact("Catchment-family q", this.prob(metric.q))}
        ${this.fact("Selected events", this.integer(metric.observations))}
        ${this.fact("Observed event years", this.integer(metric.years))}
        ${this.fact("Event-year range", `${metric.firstYear}–${metric.lastYear}`)}
        ${this.fact("Time span", `${metric.span} years`)}
        ${this.fact("Kendall tau", this.signed(metric.tau, 3))}
        ${this.fact("HydroBASINS L5", feature.hydrobasinId || "Unmatched")}
      </div>
      <div class="fce-status ${metric.fdrSupported ? "pass" : "neutral"}">${metric.fdrSupported ? "Passes catchment-level 5% FDR" : "Does not pass catchment-level 5% FDR"}</div>
      <p class="fce-note">Only catchments with at least 10 selected POT/Q95 events spanning at least 20 years are displayed. Single-catchment points give local context; the multi-catchment HydroBASINS layer is the primary spatial evidence.</p>`);
  }

  interpretation(slope, single = false) {
    const direction = Number(slope) >= 0 ? this.outcome().high : this.outcome().low;
    const subject = single ? "At this catchment" : "Across catchments in this region";
    return `${subject}, the selected large-flood events shifted ${direction}.`;
  }

  signal(metric, label) {
    const outcome = this.outcome();
    return `<div class="fce-signal"><span>${label}</span><strong style="color:${this.colorFor(metric?.slope, outcome.limit)}">${this.signed(metric?.slope, outcome.digits)}</strong><small>${this.escape(outcome.unit)}</small></div>`;
  }

  trajectory(metric, outcome) {
    const rows = metric?.trajectory || [];
    if (rows.length < 2) return "";
    const width = 320;
    const height = 150;
    const pad = { left: 35, right: 10, top: 14, bottom: 25 };
    const values = rows.flatMap((row) => [Number(row[1]), Number(row[2])]).filter(Number.isFinite);
    let min = Math.min(...values);
    let max = Math.max(...values);
    const spread = Math.max(max - min, outcome.group === "Antecedent wetness" ? 0.02 : 2);
    min -= spread * 0.12;
    max += spread * 0.12;
    const x = (year) => pad.left + ((year - rows[0][0]) / Math.max(1, rows[rows.length - 1][0] - rows[0][0])) * (width - pad.left - pad.right);
    const y = (value) => pad.top + ((max - value) / (max - min)) * (height - pad.top - pad.bottom);
    const fit = rows.map((row, index) => `${index ? "L" : "M"}${x(row[0]).toFixed(1)},${y(row[2]).toFixed(1)}`).join(" ");
    const dots = rows.map((row) => `<circle cx="${x(row[0]).toFixed(1)}" cy="${y(row[1]).toFixed(1)}" r="2.2"><title>${row[0]}: ${this.num(row[1], outcome.digits)} · ${row[4]} events</title></circle>`).join("");
    return `<div class="fce-chart"><div class="fce-subhead"><b>Continuous-time trajectory</b><span>adjusted annual mean + fitted trend</span></div>
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Annual trajectory from ${rows[0][0]} to ${rows[rows.length - 1][0]}">
        <line class="grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(min).toFixed(1)}" y2="${y(min).toFixed(1)}"/>
        <line class="grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(max).toFixed(1)}" y2="${y(max).toFixed(1)}"/>
        <text x="${pad.left}" y="${height - 6}">${rows[0][0]}</text><text x="${width - pad.right}" y="${height - 6}" text-anchor="end">${rows[rows.length - 1][0]}</text>
        <text x="${pad.left - 5}" y="${y(max).toFixed(1) + 4}" text-anchor="end">${this.num(max, outcome.digits)}</text>
        <text x="${pad.left - 5}" y="${y(min).toFixed(1) + 4}" text-anchor="end">${this.num(min, outcome.digits)}</text>
        <g class="observed">${dots}</g><path class="fit" d="${fit}"/>
      </svg></div>`;
  }

  sensitivity(metric, outcome) {
    const entries = Object.entries(metric?.sensitivities || {});
    if (!entries.length) return "";
    return `<div class="fce-block"><div class="fce-subhead"><b>Extreme-sample sensitivity</b><span>same metric, alternative samples</span></div><div class="fce-sensitivity">${entries.map(([name, value]) => {
      const available = Number.isFinite(Number(value));
      const same = available && Math.sign(Number(value)) === Math.sign(Number(metric.slope));
      return `<div class="${available ? (same ? "same" : "different") : "missing"}"><span>${this.escape(name)}</span><strong>${this.signed(value, outcome.digits)}</strong></div>`;
    }).join("")}</div></div>`;
  }

  drivers(feature) {
    if (!["intensity_fraction", "intensity_050"].includes(this.metric)) return "";
    const entries = Object.values(feature.drivers || {});
    if (!entries.length) return "";
    return `<div class="fce-block"><div class="fce-subhead"><b>Rainfall-process decomposition</b><span>approximate change per decade</span></div><div class="fce-drivers">${entries.map((item) => `<div><span>${this.escape(item.label)}</span><strong>${this.signed(item.slope, 1)}%</strong><small>95% CI ${this.signed(item.ci?.[0], 1)} to ${this.signed(item.ci?.[1], 1)}%</small></div>`).join("")}</div></div>`;
  }

  gates(metric) {
    if (!metric) return "";
    const gates = [
      ["Complete-family FDR", metric.fdrSupported],
      ["Extreme-sample direction", metric.sampleStable],
      ["SSI-window direction", metric.windowStable],
      ["Leave-one-catchment-out", metric.jackknifeStable]
    ];
    return `<div class="fce-gates">${gates.map(([name, pass]) => `<span class="${pass ? "pass" : "fail"}">${pass ? "✓" : "·"} ${name}</span>`).join("")}</div>`;
  }

  fact(label, value) {
    return `<div class="fce-fact"><span>${label}</span><strong>${value}</strong></div>`;
  }

  showOverview() {
    this.ensureModal();
    const meta = this.data.meta;
    const outcome = this.outcome();
    const rankings = (meta.ranking || []).slice(0, 12);
    this.modal.querySelector(".fce-modal-body").innerHTML = `
      <section class="fce-hero">
        <span class="fce-kicker">${meta.period} · rainfall-driven large floods</span>
        <h2>Where did flood-generating conditions move—and how?</h2>
        <p>The map follows two continuous process dimensions through time: whether event rainfall became more concentrated or more prolonged, and whether the land before the event became wetter or drier. Opposing local changes are retained instead of being averaged into one global direction.</p>
      </section>
      <div class="fce-kpis">
        ${this.kpi(meta.primaryEvents.toLocaleString(), "selected POT/Q95 events")}
        ${this.kpi(meta.primaryCatchments.toLocaleString(), "eligible catchments")}
        ${this.kpi(meta.eligibleHydrobasins, "mapped L5 regions")}
        ${this.kpi(meta.strongEvidenceBasins, "regions with strong evidence")}
      </div>
      <section><h3>Two process dimensions</h3><div class="fce-reading">
        <div><b>Rainfall organization</b><span>Pmax/Pvolume measures how much of an event's rain fell in its wettest day. Positive change means more concentrated rainfall; negative change means more prolonged, volume-dominated rainfall.</span></div>
        <div><b>Antecedent wetness</b><span>SSI summarizes soil wetness before rainfall starts. The 1-, 3-, 7- and 30-day windows show whether a result depends on the chosen memory window.</span></div>
        <div><b>Two spatial layers</b><span>Colored polygons pool neighboring catchments within HydroBASINS L5. Points retain eligible single-catchment trends for local inspection.</span></div>
      </div></section>
      <section><h3>Strongest reproducible local signals</h3><p class="fce-section-note">Click a row to switch the mapped metric and open that HydroBASINS unit.</p>
        <div class="fce-ranking">${rankings.map((item) => {
          const definition = meta.outcomes[item.metric];
          return `<button data-basin="${item.basinId}" data-outcome="${item.metric}"><span>${this.escape(item.code)} · ${this.escape(definition.short)}</span><strong>${this.signed(item.slope, definition.digits)}</strong><i style="width:${Math.min(100, item.score * 100)}%;background:${this.colorFor(item.slope, definition.limit)}"></i></button>`;
        }).join("")}</div>
      </section>
      <section><h3>How evidence is screened</h3><p>All mapped regions have at least ${meta.minimumCatchments} catchments and ${meta.minimumObservations} event observations. The strongest grade additionally requires at least ${meta.strongMinimumCatchments} catchments, complete-family 5% FDR support, the same direction under four alternative extreme samples, leave-one-catchment-out stability, and agreement across all four SSI windows for wetness metrics.</p><p>Time is modeled continuously over the verified ${meta.period} record. No arbitrary calendar breakpoint is used.</p></section>
      <section><h3>Current map</h3><p><b>${this.escape(outcome.label)}</b> — ${this.escape(outcome.definition)}</p><p class="fce-note">Primary sample: ${this.escape(meta.primarySample)}. Reconstructed flood-event and catchment attributes come from Event_Typology; regional boundaries come from HydroBASINS v1.c.</p></section>`;
    this.modal.classList.add("visible");
    this.modal.querySelectorAll("[data-basin]").forEach((button) => button.addEventListener("click", () => {
      this.setMetric(button.dataset.outcome);
      const basin = this.basins.find((item) => item.id === button.dataset.basin);
      if (basin) {
        this.selected = basin;
        this.closeOverview();
        this.showInspector(basin, this.basinLayerId);
        this.app.draw?.();
      }
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

  closeOverview() {
    this.modal?.classList.remove("visible");
  }

  kpi(value, label) {
    return `<div><strong>${value}</strong><span>${label}</span></div>`;
  }

  outcome() {
    return this.data.meta.outcomes[this.metric];
  }

  direction(value) {
    return Number(value) >= 0 ? this.outcome().high : this.outcome().low;
  }

  catchmentLimit() {
    if (this.metric === "intensity_fraction") return 15;
    if (this.metric === "intensity_050") return 30;
    return 0.04;
  }

  axisValue(value) {
    return Math.abs(value) < 0.1 ? Number(value).toFixed(3) : Number(value).toFixed(1).replace(/\.0$/, "");
  }

  integer(value) {
    return Number.isFinite(Number(value)) ? Number(value).toLocaleString() : "—";
  }

  num(value, digits = 2) {
    return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
  }

  prob(value) {
    return Number.isFinite(Number(value)) ? (Number(value) < 0.001 ? "<0.001" : Number(value).toFixed(3)) : "—";
  }

  signed(value, digits = 2) {
    return Number.isFinite(Number(value)) ? `${Number(value) > 0 ? "+" : ""}${Number(value).toFixed(digits)}` : "—";
  }

  escape(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  colorFor(value, maxAbs) {
    if (!Number.isFinite(Number(value))) return "#aeb8c2";
    const t = Math.max(-1, Math.min(1, Number(value) / maxAbs));
    return t < 0 ? this.mix("#2b6487", "#ebe8de", t + 1) : this.mix("#ebe8de", "#cf673f", t);
  }

  mix(a, b, t) {
    const parse = (hex) => [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16));
    const aa = parse(a);
    const bb = parse(b);
    return `rgb(${aa.map((value, index) => Math.round(value + (bb[index] - value) * t)).join(",")})`;
  }

  ensureStyles() {
    if (document.getElementById("fce-styles")) return;
    const style = document.createElement("style");
    style.id = "fce-styles";
    style.textContent = `
      .panel-section-header{font-size:13px}.module-item,.layer-item,.layer-expandable,.layer-sublayer,.map-display-option{font-size:13px}.legend-card{font-size:12px;padding:13px 14px}.legend-title{font-size:14px}.inspector-title{font-size:16px}.inspector-body{font-size:13px;line-height:1.55}
      .fce-toolbar{position:fixed;top:14px;left:50%;transform:translateX(-50%);z-index:850;display:flex;align-items:center;gap:10px;max-width:calc(100vw - 32px);padding:9px 10px 9px 14px;border:1px solid rgba(148,163,184,.35);border-radius:14px;background:rgba(255,255,255,.95);box-shadow:0 10px 30px rgba(15,23,42,.12);backdrop-filter:blur(16px);font:13px/1.25 Inter,system-ui,sans-serif;color:#334155}.fce-toolbar-label{font-weight:750;white-space:nowrap}.fce-segmented{display:flex;padding:3px;border-radius:10px;background:#edf1f4}.fce-segmented button,.fce-overview-button{border:0;border-radius:8px;padding:8px 10px;background:transparent;color:#526171;font:650 12px Inter,system-ui;white-space:nowrap;cursor:pointer}.fce-segmented button.active{background:#fff;color:#173d55;box-shadow:0 2px 8px rgba(15,23,42,.1)}.fce-overview-button{background:#173d55;color:#fff}
      .fce-legend-scale-title{margin:6px 0 5px;font-size:12px;font-weight:750;color:#475569}.fce-legend-bar{height:11px;border-radius:99px;background:linear-gradient(90deg,#2b6487,#ebe8de 50%,#cf673f)}.fce-legend-axis{display:flex;justify-content:space-between;margin-top:4px;font:12px/1.25 ui-monospace,monospace;color:#64748b}.fce-legend-directions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px;font-size:12px;line-height:1.35;color:#526171}.fce-legend-directions span:last-child{text-align:right}.fce-legend-unit,.fce-legend-note{margin:9px 0;font-size:12px;line-height:1.5;color:#64748b}.fce-legend-key{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:12px;line-height:1.35;color:#475569}.fce-legend-key i{display:inline-block;flex:0 0 auto;width:19px;height:10px}.fce-legend-key .boundary{border:1px solid #172235;background:#d8d3c7}.fce-legend-key .limited{border:1px solid #172235;background:#d8d3c7;opacity:.48}.fce-legend-key .glow{height:5px;border:1px solid #67e8f9;box-shadow:0 0 8px 4px rgba(34,211,238,.7)}.fce-legend-key .dot{width:9px;height:9px;border-radius:50%;background:#527b95;border:1px solid #334155}
      .fce-inspector-lead,.fce-note{font-size:12px;line-height:1.65;color:#64748b}.fce-plain-result{margin:12px 0 0;padding:11px 12px;border-left:3px solid #22d3ee;border-radius:0 9px 9px 0;background:#eefbfc;font-size:13px;font-weight:650;line-height:1.5;color:#214558}.fce-signal{margin:12px 0;padding:15px;border-radius:12px;background:#f3f6f7}.fce-signal span,.fce-signal small{display:block;color:#64748b;font-size:12px}.fce-signal strong{display:block;margin:5px 0 3px;font-size:30px;letter-spacing:-.04em}.fce-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px}.fce-fact{padding:11px;border:1px solid #dfe6eb;border-radius:10px}.fce-fact span,.fce-fact strong{display:block}.fce-fact span{font-size:12px;line-height:1.3;text-transform:uppercase;letter-spacing:.025em;color:#6f7f8e}.fce-fact strong{margin-top:5px;font-size:13px;color:#263646}.fce-status{display:inline-block;margin-top:12px;padding:6px 10px;border-radius:99px;font:650 12px/1.25 Inter,system-ui}.fce-status.pass{background:#e3efe7;color:#315e45}.fce-status.neutral{background:#eef1f3;color:#667482}.fce-status.limited{background:#f4ede0;color:#80612e}
      .fce-block,.fce-chart{margin-top:15px;padding-top:13px;border-top:1px solid #e2e8ec}.fce-subhead{display:flex;justify-content:space-between;gap:10px;align-items:baseline;margin-bottom:9px}.fce-subhead b{font-size:13px;color:#314455}.fce-subhead span{font-size:12px;color:#7a8793}.fce-chart svg{display:block;width:100%;height:auto;overflow:visible}.fce-chart svg text{font:11px Inter,system-ui;fill:#758290}.fce-chart .grid{stroke:#dce4e8;stroke-width:1}.fce-chart .observed circle{fill:#7698aa;opacity:.68}.fce-chart .fit{fill:none;stroke:#173d55;stroke-width:2.2;stroke-linecap:round}.fce-sensitivity{display:grid;grid-template-columns:1fr 1fr;gap:7px}.fce-sensitivity div{padding:9px;border-radius:9px;background:#f1f4f5;border-left:3px solid #aab4bc}.fce-sensitivity div.same{border-left-color:#5c9270}.fce-sensitivity div.different{border-left-color:#d27a55}.fce-sensitivity span,.fce-sensitivity strong{display:block;font-size:12px}.fce-sensitivity span{color:#687784}.fce-sensitivity strong{margin-top:3px;color:#263646}.fce-drivers{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.fce-drivers div{padding:10px;border-radius:9px;background:#f1f4f5}.fce-drivers span,.fce-drivers strong,.fce-drivers small{display:block}.fce-drivers span,.fce-drivers small{font-size:11px;line-height:1.4;color:#687784}.fce-drivers strong{margin:4px 0;font-size:16px;color:#263646}.fce-gates{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0}.fce-gates span{padding:6px 9px;border-radius:99px;font:650 12px/1.25 Inter,system-ui}.fce-gates .pass{background:#e4eee7;color:#315e45}.fce-gates .fail{background:#eef1f3;color:#788592}
      .fce-modal{position:fixed;inset:0;z-index:1100;display:none;align-items:center;justify-content:center;padding:28px;background:rgba(15,23,42,.48);backdrop-filter:blur(9px)}.fce-modal.visible{display:flex}.fce-modal-card{position:relative;width:min(940px,94vw);max-height:90vh;overflow:auto;border:1px solid rgba(255,255,255,.5);border-radius:22px;background:#f8fafb;box-shadow:0 32px 90px rgba(15,23,42,.28);color:#223143;font:14px/1.65 Inter,system-ui,sans-serif}.fce-close{position:sticky;float:right;top:14px;margin:14px 14px -50px 0;z-index:2;width:36px;height:36px;border:0;border-radius:50%;background:#e7ecef;color:#415161;font-size:22px;cursor:pointer}.fce-modal-body{padding:42px}.fce-hero{padding:4px 48px 26px 0;border-bottom:1px solid #dce3e8}.fce-kicker{font-size:12px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:#9b6a26}.fce-hero h2{max-width:720px;margin:9px 0 12px;font-size:35px;line-height:1.08;letter-spacing:-.04em;color:#172638}.fce-hero p{max-width:760px;margin:0;color:#5f6f7e}.fce-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:20px 0}.fce-kpis div{padding:15px;border:1px solid #dce3e8;border-radius:13px;background:#fff}.fce-kpis strong,.fce-kpis span{display:block}.fce-kpis strong{font-size:23px;color:#173d55}.fce-kpis span{margin-top:4px;font-size:12px;color:#73818f}.fce-modal section h3{margin:27px 0 8px;font-size:17px;color:#243648}.fce-reading{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.fce-reading div{padding:15px;border-radius:13px;background:#edf2f4}.fce-reading b,.fce-reading span{display:block}.fce-reading span{margin-top:5px;font-size:12px;color:#667684}.fce-section-note{margin-top:-5px;color:#788795;font-size:12px}.fce-ranking{display:grid;grid-template-columns:1fr 1fr;gap:7px}.fce-ranking button{position:relative;overflow:hidden;display:flex;justify-content:space-between;gap:10px;padding:12px 13px;border:1px solid #dce3e8;border-radius:10px;background:#fff;color:#3e4e5d;text-align:left;cursor:pointer}.fce-ranking button span,.fce-ranking button strong{position:relative;z-index:1;font-size:12px}.fce-ranking button i{position:absolute;bottom:0;left:0;height:3px}.fce-ranking button:hover{border-color:#8fa7b5;transform:translateY(-1px)}
      @media(max-width:1100px){.fce-toolbar-label{display:none}.fce-segmented button{padding:8px 7px}.fce-drivers{grid-template-columns:1fr}}
      @media(max-width:780px){.fce-toolbar{top:auto;bottom:12px;max-width:calc(100vw - 24px);flex-wrap:wrap;justify-content:center}.fce-segmented{max-width:100%;overflow:auto}.fce-modal{padding:0}.fce-modal-card{width:100%;max-height:100%;height:100%;border-radius:0}.fce-modal-body{padding:25px}.fce-hero h2{font-size:28px}.fce-kpis{grid-template-columns:1fr 1fr}.fce-reading{grid-template-columns:1fr}.fce-ranking{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }
};
